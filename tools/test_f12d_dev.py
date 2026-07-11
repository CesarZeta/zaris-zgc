r"""Suite en vivo de F12-d (POS Resto: salones/mesas/comandas) contra DEV.

Cubre: caja con perfil resto (CHECK + validación), salones y mesas (alta por
lote con numeración continua, 409 dup, inactivar), comandas de mesa (una
abierta por mesa, 409), ítems con precio de servidor (agregar/editar/quitar),
envío a cocina (payload + 409 sin pendientes), mover/unir mesas, delivery con
envio_estado, cobro que emite factura fiscal vía emitir_core (medios = total,
stock descargado, comanda cerrada con comprobante, mesa liberada), guardas
(comanda vacía 422, cerrada 409, medios que no cuadran 409), reporte de mozos
y arqueo de la sesión que suma la venta. Regla dura: nada de esto llega a la
gestión salvo el comprobante final.

El tenant de prueba se elimina al final (DELETE por cascada vía SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_f12d_dev.py \
        --base http://127.0.0.1:8021
"""

import argparse
import asyncio
import datetime as dt
import json
import subprocess
import sys
import urllib.error as E
import urllib.request as U
import uuid
from decimal import Decimal
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]


def _req(method, base, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=120)
        payload = r.read()
        if "json" not in r.headers.get("Content-Type", ""):
            return r.status, payload
        return r.status, (json.loads(payload) if payload else None)
    except E.HTTPError as ex:
        payload = ex.read()
        try:
            return ex.code, json.loads(payload)
        except Exception:
            return ex.code, payload.decode(errors="replace")


