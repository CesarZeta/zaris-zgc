"""Tesorería — cash-flow proyectado (Fase 8).

Reporte (no tabla): proyecta el saldo de tesorería a futuro sobre datos que YA
existen, sin pedir carga nueva.

  saldo inicial  = efectivo en caja (F5) + Σ saldos de cuentas bancarias
  entradas       = vencimientos de cta.cte. de clientes (facturas/ND con saldo)
                   + cheques de tercero en cartera (por fecha_pago)
  salidas        = vencimientos de cta.cte. de proveedores (compras con saldo)
                   + cheques propios emitidos (por fecha_pago)

Las agregaciones que arrancan con func escalar llevan .select_from() explícito
(lección Fase 7). RBAC `bancos`.
"""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    BancoMovimiento,
    CajaMovimiento,
    Cheque,
    Compra,
    Comprobante,
    ComprobanteVencimiento,
    ConceptoCaja,
    CompraVencimiento,
    CuentaBancaria,
    TipoComprobante,
    TipoComprobanteCompra,
    Usuario,
)

router = APIRouter(prefix="/tesoreria", tags=["tesoreria"])

SIGNO_MOV = {
    "deposito": +1, "transferencia_in": +1, "credito": +1, "ajuste_positivo": +1,
    "extraccion": -1, "transferencia_out": -1, "debito": -1, "comision": -1,
    "ajuste_negativo": -1,
}


async def _saldo_caja(db: AsyncSession, tenant_id: uuid.UUID) -> Decimal:
    """Efectivo neto acumulado (entradas − salidas) de caja_movimientos."""
    filas = (
        await db.execute(
            select(ConceptoCaja.tipo, func.coalesce(func.sum(CajaMovimiento.importe), 0))
            .select_from(CajaMovimiento)
            .join(ConceptoCaja, CajaMovimiento.concepto_id == ConceptoCaja.id)
            .where(
                CajaMovimiento.tenant_id == tenant_id,
                CajaMovimiento.medio == "efectivo",
                CajaMovimiento.anulado_at.is_(None),
            )
            .group_by(ConceptoCaja.tipo)
        )
    ).all()
    saldo = Decimal("0")
    for tipo, suma in filas:
        saldo += Decimal(suma) * (1 if tipo == "entrada" else -1)
    return saldo


async def _saldo_bancos(db: AsyncSession, tenant_id: uuid.UUID) -> Decimal:
    inicial = await db.scalar(
        select(func.coalesce(func.sum(CuentaBancaria.saldo_inicial), 0))
        .where(CuentaBancaria.tenant_id == tenant_id, CuentaBancaria.activa.is_(True))
    )
    filas = (
        await db.execute(
            select(BancoMovimiento.tipo, func.coalesce(func.sum(BancoMovimiento.importe), 0))
            .select_from(BancoMovimiento)
            .join(CuentaBancaria, BancoMovimiento.cuenta_id == CuentaBancaria.id)
            .where(
                CuentaBancaria.tenant_id == tenant_id,
                CuentaBancaria.activa.is_(True),
                BancoMovimiento.anulado_at.is_(None),
            )
            .group_by(BancoMovimiento.tipo)
        )
    ).all()
    saldo = Decimal(inicial or 0)
    for tipo, suma in filas:
        saldo += Decimal(suma) * SIGNO_MOV.get(tipo, 1)
    return saldo


def _bucket(d: date, granularidad: str) -> date:
    if granularidad == "mes":
        return d.replace(day=1)
    if granularidad == "semana":
        return d - timedelta(days=d.weekday())
    return d


