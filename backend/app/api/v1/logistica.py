"""F12-bis — Logística de entregas. Diseño en docs/DISENO-LOGISTICA-Y-DOMICILIOS.md §2.

Rol transportista sobre la BUE (patrón vendedores.py) + entregas con domicilio
SNAPSHOT + hojas de ruta. Regla de encuadre: el estado de entrega NO toca el
circuito fiscal ni la cta. cte. — una entrega rechazada se resuelve
comercialmente (NC, re-entrega) por los módulos existentes.

Estados de entrega: pendiente → asignada (en hoja) → en_reparto (despachada) →
entregada | rechazada (rendición); reprogramada = terminal, la reemplaza una
entrega nueva. Hoja: abierta → en_reparto → cerrada; anulable solo abierta.

Rutas estáticas ANTES de las paramétricas (regla §6). RBAC `logistica`:
GET=ver, escritura/rendición=editar, anulaciones=anular.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.clientes import EntidadIn, _validar_entidad
from app.api.v1.entidades import EntidadOut, aplicar_busqueda
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    Cliente,
    Comprobante,
    Entidad,
    EntidadDomicilio,
    Entrega,
    HojaRuta,
    PuntoVenta,
    Sucursal,
    TipoComprobante,
    Transportista,
    Usuario,
)

router = APIRouter(prefix="/logistica", tags=["logistica"])

# clases de comprobante que se reparten (diseño §2.1: remito o factura)
CLASES_ENTREGABLES = ("factura", "remito")
# estados de entrega que OCUPAN el comprobante (espejo del unique parcial 025)
ESTADOS_VIVOS = ("pendiente", "asignada", "en_reparto", "entregada")
ESTADOS_RENDIDOS = ("entregada", "rechazada", "reprogramada")


# ===== Schemas =====

class TransportistaIn(BaseModel):
    # BUE: o se referencia una entidad existente, o se crea una nueva — nunca ambas
    entidad_id: uuid.UUID | None = None
    entidad: EntidadIn | None = None
    codigo: str | None = Field(None, max_length=10)
    vehiculo: str | None = Field(None, max_length=60)
    dominio: str | None = Field(None, max_length=15)
    observaciones: str | None = Field(None, max_length=200)


class TransportistaUpdate(BaseModel):
    codigo: str | None = None
    vehiculo: str | None = None
    dominio: str | None = None
    observaciones: str | None = None
    activo: bool | None = None
    entidad: EntidadIn | None = None  # actualiza también los datos maestros


class TransportistaOut(BaseModel):
    id: uuid.UUID
    codigo: str | None
    vehiculo: str | None
    dominio: str | None
    observaciones: str | None
    activo: bool
    entidad: EntidadOut
    model_config = {"from_attributes": True}


class EntregaIn(BaseModel):
    comprobante_id: uuid.UUID
    # snapshot del destino: domicilio de entidad_domicilios O texto libre;
    # sin ambos, el server resuelve (predeterminado de entrega → fiscal)
    domicilio_entidad_id: uuid.UUID | None = None
    domicilio: str | None = Field(None, max_length=180)
    localidad: str | None = Field(None, max_length=60)
    telefono: str | None = Field(None, max_length=30)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    fecha_programada: date | None = None
    transportista_id: uuid.UUID | None = None
    bultos: str | None = Field(None, max_length=60)
    observaciones: str | None = Field(None, max_length=200)


class EntregaOut(BaseModel):
    id: uuid.UUID
    comprobante_id: uuid.UUID
    comprobante_desc: str = ""
    fecha_comprobante: date | None = None
    total_comprobante: Decimal | None = None
    destinatario: str
    domicilio: str
    localidad: str | None
    telefono: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    fecha_programada: date | None
    transportista_id: uuid.UUID | None
    transportista_nombre: str = ""
    hoja_ruta_id: uuid.UUID | None
    hoja_numero: int | None = None
    orden: int
    estado: str
    bultos: str | None
    recibido_por: str | None
    motivo_rechazo: str | None
    observaciones: str | None
    rendida_at: datetime | None
    anulada: bool = False


class RendirIn(BaseModel):
    resultado: str = Field(pattern="^(entregada|rechazada)$")
    recibido_por: str | None = Field(None, max_length=80)
    motivo_rechazo: str | None = Field(None, max_length=200)


class HojaIn(BaseModel):
    transportista_id: uuid.UUID
    fecha: date | None = None
    sucursal_id: uuid.UUID | None = None
    observaciones: str | None = Field(None, max_length=200)
    entrega_ids: list[uuid.UUID] = []


class HojaUpdate(BaseModel):
    transportista_id: uuid.UUID | None = None
    fecha: date | None = None
    observaciones: str | None = None
    entrega_ids: list[uuid.UUID] | None = None  # reemplaza el conjunto (solo abierta)


class HojaListaOut(BaseModel):
    id: uuid.UUID
    numero: int
    numero_formateado: str
    fecha: date
    transportista_id: uuid.UUID
    transportista_nombre: str = ""
    sucursal_id: uuid.UUID | None
    estado: str
    observaciones: str | None
    cantidad_entregas: int = 0
    anulada: bool = False


class HojaOut(HojaListaOut):
    entregas: list[EntregaOut] = []


class EntregableOut(BaseModel):
    comprobante_id: uuid.UUID
    fecha: date
    descripcion: str
    receptor_nombre: str
    receptor_domicilio: str | None
    cliente_id: uuid.UUID | None
    entidad_id: uuid.UUID | None = None
    total: Decimal


# ===== Helpers =====

async def _transportista(db: AsyncSession, tenant_id: uuid.UUID, tid: uuid.UUID) -> Transportista:
    t = await db.scalar(
        select(Transportista).where(Transportista.id == tid, Transportista.tenant_id == tenant_id)
    )
    if t is None:
        raise HTTPException(status_code=404, detail="Transportista no encontrado")
    return t


async def _nombres_transportistas(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    filas = (
        await db.execute(
            select(Transportista.id, Entidad.razon_social)
            .join(Entidad, Transportista.entidad_id == Entidad.id)
            .where(Transportista.tenant_id == tenant_id)
        )
    ).all()
    return dict(filas)


async def _contexto_entregas(db: AsyncSession, entregas: list[Entrega]) -> tuple[dict, dict]:
    """Descripciones de comprobante y números de hoja SIN cargar los ORM pesados
    (listados livianos, regla §6): select de columnas."""
    comp_ids = {e.comprobante_id for e in entregas}
    comps: dict = {}
    if comp_ids:
        filas = (
            await db.execute(
                select(
                    Comprobante.id,
                    Comprobante.tipo_codigo,
                    Comprobante.numero,
                    Comprobante.fecha,
                    Comprobante.total,
                    PuntoVenta.numero.label("pv"),
                )
                .join(PuntoVenta, Comprobante.punto_venta_id == PuntoVenta.id)
                .where(Comprobante.id.in_(comp_ids))
            )
        ).all()
        comps = {f.id: f for f in filas}
    hoja_ids = {e.hoja_ruta_id for e in entregas if e.hoja_ruta_id}
    hojas: dict = {}
    if hoja_ids:
        filas = (await db.execute(select(HojaRuta.id, HojaRuta.numero).where(HojaRuta.id.in_(hoja_ids)))).all()
        hojas = dict(filas)
    return comps, hojas


def _entrega_out(e: Entrega, comps: dict, hojas: dict, nombres: dict) -> EntregaOut:
    c = comps.get(e.comprobante_id)
    return EntregaOut(
        id=e.id,
        comprobante_id=e.comprobante_id,
        comprobante_desc=f"{c.tipo_codigo} {c.pv:04d}-{(c.numero or 0):08d}" if c else "",
        fecha_comprobante=c.fecha if c else None,
        total_comprobante=c.total if c else None,
        destinatario=e.destinatario,
        domicilio=e.domicilio,
        localidad=e.localidad,
        telefono=e.telefono,
        latitud=e.latitud,
        longitud=e.longitud,
        fecha_programada=e.fecha_programada,
        transportista_id=e.transportista_id,
        transportista_nombre=nombres.get(e.transportista_id, ""),
        hoja_ruta_id=e.hoja_ruta_id,
        hoja_numero=hojas.get(e.hoja_ruta_id),
        orden=e.orden,
        estado=e.estado,
        bultos=e.bultos,
        recibido_por=e.recibido_por,
        motivo_rechazo=e.motivo_rechazo,
        observaciones=e.observaciones,
        rendida_at=e.rendida_at,
        anulada=e.anulado_at is not None,
    )


def _hoja_out(h: HojaRuta, nombres: dict, con_entregas: bool = False, comps: dict | None = None, hojas: dict | None = None):
    base = dict(
        id=h.id,
        numero=h.numero,
        numero_formateado=f"HR-{h.numero:08d}",
        fecha=h.fecha,
        transportista_id=h.transportista_id,
        transportista_nombre=nombres.get(h.transportista_id, ""),
        sucursal_id=h.sucursal_id,
        estado=h.estado,
        observaciones=h.observaciones,
        cantidad_entregas=len(h.entregas),
        anulada=h.anulado_at is not None,
    )
    if not con_entregas:
        return HojaListaOut(**base)
    return HojaOut(
        **base,
        entregas=[_entrega_out(e, comps or {}, hojas or {}, nombres) for e in h.entregas],
    )


async def _entrega(db: AsyncSession, tenant_id: uuid.UUID, entrega_id: uuid.UUID) -> Entrega:
    e = await db.scalar(
        select(Entrega).where(Entrega.id == entrega_id, Entrega.tenant_id == tenant_id)
    )
    if e is None:
        raise HTTPException(status_code=404, detail="Entrega no encontrada")
    return e


async def _hoja(db: AsyncSession, tenant_id: uuid.UUID, hoja_id: uuid.UUID) -> HojaRuta:
    h = await db.scalar(
        select(HojaRuta).where(HojaRuta.id == hoja_id, HojaRuta.tenant_id == tenant_id)
    )
    if h is None:
        raise HTTPException(status_code=404, detail="Hoja de ruta no encontrada")
    return h


# ===== Transportistas (rol BUE, patrón vendedores) =====

@router.post("/transportistas", response_model=TransportistaOut, status_code=status.HTTP_201_CREATED)
async def crear_transportista(
    body: TransportistaIn,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if (body.entidad_id is None) == (body.entidad is None):
        raise HTTPException(
            status_code=422,
            detail="Indicar entidad_id (existente) O entidad (nueva), no ambas",
        )
    if body.entidad is not None:
        datos = _validar_entidad(body.entidad)
        entidad = Entidad(tenant_id=usuario.tenant_id, **datos.model_dump())
        db.add(entidad)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Ya existe una entidad con ese documento en la empresa (BUE: reusarla via entidad_id)",
            )
        entidad_id = entidad.id
    else:
        entidad = await db.scalar(
            select(Entidad).where(
                Entidad.id == body.entidad_id, Entidad.tenant_id == usuario.tenant_id
            )
        )
        if entidad is None:
            raise HTTPException(status_code=404, detail="Entidad no encontrada")
        entidad_id = entidad.id

    t = Transportista(
        tenant_id=usuario.tenant_id,
        entidad_id=entidad_id,
        codigo=(body.codigo or "").strip() or None,
        vehiculo=(body.vehiculo or "").strip() or None,
        dominio=(body.dominio or "").strip() or None,
        observaciones=(body.observaciones or "").strip() or None,
    )
    db.add(t)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="La entidad ya es transportista, o el código ya está en uso"
        )
    t = await db.scalar(select(Transportista).where(Transportista.id == t.id))
    return TransportistaOut.model_validate(t)


@router.get("/transportistas", response_model=list[TransportistaOut])
async def listar_transportistas(
    response: Response,
    q: str = "",
    incluir_inactivos: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("logistica", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Transportista)
        .join(Entidad, Transportista.entidad_id == Entidad.id)
        .where(Transportista.tenant_id == usuario.tenant_id)
    )
    if not incluir_inactivos:
        stmt = stmt.where(Transportista.activo)
    stmt = aplicar_busqueda(stmt, q)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    stmt = stmt.order_by(Entidad.razon_social).limit(min(limit, 200)).offset(offset)
    filas = (await db.scalars(stmt)).unique().all()
    return [TransportistaOut.model_validate(t) for t in filas]


@router.get("/transportistas/{transportista_id}", response_model=TransportistaOut)
async def obtener_transportista(
    transportista_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return TransportistaOut.model_validate(
        await _transportista(db, usuario.tenant_id, transportista_id)
    )


@router.put("/transportistas/{transportista_id}", response_model=TransportistaOut)
async def actualizar_transportista(
    transportista_id: uuid.UUID,
    body: TransportistaUpdate,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    t = await _transportista(db, usuario.tenant_id, transportista_id)
    cambios = body.model_dump(exclude_unset=True, exclude={"entidad"})
    for campo, valor in cambios.items():
        setattr(t, campo, valor)
    t.updated_at = func.now()
    if body.entidad is not None:
        datos = _validar_entidad(body.entidad)
        entidad = t.entidad
        for campo, valor in datos.model_dump().items():
            setattr(entidad, campo, valor)
        entidad.updated_at = func.now()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Conflicto de unicidad (código o documento ya en uso)"
        )
    t = await db.scalar(select(Transportista).where(Transportista.id == transportista_id))
    return TransportistaOut.model_validate(t)


# ===== Comprobantes entregables (para "crear entrega" en la UI) =====

@router.get("/entregables", response_model=list[EntregableOut])
async def listar_entregables(
    q: str = "",
    dias: int = 60,
    limit: int = 50,
    usuario: Usuario = Depends(requiere("logistica", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Facturas y remitos EMITIDOS de los últimos `dias` sin entrega viva."""
    ocupados = select(Entrega.comprobante_id).where(
        Entrega.tenant_id == usuario.tenant_id,
        Entrega.anulado_at.is_(None),
        Entrega.estado.in_(ESTADOS_VIVOS),
    )
    stmt = (
        select(
            Comprobante.id,
            Comprobante.tipo_codigo,
            Comprobante.numero,
            Comprobante.fecha,
            Comprobante.total,
            Comprobante.receptor_nombre,
            Comprobante.receptor_domicilio,
            Comprobante.cliente_id,
            Cliente.entidad_id,
            PuntoVenta.numero.label("pv"),
        )
        .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
        .join(PuntoVenta, Comprobante.punto_venta_id == PuntoVenta.id)
        .join(Cliente, Comprobante.cliente_id == Cliente.id, isouter=True)
        .where(
            Comprobante.tenant_id == usuario.tenant_id,
            Comprobante.estado == "emitido",
            TipoComprobante.clase.in_(CLASES_ENTREGABLES),
            Comprobante.fecha >= func.current_date() - dias,
            Comprobante.id.notin_(ocupados),
        )
        .order_by(Comprobante.fecha.desc(), Comprobante.numero.desc())
        .limit(min(limit, 200))
    )
    q = (q or "").strip()
    if q:
        if q.replace("-", "").isdigit():
            stmt = stmt.where(Comprobante.numero == int(q.replace("-", "").lstrip("0") or 0))
        else:
            for palabra in q.split():
                stmt = stmt.where(Comprobante.receptor_nombre.ilike(f"%{palabra}%"))
    filas = (await db.execute(stmt)).all()
    return [
        EntregableOut(
            comprobante_id=f.id,
            fecha=f.fecha,
            descripcion=f"{f.tipo_codigo} {f.pv:04d}-{(f.numero or 0):08d}",
            receptor_nombre=f.receptor_nombre,
            receptor_domicilio=f.receptor_domicilio,
            cliente_id=f.cliente_id,
            entidad_id=f.entidad_id,
            total=f.total,
        )
        for f in filas
    ]


