"""Cobranzas y cuenta corriente de clientes (Fase 3).

Recibo = documento interno X (RG 1415): registra medios de pago e imputa
facturas/ND pendientes; el resto queda a cuenta. Las NC emitidas generan
crédito que también se imputa. El saldo vive en comprobantes.saldo (deuda o
crédito según la clase) y recibos.total - recibos.aplicado (a cuenta).
"""

import re
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    Cliente,
    Comprobante,
    Entidad,
    Imputacion,
    PuntoVenta,
    Recibo,
    ReciboMedio,
    TipoComprobante,
    Usuario,
)
from app.core.cuit import validar_cuit
from app.services import cheques_core as cc
from app.services import ventas as sv

router = APIRouter(prefix="/cobranzas", tags=["cobranzas"])

MEDIOS = ("efectivo", "transferencia", "cheque", "tarjeta", "mercadopago", "otro")


# ===== Schemas =====

class ChequeMedioIn(BaseModel):
    """Datos del cheque de tercero recibido en la cobranza (medio='cheque').
    Opcional: si no viene, el medio queda como hoy (solo etiqueta, sin cartera)."""
    numero: str = Field(min_length=1, max_length=20)
    banco: str = Field(min_length=1, max_length=60)
    fecha_pago: date
    fecha_emision: date | None = None
    titular: str | None = Field(None, max_length=80)
    cuit_firmante: str | None = Field(None, max_length=13)
    plaza: str | None = Field(None, max_length=60)
    es_echeq: bool = False


class MedioIn(BaseModel):
    medio: str = Field(pattern="^(efectivo|transferencia|cheque|tarjeta|mercadopago|otro)$")
    importe: Decimal = Field(gt=0)
    referencia: str | None = Field(None, max_length=60)
    cheque: ChequeMedioIn | None = None


class ImputacionIn(BaseModel):
    comprobante_id: uuid.UUID
    importe: Decimal = Field(gt=0)


class ReciboIn(BaseModel):
    punto_venta_id: uuid.UUID
    cliente_id: uuid.UUID
    fecha: date | None = None
    medios: list[MedioIn] = Field(min_length=1)
    imputaciones: list[ImputacionIn] = []
    observaciones: str | None = None


class MedioOut(BaseModel):
    medio: str
    importe: Decimal
    referencia: str | None
    model_config = {"from_attributes": True}


class ReciboOut(BaseModel):
    id: uuid.UUID
    numero: int
    numero_formateado: str
    fecha: date
    cliente_id: uuid.UUID
    receptor_nombre: str
    total: Decimal
    aplicado: Decimal
    a_cuenta: Decimal
    estado: str
    observaciones: str | None
    medios: list[MedioOut]


class ImputarCreditoIn(BaseModel):
    comprobante_id: uuid.UUID          # la deuda (factura/ND con saldo)
    importe: Decimal = Field(gt=0)
    recibo_id: uuid.UUID | None = None  # origen: recibo con a cuenta...
    credito_id: uuid.UUID | None = None  # ...o NC con saldo


# ===== Helpers =====

def _recibo_out(r: Recibo) -> ReciboOut:
    return ReciboOut(
        id=r.id,
        numero=r.numero,
        numero_formateado=f"{r.punto_venta.numero:04d}-{r.numero:08d}",
        fecha=r.fecha,
        cliente_id=r.cliente_id,
        receptor_nombre=r.receptor_nombre,
        total=r.total,
        aplicado=r.aplicado,
        a_cuenta=r.total - r.aplicado,
        estado=r.estado,
        observaciones=r.observaciones,
        medios=[MedioOut.model_validate(m) for m in r.medios],
    )


async def _cliente(db: AsyncSession, tenant_id: uuid.UUID, cliente_id: uuid.UUID) -> Cliente:
    cliente = await db.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
    )
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


async def _deuda_bloqueada(
    db: AsyncSession, tenant_id: uuid.UUID, comprobante_id: uuid.UUID
) -> Comprobante:
    comp = await db.scalar(
        select(Comprobante)
        .where(Comprobante.id == comprobante_id, Comprobante.tenant_id == tenant_id)
        # of=: lockear solo comprobantes (los lazy="joined" meten OUTER JOINs
        # y FOR UPDATE no aplica al lado nullable)
        .with_for_update(of=Comprobante)
    )
    if comp is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    tipo = await db.scalar(
        select(TipoComprobante).where(TipoComprobante.codigo == comp.tipo_codigo)
    )
    if comp.estado != "emitido" or tipo.signo_cta_cte != 1:
        raise HTTPException(
            status_code=422, detail="Solo se imputan facturas/ND emitidas"
        )
    return comp


