"""Email transaccional (F16 — DISENO-SALIDA-DOCUMENTOS.md §3).

Infraestructura GLOBAL del SaaS (env vars, no config por tenant) con el patrón
de modos de ARCA: `deshabilitado` / `simulado` (default: registra sin enviar —
el registro es la evidencia) / `resend` (envío real por API). Todo envío deja
fila en `email_envios` con el `modo` SELLADO, incluso los errores del
proveedor (el caller comitea el registro de error ANTES de responder 502).

SIN commit adentro (patrón *_core): el endpoint comitea en su transacción.
"""

import base64

import httpx

from app.core.config import settings
from app.models import EmailEnvio

RESEND_URL = "https://api.resend.com/emails"


class EmailDeshabilitadoError(Exception):
    """EMAIL_MODO=deshabilitado — el endpoint responde 400 (espejo ARCA)."""


class ErrorEnvioEmail(Exception):
    """Fallo del proveedor o de red. `self.envio` es el registro con
    estado='error' ya agregado a la sesión: el caller debe COMITEARLO
    antes de responder 502 (si no, la evidencia se pierde en el rollback)."""

    def __init__(self, detalle: str, envio: EmailEnvio):
        super().__init__(detalle)
        self.envio = envio


async def enviar_email(
    db,
    tenant_id,
    *,
    destinatario: str,
    asunto: str,
    cuerpo_html: str,
    tipo: str,
    ref_id=None,
    adjuntos: list[tuple[str, bytes]] | None = None,
    reply_to: str | None = None,
    creado_por=None,
) -> EmailEnvio:
    modo = settings.EMAIL_MODO
    if modo == "deshabilitado":
        raise EmailDeshabilitadoError()
    if modo not in ("simulado", "resend"):
        # modo desconocido degrada a simulado (nunca bloquear por un valor no
        # mapeado — mismo criterio que los planes de tenant)
        modo = "simulado"

    envio = EmailEnvio(
        tenant_id=tenant_id,
        destinatario=destinatario,
        asunto=asunto[:200],
        cuerpo=cuerpo_html,
        tipo=tipo,
        ref_id=ref_id,
        modo=modo,
        estado="simulado",
        creado_por=creado_por,
    )

    if modo == "resend":
        payload: dict = {
            "from": settings.EMAIL_FROM,
            "to": [destinatario],
            "subject": asunto,
            "html": cuerpo_html,
        }
        if reply_to:
            payload["reply_to"] = reply_to
        if adjuntos:
            payload["attachments"] = [
                {"filename": nombre, "content": base64.b64encode(contenido).decode()}
                for nombre, contenido in adjuntos
            ]
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    RESEND_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                )
        except httpx.HTTPError as exc:
            envio.estado = "error"
            envio.error = f"red: {exc}"[:300]
            db.add(envio)
            await db.flush()
            raise ErrorEnvioEmail(f"No se pudo contactar al proveedor de email: {exc}", envio)
        if resp.status_code >= 400:
            envio.estado = "error"
            envio.error = f"HTTP {resp.status_code}: {resp.text}"[:300]
            db.add(envio)
            await db.flush()
            raise ErrorEnvioEmail(f"El proveedor de email rechazó el envío (HTTP {resp.status_code})", envio)
        envio.estado = "enviado"
        envio.proveedor_id = (resp.json() or {}).get("id")

    db.add(envio)
    await db.flush()
    return envio
