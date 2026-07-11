import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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


class Familia(Base):
    __tablename__ = "familias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(40))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)

    subfamilias: Mapped[list["Subfamilia"]] = relationship(lazy="selectin")


class Subfamilia(Base):
    __tablename__ = "subfamilias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    familia_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("familias.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(40))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Marca(Base):
    __tablename__ = "marcas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(40))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Unidad(Base):
    __tablename__ = "unidades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(6))
    nombre: Mapped[str] = mapped_column(String(30))


class Deposito(Base):
    __tablename__ = "depositos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    codigo: Mapped[str] = mapped_column(String(4))
    nombre: Mapped[str] = mapped_column(String(40))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    vigente_desde: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))


class Articulo(Base):
    __tablename__ = "articulos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(20))
    codigo_barras: Mapped[str | None] = mapped_column(String(20))
    descripcion: Mapped[str] = mapped_column(String(80))
    familia_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("familias.id"))
    subfamilia_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subfamilias.id"))
    marca_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("marcas.id"))
    unidad_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("unidades.id"))
    controla_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    costo: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    costo_con_iva: Mapped[bool] = mapped_column(Boolean, default=False)
    tasa_iva: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("21"))
    utilidad_1: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    utilidad_2: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    utilidad_3: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    utilidad_4: Mapped[Decimal] = mapped_column(Numeric(7, 2), default=0)
    precio_1: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    precio_2: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    precio_3: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    precio_4: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    en_dolares: Mapped[bool] = mapped_column(Boolean, default=False)
    impuesto_interno: Mapped[Decimal] = mapped_column(Numeric(12, 5), default=0)
    pesable: Mapped[bool] = mapped_column(Boolean, default=False)
    # PLU corto que imprime la balanza (F12-b): único por tenant, sin ceros a
    # la izquierda. NULL = el artículo no se etiqueta por balanza.
    codigo_balanza: Mapped[str | None] = mapped_column(String(6))
    venta_por_depto: Mapped[bool] = mapped_column(Boolean, default=False)
    es_envase_retornable: Mapped[bool] = mapped_column(Boolean, default=False)
    envase_articulo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("articulos.id"))
    proveedor_habitual_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proveedores.id"))
    precio_actualizado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Atributo(Base):
    __tablename__ = "atributos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(30))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)

    valores: Mapped[list["AtributoValor"]] = relationship(
        lazy="selectin", order_by="AtributoValor.orden"
    )


class AtributoValor(Base):
    __tablename__ = "atributo_valores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    atributo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atributos.id", ondelete="CASCADE"))
    valor: Mapped[str] = mapped_column(String(30))
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)


class ArticuloVariante(Base):
    __tablename__ = "articulo_variantes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulos.id", ondelete="CASCADE"))
    valor_1_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atributo_valores.id"))
    valor_2_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("atributo_valores.id"))
    valor_3_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("atributo_valores.id"))
    codigo_barras: Mapped[str | None] = mapped_column(String(20))
    sku_sufijo: Mapped[str | None] = mapped_column(String(20))
    dif_precio: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ArticuloStock(Base):
    __tablename__ = "articulo_stock"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulos.id", ondelete="CASCADE"))
    deposito_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("depositos.id"))
    variante_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("articulo_variantes.id", ondelete="CASCADE")
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    ubicacion: Mapped[str | None] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DespiecePlantilla(Base):
    """Plantilla de despiece/transformación (F12-c): artículo origen (media
    res, bolsa a fraccionar) + cortes con % de rendimiento sugerido y
    coeficiente de valor. Precarga la pantalla; los kilos reales se corrigen
    a mano en cada ingreso."""

    __tablename__ = "despiece_plantillas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    articulo_origen_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulos.id"))
    nombre: Mapped[str] = mapped_column(String(60))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    cortes: Mapped[list["DespiecePlantillaCorte"]] = relationship(
        lazy="selectin", order_by="DespiecePlantillaCorte.orden", cascade="all, delete-orphan"
    )


class DespiecePlantillaCorte(Base):
    __tablename__ = "despiece_plantilla_cortes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    plantilla_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("despiece_plantillas.id", ondelete="CASCADE")
    )
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulos.id"))
    rendimiento_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3), default=0)
    coef_valor: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=1)
    orden: Mapped[int] = mapped_column(SmallInteger, default=0)


class StockMovimiento(Base):
    __tablename__ = "stock_movimientos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    articulo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("articulos.id", ondelete="CASCADE"))
    deposito_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("depositos.id"))
    variante_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("articulo_variantes.id", ondelete="CASCADE")
    )
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tipo: Mapped[str] = mapped_column(String(15))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    saldo_resultante: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    # costo unitario NETO de IVA en ARS sellado al mover (014).
    # NULL = movimiento histórico sin costo sellado.
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    comprobante: Mapped[str | None] = mapped_column(String(30))
    observaciones: Mapped[str | None] = mapped_column(String(120))
    grupo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
