r"""Suite en vivo del NODO DE SUCURSAL (F13-LAN N1) contra DEV.

Orquesta DOS backends: la "nube" dev de siempre en :8021 (debe estar corriendo
con la migración 023 aplicada) y un NODO real en :8022 que esta suite levanta
con perfil `nodo` contra una base local propia (zgc_nodo_test, recreada por
psql en cada corrida y con TODAS las migraciones aplicadas).

Cubre el criterio de listo de N1 (DISENO-NODO-LAN.md §7): aparejamiento con
token de una sola vez, réplica de bajada (incremental + snapshot con poda +
semilla inicial), una caja de la LAN vendiendo contra el nodo con maestros
replicados, la facturación de gestión con el PV propio del nodo, la
exclusividad de PV en ambas puntas y la revocación.

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_nodo_dev.py \
        --base http://127.0.0.1:8021
"""

import argparse
import asyncio
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error as E
import urllib.parse as UP
import urllib.request as U
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]
PSQL = r"C:\Program Files\PostgreSQL\17\bin\psql.exe"
DB_NODO = "zgc_nodo_test"
NODO_PORT = 8022


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
    except Exception as ex:  # conexión rechazada, timeout
        return 0, str(ex)


def check(nombre, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok  {nombre}")
    else:
        fail += 1
        print(f" FAIL {nombre}  {extra}")


def leer_db_dev() -> dict:
    """Parsea DATABASE_URL de backend/.env.local (credencial local de dev)."""
    texto = (RAIZ / "backend" / ".env.local").read_text(encoding="utf-8")
    m = re.search(r"^DATABASE_URL=(.+)$", texto, re.MULTILINE)
    url = m.group(1).strip()
    p = UP.urlsplit(url.replace("postgresql+asyncpg", "postgresql"))
    return {
        "url": url,
        "user": UP.unquote(p.username or ""),
        "password": UP.unquote(p.password or ""),
        "host": p.hostname or "127.0.0.1",
        "port": str(p.port or 5432),
        "dbname": p.path.lstrip("/"),
    }


DEV = leer_db_dev()


def psql(dbname, sql=None, archivo=None):
    cmd = [PSQL, "-h", DEV["host"], "-p", DEV["port"], "-U", DEV["user"],
           "-d", dbname, "-v", "ON_ERROR_STOP=1", "-q", "-t", "-A"]
    if archivo:
        cmd += ["-f", str(archivo)]
    else:
        cmd += ["-c", sql]
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PGPASSWORD": DEV["password"]},
    )
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def psql_valor(dbname, sql):
    rc, out, err = psql(dbname, sql)
    if rc != 0:
        return None
    return out.splitlines()[0].strip() if out else ""