def check(nombre, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok  {nombre}")
    else:
        fail += 1
        print(f" FAIL {nombre}  {extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    razon = f"Resto F12d {SUF}"
    email = f"resto.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 1. tenant efímero (rubro restaurante) =====
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", "pos", "--rubro", "restaurante"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    check("setup_tenant.py plan pos rubro restaurante OK", r.returncode == 0, r.stdout + r.stderr)

    st, login = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    check("login -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    # ===== 2. caja con perfil resto =====
    st, cajas = _req("GET", base, "/pos/cajas", tok)
    check("caja default es perfil estandar",
          st == 200 and cajas and cajas[0]["perfil"] == "estandar", f"{st} {cajas}")
    pv_id = cajas[0]["punto_venta_id"]
    dep_id = cajas[0]["deposito_id"]

    st, caja_resto = _req("POST", base, "/pos/cajas", tok, {
        "nombre": f"Caja Resto {SUF}", "punto_venta_id": pv_id,
        "deposito_id": dep_id, "perfil": "resto",
    })
    check("crear caja perfil resto -> 201", st == 201 and caja_resto["perfil"] == "resto",
          f"{st} {caja_resto}")
    st, _ = _req("POST", base, "/pos/cajas", tok, {
        "nombre": f"Caja X {SUF}", "punto_venta_id": pv_id, "perfil": "kiosco",
    })
    check("perfil inválido -> 422", st == 422, f"{st}")

    # ===== 3. salones y mesas =====
    st, salon = _req("POST", base, "/pos/resto/salones", tok, {"nombre": f"Salón {SUF}"})
    check("crear salón -> 201", st == 201, f"{st} {salon}")
    st, _ = _req("POST", base, "/pos/resto/salones", tok, {"nombre": f"Salón {SUF}"})
    check("salón duplicado -> 409", st == 409, f"{st}")
    st, vereda = _req("POST", base, "/pos/resto/salones", tok, {"nombre": f"Vereda {SUF}", "orden": 1})
    check("segundo salón -> 201", st == 201, f"{st}")

    st, mesas1 = _req("POST", base, "/pos/resto/mesas", tok,
                      {"salon_id": salon["id"], "cantidad": 4})
    check("alta de 4 mesas -> 201 numeradas 1-4",
          st == 201 and [m["numero"] for m in mesas1] == [1, 2, 3, 4], f"{st} {mesas1}")
    st, mesas2 = _req("POST", base, "/pos/resto/mesas", tok,
                      {"salon_id": salon["id"], "cantidad": 2})
    check("segundo lote continúa numeración (5, 6)",
          st == 201 and [m["numero"] for m in mesas2] == [5, 6], f"{st} {mesas2}")
    st, mesas_v = _req("POST", base, "/pos/resto/mesas", tok,
                       {"salon_id": vereda["id"], "cantidad": 2})
    check("mesas de otro salón arrancan en 1",
          st == 201 and [m["numero"] for m in mesas_v] == [1, 2], f"{st} {mesas_v}")

    st, grilla = _req("GET", base, "/pos/resto/mesas", tok)
    check("grilla: 8 mesas todas libres",
          st == 200 and len(grilla) == 8 and all(not m["ocupada"] for m in grilla),
          f"{st} n={len(grilla) if st == 200 else '?'}")

    mesa1, mesa2, mesa3 = mesas1[0], mesas1[1], mesas1[2]

    # ===== 4. artículos de carta =====
    def alta(codigo, descripcion, precio):
        st, a = _req("POST", base, "/articulos", tok, {
            "codigo": codigo, "descripcion": descripcion, "tasa_iva": 21,
            "precio_1": precio,
        })
        check(f"alta {descripcion} -> 201", st == 201, f"{st} {a}")
        return a

    mila = alta(f"MILA{SUF}", f"Milanesa napolitana {SUF}", 8000)
    gaseosa = alta(f"GAS{SUF}", f"Gaseosa 500 {SUF}", 1500)
    flan = alta(f"FLAN{SUF}", f"Flan casero {SUF}", 2000)

    # ===== 5. comanda de mesa =====
    st, comanda = _req("POST", base, "/pos/resto/comandas", tok, {
        "caja_id": caja_resto["id"], "tipo": "mesa", "mesa_id": mesa1["id"], "cubiertos": 2,
    })
    check("abrir comanda de mesa -> 201", st == 201 and comanda["estado"] == "abierta",
          f"{st} {comanda}")
    check("comanda con mesa y salón resueltos",
          comanda["mesa_numero"] == 1 and comanda["salon_nombre"] == f"Salón {SUF}", f"{comanda}")
    st, _ = _req("POST", base, "/pos/resto/comandas", tok, {
        "caja_id": caja_resto["id"], "tipo": "mesa", "mesa_id": mesa1["id"],
    })
    check("segunda comanda en la misma mesa -> 409", st == 409, f"{st}")
    st, _ = _req("POST", base, "/pos/resto/comandas", tok, {
        "caja_id": caja_resto["id"], "tipo": "mesa",
    })
    check("comanda de mesa sin mesa_id -> 422", st == 422, f"{st}")

    # ===== 6. ítems con precio de servidor =====
    st, comanda = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/items", tok, [
        {"articulo_id": mila["id"], "cantidad": "2", "observaciones": "una sin sal"},
        {"articulo_id": gaseosa["id"], "cantidad": "2"},
    ])
    check("agregar ítems -> 200", st == 200 and len(comanda["items"]) == 2, f"{st} {comanda}")
    check("precio resuelto por el server (milanesa 8000)",
          any(Decimal(i["precio_unitario"]) == 8000 for i in comanda["items"]), f"{comanda}")
    check("total de la cuenta 19000", Decimal(comanda["total"]) == 19000, f"{comanda['total']}")
    check("ítems nacen pendientes de cocina",
          all(i["estado_cocina"] == "pendiente" for i in comanda["items"]), f"{comanda}")

    item_gas = next(i for i in comanda["items"] if i["articulo_id"] == gaseosa["id"])
    st, comanda = _req("PATCH", base,
                       f"/pos/resto/comandas/{comanda['id']}/items/{item_gas['id']}", tok,
                       {"cantidad": "3"})
    check("editar cantidad de un ítem -> total 20500",
          st == 200 and Decimal(comanda["total"]) == 20500, f"{st} {comanda.get('total')}")

    # ===== 7. cocina =====
    st, cocina = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/enviar-cocina", tok, {})
    check("enviar a cocina -> 200 con payload",
          st == 200 and len(cocina["items"]) == 2 and cocina["mesa"] == f"Salón {SUF} · Mesa 1",
          f"{st} {cocina}")
    st, _ = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/enviar-cocina", tok, {})
    check("re-enviar sin pendientes -> 409", st == 409, f"{st}")
    st, comanda = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/items", tok, [
        {"articulo_id": flan["id"], "cantidad": "1"},
    ])
    check("postre agregado queda pendiente",
          st == 200 and sum(1 for i in comanda["items"] if i["estado_cocina"] == "pendiente") == 1,
          f"{st}")
    item_flan = next(i for i in comanda["items"] if i["articulo_id"] == flan["id"])
    st, comanda = _req("DELETE", base,
                       f"/pos/resto/comandas/{comanda['id']}/items/{item_flan['id']}", tok)
    check("quitar ítem (pre-fiscal) -> 200 total 20500",
          st == 200 and Decimal(comanda["total"]) == 20500, f"{st}")

    # ===== 8. mover y unir =====
    st, comanda = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/mover", tok,
                       {"mesa_id": mesa2["id"]})
    check("mover a mesa libre -> 200", st == 200 and comanda["mesa_numero"] == 2, f"{st}")

    st, com3 = _req("POST", base, "/pos/resto/comandas", tok, {
        "caja_id": caja_resto["id"], "tipo": "mesa", "mesa_id": mesa3["id"],
    })
    _req("POST", base, f"/pos/resto/comandas/{com3['id']}/items", tok, [
        {"articulo_id": gaseosa["id"], "cantidad": "1"},
    ])
    st, _ = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/mover", tok,
                 {"mesa_id": mesa3["id"]})
    check("mover a mesa ocupada -> 409", st == 409, f"{st}")

    st, comanda = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/unir", tok,
                       {"desde_comanda_id": com3["id"]})
    check("unir mesas: absorbe los ítems (total 22000)",
          st == 200 and Decimal(comanda["total"]) == 22000 and len(comanda["items"]) == 3,
          f"{st} {comanda.get('total')}")
    st, com3_post = _req("GET", base, f"/pos/resto/comandas/{com3['id']}", tok)
    check("la comanda unida queda anulada y su mesa libre",
          st == 200 and com3_post["estado"] == "anulada" and not com3_post["items"], f"{st}")
    st, grilla = _req("GET", base, "/pos/resto/mesas", tok)
    ocupadas = {m["numero"] for m in grilla if m["ocupada"] and m["salon_nombre"] == f"Salón {SUF}"}
    check("grilla: solo la mesa 2 ocupada", ocupadas == {2}, f"{ocupadas}")

    # ===== 9. cobro (cierre de mesa -> factura fiscal) =====
    st, sesion = _req("POST", base, "/pos/sesiones", tok,
                      {"caja_id": caja_resto["id"], "fondo_inicial": "0"})
    check("abrir sesión en la caja resto -> 201", st == 201, f"{st} {sesion}")
    check("la sesión expone el perfil de la caja", sesion.get("caja_perfil") == "resto", f"{sesion}")

    st, _ = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/cobrar", tok, {
        "sesion_id": sesion["id"],
        "medios": [{"medio": "efectivo", "importe": "1"}],
    })
    check("medios que no cuadran -> 409", st == 409, f"{st}")

    st, calc = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_resto["id"],
        "items": [{"articulo_id": i["articulo_id"], "variante_id": i["variante_id"],
                   "cantidad": i["cantidad"]} for i in comanda["items"]],
    })
    check("calcular el cobro -> total 22000", st == 200 and Decimal(calc["total"]) == 22000,
          f"{st} {calc}")

    st, venta = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/cobrar", tok, {
        "sesion_id": sesion["id"],
        "medios": [{"medio": "efectivo", "importe": "12000"},
                   {"medio": "tarjeta", "importe": "10000"}],
        "propina_pct": "10",
    })
    check("cobrar la mesa -> 200 factura emitida",
          st == 200 and venta.get("numero_formateado"), f"{st} {venta}")

    st, comanda_post = _req("GET", base, f"/pos/resto/comandas/{comanda['id']}", tok)
    check("comanda cerrada con comprobante y propina sellada",
          st == 200 and comanda_post["estado"] == "cerrada"
          and comanda_post["comprobante_id"] == venta["id"]
          and Decimal(comanda_post["propina_pct"]) == 10, f"{st} {comanda_post}")
    st, _ = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/cobrar", tok, {
        "sesion_id": sesion["id"], "medios": [{"medio": "efectivo", "importe": "22000"}],
    })
    check("re-cobrar comanda cerrada -> 409", st == 409, f"{st}")

    st, grilla = _req("GET", base, "/pos/resto/mesas", tok)
    check("la mesa quedó libre tras el cobro",
          st == 200 and not any(m["ocupada"] for m in grilla), f"{st}")

    st, stock_mila = _req("GET", base, f"/stock/articulo/{mila['id']}", tok)
    check("el cobro descargó stock (milanesa -2)",
          st == 200 and any(Decimal(f["cantidad"]) == -2 for f in stock_mila), f"{st} {stock_mila}")

    st, resumen = _req("GET", base, f"/pos/sesiones/{sesion['id']}/resumen", tok)
    check("arqueo de la sesión suma la venta de la mesa",
          st == 200 and resumen["cantidad_tickets"] == 1
          and Decimal(resumen["total_ventas"]) == 22000, f"{st} {resumen}")

    # ===== 10. delivery =====
    st, pedido = _req("POST", base, "/pos/resto/comandas", tok, {
        "caja_id": caja_resto["id"], "tipo": "delivery",
        "cliente_nombre": "Juan Pérez", "telefono": "341-5555555",
        "domicilio": "Av. Siempreviva 742", "localidad": "Rosario",
    })
    check("pedido delivery -> 201 en_preparacion",
          st == 201 and pedido["envio_estado"] == "en_preparacion" and pedido["mesa_id"] is None,
          f"{st} {pedido}")
    st, pedido = _req("PATCH", base, f"/pos/resto/comandas/{pedido['id']}", tok,
                      {"envio_estado": "despachado"})
    check("PATCH envio_estado despachado -> 200", st == 200, f"{st}")
    _req("POST", base, f"/pos/resto/comandas/{pedido['id']}/items", tok, [
        {"articulo_id": mila["id"], "cantidad": "1"},
    ])
    st, venta2 = _req("POST", base, f"/pos/resto/comandas/{pedido['id']}/cobrar", tok, {
        "sesion_id": sesion["id"], "medios": [{"medio": "mercadopago", "importe": "8000"}],
    })
    check("cobrar delivery -> 200", st == 200 and venta2.get("numero_formateado"), f"{st} {venta2}")
    st, pedido = _req("PATCH", base, f"/pos/resto/comandas/{pedido['id']}", tok,
                      {"envio_estado": "entregado"})
    check("marcar entregado con la comanda cerrada -> 200",
          st == 200 and pedido["envio_estado"] == "entregado", f"{st}")
    st, _ = _req("PATCH", base, f"/pos/resto/comandas/{pedido['id']}", tok,
                 {"cliente_nombre": "Otro"})
    check("editar datos de una comanda cerrada -> 409", st == 409, f"{st}")

    # ===== 11. anular comanda abierta + guardas =====
    st, com_anular = _req("POST", base, "/pos/resto/comandas", tok, {
        "caja_id": caja_resto["id"], "tipo": "mesa", "mesa_id": mesa1["id"],
    })
    st, _ = _req("POST", base, f"/pos/resto/comandas/{com_anular['id']}/cobrar", tok, {
        "sesion_id": sesion["id"], "medios": [{"medio": "efectivo", "importe": "1"}],
    })
    check("cobrar comanda sin ítems -> 422", st == 422, f"{st}")
    st, com_anulada = _req("POST", base, f"/pos/resto/comandas/{com_anular['id']}/anular", tok, {})
    check("anular comanda abierta -> 200 (mesa libre, sin factura)",
          st == 200 and com_anulada["estado"] == "anulada", f"{st}")

    # ===== 12. reporte de mozos =====
    hoy = dt.date.today().isoformat()
    st, mozos = _req("GET", base, f"/pos/resto/reporte-mozos?desde={hoy}&hasta={hoy}", tok)
    check("reporte mozos: 2 comandas cobradas, $30.000, propina $2.200",
          st == 200 and len(mozos) == 1 and mozos[0]["comandas"] == 2
          and Decimal(mozos[0]["total_vendido"]) == 30000
          and Decimal(mozos[0]["propina_estimada"]) == 2200, f"{st} {mozos}")

    _req("POST", base, f"/pos/sesiones/{sesion['id']}/cerrar", tok, {"efectivo_contado": None})

    # ===== 13. cleanup =====
    async def _cleanup():
        from sqlalchemy import text as _text

        from app.core.db import SessionLocal

        async with SessionLocal() as db:
            await db.execute(
                _text("delete from tenants where razon_social = :r"), {"r": razon}
            )
            await db.commit()

    try:
        asyncio.run(_cleanup())
        print(f"  --  cleanup: tenant '{razon}' eliminado")
    except Exception as ex:  # noqa: BLE001
        print(f"  !!  cleanup falló (borrar a mano): {ex}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
