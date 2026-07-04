import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
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


class Provincia(Base):
    __tablename__ = "provincias"

    codigo_arca: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)


class Entidad(Base):
    __tablename__ = "entidades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    tipo_persona: Mapped[str] = mapped_column(String(1), default="F")
    razon_social: Mapped[str] = mapped_column(String(120))
    nombre_fantasia: Mapped[str | None] = mapped_column(String(80))
    tipo_documento: Mapped[str] = mapped_column(String(4), default="DNI")
    nro_documento: Mapped[str | None] = mapped_column(String(11))
    condicion_iva: Mapped[str] = mapped_column(String(2), default="CF")
    email: Mapped[str | None] = mapped_column(String(120))
    telefono_1: Mapped[str | None] = mapped_column(String(30))
    telefono_2: Mapped[str | None] = mapped_column(String(30))
    domicilio: Mapped[str | None] = mapped_column(String(120))
    localidad: Mapped[str | None] = mapped_column(String(60))
    provincia_id: Mapped[int | None] = mapped_column(ForeignKey("provincias.codigo_arca"))
    codigo_postal: Mapped[str | None] = mapped_column(String(10))
    observaciones: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntidadContacto(Base):
    __tablename__ = "entidad_contactos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    entidad_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entidades.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(80))
    cargo: Mapped[str | None] = mapped_column(String(60))
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Zona(Base):
    __tablename__ = "zonas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(40))


class CondicionVenta(Base):
    __tablename__ = "condiciones_venta"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    descripcion: Mapped[str] = mapped_column(String(60))
    dias: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=[0])
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    entidad_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entidades.id"))
    codigo: Mapped[str | None] = mapped_column(String(10))
    lista_precios: Mapped[int] = mapped_column(SmallInteger, default=1)
    condicion_venta_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("condiciones_venta.id"))
    zona_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zonas.id"))
    descuento: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    limite_credito: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    observaciones: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    entidad: Mapped[Entidad] = relationship(lazy="joined")
