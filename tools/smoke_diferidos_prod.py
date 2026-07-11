r"""Smoke del LOTE DE DIFERIDOS contra PROD (neutro: solo lecturas y dry-runs
sobre el tenant demo — no crea documentos; a lo sumo una caja POS de vitrina).

Cubre: probe de deploy por openapi (rutas export + desde_cache + OrdenPagoIn.
sucursal_id), exports CSV con BOM, cache del padrón (verifica de paso la
migración 022: sin la tabla, la 2ª consulta no cachea), planilla por sucursal
(el code path nuevo de OP) y cálculo POS con descuentos (dry-run, sin emitir).

Uso:
    python tools/smoke_diferidos_prod.py --email demo@zaris.com.ar --clave ...
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://zaris-zgc-api.vercel.app"
ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]


def _req(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(BASE + path, data=data, method=method)
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


def cuit_unico() -> str:
    base = int(SUF, 16) % 89_999_999 + 10_000_000
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    for i in range(20):
        cuerpo = "20" + str(base + i).zfill(8)
        dv = 11 - sum(int(d) * p for d, p in zip(cuerpo, pesos)) % 11
        if dv == 11:
            dv = 0
        if dv < 10:
            return cuerpo + str(dv)
    raise RuntimeError("no salió un CUIT válido")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()

    # ===== 1. probe de deploy: openapi =====
    st, spec = _req("GET", "/openapi.json")
    texto = json.dumps(spec) if isinstance(spec, dict) else str(spec)
    check("openapi -> 200", st == 200, f"{st}")
    for ruta in ("/clientes/export.csv", "/proveedores/export.csv", "/articulos/export.csv"):
        check(f"openapi expone {ruta}", f"/api/v1{ruta}" in texto, "")
    check("openapi expone desde_cache (padrón)", "desde_cache" in texto, "")
    check("openapi: OrdenPagoIn con sucursal_id",
          "sucursal_id" in json.dumps(spec.get("components", {}).get("schemas", {})
                                      .get("OrdenPagoIn", {})), "")

    # ===== 2. login demo =====
    st, login = _req("POST", "/api/v1/auth/login",
                     body={"email": args.email, "password": args.clave})
    check("login demo -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    # ===== 3. exports CSV =====
    for recurso in ("clientes", "proveedores", "articulos"):
        st, cuerpo = _req("GET", f"/api/v1/{recurso}/export.csv", tok)
        check(f"GET /{recurso}/export.csv -> 200 con BOM y ';'",
              st == 200 and isinstance(cuerpo, bytes) and cuerpo.startswith(b"\xef\xbb\xbf")
              and ";" in cuerpo.decode("utf-8-sig").splitlines()[0], f"{st}")

    # ===== 4. cache del padrón (verifica la 022 de paso) =====
    cuit = cuit_unico()
    st, p1 = _req("GET", f"/api/v1/padron/{cuit}", tok)
    check("padrón 1ª -> 200 sin cache", st == 200 and p1.get("desde_cache") is False,
          f"{st} {p1}")
    st, p2 = _req("GET", f"/api/v1/padron/{cuit}", tok)
    check("padrón 2ª -> desde_cache true (tabla 022 viva)",
          st == 200 and p2.get("desde_cache") is True, f"{st} {p2}")

    # ===== 5. planilla por sucursal (code path nuevo de OP) =====
    st, sucs = _req("GET", "/api/v1/sucursales", tok)
    check("GET /sucursales -> 200", st == 200 and len(sucs) >= 1, f"{st}")
    if sucs:
        hoy = date.today().isoformat()
        st, pl = _req("GET", f"/api/v1/caja/planilla?fecha={hoy}&sucursal_id={sucs[0]['id']}", tok)
        check("planilla por sucursal -> 200 con pagos[]",
              st == 200 and isinstance(pl.get("pagos"), list), f"{st}")

    # ===== 6. POS: cálculo con descuentos (dry-run, no emite) =====
    st, cajas = _req("GET", "/api/v1/pos/cajas", tok)
    caja = next((c for c in cajas if c.get("perfil", "estandar") == "estandar"), None) \
        if st == 200 else None
    if caja is None:
        st, pvs = _req("GET", "/api/v1/ventas/puntos-venta", tok)
        st2, deps = _req("GET", "/api/v1/catalogos-articulos/depositos", tok)
        st3, caja = _req("POST", "/api/v1/pos/cajas", tok, {
            "nombre": "Caja Mostrador", "punto_venta_id": pvs[0]["id"],
            "deposito_id": deps[0]["id"], "lista_precios": 1, "ancho_ticket": 80,
            "perfil": "estandar"})
        check("caja mostrador de vitrina creada", st3 == 201, f"{st3} {caja}")
    st, arts = _req("GET", "/api/v1/articulos?limit=50", tok)
    art = next((a for a in arts
                if float(a["precio_1"]) > 0 and not a["venta_por_depto"] and a["activo"]
                and not a.get("pesable")), None)
    check("hay artículo con precio para el dry-run", art is not None, "")
    if art and caja:
        st, calc = _req("POST", "/api/v1/pos/ventas/calcular", tok, {
            "caja_id": caja["id"], "descuento_pct": "10",
            "items": [{"articulo_id": art["id"], "cantidad": "1", "descuento_pct": "10"}],
        })
        esperado = float(art["precio_1"]) * 0.81
        check("calcular POS con línea 10% + venta 10% -> total ≈ precio×0.81",
              st == 200 and abs(float(calc["total"]) - esperado) < 0.02,
              f"{st} {calc if st != 200 else calc.get('total')} vs {esperado}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
