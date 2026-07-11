"""Smoke de la Fase 9 (Contabilidad) contra PROD, con el tenant DEMO.

Siembra el plan (lazy), regenera el mes corriente, verifica partida doble y
sumas y saldos balanceados, mayor y export CSV. Todo sobre el tenant demo:
los asientos derivados son regenerables (no ensucian nada).

Uso:
    python tools/smoke_f9_prod.py --email demo@zaris.com.ar --clave "..."
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
from datetime import date
from decimal import Decimal

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = 0
fail = 0


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
    ap.add_argument("--base", default="https://zaris-zgc-api.vercel.app")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"
    hoy = date.today()
    desde = hoy.replace(day=1).isoformat()

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    check("login", st == 200, f"{st}")
    if st != 200:
        sys.exit(1)
    tok = r["access_token"]

    st, plan = _req("GET", base, "/contabilidad/plan", tok)
    check("plan sembrado (migración 015 viva)", st == 200 and len(plan) >= 35,
          f"{st} n={len(plan) if isinstance(plan, list) else plan}")
    st, mapeos = _req("GET", base, "/contabilidad/mapeos", tok)
    check("mapeos default", st == 200 and len(mapeos) >= 35, f"{st}")

    st, gen = _req("POST", base, "/contabilidad/regenerar",
                   tok, {"desde": desde, "hasta": hoy.isoformat()})
    check("regenerar mes corriente", st == 200, f"{st} {gen}")
    print(f"      {gen.get('asientos')} asientos, {len(gen.get('warnings', []))} warnings")

    st, asientos = _req("GET", base, f"/contabilidad/asientos?desde={desde}&hasta={hoy}&limit=200", tok)
    check("diario responde", st == 200, f"{st}")
    desbal = [
        a for a in (asientos or [])
        if sum(Decimal(l["debe"]) for l in a["lineas"]) != sum(Decimal(l["haber"]) for l in a["lineas"])
    ]
    check("todos los asientos balancean", not desbal, [a["descripcion"] for a in desbal][:3])

    st, sys_ = _req("GET", base, f"/contabilidad/sumas-y-saldos?desde={desde}&hasta={hoy}", tok)
    check("sumas y saldos balancea", st == 200 and sys_["balanceado"] is True,
          f"{st} {sys_.get('total_debe')} vs {sys_.get('total_haber')}")

    if isinstance(plan, list):
        ventas = next((c for c in plan if c["codigo"] == "4.1.01"), None)
        if ventas:
            st, mayor = _req("GET", base, f"/contabilidad/mayor/{ventas['id']}?desde={desde}&hasta={hoy}", tok)
            check("mayor de Ventas responde", st == 200, f"{st}")

    st, csv_bytes = _req("GET", base, f"/contabilidad/diario.csv?desde={desde}&hasta={hoy}", tok)
    check("diario.csv responde", st == 200 and isinstance(csv_bytes, bytes), f"{st}")

    print(f"\n===== SMOKE PROD F9: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
