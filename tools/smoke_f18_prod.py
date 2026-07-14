"""Smoke E2E de F18 (Backup + observabilidad) contra PRODUCCIÓN.

NEUTRO sobre el tenant demo: descarga el backup (solo lectura; el único
registro que deja es el evento `backup_descargado` — evidencia real y
deseada) y pega a /health/db. Verifica que el backend nuevo esté vivo:
ruta en openapi, ZIP bien formado sin secretos, auditoría de la descarga,
RBAC (401 sin token) y el health que toca la DB.

Uso:
    python tools/smoke_f18_prod.py --base https://zaris-zgc-api.vercel.app \
        --email demo@zaris.com.ar --clave "..."
"""

import argparse
import io
import json
import sys
import urllib.error as E
import urllib.request as U
import zipfile

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
    raiz = args.base.rstrip("/")
    base = raiz + "/api/v1"

    st, spec, _ = _req("GET", raiz, "/openapi.json")
    check("openapi expone /backup/export.zip",
          st == 200 and "/api/v1/backup/export.zip" in json.dumps(spec), f"{st}")

    st, salud, _ = _req("GET", raiz, "/health/db")
    check("/health/db -> 200 db ok con latencia",
          st == 200 and isinstance(salud, dict) and salud.get("db") == "ok"
          and isinstance(salud.get("latencia_ms"), (int, float)), f"{st} {salud}")

    st, r, _ = _req("POST", base, "/auth/login",
                    body={"email": args.email, "password": args.clave})
    check("login demo -> 200", st == 200, f"{st}")
    if st != 200:
        sys.exit(1)
    tok = r["access_token"]

    st, contenido, hdrs = _req("GET", base, "/backup/export.zip", tok)
    check("GET /backup/export.zip -> 200 zip",
          st == 200 and "zip" in hdrs.get("Content-Type", ""), f"{st}")
    if st == 200:
        zf = zipfile.ZipFile(io.BytesIO(contenido))
        nombres = set(zf.namelist())
        check("ZIP con LEEME, manifest y tablas clave",
              {"LEEME.txt", "manifest.csv", "tenants.csv", "usuarios.csv",
               "articulos.csv", "comprobantes.csv"} <= nombres,
              f"{len(nombres)} archivos")
        encabezado = zf.read("usuarios.csv").decode("utf-8-sig").split("\r\n")[0]
        check("usuarios.csv SIN password_hash", "password_hash" not in encabezado)
        check("tablas excluidas ausentes",
              not ({"arca_tokens.csv", "password_resets.csv"} & nombres))
        filas = [ln for ln in zf.read("manifest.csv").decode("utf-8-sig").split("\r\n") if ln]
        check("manifest con 70+ tablas y sin truncados",
              len(filas) > 70 and all(f.rsplit(";", 1)[-1] != "Sí" for f in filas[1:]),
              f"{len(filas)}")

    st, evs, hdrs = _req("GET", base,
                         "/auditoria/eventos?accion=backup_descargado&limit=1", tok)
    total = int(hdrs.get("X-Total-Count") or 0)
    check("backup_descargado auditado (la descarga de este smoke)",
          st == 200 and total >= 1 and (evs[0].get("detalle") or {}).get("tablas", 0) > 50,
          f"{st} {total}")

    st, r_, _ = _req("GET", base, "/backup/export.zip", None)
    check("sin token -> 401", st == 401, f"{st}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
