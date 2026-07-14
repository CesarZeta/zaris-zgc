r"""Suite en vivo de F17 (Auditoría de acciones) contra DEV.

Cubre: eventos de auth (login ok/fallido comiteado pese al 401, sin evento para
email inexistente, recuperación/restablecimiento de clave), usuarios y roles
(alta/edición con antes-después, matriz de permisos, borrado, reset admin),
config ARCA sin PEM en el detalle, puntos de venta, cambio masivo de precios
(dry-run NO audita), import Excel, nodos LAN (alta/token/revocación), períodos
contables, anulación POS con supervisor, consulta (filtros específicos,
X-Total-Count, catálogo, export CSV con BOM), RBAC (403 nunca 401),
inmutabilidad (sin rutas de escritura) y aislamiento de tenant.

El tenant de prueba se elimina al final (DELETE por cascada vía SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_f17_dev.py \
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
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]


def _req(method, base, path, token=None, body=None, raw=None, content_type=None):
    if raw is not None:
        data = raw
    else:
        data = json.dumps(body).encode() if body is not None else None
    req = U.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", content_type or "application/json")
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
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    razon = f"Audit F17 {SUF}"
    email = f"audit.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 1. tenant efímero =====
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

    def eventos(filtros, token=tok):
        st, evs, hdrs = _req("GET", base, f"/auditoria/eventos?{filtros}", token)
        total = int(hdrs.get("X-Total-Count") or -1) if hdrs else -1
        return st, (evs if isinstance(evs, list) else []), total

    # ===== 2. auth: login_ok / login_fallido =====
    print("--- 2. eventos de auth")
    st, evs, total = eventos(f"accion=login_ok&q={email}")
    check("login_ok registrado con email sellado",
          st == 200 and total == 1 and evs[0]["usuario_email"] == email, f"{st} {total} {evs}")
    check("login_ok con IP y origen suite",
          evs and evs[0]["ip"] and (evs[0]["detalle"] or {}).get("origen") == "suite",
          f"{evs}")

    st, _, _ = _req("POST", base, "/auth/login", body={"email": email, "password": "MALA-clave"})
    check("login con clave mala -> 401", st == 401, f"{st}")
    st, evs, total = eventos(f"accion=login_fallido&q={email}")
    check("login_fallido COMITEADO pese al 401 (motivo clave)",
          st == 200 and total == 1 and (evs[0]["detalle"] or {}).get("motivo") == "clave",
          f"{st} {total} {evs}")

    fantasma = f"no-existe-{SUF}@zgc.dev"
    st, _, _ = _req("POST", base, "/auth/login", body={"email": fantasma, "password": "x" * 8})
    check("login email inexistente -> 401", st == 401, f"{st}")
    st, evs, total = eventos(f"q={fantasma}")
    check("email inexistente NO deja evento (sin tenant que lo vea)",
          st == 200 and total == 0, f"{st} {total} {evs}")

    st, _, _ = _req("POST", base, "/pos/auth/login", body={"email": email, "password": clave})
    check("login POS -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=login_ok&q={email}")
    check("login POS registrado con origen pos",
          st == 200 and total == 2
          and any((e["detalle"] or {}).get("origen") == "pos" for e in evs),
          f"{st} {total}")

    # ===== 3. roles: alta / matriz / edición / borrado =====
    print("--- 3. roles y matriz de permisos")
    st, roles, _ = _req("GET", base, "/roles", tok)
    vendedor = next((x for x in roles if x["codigo"] == "vendedor"), None)
    check("roles base sembrados", st == 200 and vendedor is not None, f"{st}")

    st, roles, _ = _req("POST", base, "/roles", tok, body={
        "nombre": f"Deposito {SUF}", "clonar_de": vendedor["id"],
    })
    check("crear rol propio -> 201", st == 201, f"{st}")
    rol = next((x for x in roles if x["nombre"] == f"Deposito {SUF}"), None)
    st, evs, total = eventos(f"accion=rol_alta&ref_id={rol['id']}")
    check("rol_alta con ref al rol y clon en el detalle",
          st == 200 and total == 1 and (evs[0]["detalle"] or {}).get("clonado_de") == vendedor["id"],
          f"{st} {total} {evs}")

    st, _, _ = _req("PUT", base, f"/roles/{rol['id']}/permisos", tok, body={
        "permisos": {"stock": "editar", "articulos": "ver"},
    })
    check("guardar matriz -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=rol_permisos&ref_id={rol['id']}")
    d = (evs[0]["detalle"] or {}) if evs else {}
    check("rol_permisos con matriz antes/después",
          st == 200 and total == 1 and d.get("despues", {}).get("stock") == "editar"
          and "antes" in d, f"{st} {total} {d}")

    st, _, _ = _req("PUT", base, f"/roles/{rol['id']}", tok, body={"nombre": f"Deposito v2 {SUF}"})
    check("renombrar rol -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=rol_edicion&ref_id={rol['id']}")
    check("rol_edicion con antes/después del nombre",
          st == 200 and total == 1
          and (evs[0]["detalle"] or {}).get("nombre", {}).get("antes") == f"Deposito {SUF}",
          f"{st} {total} {evs}")

    # ===== 4. usuarios: alta / edición / reset =====
    print("--- 4. usuarios")
    user_email = f"audit-user-{SUF}@zgc.dev"
    st, nuevo, _ = _req("POST", base, "/usuarios", tok, body={
        "email": user_email, "nombre": f"Prueba F17 {SUF}",
        "password": "Original6", "rol_id": vendedor["id"],
    })
    check("alta usuario -> 201", st == 201, f"{st} {nuevo}")
    user_id = nuevo["id"]
    st, evs, total = eventos(f"accion=usuario_alta&ref_id={user_id}")
    check("usuario_alta con rol en el detalle",
          st == 200 and total == 1 and (evs[0]["detalle"] or {}).get("rol") == "Vendedor",
          f"{st} {total} {evs}")

    st, _, _ = _req("PUT", base, f"/usuarios/{user_id}", tok, body={"rol_id": rol["id"]})
    check("cambiar rol del usuario -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=usuario_edicion&ref_id={user_id}")
    d = (evs[0]["detalle"] or {}) if evs else {}
    check("usuario_edicion registra rol_id antes/después",
          st == 200 and total == 1 and d.get("rol_id", {}).get("despues") == rol["id"],
          f"{st} {total} {d}")

    st, r_reset, _ = _req("POST", base, f"/usuarios/{user_id}/reset-password", tok)
    check("reset admin -> 200 con clave nueva", st == 200 and r_reset.get("password"), f"{st}")
    st, evs, total = eventos(f"accion=password_reset_admin&ref_id={user_id}")
    check("password_reset_admin registrado (sin la clave)",
          st == 200 and total == 1 and evs[0]["detalle"] is None
          and r_reset["password"] not in json.dumps(evs), f"{st} {total}")

    # rol_borrado: primero devolver el usuario a vendedor para liberar el rol
    _req("PUT", base, f"/usuarios/{user_id}", tok, body={"rol_id": vendedor["id"]})
    st, _, _ = _req("DELETE", base, f"/roles/{rol['id']}", tok)
    check("borrar rol -> 204", st == 204, f"{st}")
    st, evs, total = eventos(f"accion=rol_borrado&ref_id={rol['id']}")
    check("rol_borrado registrado", st == 200 and total == 1, f"{st} {total}")

    # ===== 5. recuperación de clave (autoservicio) =====
    print("--- 5. recuperación de clave")
    st, _, _ = _req("POST", base, "/auth/recuperar", body={"email": user_email})
    check("recuperar -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=password_recuperacion&q={user_email}")
    check("password_recuperacion registrada (evento interno)",
          st == 200 and total == 1, f"{st} {total}")

    st, envios, _ = _req("GET", base, f"/emails/envios?tipo=password_reset&ref_id={user_id}", tok)
    st, detalle, _ = _req("GET", base, f"/emails/envios/{envios[0]['id']}", tok)
    import re as _re
    m = _re.search(r"/restablecer\?token=([A-Za-z0-9_\-]+)", detalle.get("cuerpo") or "")
    check("token de reset disponible (modo simulado)", m is not None)
    st, _, _ = _req("POST", base, "/auth/restablecer",
                    body={"token": m.group(1), "password": "NuevaClave9"})
    check("restablecer -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=password_restablecida&q={user_email}")
    check("password_restablecida registrada", st == 200 and total == 1, f"{st} {total}")

    # ===== 6. RBAC de la consulta =====
    print("--- 6. RBAC")
    st, login_v, _ = _req("POST", base, "/auth/login",
                          body={"email": user_email, "password": "NuevaClave9"})
    tok_vend = login_v["access_token"] if st == 200 else None
    st, r_, _ = _req("GET", base, "/auditoria/eventos", tok_vend)
    check("rol vendedor -> 403 (nunca 401)", st == 403, f"{st} {r_}")
    st, r_, _ = _req("GET", base, "/auditoria/eventos", None)
    check("sin token -> 401", st == 401, f"{st}")

    # ===== 7. config ARCA y puntos de venta =====
    print("--- 7. config ARCA + PV")
    st, _, _ = _req("PUT", base, "/ventas/arca-config", tok, body={"modo": "simulado"})
    check("PUT arca-config -> 200", st == 200, f"{st}")
    st, evs, total = eventos("accion=arca_config")
    d = (evs[0]["detalle"] or {}) if evs else {}
    check("arca_config con modos y SIN material sensible",
          st == 200 and total == 1 and d.get("modo_despues") == "simulado"
          and d.get("cargo_certificado") is False
          and "PEM" not in json.dumps(evs) and "cert_pem" not in json.dumps(d),
          f"{st} {total} {d}")

    nro_pv = 9000 + int(SUF[:3], 16) % 900
    st, pv, _ = _req("POST", base, "/ventas/puntos-venta", tok,
                     body={"numero": nro_pv, "descripcion": f"PV audit {SUF}"})
    check("crear PV -> 201", st == 201, f"{st} {pv}")
    st, evs, total = eventos(f"accion=punto_venta_alta&ref_id={pv['id']}")
    check("punto_venta_alta registrado", st == 200 and total == 1, f"{st} {total}")

    st, _, _ = _req("PUT", base, f"/ventas/puntos-venta/{pv['id']}", tok,
                    body={"descripcion": f"PV audit v2 {SUF}"})
    check("editar PV -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=punto_venta_edicion&ref_id={pv['id']}")
    check("punto_venta_edicion con antes/después",
          st == 200 and total == 1
          and (evs[0]["detalle"] or {}).get("descripcion", {}).get("despues") == f"PV audit v2 {SUF}",
          f"{st} {total} {evs}")

    # ===== 8. cambio masivo de precios: dry-run NO audita =====
    print("--- 8. precios masivo + import excel")
    st, art, _ = _req("POST", base, "/articulos", tok, body={
        "codigo": f"AUD{SUF}", "descripcion": f"Articulo audit {SUF}",
        "tasa_iva": 21, "precio_1": 1000,
    })
    check("alta artículo fixture -> 201", st == 201, f"{st} {art}")

    st, r_dry, _ = _req("POST", base, "/articulos/cambio-precios", tok, body={
        "tipo": "porcentaje_precios", "porcentaje": 10, "q": f"AUD{SUF}", "dry_run": True,
    })
    check("dry-run -> 200 con 1 afectado", st == 200 and r_dry["afectados"] == 1, f"{st} {r_dry}")
    st, evs, total = eventos("accion=precios_masivo")
    check("dry-run NO audita", st == 200 and total == 0, f"{st} {total}")

    st, r_real, _ = _req("POST", base, "/articulos/cambio-precios", tok, body={
        "tipo": "porcentaje_precios", "porcentaje": 10, "q": f"AUD{SUF}",
    })
    check("cambio real -> 200", st == 200 and r_real["afectados"] == 1, f"{st} {r_real}")
    st, evs, total = eventos("accion=precios_masivo")
    d = (evs[0]["detalle"] or {}) if evs else {}
    check("precios_masivo auditado con parámetros y afectados",
          st == 200 and total == 1 and d.get("afectados") == 1
          and d.get("porcentaje") == "10" and d.get("filtros", {}).get("q") == f"AUD{SUF}",
          f"{st} {total} {d}")

    # import excel (multipart a mano)
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["codigo", "descripcion", "precio_1"])
    ws.append([f"XLS{SUF}", f"Importado audit {SUF}", 500])
    buf = io.BytesIO()
    wb.save(buf)
    boundary = f"----audit{SUF}"
    cuerpo = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"archivo\"; "
        f"filename=\"audit-{SUF}.xlsx\"\r\nContent-Type: application/octet-stream\r\n\r\n"
    ).encode() + buf.getvalue() + f"\r\n--{boundary}--\r\n".encode()
    st, r_xls, _ = _req("POST", base, "/articulos/importar-excel", tok, raw=cuerpo,
                        content_type=f"multipart/form-data; boundary={boundary}")
    check("import excel -> 200 con 1 creado", st == 200 and r_xls["creados"] == 1, f"{st} {r_xls}")
    st, evs, total = eventos("accion=import_excel")
    check("import_excel auditado con conteos",
          st == 200 and total == 1 and (evs[0]["detalle"] or {}).get("creados") == 1,
          f"{st} {total} {evs}")

    # ===== 9. nodos LAN =====
    print("--- 9. nodos LAN")
    st, sucs, _ = _req("GET", base, "/sucursales", tok)
    suc_id = sucs[0]["id"]
    st, nodo, _ = _req("POST", base, "/nodos", tok,
                       body={"sucursal_id": suc_id, "nombre": f"Nodo audit {SUF}"})
    check("crear nodo -> 201 con token", st == 201 and nodo.get("token"), f"{st}")
    st, evs, total = eventos(f"accion=nodo_alta&ref_id={nodo['id']}")
    check("nodo_alta registrado (sin el token)",
          st == 200 and total == 1 and nodo["token"] not in json.dumps(evs),
          f"{st} {total}")
    st, _, _ = _req("POST", base, f"/nodos/{nodo['id']}/regenerar-token", tok)
    check("regenerar token -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=nodo_token_regenerado&ref_id={nodo['id']}")
    check("nodo_token_regenerado registrado", st == 200 and total == 1, f"{st} {total}")
    st, _, _ = _req("POST", base, f"/nodos/{nodo['id']}/revocar", tok)
    check("revocar nodo -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=nodo_revocado&ref_id={nodo['id']}")
    check("nodo_revocado registrado", st == 200 and total == 1, f"{st} {total}")

    # ===== 10. períodos contables =====
    print("--- 10. períodos contables")
    st, r_per, _ = _req("POST", base, "/contabilidad/periodos/cerrar", tok,
                        body={"periodo": "2020-01-01"})
    check("cerrar período -> 201", st == 201, f"{st} {r_per}")
    per_id = r_per["id"]
    st, evs, total = eventos(f"accion=periodo_cerrado&ref_id={per_id}")
    check("periodo_cerrado registrado",
          st == 200 and total == 1 and "2020-01" in (evs[0]["ref_texto"] or ""),
          f"{st} {total} {evs}")
    st, _, _ = _req("POST", base, f"/contabilidad/periodos/{per_id}/reabrir", tok)
    check("reabrir período -> 200", st == 200, f"{st}")
    st, evs, total = eventos(f"accion=periodo_reabierto&ref_id={per_id}")
    check("periodo_reabierto registrado", st == 200 and total == 1, f"{st} {total}")

    # ===== 11. anulación POS con supervisor =====
    print("--- 11. anulación POS")
    st, cajas, _ = _req("GET", base, "/pos/cajas", tok)
    caja_id = cajas[0]["id"]
    st, sesion, _ = _req("POST", base, "/pos/sesiones", tok,
                         body={"caja_id": caja_id, "fondo_inicial": "1000"})
    check("abrir sesión POS -> 201", st == 201, f"{st} {sesion}")
    items = [{"articulo_id": art["id"], "cantidad": "1"}]
    st, calc, _ = _req("POST", base, "/pos/ventas/calcular", tok,
                       body={"caja_id": caja_id, "items": items})
    st, venta, _ = _req("POST", base, "/pos/ventas", tok, body={
        "sesion_id": sesion["id"], "items": items,
        "medios": [{"medio": "efectivo", "importe": calc["total"]}],
    })
    check("venta POS emitida -> 201", st == 201, f"{st} {venta}")
    st, nc, _ = _req("POST", base, f"/pos/ventas/{venta['id']}/anular", tok, body={
        "sesion_id": sesion["id"], "supervisor_email": email,
        "supervisor_password": clave, "motivo": "prueba F17",
    })
    check("anular con supervisor -> 200", st == 200, f"{st} {nc}")
    st, evs, total = eventos(f"accion=pos_anulacion_supervisor&ref_id={venta['id']}")
    d = (evs[0]["detalle"] or {}) if evs else {}
    check("pos_anulacion_supervisor con supervisor y motivo",
          st == 200 and total == 1 and d.get("supervisor_email") == email
          and d.get("motivo") == "prueba F17", f"{st} {total} {d}")
    _req("POST", base, f"/pos/sesiones/{sesion['id']}/cerrar", tok,
         body={"efectivo_contado": None})

    # ===== 12. consulta: filtros, catálogo, CSV, inmutabilidad =====
    print("--- 12. consulta y contrato")
    st, cat, _ = _req("GET", base, "/auditoria/catalogo", tok)
    check("catálogo con etiquetas y módulos",
          st == 200 and len(cat["acciones"]) >= 20 and "auth" in cat["modulos"], f"{st}")

    st, evs, total = eventos("modulo=auth")
    check("filtro por módulo auth", st == 200 and total >= 5
          and all(e["modulo"] == "auth" for e in evs), f"{st} {total}")

    hoy = date.today().isoformat()
    st, evs, total = eventos(f"accion=login_fallido&desde={hoy}&hasta={hoy}&q={email}")
    check("filtro combinado acción+rango+q", st == 200 and total == 1, f"{st} {total}")

    st, r_, _ = _req("GET", base, "/auditoria/eventos?accion=no_existe", tok)
    check("acción desconocida -> 422", st == 422, f"{st}")

    st, csv, hdrs = _req("GET", base, f"/auditoria/export.csv?q={email}", tok)
    check("export CSV con BOM y eventos",
          st == 200 and isinstance(csv, bytes) and csv[:3] == b"\xef\xbb\xbf"
          and email.encode() in csv, f"{st} {csv[:40] if isinstance(csv, bytes) else csv}")

    st, r_, _ = _req("PUT", base, "/auditoria/eventos", tok, body={})
    check("PUT sobre eventos -> 405 (inmutable)", st == 405, f"{st}")
    evento_id = evs[0]["id"] if evs else uuid.uuid4()
    st, r_, _ = _req("DELETE", base, f"/auditoria/eventos/{evento_id}", tok)
    check("DELETE de un evento -> sin ruta (404/405)", st in (404, 405), f"{st}")

    # ===== 13. aislamiento de tenant =====
    print("--- 13. aislamiento")
    st, login_demo, _ = _req("POST", base, "/auth/login",
                             body={"email": "admin@zgc.dev", "password": "123456"})
    if st == 200:
        st, evs, total = eventos(f"q={email}", token=login_demo["access_token"])
        check("otro tenant no ve los eventos", st == 200 and total == 0, f"{st} {total}")
    else:
        check("aislamiento (sin tenant demo local, salteado)", True)

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
