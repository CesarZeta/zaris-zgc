"""F11 — Vendedores y comisiones. Diseño en docs/DISENO-VENDEDORES-COMISIONES.md.

Rol vendedor sobre la BUE (patrón proveedores.py) + liquidaciones de comisión
como DOCUMENTO contabilizable: los pendientes se calculan al vuelo (modalidad
venta = fiscales emitidos del vendedor; cobranza = recibos vivos, neto de
rechazos), "ya liquidado" = existe un ítem de una liquidación VIVA que
referencia el documento — anular la liquidación (marcar) los libera.

Rutas estáticas (/liquidaciones…) ANTES de las paramétricas /{vendedor_id}
(regla §6 del CLAUDE.md). RBAC `vendedores`: GET=ver, escritura=editar,
anular=anular.
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
from app.core.csv_export import csv_response, num
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    ComisionLiquidacion,
    ComisionLiquidacionItem,
    Comprobante,
    Entidad,
    Recibo,
    TipoComprobante,
    Usuario,
    Vendedor,
)

router = APIRouter(prefix="/vendedores", tags=["vendedores"])

D0 = Decimal("0")
C2 = Decimal("0.01")


# ===== Schemas =====

class VendedorIn(BaseModel):
    # BUE: o se referencia una entidad existente, o se crea una nueva — nunca ambas
    entidad_id: uuid.UUID | None = None
    entidad: EntidadIn | None = None
    codigo: str | None = Field(None, max_length=10)
    comision_pct: Decimal = Field(D0, ge=0, le=100)
    modalidad: str = Field("venta", pattern="^(venta|cobranza)$")
    observaciones: str | None = Field(None, max_length=200)


class VendedorUpdate(BaseModel):
    codigo: str | None = None
    comision_pct: Decimal | None = Field(None, ge=0, le=100)
    modalidad: str | None = Field(None, pattern="^(venta|cobranza)$")
    observaciones: str | None = None
    activo: bool | None = None
    entidad: EntidadIn | None = None  # actualiza también los datos maestros


class VendedorOut(BaseModel):
    id: uuid.UUID
    codigo: str | None
    comision_pct: Decimal
    modalidad: str
    observaciones: str | None
    activo: bool
    entidad: EntidadOut
    model_config = {"from_attributes": True}


class PendienteOut(BaseModel):
    comprobante_id: uuid.UUID | None = None
    recibo_id: uuid.UUID | None = None
    fecha: date
    descripcion: str
    base: Decimal
    importe: Decimal


class LiquidarIn(BaseModel):
    desde: date
    hasta: date
    observaciones: str | None = Field(None, max_length=200)


class LiquidacionListaOut(BaseModel):
    id: uuid.UUID
    numero: int
    numero_formateado: str
    vendedor_id: uuid.UUID
    vendedor_nombre: str = ""
    modalidad: str
    desde: date
    hasta: date
    comision_pct: Decimal
    base_total: Decimal
    total: Decimal
    fecha: date
    observaciones: str | None
    anulada: bool = False


class LiquidacionOut(LiquidacionListaOut):
    items: list[PendienteOut] = []


# ===== Helpers =====

async def _vendedor(db: AsyncSession, tenant_id: uuid.UUID, vendedor_id: uuid.UUID) -> Vendedor:
    v = await db.scalar(
        select(Vendedor).where(Vendedor.id == vendedor_id, Vendedor.tenant_id == tenant_id)
    )
    if v is None:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    return v


async def _nombres_vendedores(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    filas = (
        await db.execute(
            select(Vendedor.id, Entidad.razon_social)
            .join(Entidad, Vendedor.entidad_id == Entidad.id)
            .where(Vendedor.tenant_id == tenant_id)
        )
    ).all()
    return dict(filas)


def _liq_out(lq: ComisionLiquidacion, nombres: dict, con_items: bool = False):
    base = dict(
        id=lq.id,
        numero=lq.numero,
        numero_formateado=f"LC-{lq.numero:08d}",
        vendedor_id=lq.vendedor_id,
        vendedor_nombre=nombres.get(lq.vendedor_id, ""),
        modalidad=lq.modalidad,
        desde=lq.desde,
        hasta=lq.hasta,
        comision_pct=lq.comision_pct,
        base_total=lq.base_total,
        total=lq.total,
        fecha=lq.created_at.date(),
        observaciones=lq.observaciones,
        anulada=lq.anulado_at is not None,
    )
    if not con_items:
        return LiquidacionListaOut(**base)
    return LiquidacionOut(
        **base,
        items=[
            PendienteOut(
                comprobante_id=i.comprobante_id, recibo_id=i.recibo_id,
                fecha=i.fecha, descripcion=i.descripcion, base=i.base, importe=i.importe,
            )
            for i in lq.items
        ],
    )


async def _pendientes(
    db: AsyncSession, tenant_id: uuid.UUID, v: Vendedor, desde: date, hasta: date
) -> list[PendienteOut]:
    """Documentos comisionables del vendedor en el rango, excluyendo los ya
    tomados por una liquidación VIVA. La comisión se calcula con el % ACTUAL."""
    pct = Decimal(v.comision_pct)
    out: list[PendienteOut] = []
    if v.modalidad == "venta":
        ya = (
            select(ComisionLiquidacionItem.comprobante_id)
            .join(
                ComisionLiquidacion,
                ComisionLiquidacionItem.liquidacion_id == ComisionLiquidacion.id,
            )
            .where(
                ComisionLiquidacionItem.tenant_id == tenant_id,
                ComisionLiquidacionItem.comprobante_id.is_not(None),
                ComisionLiquidacion.anulado_at.is_(None),
            )
        )
        comps = (
            await db.scalars(
                select(Comprobante)
                .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
                .where(
                    Comprobante.tenant_id == tenant_id,
                    Comprobante.vendedor_id == v.id,
                    Comprobante.estado == "emitido",
                    TipoComprobante.fiscal.is_(True),
                    Comprobante.fecha >= desde,
                    Comprobante.fecha <= hasta,
                    Comprobante.id.notin_(ya),
                )
                .order_by(Comprobante.fecha, Comprobante.numero)
            )
        ).all()
        for c in comps:
            base = (c.neto_gravado + c.neto_no_gravado + c.exento) * c.tipo.signo_cta_cte
            out.append(
                PendienteOut(
                    comprobante_id=c.id,
                    fecha=c.fecha,
                    descripcion=f"{c.tipo_codigo} {c.punto_venta.numero:04d}-{(c.numero or 0):08d} {c.receptor_nombre[:60]}",
                    base=base.quantize(C2),
                    importe=(base * pct / 100).quantize(C2),
                )
            )
    else:
        ya = (
            select(ComisionLiquidacionItem.recibo_id)
            .join(
                ComisionLiquidacion,
                ComisionLiquidacionItem.liquidacion_id == ComisionLiquidacion.id,
            )
            .where(
                ComisionLiquidacionItem.tenant_id == tenant_id,
                ComisionLiquidacionItem.recibo_id.is_not(None),
                ComisionLiquidacion.anulado_at.is_(None),
            )
        )
        recibos = (
            await db.scalars(
                select(Recibo).where(
                    Recibo.tenant_id == tenant_id,
                    Recibo.vendedor_id == v.id,
                    Recibo.estado == "emitido",
                    Recibo.anulado_at.is_(None),
                    Recibo.fecha >= desde,
                    Recibo.fecha <= hasta,
                    Recibo.id.notin_(ya),
                ).order_by(Recibo.fecha, Recibo.numero)
            )
        ).all()
        for r in recibos:
            base = Decimal(r.total) - Decimal(r.rechazado_total)
            out.append(
                PendienteOut(
                    recibo_id=r.id,
                    fecha=r.fecha,
                    descripcion=f"Recibo {r.punto_venta.numero:04d}-{r.numero:08d} {r.receptor_nombre[:60]}",
                    base=base.quantize(C2),
                    importe=(base * pct / 100).quantize(C2),
                )
            )
    return out


# ===== Liquidaciones (estáticas ANTES de /{vendedor_id}) =====

@router.get("/liquidaciones", response_model=list[LiquidacionListaOut])
async def listar_liquidaciones(
    response: Response,
    vendedor_id: uuid.UUID | None = None,
    incluir_anuladas: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("vendedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ComisionLiquidacion).where(
        ComisionLiquidacion.tenant_id == usuario.tenant_id
    )
    if vendedor_id:
        stmt = stmt.where(ComisionLiquidacion.vendedor_id == vendedor_id)
    if not incluir_anuladas:
        stmt = stmt.where(ComisionLiquidacion.anulado_at.is_(None))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = (
        await db.scalars(
            stmt.order_by(ComisionLiquidacion.numero.desc()).limit(min(limit, 200)).offset(offset)
        )
    ).all()
    nombres = await _nombres_vendedores(db, usuario.tenant_id)
    return [_liq_out(lq, nombres) for lq in filas]


@router.get("/liquidaciones/{liq_id}", response_model=LiquidacionOut)
async def detalle_liquidacion(
    liq_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("vendedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    lq = await db.scalar(
        select(ComisionLiquidacion).where(
            ComisionLiquidacion.id == liq_id,
            ComisionLiquidacion.tenant_id == usuario.tenant_id,
        )
    )
    if lq is None:
        raise HTTPException(status_code=404, detail="Liquidación no encontrada")
    nombres = await _nombres_vendedores(db, usuario.tenant_id)
    return _liq_out(lq, nombres, con_items=True)


@router.get("/liquidaciones/{liq_id}/export.csv")
async def export_liquidacion(
    liq_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("vendedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    lq = await db.scalar(
        select(ComisionLiquidacion).where(
            ComisionLiquidacion.id == liq_id,
            ComisionLiquidacion.tenant_id == usuario.tenant_id,
        )
    )
    if lq is None:
        raise HTTPException(status_code=404, detail="Liquidación no encontrada")
    nombres = await _nombres_vendedores(db, usuario.tenant_id)
    encabezado = ["Fecha", "Documento", "Base", "%", "Comisión"]
    datos = [
        [i.fecha.strftime("%d/%m/%Y"), i.descripcion, num(i.base), num(lq.comision_pct), num(i.importe)]
        for i in lq.items
    ]
    datos.append(["", f"TOTAL {nombres.get(lq.vendedor_id, '')}", num(lq.base_total), "", num(lq.total)])
    return csv_response(f"liquidacion-LC-{lq.numero:08d}.csv", encabezado, datos)


@router.post("/liquidaciones/{liq_id}/anular", response_model=LiquidacionOut)
async def anular_liquidacion(
    liq_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("vendedores", "anular")),
    db: AsyncSession = Depends(get_db),
):
    """Anular = marcar (contrato 014). Los documentos vuelven a estar
    pendientes de liquidar; el asiento derivado revierte al regenerar."""
    from datetime import datetime, timezone

    lq = await db.scalar(
        select(ComisionLiquidacion).where(
            ComisionLiquidacion.id == liq_id,
            ComisionLiquidacion.tenant_id == usuario.tenant_id,
            ComisionLiquidacion.anulado_at.is_(None),
        )
    )
    if lq is None:
        raise HTTPException(status_code=404, detail="Liquidación no encontrada")
    lq.anulado_at = datetime.now(timezone.utc)
    lq.anulado_por = usuario.id
    await db.commit()
    lq = await db.scalar(select(ComisionLiquidacion).where(ComisionLiquidacion.id == liq_id))
    nombres = await _nombres_vendedores(db, usuario.tenant_id)
    return _liq_out(lq, nombres, con_items=True)


# ===== Vendedores (rol BUE) =====

@router.post("", response_model=VendedorOut, status_code=status.HTTP_201_CREATED)
async def crear_vendedor(
    body: VendedorIn,
    usuario: Usuario = Depends(requiere("vendedores", "editar")),
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

    vendedor = Vendedor(
        tenant_id=usuario.tenant_id,
        entidad_id=entidad_id,
        codigo=(body.codigo or "").strip() or None,
        comision_pct=body.comision_pct,
        modalidad=body.modalidad,
        observaciones=(body.observaciones or "").strip() or None,
    )
    db.add(vendedor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="La entidad ya es vendedor, o el código ya está en uso"
        )
    vendedor = await db.scalar(select(Vendedor).where(Vendedor.id == vendedor.id))
    return VendedorOut.model_validate(vendedor)


@router.get("", response_model=list[VendedorOut])
async def listar_vendedores(
    response: Response,
    q: str = "",
    incluir_inactivos: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("vendedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Vendedor)
        .join(Entidad, Vendedor.entidad_id == Entidad.id)
        .where(Vendedor.tenant_id == usuario.tenant_id)
    )
    if not incluir_inactivos:
        stmt = stmt.where(Vendedor.activo)
    stmt = aplicar_busqueda(stmt, q)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    stmt = stmt.order_by(Entidad.razon_social).limit(min(limit, 200)).offset(offset)
    filas = (await db.scalars(stmt)).unique().all()
    return [VendedorOut.model_validate(v) for v in filas]


@router.get("/{vendedor_id}", response_model=VendedorOut)
async def obtener_vendedor(
    vendedor_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("vendedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return VendedorOut.model_validate(await _vendedor(db, usuario.tenant_id, vendedor_id))


@router.put("/{vendedor_id}", response_model=VendedorOut)
async def actualizar_vendedor(
    vendedor_id: uuid.UUID,
    body: VendedorUpdate,
    usuario: Usuario = Depends(requiere("vendedores", "editar")),
    db: AsyncSession = Depends(get_db),
):
    vendedor = await _vendedor(db, usuario.tenant_id, vendedor_id)
    cambios = body.model_dump(exclude_unset=True, exclude={"entidad"})
    for campo, valor in cambios.items():
        setattr(vendedor, campo, valor)
    vendedor.updated_at = func.now()
    if body.entidad is not None:
        datos = _validar_entidad(body.entidad)
        entidad = vendedor.entidad
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
    vendedor = await db.scalar(select(Vendedor).where(Vendedor.id == vendedor_id))
    return VendedorOut.model_validate(vendedor)


@router.get("/{vendedor_id}/comisiones/pendientes", response_model=list[PendienteOut])
async def comisiones_pendientes(
    vendedor_id: uuid.UUID,
    desde: date,
    hasta: date,
    usuario: Usuario = Depends(requiere("vendedores", "ver")),
    db: AsyncSession = Depends(get_db),
):
    if desde > hasta:
        raise HTTPException(status_code=422, detail="Rango de fechas inválido")
    v = await _vendedor(db, usuario.tenant_id, vendedor_id)
    return await _pendientes(db, usuario.tenant_id, v, desde, hasta)


@router.post(
    "/{vendedor_id}/liquidaciones",
    response_model=LiquidacionOut,
    status_code=status.HTTP_201_CREATED,
)
async def liquidar_comisiones(
    vendedor_id: uuid.UUID,
    body: LiquidarIn,
    usuario: Usuario = Depends(requiere("vendedores", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Liquida TODOS los pendientes del rango (el server recalcula — el % y la
    modalidad quedan sellados en el documento)."""
    if body.desde > body.hasta:
        raise HTTPException(status_code=422, detail="Rango de fechas inválido")
    v = await _vendedor(db, usuario.tenant_id, vendedor_id)
    pendientes = await _pendientes(db, usuario.tenant_id, v, body.desde, body.hasta)
    if not pendientes:
        raise HTTPException(
            status_code=422, detail="No hay documentos pendientes de comisión en el rango"
        )
    ultimo = await db.scalar(
        select(func.coalesce(func.max(ComisionLiquidacion.numero), 0)).where(
            ComisionLiquidacion.tenant_id == usuario.tenant_id
        )
    )
    lq = ComisionLiquidacion(
        tenant_id=usuario.tenant_id,
        numero=int(ultimo or 0) + 1,
        vendedor_id=v.id,
        modalidad=v.modalidad,
        desde=body.desde,
        hasta=body.hasta,
        comision_pct=v.comision_pct,
        base_total=sum((p.base for p in pendientes), D0),
        total=sum((p.importe for p in pendientes), D0),
        observaciones=(body.observaciones or "").strip() or None,
        creado_por=usuario.id,
    )
    db.add(lq)
    await db.flush()
    for p in pendientes:
        db.add(
            ComisionLiquidacionItem(
                tenant_id=usuario.tenant_id,
                liquidacion_id=lq.id,
                comprobante_id=p.comprobante_id,
                recibo_id=p.recibo_id,
                fecha=p.fecha,
                descripcion=p.descripcion,
                base=p.base,
                importe=p.importe,
            )
        )
    await db.commit()
    lq = await db.scalar(select(ComisionLiquidacion).where(ComisionLiquidacion.id == lq.id))
    nombres = await _nombres_vendedores(db, usuario.tenant_id)
    return _liq_out(lq, nombres, con_items=True)
