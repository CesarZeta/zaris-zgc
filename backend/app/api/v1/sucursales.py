"""ABM de sucursales (Fase 7). La tabla existe desde la migración 001; esto
le pone la API que faltaba. El listado lo consumen los pickers de usuarios,
cajas POS y los filtros de caja; la edición es config sensible
(`configuracion.editar`, como cajas POS y puntos de venta).

No hay DELETE: las sucursales se desactivan (`activa=false`) porque usuarios,
depósitos, cajas y movimientos pueden referenciarlas.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere, requiere_alguno
from app.models import Provincia, Sucursal, Usuario

router = APIRouter(prefix="/sucursales", tags=["sucursales"])


class SucursalOut(BaseModel):
    id: uuid.UUID
    nombre: str
    domicilio: str | None
    localidad: str | None
    provincia_id: int | None
    codigo_postal: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    telefono: str | None
    activa: bool

    model_config = {"from_attributes": True}


class SucursalIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    domicilio: str | None = Field(None, max_length=120)
    localidad: str | None = Field(None, max_length=60)
    provincia_id: int | None = None
    codigo_postal: str | None = Field(None, max_length=10)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    telefono: str | None = Field(None, max_length=40)


class SucursalUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=60)
    domicilio: str | None = Field(None, max_length=120)
    localidad: str | None = Field(None, max_length=60)
    provincia_id: int | None = None
    codigo_postal: str | None = Field(None, max_length=10)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    telefono: str | None = Field(None, max_length=40)
    activa: bool | None = None


async def _validar_provincia(db: AsyncSession, provincia_id: int | None) -> None:
    if provincia_id is not None:
        if await db.get(Provincia, provincia_id) is None:
            raise HTTPException(status_code=422, detail="Provincia inexistente")


@router.get("", response_model=list[SucursalOut])
async def listar_sucursales(
    incluir_inactivas: bool = False,
    usuario: Usuario = Depends(
        requiere_alguno(["configuracion", "caja", "pos"], "ver")
    ),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Sucursal).where(Sucursal.tenant_id == usuario.tenant_id)
    if not incluir_inactivas:
        stmt = stmt.where(Sucursal.activa.is_(True))
    sucursales = (await db.scalars(stmt.order_by(Sucursal.nombre))).all()
    return [SucursalOut.model_validate(s) for s in sucursales]


@router.post("", response_model=SucursalOut, status_code=status.HTTP_201_CREATED)
async def crear_sucursal(
    body: SucursalIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _validar_provincia(db, body.provincia_id)
    sucursal = Sucursal(
        tenant_id=usuario.tenant_id,
        **{k: (v.strip() if isinstance(v, str) else v) for k, v in body.model_dump().items()},
    )
    db.add(sucursal)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una sucursal con ese nombre")
    return SucursalOut.model_validate(sucursal)


@router.patch("/{sucursal_id}", response_model=SucursalOut)
async def editar_sucursal(
    sucursal_id: uuid.UUID,
    body: SucursalUpdate,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    sucursal = await db.scalar(
        select(Sucursal).where(
            Sucursal.id == sucursal_id, Sucursal.tenant_id == usuario.tenant_id
        )
    )
    if sucursal is None:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    datos = body.model_dump(exclude_unset=True)
    if "provincia_id" in datos:
        await _validar_provincia(db, datos["provincia_id"])
    for campo, valor in datos.items():
        setattr(sucursal, campo, valor.strip() if isinstance(valor, str) else valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una sucursal con ese nombre")
    return SucursalOut.model_validate(sucursal)
