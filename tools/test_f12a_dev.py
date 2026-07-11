r"""Suite en vivo de F12-a (POS standalone: plan por tenant) contra DEV.

Cubre: setup_tenant.py con --plan pos (tenant efímero de la corrida), login que
devuelve `permisos` recortado por el plan (rol NULL = acceso total DEL plan),
guardas 403 (nunca 401) con mensaje de plan en módulos excluidos, endpoints de
módulos incluidos vivos, `requiere_alguno` con catálogo compartido (entidades
pasa por clientes aunque proveedores esté fuera del plan), /permisos/catalogo
filtrado, plan∩rol para un usuario con rol, rubros nuevos carniceria/restaurante
(CHECK 018 + presets), GET /empresa con plan, y regresión del tenant suite
(demo: los 13 módulos siguen ahí y compras responde 200).

El tenant de prueba se elimina al final (DELETE por cascada vía SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_f12a_dev.py \
        --base http://127.0.0.1:8021 --demo-email demo@zaris.com.ar --demo-clave "..."
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

PLAN_POS_ESPERADO = {"pos", "articulos", "stock", "clientes", "ventas", "caja", "libros_iva", "configuracion"}
FUERA_DE_PLAN = {"proveedores", "compras", "vendedores", "bancos", "contabilidad"}


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
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    ap.add_argument("--demo-email", required=True)
    ap.add_argument("--demo-clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    razon = f"Kiosco F12a {SUF}"
    email = f"kiosco.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 1. setup_tenant.py --plan pos (herramienta de onboarding) =====
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", "pos", "--rubro", "general"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    check("setup_tenant.py --plan pos corre OK", r.returncode == 0, r.stdout + r.stderr)
    check("setup crea caja POS default", "Caja 1" in r.stdout, r.stdout)
    r2 = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", "pos", "--rubro", "general"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    check("setup_tenant.py es idempotente", r2.returncode == 0 and "[+] Tenant creado" not in r2.stdout,
          r2.stdout + r2.stderr)

    # ===== 2. login POS-only: permisos = intersección con el plan =====
    st, login = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    check("login tenant POS -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]
    permisos = login["permisos"]
    check("permisos del login = módulos del plan pos (rol NULL = todo el PLAN)",
          set(permisos) == PLAN_POS_ESPERADO, f"{sorted(permisos)}")
    check("nivel anular en los módulos del plan (rol NULL)",
          all(a == "anular" for a in permisos.values()), f"{permisos}")

    # ===== 3. módulos fuera del plan -> 403 con mensaje de plan (nunca 401) =====
    for path, nombre in [
        ("/compras/comprobantes", "compras"),
        ("/proveedores", "proveedores"),
        ("/bancos/cuentas", "bancos"),
        ("/contabilidad/plan", "contabilidad"),
        ("/vendedores", "vendedores"),
    ]:
        st, r = _req("GET", base, path, tok)
        detalle = (r or {}).get("detail", "") if isinstance(r, dict) else str(r)
        check(f"GET {path} -> 403 por plan", st == 403 and "plan" in detalle.lower(),
              f"{st} {detalle}")

    # ===== 4. módulos del plan -> vivos =====
    for path in ["/ventas/comprobantes", "/articulos?limit=1", "/clientes?limit=1",
                 "/pos/cajas", "/caja/conceptos", "/libros/iva-ventas?periodo=2026-07",
                 "/empresa", "/usuarios", "/roles"]:
        st, _ = _req("GET", base, path, tok)
        check(f"GET {path} -> 200 (en plan)", st == 200, f"{st}")

    # ===== 5. catálogo compartido (requiere_alguno): entidades pasa por clientes =====
    st, r = _req("GET", base, f"/clientes/zonas", tok)
    check("catálogo compartido (zonas) -> 200 aunque proveedores esté fuera", st == 200, f"{st}")

    # ===== 6. /permisos/catalogo filtrado por plan =====
    st, cat = _req("GET", base, "/permisos/catalogo", tok)
    codigos = {m["codigo"] for m in cat["modulos"]} if st == 200 else set()
    check("/permisos/catalogo -> solo módulos del plan", st == 200 and codigos == PLAN_POS_ESPERADO,
          f"{st} {sorted(codigos)}")

    # ===== 7. plan ∩ rol: usuario cajero en tenant POS =====
    st, roles = _req("GET", base, "/roles", tok)
    rol_cajero = next((r for r in roles if r["codigo"] == "cajero"), None)
    check("roles base sembrados en el tenant POS", rol_cajero is not None, f"{st}")
    st, u = _req("POST", base, "/usuarios", tok, {
        "email": f"cajero.{SUF}@zgc.dev", "nombre": f"Cajero {SUF}",
        "password": clave, "rol_id": rol_cajero["id"], "nivel_acceso": 3})
    check("alta usuario cajero -> 201", st in (200, 201), f"{st} {u}")
    st, login_c = _req("POST", base, "/auth/login", body={"email": f"cajero.{SUF}@zgc.dev", "password": clave})
    perm_c = login_c.get("permisos", {}) if st == 200 else {}
    # cajero tiene bancos=editar en el rol base, pero bancos NO está en el plan
    check("cajero POS: bancos recortado por plan aunque el rol lo tenga",
          st == 200 and "bancos" not in perm_c and perm_c.get("pos") == "editar",
          f"{st} {sorted(perm_c)}")
    st, _ = _req("GET", base, "/bancos/cuentas", login_c.get("access_token"))
    check("cajero POS: GET /bancos/cuentas -> 403", st == 403, f"{st}")

    # ===== 8. rubros nuevos (CHECK 018 + presets) =====
    st, rubros = _req("GET", base, "/empresa/rubros", tok)
    codigos_rubro = {r["codigo"] for r in rubros} if st == 200 else set()
    check("presets incluyen carniceria y restaurante",
          {"carniceria", "restaurante"} <= codigos_rubro, f"{sorted(codigos_rubro)}")
    carn = next((r for r in rubros if r["codigo"] == "carniceria"), {})
    check("carniceria trae flags_pos_super (pesables)", carn.get("flags_pos_super") is True, f"{carn}")
    st, emp = _req("PUT", base, "/empresa/rubro", tok, {"rubro": "carniceria"})
    check("PUT /empresa/rubro carniceria -> 200 (CHECK 018 en DB)", st == 200, f"{st} {emp}")
    st, emp = _req("PUT", base, "/empresa/rubro", tok, {"rubro": "restaurante"})
    check("PUT /empresa/rubro restaurante -> 200", st == 200, f"{st} {emp}")
    st, emp = _req("GET", base, "/empresa", tok)
    check("GET /empresa expone plan='pos'", st == 200 and emp.get("plan") == "pos", f"{st} {emp}")

    # ===== 9. regresión tenant SUITE (demo) =====
    st, login_d = _req("POST", base, "/auth/login",
                       body={"email": args.demo_email, "password": args.demo_clave})
    check("login demo (suite) -> 200", st == 200, f"{st}")
    if st == 200:
        tok_d = login_d["access_token"]
        perm_d = login_d["permisos"]
        check("suite conserva los 13 módulos", len(perm_d) == 13, f"{len(perm_d)} {sorted(perm_d)}")
        st, _ = _req("GET", base, "/compras/comprobantes", tok_d)
        check("suite: GET /compras/comprobantes -> 200", st == 200, f"{st}")
        st, emp_d = _req("GET", base, "/empresa", tok_d)
        check("suite: GET /empresa plan='suite'", st == 200 and emp_d.get("plan") == "suite",
              f"{st} {emp_d}")
        st, cat_d = _req("GET", base, "/permisos/catalogo", tok_d)
        check("suite: catálogo completo (13 módulos)",
              st == 200 and len(cat_d["modulos"]) == 13, f"{st}")

    # ===== 10. cleanup: borrar el tenant efímero (cascada) =====
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
