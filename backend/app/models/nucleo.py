import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    razon_social: Mapped[str] = mapped_column(String(80))
    nombre_fantasia: Mapped[str | None] = mapped_column(String(80))
    cuit: Mapped[str | None] = mapped_column(String(11))
    condicion_iva: Mapped[str] = mapped_column(String(2), default="RI")
    email: Mapped[str | None] = mapped_column(String(120))
    telefono: Mapped[str | None] = mapped_column(String(40))
    domicilio: Mapped[str | None] = mapped_column(String(120))
    localidad: Mapped[str | None] = mapped_column(String(60))
    provincia: Mapped[str | None] = mapped_column(String(40))
    codigo_postal: Mapped[str | None] = mapped_column(String(10))
    rubro: Mapped[str] = mapped_column(String(30), default="general")
    # Plan comercial (F12-a, POS standalone): 'suite' = todos los módulos;
    # 'pos' = licencia solo-POS (catálogo PLANES en core/permisos.py). Lo fija
    # ZARIS al vender (v1 por script/SQL); la UI lo muestra read-only.
    plan: Mapped[str] = mapped_column(String(20), default="suite")
    # Sesgo geográfico opcional para el proxy Nominatim (viewbox SIN bounded=1).
    # NULL = sin sesgo: resultados de todo el país.
    geo_centro_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geo_centro_lon: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geo_delta_grados: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Sucursal(Base):
    __tablename__ = "sucursales"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(60))
    domicilio: Mapped[str | None] = mapped_column(String(120))
    localidad: Mapped[str | None] = mapped_column(String(60))
    provincia_id: Mapped[int | None] = mapped_column(ForeignKey("provincias.codigo_arca"))
    codigo_postal: Mapped[str | None] = mapped_column(String(10))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    telefono: Mapped[str | None] = mapped_column(String(40))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    nombre: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(100))
    nivel_acceso: Mapped[int] = mapped_column(SmallInteger, default=1)
    # rol_id NULL = acceso total (compat: usuarios creados por scripts/SQL).
    # nivel_acceso sigue gobernando SOLO la autorización de supervisor del POS.
    rol_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("roles.id"))
    sucursal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sucursales.id"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(30))
    nombre: Mapped[str] = mapped_column(String(60))
    es_sistema: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SucursalNodo(Base):
    """Nodo LAN apareado a una sucursal (F13-LAN N1 — DISENO-NODO-LAN.md §3).
    El token de aparejamiento se muestra UNA vez al crear/regenerar; acá vive
    solo su hash bcrypt. `punto_venta_id` = PV propio del nodo para la
    facturación de gestión (§0-bis); mientras el nodo esté activo, ese PV y
    los de las cajas POS de su sucursal son exclusivos del nodo."""

    __tablename__ = "sucursal_nodos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    sucursal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sucursales.id"))
    nombre: Mapped[str] = mapped_column(String(60))
    token_hash: Mapped[str] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(8), default="activo")
    punto_venta_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("puntos_venta.id"))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version_app: Mapped[str | None] = mapped_column(String(20))
    # monitoreo N2: atraso reportado por el ping del ciclo (0 = al día)
    subida_pendientes: Mapped[int] = mapped_column(Integer, default=0)
    cae_pendientes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyncCheckpoint(Base):
    """Checkpoint de réplica por tabla — vive SOLO en la base local del nodo
    (en la nube queda vacía). La fila especial '_nodo' guarda en `extra` el
    contexto del aparejamiento (sucursal, PV propio) para arrancar offline."""

    __tablename__ = "sync_checkpoints"

    tabla: Mapped[str] = mapped_column(Text, primary_key=True)
    hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filas: Mapped[int] = mapped_column(BigInteger, default=0)
    extra: Mapped[dict | None] = mapped_column(JSONB)
    actualizado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    rol_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    modulo: Mapped[str] = mapped_column(String(20), primary_key=True)
    accion: Mapped[str] = mapped_column(String(10))
