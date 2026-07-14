"""Smoke E2E de F17 (Auditoría de acciones) contra PRODUCCIÓN.

NEUTRO sobre el tenant demo: los únicos eventos que genera son de auth
(login ok/fallido) — evidencia real y deseada, no basura. Verifica que la
migración 027 + el backend nuevo estén vivos: rutas de consulta, catálogo,
filtros específicos, export CSV con BOM, RBAC (401 sin token) e inmutabilidad
(405 sobre PUT).

Uso:
    python tools/smoke_f17_prod.py --base https://zaris-zgc-api.vercel.app \
        --email demo@zaris.com.ar --clave "..."
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U

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
            return r.status, payload, r.headers
        return r.status, (json.loads(payload) if payload else None), r.headers
    except E.HTTPError as ex:
        payload = ex.read()
        try:
            return ex.code, json.loads(payload), ex.headers
        except Exception:
            return ex.code, payload.decode(errors="replace"), ex.headers


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

    st, spec, _ = _req("GET", args.base.rstrip("/") + "/openapi.json", None)
    check("openapi expone /auditoria/eventos",
          st == 200 and "/api/v1/auditoria/eventos" in json.dumps(spec), f"{st}")

    st, r, _ = _req("POST", base, "/auth/login",
                    body={"email": args.email, "password": "clave-INCORRECTA-smoke"})
    check("login fallido -> 401", st == 401, f"{st}")

    st, r, _ = _req("POST", base, "/auth/login",
                    body={"email": args.email, "password": args.clave})
    check("login demo -> 200", st == 200, f"{st}")
    if st != 200:
        sys.exit(1)
    tok = r["access_token"]

    st, cat, _ = _req("GET", base, "/auditoria/catalogo", tok)
    check("catálogo -> 200 con 20+ acciones",
          st == 200 and len(cat.get("acciones", [])) >= 20, f"{st}")

    st, evs, hdrs = _req("GET", base,
                         f"/auditoria/eventos?accion=login_ok&q={args.email}&limit=1", tok)
    total = int(hdrs.get("X-Total-Count") or 0)
    check("login_ok del smoke registrado (filtro específico)",
          st == 200 and total >= 1 and evs and evs[0]["usuario_email"] == args.email,
          f"{st} {total}")

    st, evs, hdrs = _req("GET", base,
                         f"/auditoria/eventos?accion=login_fallido&q={args.email}&limit=1", tok)
    total = int(hdrs.get("X-Total-Count") or 0)
    check("login_fallido COMITEADO pese al 401",
          st == 200 and total >= 1
          and (evs[0]["detalle"] or {}).get("motivo") == "clave", f"{st} {total}")

    st, r_, _ = _req("GET", base, "/auditoria/eventos?accion=no_existe", tok)
    check("acción desconocida -> 422", st == 422, f"{st}")

    st, csv, _ = _req("GET", base, "/auditoria/export.csv?accion=login_ok", tok)
    check("export CSV con BOM", st == 200 and isinstance(csv, bytes)
          and csv[:3] == b"\xef\xbb\xbf", f"{st}")

    st, r_, _ = _req("GET", base, "/auditoria/eventos", None)
    check("sin token -> 401", st == 401, f"{st}")

    st, r_, _ = _req("PUT", base, "/auditoria/eventos", tok, body={})
    check("PUT sobre eventos -> 405 (inmutable)", st == 405, f"{st}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
