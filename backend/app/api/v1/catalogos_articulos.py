"""Catálogos del módulo Artículos: familias/subfamilias, marcas, unidades,
depósitos y cotización del dólar (decisión MVP: precios en USD + cotización)."""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere, requiere_alguno
from app.models import (
    Atributo,
    AtributoValor,
    Cotizacion,
    Deposito,
    Familia,
    Marca,
    Subfamilia,
    Unidad,
    Usuario,
)

router = APIRouter(prefix="/catalogos-articulos", tags=["catalogos-articulos"])


# ===== Schemas =====

class NombreIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=40)


class NombreUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=40)
    activa: bool | None = None


class SubfamiliaOut(BaseModel):
    id: uuid.UUID
    familia_id: uuid.UUID
    nombre: str
    activa: bool
    model_config = {"from_attributes": True}


class FamiliaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    activa: bool
    subfamilias: list[SubfamiliaOut] = []
    model_config = {"from_attributes": True}


class MarcaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    activa: bool
    model_config = {"from_attributes": True}


class UnidadIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=6)
    nombre: str = Field(min_length=1, max_length=30)


class UnidadOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    model_config = {"from_attributes": True}


class DepositoIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=4)
    nombre: str = Field(min_length=1, max_length=40)
    sucursal_id: uuid.UUID | None = None


class DepositoUpdate(BaseModel):
    codigo: str | None = Field(None, min_length=1, max_length=4)
    nombre: str | None = Field(None, min_length=1, max_length=40)
    sucursal_id: uuid.UUID | None = None
    activo: bool | None = None


class DepositoOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    sucursal_id: uuid.UUID | None
    activo: bool
    model_config = {"from_attributes": True}


class CotizacionIn(BaseModel):
    valor: Decimal = Field(gt=0)


class CotizacionOut(BaseModel):
    id: uuid.UUID
    valor: Decimal
    vigente_desde: datetime
    model_config = {"from_attributes": True}


def _conflicto(detalle: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detalle)


async def _obtener(db: AsyncSession, modelo, tenant_id: uuid.UUID, id_: uuid.UUID):
    obj = await db.scalar(select(modelo).where(modelo.id == id_, modelo.tenant_id == tenant_id))
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return obj


# ===== Familias / Subfamilias =====

@router.get("/familias", response_model=list[FamiliaOut])
async def listar_familias(
    usuario: Usuario = Depends(requiere("articulos", "ver")), db: AsyncSession = Depends(get_db)
):
    familias = (
        await db.scalars(
            select(Familia).where(Familia.tenant_id == usuario.tenant_id).order_by(Familia.nombre)
        )
    ).unique().all()
    return [FamiliaOut.model_validate(f) for f in familias]


