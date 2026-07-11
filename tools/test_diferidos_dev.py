r"""Suite en vivo del LOTE DE DIFERIDOS contra DEV (2026-07-11).

Cubre los 5 diferidos menores:
1. Descuento por línea y por venta en el POS (calcular + venta emitida con
   bonif_pct sellado, guardas 422).
2. Vendedor en recibo (explícito, default al habitual, inexistente 422) —
   el backend era de F11; acá se asegura el contrato que usa el modal nuevo.
3. Sucursal en órdenes de pago: sellada en la OP y la planilla por sucursal
   suma sus pagos (deltas, nunca absolutos — día compartido).
4. Cache de resultados del padrón ARCA (desde_cache, TTL implícito, DV 422).
5. Export CSV de clientes / proveedores / artículos (BOM, ';', filtro q).

El tenant de prueba se elimina al final (DELETE por cascada vía SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_diferidos_dev.py \
        --base http://127.0.0.1:8021
"""

import argparse
import asyncio
import json
import subprocess
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import date
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


def cuit_con_dv(prefijo: str, dni8: str) -> str | None:
    """CUIT válido (o None si el DV daría 10)."""
    cuerpo = prefijo + dni8
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    dv = 11 - sum(int(d) * p for d, p in zip(cuerpo, pesos)) % 11
    if dv == 11:
        dv = 0
    if dv == 10:
        return None
    return cuerpo + str(dv)


def cuit_unico() -> str:
    base = int(SUF, 16) % 89_999_999 + 10_000_000
    for i in range(20):
        c = cuit_con_dv("20", str(base + i).zfill(8))
        if c:
            return c
    raise RuntimeError("no salió un CUIT válido")


