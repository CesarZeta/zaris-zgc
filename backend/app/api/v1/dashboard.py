"""Dashboard — KPIs agregados en tiempo real (Fase 7).

Conecta los 4 KPIs que el inicio tenía en skeleton. Cada indicador es una
agregación acotada por tenant; el endpoint compuesto respeta el permiso del
módulo natural de cada KPI y devuelve null (no 403) en los que el usuario no
puede ver, para que el inicio nunca se rompa.

Semántica alineada con los módulos existentes:
- Ventas del mes: comprobantes fiscales emitidos del mes en curso, netos de NC
  (signo_cta_cte), como el libro IVA ventas.
- Cobros pendientes: saldo deudor de clientes (comprobantes emitidos con saldo>0),
  mismo criterio que la cta. cte. de cobranzas.
- Stock valorizado: Σ cantidad × costo neto (descontando IVA si el costo lo
  incluye), como la valorización de Stock.
- Saldo de caja: efectivo del día = cobranzas efectivo − pagos efectivo +
  movimientos manuales de efectivo (entradas−salidas), criterio de la planilla F5.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.core.permisos import permisos_efectivos
from app.models import (
    Articulo,
    ArticuloStock,
    CajaMovimiento,
    Comprobante,
    OrdenPago,
    OrdenPagoMedio,
    Recibo,
    ReciboMedio,
    TipoComprobante,
    Usuario,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_CENT = Decimal("0.01")


def _q(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return str(v.quantize(_CENT))


async def _ventas_del_mes(db: AsyncSession, tenant_id, hoy: date) -> Decimal:
    inicio = hoy.replace(day=1)
    total = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.total * TipoComprobante.signo_cta_cte), 0))
        .select_from(Comprobante)
        .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
        .where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.estado == "emitido",
            TipoComprobante.fiscal.is_(True),
            Comprobante.fecha >= inicio,
            Comprobante.fecha <= hoy,
        )
    )
    return total or Decimal("0")


async def _cobros_pendientes(db: AsyncSession, tenant_id) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.saldo * TipoComprobante.signo_cta_cte), 0))
        .select_from(Comprobante)
        .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
        .where(
            Comprobante.tenant_id == tenant_id,
            Comprobante.estado == "emitido",
            Comprobante.saldo > 0,
        )
    )
    return total or Decimal("0")


async def _stock_valorizado(db: AsyncSession, tenant_id) -> Decimal:
    costo_neto = case(
        (Articulo.costo_con_iva.is_(True), Articulo.costo / (1 + Articulo.tasa_iva / 100)),
        else_=Articulo.costo,
    )
    # Solo existencias positivas: el valorizado es el valor del inventario que
    # HAY, no una deuda de stock. Un saldo negativo (vendido sin reponer) es un
    # faltante — se ve en el kardex/Stock, no resta valor al inventario.
    cantidad_pos = func.greatest(ArticuloStock.cantidad, 0)
    total = await db.scalar(
        select(func.coalesce(func.sum(cantidad_pos * costo_neto), 0))
        .select_from(ArticuloStock)
        .join(Articulo, Articulo.id == ArticuloStock.articulo_id)
        .where(ArticuloStock.tenant_id == tenant_id, Articulo.activo.is_(True))
    )
    return total or Decimal("0")


async def _saldo_caja(db: AsyncSession, tenant_id, hoy: date) -> Decimal:
    cobrado = await db.scalar(
        select(func.coalesce(func.sum(ReciboMedio.importe), 0))
        .select_from(ReciboMedio)
        .join(Recibo, Recibo.id == ReciboMedio.recibo_id)
        .where(
            Recibo.tenant_id == tenant_id,
            Recibo.estado == "emitido",
            Recibo.fecha == hoy,
            ReciboMedio.medio == "efectivo",
        )
    )
    pagado = await db.scalar(
        select(func.coalesce(func.sum(OrdenPagoMedio.importe), 0))
        .select_from(OrdenPagoMedio)
        .join(OrdenPago, OrdenPago.id == OrdenPagoMedio.orden_pago_id)
        .where(
            OrdenPago.tenant_id == tenant_id,
            OrdenPago.estado == "emitida",
            OrdenPago.fecha == hoy,
            OrdenPagoMedio.medio == "efectivo",
        )
    )
    manuales = await db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (CajaMovimiento.tipo == "entrada", CajaMovimiento.importe),
                        else_=-CajaMovimiento.importe,
                    )
                ),
                0,
            )
        ).where(
            CajaMovimiento.tenant_id == tenant_id,
            CajaMovimiento.fecha == hoy,
            CajaMovimiento.medio == "efectivo",
        )
    )
    return (cobrado or Decimal("0")) - (pagado or Decimal("0")) + (manuales or Decimal("0"))


@router.get("/kpis")
async def kpis(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """KPIs del inicio. Cada uno respeta el permiso de su módulo: si el usuario
    no lo tiene, el valor va en null (el inicio muestra '—')."""
    permisos = await permisos_efectivos(db, usuario)
    tenant_id = usuario.tenant_id
    hoy = (await db.scalar(select(func.current_date()))) or date.today()

    def puede(modulo: str) -> bool:
        return modulo in permisos  # cualquier nivel ≥ ver

    ventas = await _ventas_del_mes(db, tenant_id, hoy) if puede("ventas") else None
    cobros = await _cobros_pendientes(db, tenant_id) if puede("ventas") else None
    stock = await _stock_valorizado(db, tenant_id) if puede("stock") else None
    caja = await _saldo_caja(db, tenant_id, hoy) if puede("caja") else None

    return {
        "fecha": hoy.isoformat(),
        "ventas_mes": _q(ventas),
        "cobros_pendientes": _q(cobros),
        "stock_valorizado": _q(stock),
        "saldo_caja": _q(caja),
    }
