"""Fase 4 — Compras y Proveedores (migración 007).

El comprobante de compra lo emite el proveedor: numeración ajena, carga
manual, sin ARCA. Los datos del proveedor en compras y ordenes_pago son
snapshot al registrar (patrón receptor de ventas.py).
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
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.bue import Entidad


class Proveedor(Base):
    __tablename__ = "proveedores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    entidad_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entidades.id"))
    codigo: Mapped[str | None] = mapped_column(String(10))
    condicion_compra_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("condiciones_venta.id")
    )
    rubro: Mapped[str | None] = mapped_column(String(40))
    observaciones: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entidad: Mapped[Entidad] = relationship(lazy="joined")


class ArticuloProveedor(Base):
    __tablename__ = "articulo_proveedores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    articulo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articulos.id", ondelete="CASCADE")
    )
    proveedor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proveedores.id", ondelete="CASCADE")
    )
    codigo_proveedor: Mapped[str | None] = mapped_column(String(30))
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    bonif_1: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    bonif_2: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    bonif_3: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    ultima_compra: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TipoComprobanteCompra(Base):
    __tablename__ = "tipos_comprobante_compra"

    codigo: Mapped[str] = mapped_column(String(5), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(40))
    letra: Mapped[str] = mapped_column(String(1))
    clase: Mapped[str] = mapped_column(String(13))
    signo_cta_cte: Mapped[int] = mapped_column(SmallInteger, default=0)
    fiscal: Mapped[bool] = mapped_column(Boolean, default=False)
    codigo_arca: Mapped[int | None] = mapped_column(SmallInteger)  # 008: libro/CITI compras


class Compra(Base):
    __tablename__ = "compras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    tipo_codigo: Mapped[str] = mapped_column(ForeignKey("tipos_comprobante_compra.codigo"))
    letra: Mapped[str] = mapped_column(String(1))
    punto_venta: Mapped[int] = mapped_column(Integer, default=0)
    numero: Mapped[int] = mapped_column(BigInteger, default=0)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    periodo_iva: Mapped[date | None] = mapped_column(Date)
    proveedor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proveedores.id"))
    proveedor_nombre: Mapped[str] = mapped_column(String(120), default="")
    proveedor_cuit: Mapped[str | None] = mapped_column(String(11))
    proveedor_condicion_iva: Mapped[str] = mapped_column(String(2), default="RI")
    contado: Mapped[bool] = mapped_column(Boolean, default=False)
    condicion_compra_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("condiciones_venta.id")
    )
    condicion_desc: Mapped[str | None] = mapped_column(String(60))
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("depositos.id"))
    actualiza_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    actualiza_costos: Mapped[bool] = mapped_column(Boolean, default=True)
    neto_gravado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    no_gravado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    exento: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    percepcion_iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    percepcion_iibb: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    impuestos_internos: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    otros_tributos: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    redondeo: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estado: Mapped[str] = mapped_column(String(10), default="borrador")
    compra_asociada_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("compras.id"))
    observaciones: Mapped[str | None] = mapped_column(Text)
    registrado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registrado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tipo: Mapped[TipoComprobanteCompra] = relationship(lazy="joined")
    items: Mapped[list["CompraItem"]] = relationship(
        lazy="selectin", order_by="CompraItem.orden", cascade="all, delete-orphan"
    )
    vencimientos: Mapped[list["CompraVencimiento"]] = relationship(
        lazy="selectin", order_by="CompraVencimiento.nro_cuota", cascade="all, delete-orphan"
    )
    medios: Mapped[list["CompraMedio"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class CompraMedio(Base):
    """Medios de pago de una compra CONTADO (014, espejo de venta_medios).
    Sin filas = comportamiento histórico (sin contrapartida financiera)."""

    __tablename__ = "compra_medios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    compra_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compras.id", ondelete="CASCADE"))
    medio: Mapped[str] = mapped_column(String(15))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    cuenta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_bancarias.id")
    )
    referencia: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompraItem(Base):
    __tablename__ = "compra_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    compra_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compras.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    articulo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articulos.id"))
    variante_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articulo_variantes.id"))
    codigo: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(120))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    bonif_1: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    bonif_2: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    tasa_iva: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("21"))
    importe_neto: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    importe_iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    importe_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)


class CompraVencimiento(Base):
    __tablename__ = "compra_vencimientos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    compra_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compras.id", ondelete="CASCADE"))
    nro_cuota: Mapped[int] = mapped_column(SmallInteger, default=1)
    fecha_vto: Mapped[date] = mapped_column(Date)
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class NumeracionCompras(Base):
    __tablename__ = "numeracion_compras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(5))
    ultimo: Mapped[int] = mapped_column(BigInteger, default=0)


class OrdenPago(Base):
    __tablename__ = "ordenes_pago"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    # NULL = sin sucursal: la OP entra solo en la planilla de caja global
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    proveedor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proveedores.id"))
    proveedor_nombre: Mapped[str] = mapped_column(String(120))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    aplicado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estado: Mapped[str] = mapped_column(String(10), default="emitida")
    observaciones: Mapped[str | None] = mapped_column(Text)
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    medios: Mapped[list["OrdenPagoMedio"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class OrdenPagoMedio(Base):
    __tablename__ = "orden_pago_medios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    orden_pago_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ordenes_pago.id", ondelete="CASCADE")
    )
    medio: Mapped[str] = mapped_column(String(15))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    referencia: Mapped[str | None] = mapped_column(String(60))
    cuenta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_bancarias.id")
    )


class ImputacionCompra(Base):
    __tablename__ = "imputaciones_compras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    proveedor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proveedores.id"))
    orden_pago_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ordenes_pago.id", ondelete="CASCADE")
    )
    credito_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("compras.id", ondelete="CASCADE")
    )
    compra_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compras.id", ondelete="CASCADE"))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    # anulación NO destructiva (014): la imputación se marca, nunca se borra
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
