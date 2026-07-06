"""Rol proveedor sobre la BUE (Fase 4) — espejo del patrón clientes.py.

Una entidad es proveedor UNA vez por tenant; puede ser cliente Y proveedor
sin duplicar datos maestros (CLAUDE.md §1-bis).
"""

import uuid
from datetime import date
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
from app.models import Articulo, ArticuloProveedor, Entidad, Proveedor, Usuario

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


class ProveedorIn(BaseModel):
    # BUE: o se referencia una entidad existente, o se crea una nueva — nunca ambas
    entidad_id: uuid.UUID | None = None
    entidad: EntidadIn | None = None
    codigo: str | None = Field(None, max_length=10)
    condicion_compra_id: uuid.UUID | None = None
    rubro: str | None = Field(None, max_length=40)
    observaciones: str | None = None


class ProveedorUpdate(BaseModel):
    codigo: str | None = None
    condicion_compra_id: uuid.UUID | None = None
    rubro: str | None = None
    observaciones: str | None = None
    activo: bool | None = None
    entidad: EntidadIn | None = None  # actualiza también los datos maestros


class ProveedorOut(BaseModel):
    id: uuid.UUID
    codigo: str | None
    condicion_compra_id: uuid.UUID | None
    rubro: str | None
    observaciones: str | None
    activo: bool
    entidad: EntidadOut

    model_config = {"from_attributes": True}


class ArticuloProveedorOut(BaseModel):
    id: uuid.UUID
    articulo_id: uuid.UUID
    articulo_codigo: str
    articulo_descripcion: str
    codigo_proveedor: str | None
    costo: Decimal
    bonif_1: Decimal
    bonif_2: Decimal
    bonif_3: Decimal
    costo_neto: Decimal
    ultima_compra: date | None


async def _obtener_proveedor(
    db: AsyncSession, tenant_id: uuid.UUID, proveedor_id: uuid.UUID
) -> Proveedor:
    proveedor = await db.scalar(
        select(Proveedor).where(Proveedor.id == proveedor_id, Proveedor.tenant_id == tenant_id)
    )
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


def costo_neto(ap: ArticuloProveedor) -> Decimal:
    cien = Decimal("100")
    neto = (
        ap.costo
        * (cien - ap.bonif_1) / cien
        * (cien - ap.bonif_2) / cien
        * (cien - ap.bonif_3) / cien
    )
    return neto.quantize(Decimal("0.0001"))


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
async def crear_proveedor(
    body: ProveedorIn,
    usuario: Usuario = Depends(requiere("proveedores", "editar")),
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

    proveedor = Proveedor(
        tenant_id=usuario.tenant_id,
        entidad_id=entidad_id,
        **body.model_dump(exclude={"entidad_id", "entidad"}),
    )
    db.add(proveedor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La entidad ya es proveedor, o el código ya está en uso",
        )
    proveedor = await db.scalar(select(Proveedor).where(Proveedor.id == proveedor.id))
    return ProveedorOut.model_validate(proveedor)


@router.get("", response_model=list[ProveedorOut])
async def listar_proveedores(
    response: Response,
    q: str = "",
    incluir_inactivos: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("proveedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Proveedor)
        .join(Entidad, Proveedor.entidad_id == Entidad.id)
        .where(Proveedor.tenant_id == usuario.tenant_id)
    )
    if not incluir_inactivos:
        stmt = stmt.where(Proveedor.activo)
    stmt = aplicar_busqueda(stmt, q)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)

    stmt = stmt.order_by(Entidad.razon_social).limit(min(limit, 200)).offset(offset)
    proveedores = (await db.scalars(stmt)).unique().all()
    return [ProveedorOut.model_validate(p) for p in proveedores]


@router.get("/{proveedor_id}", response_model=ProveedorOut)
async def obtener_proveedor(
    proveedor_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("proveedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return ProveedorOut.model_validate(
        await _obtener_proveedor(db, usuario.tenant_id, proveedor_id)
    )


@router.put("/{proveedor_id}", response_model=ProveedorOut)
async def actualizar_proveedor(
    proveedor_id: uuid.UUID,
    body: ProveedorUpdate,
    usuario: Usuario = Depends(requiere("proveedores", "editar")),
    db: AsyncSession = Depends(get_db),
):
    proveedor = await _obtener_proveedor(db, usuario.tenant_id, proveedor_id)

    cambios = body.model_dump(exclude_unset=True, exclude={"entidad"})
    for campo, valor in cambios.items():
        setattr(proveedor, campo, valor)
    proveedor.updated_at = func.now()

    if body.entidad is not None:
        datos = _validar_entidad(body.entidad)
        entidad = proveedor.entidad
        for campo, valor in datos.model_dump().items():
            setattr(entidad, campo, valor)
        entidad.updated_at = func.now()

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflicto de unicidad (código o documento ya en uso)",
        )
    proveedor = await db.scalar(select(Proveedor).where(Proveedor.id == proveedor_id))
    return ProveedorOut.model_validate(proveedor)


@router.get("/{proveedor_id}/articulos", response_model=list[ArticuloProveedorOut])
async def articulos_del_proveedor(
    proveedor_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("proveedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Artículos que provee, con su costo de lista y bonificaciones."""
    await _obtener_proveedor(db, usuario.tenant_id, proveedor_id)
    filas = (
        await db.execute(
            select(ArticuloProveedor, Articulo)
            .join(Articulo, ArticuloProveedor.articulo_id == Articulo.id)
            .where(
                ArticuloProveedor.tenant_id == usuario.tenant_id,
                ArticuloProveedor.proveedor_id == proveedor_id,
            )
            .order_by(Articulo.descripcion)
        )
    ).all()
    return [
        ArticuloProveedorOut(
            id=ap.id,
            articulo_id=art.id,
            articulo_codigo=art.codigo,
            articulo_descripcion=art.descripcion,
            codigo_proveedor=ap.codigo_proveedor,
            costo=ap.costo,
            bonif_1=ap.bonif_1,
            bonif_2=ap.bonif_2,
            bonif_3=ap.bonif_3,
            costo_neto=costo_neto(ap),
            ultima_compra=ap.ultima_compra,
        )
        for ap, art in filas
    ]