# ===== Entregas =====

@router.post("/entregas", response_model=EntregaOut, status_code=status.HTTP_201_CREATED)
async def crear_entrega(
    body: EntregaIn,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    fila = (
        await db.execute(
            select(Comprobante.id, Comprobante.estado, Comprobante.receptor_nombre,
                   Comprobante.receptor_domicilio, Comprobante.cliente_id, TipoComprobante.clase)
            .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
            .where(Comprobante.id == body.comprobante_id, Comprobante.tenant_id == usuario.tenant_id)
        )
    ).first()
    if fila is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if fila.clase not in CLASES_ENTREGABLES:
        raise HTTPException(status_code=422, detail="Solo se reparten facturas y remitos")
    if fila.estado != "emitido":
        raise HTTPException(status_code=422, detail="El comprobante debe estar emitido")
    ocupado = await db.scalar(
        select(Entrega.id).where(
            Entrega.comprobante_id == body.comprobante_id,
            Entrega.anulado_at.is_(None),
            Entrega.estado.in_(ESTADOS_VIVOS),
        )
    )
    if ocupado is not None:
        raise HTTPException(status_code=409, detail="El comprobante ya tiene una entrega activa")

    if body.transportista_id is not None:
        await _transportista(db, usuario.tenant_id, body.transportista_id)

    # ---- snapshot del destino: body > domicilio elegido > predeterminado de
    # entrega > fiscal de la entidad > receptor del comprobante ----
    entidad: Entidad | None = None
    if fila.cliente_id is not None:
        entidad = await db.scalar(
            select(Entidad)
            .join(Cliente, Cliente.entidad_id == Entidad.id)
            .where(Cliente.id == fila.cliente_id)
        )
    domicilio = (body.domicilio or "").strip() or None
    localidad = (body.localidad or "").strip() or None
    latitud, longitud = body.latitud, body.longitud
    if domicilio is None and body.domicilio_entidad_id is not None:
        d = await db.scalar(
            select(EntidadDomicilio).where(
                EntidadDomicilio.id == body.domicilio_entidad_id,
                EntidadDomicilio.tenant_id == usuario.tenant_id,
            )
        )
        if d is None or (entidad is not None and d.entidad_id != entidad.id):
            raise HTTPException(status_code=404, detail="Domicilio de entidad no encontrado")
        domicilio, localidad = d.domicilio, d.localidad
        latitud, longitud = d.latitud, d.longitud
    if domicilio is None and entidad is not None:
        d = await db.scalar(
            select(EntidadDomicilio).where(
                EntidadDomicilio.entidad_id == entidad.id,
                EntidadDomicilio.tipo == "entrega",
                EntidadDomicilio.predeterminado.is_(True),
                EntidadDomicilio.activo.is_(True),
            )
        )
        if d is not None:
            domicilio, localidad = d.domicilio, d.localidad
            latitud, longitud = d.latitud, d.longitud
        elif entidad.domicilio:
            domicilio, localidad = entidad.domicilio, entidad.localidad
            latitud, longitud = entidad.latitud, entidad.longitud
    if domicilio is None:
        domicilio = fila.receptor_domicilio
    if not domicilio:
        raise HTTPException(
            status_code=422,
            detail="El destino no tiene domicilio: indicarlo en la entrega o cargarlo en la entidad",
        )

    e = Entrega(
        tenant_id=usuario.tenant_id,
        comprobante_id=body.comprobante_id,
        destinatario=fila.receptor_nombre,
        domicilio=domicilio,
        localidad=localidad,
        telefono=(body.telefono or "").strip() or (entidad.telefono_1 if entidad else None),
        latitud=latitud,
        longitud=longitud,
        fecha_programada=body.fecha_programada,
        transportista_id=body.transportista_id,
        bultos=(body.bultos or "").strip() or None,
        observaciones=(body.observaciones or "").strip() or None,
        creado_por=usuario.id,
    )
    db.add(e)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El comprobante ya tiene una entrega activa")
    e = await db.scalar(select(Entrega).where(Entrega.id == e.id))
    comps, hojas = await _contexto_entregas(db, [e])
    return _entrega_out(e, comps, hojas, await _nombres_transportistas(db, usuario.tenant_id))


@router.get("/entregas", response_model=list[EntregaOut])
async def listar_entregas(
    response: Response,
    estado: str = "",
    transportista_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str = "",
    incluir_anuladas: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("logistica", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Entrega).where(Entrega.tenant_id == usuario.tenant_id)
    if estado:
        stmt = stmt.where(Entrega.estado == estado)
    if transportista_id:
        stmt = stmt.where(Entrega.transportista_id == transportista_id)
    if desde:
        stmt = stmt.where(Entrega.created_at >= desde)
    if hasta:
        stmt = stmt.where(func.date(Entrega.created_at) <= hasta)
    if not incluir_anuladas:
        stmt = stmt.where(Entrega.anulado_at.is_(None))
    q = (q or "").strip()
    for palabra in q.split():
        stmt = stmt.where(
            Entrega.destinatario.ilike(f"%{palabra}%") | Entrega.domicilio.ilike(f"%{palabra}%")
        )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = (
        await db.scalars(stmt.order_by(Entrega.created_at.desc()).limit(min(limit, 200)).offset(offset))
    ).all()
    comps, hojas = await _contexto_entregas(db, filas)
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    return [_entrega_out(e, comps, hojas, nombres) for e in filas]


@router.get("/entregas/{entrega_id}", response_model=EntregaOut)
async def obtener_entrega(
    entrega_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "ver")),
    db: AsyncSession = Depends(get_db),
):
    e = await _entrega(db, usuario.tenant_id, entrega_id)
    comps, hojas = await _contexto_entregas(db, [e])
    return _entrega_out(e, comps, hojas, await _nombres_transportistas(db, usuario.tenant_id))


