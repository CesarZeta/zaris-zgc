"""Auditoría de acciones (F17 — DISENO-AUDITORIA.md): eventos de seguridad y
escrituras de configuración que NO dejan documento. Tabla INMUTABLE por
construcción: la API no expone UPDATE/DELETE y no hay updated_at."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditEvento(Base):
    __tablename__ = "audit_eventos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    # SNAPSHOT (patrón F12-bis): legible sin join; si el usuario se renombra,
    # el evento no cambia. En login fallido: el email intentado.
    usuario_email: Mapped[str | None] = mapped_column(String(120))
    accion: Mapped[str] = mapped_column(String(40))  # catálogo en services/auditoria.py
    modulo: Mapped[str] = mapped_column(String(20))  # módulo RBAC del evento + 'auth'
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ref_texto: Mapped[str | None] = mapped_column(String(200))
    # parámetros / antes-después; NUNCA claves, hashes ni certificados
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
