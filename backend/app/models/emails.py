"""Salida de documentos (F16 — DISENO-SALIDA-DOCUMENTOS.md): registro de
emails salientes + tokens de recuperación de contraseña. El `modo` queda
sellado por fila (patrón ARCA); en modo simulado el registro es la ÚNICA
evidencia del envío."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.models.base import Base


class EmailEnvio(Base):
    __tablename__ = "email_envios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    destinatario: Mapped[str] = mapped_column(String(120))
    asunto: Mapped[str] = mapped_column(String(200))
    # HTML completo: pesada, nunca viaja en listados (regla §6 de deferred)
    cuerpo: Mapped[str | None] = deferred(mapped_column(Text))
    tipo: Mapped[str] = mapped_column(String(20))  # comprobante | password_reset
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    modo: Mapped[str] = mapped_column(String(15))  # simulado | resend (sellado)
    estado: Mapped[str] = mapped_column(String(10))  # simulado | enviado | error
    error: Mapped[str | None] = mapped_column(String(300))
    proveedor_id: Mapped[str | None] = mapped_column(String(60))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    # sha256 hex del token urlsafe: el token en claro viaja SOLO en el email
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