@router.post("/entregas/{entrega_id}/rendir", response_model=EntregaOut)
async def rendir_entrega(
    entrega_id: uuid.UUID,
    body: RendirIn,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Marca el resultado del reparto. Vale desde en_reparto (rendición de la
    hoja) y también desde pendiente/asignada (entrega directa sin hoja)."""
    e = await _entrega(db, usuario.tenant_id, entrega_id)
    if e.anulado_at is not None or e.estado not in ("pendiente", "asignada", "en_reparto"):
        raise HTTPException(status_code=422, detail=f"La entrega no admite rendición (estado: {e.estado})")
    if body.resultado == "rechazada" and not (body.motivo_rechazo or "").strip():
        raise HTTPException(status_code=422, detail="Indicar el motivo del rechazo")
    e.estado = body.resultado
    e.recibido_por = (body.recibido_por or "").strip() or None
    e.motivo_rechazo = (body.motivo_rechazo or "").strip() or None
    e.rendida_at = datetime.now(timezone.utc)
    e.updated_at = func.now()
    await db.commit()
    e = await db.scalar(select(Entrega).where(Entrega.id == entrega_id))
    comps, hojas = await _contexto_entregas(db, [e])
    return _entrega_out(e, comps, hojas, await _nombres_transportistas(db, usuario.tenant_id))


@router.post("/entregas/{entrega_id}/reprogramar", response_model=EntregaOut, status_code=status.HTTP_201_CREATED)
async def reprogramar_entrega(
    entrega_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Una entrega RECHAZADA se reintenta con una entrega NUEVA (la historia
    del rechazo queda intacta; la vieja pasa a reprogramada)."""
    e = await _entrega(db, usuario.tenant_id, entrega_id)
    if e.anulado_at is not None or e.estado != "rechazada":
        raise HTTPException(status_code=422, detail="Solo se reprograma una entrega rechazada")
    e.estado = "reprogramada"
    e.updated_at = func.now()
    nueva = Entrega(
        tenant_id=e.tenant_id,
        comprobante_id=e.comprobante_id,
        destinatario=e.destinatario,
        domicilio=e.domicilio,
        localidad=e.localidad,
        telefono=e.telefono,
        latitud=e.latitud,
        longitud=e.longitud,
        transportista_id=e.transportista_id,
        bultos=e.bultos,
        observaciones=e.observaciones,
        creado_por=usuario.id,
    )
    db.add(nueva)
    await db.commit()
    nueva = await db.scalar(select(Entrega).where(Entrega.id == nueva.id))
    comps, hojas = await _contexto_entregas(db, [nueva])
    return _entrega_out(nueva, comps, hojas, await _nombres_transportistas(db, usuario.tenant_id))


@router.post("/entregas/{entrega_id}/anular", response_model=EntregaOut)
async def anular_entrega(
    entrega_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "anular")),
    db: AsyncSession = Depends(get_db),
):
    """Anular = marcar (contrato 014). Solo pendiente/asignada — lo despachado
    se rinde, no se anula. Si estaba en una hoja abierta, se la quita."""
    e = await _entrega(db, usuario.tenant_id, entrega_id)
    if e.anulado_at is not None or e.estado not in ("pendiente", "asignada"):
        raise HTTPException(status_code=422, detail=f"La entrega no se puede anular (estado: {e.estado})")
    e.anulado_at = datetime.now(timezone.utc)
    e.anulado_por = usuario.id
    e.hoja_ruta_id = None
    e.updated_at = func.now()
    await db.commit()
    e = await db.scalar(select(Entrega).where(Entrega.id == entrega_id))
    comps, hojas = await _contexto_entregas(db, [e])
    return _entrega_out(e, comps, hojas, await _nombres_transportistas(db, usuario.tenant_id))


