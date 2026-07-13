"""Smoke F16 (Salida de documentos) contra PROD — conductual, SIN mutar datos.

Patrón post-N2: las rutas nuevas se apuntan con requests que mueren DESPUÉS de
la guarda en errores de negocio esperados (404/422) o son lecturas puras. El
único registro que deja es opcional (--con-envio) y va al tenant demo como
email simulado (evidencia inocua, ni un email real sale).

Uso:
    python tools/smoke_f16_prod.py --base https://zaris-zgc-api.vercel.app \
        --email demo@zaris.com.ar --clave <clave-demo>
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid

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
    ap.add_argument("--con-envio", action="store_true",
                    help="además, envía (simulado) un comprobante real del demo")
    args = ap.parse_args()
    raiz = args.base.rstrip("/")
    base = raiz + "/api/v1"

    # 1. probe openapi: las rutas nuevas están servidas
    st, spec = _req("GET", raiz, "/openapi.json")
    rutas = set((spec or {}).get("paths", {})) if st == 200 else set()
    check("openapi: /auth/recuperar", "/api/v1/auth/recuperar" in rutas)
    check("openapi: /auth/restablecer", "/api/v1/auth/restablecer" in rutas)
    check("openapi: /emails/envios", "/api/v1/emails/envios" in rutas)
    check("openapi: pdf + enviar",
          "/api/v1/ventas/comprobantes/{comp_id}/pdf" in rutas
          and "/api/v1/ventas/comprobantes/{comp_id}/enviar" in rutas)

    st, r = _req("POST", base, "/auth/login",
                 body={"email": args.email, "password": args.clave})
    check("login demo", st == 200, f"{st}")
    if st != 200:
        print("sin login no hay smoke — corto acá")
        sys.exit(1)
    tok = r["access_token"]

    # 2. PDF de un comprobante emitido real del demo (lectura pura)
    st, comps = _req("GET", base, "/ventas/comprobantes?limit=5", tok)
    emitido = next((c for c in (comps or []) if c.get("estado") == "emitido"), None)
    check("hay comprobante emitido en el demo", emitido is not None, f"{st}")
    if emitido:
        st, pdf = _req("GET", base, f"/ventas/comprobantes/{emitido['id']}/pdf", tok)
        check("PDF en prod → 200 %PDF",
              st == 200 and isinstance(pdf, bytes) and pdf[:5] == b"%PDF-",
              f"{st}")

    # 3. guardas vivas sin mutar: 404/422 esperados DESPUÉS de la guarda
    st, _ = _req("GET", base, f"/ventas/comprobantes/{uuid.uuid4()}/pdf", tok)
    check("PDF inexistente → 404 (guarda corrió limpia)", st == 404, f"{st}")
    st, r = _req("POST", base, "/auth/restablecer",
                 body={"token": "x" * 43, "password": "NuevaClave9"})
    check("restablecer token inválido → 422", st == 422, f"{st} {r}")
    st, r = _req("POST", base, "/auth/recuperar",
                 body={"email": f"no-existe-{uuid.uuid4().hex[:6]}@zgc.dev"})
    check("recuperar inexistente → 200 genérico (no crea nada)",
          st == 200 and r.get("detail"), f"{st} {r}")

    # 4. bandeja de salida responde (lectura pura)
    st, envios = _req("GET", base, "/emails/envios?limit=5", tok)
    check("bandeja de salida → 200", st == 200 and isinstance(envios, list), f"{st}")

    # 5. opcional: envío simulado real (deja UNA fila inocua en el demo)
    if args.con_envio and emitido:
        st, envio = _req("POST", base, f"/ventas/comprobantes/{emitido['id']}/enviar",
                         tok, body={"email": "smoke-f16@zgc.dev"})
        check("envío simulado en prod → 200 estado simulado",
              st == 200 and isinstance(envio, dict) and envio.get("estado") == "simulado",
              f"{st} {envio}")

    print(f"\nRESULTADO: {ok} ok, {fail} fail")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
