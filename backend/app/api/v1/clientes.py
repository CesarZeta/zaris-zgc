import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.entidades import EntidadOut, aplicar_busqueda
from app.core.cuit import validar_documento
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import Cliente, Entidad, Usuario, Zona

router = APIRouter(prefix="/clientes", tags=["clientes"])


class EntidadIn(BaseModel):
    tipo_persona: str = Field("F", pattern="^[FJ]$")
    razon_social: str = Field(min_length=2, max_length=120)
    nombre_fantasia: str | None = None
    tipo_documento: str = Field("DNI", pattern="^(CUIT|CUIL|DNI|SD)$")
    nro_documento: str | None = None
    condicion_iva: str = Field("CF", pattern="^(RI|MT|EX|CF)$")
    email: str | None = None
    telefono_1: str | None = None
    telefono_2: str | None = None
    domicilio: str | None = None
    localidad: str | None = None
    provincia_id: int | None = None
    codigo_postal: str | None = None
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    observaciones: str | None = None


class ClienteIn(BaseModel):
    # BUE: o se referencia una entidad existente, o se crea una nueva — nunca ambas
    entidad_id: uuid.UUID | None = None
    entidad: EntidadIn | None = None
    codigo: str | None = Field(None, max_length=10)
    lista_precios: int = Field(1, ge=1, le=4)
    condicion_venta_id: uuid.UUID | None = None
    zona_id: uuid.UUID | None = None
    descuento: Decimal = Decimal("0")
    limite_credito: Decimal | None = None
    bloqueado: bool = False
    observaciones: str | None = None


class ClienteUpdate(BaseModel):
    codigo: str | None = None
    lista_precios: int | None = Field(None, ge=1, le=4)
    condicion_venta_id: uuid.UUID | None = None
    zona_id: uuid.UUID | None = None
    descuento: Decimal | None = None
    limite_credito: Decimal | None = None
    bloqueado: bool | None = None
    observaciones: str | None = None
    activo: bool | None = None
    entidad: EntidadIn | None = None  # actualiza también los datos maestros


class ClienteOut(BaseModel):
    id: uuid.UUID
    codigo: str | None
    lista_precios: int
    condicion_venta_id: uuid.UUID | None
    zona_id: uuid.UUID | None
    descuento: Decimal
    limite_credito: Decimal | None
    bloqueado: bool
    observaciones: str | None
    activo: bool
    entidad: EntidadOut

    model_config = {"from_attributes": True}


def _validar_entidad(datos: EntidadIn) -> EntidadIn:
    try:
        datos.nro_documento = validar_documento(datos.tipo_documento, datos.nro_documento)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    return datos


async def _obtener_cliente(db: AsyncSession, tenant_id: uuid.UUID, cliente_id: uuid.UUID) -> Cliente:
    cliente = await db.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
    )
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente


# ===== Zonas (catálogo del rol cliente; declaradas ANTES de /{cliente_id}) =====

class ZonaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    model_config = {"from_attributes": True}


class ZonaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=40)


@router.get("/zonas", response_model=list[ZonaOut])
async def listar_zonas(
    usuario: Usuario = Depends(requiere("clientes", "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas = await db.scalars(
        select(Zona).where(Zona.tenant_id == usuario.tenant_id).order_by(Zona.nombre)
    )
    return list(filas)


@router.post("/zonas", response_model=ZonaOut, status_code=status.HTTP_201_CREATED)
async def crear_zona(
    body: ZonaIn,
    usuario: Usuario = Depends(requiere("clientes", "editar")),
    db: AsyncSession = Depends(get_db),
):
    nombre = body.nombre.strip()
    existente = await db.scalar(
        select(Zona).where(
            Zona.tenant_id == usuario.tenant_id, func.lower(Zona.nombre) == nombre.lower()
        )
    )
    if existente is not None:
        return existente
    zona = Zona(tenant_id=usuario.tenant_id, nombre=nombre)
    db.add(zona)
    await db.commit()
    return zona


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_cliente(
    body: ClienteIn,
    usuario: Usuario = Depends(requiere("clientes", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if (body.entidad_id is None) == (body.entidad is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una entidad con ese documento en la empresa (BUE: reusarla via entidad_id)",
            )
        entidad_id = entidad.id
    else:
        entidad = await db.scalar(
            select(Entidad).where(Entidad.id == body.entidad_id, Entidad.tenant_id == usuario.tenant_id)
        )
        if entidad is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entidad no encontrada")
        entidad_id = entidad.id

    cliente = Cliente(
        tenant_id=usuario.tenant_id,
        entidad_id=entidad_id,
        **body.model_dump(exclude={"entidad_id", "entidad"}),
    )
    db.add(cliente)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La entidad ya es cliente, o el código ya está en uso",
        )
    cliente = await db.scalar(select(Cliente).where(Cliente.id == cliente.id))
    return ClienteOut.model_validate(cliente)


@router.get("", response_model=list[ClienteOut])
async def listar_clientes(
    response: Response,
    q: str = "",
    incluir_inactivos: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("clientes", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Cliente)
        .join(Entidad, Cliente.entidad_id == Entidad.id)
        .where(Cliente.tenant_id == usuario.tenant_id)
    )
    if not incluir_inactivos:
        stmt = stmt.where(Cliente.activo)
    stmt = aplicar_busqueda(stmt, q)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)

    stmt = stmt.order_by(Entidad.razon_social).limit(min(limit, 200)).offset(offset)
    clientes = (await db.scalars(stmt)).unique().all()
    return [ClienteOut.model_validate(c) for c in clientes]


@router.get("/{cliente_id}", response_model=ClienteOut)
async def obtener_cliente(
    cliente_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("clientes", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return ClienteOut.model_validate(await _obtener_cliente(db, usuario.tenant_id, cliente_id))


@router.put("/{cliente_id}", response_model=ClienteOut)
async def actualizar_cliente(
    cliente_id: uuid.UUID,
    body: ClienteUpdate,
    usuario: Usuario = Depends(requiere("clientes", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cliente = await _obtener_cliente(db, usuario.tenant_id, cliente_id)

    cambios = body.model_dump(exclude_unset=True, exclude={"entidad"})
    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)
    cliente.updated_at = func.now()

    if body.entidad is not None:
        datos = _validar_entidad(body.entidad)
        entidad = cliente.entidad
        for campo, valor in datos.model_dump().items():
            setattr(entidad, campo, valor)
        entidad.updated_at = func.now()

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto de unicidad (código o documento ya en uso)",
        )
    cliente = await db.scalar(select(Cliente).where(Cliente.id == cliente_id))
    return ClienteOut.model_validate(cliente)
