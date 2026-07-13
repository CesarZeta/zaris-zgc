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
    # Perfil (F12-d): estandar = mostrador (F6) | resto = mesas/comandas (§3)
    perfil: Mapped[str] = mapped_column(String(10), default="estandar")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PosBalanzaConfig(Base):
    """Config de etiquetas de balanza por tenant (F12-b). Esquema clásico:
    prefijo(2) + PLU(codigo_digitos) + valor(10-codigo_digitos) + DV = EAN-13.
    Ausencia de fila (o habilitado=False) = parsing de etiquetas apagado."""

    __tablename__ = "pos_balanza_config"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)
    prefijo: Mapped[str] = mapped_column(String(2), default="20")
    valor_tipo: Mapped[str] = mapped_column(String(7), default="peso")
    codigo_digitos: Mapped[int] = mapped_column(SmallInteger, default=5)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    caja: Mapped[PosCaja] = relationship(lazy="joined")


class PosSalon(Base):
    """Sector del local resto (salón, vereda, barra) — F12-d."""

    __tablename__ = "pos_salones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(40))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PosMesa(Base):
    __tablename__ = "pos_mesas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    salon_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pos_salones.id", ondelete="CASCADE")
    )
    numero: Mapped[int] = mapped_column(Integer)
    nombre: Mapped[str | None] = mapped_column(String(20))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PosComanda(Base):
    """Cuenta abierta de mesa / pedido delivery (legacy MESAS.DBF). NO es un
    comprobante: el comprobante fiscal nace recién al cobrar (mandato César:
    nada de esto se traslada a la gestión)."""

    __tablename__ = "pos_comandas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    caja_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pos_cajas.id"))
    mesa_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pos_mesas.id"))
    tipo: Mapped[str] = mapped_column(String(10), default="mesa")
    estado: Mapped[str] = mapped_column(String(10), default="abierta")
    mozo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    cubiertos: Mapped[int | None] = mapped_column(SmallInteger)
    cliente_nombre: Mapped[str | None] = mapped_column(String(80))
    telefono: Mapped[str | None] = mapped_column(String(40))
    domicilio: Mapped[str | None] = mapped_column(String(120))
    localidad: Mapped[str | None] = mapped_column(String(60))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    envio_estado: Mapped[str | None] = mapped_column(String(15))
    propina_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    observaciones: Mapped[str | None] = mapped_column(String(200))
    comprobante_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("comprobantes.id"))
    abierta_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cerrada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["PosComandaItem"]] = relationship(
        lazy="selectin", order_by="PosComandaItem.orden", cascade="all, delete-orphan"
    )


class PosComandaItem(Base):
    __tablename__ = "pos_comanda_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    comanda_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pos_comandas.id", ondelete="CASCADE")
    )
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulos.id"))
    variante_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articulo_variantes.id"))
    descripcion: Mapped[str] = mapped_column(String(120))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    observaciones: Mapped[str | None] = mapped_column(String(120))
    estado_cocina: Mapped[str] = mapped_column(String(10), default="pendiente")
    enviado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
