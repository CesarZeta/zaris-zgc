"""Caja (Fase 5): conceptos, movimientos manuales, planilla diaria y cierre.

La planilla del día es un REPORTE que agrega lo ya registrado (ventas contado,
cobranzas por medio, pagos por medio) más los movimientos manuales de caja.
Solo el cierre se materializa (caja_cierres), con arqueo de efectivo.

Criterios (espejo del legacy MOVIM/SALCAJA):
- El saldo de caja es EFECTIVO. La planilla muestra todos los medios; el
  cierre sella entradas/salidas de efectivo. Las ventas de contado se asumen
  efectivo hasta que el POS (Fase 6) registre medios por venta.
- Las órdenes de pago no tienen sucursal: entran solo en la planilla global
  (sin filtro de sucursal).
- Cerrado el día (por sucursal o global), no se permiten altas/bajas de
  movimientos manuales de esa fecha; el cierre puede eliminarse (reabrir).
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    CajaCierre,
    CajaMovimiento,
    Comprobante,
    ConceptoCaja,
    OrdenPago,
    OrdenPagoMedio,
    PuntoVenta,
    Recibo,
    ReciboMedio,
    TipoComprobante,
    Usuario,
    VentaMedio,
)

router = APIRouter(prefix="/caja", tags=["caja"])

MEDIOS = ("efectivo", "transferencia", "cheque", "tarjeta", "mercadopago", "otro")


# ---------------------------------------------------------------- schemas
class ConceptoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=40)
    tipo: str = Field(pattern="^(entrada|salida)$")


class ConceptoUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=40)
    activo: bool | None = None


class ConceptoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    tipo: str
    activo: bool

    model_config = {"from_attributes": True}


class MovimientoIn(BaseModel):
    fecha: date | None = None
    sucursal_id: uuid.UUID | None = None
    concepto_id: uuid.UUID
    medio: str = Field("efectivo", pattern="^(efectivo|transferencia|cheque|tarjeta|mercadopago|otro)$")
    importe: Decimal = Field(gt=0)
    descripcion: str | None = Field(None, max_length=120)


class MovimientoOut(BaseModel):
    id: uuid.UUID
    fecha: date
    sucursal_id: uuid.UUID | None
    concepto_id: uuid.UUID
    concepto_nombre: str
    tipo: str
    medio: str
    importe: Decimal
    descripcion: str | None


class TotalMedio(BaseModel):
    medio: str
    total: Decimal
    cantidad: int


class CierreOut(BaseModel):
    id: uuid.UUID
    sucursal_id: uuid.UUID | None
    fecha: date
    saldo_inicial: Decimal
    entradas: Decimal
    salidas: Decimal
    saldo_final: Decimal
    efectivo_contado: Decimal | None
    diferencia: Decimal | None
    observaciones: str | None

    model_config = {"from_attributes": True}


class PlanillaOut(BaseModel):
    fecha: date
    sucursal_id: uuid.UUID | None
    saldo_inicial: Decimal
    ventas_contado_cantidad: int
    ventas_contado_total: Decimal  # neto: facturas/ND menos NC contado del día
    ventas_por_medio: list[TotalMedio]  # ventas con medios registrados (POS, Fase 6)
    cobranzas: list[TotalMedio]
    pagos: list[TotalMedio]
    movimientos: list[MovimientoOut]
    entradas_efectivo: Decimal
    salidas_efectivo: Decimal
    saldo_final: Decimal
    cierre: CierreOut | None


class CierreIn(BaseModel):
    fecha: date
    sucursal_id: uuid.UUID | None = None
    efectivo_contado: Decimal | None = None
    observaciones: str | None = None


# ---------------------------------------------------------------- helpers
def _mov_out(m: CajaMovimiento) -> MovimientoOut:
    return MovimientoOut(
        id=m.id,
        fecha=m.fecha,
        sucursal_id=m.sucursal_id,
        concepto_id=m.concepto_id,
        concepto_nombre=m.concepto.nombre,
        tipo=m.tipo,
        medio=m.medio,
        importe=m.importe,
        descripcion=m.descripcion,
    )


async def _cierre_de(
    db: AsyncSession, tenant_id: uuid.UUID, fecha: date, sucursal_id: uuid.UUID | None
) -> CajaCierre | None:
    stmt = select(CajaCierre).where(CajaCierre.tenant_id == tenant_id, CajaCierre.fecha == fecha)
    stmt = stmt.where(
        CajaCierre.sucursal_id == sucursal_id if sucursal_id else CajaCierre.sucursal_id.is_(None)
    )
    return await db.scalar(stmt)


async def _fecha_cerrada(
    db: AsyncSession, tenant_id: uuid.UUID, fecha: date, sucursal_id: uuid.UUID | None
) -> bool:
    """Cerrada si existe cierre de esa fecha en el scope del movimiento O global."""
    scope = CajaCierre.sucursal_id.is_(None)
    if sucursal_id:
        scope = or_(scope, CajaCierre.sucursal_id == sucursal_id)
    return (
        await db.scalar(
            select(func.count())
            .select_from(CajaCierre)
            .where(CajaCierre.tenant_id == tenant_id, CajaCierre.fecha == fecha, scope)
        )
    ) > 0


async def _calcular_planilla(
    db: AsyncSession, tenant_id: uuid.UUID, fecha: date, sucursal_id: uuid.UUID | None
) -> PlanillaOut:
    # --- saldo inicial: saldo_final del último cierre anterior del mismo scope ---
    stmt = (
        select(CajaCierre.saldo_final)
        .where(CajaCierre.tenant_id == tenant_id, CajaCierre.fecha < fecha)
        .order_by(CajaCierre.fecha.desc())
        .limit(1)
    )
    stmt = stmt.where(
        CajaCierre.sucursal_id == sucursal_id if sucursal_id else CajaCierre.sucursal_id.is_(None)
    )
    saldo_inicial = (await db.scalar(stmt)) or Decimal("0")

    # --- ventas contado del día (emitidas): facturas/ND entran, NC salen.
    # Contado = cobrado/devuelto en el acto: el flujo de caja tiene el MISMO
    # signo que signo_cta_cte (FA/ND +1, NC -1; seed de la 006).
    stmt = (
        select(
            func.count(),
            func.coalesce(func.sum(Comprobante.total * TipoComprobante.signo_cta_cte), 0),
        )
        .select_from(Comprobante)
        .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
        .where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.fecha == fecha,
            Comprobante.estado == "emitido",
            Comprobante.contado.is_(True),
            TipoComprobante.clase.in_(("factura", "nota_debito", "nota_credito")),
        )
    )
    if sucursal_id:
        stmt = stmt.join(PuntoVenta, PuntoVenta.id == Comprobante.punto_venta_id).where(
            PuntoVenta.sucursal_id == sucursal_id
        )
    ventas_cant, ventas_total = (await db.execute(stmt)).one()

    # --- ventas con medios registrados (POS Fase 6): entran por su medio real ---
    stmt = (
        select(
            VentaMedio.medio,
            func.coalesce(func.sum(VentaMedio.importe * TipoComprobante.signo_cta_cte), 0),
            func.count(),
        )
        .select_from(VentaMedio)
        .join(Comprobante, Comprobante.id == VentaMedio.comprobante_id)
        .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
        .where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.fecha == fecha,
            Comprobante.estado == "emitido",
            Comprobante.contado.is_(True),
        )
        .group_by(VentaMedio.medio)
    )
    if sucursal_id:
        stmt = stmt.join(PuntoVenta, PuntoVenta.id == Comprobante.punto_venta_id).where(
            PuntoVenta.sucursal_id == sucursal_id
        )
    ventas_por_medio = [
        TotalMedio(medio=m, total=t, cantidad=c) for m, t, c in (await db.execute(stmt)).all()
    ]

    # --- ventas SIN medios registrados (gestión manual): se asumen efectivo,
    # criterio Fase 5 (el POS ya registra los suyos arriba) ---
    tiene_medios = (
        select(VentaMedio.id).where(VentaMedio.comprobante_id == Comprobante.id).exists()
    )
    stmt = (
        select(func.coalesce(func.sum(Comprobante.total * TipoComprobante.signo_cta_cte), 0))
        .select_from(Comprobante)
        .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
        .where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.fecha == fecha,
            Comprobante.estado == "emitido",
            Comprobante.contado.is_(True),
            TipoComprobante.clase.in_(("factura", "nota_debito", "nota_credito")),
            ~tiene_medios,
        )
    )
    if sucursal_id:
        stmt = stmt.join(PuntoVenta, PuntoVenta.id == Comprobante.punto_venta_id).where(
            PuntoVenta.sucursal_id == sucursal_id
        )
    ventas_sin_medios = Decimal((await db.scalar(stmt)) or 0)

    # --- cobranzas del día por medio ---
    stmt = (
        select(ReciboMedio.medio, func.sum(ReciboMedio.importe), func.count())
        .join(Recibo, Recibo.id == ReciboMedio.recibo_id)
        .where(
            Recibo.tenant_id == tenant_id,
            Recibo.fecha == fecha,
            Recibo.estado == "emitido",
        )
        .group_by(ReciboMedio.medio)
    )
    if sucursal_id:
        stmt = stmt.join(PuntoVenta, PuntoVenta.id == Recibo.punto_venta_id).where(
            PuntoVenta.sucursal_id == sucursal_id
        )
    cobranzas = [
        TotalMedio(medio=m, total=t, cantidad=c) for m, t, c in (await db.execute(stmt)).all()
    ]

    # --- pagos del día por medio (OP no tienen sucursal: solo planilla global) ---
    pagos: list[TotalMedio] = []
    if not sucursal_id:
        stmt = (
            select(OrdenPagoMedio.medio, func.sum(OrdenPagoMedio.importe), func.count())
            .join(OrdenPago, OrdenPago.id == OrdenPagoMedio.orden_pago_id)
            .where(
                OrdenPago.tenant_id == tenant_id,
                OrdenPago.fecha == fecha,
                OrdenPago.estado == "emitida",
            )
            .group_by(OrdenPagoMedio.medio)
        )
        pagos = [
            TotalMedio(medio=m, total=t, cantidad=c) for m, t, c in (await db.execute(stmt)).all()
        ]

    # --- movimientos manuales del día ---
    stmt = (
        select(CajaMovimiento)
        .where(CajaMovimiento.tenant_id == tenant_id, CajaMovimiento.fecha == fecha)
        .order_by(CajaMovimiento.created_at)
    )
    if sucursal_id:
        stmt = stmt.where(CajaMovimiento.sucursal_id == sucursal_id)
    movimientos = (await db.scalars(stmt)).all()

    # --- efectivo: ventas sin medios (asumidas efectivo) + medios POS en
    # efectivo + cobranzas/pagos/movs ---
    cob_ef = sum((c.total for c in cobranzas if c.medio == "efectivo"), Decimal("0"))
    pag_ef = sum((p.total for p in pagos if p.medio == "efectivo"), Decimal("0"))
    mov_ent_ef = sum(
        (m.importe for m in movimientos if m.tipo == "entrada" and m.medio == "efectivo"),
        Decimal("0"),
    )
    mov_sal_ef = sum(
        (m.importe for m in movimientos if m.tipo == "salida" and m.medio == "efectivo"),
        Decimal("0"),
    )
    ventas_total = Decimal(ventas_total)
    ventas_ef = ventas_sin_medios + sum(
        (Decimal(v.total) for v in ventas_por_medio if v.medio == "efectivo"), Decimal("0")
    )
    entradas = (ventas_ef if ventas_ef > 0 else Decimal("0")) + cob_ef + mov_ent_ef
    salidas = (-ventas_ef if ventas_ef < 0 else Decimal("0")) + pag_ef + mov_sal_ef

    cierre = await _cierre_de(db, tenant_id, fecha, sucursal_id)
    return PlanillaOut(
        fecha=fecha,
        sucursal_id=sucursal_id,
        saldo_inicial=saldo_inicial,
        ventas_contado_cantidad=ventas_cant,
        ventas_contado_total=ventas_total,
        ventas_por_medio=ventas_por_medio,
        cobranzas=cobranzas,
        pagos=pagos,
        movimientos=[_mov_out(m) for m in movimientos],
        entradas_efectivo=entradas,
        salidas_efectivo=salidas,
        saldo_final=saldo_inicial + entradas - salidas,
        cierre=CierreOut.model_validate(cierre) if cierre else None,
    )


# ---------------------------------------------------------------- conceptos
@router.get("/conceptos", response_model=list[ConceptoOut])
async def listar_conceptos(
    incluir_inactivos: bool = False,
    usuario: Usuario = Depends(requiere("caja", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ConceptoCaja).where(ConceptoCaja.tenant_id == usuario.tenant_id)
    if not incluir_inactivos:
        stmt = stmt.where(ConceptoCaja.activo.is_(True))
    return (await db.scalars(stmt.order_by(ConceptoCaja.tipo, ConceptoCaja.nombre))).all()


@router.post("/conceptos", response_model=ConceptoOut, status_code=status.HTTP_201_CREATED)
async def crear_concepto(
    body: ConceptoIn,
    usuario: Usuario = Depends(requiere("caja", "editar")),
    db: AsyncSession = Depends(get_db),
):
    concepto = ConceptoCaja(tenant_id=usuario.tenant_id, nombre=body.nombre.strip(), tipo=body.tipo)
    db.add(concepto)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un concepto con ese nombre")
    await db.refresh(concepto)
    return concepto


@router.patch("/conceptos/{concepto_id}", response_model=ConceptoOut)
async def editar_concepto(
    concepto_id: uuid.UUID,
    body: ConceptoUpdate,
    usuario: Usuario = Depends(requiere("caja", "editar")),
    db: AsyncSession = Depends(get_db),
):
    concepto = await db.scalar(
        select(ConceptoCaja).where(
            ConceptoCaja.id == concepto_id, ConceptoCaja.tenant_id == usuario.tenant_id
        )
    )
    if concepto is None:
        raise HTTPException(status_code=404, detail="Concepto no encontrado")
    if body.nombre is not None:
        concepto.nombre = body.nombre.strip()
    if body.activo is not None:
        concepto.activo = body.activo
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un concepto con ese nombre")
    await db.refresh(concepto)
    return concepto


# ---------------------------------------------------------------- movimientos
@router.get("/movimientos", response_model=list[MovimientoOut])
async def listar_movimientos(
    desde: date | None = None,
    hasta: date | None = None,
    sucursal_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("caja", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CajaMovimiento).where(CajaMovimiento.tenant_id == usuario.tenant_id)
    if desde:
        stmt = stmt.where(CajaMovimiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(CajaMovimiento.fecha <= hasta)
    if sucursal_id:
        stmt = stmt.where(CajaMovimiento.sucursal_id == sucursal_id)
    stmt = stmt.order_by(CajaMovimiento.fecha.desc(), CajaMovimiento.created_at.desc())
    movimientos = (await db.scalars(stmt.limit(min(limit, 500)).offset(offset))).all()
    return [_mov_out(m) for m in movimientos]


@router.post("/movimientos", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def crear_movimiento(
    body: MovimientoIn,
    usuario: Usuario = Depends(requiere("caja", "editar")),
    db: AsyncSession = Depends(get_db),
):
    concepto = await db.scalar(
        select(ConceptoCaja).where(
            ConceptoCaja.id == body.concepto_id, ConceptoCaja.tenant_id == usuario.tenant_id
        )
    )
    if concepto is None or not concepto.activo:
        raise HTTPException(status_code=422, detail="Concepto inexistente o inactivo")
    fecha = body.fecha or date.today()
    if await _fecha_cerrada(db, usuario.tenant_id, fecha, body.sucursal_id):
        raise HTTPException(status_code=409, detail="La caja de esa fecha está cerrada")

    movimiento = CajaMovimiento(
        tenant_id=usuario.tenant_id,
        sucursal_id=body.sucursal_id,
        fecha=fecha,
        concepto_id=concepto.id,
        tipo=concepto.tipo,
        medio=body.medio,
        importe=body.importe,
        descripcion=body.descripcion,
        creado_por=usuario.id,
    )
    db.add(movimiento)
    await db.commit()
    await db.refresh(movimiento)
    return _mov_out(movimiento)


@router.delete("/movimientos/{movimiento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_movimiento(
    movimiento_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("caja", "anular")),
    db: AsyncSession = Depends(get_db),
):
    movimiento = await db.scalar(
        select(CajaMovimiento).where(
            CajaMovimiento.id == movimiento_id, CajaMovimiento.tenant_id == usuario.tenant_id
        )
    )
    if movimiento is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    if await _fecha_cerrada(db, usuario.tenant_id, movimiento.fecha, movimiento.sucursal_id):
        raise HTTPException(status_code=409, detail="La caja de esa fecha está cerrada")
    await db.delete(movimiento)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- planilla y cierre
@router.get("/planilla", response_model=PlanillaOut)
async def planilla_diaria(
    fecha: date | None = None,
    sucursal_id: uuid.UUID | None = None,
    usuario: Usuario = Depends(requiere("caja", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return await _calcular_planilla(db, usuario.tenant_id, fecha or date.today(), sucursal_id)


@router.get("/cierres", response_model=list[CierreOut])
async def listar_cierres(
    desde: date | None = None,
    hasta: date | None = None,
    sucursal_id: uuid.UUID | None = None,
    limit: int = 60,
    usuario: Usuario = Depends(requiere("caja", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CajaCierre).where(CajaCierre.tenant_id == usuario.tenant_id)
    if desde:
        stmt = stmt.where(CajaCierre.fecha >= desde)
    if hasta:
        stmt = stmt.where(CajaCierre.fecha <= hasta)
    if sucursal_id:
        stmt = stmt.where(CajaCierre.sucursal_id == sucursal_id)
    return (await db.scalars(stmt.order_by(CajaCierre.fecha.desc()).limit(min(limit, 366)))).all()


@router.post("/cierres", response_model=CierreOut, status_code=status.HTTP_201_CREATED)
async def cerrar_caja(
    body: CierreIn,
    usuario: Usuario = Depends(requiere("caja", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if await _cierre_de(db, usuario.tenant_id, body.fecha, body.sucursal_id) is not None:
        raise HTTPException(status_code=409, detail="Esa fecha ya está cerrada")
    planilla = await _calcular_planilla(db, usuario.tenant_id, body.fecha, body.sucursal_id)
    diferencia = (
        body.efectivo_contado - planilla.saldo_final if body.efectivo_contado is not None else None
    )
    cierre = CajaCierre(
        tenant_id=usuario.tenant_id,
        sucursal_id=body.sucursal_id,
        fecha=body.fecha,
        saldo_inicial=planilla.saldo_inicial,
        entradas=planilla.entradas_efectivo,
        salidas=planilla.salidas_efectivo,
        saldo_final=planilla.saldo_final,
        efectivo_contado=body.efectivo_contado,
        diferencia=diferencia,
        observaciones=body.observaciones,
        cerrado_por=usuario.id,
    )
    db.add(cierre)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Esa fecha ya está cerrada")
    await db.refresh(cierre)
    return cierre


@router.delete("/cierres/{cierre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def reabrir_caja(
    cierre_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("caja", "anular")),
    db: AsyncSession = Depends(get_db),
):
    cierre = await db.scalar(
        select(CajaCierre).where(
            CajaCierre.id == cierre_id, CajaCierre.tenant_id == usuario.tenant_id
        )
    )
    if cierre is None:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    await db.delete(cierre)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