@router.post("/familias", response_model=FamiliaOut, status_code=status.HTTP_201_CREATED)
async def crear_familia(
    body: NombreIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    familia = Familia(tenant_id=usuario.tenant_id, nombre=body.nombre.strip())
    db.add(familia)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe una familia con ese nombre")
    familia = await db.scalar(select(Familia).where(Familia.id == familia.id))
    return FamiliaOut.model_validate(familia)


@router.put("/familias/{familia_id}", response_model=FamiliaOut)
async def actualizar_familia(
    familia_id: uuid.UUID,
    body: NombreUpdate,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    familia = await _obtener(db, Familia, usuario.tenant_id, familia_id)
    if body.nombre is not None:
        familia.nombre = body.nombre.strip()
    if body.activa is not None:
        familia.activa = body.activa
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe una familia con ese nombre")
    familia = await db.scalar(select(Familia).where(Familia.id == familia_id))
    return FamiliaOut.model_validate(familia)


class SubfamiliaIn(BaseModel):
    familia_id: uuid.UUID
    nombre: str = Field(min_length=1, max_length=40)


@router.post("/subfamilias", response_model=SubfamiliaOut, status_code=status.HTTP_201_CREATED)
async def crear_subfamilia(
    body: SubfamiliaIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _obtener(db, Familia, usuario.tenant_id, body.familia_id)
    sub = Subfamilia(
        tenant_id=usuario.tenant_id, familia_id=body.familia_id, nombre=body.nombre.strip()
    )
    db.add(sub)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe esa subfamilia en la familia")
    return SubfamiliaOut.model_validate(sub)


@router.put("/subfamilias/{subfamilia_id}", response_model=SubfamiliaOut)
async def actualizar_subfamilia(
    subfamilia_id: uuid.UUID,
    body: NombreUpdate,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    sub = await _obtener(db, Subfamilia, usuario.tenant_id, subfamilia_id)
    if body.nombre is not None:
        sub.nombre = body.nombre.strip()
    if body.activa is not None:
        sub.activa = body.activa
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe esa subfamilia en la familia")
    return SubfamiliaOut.model_validate(sub)


# ===== Marcas =====

@router.get("/marcas", response_model=list[MarcaOut])
async def listar_marcas(
    usuario: Usuario = Depends(requiere("articulos", "ver")), db: AsyncSession = Depends(get_db)
):
    marcas = (
        await db.scalars(
            select(Marca).where(Marca.tenant_id == usuario.tenant_id).order_by(Marca.nombre)
        )
    ).all()
    return [MarcaOut.model_validate(m) for m in marcas]


@router.post("/marcas", response_model=MarcaOut, status_code=status.HTTP_201_CREATED)
async def crear_marca(
    body: NombreIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    marca = Marca(tenant_id=usuario.tenant_id, nombre=body.nombre.strip())
    db.add(marca)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe una marca con ese nombre")
    return MarcaOut.model_validate(marca)


@router.put("/marcas/{marca_id}", response_model=MarcaOut)
async def actualizar_marca(
    marca_id: uuid.UUID,
    body: NombreUpdate,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    marca = await _obtener(db, Marca, usuario.tenant_id, marca_id)
    if body.nombre is not None:
        marca.nombre = body.nombre.strip()
    if body.activa is not None:
        marca.activa = body.activa
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe una marca con ese nombre")
    return MarcaOut.model_validate(marca)


# ===== Unidades =====

@router.get("/unidades", response_model=list[UnidadOut])
async def listar_unidades(
    usuario: Usuario = Depends(requiere("articulos", "ver")), db: AsyncSession = Depends(get_db)
):
    unidades = (
        await db.scalars(
            select(Unidad).where(Unidad.tenant_id == usuario.tenant_id).order_by(Unidad.codigo)
        )
    ).all()
    return [UnidadOut.model_validate(u) for u in unidades]


@router.post("/unidades", response_model=UnidadOut, status_code=status.HTTP_201_CREATED)
async def crear_unidad(
    body: UnidadIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    unidad = Unidad(
        tenant_id=usuario.tenant_id, codigo=body.codigo.strip().upper(), nombre=body.nombre.strip()
    )
    db.add(unidad)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe una unidad con ese código")
    return UnidadOut.model_validate(unidad)


# ===== Depósitos =====

@router.get("/depositos", response_model=list[DepositoOut])
async def listar_depositos(
    usuario: Usuario = Depends(requiere_alguno(["articulos", "stock", "compras"], "ver")), db: AsyncSession = Depends(get_db)
):
    depositos = (
        await db.scalars(
            select(Deposito).where(Deposito.tenant_id == usuario.tenant_id).order_by(Deposito.codigo)
        )
    ).all()
    return [DepositoOut.model_validate(d) for d in depositos]


@router.post("/depositos", response_model=DepositoOut, status_code=status.HTTP_201_CREATED)
async def crear_deposito(
    body: DepositoIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    deposito = Deposito(
        tenant_id=usuario.tenant_id,
        codigo=body.codigo.strip().upper(),
        nombre=body.nombre.strip(),
        sucursal_id=body.sucursal_id,
    )
    db.add(deposito)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe un depósito con ese código o nombre")
    return DepositoOut.model_validate(deposito)


@router.put("/depositos/{deposito_id}", response_model=DepositoOut)
async def actualizar_deposito(
    deposito_id: uuid.UUID,
    body: DepositoUpdate,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    deposito = await _obtener(db, Deposito, usuario.tenant_id, deposito_id)
    for campo, valor in body.model_dump(exclude_unset=True).items():
        if campo == "codigo" and valor is not None:
            valor = valor.strip().upper()
        setattr(deposito, campo, valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe un depósito con ese código o nombre")
    return DepositoOut.model_validate(deposito)


# ===== Atributos y valores (para variantes — Fase 2.5) =====

class AtributoValorOut(BaseModel):
    id: uuid.UUID
    valor: str
    orden: int
    model_config = {"from_attributes": True}


class AtributoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    orden: int
    valores: list[AtributoValorOut] = []
    model_config = {"from_attributes": True}


class AtributoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=30)


class ValorIn(BaseModel):
    atributo_id: uuid.UUID
    valor: str = Field(min_length=1, max_length=30)


@router.get("/atributos", response_model=list[AtributoOut])
async def listar_atributos(
    usuario: Usuario = Depends(requiere("articulos", "ver")), db: AsyncSession = Depends(get_db)
):
    atributos = (
        await db.scalars(
            select(Atributo).where(Atributo.tenant_id == usuario.tenant_id).order_by(Atributo.orden)
        )
    ).unique().all()
    return [AtributoOut.model_validate(a) for a in atributos]


@router.post("/atributos", response_model=AtributoOut, status_code=status.HTTP_201_CREATED)
async def crear_atributo(
    body: AtributoIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    total = len((await db.scalars(select(Atributo).where(Atributo.tenant_id == usuario.tenant_id))).all())
    atributo = Atributo(tenant_id=usuario.tenant_id, nombre=body.nombre.strip(), orden=total)
    db.add(atributo)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe un atributo con ese nombre")
    atributo = await db.scalar(select(Atributo).where(Atributo.id == atributo.id))
    return AtributoOut.model_validate(atributo)


@router.post("/atributos/valores", response_model=AtributoValorOut, status_code=status.HTTP_201_CREATED)
async def crear_valor(
    body: ValorIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    atributo = await _obtener(db, Atributo, usuario.tenant_id, body.atributo_id)
    total = len(atributo.valores)
    valor = AtributoValor(
        tenant_id=usuario.tenant_id, atributo_id=atributo.id, valor=body.valor.strip(), orden=total
    )
    db.add(valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _conflicto("Ya existe ese valor en el atributo")
    return AtributoValorOut.model_validate(valor)


# ===== Cotización del dólar =====

@router.get("/cotizacion", response_model=CotizacionOut | None)
async def cotizacion_vigente(
    usuario: Usuario = Depends(requiere_alguno(["articulos", "ventas", "compras"], "ver")), db: AsyncSession = Depends(get_db)
):
    cot = await db.scalar(
        select(Cotizacion)
        .where(Cotizacion.tenant_id == usuario.tenant_id)
        .order_by(Cotizacion.vigente_desde.desc())
        .limit(1)
    )
    return CotizacionOut.model_validate(cot) if cot else None


@router.post("/cotizacion", response_model=CotizacionOut, status_code=status.HTTP_201_CREATED)
async def registrar_cotizacion(
    body: CotizacionIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cot = Cotizacion(tenant_id=usuario.tenant_id, valor=body.valor, usuario_id=usuario.id)
    db.add(cot)
    await db.commit()
    return CotizacionOut.model_validate(cot)
