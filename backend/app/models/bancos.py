"""Fase 8 — Cheques y Bancos (migración 013).

Diseño en docs/DISENO-CHEQUES-Y-BANCOS.md. El cheque es una entidad con máquina
de estados (terceros: en_cartera→depositado→acreditado / endosado / rechazado;
propios: emitido→debitado). Modernización del legacy cheques.DBF (PROP_TER,
CART_PAS, RECHAZADO, PASADO_A) con estados explícitos y FKs. Las transiciones
viven en app/core/cheques_core.py (sin commit), reutilizables por cobranza (ventas),
OP (compras) y los endpoints de cheques — patrón emitir_core (CLAUDE.md §6).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CuentaBancaria(Base):
    __tablename__ = "cuentas_bancarias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    banco: Mapped[str] = mapped_column(String(60))
    sucursal_bancaria: Mapped[str | None] = mapped_column(String(60))
    tipo: Mapped[str] = mapped_column(String(2), default="CC")  # CC | CA
    numero: Mapped[str | None] = mapped_column(String(30))
    cbu: Mapped[str | None] = mapped_column(String(22))
    alias: Mapped[str | None] = mapped_column(String(40))
    moneda: Mapped[str] = mapped_column(String(3), default="ARS")
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    # fecha de corte del saldo inicial (014): el asiento de apertura del
    # motor contable necesita "saldo inicial ¿a qué fecha?"
    saldo_inicial_fecha: Mapped[date | None] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    observaciones: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cheque(Base):
    __tablename__ = "cheques"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    clase: Mapped[str] = mapped_column(String(8))  # tercero | propio
    numero: Mapped[str] = mapped_column(String(20))
    banco: Mapped[str] = mapped_column(String(60))
    sucursal_banco: Mapped[str | None] = mapped_column(String(60))
    plaza: Mapped[str | None] = mapped_column(String(60))
    titular: Mapped[str | None] = mapped_column(String(80))
    cuit_firmante: Mapped[str | None] = mapped_column(String(13))
    fecha_emision: Mapped[date | None] = mapped_column(Date)
    fecha_pago: Mapped[date] = mapped_column(Date)
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    moneda: Mapped[str] = mapped_column(String(3), default="ARS")
    es_echeq: Mapped[bool] = mapped_column(Boolean, default=False)
    # origen (cheque de tercero recibido en cobranza)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clientes.id"))
    recibo_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recibos.id", ondelete="SET NULL")
    )
    # destino (según estado)
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proveedores.id"))
    orden_pago_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ordenes_pago.id", ondelete="SET NULL")
    )
    cuenta_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cuentas_bancarias.id"))
    banco_movimiento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("banco_movimientos.id", ondelete="SET NULL")
    )
    estado: Mapped[str] = mapped_column(String(12))
    observaciones: Mapped[str | None] = mapped_column(String(200))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExtractoImport(Base):
    __tablename__ = "extracto_imports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cuentas_bancarias.id", ondelete="CASCADE")
    )
    nombre_archivo: Mapped[str | None] = mapped_column(String(200))
    filas_total: Mapped[int] = mapped_column(Integer, default=0)
    filas_conciliadas: Mapped[int] = mapped_column(Integer, default=0)
    fecha_import: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))


class BancoMovimiento(Base):
    __tablename__ = "banco_movimientos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cuentas_bancarias.id", ondelete="CASCADE")
    )
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    # deposito | extraccion | transferencia_in | transferencia_out | debito |
    # credito | comision | ajuste_positivo | ajuste_negativo
    # (el signo lo da el tipo; importe siempre > 0)
    tipo: Mapped[str] = mapped_column(String(18))
    importe: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    descripcion: Mapped[str | None] = mapped_column(String(120))
    referencia: Mapped[str | None] = mapped_column(String(60))
    cheque_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cheques.id", ondelete="SET NULL")
    )
    conciliado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_conciliacion: Mapped[date | None] = mapped_column(Date)
    extracto_import_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("extracto_imports.id", ondelete="SET NULL")
    )
    origen: Mapped[str] = mapped_column(String(8), default="manual")
    # apareo de transferencias entre cuentas propias (016, simétrico): un par
    # apareado deriva UN asiento banco a banco, sin cuenta puente
    contrapartida_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("banco_movimientos.id", ondelete="SET NULL")
    )
    # eliminar = marcar (014): el movimiento nunca se borra físicamente
    anulado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anulado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChequeEvento(Base):
    __tablename__ = "cheque_eventos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    cheque_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cheques.id", ondelete="CASCADE"))
    fecha: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    estado_desde: Mapped[str | None] = mapped_column(String(12))
    estado_hasta: Mapped[str] = mapped_column(String(12))
    detalle: Mapped[str | None] = mapped_column(String(200))
    banco_movimiento_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("banco_movimientos.id", ondelete="SET NULL")
    )
    creado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
