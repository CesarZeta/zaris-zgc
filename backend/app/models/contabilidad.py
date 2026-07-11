"""Fase 9 — Contabilidad (migración 015).

Diseño en docs/DISENO-CONTABILIDAD.md: contabilidad DERIVADA — el motor
(services/contabilidad.py) lee los documentos operativos y genera partida
doble según asiento_mapeos. Los asientos derivados (origen_tipo != 'manual')
son artefactos regenerables por período; los manuales se anulan marcando.
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


class PlanCuenta(Base):
    __tablename__ = "plan_cuentas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(15))
    nombre: Mapped[str] = mapped_column(String(80))
    # activo | pasivo | pn | r_positivo | r_negativo
    tipo: Mapped[str] = mapped_column(String(11))
    imputable: Mapped[bool] = mapped_column(Boolean, default=True)
    padre_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plan_cuentas.id"))
    es_sistema: Mapped[bool] = mapped_column(Boolean, default=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AsientoMapeo(Base):
    __tablename__ = "asiento_mapeos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    origen: Mapped[str] = mapped_column(String(20))
    clave: Mapped[str | None] = mapped_column(String(40))  # NULL = default de la regla
    cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_cuentas.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Asiento(Base):
    __tablename__ = "asientos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    numero: Mapped[int | None] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date)
    descripcion: Mapped[str | None] = mapped_column(String(200))
    origen_tipo: Mapped[str] = mapped_column(String(20), default="manual")
    origen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lineas: Mapped[list["AsientoLinea"]] = relationship(
        lazy="selectin", order_by="AsientoLinea.orden", cascade="all, delete-orphan"
    )


class AsientoLinea(Base):
    __tablename__ = "asiento_lineas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    asiento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("asientos.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plan_cuentas.id"))
    debe: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    haber: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    detalle: Mapped[str | None] = mapped_column(String(120))


class ContabPeriodo(Base):
    __tablename__ = "contab_periodos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    periodo: Mapped[date] = mapped_column(Date)  # 1° del mes
    cerrado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    cerrado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
