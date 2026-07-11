r"""Suite en vivo del LOGIN POS DEDICADO (adelanto de F13-LAN) contra DEV.

Cubre: POST /pos/auth/login (200 con scope, 401 credenciales, 403 sin permiso
pos), el alcance del token de caja (módulo pos completo, solo-lectura de
ventas/clientes, 403 "sesión de caja" en el resto — nunca 401), el ciclo
completo de venta POS operado con un token de caja (sesión → venta → ticket)
y que el login funciona igual para un tenant plan `pos` (standalone).

El/los tenants de prueba se eliminan al final (DELETE por cascada, SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_pos_login_dev.py \
        --base http://127.0.0.1:8021
"""

import argparse
import asyncio
import json
import subprocess
import sys
import urllib.error as E
import urllib.request as U
import uuid
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


def setup_tenant(razon, email, clave, plan):
    return subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", plan, "--rubro", "general"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    razon = f"PosLogin {SUF}"
    razon_pos = f"PosLoginKiosco {SUF}"
    email = f"poslogin.{SUF}@zgc.dev"
    email_pos = f"kiosco.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 0. tenants efímeros (suite y plan pos) =====
    r = setup_tenant(razon, email, clave, "suite")
    check("setup_tenant suite OK", r.returncode == 0, r.stdout + r.stderr)
    r = setup_tenant(razon_pos, email_pos, clave, "pos")
    check("setup_tenant plan pos OK", r.returncode == 0, r.stdout + r.stderr)

    # ===== 1. login POS: contratos =====
    st, _ = _req("POST", base, "/pos/auth/login", body={"email": email, "password": "mala"})
    check("credenciales malas -> 401", st == 401, f"{st}")

    st, pl = _req("POST", base, "/pos/auth/login", body={"email": email, "password": clave})
    check("login POS -> 200 con scope pos", st == 200 and pl.get("scope") == "pos", f"{st} {pl}")
    if st != 200:
        sys.exit(1)
    tok_pos = pl["access_token"]
    check("permisos recortados a la superficie POS",
          "pos" in pl["permisos"] and "compras" not in pl["permisos"]
          and pl["permisos"].get("ventas", "ver") == "ver"
          and pl["permisos"].get("clientes", "ver") == "ver", f"{pl['permisos']}")

    st, login = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    tok_suite = login["access_token"]
    check("login de la suite sigue sin scope", "scope" not in login, f"{login.keys()}")

    # ===== 2. alcance del token de caja =====
    st, _ = _req("GET", base, "/pos/cajas", tok_pos)
    check("token caja: GET /pos/cajas -> 200", st == 200, f"{st}")
    st, _ = _req("GET", base, "/ventas/comprobantes", tok_pos)
    check("token caja: GET ventas (apoyo, ver) -> 200", st == 200, f"{st}")
    st, _ = _req("GET", base, "/clientes?q=", tok_pos)
    check("token caja: GET clientes (apoyo, ver) -> 200", st == 200, f"{st}")
    st, det = _req("GET", base, "/compras/comprobantes", tok_pos)
    check("token caja: compras -> 403 'sesión de caja' (nunca 401)",
          st == 403 and "caja" in str(det).lower(), f"{st} {det}")
    st, det = _req("POST", base, "/articulos", tok_pos, {"codigo": "X", "descripcion": "X"})
    check("token caja: POST articulos -> 403", st == 403, f"{st} {det}")
    st, det = _req("POST", base, "/cobranzas/recibos", tok_pos, {})
    check("token caja: escribir en ventas/cobranzas -> 403 (apoyo es solo-lectura)",
          st == 403, f"{st} {det}")
    st, _ = _req("GET", base, "/contabilidad/plan", tok_pos)
    check("token caja: contabilidad -> 403", st == 403, f"{st}")

    # ===== 3. ciclo de caja completo con token POS =====
    st, art = _req("POST", base, "/articulos", tok_suite, {
        "codigo": f"PL{SUF}", "descripcion": f"Artículo PL {SUF}",
        "tasa_iva": 21, "precio_1": 500,
    })
    check("alta artículo (con token suite) -> 201", st == 201, f"{st}")
    st, cajas = _req("GET", base, "/pos/cajas", tok_pos)
    caja_id = cajas[0]["id"]
    st, res = _req("GET", base, f"/pos/buscar?q=PL{SUF}&caja_id={caja_id}", tok_pos)
    check("token caja: /pos/buscar -> 200 con match", st == 200 and len(res) == 1, f"{st} {res}")
    st, sesion = _req("POST", base, "/pos/sesiones", tok_pos,
                      {"caja_id": caja_id, "fondo_inicial": "100"})
    check("token caja: abrir sesión -> 201", st == 201, f"{st} {sesion}")
    st, venta = _req("POST", base, "/pos/ventas", tok_pos, {
        "sesion_id": sesion["id"],
        "items": [{"articulo_id": art["id"], "cantidad": "1"}],
        "medios": [{"medio": "efectivo", "importe": "500.00"}],
    })
    check("token caja: venta POS emitida -> 201", st == 201, f"{st} {venta}")
    if st == 201:
        st, _ = _req("GET", base, f"/ventas/comprobantes/{venta['id']}/impresion", tok_pos)
        check("token caja: payload de impresión -> 200", st == 200, f"{st}")
    _req("POST", base, f"/pos/sesiones/{sesion['id']}/cerrar", tok_pos,
         {"efectivo_contado": None})

    # ===== 4. usuario sin permiso pos -> 403 en el login POS =====
    st, roles = _req("GET", base, "/roles", tok_suite)
    rol_vendedor = next(r["id"] for r in roles if r["codigo"] == "vendedor")
    st, usr = _req("POST", base, "/usuarios", tok_suite, {
        "email": f"vend.{SUF}@zgc.dev", "nombre": "Vendedor Sin POS",
        "password": f"clave-{SUF}", "rol_id": rol_vendedor,
    })
    check("alta usuario rol vendedor -> 201", st in (200, 201), f"{st} {usr}")
    st, det = _req("POST", base, "/pos/auth/login",
                   body={"email": f"vend.{SUF}@zgc.dev", "password": f"clave-{SUF}"})
    check("login POS sin permiso pos -> 403 (nunca 401)", st == 403, f"{st} {det}")
    st, _ = _req("POST", base, "/auth/login",
                 body={"email": f"vend.{SUF}@zgc.dev", "password": f"clave-{SUF}"})
    check("el mismo usuario entra a la suite -> 200", st == 200, f"{st}")

    # ===== 5. tenant plan pos (kiosco standalone) =====
    st, pl2 = _req("POST", base, "/pos/auth/login",
                   body={"email": email_pos, "password": clave})
    check("login POS en tenant plan pos -> 200", st == 200 and pl2.get("scope") == "pos",
          f"{st} {pl2}")
    if st == 200:
        st, _ = _req("GET", base, "/pos/cajas", pl2["access_token"])
        check("token caja del kiosco: /pos/cajas -> 200", st == 200, f"{st}")

    # ===== cleanup =====
    async def _cleanup():
        from sqlalchemy import text as _text

        from app.core.db import SessionLocal

        async with SessionLocal() as db:
            await db.execute(
                _text("delete from tenants where razon_social in (:r1, :r2)"),
                {"r1": razon, "r2": razon_pos},
            )
            await db.commit()

    try:
        asyncio.run(_cleanup())
        print(f"  --  cleanup: tenants '{razon}' y '{razon_pos}' eliminados")
    except Exception as ex:  # noqa: BLE001
        print(f"  !!  cleanup falló (borrar a mano): {ex}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
