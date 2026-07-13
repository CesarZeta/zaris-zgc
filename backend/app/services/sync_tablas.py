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
    Comprobante,
    ComprobanteAlicuota,
    ComprobanteItem,
    ComprobanteVencimiento,
    CondicionVenta,
    Cotizacion,
    Deposito,
    Entidad,
    EntidadContacto,
    EntidadDomicilio,
    Familia,
    Imputacion,
    Marca,
    Numeracion,
    PosBalanzaConfig,
    PosCaja,
    PosMesa,
    PosSalon,
    PosSesion,
    Proveedor,
    Provincia,
    PuntoVenta,
    Recibo,
    ReciboMedio,
    Rol,
    RolPermiso,
    StockMovimiento,
    Subfamilia,
    Sucursal,
    Tenant,
    TipoComprobante,
    Unidad,
    Usuario,
    Vendedor,
    VentaMedio,
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


# ===== Subida nodo → nube (N2, "el origen manda") =====
#
# El outbox SON las tablas transaccionales: todas sus filas nacen en el nodo
# (las transacciones nunca replican hacia abajo) y el UUID es la clave de
# idempotencia — no hace falta una cola de eventos aparte (evita el
# doble-write transacción+evento). Checkpoint por tabla:
#   mutable=True  → filtro por updated_at (trigger de la 024) y upsert LWW
#                   en la nube (solo pisa si el updated_at entrante es ≥).
#   mutable=False → insert-only: filtro por created_at y DO NOTHING.
# La paginación SIEMPRE es keyset por (created_at, id): created_at es
# inmutable (páginas estables aunque cambie updated_at a mitad de la pasada)
# y ordena padres antes que hijos en los self-FK (una NC espejo nunca llega
# a la nube antes que su factura asociada).
#
# `hijos`: filas sin timestamps propios (items/alícuotas/vencimientos/medios
# de recibo) viajan ANIDADAS con su padre en cada re-subida; la nube las
# inserta DO NOTHING (inmutables). `efecto_stock`: el agregado articulo_stock
# de la nube NO se pisa — se le aplica el delta de cada movimiento NUEVO
# (exactamente una vez, vía RETURNING del insert).


@dataclass(frozen=True)
class TablaSubida:
    nombre: str
    modelo: type
    mutable: bool
    hijos: tuple = ()  # (nombre_tabla, modelo, fk_attr) — anidados con el padre
    excluir: frozenset = frozenset()  # columnas que no viajan (XML deferred)
    efecto_stock: bool = False  # delta sobre articulo_stock al insertar en nube
    # filtro extra del lado nodo: los borradores no viajan (pueden borrarse)
    solo_no_borrador: bool = False


TABLAS_SUBIDA: list[TablaSubida] = [
    TablaSubida("pos_sesiones", PosSesion, mutable=True),
    TablaSubida(
        "comprobantes",
        Comprobante,
        mutable=True,
        hijos=(
            ("comprobante_items", ComprobanteItem, "comprobante_id"),
            ("comprobante_alicuotas", ComprobanteAlicuota, "comprobante_id"),
            ("comprobante_vencimientos", ComprobanteVencimiento, "comprobante_id"),
        ),
        # los XML de WSFEv1 quedan como auditoría local del nodo (deferred +
        # pesados; leerlos acá exigiría undefer en cada pasada)
        excluir=frozenset({"arca_request", "arca_response"}),
        solo_no_borrador=True,
    ),
    TablaSubida("venta_medios", VentaMedio, mutable=False),
    TablaSubida(
        "recibos", Recibo, mutable=True,
        hijos=(("recibo_medios", ReciboMedio, "recibo_id"),),
    ),
    TablaSubida("imputaciones", Imputacion, mutable=True),
    TablaSubida("stock_movimientos", StockMovimiento, mutable=False, efecto_stock=True),
    # espejo LWW de la numeración del nodo: la nube retoma la secuencia sola
    # al revocar (las filas de PVs de la nube que vinieron en la semilla viajan
    # con updated_at viejo y el LWW impide pisar valores más nuevos)
    TablaSubida("numeracion", Numeracion, mutable=True),
]

SUBIDA_POR_NOMBRE: dict[str, TablaSubida] = {t.nombre: t for t in TABLAS_SUBIDA}


def columnas(modelo: type) -> dict[str, object]:
    """{nombre_attr: Column} del modelo (attr y columna comparten nombre en ZGC)."""
    return {c.key: c for c in sa_inspect(modelo).columns}


def pk_columnas(modelo: type) -> list[str]:
    return [c.key for c in sa_inspect(modelo).primary_key]


def serializar_fila(modelo: type, obj, excluir: frozenset = frozenset()) -> dict:
    """ORM → dict JSON-friendly (UUID/Decimal → str, fechas → ISO)."""
    fila: dict = {}
    for key in columnas(modelo):
        if key in excluir:
            continue
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
