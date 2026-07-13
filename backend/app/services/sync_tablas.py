"""Registro de tablas de la réplica de bajada nube → nodo (F13-LAN N1).

Diseño en DISENO-NODO-LAN.md §5: "la nube manda" para maestros. Tres modos:

- ``incremental``: checkpoint por ``updated_at`` (confiable a nivel DB: la
  migración 023 le pone trigger BEFORE UPDATE a estas tablas). Para volúmenes
  grandes (entidades, clientes, artículos, variantes). Los maestros se
  inactivan (``activo=false``) y eso viaja como update — sin deletes.
- ``snapshot``: tabla completa del tenant en cada ciclo, con poda de filas que
  ya no existen en la nube. Para tablas chicas y para las que sufren HARD
  deletes (``roles``/``rol_permisos`` en la matriz de permisos, colecciones
  reemplazadas de domicilios/contactos).
- ``inicial``: se baja UNA vez al aparejar (semilla) y no se vuelve a tocar:
  el nodo pasa a ser autoridad local (stock de su depósito, numeración de sus
  PV exclusivos). Reaplicar pisaría el avance local.

El ORDEN de la lista respeta las FKs para el upsert; la poda de snapshots se
corre en orden INVERSO (el nodo la hace en una segunda pasada).
"""

import datetime as dt
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from app.models import (
    ArcaConfig,
    Articulo,
    ArticuloStock,
    ArticuloVariante,
    Atributo,
    AtributoValor,
    Cliente,
    CondicionVenta,
    Cotizacion,
    Deposito,
    Entidad,
    EntidadContacto,
    EntidadDomicilio,
    Familia,
    Marca,
    Numeracion,
    PosBalanzaConfig,
    PosCaja,
    PosMesa,
    PosSalon,
    Proveedor,
    Provincia,
    PuntoVenta,
    Rol,
    RolPermiso,
    Subfamilia,
    Sucursal,
    Tenant,
    TipoComprobante,
    Unidad,
    Usuario,
    Vendedor,
    Zona,
)


@dataclass(frozen=True)
class TablaSync:
    nombre: str
    modelo: type
    modo: str  # "snapshot" | "incremental" | "inicial"
    es_global: bool = False  # catálogo sin tenant_id (provincias, tipos_comprobante)


# Orden por dependencias FK (upsert de arriba hacia abajo; poda al revés).
TABLAS_SYNC: list[TablaSync] = [
    TablaSync("tenants", Tenant, "snapshot"),
    TablaSync("provincias", Provincia, "snapshot", es_global=True),
    TablaSync("tipos_comprobante", TipoComprobante, "snapshot", es_global=True),
    TablaSync("sucursales", Sucursal, "snapshot"),
    TablaSync("roles", Rol, "snapshot"),
    TablaSync("rol_permisos", RolPermiso, "snapshot"),
    TablaSync("usuarios", Usuario, "snapshot"),
    TablaSync("puntos_venta", PuntoVenta, "snapshot"),
    TablaSync("zonas", Zona, "snapshot"),
    TablaSync("condiciones_venta", CondicionVenta, "snapshot"),
    TablaSync("entidades", Entidad, "incremental"),
    TablaSync("entidad_domicilios", EntidadDomicilio, "snapshot"),
    TablaSync("entidad_contactos", EntidadContacto, "snapshot"),
    TablaSync("proveedores", Proveedor, "snapshot"),
    TablaSync("vendedores", Vendedor, "snapshot"),
    TablaSync("clientes", Cliente, "incremental"),
    TablaSync("familias", Familia, "snapshot"),
    TablaSync("subfamilias", Subfamilia, "snapshot"),
    TablaSync("marcas", Marca, "snapshot"),
    TablaSync("unidades", Unidad, "snapshot"),
    TablaSync("depositos", Deposito, "snapshot"),
    TablaSync("cotizaciones", Cotizacion, "snapshot"),
    TablaSync("atributos", Atributo, "snapshot"),
    TablaSync("atributo_valores", AtributoValor, "snapshot"),
    TablaSync("articulos", Articulo, "incremental"),
    TablaSync("articulo_variantes", ArticuloVariante, "incremental"),
    TablaSync("articulo_stock", ArticuloStock, "inicial"),
    TablaSync("numeracion", Numeracion, "inicial"),
    TablaSync("pos_cajas", PosCaja, "snapshot"),
    TablaSync("pos_balanza_config", PosBalanzaConfig, "snapshot"),
    TablaSync("pos_salones", PosSalon, "snapshot"),
    TablaSync("pos_mesas", PosMesa, "snapshot"),
    TablaSync("arca_config", ArcaConfig, "snapshot"),
]

POR_NOMBRE: dict[str, TablaSync] = {t.nombre: t for t in TABLAS_SYNC}


def columnas(modelo: type) -> dict[str, object]:
    """{nombre_attr: Column} del modelo (attr y columna comparten nombre en ZGC)."""
    return {c.key: c for c in sa_inspect(modelo).columns}


def pk_columnas(modelo: type) -> list[str]:
    return [c.key for c in sa_inspect(modelo).primary_key]


def serializar_fila(modelo: type, obj) -> dict:
    """ORM → dict JSON-friendly (UUID/Decimal → str, fechas → ISO)."""
    fila: dict = {}
    for key in columnas(modelo):
        valor = getattr(obj, key)
        if isinstance(valor, uuid.UUID):
            valor = str(valor)
        elif isinstance(valor, Decimal):
            valor = str(valor)
        elif isinstance(valor, dt.datetime | dt.date):
            valor = valor.isoformat()
        fila[key] = valor
    return fila


def fila_a_python(modelo: type, fila: dict) -> dict:
    """JSON → tipos que asyncpg acepta, según el tipo de cada columna del
    modelo (SQLAlchemy no parsea strings para DateTime/Numeric en asyncpg)."""
    cols = columnas(modelo)
    out: dict = {}
    for key, valor in fila.items():
        col = cols.get(key)
        if col is None or valor is None:
            out[key] = valor
            continue
        tipo = col.type
        if isinstance(tipo, DateTime) and isinstance(valor, str):
            valor = dt.datetime.fromisoformat(valor)
        elif isinstance(tipo, Date) and isinstance(valor, str):
            valor = dt.date.fromisoformat(valor)
        elif isinstance(tipo, Numeric) and isinstance(valor, str):
            valor = Decimal(valor)
        elif isinstance(tipo, PgUUID) and isinstance(valor, str):
            valor = uuid.UUID(valor)
        out[key] = valor
    return out