def setup_tenant(razon, email, clave):
    return subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", "suite", "--rubro", "general"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(RAIZ / "backend"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    nube = args.base.rstrip("/") + "/api/v1"
    nodo = f"http://127.0.0.1:{NODO_PORT}/api/v1"

    razon = f"NodoLan {SUF}"
    email = f"nodolan.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"
    env_nodo = RAIZ / "backend" / ".env.nodo"
    log_nodo = RAIZ / "backend" / "uvicorn_nodo_test.log"
    proc_nodo = None

    # ===== 0. base local del nodo: recrear + migraciones completas =====
    rc, _, err = psql("postgres", f'drop database if exists {DB_NODO} with (force)')
    check("drop db nodo previa", rc == 0, err)
    rc, _, err = psql("postgres", f"create database {DB_NODO}")
    check("create db nodo", rc == 0, err)
    migraciones = sorted((RAIZ / "sql").glob("0*.sql"))
    fallo_mig = ""
    for mig in migraciones:
        rc, _, err = psql(DB_NODO, archivo=mig)
        if rc != 0:
            fallo_mig = f"{mig.name}: {err}"
            break
    check(f"migraciones aplicadas al nodo ({len(migraciones)})", not fallo_mig, fallo_mig)

    # ===== 1. tenant efímero + maestros en la nube =====
    r = setup_tenant(razon, email, clave)
    check("setup_tenant OK", r.returncode == 0, r.stdout + r.stderr)
    st, login = _req("POST", nube, "/auth/login", body={"email": email, "password": clave})
    check("login admin nube -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]
    tenant_id = psql_valor(DEV["dbname"],
                           f"select id from tenants where razon_social='{razon}'")

    st, suc = _req("POST", nube, "/sucursales", tok, {"nombre": f"Sucursal LAN {SUF}"})
    check("alta sucursal del nodo -> 201", st == 201, f"{st} {suc}")
    st, pvs = _req("GET", nube, "/ventas/puntos-venta", tok)
    pv_nube = pvs[0]  # el del setup_tenant: sigue siendo de la nube
    st, pv_nodo = _req("POST", nube, "/ventas/puntos-venta", tok,
                       {"numero": 90, "descripcion": f"PV nodo {SUF}",
                        "sucursal_id": suc["id"]})
    check("alta PV propio del nodo -> 201", st == 201, f"{st} {pv_nodo}")
    st, pv_caja = _req("POST", nube, "/ventas/puntos-venta", tok,
                       {"numero": 91, "descripcion": f"PV caja LAN {SUF}",
                        "sucursal_id": suc["id"]})
    check("alta PV de la caja LAN -> 201", st == 201, f"{st} {pv_caja}")
    st, caja = _req("POST", nube, "/pos/cajas", tok,
                    {"nombre": f"Caja LAN {SUF}", "sucursal_id": suc["id"],
                     "punto_venta_id": pv_caja["id"]})
    check("alta caja POS de la sucursal -> 201", st in (200, 201), f"{st} {caja}")
    st, art = _req("POST", nube, "/articulos", tok, {
        "codigo": f"NL{SUF}", "descripcion": f"Artículo nodo {SUF}",
        "tasa_iva": 21, "precio_1": 500,
    })
    check("alta artículo -> 201", st == 201, f"{st} {art}")

    # ===== 2. aparejamiento =====
    st, det = _req("POST", nube, "/nodos", tok,
                   {"sucursal_id": suc["id"], "nombre": f"Nodo {SUF}",
                    "punto_venta_id": pv_caja["id"]})
    check("PV de una caja como PV propio -> 422", st == 422, f"{st} {det}")
    st, nodo_creado = _req("POST", nube, "/nodos", tok,
                           {"sucursal_id": suc["id"], "nombre": f"Nodo {SUF}",
                            "punto_venta_id": pv_nodo["id"]})
    check("alta nodo -> 201 con token una vez", st == 201 and "token" in nodo_creado,
          f"{st} {nodo_creado}")
    if st != 201:
        sys.exit(1)
    st, otra = _req("POST", nube, "/nodos", tok,
                    {"sucursal_id": suc["id"], "nombre": "Segundo"})
    check("segundo nodo en la misma sucursal -> 409", st == 409, f"{st} {otra}")
    st, lista = _req("GET", nube, "/nodos", tok)
    check("GET /nodos lista sin token", st == 200 and len(lista) == 1
          and "token" not in lista[0], f"{st} {lista}")
    st, det = _req("GET", nube, "/sync/bajada/articulos", tok)
    check("bajada con token de usuario -> 401 (scope nodo)", st == 401, f"{st} {det}")

    # ===== 3. levantar el nodo =====
    url_nodo_db = re.sub(r"/[^/]+$", f"/{DB_NODO}", DEV["url"])
    env_nodo.write_text(
        f"ENV=nodo-test\nPERFIL=nodo\nDATABASE_URL={url_nodo_db}\n"
        f"JWT_SECRET={secrets.token_hex(24)}\nNUBE_URL={args.base.rstrip('/')}\n"
        f"NODO_ID={nodo_creado['id']}\nNODO_TOKEN={nodo_creado['token']}\n"
        f"SYNC_INTERVALO_SEG=3600\nCORS_ORIGINS=http://localhost:5173\n",
        encoding="utf-8",
    )
    log_f = open(log_nodo, "w", encoding="utf-8")
    proc_nodo = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(NODO_PORT)],
        cwd=str(RAIZ / "backend"), stdout=log_f, stderr=subprocess.STDOUT,
        env={**os.environ, "ENV_FILE": ".env.nodo"},
    )
    salud = None
    for _ in range(40):
        st, salud = _req("GET", f"http://127.0.0.1:{NODO_PORT}", "/health")
        if st == 200:
            break
        time.sleep(1)
    check("nodo levanta con perfil nodo", st == 200 and salud.get("perfil") == "nodo",
          f"{st} {salud}")

    # primer ciclo de réplica: esperar a que el admin exista en el nodo
    tok_n = None
    for _ in range(30):
        st, login_n = _req("POST", nodo, "/auth/login",
                           body={"email": email, "password": clave})
        if st == 200:
            tok_n = login_n["access_token"]
            break
        time.sleep(2)
    check("réplica inicial: login del admin EN EL NODO -> 200", tok_n is not None,
          f"último status {st}")
    if tok_n is None:
        print((RAIZ / "backend" / "uvicorn_nodo_test.log").read_text(encoding="utf-8")[-3000:])
        sys.exit(1)

    # el login del admin llega a MITAD del primer ciclo (usuarios replica
    # temprano): esperar a que el ciclo entero termine antes de asertar
    estado = None
    for _ in range(30):
        st, estado = _req("GET", nodo, "/nodo/estado", tok_n)
        if st == 200 and estado.get("ultimo_ok"):
            break
        time.sleep(2)
    check("GET /nodo/estado -> ciclo completo con contexto", st == 200
          and estado.get("ultimo_ok") is not None
          and estado["contexto"]["punto_venta_id"] == pv_nodo["id"]
          and len(estado["checkpoints"]) >= 30, f"{st} {estado}")

    # ===== 4. réplica verificada contra la base local =====
    def n_nodo(sql):
        return psql_valor(DB_NODO, sql)

    check("artículo replicado con precio",
          n_nodo(f"select precio_1 from articulos where tenant_id='{tenant_id}'"
                 f" and codigo='NL{SUF}'") == "500.0000")
    check("roles base replicados (5)",
          n_nodo(f"select count(*) from roles where tenant_id='{tenant_id}'") == "5")
    check("rol_permisos replicados (>0)",
          int(n_nodo(f"select count(*) from rol_permisos where tenant_id='{tenant_id}'") or 0) > 0)
    check("cajas POS replicadas (2)",
          n_nodo(f"select count(*) from pos_cajas where tenant_id='{tenant_id}'") == "2")
    check("puntos de venta replicados (3)",
          n_nodo(f"select count(*) from puntos_venta where tenant_id='{tenant_id}'") == "3")
    check("arca_config replicada en modo simulado",
          n_nodo(f"select modo from arca_config where tenant_id='{tenant_id}'") == "simulado")

    # ===== 5. maestros de solo lectura en el nodo =====
    st, det = _req("POST", nodo, "/articulos", tok_n, {"codigo": "X", "descripcion": "X"})
    check("POST /articulos en el nodo -> 403 solo lectura", st == 403
          and "solo lectura" in str(det).lower(), f"{st} {det}")
    st, det = _req("PATCH", nodo, f"/ventas/puntos-venta/{pv_nodo['id']}", tok_n,
                   {"descripcion": "hack"})
    check("PATCH puntos-venta en el nodo -> 403", st == 403, f"{st} {det}")
    st, det = _req("GET", nodo, "/nodos", tok_n)
    check("routers de nube NO montados en el nodo (404)", st == 404, f"{st}")

    # ===== 6. la caja de la LAN vende contra el nodo =====
    st, pl = _req("POST", nodo, "/pos/auth/login", body={"email": email, "password": clave})
    check("login POS en el nodo -> 200 scope pos", st == 200 and pl.get("scope") == "pos",
          f"{st} {pl}")
    tok_caja = pl["access_token"]
    st, cajas_n = _req("GET", nodo, "/pos/cajas", tok_caja)
    caja_lan = next(c for c in cajas_n if c["id"] == caja["id"])
    st, sesion = _req("POST", nodo, "/pos/sesiones", tok_caja,
                      {"caja_id": caja_lan["id"], "fondo_inicial": "100"})
    check("abrir sesión en la caja LAN -> 201", st == 201, f"{st} {sesion}")
    st, venta = _req("POST", nodo, "/pos/ventas", tok_caja, {
        "sesion_id": sesion["id"],
        "items": [{"articulo_id": art["id"], "cantidad": "1"}],
        "medios": [{"medio": "efectivo", "importe": "500.00"}],
    })
    check("venta POS emitida EN EL NODO -> 201", st == 201, f"{st} {venta}")
    if st == 201:
        st, _ = _req("GET", nodo, f"/ventas/comprobantes/{venta['id']}/impresion", tok_caja)
        check("ticket imprimible en el nodo -> 200", st == 200, f"{st}")
    check("stock local del nodo descontado (-1)",
          n_nodo(f"select cantidad from articulo_stock where articulo_id='{art['id']}'")
          == "-1.000")
    check("el stock de la NUBE no se movió",
          psql_valor(DEV["dbname"],
                     f"select coalesce(sum(cantidad),0) from articulo_stock"
                     f" where articulo_id='{art['id']}'") in ("0", "0.000"))

    # ===== 7. facturación de gestión con el PV propio del nodo =====
    st, comp = _req("POST", nodo, "/ventas/comprobantes", tok_n, {
        "clase": "factura", "punto_venta_id": pv_nodo["id"],
        "items": [{"descripcion": "Servicio LAN", "cantidad": "1",
                   "precio_unitario": "1000"}],
    })
    check("borrador de gestión en el nodo -> 201", st == 201, f"{st} {comp}")
    st, emitido = _req("POST", nodo, f"/ventas/comprobantes/{comp['id']}/emitir", tok_n, {})
    check("emitir con PV propio del nodo -> numeración local 1",
          st == 200 and emitido["numero"] == 1, f"{st} {emitido}")
    # la numeración nace LAZY en la primera emisión: debe existir en el nodo
    # (que emitió) y NO en la nube (su PV es exclusivo del nodo)
    check("numeración del PV propio vive en el nodo",
          int(n_nodo(f"select count(*) from numeracion where punto_venta_id="
                     f"'{pv_nodo['id']}'") or 0) > 0)
    check("numeración del PV propio NO existe en la nube",
          psql_valor(DEV["dbname"],
                     f"select count(*) from numeracion where punto_venta_id="
                     f"'{pv_nodo['id']}'") == "0")
    st, comp2 = _req("POST", nodo, "/ventas/comprobantes", tok_n, {
        "clase": "factura", "punto_venta_id": pv_nube["id"],
        "items": [{"descripcion": "X", "cantidad": "1", "precio_unitario": "1"}],
    })
    st, det = _req("POST", nodo, f"/ventas/comprobantes/{comp2['id']}/emitir", tok_n, {})
    check("emitir en el nodo con PV de la NUBE -> 422", st == 422
          and "no pertenece" in str(det), f"{st} {det}")

    # ===== 8. exclusividad del PV en la nube =====
    def borrador_nube(pv_id):
        _, c = _req("POST", nube, "/ventas/comprobantes", tok, {
            "clase": "factura", "punto_venta_id": pv_id,
            "items": [{"descripcion": "X", "cantidad": "1", "precio_unitario": "1"}],
        })
        return c

    c = borrador_nube(pv_nodo["id"])
    st, det = _req("POST", nube, f"/ventas/comprobantes/{c['id']}/emitir", tok, {})
    check("nube: emitir con el PV propio del nodo -> 422", st == 422
          and "nodo" in str(det).lower(), f"{st} {det}")
    c = borrador_nube(pv_caja["id"])
    st, det = _req("POST", nube, f"/ventas/comprobantes/{c['id']}/emitir", tok, {})
    check("nube: emitir con el PV de la caja LAN -> 422", st == 422, f"{st} {det}")
    c = borrador_nube(pv_nube["id"])
    st, det = _req("POST", nube, f"/ventas/comprobantes/{c['id']}/emitir", tok, {})
    check("nube: emitir con su propio PV -> 200 (control)", st == 200, f"{st} {det}")

    # ===== 9. réplica continua: incremental, snapshot con poda, semilla =====
    st, _ = _req("PUT", nube, f"/articulos/{art['id']}", tok, {
        "codigo": f"NL{SUF}", "descripcion": f"Artículo nodo {SUF}",
        "tasa_iva": 21, "precio_1": 600,
    })
    check("nube: precio actualizado -> 200", st == 200, f"{st}")
    st, roles_n = _req("POST", nube, "/roles", tok, {"nombre": f"Rol Nodo {SUF}"})
    check("nube: rol nuevo -> 201", st == 201, f"{st}")
    rol_nuevo = next(r["id"] for r in roles_n if r["nombre"] == f"Rol Nodo {SUF}")

    st, resumen = _req("POST", nodo, "/nodo/sync-ahora", tok_n, {})
    check("sync-ahora -> ok", st == 200 and resumen.get("ok"), f"{st} {resumen}")
    check("incremental: precio nuevo llegó al nodo",
          n_nodo(f"select precio_1 from articulos where id='{art['id']}'") == "600.0000")
    check("snapshot: rol nuevo llegó al nodo",
          n_nodo(f"select count(*) from roles where id='{rol_nuevo}'") == "1")
    check("semilla inicial NO pisó el stock local del nodo",
          n_nodo(f"select cantidad from articulo_stock where articulo_id='{art['id']}'")
          == "-1.000")

    st, _ = _req("DELETE", nube, f"/roles/{rol_nuevo}", tok)
    check("nube: rol borrado (hard delete) -> 204", st == 204, f"{st}")
    st, _ = _req("POST", nodo, "/nodo/sync-ahora", tok_n, {})
    check("poda snapshot: el rol borrado desapareció del nodo",
          n_nodo(f"select count(*) from roles where id='{rol_nuevo}'") == "0")

    # ===== 10. revocación =====
    st, _ = _req("POST", nube, f"/nodos/{nodo_creado['id']}/revocar", tok, {})
    check("revocar nodo -> 200", st == 200, f"{st}")
    st, det = _req("POST", nodo, "/nodo/sync-ahora", tok_n, {})
    check("nodo revocado: sync -> 502 con detalle", st == 502
          and "revocado" in str(det).lower(), f"{st} {det}")
    c = borrador_nube(pv_nodo["id"])
    st, det = _req("POST", nube, f"/ventas/comprobantes/{c['id']}/emitir", tok, {})
    check("nube: el PV del nodo revocado emite de nuevo -> 200", st == 200, f"{st} {det}")

    # ===== cleanup =====
    if proc_nodo is not None:
        proc_nodo.kill()
        proc_nodo.wait(timeout=15)
    log_f.close()
    psql("postgres", f"drop database if exists {DB_NODO} with (force)")
    env_nodo.unlink(missing_ok=True)
    log_nodo.unlink(missing_ok=True)

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
        print(f"  --  cleanup: tenant '{razon}', base {DB_NODO} y .env.nodo eliminados")
    except Exception as ex:  # noqa: BLE001
        print(f"  !!  cleanup falló (borrar a mano): {ex}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