# ===== Recibos =====

@router.post("/recibos", response_model=ReciboOut, status_code=status.HTTP_201_CREATED)
async def crear_recibo(
    body: ReciboIn,
    usuario: Usuario = Depends(requiere("clientes", "editar")),
    db: AsyncSession = Depends(get_db),
):
    pv = await db.scalar(
        select(PuntoVenta).where(
            PuntoVenta.id == body.punto_venta_id,
            PuntoVenta.tenant_id == usuario.tenant_id,
            PuntoVenta.activo.is_(True),
        )
    )
    if pv is None:
        raise HTTPException(status_code=404, detail="Punto de venta no encontrado o inactivo")
    cliente = await _cliente(db, usuario.tenant_id, body.cliente_id)

    total = sum((m.importe for m in body.medios), Decimal("0"))
    total_imputado = sum((i.importe for i in body.imputaciones), Decimal("0"))
    if total_imputado > total:
        raise HTTPException(
            status_code=422, detail="Lo imputado no puede superar el total del recibo"
        )

    numero = await sv.proximo_numero(db, usuario.tenant_id, pv.id, "REC")
    recibo = Recibo(
        tenant_id=usuario.tenant_id,
        punto_venta_id=pv.id,
        numero=numero,
        fecha=body.fecha or date.today(),
        cliente_id=cliente.id,
        receptor_nombre=cliente.entidad.razon_social,
        total=total,
        aplicado=Decimal("0"),
        observaciones=body.observaciones,
        creado_por=usuario.id,
    )
    db.add(recibo)
    await db.flush()
    for m in body.medios:
        db.add(
            ReciboMedio(
                tenant_id=usuario.tenant_id,
                recibo_id=recibo.id,
                medio=m.medio,
                importe=m.importe,
                referencia=(m.referencia or "").strip() or None,
            )
        )
        # Cheque de tercero → materializa en cartera (Fase 8). Si el medio es
        # cheque pero no manda datos, se comporta como antes (solo etiqueta).
        if m.medio == "cheque" and m.cheque is not None:
            if m.cheque.cuit_firmante and not validar_cuit(m.cheque.cuit_firmante):
                raise HTTPException(status_code=422, detail="CUIT del firmante inválido")
            await cc.recibir_tercero(
                db,
                tenant_id=usuario.tenant_id,
                datos={
                    "numero": m.cheque.numero.strip(),
                    "banco": m.cheque.banco.strip(),
                    "plaza": (m.cheque.plaza or "").strip() or None,
                    "titular": (m.cheque.titular or "").strip() or None,
                    "cuit_firmante": (m.cheque.cuit_firmante or "").strip() or None,
                    "fecha_emision": m.cheque.fecha_emision,
                    "fecha_pago": m.cheque.fecha_pago,
                    "importe": m.importe,
                    "es_echeq": m.cheque.es_echeq,
                },
                cliente_id=cliente.id,
                recibo_id=recibo.id,
                usuario_id=usuario.id,
            )
    for imp in body.imputaciones:
        deuda = await _deuda_bloqueada(db, usuario.tenant_id, imp.comprobante_id)
        if deuda.cliente_id != cliente.id:
            raise HTTPException(
                status_code=422, detail="La factura imputada es de otro cliente"
            )
        if imp.importe > deuda.saldo:
            raise HTTPException(
                status_code=422,
                detail=f"Imputación de ${imp.importe} supera el saldo ${deuda.saldo} "
                f"de {deuda.tipo_codigo} {deuda.numero}",
            )
        deuda.saldo = deuda.saldo - imp.importe
        recibo.aplicado = recibo.aplicado + imp.importe
        db.add(
            Imputacion(
                tenant_id=usuario.tenant_id,
                cliente_id=cliente.id,
                recibo_id=recibo.id,
                comprobante_id=deuda.id,
                importe=imp.importe,
                fecha=recibo.fecha,
                creado_por=usuario.id,
            )
        )
    await db.commit()
    recibo = await db.scalar(select(Recibo).where(Recibo.id == recibo.id))
    return _recibo_out(recibo)