def pagos_medio(planilla: dict, medio: str) -> float:
    return next((float(p["total"]) for p in planilla["pagos"] if p["medio"] == medio), 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    razon = f"Diferidos {SUF}"
    email = f"diferidos.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 0. tenant efímero =====
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", "suite", "--rubro", "general"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    check("setup_tenant.py corre OK", r.returncode == 0, r.stdout + r.stderr)

    st, login = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    check("login -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    st, cajas = _req("GET", base, "/pos/cajas", tok)
    caja_id = cajas[0]["id"]
    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    check("GET /ventas/puntos-venta trae el PV default", st == 200 and len(pvs) >= 1, f"{st} {pvs}")
    pv_id = pvs[0]["id"]

    # ===== 1. POS: descuento por línea y por venta =====
    st, art = _req("POST", base, "/articulos", tok, {
        "codigo": f"DESC{SUF}", "descripcion": f"Artículo descuento {SUF}",
        "tasa_iva": 21, "precio_1": 1000,
    })
    check("alta artículo precio 1000 -> 201", st == 201, f"{st} {art}")

    st, calc = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id,
        "items": [{"articulo_id": art["id"], "cantidad": "1"}],
    })
    check("calcular sin descuento -> total 1000", st == 200 and float(calc["total"]) == 1000.0,
          f"{st} {calc}")

    st, calc = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id, "descuento_pct": "10",
        "items": [{"articulo_id": art["id"], "cantidad": "1"}],
    })
    check("descuento 10% a la venta -> total 900", st == 200 and float(calc["total"]) == 900.0,
          f"{st} {calc}")

    st, calc = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id,
        "items": [{"articulo_id": art["id"], "cantidad": "1", "descuento_pct": "10"}],
    })
    check("descuento 10% por línea -> total 900", st == 200 and float(calc["total"]) == 900.0,
          f"{st} {calc}")

    st, calc = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id, "descuento_pct": "10",
        "items": [{"articulo_id": art["id"], "cantidad": "1", "descuento_pct": "10"}],
    })
    check("línea 10% + venta 10% -> total 810 (multiplicativos)",
          st == 200 and float(calc["total"]) == 810.0, f"{st} {calc}")

    st, _ = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id, "descuento_pct": "150",
        "items": [{"articulo_id": art["id"], "cantidad": "1"}],
    })
    check("descuento venta > 100 -> 422", st == 422, f"{st}")
    st, _ = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id,
        "items": [{"articulo_id": art["id"], "cantidad": "1", "descuento_pct": "150"}],
    })
    check("descuento línea > 100 -> 422", st == 422, f"{st}")

    st, sesion = _req("POST", base, "/pos/sesiones", tok,
                      {"caja_id": caja_id, "fondo_inicial": "500"})
    check("abrir sesión POS -> 201", st == 201, f"{st} {sesion}")
    st, venta = _req("POST", base, "/pos/ventas", tok, {
        "sesion_id": sesion["id"], "descuento_pct": "10",
        "items": [{"articulo_id": art["id"], "cantidad": "1", "descuento_pct": "10"}],
        "medios": [{"medio": "efectivo", "importe": "810.00"}],
    })
    check("venta POS con descuentos emitida -> 201", st == 201, f"{st} {venta}")
    if st == 201:
        st, det = _req("GET", base, f"/ventas/comprobantes/{venta['id']}", tok)
        check("bonif_pct 10 sellado en el ítem fiscal",
              st == 200 and float(det["items"][0]["bonif_pct"]) == 10.0, f"{st} {det}")
        check("descuento_pct 10 sellado en el comprobante",
              float(det["descuento_pct"]) == 10.0, f"{det.get('descuento_pct')}")
        check("total fiscal 810", float(det["total"]) == 810.0, f"{det.get('total')}")
    _req("POST", base, f"/pos/sesiones/{sesion['id']}/cerrar", tok, {"efectivo_contado": None})

    # ===== 2. vendedor en recibo =====
    st, vend = _req("POST", base, "/vendedores", tok, {
        "entidad": {"razon_social": f"Vendedor Dif {SUF}", "tipo_documento": "SD"},
        "comision_pct": "5", "modalidad": "cobranza",
    })
    check("alta vendedor -> 201", st == 201, f"{st} {vend}")

    st, cli = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente Dif {SUF}", "tipo_documento": "SD"},
    })
    check("alta cliente sin habitual -> 201", st == 201, f"{st} {cli}")
    st, cli_hab = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente Hab {SUF}", "tipo_documento": "SD"},
        "vendedor_id": vend["id"],
    })
    check("alta cliente con vendedor habitual -> 201", st == 201, f"{st} {cli_hab}")

    st, rec = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli["id"],
        "medios": [{"medio": "efectivo", "importe": "111.11"}],
        "imputaciones": [], "vendedor_id": vend["id"],
    })
    check("recibo con vendedor explícito -> sellado",
          st in (200, 201) and rec.get("vendedor_id") == vend["id"], f"{st} {rec}")

    st, rec2 = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli_hab["id"],
        "medios": [{"medio": "efectivo", "importe": "222.22"}],
        "imputaciones": [],
    })
    check("recibo sin vendedor -> hereda el habitual del cliente",
          st in (200, 201) and rec2.get("vendedor_id") == vend["id"], f"{st} {rec2}")

    st, _ = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli["id"],
        "medios": [{"medio": "efectivo", "importe": "10"}],
        "imputaciones": [], "vendedor_id": str(uuid.uuid4()),
    })
    check("recibo con vendedor inexistente -> 422", st == 422, f"{st}")

    # ===== 3. sucursal en OP + planilla =====
    st, suc = _req("POST", base, "/sucursales", tok, {"nombre": f"Sucursal Dif {SUF}"})
    check("alta sucursal -> 201", st in (200, 201), f"{st} {suc}")

    st, prov = _req("POST", base, "/proveedores", tok, {
        "entidad": {"razon_social": f"Proveedor Dif {SUF}", "tipo_documento": "SD"},
    })
    check("alta proveedor -> 201", st == 201, f"{st} {prov}")

    # importes únicos por corrida (regla de suites: nada de valores fijos)
    imp1 = f"{700 + int(SUF, 16) % 200}.31"
    imp2 = f"{300 + int(SUF, 16) % 150}.47"
    hoy = date.today().isoformat()

    st, pl_g0 = _req("GET", base, f"/caja/planilla?fecha={hoy}", tok)
    st2, pl_s0 = _req("GET", base, f"/caja/planilla?fecha={hoy}&sucursal_id={suc['id']}", tok)
    check("planillas base -> 200", st == 200 and st2 == 200, f"{st} {st2}")

    st, op1 = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov["id"], "sucursal_id": suc["id"],
        "medios": [{"medio": "efectivo", "importe": imp1}], "imputaciones": [],
    })
    check("OP con sucursal -> 201 y sucursal_id sellado",
          st == 201 and op1.get("sucursal_id") == suc["id"], f"{st} {op1}")

    st, op2 = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov["id"],
        "medios": [{"medio": "efectivo", "importe": imp2}], "imputaciones": [],
    })
    check("OP sin sucursal -> 201 con sucursal_id null",
          st == 201 and op2.get("sucursal_id") is None, f"{st} {op2}")

    st, _ = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov["id"], "sucursal_id": str(uuid.uuid4()),
        "medios": [{"medio": "efectivo", "importe": "10"}], "imputaciones": [],
    })
    check("OP con sucursal inexistente -> 422", st == 422, f"{st}")

    st, pl_g1 = _req("GET", base, f"/caja/planilla?fecha={hoy}", tok)
    st2, pl_s1 = _req("GET", base, f"/caja/planilla?fecha={hoy}&sucursal_id={suc['id']}", tok)
    delta_g = pagos_medio(pl_g1, "efectivo") - pagos_medio(pl_g0, "efectivo")
    delta_s = pagos_medio(pl_s1, "efectivo") - pagos_medio(pl_s0, "efectivo")
    check("planilla GLOBAL suma ambas OP (delta)",
          abs(delta_g - (float(imp1) + float(imp2))) < 0.001, f"delta_g={delta_g}")
    check("planilla de la SUCURSAL suma solo su OP (delta)",
          abs(delta_s - float(imp1)) < 0.001, f"delta_s={delta_s}")

    # ===== 4. cache del padrón =====
    cuit = cuit_unico()
    st, p1 = _req("GET", base, f"/padron/{cuit}", tok)
    check("padrón 1ª consulta -> 200 sin cache",
          st == 200 and p1["desde_cache"] is False and p1["fuente"] == "simulado", f"{st} {p1}")
    st, p2 = _req("GET", base, f"/padron/{cuit}", tok)
    check("padrón 2ª consulta -> desde_cache true",
          st == 200 and p2["desde_cache"] is True, f"{st} {p2}")
    check("cache devuelve los mismos datos",
          p1["razon_social"] == p2["razon_social"] and p1["condicion_iva"] == p2["condicion_iva"],
          f"{p1} vs {p2}")
    cuit_malo = cuit[:-1] + str((int(cuit[-1]) + 1) % 10)
    st, _ = _req("GET", base, f"/padron/{cuit_malo}", tok)
    check("padrón DV inválido -> 422", st == 422, f"{st}")

    # ===== 5. exports CSV =====
    for recurso, esperado in (
        ("clientes", f"Cliente Dif {SUF}"),
        ("proveedores", f"Proveedor Dif {SUF}"),
        ("articulos", f"DESC{SUF}"),
    ):
        st, cuerpo = _req("GET", base, f"/{recurso}/export.csv", tok)
        texto = cuerpo.decode("utf-8-sig") if isinstance(cuerpo, bytes) else str(cuerpo)
        check(f"GET /{recurso}/export.csv -> 200 con BOM y ';'",
              st == 200 and isinstance(cuerpo, bytes) and cuerpo.startswith(b"\xef\xbb\xbf")
              and ";" in texto.splitlines()[0], f"{st}")
        check(f"export {recurso} contiene el registro de la corrida",
              esperado in texto, esperado)

    st, cuerpo = _req("GET", base, f"/articulos/export.csv?q=DESC{SUF}", tok)
    texto = cuerpo.decode("utf-8-sig") if isinstance(cuerpo, bytes) else str(cuerpo)
    check("export artículos respeta el filtro q (solo 1 fila + encabezado)",
          st == 200 and len([ln for ln in texto.splitlines() if ln.strip()]) == 2, f"{st}")

    # ===== cleanup =====
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
