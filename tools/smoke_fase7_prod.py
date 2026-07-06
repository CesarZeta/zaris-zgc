"""Smoke E2E de la Fase 7 contra PROD (Vercel) — se corre DESPUÉS del deploy.

Uso:
    python tools/smoke_fase7_prod.py --email <admin> --clave <clave>

Pega contra https://zaris-zgc-api.vercel.app (SIN proxy, así se ven CORS/headers
reales). Verifica que los endpoints nuevos de F7 existan y respondan coherente en
prod. NO valida OSM real (depende de red externa a Nominatim) más allá de que el
proxy responda 200 o 502. Todo recurso nombrado lleva sufijo único de la corrida;
la sucursal creada se DESACTIVA al final (no hay DELETE de sucursales por diseño).
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid

BASE = "https://zaris-zgc-api.vercel.app/api/v1"
SUF = uuid.uuid4().hex[:8]
ok = 0
fail = 0


def _req(method, path, token=None, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=40)
        payload = r.read()
        return r.status, (payload if raw else (json.loads(payload) if payload else None)), dict(r.headers)
    except E.HTTPError as ex:
        payload = ex.read()
        try:
            return ex.code, json.loads(payload), dict(ex.headers)
        except Exception:
            return ex.code, payload.decode(errors="replace"), dict(ex.headers)


def check(nombre, cond, detalle=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK  {nombre}")
    else:
        fail += 1
        print(f" FAIL {nombre}  {detalle}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()

    st, body, _ = _req("POST", "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print(f"login FALLÓ: {st} {body}")
        sys.exit(2)
    tok = body["access_token"]
    print(f"# login OK contra PROD — sufijo {SUF}")

    # --- migración 012 aplicada: entidades expone latitud ---
    print("\n[migración 012 en prod]")
    st, srch, _ = _req("GET", "/entidades/buscar?q=a&limit=1", tok)
    check("entidades/buscar 200", st == 200, f"{st} {srch}")
    check("EntidadOut trae campo latitud (012 aplicada)", st == 200 and (not srch or "latitud" in srch[0]))

    # --- ABM sucursales (endpoint nuevo) ---
    print("\n[ABM sucursales]")
    nombre = f"Smoke F7 {SUF}"
    st, suc, _ = _req("POST", "/sucursales", tok, {
        "nombre": nombre, "domicilio": "Test 100", "provincia_id": 1,
        "latitud": "-34.60", "longitud": "-58.38",
    })
    check("crear sucursal 201", st == 201, f"{st} {suc}")
    suc_id = suc["id"] if st == 201 else None
    check("sucursal trae lat/lon", st == 201 and suc.get("latitud") is not None)
    st, dup, _ = _req("POST", "/sucursales", tok, {"nombre": nombre})
    check("sucursal duplicada 409", st == 409, f"{st}")
    st, lst, _ = _req("GET", "/sucursales", tok)
    check("listar sucursales 200 + aparece la nueva", st == 200 and any(s["id"] == suc_id for s in lst))

    # --- dashboard KPIs ---
    print("\n[dashboard KPIs]")
    st, k, _ = _req("GET", "/dashboard/kpis", tok)
    check("kpis 200", st == 200, f"{st} {k}")
    check("kpis trae los 4 campos", st == 200 and all(
        c in k for c in ("ventas_mes", "cobros_pendientes", "stock_valorizado", "saldo_caja")))

    # --- padrón ARCA (guarda + validación; simulado si el tenant lo tiene) ---
    print("\n[padrón ARCA]")
    st, pad, _ = _req("GET", "/padron/30500010912", tok)
    check("padron responde 200 o 400 (no 500)", st in (200, 400), f"{st} {pad}")
    st, badp, _ = _req("GET", "/padron/12345678901", tok)
    check("CUIT con DV malo 422", st == 422, f"{st}")

    # --- geo proxy (200 real de OSM o 502 si Nominatim no responde) ---
    print("\n[geo proxy Nominatim]")
    st, g, _ = _req("GET", "/geo/buscar?q=Corrientes%20348%20CABA&limit=2&solo_direcciones=true", tok)
    check("geo/buscar 200 o 502", st in (200, 502), f"{st}")
    st, gc, _ = _req("GET", "/geo/buscar?q=ab", tok)
    check("geo q corto 422", st == 422, f"{st}")

    # --- export CSV (headers CORS reales: X-Total-Count/Content-Disposition) ---
    print("\n[export CSV]")
    st, csvv, hdrs = _req("GET", "/ventas/comprobantes/export.csv", tok, raw=True)
    check("export ventas.csv 200", st == 200, f"{st}")
    if st == 200:
        txt = csvv.decode("utf-8")
        check("ventas.csv con BOM + separador ;", txt.startswith("﻿") and ";" in txt.split("\r\n")[0])

    # --- cleanup: desactivar la sucursal de prueba (no hay DELETE por diseño) ---
    if suc_id:
        _req("PATCH", f"/sucursales/{suc_id}", tok, {"activa": False})
        print(f"\n# sucursal de prueba desactivada ({suc_id})")

    print(f"\n===== SMOKE PROD F7: {ok} OK, {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
