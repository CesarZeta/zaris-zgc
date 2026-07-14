r"""Suite en vivo de F18 (Backup por tenant + observabilidad) contra DEV.

Cubre: descarga del ZIP de backup (estructura, LEEME, manifest), guarda de
COMPLETITUD contra el metadata (toda tabla con tenant_id está en el ZIP o en
TABLAS_EXCLUIDAS — una tabla futura no puede quedar afuera en silencio),
exclusiones de seguridad (sin password_hash / cert_pem / key_pem / token_hash,
sin arca_tokens / password_resets / padron_cache), aislamiento de tenant
(exactamente las filas propias), auditoría de la descarga
(`backup_descargado`), RBAC (403 nunca 401) y /health/db.

El tenant de prueba se elimina al final (DELETE por cascada vía SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_f18_dev.py \
        --base http://127.0.0.1:8021
"""

import argparse
import asyncio
import io
import json
import subprocess
import sys
import urllib.error as E
import urllib.request as U
import uuid
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]


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


def _csv(zf: zipfile.ZipFile, nombre: str) -> tuple[list[str], list[list[str]]]:
    """Parsea un CSV del ZIP (BOM UTF-8, `;`, CRLF) -> (encabezado, filas).
    Suficiente para las aserciones (los valores de la suite no traen `;`)."""
    lineas = zf.read(nombre).decode("utf-8-sig").split("\r\n")
    filas = [ln.split(";") for ln in lineas if ln]
    return filas[0], filas[1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    raiz = args.base.rstrip("/")
    base = raiz + "/api/v1"

    razon = f"Backup F18 {SUF}"
    email = f"backup.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 1. tenant efímero =====
    print("--- 1. setup")
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave, "--plan", "suite"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    check("setup_tenant.py corre OK", r.returncode == 0, r.stdout + r.stderr)

    st, login, _ = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    check("login -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    # ===== 2. descarga del ZIP =====
    print("--- 2. backup ZIP")
    st, contenido, hdrs = _req("GET", base, "/backup/export.zip", tok)
    check("GET /backup/export.zip -> 200 zip",
          st == 200 and "zip" in hdrs.get("Content-Type", ""), f"{st}")
    zf = zipfile.ZipFile(io.BytesIO(contenido))
    nombres = set(zf.namelist())
    check("LEEME.txt y manifest.csv presentes",
          "LEEME.txt" in nombres and "manifest.csv" in nombres, f"{sorted(nombres)[:5]}")
    check("tenants.csv presente (fila propia, caso especial)", "tenants.csv" in nombres)
    leeme = zf.read("LEEME.txt").decode("utf-8")
    check("LEEME explica formato y exclusiones",
          "Excel" in leeme and "Contraseñas" in leeme)

    # ===== 3. guarda de COMPLETITUD contra el metadata =====
    print("--- 3. completitud")
    from app.models import Base  # noqa: E402 (in-process, mismo criterio que el cleanup)
    from app.services.backup import COLUMNAS_EXCLUIDAS, TABLAS_EXCLUIDAS  # noqa: E402

    tablas_tenant = {
        t.name for t in Base.metadata.tables.values() if "tenant_id" in t.columns
    }
    en_zip = {n[:-4] for n in nombres if n.endswith(".csv") and n != "manifest.csv"}
    faltantes = tablas_tenant - en_zip - set(TABLAS_EXCLUIDAS)
    check("toda tabla con tenant_id está en el ZIP o excluida EXPLÍCITAMENTE",
          not faltantes, f"faltan: {faltantes}")
    filtradas = en_zip & set(TABLAS_EXCLUIDAS)
    check("ninguna tabla excluida se coló al ZIP", not filtradas, f"{filtradas}")
    muertas = set(TABLAS_EXCLUIDAS) - tablas_tenant
    check("TABLAS_EXCLUIDAS solo lista tablas reales del tenant", not muertas, f"{muertas}")

    # ===== 4. exclusiones de seguridad + aislamiento =====
    print("--- 4. seguridad y aislamiento")
    enc_u, filas_u = _csv(zf, "usuarios.csv")
    check("usuarios.csv SIN password_hash", "password_hash" not in enc_u, f"{enc_u}")
    check("usuarios.csv = exactamente el usuario propio (aislamiento)",
          len(filas_u) == 1 and any(email in c for c in filas_u[0]),
          f"{len(filas_u)} filas")
    enc_a, filas_a = _csv(zf, "arca_config.csv")
    check("arca_config.csv SIN cert_pem/key_pem",
          "cert_pem" not in enc_a and "key_pem" not in enc_a, f"{enc_a}")
    check("arca_config.csv con la fila del tenant (modo simulado)",
          len(filas_a) == 1 and "simulado" in filas_a[0], f"{filas_a}")
    enc_n, _ = _csv(zf, "sucursal_nodos.csv")
    check("sucursal_nodos.csv SIN token_hash", "token_hash" not in enc_n, f"{enc_n}")
    enc_t, filas_t = _csv(zf, "tenants.csv")
    check("tenants.csv = solo la fila propia",
          len(filas_t) == 1 and any(razon in c for c in filas_t[0]), f"{len(filas_t)}")
    check("COLUMNAS_EXCLUIDAS referencia columnas reales",
          all(
              col in Base.metadata.tables[tabla].columns
              for tabla, col in COLUMNAS_EXCLUIDAS
          ))

    # tablas sembradas por setup_tenant con datos
    manifest_enc, manifest_filas = _csv(zf, "manifest.csv")
    conteos = {f[0]: (int(f[1]), f[2]) for f in manifest_filas}
    for tabla in ("usuarios", "roles", "rol_permisos", "depositos", "puntos_venta",
                  "pos_cajas", "arca_config", "sucursales", "tenants"):
        n, trunc = conteos.get(tabla, (0, "?"))
        check(f"manifest: {tabla} con filas>0 sin truncar", n > 0 and trunc == "No",
              f"{n} {trunc}")
    check("manifest cubre todas las tablas del ZIP",
          set(conteos) == en_zip, f"{set(conteos) ^ en_zip}")

    # ===== 5. auditoría de la descarga =====
    print("--- 5. auditoría")
    st, evs, hdrs = _req("GET", base, "/auditoria/eventos?accion=backup_descargado", tok)
    total = int(hdrs.get("X-Total-Count") or -1)
    d = (evs[0].get("detalle") or {}) if evs else {}
    check("backup_descargado registrado con conteos",
          st == 200 and total == 1 and d.get("tablas", 0) > 50 and d.get("filas_total", 0) > 0,
          f"{st} {total} {d}")

    # ===== 6. RBAC =====
    print("--- 6. RBAC")
    st, roles, _ = _req("GET", base, "/roles", tok)
    vendedor = next((x for x in roles if x["codigo"] == "vendedor"), None)
    user_email = f"backup-user-{SUF}@zgc.dev"
    st, _, _ = _req("POST", base, "/usuarios", tok, body={
        "email": user_email, "nombre": f"Prueba F18 {SUF}",
        "password": "Original6", "rol_id": vendedor["id"],
    })
    check("alta usuario vendedor -> 201", st == 201, f"{st}")
    st, login_v, _ = _req("POST", base, "/auth/login",
                          body={"email": user_email, "password": "Original6"})
    tok_vend = login_v["access_token"] if st == 200 else None
    st, r_, _ = _req("GET", base, "/backup/export.zip", tok_vend)
    check("rol vendedor -> 403 (nunca 401)", st == 403, f"{st} {r_}")
    st, _, _ = _req("GET", base, "/backup/export.zip", None)
    check("sin token -> 401", st == 401, f"{st}")

    # ===== 7. health/db =====
    print("--- 7. observabilidad")
    st, salud, _ = _req("GET", raiz, "/health/db")
    check("/health/db -> 200 con latencia numérica",
          st == 200 and salud.get("db") == "ok"
          and isinstance(salud.get("latencia_ms"), (int, float)),
          f"{st} {salud}")
    st, openapi, _ = _req("GET", raiz, "/openapi.json")
    check("openapi expone /backup/export.zip",
          st == 200 and "/api/v1/backup/export.zip" in (openapi or {}).get("paths", {}),
          f"{st}")

    # ===== cleanup =====
    async def _cleanup():
        from sqlalchemy import text as _text

        from app.core.db import SessionLocal

        async with SessionLocal() as db:
            await db.execute(
                _text("delete from tenants where razon_social = :r"), {"r": razon}
            )
            await db.commit()

    try:
        asyncio.run(_cleanup())
        print(f"  --  cleanup: tenant '{razon}' eliminado")
    except Exception as ex:  # noqa: BLE001
        print(f"  !!  cleanup falló (borrar a mano): {ex}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
