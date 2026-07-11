"""Caja e IVA (Fase 5, migración 008).

Espejo del legacy: CONC_CAJ (conceptos), MOVIM (movimientos manuales),
SALCAJA (cierre/arqueo diario), RET_CLI/RET_PROV (retenciones básicas).
Los libros de IVA y la planilla diaria son reportes, no tablas.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ConceptoCaja(Base):
    __tablename__ = "conceptos_caja"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(40))
    tipo: Mapped[str] = mapped_column(String(7))  # entrada | salida
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CajaMovimiento(Base):
    __tablename__ = "caja_movimientos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    concepto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conceptos_caja.id"))
    tipo: Mapped[str] = mapped_column(String(7))  # sellado del concepto al crear
    medio: Mapped[str] = mapped_column(String(15), default="efectivo")
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    descripcion: Mapped[str | None] = mapped_column(String(120))
    cuenta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_bancarias.id")
    )
    # eliminar = marcar (014): el movimiento nunca se borra físicamente
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    concepto: Mapped[ConceptoCaja] = relationship(lazy="joined")


class CajaCierre(Base):
    __tablename__ = "caja_cierres"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    fecha: Mapped[date] = mapped_column(Date)
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    entradas: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    salidas: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    saldo_final: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    efectivo_contado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    diferencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    observaciones: Mapped[str | None] = mapped_column(Text)
    # reabrir = marcar (014): el cierre sellado nunca se borra físicamente
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    cerrado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Retencion(Base):
    __tablename__ = "retenciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(10))  # sufrida | practicada
    regimen: Mapped[str] = mapped_column(String(10))  # IVA | IIBB | Ganancias | SUSS | otro
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    nro_certificado: Mapped[str | None] = mapped_column(String(30))
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clientes.id"))
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proveedores.id"))
    recibo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("recibos.id", ondelete="SET NULL"))
    orden_pago_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ordenes_pago.id", ondelete="SET NULL")
    )
    descripcion: Mapped[str | None] = mapped_column(String(120))
    # eliminar = marcar (014)
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