@router.get("/recibos", response_model=list[ReciboOut])
async def listar_recibos(
    response: Response,
    q: str = "",
    cliente_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("clientes", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recibo).where(Recibo.tenant_id == usuario.tenant_id)
    if cliente_id:
        stmt = stmt.where(Recibo.cliente_id == cliente_id)
    q = q.strip()
    if q:
        solo_digitos = re.sub(r"\D", "", q)
        if solo_digitos and not re.sub(r"[\d\s\-]", "", q):
            numero = int(solo_digitos[-8:]) if len(solo_digitos) > 8 else int(solo_digitos)
            stmt = stmt.where(Recibo.numero == numero)
        else:
            stmt = stmt.where(
                and_(*(Recibo.receptor_nombre.ilike(f"%{tok}%") for tok in q.split()))
            )
    if desde:
        stmt = stmt.where(Recibo.fecha >= desde)
    if hasta:
        stmt = stmt.where(Recibo.fecha <= hasta)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        stmt.order_by(Recibo.fecha.desc(), Recibo.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return [_recibo_out(r) for r in filas]


@router.post("/recibos/{recibo_id}/anular", response_model=ReciboOut)
async def anular_recibo(
    recibo_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("clientes", "anular")),
    db: AsyncSession = Depends(get_db),
):
    recibo = await db.scalar(
        select(Recibo)
        .where(Recibo.id == recibo_id, Recibo.tenant_id == usuario.tenant_id)
        .with_for_update(of=Recibo)
    )
    if recibo is None:
        raise HTTPException(status_code=404, detail="Recibo no encontrado")
    if recibo.estado != "emitido":
        raise HTTPException(status_code=409, detail="El recibo ya está anulado")

    imputaciones = (
        await db.scalars(
            select(Imputacion).where(
                Imputacion.recibo_id == recibo.id,
                Imputacion.tenant_id == usuario.tenant_id,
            )
        )
    ).all()
    for imp in imputaciones:
        deuda = await db.scalar(
            select(Comprobante)
            .where(Comprobante.id == imp.comprobante_id)
            .with_for_update(of=Comprobante)
        )
        deuda.saldo = deuda.saldo + imp.importe
        await db.delete(imp)
    recibo.aplicado = Decimal("0")
    recibo.estado = "anulado"
    await db.commit()
    recibo = await db.scalar(select(Recibo).where(Recibo.id == recibo_id))
    return _recibo_out(recibo)


# ===== Imputación suelta (a cuenta de recibo o crédito de NC → deuda) =====

@router.post("/imputaciones", status_code=status.HTTP_201_CREATED)
async def imputar(
    body: ImputarCreditoIn,
    usuario: Usuario = Depends(requiere("clientes", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if (body.recibo_id is None) == (body.credito_id is None):
        raise HTTPException(
            status_code=422, detail="Indicar recibo_id O credito_id (exactamente uno)"
        )
    deuda = await _deuda_bloqueada(db, usuario.tenant_id, body.comprobante_id)
    if body.importe > deuda.saldo:
        raise HTTPException(status_code=422, detail="La imputación supera el saldo de la deuda")

    if body.recibo_id is not None:
        recibo = await db.scalar(
            select(Recibo)
            .where(
                Recibo.id == body.recibo_id,
                Recibo.tenant_id == usuario.tenant_id,
                Recibo.estado == "emitido",
            )
            .with_for_update(of=Recibo)
        )
        if recibo is None:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")
        if recibo.cliente_id != deuda.cliente_id:
            raise HTTPException(status_code=422, detail="Recibo y deuda de clientes distintos")
        disponible = recibo.total - recibo.aplicado
        if body.importe > disponible:
            raise HTTPException(
                status_code=422, detail=f"El recibo solo tiene ${disponible} a cuenta"
            )
        recibo.aplicado = recibo.aplicado + body.importe
    else:
        credito = await db.scalar(
            select(Comprobante)
            .where(
                Comprobante.id == body.credito_id,
                Comprobante.tenant_id == usuario.tenant_id,
                Comprobante.estado == "emitido",
            )
            .with_for_update(of=Comprobante)
        )
        if credito is None:
            raise HTTPException(status_code=404, detail="Nota de crédito no encontrada")
        tipo = await db.scalar(
            select(TipoComprobante).where(TipoComprobante.codigo == credito.tipo_codigo)
        )
        if tipo.signo_cta_cte != -1:
            raise HTTPException(status_code=422, detail="El crédito debe ser una NC emitida")
        if credito.cliente_id != deuda.cliente_id:
            raise HTTPException(status_code=422, detail="NC y deuda de clientes distintos")
        if body.importe > credito.saldo:
            raise HTTPException(
                status_code=422, detail=f"La NC solo tiene ${credito.saldo} disponibles"
            )
        credito.saldo = credito.saldo - body.importe

    deuda.saldo = deuda.saldo - body.importe
    db.add(
        Imputacion(
            tenant_id=usuario.tenant_id,
            cliente_id=deuda.cliente_id,
            recibo_id=body.recibo_id,
            credito_id=body.credito_id,
            comprobante_id=deuda.id,
            importe=body.importe,
            creado_por=usuario.id,
        )
    )
    await db.commit()
    return {"ok": True, "saldo_restante_deuda": str(deuda.saldo)}


# ===== Cuenta corriente y saldos =====

@router.get("/cuenta-corriente/{cliente_id}")
async def cuenta_corriente(
    cliente_id: uuid.UUID,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(requiere("clientes", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Movimientos históricos (debe/haber) + saldo actual del cliente."""
    await _cliente(db, usuario.tenant_id, cliente_id)

    # Proyección de columnas + filtro de fechas en SQL: antes cargaba los ORM
    # completos de TODA la historia (con items/alícuotas/vencimientos por
    # selectin) y filtraba en Python. El acumulado sigue arrancando en 0 en
    # la ventana filtrada (semántica original).
    stmt_c = (
        select(
            Comprobante.fecha,
            Comprobante.created_at,
            TipoComprobante.descripcion,
            PuntoVenta.numero.label("pv_numero"),
            Comprobante.numero,
            Comprobante.total,
            Comprobante.saldo,
            Comprobante.contado,
            TipoComprobante.signo_cta_cte,
        )
        .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
        .join(PuntoVenta, Comprobante.punto_venta_id == PuntoVenta.id)
        .where(
            Comprobante.tenant_id == usuario.tenant_id,
            Comprobante.cliente_id == cliente_id,
            Comprobante.estado == "emitido",
            TipoComprobante.fiscal.is_(True),
        )
    )
    stmt_r = (
        select(
            Recibo.fecha,
            Recibo.created_at,
            PuntoVenta.numero.label("pv_numero"),
            Recibo.numero,
            Recibo.total,
            Recibo.aplicado,
        )
        .join(PuntoVenta, Recibo.punto_venta_id == PuntoVenta.id)
        .where(
            Recibo.tenant_id == usuario.tenant_id,
            Recibo.cliente_id == cliente_id,
            Recibo.estado == "emitido",
        )
    )
    if desde:
        stmt_c = stmt_c.where(Comprobante.fecha >= desde)
        stmt_r = stmt_r.where(Recibo.fecha >= desde)
    if hasta:
        stmt_c = stmt_c.where(Comprobante.fecha <= hasta)
        stmt_r = stmt_r.where(Recibo.fecha <= hasta)
    comps = (await db.execute(stmt_c)).all()
    recibos = (await db.execute(stmt_r)).all()

    movimientos = []
    for c in comps:
        # comprobantes contado no mueven la cta. cte. (pagados en el acto)
        if c.contado and c.signo_cta_cte == 1:
            continue
        debe = c.total if c.signo_cta_cte == 1 else Decimal("0")
        haber = c.total if c.signo_cta_cte == -1 else Decimal("0")
        movimientos.append(
            {
                "fecha": c.fecha.isoformat(),
                "orden": c.created_at.isoformat(),
                "tipo": c.descripcion,
                "numero": f"{c.pv_numero:04d}-{c.numero:08d}",
                "debe": str(debe),
                "haber": str(haber),
                "pendiente": str(c.saldo),
            }
        )
    for r in recibos:
        movimientos.append(
            {
                "fecha": r.fecha.isoformat(),
                "orden": r.created_at.isoformat(),
                "tipo": "Recibo",
                "numero": f"{r.pv_numero:04d}-{r.numero:08d}",
                "debe": "0",
                "haber": str(r.total),
                "pendiente": str(r.total - r.aplicado),
            }
        )
    movimientos.sort(key=lambda m: (m["fecha"], m["orden"]))

    acumulado = Decimal("0")
    for m in movimientos:
        acumulado += Decimal(m["debe"]) - Decimal(m["haber"])
        m["saldo_acumulado"] = str(acumulado)

    saldo_total = await _saldo_cliente(db, usuario.tenant_id, cliente_id)
    return {"movimientos": movimientos, "saldo": str(saldo_total)}


async def _saldo_cliente(
    db: AsyncSession, tenant_id: uuid.UUID, cliente_id: uuid.UUID
) -> Decimal:
    """deuda pendiente (facturas/ND.saldo) − créditos NC.saldo − a cuenta de recibos."""
    deuda = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.saldo), 0))
        .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
        .where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.cliente_id == cliente_id,
            Comprobante.estado == "emitido",
            TipoComprobante.signo_cta_cte == 1,
        )
    )
    creditos = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.saldo), 0))
        .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
        .where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.cliente_id == cliente_id,
            Comprobante.estado == "emitido",
            TipoComprobante.signo_cta_cte == -1,
        )
    )
    a_cuenta = await db.scalar(
        select(func.coalesce(func.sum(Recibo.total - Recibo.aplicado), 0)).where(
            Recibo.tenant_id == tenant_id,
            Recibo.cliente_id == cliente_id,
            Recibo.estado == "emitido",
        )
    )
    return Decimal(deuda) - Decimal(creditos) - Decimal(a_cuenta)


@router.get("/saldos")
async def saldos_por_cliente(
    solo_deudores: bool = True,
    usuario: Usuario = Depends(requiere("clientes", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Listado de saldos (morosidad-lite): saldo total y vencido por cliente."""
    from app.models import ComprobanteVencimiento

    hoy = date.today()
    filas = (
        await db.execute(
            select(
                Comprobante.cliente_id,
                func.sum(Comprobante.saldo * TipoComprobante.signo_cta_cte).label("saldo"),
            )
            .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
            .where(
                Comprobante.tenant_id == usuario.tenant_id,
                Comprobante.cliente_id.is_not(None),
                Comprobante.estado == "emitido",
                TipoComprobante.fiscal.is_(True),
                Comprobante.saldo != 0,
            )
            .group_by(Comprobante.cliente_id)
        )
    ).all()
    saldos = {cid: Decimal(s) for cid, s in filas}

    a_cuenta_filas = (
        await db.execute(
            select(Recibo.cliente_id, func.sum(Recibo.total - Recibo.aplicado))
            .where(
                Recibo.tenant_id == usuario.tenant_id,
                Recibo.estado == "emitido",
                Recibo.total != Recibo.aplicado,
            )
            .group_by(Recibo.cliente_id)
        )
    ).all()
    for cid, ac in a_cuenta_filas:
        saldos[cid] = saldos.get(cid, Decimal("0")) - Decimal(ac)

    # vencido: cuotas con fecha pasada de facturas/ND que aún tienen saldo
    vencido_filas = (
        await db.execute(
            select(
                Comprobante.cliente_id,
                func.sum(ComprobanteVencimiento.importe),
                func.sum(Comprobante.total - Comprobante.saldo),
            )
            .join(
                ComprobanteVencimiento,
                ComprobanteVencimiento.comprobante_id == Comprobante.id,
            )
            .where(
                Comprobante.tenant_id == usuario.tenant_id,
                Comprobante.estado == "emitido",
                Comprobante.saldo > 0,
                ComprobanteVencimiento.fecha_vto < hoy,
            )
            .group_by(Comprobante.cliente_id)
        )
    ).all()
    vencidos = {}
    for cid, venc, pagado in vencido_filas:
        vencidos[cid] = max(Decimal("0"), Decimal(venc) - Decimal(pagado or 0))

    if not saldos:
        return []
    clientes = (
        await db.execute(
            select(Cliente, Entidad)
            .join(Entidad, Cliente.entidad_id == Entidad.id)
            .where(Cliente.id.in_(saldos.keys()), Cliente.tenant_id == usuario.tenant_id)
        )
    ).all()
    resultado = []
    for cliente, entidad in clientes:
        saldo = saldos.get(cliente.id, Decimal("0"))
        if solo_deudores and saldo <= 0:
            continue
        resultado.append(
            {
                "cliente_id": str(cliente.id),
                "codigo": cliente.codigo,
                "nombre": entidad.razon_social,
                "saldo": str(saldo),
                "vencido": str(vencidos.get(cliente.id, Decimal("0"))),
                "limite_credito": str(cliente.limite_credito) if cliente.limite_credito else None,
            }
        )
    resultado.sort(key=lambda x: Decimal(x["saldo"]), reverse=True)
    return resultado
