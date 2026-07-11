r"""Smoke E2E de F12-b/c/d contra PROD (Vercel), sobre un tenant EFÍMERO.

El tenant se crea antes con `tools/setup_tenant.py` (contra la DB de prod, con
.env.prod temporal) y se elimina después por psql — esta suite solo pega a la
API pública. Ciclo completo: balanza (config + etiqueta peso), venta por
departamento, despiece con costeo por valor, y POS resto (salón/mesa/comanda/
cocina/cobro fiscal simulado + reporte de mozos).

Uso:
    python tools/smoke_f12_prod.py --base https://zaris-zgc-api.vercel.app \
        --email <admin del tenant efimero> --clave <clave>
"""

import argparse
import datetime as dt
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
from decimal import Decimal

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


def dv_ean13(doce: str) -> int:
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(doce))
    return (10 - suma % 10) % 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://zaris-zgc-api.vercel.app")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    st, login = _req("POST", base, "/auth/login",
                     body={"email": args.email, "password": args.clave})
    check("login prod -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    st, cajas = _req("GET", base, "/pos/cajas", tok)
    check("caja default con perfil (migración 021 viva)",
          st == 200 and cajas and cajas[0].get("perfil") == "estandar", f"{st} {cajas}")
    caja_id = cajas[0]["id"]
    pv_id = cajas[0]["punto_venta_id"]
    dep = cajas[0]["deposito_id"]

    # ===== F12-b: balanza + departamento =====
    st, cfg = _req("PUT", base, "/pos/balanza-config", tok,
                   {"habilitado": True, "prefijo": "20", "valor_tipo": "peso", "codigo_digitos": 5})
    check("PUT balanza-config (migración 019 viva)", st == 200 and cfg["prefijo"] == "20",
          f"{st} {cfg}")
    st, carne = _req("POST", base, "/articulos", tok, {
        "codigo": f"SMK-CARNE{SUF}", "descripcion": f"Smoke carne {SUF}",
        "tasa_iva": 21, "precio_1": 5000, "pesable": True, "codigo_balanza": "77",
    })
    check("alta pesable con PLU -> 201", st == 201, f"{st} {carne}")
    doce = "20" + "00077" + "01250"
    q = doce + str(dv_ean13(doce))
    st, res = _req("GET", base, f"/pos/buscar?q={q}&caja_id={caja_id}", tok)
    check("etiqueta de balanza -> cantidad 1.250 kg",
          st == 200 and len(res) == 1 and res[0]["cantidad"] == "1.250"
          and res[0]["articulo_id"] == carne["id"], f"{st} {res}")

    st, depto = _req("POST", base, "/articulos", tok, {
        "codigo": f"SMK-DEP{SUF}", "descripcion": f"Smoke depto {SUF}",
        "tasa_iva": 21, "venta_por_depto": True, "controla_stock": False,
    })
    check("alta departamento -> 201", st == 201, f"{st}")
    st, calc = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id,
        "items": [{"articulo_id": depto["id"], "cantidad": "1", "precio_unitario": "1210"}],
    })
    check("venta por depto: calcular total 1210",
          st == 200 and float(calc["total"]) == 1210.0, f"{st} {calc}")

    # ===== F12-c: despiece =====
    st, lomo = _req("POST", base, "/articulos", tok, {
        "codigo": f"SMK-LOMO{SUF}", "descripcion": f"Smoke lomo {SUF}",
        "tasa_iva": 21, "precio_1": 15000,
    })
    st, _ = _req("POST", base, "/stock/ajuste", tok, {
        "articulo_id": carne["id"], "deposito_id": dep, "delta": "20",
    })
    check("ajuste inicial +20 -> 201", st == 201, f"{st}")
    st, plantilla = _req("POST", base, "/stock/despiece-plantillas", tok, {
        "nombre": f"Smoke despiece {SUF}", "articulo_origen_id": carne["id"],
        "cortes": [{"articulo_id": lomo["id"], "rendimiento_pct": "90", "coef_valor": "2"}],
    })
    check("plantilla de despiece -> 201 (migración 020 viva)", st == 201, f"{st} {plantilla}")
    st, tr = _req("POST", base, "/stock/transformacion", tok, {
        "deposito_id": dep, "articulo_origen_id": carne["id"], "cantidad_origen": "10",
        "costo_total": "40000",
        "cortes": [{"articulo_id": lomo["id"], "cantidad": "9", "coef_valor": "2"}],
    })
    check("transformación -> 201 con costeo por valor (40000/9... coef único)",
          st == 201 and Decimal(tr["merma"]) == 1
          and Decimal(tr["costos_corte"][0]["costo_unitario"]) == Decimal("4444.4444"),
          f"{st} {tr}")

    # ===== F12-d: resto =====
    st, caja_resto = _req("POST", base, "/pos/cajas", tok, {
        "nombre": f"Smoke Resto {SUF}", "punto_venta_id": pv_id,
        "deposito_id": dep, "perfil": "resto",
    })
    check("caja perfil resto -> 201", st == 201 and caja_resto["perfil"] == "resto",
          f"{st} {caja_resto}")
    st, salon = _req("POST", base, "/pos/resto/salones", tok, {"nombre": f"Salón smoke {SUF}"})
    check("salón -> 201", st == 201, f"{st}")
    st, mesas = _req("POST", base, "/pos/resto/mesas", tok,
                     {"salon_id": salon["id"], "cantidad": 2})
    check("2 mesas -> 201", st == 201 and len(mesas) == 2, f"{st}")

    st, comanda = _req("POST", base, "/pos/resto/comandas", tok, {
        "caja_id": caja_resto["id"], "tipo": "mesa", "mesa_id": mesas[0]["id"],
    })
    check("comanda de mesa -> 201", st == 201, f"{st} {comanda}")
    st, comanda = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/items", tok, [
        {"articulo_id": lomo["id"], "cantidad": "2", "observaciones": "jugoso"},
    ])
    check("ítems con precio de servidor (2×15000=30000)",
          st == 200 and Decimal(comanda["total"]) == 30000, f"{st} {comanda}")
    st, cocina = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/enviar-cocina", tok, {})
    check("enviar a cocina -> payload", st == 200 and len(cocina["items"]) == 1, f"{st}")

    st, sesion = _req("POST", base, "/pos/sesiones", tok,
                      {"caja_id": caja_resto["id"], "fondo_inicial": "0"})
    check("sesión en caja resto -> 201 con caja_perfil",
          st == 201 and sesion.get("caja_perfil") == "resto", f"{st} {sesion}")
    st, venta = _req("POST", base, f"/pos/resto/comandas/{comanda['id']}/cobrar", tok, {
        "sesion_id": sesion["id"],
        "medios": [{"medio": "efectivo", "importe": "30000"}],
        "propina_pct": "10",
    })
    check("cobrar la mesa -> factura fiscal (simulada)",
          st == 200 and venta.get("numero_formateado"), f"{st} {venta}")
    st, grilla = _req("GET", base, "/pos/resto/mesas", tok)
    check("mesa liberada tras el cobro", st == 200 and not any(m["ocupada"] for m in grilla),
          f"{st}")
    hoy = dt.date.today().isoformat()
    st, mozos = _req("GET", base, f"/pos/resto/reporte-mozos?desde={hoy}&hasta={hoy}", tok)
    check("reporte mozos: 1 comanda $30.000 propina $3.000",
          st == 200 and len(mozos) == 1 and Decimal(mozos[0]["total_vendido"]) == 30000
          and Decimal(mozos[0]["propina_estimada"]) == 3000, f"{st} {mozos}")
    _req("POST", base, f"/pos/sesiones/{sesion['id']}/cerrar", tok, {"efectivo_contado": None})

    print(f"\n===== SMOKE F12 PROD: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
