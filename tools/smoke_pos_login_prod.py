r"""Smoke del LOGIN POS DEDICADO contra PROD (neutro: solo login y lecturas
sobre el tenant demo — no crea nada).

Uso:
    python tools/smoke_pos_login_prod.py --email demo@zaris.com.ar --clave ...
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://zaris-zgc-api.vercel.app"
ok = 0
fail = 0


def _req(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=120)
        payload = r.read()
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
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()

    st, spec = _req("GET", "/openapi.json")
    check("openapi expone /pos/auth/login",
          st == 200 and "/api/v1/pos/auth/login" in json.dumps(spec), f"{st}")

    st, _ = _req("POST", "/api/v1/pos/auth/login",
                 body={"email": args.email, "password": "clave-mala"})
    check("credenciales malas -> 401", st == 401, f"{st}")

    st, pl = _req("POST", "/api/v1/pos/auth/login",
                  body={"email": args.email, "password": args.clave})
    check("login POS -> 200 con scope pos", st == 200 and pl.get("scope") == "pos",
          f"{st} {pl}")
    if st != 200:
        sys.exit(1)
    tok = pl["access_token"]
    check("permisos recortados (sin compras/config)",
          "pos" in pl["permisos"] and "compras" not in pl["permisos"]
          and "configuracion" not in pl["permisos"], f"{pl['permisos']}")

    st, cajas = _req("GET", "/api/v1/pos/cajas", tok)
    check("token caja: GET /pos/cajas -> 200", st == 200, f"{st}")
    st, _ = _req("GET", "/api/v1/ventas/comprobantes?limit=1", tok)
    check("token caja: ventas ver -> 200", st == 200, f"{st}")
    st, det = _req("GET", "/api/v1/compras/comprobantes?limit=1", tok)
    check("token caja: compras -> 403 (nunca 401)", st == 403, f"{st} {det}")
    st, det = _req("GET", "/api/v1/contabilidad/plan", tok)
    check("token caja: contabilidad -> 403", st == 403, f"{st} {det}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