@router.get("/cashflow")
async def cashflow(
    desde: date | None = None,
    hasta: date | None = None,
    granularidad: str = Query("semana", pattern="^(dia|semana|mes)$"),
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    hoy = date.today()
    desde = desde or hoy
    hasta = hasta or (hoy + timedelta(days=90))
    tid = usuario.tenant_id

    saldo_inicial = (await _saldo_caja(db, tid)) + (await _saldo_bancos(db, tid))

    entradas: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    salidas: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    detalle: dict[date, list] = defaultdict(list)

    def _agrega(mapa, venc: date, importe: Decimal, concepto: str, ref: str):
        b = _bucket(max(venc, desde), granularidad)
        mapa[b] += importe
        detalle[b].append({"concepto": concepto, "referencia": ref, "importe": str(importe)})

    # --- Entradas: vencimientos de clientes (facturas/ND con saldo) ---
    venc_cli = (
        await db.execute(
            select(
                ComprobanteVencimiento.fecha_vto,
                ComprobanteVencimiento.importe,
                Comprobante.saldo,
                Comprobante.total,
                Comprobante.numero,
            )
            .select_from(ComprobanteVencimiento)
            .join(Comprobante, ComprobanteVencimiento.comprobante_id == Comprobante.id)
            .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
            .where(
                Comprobante.tenant_id == tid,
                Comprobante.estado == "emitido",
                Comprobante.saldo > 0,
                TipoComprobante.signo_cta_cte == 1,
                ComprobanteVencimiento.fecha_vto <= hasta,
            )
        )
    ).all()
    for fv, imp, saldo, total, numero in venc_cli:
        # la cuota proyecta hasta lo que reste de saldo del comprobante
        proyecta = min(Decimal(imp), Decimal(saldo))
        if proyecta > 0:
            _agrega(entradas, fv, proyecta, "Cobro a vencer", f"Fac #{numero}")

    # --- Entradas: cheques de tercero en cartera (por fecha_pago) ---
    ch_in = (
        await db.scalars(
            select(Cheque).where(
                Cheque.tenant_id == tid,
                Cheque.clase == "tercero",
                Cheque.estado.in_(("en_cartera", "depositado")),
                Cheque.fecha_pago <= hasta,
            )
        )
    ).all()
    for c in ch_in:
        _agrega(entradas, c.fecha_pago, Decimal(c.importe), "Cheque a cobrar", f"Cheq {c.numero}")

    # --- Salidas: vencimientos de proveedores (compras con saldo) ---
    venc_prov = (
        await db.execute(
            select(
                CompraVencimiento.fecha_vto,
                CompraVencimiento.importe,
                Compra.saldo,
                Compra.numero,
            )
            .select_from(CompraVencimiento)
            .join(Compra, CompraVencimiento.compra_id == Compra.id)
            .join(TipoComprobanteCompra, Compra.tipo_codigo == TipoComprobanteCompra.codigo)
            .where(
                Compra.tenant_id == tid,
                Compra.estado == "registrado",
                Compra.saldo > 0,
                TipoComprobanteCompra.signo_cta_cte == 1,
                CompraVencimiento.fecha_vto <= hasta,
            )
        )
    ).all()
    for fv, imp, saldo, numero in venc_prov:
        proyecta = min(Decimal(imp), Decimal(saldo))
        if proyecta > 0:
            _agrega(salidas, fv, proyecta, "Pago a vencer", f"Compra #{numero}")

    # --- Salidas: cheques propios emitidos (por fecha_pago) ---
    ch_out = (
        await db.scalars(
            select(Cheque).where(
                Cheque.tenant_id == tid,
                Cheque.clase == "propio",
                Cheque.estado == "emitido",
                Cheque.fecha_pago <= hasta,
            )
        )
    ).all()
    for c in ch_out:
        _agrega(salidas, c.fecha_pago, Decimal(c.importe), "Cheque propio a debitar", f"Cheq {c.numero}")

    # --- Serie temporal acumulada ---
    buckets = sorted(set(entradas) | set(salidas))
    serie = []
    saldo = saldo_inicial
    for b in buckets:
        ent = entradas.get(b, Decimal("0"))
        sal = salidas.get(b, Decimal("0"))
        saldo = saldo + ent - sal
        serie.append(
            {
                "fecha": b.isoformat(),
                "entradas": str(ent),
                "salidas": str(sal),
                "saldo_proyectado": str(saldo),
                "detalle": detalle.get(b, []),
            }
        )

    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "granularidad": granularidad,
        "saldo_inicial": str(saldo_inicial),
        "serie": serie,
    }