# ===== Hojas de ruta =====

async def _asignar_entregas(
    db: AsyncSession, tenant_id: uuid.UUID, hoja: HojaRuta, entrega_ids: list[uuid.UUID]
) -> None:
    """Reemplaza el conjunto de entregas de una hoja ABIERTA: las que salen
    vuelven a pendiente, las que entran deben estar pendientes y vivas."""
    actuales = (
        await db.scalars(
            select(Entrega).where(Entrega.hoja_ruta_id == hoja.id, Entrega.tenant_id == tenant_id)
        )
    ).all()
    nuevas_set = set(entrega_ids)
    for e in actuales:
        if e.id not in nuevas_set:
            e.estado = "pendiente"
            e.hoja_ruta_id = None
            e.orden = 0
            e.updated_at = func.now()
    actuales_map = {e.id: e for e in actuales}
    for orden, eid in enumerate(entrega_ids, start=1):
        e = actuales_map.get(eid)
        if e is None:
            e = await db.scalar(
                select(Entrega).where(Entrega.id == eid, Entrega.tenant_id == tenant_id)
            )
            if e is None:
                raise HTTPException(status_code=404, detail=f"Entrega no encontrada: {eid}")
            if e.anulado_at is not None or e.estado != "pendiente":
                raise HTTPException(
                    status_code=422,
                    detail=f"La entrega {eid} no está pendiente (estado: {e.estado})",
                )
        e.hoja_ruta_id = hoja.id
        e.estado = "asignada"
        e.orden = orden
        e.transportista_id = hoja.transportista_id
        e.updated_at = func.now()


