"""Smoke de F11 (Vendedores y comisiones) contra PROD.

Ciclo corto y limpio en el tenant DEMO: vendedor de smoke → venta contado con
vendedor → pendientes → liquidar → asiento derivado → anular liquidación →
NC espejo de la venta (deja la operatoria neutra) → inactivar vendedor.

Uso:
    python tools/smoke_f11_prod.py --email demo@zaris.com.ar --clave "..."
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import date, timedelta
from decimal import Decimal

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]
NUM6 = f"{int(SUF, 16) % 1_000_000:06d}"


def _req(method, base, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=90)
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


def D(x) -> Decimal:
    return Decimal(str(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://zaris-zgc-api.vercel.app")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print("login FAIL", st, r)
        sys.exit(1)
    tok = r["access_token"]
    print(f"login OK — sufijo {SUF}")

    # 1. migración viva: listados con las columnas nuevas
    st, vs = _req("GET", base, "/vendedores", tok)
    check("GET /vendedores responde (migración 017 viva)", st == 200, f"{st}")
    st, comps = _req("GET", base, "/ventas/comprobantes?limit=1", tok)
    check("listado de ventas expone vendedor_id",
          st == 200 and (not comps or "vendedor_id" in comps[0]), f"{st}")

    # 2. vendedor smoke + venta con vendedor
    st, v = _req("POST", base, "/vendedores", tok, {
        "entidad": {"razon_social": f"Smoke Vendedor {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": NUM6, "condicion_iva": "CF"},
        "comision_pct": "5", "modalidad": "venta"})
    check("alta vendedor -> 201", st == 201, f"{st} {v}")
    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    st, arts = _req("GET", base, "/articulos?limit=1", tok)
    if not arts:
        print("sin artículos en el tenant demo — abortando")
        sys.exit(1)
    st, vb = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pvs[0]["id"], "contado": True,
        "precios_con_iva": True, "vendedor_id": v["id"],
        "items": [{"articulo_id": arts[0]["id"], "cantidad": "1",
                   "precio_unitario": "121.00", "tasa_iva": "21"}]})
    st, f1 = _req("POST", base, f"/ventas/comprobantes/{vb['id']}/emitir", tok,
                  {"medios": [{"medio": "efectivo", "importe": vb["total"]}]})
    check("venta emitida con vendedor sellado", st == 200 and f1["vendedor_id"] == v["id"], f"{st}")

    # 3. pendientes + liquidación
    st, pend = _req("GET", base,
                    f"/vendedores/{v['id']}/comisiones/pendientes?desde={ayer}&hasta={hoy}", tok)
    check("pendientes con la venta", st == 200 and len(pend) == 1, f"{st} n={len(pend) if isinstance(pend, list) else pend}")
    st, lq = _req("POST", base, f"/vendedores/{v['id']}/liquidaciones", tok,
                  {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("liquidación -> 201", st == 201 and D(lq["total"]) > 0, f"{st}")
    st, csv_b = _req("GET", base, f"/vendedores/liquidaciones/{lq['id']}/export.csv", tok)
    check("export.csv responde", st == 200, f"{st}")

    # 4. derivación contable en prod
    st, gen = _req("POST", base, "/contabilidad/regenerar", tok,
                   {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    st, asientos = _req("GET", base,
                        f"/contabilidad/asientos?desde={ayer}&hasta={hoy}&origen=comision&limit=20", tok)
    check("asiento de comisión derivado en prod",
          st == 200 and any(f"LC-{lq['numero']:08d}" in (a["descripcion"] or "") for a in asientos),
          f"{st} n={len(asientos) if isinstance(asientos, list) else asientos}")

    # 5. limpieza: anular liquidación, NC espejo de la venta, regenerar, inactivar
    st, _ = _req("POST", base, f"/vendedores/liquidaciones/{lq['id']}/anular", tok)
    check("anular liquidación smoke", st == 200, f"{st}")
    st, nc = _req("POST", base, f"/ventas/comprobantes/{f1['id']}/nota-credito", tok)
    st, nc = _req("POST", base, f"/ventas/comprobantes/{nc['id']}/emitir", tok, {})
    check("NC espejo emitida (operatoria neutra)", st == 200 and nc["vendedor_id"] == v["id"], f"{st}")
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    st, v_off = _req("PUT", base, f"/vendedores/{v['id']}", tok, {"activo": False})
    check("vendedor smoke inactivado", st == 200 and v_off["activo"] is False, f"{st}")

    print(f"\n===== SMOKE F11 PROD: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
