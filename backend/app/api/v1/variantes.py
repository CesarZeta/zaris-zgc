"""Variantes de artículos (Fase 2.5): combinaciones de hasta 3 valores de
atributo con EAN, diferencial de precio y stock propios.

El padre (articulos) define descripción, familia, IVA y las 4 listas; la
variante define identidad de venta. Un artículo sin variantes sigue operando
como siempre. La unicidad del EAN se valida contra articulos Y variantes
(cross-tabla, a nivel app; cada tabla además tiene su unique parcial).
"""

import itertools
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    Articulo,
    ArticuloStock,
    ArticuloVariante,
    Atributo,
    AtributoValor,
    Usuario,
)

router = APIRouter(prefix="/articulos", tags=["variantes"])


class VarianteIn(BaseModel):
    valor_ids: list[uuid.UUID] = Field(min_length=1, max_length=3)
    codigo_barras: str | None = Field(None, max_length=20)
    sku_sufijo: str | None = Field(None, max_length=20)
    dif_precio: Decimal = Decimal("0")


class GenerarIn(BaseModel):
    # un set de valores por atributo; se genera el producto cartesiano
    valores_por_atributo: list[list[uuid.UUID]] = Field(min_length=1, max_length=3)


class VarianteUpdate(BaseModel):
    codigo_barras: str | None = Field(None, max_length=20)
    sku_sufijo: str | None = Field(None, max_length=20)
    dif_precio: Decimal | None = None
    activo: bool | None = None


class VarianteOut(BaseModel):
    id: uuid.UUID
    articulo_id: uuid.UUID
    valor_1_id: uuid.UUID
    valor_2_id: uuid.UUID | None
    valor_3_id: uuid.UUID | None
    etiqueta: str  # "M / Rojo"
    codigo_barras: str | None
    sku_sufijo: str | None
    dif_precio: Decimal
    activo: bool
    stock_total: Decimal


async def _articulo(db: AsyncSession, tenant_id: uuid.UUID, articulo_id: uuid.UUID) -> Articulo:
    articulo = await db.scalar(
        select(Articulo).where(Articulo.id == articulo_id, Articulo.tenant_id == tenant_id)
    )
    if articulo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    return articulo


async def _fetch_valores(
    db: AsyncSession, tenant_id: uuid.UUID, valor_ids: list[uuid.UUID]
) -> list[tuple[AtributoValor, Atributo]]:
    valores = (
        await db.execute(
            select(AtributoValor, Atributo)
            .join(Atributo, AtributoValor.atributo_id == Atributo.id)
            .where(AtributoValor.id.in_(valor_ids), AtributoValor.tenant_id == tenant_id)
        )
    ).all()
    if len(valores) != len(set(valor_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Algún valor de atributo no existe en la empresa",
        )
    return [(v, a) for v, a in valores]


async def _valores_ordenados(
    db: AsyncSession, tenant_id: uuid.UUID, valor_ids: list[uuid.UUID]
) -> list[AtributoValor]:
    """Valida una COMBINACIÓN (un valor por atributo) y la devuelve en orden
    estable (por atributo.orden): (Talle M, Color Rojo) debe guardarse siempre
    igual para que el unique de combinación funcione."""
    valores = await _fetch_valores(db, tenant_id, valor_ids)
    atributos = [a.id for _, a in valores]
    if len(set(atributos)) != len(atributos):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede combinar dos valores del mismo atributo",
        )
    return [v for v, a in sorted(valores, key=lambda par: (par[1].orden, par[1].nombre))]


async def _etiquetas(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, str]:
    filas = (
        await db.scalars(select(AtributoValor).where(AtributoValor.tenant_id == tenant_id))
    ).all()
    return {v.id: v.valor for v in filas}


def _armar_out(v: ArticuloVariante, etiquetas: dict, stock: Decimal) -> VarianteOut:
    partes = [etiquetas.get(x) for x in (v.valor_1_id, v.valor_2_id, v.valor_3_id) if x]
    return VarianteOut(
        id=v.id,
        articulo_id=v.articulo_id,
        valor_1_id=v.valor_1_id,
        valor_2_id=v.valor_2_id,
        valor_3_id=v.valor_3_id,
        etiqueta=" / ".join(p or "?" for p in partes),
        codigo_barras=v.codigo_barras,
        sku_sufijo=v.sku_sufijo,
        dif_precio=v.dif_precio,
        activo=v.activo,
        stock_total=stock,
    )


async def _validar_cbarra_cruzado(
    db: AsyncSession, tenant_id: uuid.UUID, cbarra: str, variante_id: uuid.UUID | None = None
) -> None:
    """El EAN no puede repetirse ni entre variantes ni contra artículos."""
    en_articulo = await db.scalar(
        select(Articulo.id).where(Articulo.tenant_id == tenant_id, Articulo.codigo_barras == cbarra)
    )
    stmt = select(ArticuloVariante.id).where(
        ArticuloVariante.tenant_id == tenant_id, ArticuloVariante.codigo_barras == cbarra
    )
    if variante_id:
        stmt = stmt.where(ArticuloVariante.id != variante_id)
    en_variante = await db.scalar(stmt)
    if en_articulo or en_variante:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El código de barras {cbarra} ya está en uso",
        )


async def _stock_por_variante(db: AsyncSession, tenant_id: uuid.UUID, articulo_id: uuid.UUID) -> dict:
    filas = (
        await db.execute(
            select(ArticuloStock.variante_id, func.sum(ArticuloStock.cantidad))
            .where(
                ArticuloStock.tenant_id == tenant_id,
                ArticuloStock.articulo_id == articulo_id,
                ArticuloStock.variante_id.is_not(None),
            )
            .group_by(ArticuloStock.variante_id)
        )
    ).all()
    return {vid: cant for vid, cant in filas}


