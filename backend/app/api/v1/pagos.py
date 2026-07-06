"""Pagos a proveedores y cuenta corriente (Fase 4) — espejo de cobranzas.py.

Orden de pago = documento interno: registra medios de pago e imputa
facturas/ND de compra pendientes; el resto queda a cuenta. Las NC de compra
registradas generan crédito que también se imputa. El saldo vive en
compras.saldo y ordenes_pago.total - aplicado (a cuenta).
"""

import re
import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    Cheque,
    Compra,
    CompraVencimiento,
    Entidad,
    ImputacionCompra,
    OrdenPago,
    OrdenPagoMedio,
    Proveedor,
    TipoComprobanteCompra,
    Usuario,
)
from app.services import cheques_core as cc
from app.services import compras as sc

router = APIRouter(prefix="/compras/pagos", tags=["pagos"])


# ===== Schemas =====

class ChequePropioIn(BaseModel):
    """Datos de un cheque propio a emitir contra una cuenta (medio='cheque')."""
    cuenta_id: uuid.UUID
    numero: str = Field(min_length=1, max_length=20)
    fecha_pago: date
    fecha_emision: date | None = None


class MedioIn(BaseModel):
    medio: str = Field(pattern="^(efectivo|transferencia|cheque|tarjeta|mercadopago|otro)$")
    importe: Decimal = Field(gt=0)
    referencia: str | None = Field(None, max_length=60)
    # medio='cheque': endosar uno de cartera (endosar_cheque_id) O emitir propio
    # (cheque_propio). Exactamente uno, o ninguno (queda como etiqueta, compat).
    endosar_cheque_id: uuid.UUID | None = None
    cheque_propio: ChequePropioIn | None = None


class ImputacionIn(BaseModel):
    compra_id: uuid.UUID
    importe: Decimal = Field(gt=0)


class OrdenPagoIn(BaseModel):
    proveedor_id: uuid.UUID
    fecha: date | None = None
    medios: list[MedioIn] = Field(min_length=1)
    imputaciones: list[ImputacionIn] = []
    observaciones: str | None = None


class MedioOut(BaseModel):
    medio: str
    importe: Decimal
    referencia: str | None
    model_config = {"from_attributes": True}


class OrdenPagoOut(BaseModel):
    id: uuid.UUID
    numero: int
    numero_formateado: str
    fecha: date
    proveedor_id: uuid.UUID
    proveedor_nombre: str
    total: Decimal
    aplicado: Decimal
    a_cuenta: Decimal
    estado: str
    observaciones: str | None
    medios: list[MedioOut]


class ImputarCreditoIn(BaseModel):
    compra_id: uuid.UUID                    # la deuda (factura/ND con saldo)
    importe: Decimal = Field(gt=0)
    orden_pago_id: uuid.UUID | None = None  # origen: OP con a cuenta...
    credito_id: uuid.UUID | None = None     # ...o NC de compra con saldo


# ===== Helpers =====

def _op_out(op: OrdenPago) -> OrdenPagoOut:
    return OrdenPagoOut(
        id=op.id,
        numero=op.numero,
        numero_formateado=f"OP-{op.numero:08d}",
        fecha=op.fecha,
        proveedor_id=op.proveedor_id,
        proveedor_nombre=op.proveedor_nombre,
        total=op.total,
        aplicado=op.aplicado,
        a_cuenta=op.total - op.aplicado,
        estado=op.estado,
        observaciones=op.observaciones,
        medios=[MedioOut.model_validate(m) for m in op.medios],
    )


async def _proveedor(
    db: AsyncSession, tenant_id: uuid.UUID, proveedor_id: uuid.UUID
) -> Proveedor:
    proveedor = await db.scalar(
        select(Proveedor).where(Proveedor.id == proveedor_id, Proveedor.tenant_id == tenant_id)
    )
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


