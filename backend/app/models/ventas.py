"""Fase 3 — Ventas y Facturación Electrónica ARCA (migración 006).

Diseño de cumplimiento en docs/FACTURACION-ARCA.md. Los datos del receptor en
comprobantes y recibos son snapshot al momento de emitir: un documento fiscal
no cambia si después se edita la entidad.
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


class PuntoVenta(Base):
    __tablename__ = "puntos_venta"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    numero: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str] = mapped_column(String(60), default="")
    electronico: Mapped[bool] = mapped_column(Boolean, default=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TipoComprobante(Base):
    __tablename__ = "tipos_comprobante"

    codigo: Mapped[str] = mapped_column(String(5), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(40))
    letra: Mapped[str] = mapped_column(String(1))
    codigo_arca: Mapped[int | None] = mapped_column(SmallInteger)
    clase: Mapped[str] = mapped_column(String(13))
    signo_cta_cte: Mapped[int] = mapped_column(SmallInteger, default=0)
    fiscal: Mapped[bool] = mapped_column(Boolean, default=False)


class Numeracion(Base):
    __tablename__ = "numeracion"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    punto_venta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("puntos_venta.id", ondelete="CASCADE")
    )
    tipo_codigo: Mapped[str] = mapped_column(ForeignKey("tipos_comprobante.codigo"))
    ultimo: Mapped[int] = mapped_column(BigInteger, default=0)


class Comprobante(Base):
    __tablename__ = "comprobantes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    punto_venta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("puntos_venta.id"))
    tipo_codigo: Mapped[str] = mapped_column(ForeignKey("tipos_comprobante.codigo"))
    letra: Mapped[str] = mapped_column(String(1))
    numero: Mapped[int | None] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clientes.id"))
    receptor_nombre: Mapped[str] = mapped_column(String(120), default="Consumidor Final")
    receptor_doc_tipo: Mapped[int] = mapped_column(SmallInteger, default=99)
    receptor_doc_nro: Mapped[str | None] = mapped_column(String(11))
    receptor_condicion_iva: Mapped[str] = mapped_column(String(2), default="CF")
    receptor_domicilio: Mapped[str | None] = mapped_column(String(180))
    contado: Mapped[bool] = mapped_column(Boolean, default=True)
    condicion_venta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("condiciones_venta.id")
    )
    condicion_venta_desc: Mapped[str | None] = mapped_column(String(60))
    lista_precios: Mapped[int] = mapped_column(SmallInteger, default=1)
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("depositos.id"))
    actualiza_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    moneda: Mapped[str] = mapped_column(String(3), default="PES")
    cotizacion: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=1)
    descuento_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    descuento_importe: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    neto_gravado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    neto_no_gravado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    exento: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    otros_tributos: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    iva_contenido: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    otros_imp_indirectos: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estado: Mapped[str] = mapped_column(String(10), default="borrador")
    cae: Mapped[str | None] = mapped_column(String(14))
    cae_vencimiento: Mapped[date | None] = mapped_column(Date)
    arca_resultado: Mapped[str | None] = mapped_column(String(1))
    arca_observaciones: Mapped[str | None] = mapped_column(Text)
    # deferred: el XML completo de WSFEv1 no viaja en los SELECT de listados,
    # cta. cte., libros ni POS (regla §6 del CLAUDE.md). Solo se escribe al
    # emitir; nadie lo lee después (auditoría → recuperarlo exige undefer).
    arca_request: Mapped[str | None] = mapped_column(Text, deferred=True)
    arca_response: Mapped[str | None] = mapped_column(Text, deferred=True)
    comprobante_asociado_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comprobantes.id")
    )
    origen_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comprobantes.id"))
    pos_sesion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pos_sesiones.id"))
    # vendedor sellado (017, espejo de VENTASM.CVIAJ): default = el habitual
    # del cliente; la NC espejo lo copia de la factura
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vendedores.id"))
    observaciones: Mapped[str | None] = mapped_column(Text)
    emitido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emitido_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tipo: Mapped[TipoComprobante] = relationship(lazy="joined")
    punto_venta: Mapped[PuntoVenta] = relationship(lazy="joined")
    items: Mapped[list["ComprobanteItem"]] = relationship(
        lazy="selectin", order_by="ComprobanteItem.orden", cascade="all, delete-orphan"
    )
    alicuotas: Mapped[list["ComprobanteAlicuota"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )
    vencimientos: Mapped[list["ComprobanteVencimiento"]] = relationship(
        lazy="selectin", order_by="ComprobanteVencimiento.nro_cuota", cascade="all, delete-orphan"
    )


class ComprobanteItem(Base):
    __tablename__ = "comprobante_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    comprobante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    articulo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articulos.id"))
    variante_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articulo_variantes.id"))
    codigo: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(120))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    bonif_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    tasa_iva: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("21"))
    importe_neto: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    importe_iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    importe_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)


class ComprobanteAlicuota(Base):
    __tablename__ = "comprobante_alicuotas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    comprobante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    tasa: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    codigo_arca: Mapped[int] = mapped_column(SmallInteger)
    base: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)


class ComprobanteVencimiento(Base):
    __tablename__ = "comprobante_vencimientos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    comprobante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    nro_cuota: Mapped[int] = mapped_column(SmallInteger, default=1)
    fecha_vto: Mapped[date] = mapped_column(Date)
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class Recibo(Base):
    __tablename__ = "recibos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    punto_venta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("puntos_venta.id"))
    numero: Mapped[int] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    receptor_nombre: Mapped[str] = mapped_column(String(120))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    aplicado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    # cheques rechazados (014): el total NO se reescribe; el "a cuenta"
    # disponible es total − aplicado − rechazado_total
    rechazado_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estado: Mapped[str] = mapped_column(String(10), default="emitido")
    # vendedor sellado (017, espejo de RECIBOSM.CVIAJ): comisión por cobranza
    vendedor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vendedores.id"))
    observaciones: Mapped[str | None] = mapped_column(Text)
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    punto_venta: Mapped[PuntoVenta] = relationship(lazy="joined")
    medios: Mapped[list["ReciboMedio"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class ReciboMedio(Base):
    __tablename__ = "recibo_medios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    recibo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recibos.id", ondelete="CASCADE"))
    medio: Mapped[str] = mapped_column(String(15))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    referencia: Mapped[str | None] = mapped_column(String(60))
    cuenta_bancaria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cuentas_bancarias.id")
    )


class Imputacion(Base):
    __tablename__ = "imputaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    recibo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recibos.id", ondelete="CASCADE")
    )
    credito_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    comprobante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    # anulación NO destructiva (014): la imputación se marca, nunca se borra
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ArcaConfig(Base):
    __tablename__ = "arca_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), unique=True
    )
    modo: Mapped[str] = mapped_column(String(13), default="deshabilitado")
    cuit: Mapped[str | None] = mapped_column(String(11))
    razon_social: Mapped[str | None] = mapped_column(String(80))
    iibb: Mapped[str | None] = mapped_column(String(15))
    inicio_actividades: Mapped[date | None] = mapped_column(Date)
    concepto: Mapped[int] = mapped_column(SmallInteger, default=1)
    umbral_identificar_cf: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("10000000")
    )
    cert_pem: Mapped[str | None] = mapped_column(Text)
    key_pem: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ArcaToken(Base):
    __tablename__ = "arca_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    servicio: Mapped[str] = mapped_column(String(10), default="wsfe")
    modo: Mapped[str] = mapped_column(String(13))
    token: Mapped[str] = mapped_column(Text)
    sign: Mapped[str] = mapped_column(Text)
    expira: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