@router.get("/{articulo_id}/variantes", response_model=list[VarianteOut])
async def listar_variantes(
    articulo_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("articulos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    await _articulo(db, usuario.tenant_id, articulo_id)
    variantes = (
        await db.scalars(
            select(ArticuloVariante)
            .where(
                ArticuloVariante.tenant_id == usuario.tenant_id,
                ArticuloVariante.articulo_id == articulo_id,
            )
            .order_by(ArticuloVariante.created_at)
        )
    ).all()
    etiquetas = await _etiquetas(db, usuario.tenant_id)
    stock = await _stock_por_variante(db, usuario.tenant_id, articulo_id)
    return [_armar_out(v, etiquetas, stock.get(v.id, Decimal("0"))) for v in variantes]


@router.post(
    "/{articulo_id}/variantes", response_model=VarianteOut, status_code=status.HTTP_201_CREATED
)
async def crear_variante(
    articulo_id: uuid.UUID,
    body: VarianteIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _articulo(db, usuario.tenant_id, articulo_id)
    valores = await _valores_ordenados(db, usuario.tenant_id, body.valor_ids)
    cbarra = (body.codigo_barras or "").strip() or None
    if cbarra:
        await _validar_cbarra_cruzado(db, usuario.tenant_id, cbarra)

    ids = [v.id for v in valores] + [None, None]
    variante = ArticuloVariante(
        tenant_id=usuario.tenant_id,
        articulo_id=articulo_id,
        valor_1_id=ids[0],
        valor_2_id=ids[1],
        valor_3_id=ids[2],
        codigo_barras=cbarra,
        sku_sufijo=(body.sku_sufijo or "").strip() or None,
        dif_precio=body.dif_precio,
    )
    db.add(variante)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esa combinación (o ese código de barras) ya existe",
        )
    etiquetas = await _etiquetas(db, usuario.tenant_id)
    return _armar_out(variante, etiquetas, Decimal("0"))


@router.post("/{articulo_id}/variantes/generar", response_model=list[VarianteOut])
async def generar_variantes(
    articulo_id: uuid.UUID,
    body: GenerarIn,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Genera el producto cartesiano de los valores elegidos (grilla talle×color).
    Las combinaciones que ya existen se saltean — es idempotente."""
    await _articulo(db, usuario.tenant_id, articulo_id)

    listas: list[list[AtributoValor]] = []
    orden_atributo: dict[uuid.UUID, tuple] = {}  # valor_id -> clave de orden estable
    for grupo in body.valores_por_atributo:
        if not grupo:
            continue
        pares = await _fetch_valores(db, usuario.tenant_id, grupo)
        if len({a.id for _, a in pares}) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cada grupo debe contener valores de un solo atributo",
            )
        for v, a in pares:
            orden_atributo[v.id] = (a.orden, a.nombre)
        listas.append([v for v, _ in sorted(pares, key=lambda par: par[0].orden)])
    if not listas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sin valores para generar"
        )
    if len({v.atributo_id for lista in listas for v in lista}) != len(listas):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Los grupos deben ser de atributos distintos",
        )

    existentes = {
        (v.valor_1_id, v.valor_2_id, v.valor_3_id)
        for v in (
            await db.scalars(
                select(ArticuloVariante).where(
                    ArticuloVariante.tenant_id == usuario.tenant_id,
                    ArticuloVariante.articulo_id == articulo_id,
                )
            )
        ).all()
    }
    nuevas = []
    for combinacion in itertools.product(*listas):
        ordenada = sorted(combinacion, key=lambda v: orden_atributo[v.id])
        ids = [v.id for v in ordenada] + [None, None]
        clave = (ids[0], ids[1], ids[2])
        if clave in existentes:
            continue
        existentes.add(clave)
        sufijo = "-" + "-".join(v.valor[:8].upper().replace(" ", "") for v in ordenada)
        variante = ArticuloVariante(
            tenant_id=usuario.tenant_id,
            articulo_id=articulo_id,
            valor_1_id=ids[0],
            valor_2_id=ids[1],
            valor_3_id=ids[2],
            sku_sufijo=sufijo[:20],
        )
        db.add(variante)
        nuevas.append(variante)
    await db.commit()

    etiquetas = await _etiquetas(db, usuario.tenant_id)
    return [_armar_out(v, etiquetas, Decimal("0")) for v in nuevas]


@router.put("/variantes/{variante_id}", response_model=VarianteOut)
async def actualizar_variante(
    variante_id: uuid.UUID,
    body: VarianteUpdate,
    usuario: Usuario = Depends(requiere("articulos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    variante = await db.scalar(
        select(ArticuloVariante).where(
            ArticuloVariante.id == variante_id, ArticuloVariante.tenant_id == usuario.tenant_id
        )
    )
    if variante is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variante no encontrada")

    cambios = body.model_dump(exclude_unset=True)
    if "codigo_barras" in cambios:
        cbarra = (cambios["codigo_barras"] or "").strip() or None
        if cbarra:
            await _validar_cbarra_cruzado(db, usuario.tenant_id, cbarra, variante.id)
        cambios["codigo_barras"] = cbarra
    for campo, valor in cambios.items():
        setattr(variante, campo, valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Código de barras en uso")

    etiquetas = await _etiquetas(db, usuario.tenant_id)
    stock = await _stock_por_variante(db, usuario.tenant_id, variante.articulo_id)
    return _armar_out(variante, etiquetas, stock.get(variante.id, Decimal("0")))
