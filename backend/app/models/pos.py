"""POS Mostrador (Fase 6, migración 009).

El POS vende con la maquinaria de Fase 3 (Comprobante + ARCA + stock); acá
vive lo específico del mostrador: la caja física (config), el turno del
cajero (sesión con apertura/arqueo/cierre) y los medios de pago por venta
contado (el hueco documentado en la planilla de caja de Fase 5).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PosCaja(Base):
    __tablename__ = "pos_cajas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    nombre: Mapped[str] = mapped_column(String(40))
    punto_venta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("puntos_venta.id"))
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("depositos.id"))
    lista_precios: Mapped[int] = mapped_column(SmallInteger, default=1)
    ancho_ticket: Mapped[int] = mapped_column(SmallInteger, default=80)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PosSesion(Base):
    __tablename__ = "pos_sesiones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    caja_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pos_cajas.id"))
    cajero_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    estado: Mapped[str] = mapped_column(String(7), default="abierta")
    fondo_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    abierta_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cerrada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cantidad_tickets: Mapped[int | None] = mapped_column(Integer)
    total_ventas: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    cobrado_efectivo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    cobrado_tarjeta: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    cobrado_mercadopago: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    cobrado_otros: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    efectivo_teorico: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    efectivo_contado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    diferencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    observaciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    caja: Mapped[PosCaja] = relationship(lazy="joined")


class VentaMedio(Base):
    __tablename__ = "venta_medios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    comprobante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    pos_sesion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pos_sesiones.id"))
    medio: Mapped[str] = mapped_column(String(15))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    referencia: Mapped[str | None] = mapped_column(String(60))
    cuenta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_bancarias.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
