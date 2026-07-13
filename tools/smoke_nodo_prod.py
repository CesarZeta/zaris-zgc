r"""Smoke de F13-LAN N1 (nodo de sucursal) contra PROD — NEUTRO: solo lecturas
y negativos de auth sobre el tenant demo; no crea nodos ni toca datos.

Uso:
    python tools/smoke_nodo_prod.py --email demo@zaris.com.ar --clave ...
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid

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

    st, salud = _req("GET", "/health")
    check("health -> perfil nube", st == 200 and salud.get("perfil") == "nube",
          f"{st} {salud}")

    st, spec = _req("GET", "/openapi.json")
    texto = json.dumps(spec) if st == 200 else ""
    check("openapi expone /nodos", st == 200 and "/api/v1/nodos" in texto, f"{st}")
    check("openapi expone /sync/handshake", "/api/v1/sync/handshake" in texto)
    check("openapi expone /sync/bajada/{tabla}", "/api/v1/sync/bajada/{tabla}" in texto)
    check("openapi expone /sync/ping", "/api/v1/sync/ping" in texto)

    st, login = _req("POST", "/api/v1/auth/login",
                     body={"email": args.email, "password": args.clave})
    check("login demo -> 200", st == 200, f"{st}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    st, nodos = _req("GET", "/api/v1/nodos", tok)
    check("GET /nodos -> 200 lista", st == 200 and isinstance(nodos, list),
          f"{st} {nodos}")

    st, det = _req("POST", "/api/v1/sync/handshake",
                   body={"nodo_id": str(uuid.uuid4()), "token": "token-invalido-123"})
    check("handshake con nodo inexistente -> 401", st == 401, f"{st} {det}")

    st, det = _req("GET", "/api/v1/sync/bajada/articulos", tok)
    check("bajada con token de usuario -> 401 (scope nodo)", st == 401, f"{st} {det}")
    st, det = _req("GET", "/api/v1/sync/bajada/articulos")
    check("bajada sin token -> 401", st == 401, f"{st} {det}")

    st, _ = _req("GET", "/api/v1/ventas/comprobantes?limit=1", tok)
    check("regresión: listado de ventas -> 200", st == 200, f"{st}")
    st, _ = _req("GET", "/api/v1/pos/cajas", tok)
    check("regresión: cajas POS -> 200", st == 200, f"{st}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
