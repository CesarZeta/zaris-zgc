r"""Smoke F12-a (POS standalone: plan por tenant) contra PROD (Vercel + Supabase).

No crea tenants por DB (eso exige .env.prod): valida sobre los tenants existentes
que la migración 018 + el backend nuevo están vivos y que el plan `suite` no cambió
nada (todos los tenants de prod quedaron `suite`):

  1. /openapi.json expone `plan` en EmpresaOut (probe de deploy del backend).
  2. Login del tenant demo -> 200 con los 13 módulos en `permisos` (suite intacta).
  3. GET /empresa -> plan='suite'.
  4. GET /empresa/rubros -> incluye carniceria y restaurante (presets nuevos).
  5. GET /permisos/catalogo -> 13 módulos (catálogo completo en suite).
  6. GET /compras/comprobantes -> 200 (ningún módulo se recortó en suite).
  7. PUT /empresa/rubro carniceria y vuelta al original (CHECK 018 vivo en prod,
     ciclo neutro: deja el rubro como estaba).

La verificación del plan `pos` punta a punta quedó cubierta en dev (36/36 con
tenant efímero); en prod se activará al vender la primera licencia con
tools/setup_tenant.py + .env.prod temporal.

Uso:
    python tools/smoke_f12a_prod.py --base https://zaris-zgc-api.vercel.app \
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
    raiz = args.base.rstrip("/")
    base = raiz + "/api/v1"

    # 1. probe de deploy: el schema nuevo está en el openapi (público, sin token)
    st, spec = _req("GET", raiz, "/openapi.json")
    empresa_props = (
        spec.get("components", {}).get("schemas", {}).get("EmpresaOut", {}).get("properties", {})
        if st == 200 else {}
    )
    check("openapi expone EmpresaOut.plan (backend nuevo servido)", "plan" in empresa_props, f"{st}")

    # 2. login demo (suite)
    st, login = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    check("login demo -> 200", st == 200, f"{st} {login}")
    if st != 200:
        print("\nsin login no hay smoke — abortando")
        sys.exit(1)
    tok = login["access_token"]
    permisos = login.get("permisos", {})
    check("suite conserva los 13 módulos en permisos", len(permisos) == 13, f"{len(permisos)} {sorted(permisos)}")

    # 3. plan del tenant
    st, emp = _req("GET", base, "/empresa", tok)
    check("GET /empresa -> plan='suite'", st == 200 and emp.get("plan") == "suite", f"{st} {emp}")
    rubro_original = emp.get("rubro", "general")

    # 4. presets nuevos
    st, rubros = _req("GET", base, "/empresa/rubros", tok)
    codigos = {r["codigo"] for r in rubros} if st == 200 else set()
    check("rubros incluyen carniceria y restaurante", {"carniceria", "restaurante"} <= codigos,
          f"{st} {sorted(codigos)}")

    # 5. catálogo de permisos completo en suite
    st, cat = _req("GET", base, "/permisos/catalogo", tok)
    check("catálogo de permisos completo (13 módulos)",
          st == 200 and len(cat.get("modulos", [])) == 13, f"{st}")

    # 6. módulos de gestión intactos
    st, _ = _req("GET", base, "/compras/comprobantes", tok)
    check("GET /compras/comprobantes -> 200 (suite sin recortes)", st == 200, f"{st}")
    st, _ = _req("GET", base, "/bancos/cuentas", tok)
    check("GET /bancos/cuentas -> 200", st == 200, f"{st}")

    # 7. CHECK 018 vivo: rubro carniceria acepta y ciclo neutro
    st, _ = _req("PUT", base, "/empresa/rubro", tok, {"rubro": "carniceria"})
    check("PUT rubro carniceria -> 200 (CHECK 018 en prod)", st == 200, f"{st}")
    st, emp2 = _req("PUT", base, "/empresa/rubro", tok, {"rubro": rubro_original})
    check(f"rubro restaurado a '{rubro_original}' (ciclo neutro)",
          st == 200 and emp2.get("rubro") == rubro_original, f"{st} {emp2}")

    print(f"\n===== SMOKE F12-A PROD: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