async def _deuda_bloqueada(
    db: AsyncSession, tenant_id: uuid.UUID, compra_id: uuid.UUID
) -> Compra:
    compra = await db.scalar(
        select(Compra)
        .where(Compra.id == compra_id, Compra.tenant_id == tenant_id)
        # of=: lockear solo compras (el lazy="joined" del tipo mete OUTER JOIN)
        .with_for_update(of=Compra)
    )
    if compra is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    tipo = await db.scalar(
        select(TipoComprobanteCompra).where(TipoComprobanteCompra.codigo == compra.tipo_codigo)
    )
    if compra.estado != "registrado" or tipo.signo_cta_cte != 1:
        raise HTTPException(
            status_code=422, detail="Solo se imputan facturas/ND de compra registradas"
        )
    return compra


# ===== Órdenes de pago =====

@router.post("/ordenes-pago", response_model=OrdenPagoOut, status_code=status.HTTP_201_CREATED)
async def crear_orden_pago(
    body: OrdenPagoIn,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    proveedor = await _proveedor(db, usuario.tenant_id, body.proveedor_id)

    total = sum((m.importe for m in body.medios), Decimal("0"))
    total_imputado = sum((i.importe for i in body.imputaciones), Decimal("0"))
    if total_imputado > total:
        raise HTTPException(
            status_code=422, detail="Lo imputado no puede superar el total de la orden de pago"
        )

    numero = await sc.proximo_numero_op(db, usuario.tenant_id)
    op = OrdenPago(
        tenant_id=usuario.tenant_id,
        numero=numero,
        fecha=body.fecha or date.today(),
        proveedor_id=proveedor.id,
        proveedor_nombre=proveedor.entidad.razon_social,
        total=total,
        aplicado=Decimal("0"),
        observaciones=body.observaciones,
        creado_por=usuario.id,
    )
    db.add(op)
    await db.flush()
    for m in body.medios:
        db.add(
            OrdenPagoMedio(
                tenant_id=usuario.tenant_id,
                orden_pago_id=op.id,
                medio=m.medio,
                importe=m.importe,
                referencia=(m.referencia or "").strip() or None,
            )
        )
        if m.medio == "cheque":
            if m.endosar_cheque_id and m.cheque_propio:
                raise HTTPException(
                    status_code=422,
                    detail="Un medio cheque endosa uno de cartera O emite uno propio, no ambos",
                )
            # (a) Endosar un cheque de tercero en cartera
            if m.endosar_cheque_id:
                cheque = await db.scalar(
                    select(Cheque)
                    .where(
                        Cheque.id == m.endosar_cheque_id,
                        Cheque.tenant_id == usuario.tenant_id,
                    )
                    .with_for_update(of=Cheque)
                )
                if cheque is None:
                    raise HTTPException(status_code=404, detail="Cheque a endosar no encontrado")
                if cheque.importe != m.importe:
                    raise HTTPException(
                        status_code=422,
                        detail=f"El importe del medio (${m.importe}) no coincide con el "
                        f"del cheque (${cheque.importe})",
                    )
                await cc.endosar(
                    db, cheque=cheque, proveedor_id=proveedor.id,
                    orden_pago_id=op.id, fecha=op.fecha, usuario_id=usuario.id,
                )
            # (b) Emitir un cheque propio contra una cuenta
            elif m.cheque_propio:
                await cc.emitir_propio(
                    db,
                    tenant_id=usuario.tenant_id,
                    datos={
                        "numero": m.cheque_propio.numero.strip(),
                        "fecha_emision": m.cheque_propio.fecha_emision or op.fecha,
                        "fecha_pago": m.cheque_propio.fecha_pago,
                        "importe": m.importe,
                    },
                    cuenta_id=m.cheque_propio.cuenta_id,
                    proveedor_id=proveedor.id,
                    orden_pago_id=op.id,
                    usuario_id=usuario.id,
                )
    for imp in body.imputaciones:
        deuda = await _deuda_bloqueada(db, usuario.tenant_id, imp.compra_id)
        if deuda.proveedor_id != proveedor.id:
            raise HTTPException(
                status_code=422, detail="La compra imputada es de otro proveedor"
            )
        if imp.importe > deuda.saldo:
            raise HTTPException(
                status_code=422,
                detail=f"Imputación de ${imp.importe} supera el saldo ${deuda.saldo} "
                f"de {deuda.tipo_codigo} {deuda.numero}",
            )
        deuda.saldo = deuda.saldo - imp.importe
        op.aplicado = op.aplicado + imp.importe
        db.add(
            ImputacionCompra(
                tenant_id=usuario.tenant_id,
                proveedor_id=proveedor.id,
                orden_pago_id=op.id,
                compra_id=deuda.id,
                importe=imp.importe,
                fecha=op.fecha,
                creado_por=usuario.id,
            )
        )
    await db.commit()
    op = await db.scalar(select(OrdenPago).where(OrdenPago.id == op.id))
    return _op_out(op)


@router.get("/ordenes-pago", response_model=list[OrdenPagoOut])
async def listar_ordenes_pago(
    response: Response,
    q: str = "",
    proveedor_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(OrdenPago).where(OrdenPago.tenant_id == usuario.tenant_id)
    if proveedor_id:
        stmt = stmt.where(OrdenPago.proveedor_id == proveedor_id)
    q = q.strip()
    if q:
        solo_digitos = re.sub(r"\D", "", q)
        if solo_digitos and not re.sub(r"[\d\s\-]", "", q.replace("OP", "").replace("op", "")):
            numero = int(solo_digitos[-8:]) if len(solo_digitos) > 8 else int(solo_digitos)
            stmt = stmt.where(OrdenPago.numero == numero)
        else:
            stmt = stmt.where(
                and_(*(OrdenPago.proveedor_nombre.ilike(f"%{tok}%") for tok in q.split()))
            )
    if desde:
        stmt = stmt.where(OrdenPago.fecha >= desde)
    if hasta:
        stmt = stmt.where(OrdenPago.fecha <= hasta)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        stmt.order_by(OrdenPago.fecha.desc(), OrdenPago.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return [_op_out(o) for o in filas]


@router.post("/ordenes-pago/{op_id}/anular", response_model=OrdenPagoOut)
async def anular_orden_pago(
    op_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("compras", "anular")),
    db: AsyncSession = Depends(get_db),
):
    op = await db.scalar(
        select(OrdenPago)
        .where(OrdenPago.id == op_id, OrdenPago.tenant_id == usuario.tenant_id)
        .with_for_update(of=OrdenPago)
    )
    if op is None:
        raise HTTPException(status_code=404, detail="Orden de pago no encontrada")
    if op.estado != "emitida":
        raise HTTPException(status_code=409, detail="La orden de pago ya está anulada")

    imputaciones = (
        await db.scalars(
            select(ImputacionCompra).where(
                ImputacionCompra.orden_pago_id == op.id,
                ImputacionCompra.tenant_id == usuario.tenant_id,
            )
        )
    ).all()
    for imp in imputaciones:
        deuda = await db.scalar(
            select(Compra).where(Compra.id == imp.compra_id).with_for_update(of=Compra)
        )
        deuda.saldo = deuda.saldo + imp.importe
        await db.delete(imp)
    op.aplicado = Decimal("0")
    op.estado = "anulada"
    await db.commit()
    op = await db.scalar(select(OrdenPago).where(OrdenPago.id == op_id))
    return _op_out(op)


# ===== Imputación suelta (a cuenta de OP o crédito de NC → deuda) =====

@router.post("/imputaciones", status_code=status.HTTP_201_CREATED)
async def imputar(
    body: ImputarCreditoIn,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if (body.orden_pago_id is None) == (body.credito_id is None):
        raise HTTPException(
            status_code=422, detail="Indicar orden_pago_id O credito_id (exactamente uno)"
        )
    deuda = await _deuda_bloqueada(db, usuario.tenant_id, body.compra_id)
    if body.importe > deuda.saldo:
        raise HTTPException(status_code=422, detail="La imputación supera el saldo de la deuda")

    if body.orden_pago_id is not None:
        op = await db.scalar(
            select(OrdenPago)
            .where(
                OrdenPago.id == body.orden_pago_id,
                OrdenPago.tenant_id == usuario.tenant_id,
                OrdenPago.estado == "emitida",
            )
            .with_for_update(of=OrdenPago)
        )
        if op is None:
            raise HTTPException(status_code=404, detail="Orden de pago no encontrada")
        if op.proveedor_id != deuda.proveedor_id:
            raise HTTPException(status_code=422, detail="OP y deuda de proveedores distintos")
        disponible = op.total - op.aplicado
        if body.importe > disponible:
            raise HTTPException(
                status_code=422, detail=f"La orden de pago solo tiene ${disponible} a cuenta"
            )
        op.aplicado = op.aplicado + body.importe
    else:
        credito = await db.scalar(
            select(Compra)
            .where(
                Compra.id == body.credito_id,
                Compra.tenant_id == usuario.tenant_id,
                Compra.estado == "registrado",
            )
            .with_for_update(of=Compra)
        )
        if credito is None:
            raise HTTPException(status_code=404, detail="Nota de crédito no encontrada")
        tipo = await db.scalar(
            select(TipoComprobanteCompra).where(
                TipoComprobanteCompra.codigo == credito.tipo_codigo
            )
        )
        if tipo.signo_cta_cte != -1:
            raise HTTPException(
                status_code=422, detail="El crédito debe ser una NC de compra registrada"
            )
        if credito.proveedor_id != deuda.proveedor_id:
            raise HTTPException(status_code=422, detail="NC y deuda de proveedores distintos")
        if body.importe > credito.saldo:
            raise HTTPException(
                status_code=422, detail=f"La NC solo tiene ${credito.saldo} disponibles"
            )
        credito.saldo = credito.saldo - body.importe

    deuda.saldo = deuda.saldo - body.importe
    db.add(
        ImputacionCompra(
            tenant_id=usuario.tenant_id,
            proveedor_id=deuda.proveedor_id,
            orden_pago_id=body.orden_pago_id,
            credito_id=body.credito_id,
            compra_id=deuda.id,
            importe=body.importe,
            creado_por=usuario.id,
        )
    )
    await db.commit()
    return {"ok": True, "saldo_restante_deuda": str(deuda.saldo)}


# ===== Cuenta corriente, saldos y vencimientos =====

@router.get("/cuenta-corriente/{proveedor_id}")
async def cuenta_corriente(
    proveedor_id: uuid.UUID,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Movimientos históricos (debe/haber) + saldo actual con el proveedor.
    Acá el DEBE es nuestra deuda (facturas/ND) y el HABER lo que pagamos o
    nos acreditan (OP/NC)."""
    await _proveedor(db, usuario.tenant_id, proveedor_id)

    # Proyección de columnas + filtro de fechas en SQL (espejo de cobranzas):
    # antes cargaba los ORM completos de TODA la historia (items/vencimientos
    # por selectin) y filtraba en Python.
    stmt_c = (
        select(
            Compra.fecha,
            Compra.created_at,
            TipoComprobanteCompra.descripcion,
            Compra.punto_venta,
            Compra.numero,
            Compra.total,
            Compra.saldo,
            Compra.contado,
            TipoComprobanteCompra.signo_cta_cte,
        )
        .join(TipoComprobanteCompra, Compra.tipo_codigo == TipoComprobanteCompra.codigo)
        .where(
            Compra.tenant_id == usuario.tenant_id,
            Compra.proveedor_id == proveedor_id,
            Compra.estado == "registrado",
            TipoComprobanteCompra.fiscal.is_(True),
        )
    )
    stmt_o = select(
        OrdenPago.fecha,
        OrdenPago.created_at,
        OrdenPago.numero,
        OrdenPago.total,
        OrdenPago.aplicado,
    ).where(
        OrdenPago.tenant_id == usuario.tenant_id,
        OrdenPago.proveedor_id == proveedor_id,
        OrdenPago.estado == "emitida",
    )
    if desde:
        stmt_c = stmt_c.where(Compra.fecha >= desde)
        stmt_o = stmt_o.where(OrdenPago.fecha >= desde)
    if hasta:
        stmt_c = stmt_c.where(Compra.fecha <= hasta)
        stmt_o = stmt_o.where(OrdenPago.fecha <= hasta)
    compras = (await db.execute(stmt_c)).all()
    ops = (await db.execute(stmt_o)).all()

    movimientos = []
    for c in compras:
        # compras contado no mueven la cta. cte. (pagadas en el acto)
        if c.contado and c.signo_cta_cte == 1:
            continue
        debe = c.total if c.signo_cta_cte == 1 else Decimal("0")
        haber = c.total if c.signo_cta_cte == -1 else Decimal("0")
        movimientos.append(
            {
                "fecha": c.fecha.isoformat(),
                "orden": c.created_at.isoformat(),
                "tipo": c.descripcion,
                "numero": f"{c.punto_venta:04d}-{c.numero:08d}",
                "debe": str(debe),
                "haber": str(haber),
                "pendiente": str(c.saldo),
            }
        )
    for op in ops:
        movimientos.append(
            {
                "fecha": op.fecha.isoformat(),
                "orden": op.created_at.isoformat(),
                "tipo": "Orden de pago",
                "numero": f"OP-{op.numero:08d}",
                "debe": "0",
                "haber": str(op.total),
                "pendiente": str(op.total - op.aplicado),
            }
        )
    movimientos.sort(key=lambda m: (m["fecha"], m["orden"]))

    acumulado = Decimal("0")
    for m in movimientos:
        acumulado += Decimal(m["debe"]) - Decimal(m["haber"])
        m["saldo_acumulado"] = str(acumulado)

    saldo_total = await _saldo_proveedor(db, usuario.tenant_id, proveedor_id)
    return {"movimientos": movimientos, "saldo": str(saldo_total)}


async def _saldo_proveedor(
    db: AsyncSession, tenant_id: uuid.UUID, proveedor_id: uuid.UUID
) -> Decimal:
    """deuda pendiente (facturas/ND.saldo) − créditos NC.saldo − a cuenta de OPs."""
    deuda = await db.scalar(
        select(func.coalesce(func.sum(Compra.saldo), 0))
        .join(TipoComprobanteCompra, Compra.tipo_codigo == TipoComprobanteCompra.codigo)
        .where(
            Compra.tenant_id == tenant_id,
            Compra.proveedor_id == proveedor_id,
            Compra.estado == "registrado",
            TipoComprobanteCompra.signo_cta_cte == 1,
        )
    )
    creditos = await db.scalar(
        select(func.coalesce(func.sum(Compra.saldo), 0))
        .join(TipoComprobanteCompra, Compra.tipo_codigo == TipoComprobanteCompra.codigo)
        .where(
            Compra.tenant_id == tenant_id,
            Compra.proveedor_id == proveedor_id,
            Compra.estado == "registrado",
            TipoComprobanteCompra.signo_cta_cte == -1,
        )
    )
    a_cuenta = await db.scalar(
        select(func.coalesce(func.sum(OrdenPago.total - OrdenPago.aplicado), 0)).where(
            OrdenPago.tenant_id == tenant_id,
            OrdenPago.proveedor_id == proveedor_id,
            OrdenPago.estado == "emitida",
        )
    )
    return Decimal(deuda) - Decimal(creditos) - Decimal(a_cuenta)


@router.get("/saldos")
async def saldos_por_proveedor(
    solo_con_deuda: bool = True,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Listado de saldos: cuánto le debemos a cada proveedor."""
    filas = (
        await db.execute(
            select(
                Compra.proveedor_id,
                func.sum(Compra.saldo * TipoComprobanteCompra.signo_cta_cte).label("saldo"),
            )
            .join(TipoComprobanteCompra, Compra.tipo_codigo == TipoComprobanteCompra.codigo)
            .where(
                Compra.tenant_id == usuario.tenant_id,
                Compra.estado == "registrado",
                TipoComprobanteCompra.fiscal.is_(True),
                Compra.saldo != 0,
            )
            .group_by(Compra.proveedor_id)
        )
    ).all()
    saldos = {pid: Decimal(s) for pid, s in filas}

    a_cuenta_filas = (
        await db.execute(
            select(OrdenPago.proveedor_id, func.sum(OrdenPago.total - OrdenPago.aplicado))
            .where(
                OrdenPago.tenant_id == usuario.tenant_id,
                OrdenPago.estado == "emitida",
                OrdenPago.total != OrdenPago.aplicado,
            )
            .group_by(OrdenPago.proveedor_id)
        )
    ).all()
    for pid, ac in a_cuenta_filas:
        saldos[pid] = saldos.get(pid, Decimal("0")) - Decimal(ac)

    if not saldos:
        return []
    proveedores = (
        await db.execute(
            select(Proveedor, Entidad)
            .join(Entidad, Proveedor.entidad_id == Entidad.id)
            .where(Proveedor.id.in_(saldos.keys()), Proveedor.tenant_id == usuario.tenant_id)
        )
    ).all()
    resultado = []
    for proveedor, entidad in proveedores:
        saldo = saldos.get(proveedor.id, Decimal("0"))
        if solo_con_deuda and saldo <= 0:
            continue
        resultado.append(
            {
                "proveedor_id": str(proveedor.id),
                "codigo": proveedor.codigo,
                "nombre": entidad.razon_social,
                "saldo": str(saldo),
            }
        )
    resultado.sort(key=lambda x: Decimal(x["saldo"]), reverse=True)
    return resultado


@router.get("/vencimientos")
async def vencimientos_a_pagar(
    dias: int = 30,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Cuentas a pagar: cuotas de compras con saldo, vencidas o por vencer
    en los próximos `dias` días, ordenadas por fecha."""
    hasta = date.today() + timedelta(days=max(0, min(dias, 365)))
    filas = (
        await db.execute(
            select(CompraVencimiento, Compra, Entidad)
            .join(Compra, CompraVencimiento.compra_id == Compra.id)
            .join(Proveedor, Compra.proveedor_id == Proveedor.id)
            .join(Entidad, Proveedor.entidad_id == Entidad.id)
            .where(
                Compra.tenant_id == usuario.tenant_id,
                Compra.estado == "registrado",
                Compra.saldo > 0,
                CompraVencimiento.fecha_vto <= hasta,
            )
            .order_by(CompraVencimiento.fecha_vto)
        )
    ).all()
    hoy = date.today()
    return [
        {
            "compra_id": str(compra.id),
            "proveedor_id": str(compra.proveedor_id),
            "proveedor_nombre": entidad.razon_social,
            "tipo_codigo": compra.tipo_codigo,
            "numero": f"{compra.punto_venta:04d}-{compra.numero:08d}",
            "nro_cuota": vto.nro_cuota,
            "fecha_vto": vto.fecha_vto.isoformat(),
            "importe_cuota": str(vto.importe),
            "saldo_compra": str(compra.saldo),
            "vencida": vto.fecha_vto < hoy,
        }
        for vto, compra, entidad in filas
    ]
