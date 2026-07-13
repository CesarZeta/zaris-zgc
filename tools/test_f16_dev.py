"""Suite en vivo de F16 (Salida de documentos: PDF + email) contra DEV.

Cubre: PDF server-side del comprobante (bytes %PDF, 409 borrador, 404
inexistente), envío por email en modo simulado (registro en email_envios con
modo sellado, destinatario explícito y default de entidad, 422 sin email,
409 borrador), bandeja de salida (filtros específicos por tipo/ref_id, cuerpo
deferred solo en el detalle, RBAC configuracion.ver → 403 nunca 401) y la
recuperación de contraseña autoservicio (mismo 200 exista o no el email,
token de un solo uso con vencimiento, restablecer + re-login, reuso 422).

Prerrequisito: EMAIL_MODO sin setear (default "simulado") en el backend.

Uso:
    python tools/test_f16_dev.py --base http://127.0.0.1:8021 \
        --email admin@zgc.dev --clave 123456
"""

import argparse
import json
import re
import sys
import urllib.error as E
import urllib.request as U
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print("login FAIL", st, r)
        sys.exit(1)
    tok = r["access_token"]

    # ===== Fixture: factura contado CF con ítem de texto libre (sin stock) =====
    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    check("hay punto de venta", st == 200 and len(pvs) > 0, f"{st} {pvs}")
    pv_id = pvs[0]["id"]

    st, borr = _req("POST", base, "/ventas/comprobantes", tok, body={
        "clase": "factura",
        "punto_venta_id": pv_id,
        "contado": True,
        "items": [{"descripcion": f"Servicio F16 {SUF}", "cantidad": 1,
                   "precio_unitario": 1234.56}],
    })
    check("borrador creado", st in (200, 201) and borr["estado"] == "borrador", f"{st} {borr}")
    borr_id = borr["id"]

    # ===== A. PDF: borrador no se imprime / emitido baja bytes reales =====
    print("--- A. PDF server-side")
    st, r = _req("GET", base, f"/ventas/comprobantes/{borr_id}/pdf", tok)
    check("PDF de borrador → 409", st == 409, f"{st} {r}")
    st, r = _req("POST", base, f"/ventas/comprobantes/{borr_id}/enviar", tok, body={})
    check("enviar borrador → 409", st == 409, f"{st} {r}")

    st, emitido = _req("POST", base, f"/ventas/comprobantes/{borr_id}/emitir", tok, body={})
    check("emitir fixture", st == 200 and emitido["estado"] == "emitido", f"{st} {emitido}")
    comp_id = emitido["id"]
    numero = emitido.get("numero_formateado")

    st, pdf = _req("GET", base, f"/ventas/comprobantes/{comp_id}/pdf", tok)
    check("PDF emitido → 200", st == 200, f"{st}")
    check("PDF es un PDF real", isinstance(pdf, bytes) and pdf[:5] == b"%PDF-" and len(pdf) > 1500,
          f"prefijo={pdf[:8] if isinstance(pdf, bytes) else type(pdf)}")
    st, r = _req("GET", base, f"/ventas/comprobantes/{uuid.uuid4()}/pdf", tok)
    check("PDF inexistente → 404", st == 404, f"{st}")

    # ===== B. Envío por email (modo simulado) =====
    print("--- B. Envío por email")
    st, r = _req("POST", base, f"/ventas/comprobantes/{comp_id}/enviar", tok, body={})
    check("enviar sin email y sin cliente → 422", st == 422, f"{st} {r}")

    destino = f"f16-{SUF}@zgc.dev"
    st, envio = _req("POST", base, f"/ventas/comprobantes/{comp_id}/enviar", tok,
                     body={"email": destino})
    envio = envio if isinstance(envio, dict) else {}
    check("enviar con email explícito → 200 simulado",
          st == 200 and envio.get("estado") == "simulado" and envio.get("modo") == "simulado"
          and envio.get("destinatario") == destino, f"{st} {envio}")
    check("asunto lleva el número", st == 200 and (numero or "") in envio.get("asunto", ""),
          f"{envio.get('asunto')}")

    st, envios = _req("GET", base, f"/emails/envios?tipo=comprobante&ref_id={comp_id}", tok)
    check("bandeja filtrada por ref_id → 1 envío",
          st == 200 and len(envios) == 1 and envios[0]["destinatario"] == destino,
          f"{st} {envios}")
    check("listado NO trae cuerpo (deferred)", st == 200 and "cuerpo" not in envios[0])

    st, detalle = _req("GET", base, f"/emails/envios/{envios[0]['id']}", tok)
    check("detalle trae cuerpo con el total del server",
          st == 200 and detalle.get("cuerpo") and str(emitido["total"]) in detalle["cuerpo"],
          f"{st} total={emitido.get('total')}")
    check("cuerpo avisa modo simulado",
          st == 200 and "simulado" in detalle["cuerpo"].lower())

    st, r = _req("GET", base, f"/emails/envios/{uuid.uuid4()}", tok)
    check("detalle inexistente → 404", st == 404, f"{st}")
    st, r = _req("GET", base, "/emails/envios", None)
    check("bandeja sin token → 401", st == 401, f"{st}")

    # ===== C. Recuperación de contraseña autoservicio =====
    print("--- C. Recuperación de contraseña")
    st, roles = _req("GET", base, "/roles", tok)
    vendedor = next((x for x in roles if x["codigo"] == "vendedor"), None)
    check("rol vendedor disponible", vendedor is not None, f"{st}")

    user_email = f"f16-user-{SUF}@zgc.dev"
    st, nuevo = _req("POST", base, "/usuarios", tok, body={
        "email": user_email, "nombre": f"Prueba F16 {SUF}",
        "password": "Original6", "rol_id": vendedor["id"],
    })
    check("alta usuario de prueba", st == 201, f"{st} {nuevo}")
    user_id = nuevo["id"]

    st, r = _req("POST", base, "/auth/login",
                 body={"email": user_email, "password": "Original6"})
    check("login inicial del usuario", st == 200, f"{st}")
    tok_vend = r["access_token"] if st == 200 else None

    st, r = _req("GET", base, "/emails/envios", tok_vend)
    check("bandeja con rol vendedor → 403 (nunca 401)", st == 403, f"{st} {r}")

    st, r = _req("POST", base, "/auth/recuperar",
                 body={"email": f"no-existe-{SUF}@zgc.dev"})
    mensaje_generico = r.get("detail") if st == 200 else None
    check("recuperar email inexistente → 200 genérico", st == 200 and mensaje_generico,
          f"{st} {r}")

    st, r = _req("POST", base, "/auth/recuperar", body={"email": user_email})
    check("recuperar email real → mismo 200 (no filtra)",
          st == 200 and r.get("detail") == mensaje_generico, f"{st} {r}")

    st, envios = _req("GET", base, f"/emails/envios?tipo=password_reset&ref_id={user_id}", tok)
    check("email de reset registrado (simulado)",
          st == 200 and len(envios) == 1 and envios[0]["estado"] == "simulado",
          f"{st} {envios}")
    st, detalle = _req("GET", base, f"/emails/envios/{envios[0]['id']}", tok)
    m = re.search(r"/restablecer\?token=([A-Za-z0-9_\-]+)", detalle.get("cuerpo") or "")
    check("el cuerpo trae el link con token", m is not None)
    token_reset = m.group(1) if m else ""

    st, r = _req("POST", base, "/auth/restablecer",
                 body={"token": "x" * 43, "password": "NuevaClave9"})
    check("token inválido → 422", st == 422, f"{st} {r}")
    st, r = _req("POST", base, "/auth/restablecer",
                 body={"token": token_reset, "password": "corta"})
    check("password corta → 422", st == 422, f"{st}")

    st, r = _req("POST", base, "/auth/restablecer",
                 body={"token": token_reset, "password": "NuevaClave9"})
    check("restablecer OK", st == 200, f"{st} {r}")

    st, r = _req("POST", base, "/auth/login",
                 body={"email": user_email, "password": "Original6"})
    check("clave vieja ya no entra → 401", st == 401, f"{st}")
    st, r = _req("POST", base, "/auth/login",
                 body={"email": user_email, "password": "NuevaClave9"})
    check("clave nueva entra → 200", st == 200, f"{st}")

    st, r = _req("POST", base, "/auth/restablecer",
                 body={"token": token_reset, "password": "OtraClave99"})
    check("token es de un solo uso → 422", st == 422, f"{st} {r}")

    # ===== Cleanup =====
    st, r = _req("PUT", base, f"/usuarios/{user_id}", tok, body={"activo": False})
    check("cleanup: usuario desactivado", st == 200, f"{st} {r}")

    print(f"\nRESULTADO: {ok} ok, {fail} fail")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
