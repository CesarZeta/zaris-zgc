"""F11 — Vendedores y comisiones (migración 017).

Diseño en docs/DISENO-VENDEDORES-COMISIONES.md: rol vendedor sobre la BUE
(espejo moderno de VIAJANTE.DBF, % único + modalidad venta/cobranza) y
liquidaciones como DOCUMENTO contabilizable — "ya liquidado" se deriva de que
exista un ítem de una liquidación viva, los documentos fuente no se mutan.
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
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.bue import Entidad


class Vendedor(Base):
    __tablename__ = "vendedores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    entidad_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entidades.id"))
    codigo: Mapped[str | None] = mapped_column(String(10))
    comision_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    # venta = devenga sobre lo facturado | cobranza = sobre lo cobrado
    modalidad: Mapped[str] = mapped_column(String(8), default="venta")
    observaciones: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entidad: Mapped[Entidad] = relationship(lazy="joined")


class ComisionLiquidacion(Base):
    __tablename__ = "comision_liquidaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(BigInteger)
    vendedor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vendedores.id"))
    modalidad: Mapped[str] = mapped_column(String(8))
    desde: Mapped[date] = mapped_column(Date)
    hasta: Mapped[date] = mapped_column(Date)
    comision_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # sellado al liquidar
    base_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    observaciones: Mapped[str | None] = mapped_column(String(200))
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["ComisionLiquidacionItem"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class ComisionLiquidacionItem(Base):
    __tablename__ = "comision_liquidacion_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    liquidacion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comision_liquidaciones.id", ondelete="CASCADE")
    )
    comprobante_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    recibo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recibos.id", ondelete="CASCADE")
    )
    fecha: Mapped[date] = mapped_column(Date)
    descripcion: Mapped[str] = mapped_column(String(120))
    base: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