@router.post("/hojas", response_model=HojaOut, status_code=status.HTTP_201_CREATED)
async def crear_hoja(
    body: HojaIn,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _transportista(db, usuario.tenant_id, body.transportista_id)
    if body.sucursal_id is not None:
        suc = await db.scalar(
            select(Sucursal.id).where(
                Sucursal.id == body.sucursal_id, Sucursal.tenant_id == usuario.tenant_id
            )
        )
        if suc is None:
            raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    ultimo = await db.scalar(
        select(func.coalesce(func.max(HojaRuta.numero), 0)).where(
            HojaRuta.tenant_id == usuario.tenant_id
        )
    )
    h = HojaRuta(
        tenant_id=usuario.tenant_id,
        numero=int(ultimo or 0) + 1,
        fecha=body.fecha or date.today(),
        transportista_id=body.transportista_id,
        sucursal_id=body.sucursal_id,
        observaciones=(body.observaciones or "").strip() or None,
        creado_por=usuario.id,
    )
    db.add(h)
    await db.flush()
    if body.entrega_ids:
        await _asignar_entregas(db, usuario.tenant_id, h, body.entrega_ids)
    await db.commit()
    h = await db.scalar(
        select(HojaRuta).where(HojaRuta.id == h.id).execution_options(populate_existing=True)
    )
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    comps, hojas = await _contexto_entregas(db, h.entregas)
    return _hoja_out(h, nombres, con_entregas=True, comps=comps, hojas=hojas)


@router.get("/hojas", response_model=list[HojaListaOut])
async def listar_hojas(
    response: Response,
    estado: str = "",
    transportista_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    incluir_anuladas: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("logistica", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(HojaRuta).where(HojaRuta.tenant_id == usuario.tenant_id)
    if estado:
        stmt = stmt.where(HojaRuta.estado == estado)
    if transportista_id:
        stmt = stmt.where(HojaRuta.transportista_id == transportista_id)
    if desde:
        stmt = stmt.where(HojaRuta.fecha >= desde)
    if hasta:
        stmt = stmt.where(HojaRuta.fecha <= hasta)
    if not incluir_anuladas:
        stmt = stmt.where(HojaRuta.anulado_at.is_(None))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = (
        await db.scalars(stmt.order_by(HojaRuta.numero.desc()).limit(min(limit, 200)).offset(offset))
    ).all()
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    return [_hoja_out(h, nombres) for h in filas]


@router.get("/hojas/{hoja_id}", response_model=HojaOut)
async def obtener_hoja(
    hoja_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "ver")),
    db: AsyncSession = Depends(get_db),
):
    h = await _hoja(db, usuario.tenant_id, hoja_id)
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    comps, hojas = await _contexto_entregas(db, h.entregas)
    return _hoja_out(h, nombres, con_entregas=True, comps=comps, hojas=hojas)


@router.put("/hojas/{hoja_id}", response_model=HojaOut)
async def actualizar_hoja(
    hoja_id: uuid.UUID,
    body: HojaUpdate,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    h = await _hoja(db, usuario.tenant_id, hoja_id)
    if h.anulado_at is not None or h.estado != "abierta":
        raise HTTPException(status_code=422, detail="Solo se edita una hoja abierta")
    if body.transportista_id is not None:
        await _transportista(db, usuario.tenant_id, body.transportista_id)
        h.transportista_id = body.transportista_id
        for e in h.entregas:
            e.transportista_id = body.transportista_id
    if body.fecha is not None:
        h.fecha = body.fecha
    if body.observaciones is not None:
        h.observaciones = body.observaciones.strip() or None
    if body.entrega_ids is not None:
        await _asignar_entregas(db, usuario.tenant_id, h, body.entrega_ids)
    h.updated_at = func.now()
    await db.commit()
    # populate_existing: la colección `entregas` cambió de MEMBRESÍA — sin esto
    # el identity map devuelve la instancia vieja con la lista stale (regla §6)
    h = await db.scalar(
        select(HojaRuta).where(HojaRuta.id == hoja_id).execution_options(populate_existing=True)
    )
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    comps, hojas = await _contexto_entregas(db, h.entregas)
    return _hoja_out(h, nombres, con_entregas=True, comps=comps, hojas=hojas)


@router.post("/hojas/{hoja_id}/despachar", response_model=HojaOut)
async def despachar_hoja(
    hoja_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    h = await _hoja(db, usuario.tenant_id, hoja_id)
    if h.anulado_at is not None or h.estado != "abierta":
        raise HTTPException(status_code=422, detail="Solo se despacha una hoja abierta")
    if not h.entregas:
        raise HTTPException(status_code=422, detail="La hoja no tiene entregas")
    h.estado = "en_reparto"
    h.updated_at = func.now()
    for e in h.entregas:
        if e.estado == "asignada":
            e.estado = "en_reparto"
            e.updated_at = func.now()
    await db.commit()
    h = await db.scalar(select(HojaRuta).where(HojaRuta.id == hoja_id))
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    comps, hojas = await _contexto_entregas(db, h.entregas)
    return _hoja_out(h, nombres, con_entregas=True, comps=comps, hojas=hojas)


@router.post("/hojas/{hoja_id}/cerrar", response_model=HojaOut)
async def cerrar_hoja(
    hoja_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "editar")),
    db: AsyncSession = Depends(get_db),
):
    h = await _hoja(db, usuario.tenant_id, hoja_id)
    if h.anulado_at is not None or h.estado != "en_reparto":
        raise HTTPException(status_code=422, detail="Solo se cierra una hoja en reparto")
    sin_rendir = [e for e in h.entregas if e.anulado_at is None and e.estado not in ESTADOS_RENDIDOS]
    if sin_rendir:
        raise HTTPException(
            status_code=422,
            detail=f"Quedan {len(sin_rendir)} entregas sin rendir (entregada/rechazada)",
        )
    h.estado = "cerrada"
    h.updated_at = func.now()
    await db.commit()
    h = await db.scalar(select(HojaRuta).where(HojaRuta.id == hoja_id))
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    comps, hojas = await _contexto_entregas(db, h.entregas)
    return _hoja_out(h, nombres, con_entregas=True, comps=comps, hojas=hojas)


@router.post("/hojas/{hoja_id}/anular", response_model=HojaOut)
async def anular_hoja(
    hoja_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("logistica", "anular")),
    db: AsyncSession = Depends(get_db),
):
    """Anular = marcar (contrato 014). Solo abierta — una hoja despachada se
    rinde y se cierra. Las entregas asignadas vuelven a pendiente."""
    h = await _hoja(db, usuario.tenant_id, hoja_id)
    if h.anulado_at is not None or h.estado != "abierta":
        raise HTTPException(status_code=422, detail="Solo se anula una hoja abierta")
    for e in h.entregas:
        e.estado = "pendiente"
        e.hoja_ruta_id = None
        e.orden = 0
        e.updated_at = func.now()
    h.anulado_at = datetime.now(timezone.utc)
    h.anulado_por = usuario.id
    h.updated_at = func.now()
    await db.commit()
    h = await db.scalar(
        select(HojaRuta).where(HojaRuta.id == hoja_id).execution_options(populate_existing=True)
    )
    nombres = await _nombres_transportistas(db, usuario.tenant_id)
    return _hoja_out(h, nombres, con_entregas=True)
