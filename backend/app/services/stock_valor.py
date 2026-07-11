"""Valorización del kardex (014 — mini-fase Contabilizabilidad).

Cada movimiento de stock sella `costo_unitario` = costo NETO de IVA y en ARS
al momento del movimiento, para que el kardex sea valorizable retroactivamente
(inventario permanente a costo de reposición; ver docs/DISENO-CONTABILIDAD.md).

Convención por tipo de movimiento:
- compra/remito de compra: costo REAL del documento (importe_neto/cantidad del
  ítem — en letra A es neto; en B/C el final entero ES el costo, criterio F4).
- venta/devolución/ajuste/transferencia/inicial: costo vigente del artículo
  normalizado con `costo_neto_ars` (neteo de IVA si costo_con_iva, conversión
  USD→ARS por la cotización vigente del tenant).
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Articulo, Cotizacion

_CIEN = Decimal("100")
_CUATRO = Decimal("0.0001")


def _r4(x: Decimal) -> Decimal:
    return x.quantize(_CUATRO, rounding=ROUND_HALF_UP)


async def cotizacion_vigente(db: AsyncSession, tenant_id: uuid.UUID) -> Decimal:
    """Última cotización USD del tenant (1 si nunca cargó ninguna)."""
    valor = await db.scalar(
        select(Cotizacion.valor)
        .where(Cotizacion.tenant_id == tenant_id)
        .order_by(desc(Cotizacion.vigente_desde))
        .limit(1)
    )
    return Decimal(valor) if valor else Decimal("1")


def costo_neto_ars(articulo: Articulo, cotizacion: Decimal) -> Decimal:
    """Costo unitario vigente del artículo, neto de IVA y en ARS."""
    costo = Decimal(articulo.costo or 0)
    if articulo.costo_con_iva and articulo.tasa_iva:
        costo = costo / (1 + Decimal(articulo.tasa_iva) / _CIEN)
    if articulo.en_dolares:
        costo = costo * cotizacion
    return _r4(costo)


def costo_item_compra(importe_neto: Decimal, cantidad: Decimal) -> Decimal:
    """Costo unitario real del ítem de compra (neto tras bonifs; B/C = final)."""
    if not cantidad:
        return Decimal("0")
    return _r4(Decimal(importe_neto) / Decimal(cantidad))
