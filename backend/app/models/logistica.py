"""F12-bis — Logística de entregas (migración 025).

Diseño en docs/DISENO-LOGISTICA-Y-DOMICILIOS.md §2: rol transportista sobre la
BUE (patrón vendedores), entregas con domicilio SNAPSHOT (si el cliente se
muda, la entrega histórica no cambia) y hojas de ruta imprimibles. El estado
de entrega NO toca el circuito fiscal ni la cta. cte.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.bue import Entidad


class Transportista(Base):
    __tablename__ = "transportistas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    entidad_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entidades.id"))
    codigo: Mapped[str | None] = mapped_column(String(10))
    vehiculo: Mapped[str | None] = mapped_column(String(60))
    dominio: Mapped[str | None] = mapped_column(String(15))
    observaciones: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entidad: Mapped[Entidad] = relationship(lazy="joined")


class HojaRuta(Base):
    __tablename__ = "hojas_ruta"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    transportista_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("transportistas.id"))
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    # abierta (se arma) → en_reparto (despachada) → cerrada (rendida)
    estado: Mapped[str] = mapped_column(String(10), default="abierta")
    observaciones: Mapped[str | None] = mapped_column(String(200))
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transportista: Mapped[Transportista] = relationship(lazy="joined")
    entregas: Mapped[list["Entrega"]] = relationship(
        lazy="selectin", order_by="Entrega.orden", back_populates="hoja"
    )


class Entrega(Base):
    __tablename__ = "entregas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    comprobante_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comprobantes.id"))
    # snapshot del destino al crearla (OSM normalizado o texto libre)
    destinatario: Mapped[str] = mapped_column(String(120))
    domicilio: Mapped[str] = mapped_column(String(180))
    localidad: Mapped[str | None] = mapped_column(String(60))
    telefono: Mapped[str | None] = mapped_column(String(30))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    fecha_programada: Mapped[date | None] = mapped_column(Date)
    transportista_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transportistas.id"))
    hoja_ruta_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hojas_ruta.id"))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    # pendiente → asignada → en_reparto → entregada | rechazada;
    # reprogramada = terminal (la reemplaza una entrega nueva)
    estado: Mapped[str] = mapped_column(String(12), default="pendiente")
    bultos: Mapped[str | None] = mapped_column(String(60))
    recibido_por: Mapped[str | None] = mapped_column(String(80))
    motivo_rechazo: Mapped[str | None] = mapped_column(String(200))
    observaciones: Mapped[str | None] = mapped_column(String(200))
    rendida_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    hoja: Mapped[HojaRuta | None] = relationship(lazy="noload", back_populates="entregas")
