"""Registro de auditoría (F17 — DISENO-AUDITORIA.md §3-§4).

Helper explícito SIN commit (patrón emitir_core): la fila entra a la
transacción del endpoint — si la acción rollbackea, el evento desaparece con
ella (correcto: la acción no ocurrió). La excepción son los eventos que deben
sobrevivir a una respuesta de error (login fallido): el caller los comitea
ANTES del raise (lección F16, CLAUDE.md §6).

El catálogo ACCIONES_AUDIT es la fuente de verdad de qué se audita (espejo del
§3 del diseño): toda fase nueva que agregue una escritura de configuración o
un evento de seguridad suma su acción acá y llama a `registrar`.
"""

import json
import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvento, Usuario

# accion -> (modulo, etiqueta humana). El módulo sale de acá (no se pasa a mano)
# para que el filtro del viewer sea consistente. `auth` no es un módulo RBAC:
# agrupa los eventos de sesión/credenciales.
ACCIONES_AUDIT: dict[str, tuple[str, str]] = {
    "login_ok": ("auth", "Ingreso"),
    "login_fallido": ("auth", "Ingreso fallido"),
    "password_recuperacion": ("auth", "Recuperación de contraseña solicitada"),
    "password_restablecida": ("auth", "Contraseña restablecida"),
    "password_reset_admin": ("configuracion", "Reset de contraseña por administrador"),
    "usuario_alta": ("configuracion", "Alta de usuario"),
    "usuario_edicion": ("configuracion", "Edición de usuario"),
    "rol_alta": ("configuracion", "Alta de rol"),
    "rol_edicion": ("configuracion", "Edición de rol"),
    "rol_permisos": ("configuracion", "Matriz de permisos modificada"),
    "rol_borrado": ("configuracion", "Rol eliminado"),
    "arca_config": ("configuracion", "Configuración ARCA modificada"),
    "punto_venta_alta": ("configuracion", "Alta de punto de venta"),
    "punto_venta_edicion": ("configuracion", "Edición de punto de venta"),
    "nodo_alta": ("configuracion", "Alta de nodo de sucursal"),
    "nodo_revocado": ("configuracion", "Nodo de sucursal revocado"),
    "nodo_token_regenerado": ("configuracion", "Token de nodo regenerado"),
    "precios_masivo": ("articulos", "Cambio masivo de precios"),
    "import_excel": ("articulos", "Importación de artículos desde Excel"),
    "pos_anulacion_supervisor": ("pos", "Anulación POS autorizada por supervisor"),
    "periodo_cerrado": ("contabilidad", "Período contable cerrado"),
    "periodo_reabierto": ("contabilidad", "Período contable reabierto"),
    # F18: primera LECTURA auditada — descargar todo el tenant es la lectura
    # más sensible del sistema (extensión anotada en el cierre de F17).
    "backup_descargado": ("configuracion", "Backup del tenant descargado"),
}


def ip_de(request: Request | None) -> str | None:
    """IP del cliente: primer valor de x-forwarded-for (Vercel/proxies) con
    fallback a la conexión directa (dev/nodo)."""
    if request is None:
        return None
    reenviado = request.headers.get("x-forwarded-for")
    if reenviado:
        return reenviado.split(",")[0].strip()[:45]
    return request.client.host[:45] if request.client else None


def registrar(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    accion: str,
    usuario: Usuario | None = None,
    usuario_email: str | None = None,
    ref_id: uuid.UUID | None = None,
    ref_texto: str | None = None,
    detalle: dict | None = None,
    request: Request | None = None,
) -> AuditEvento:
    """Agrega el evento a la sesión (sin commit). Devuelve la instancia por si
    el caller necesita comitearla suelta (login fallido)."""
    if accion not in ACCIONES_AUDIT:  # typo = error de programación, no de datos
        raise ValueError(f"Acción de auditoría inexistente: {accion}")
    if detalle is not None:
        # JSONB serializa con json.dumps: Decimal/UUID/date pasan por str
        detalle = json.loads(json.dumps(detalle, default=str))
    evento = AuditEvento(
        tenant_id=tenant_id,
        usuario_id=usuario.id if usuario else None,
        usuario_email=(usuario_email or (usuario.email if usuario else None) or "")[:120] or None,
        accion=accion,
        modulo=ACCIONES_AUDIT[accion][0],
        ref_id=ref_id,
        ref_texto=ref_texto[:200] if ref_texto else None,
        detalle=detalle,
        ip=ip_de(request),
    )
    db.add(evento)
    return evento
