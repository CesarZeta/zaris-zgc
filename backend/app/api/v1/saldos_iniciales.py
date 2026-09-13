"""Saldo inicial de cuenta corriente (029 — DISENO-CONTABILIDAD.md §7).

Carga la deuda/crédito vivo de un cliente o proveedor como documento interno
de cta. cte. (clase `saldo_inicial`, letra X, sin ítems, `fiscal=false`).
Nace emitido/registrado: no hay borrador, UPDATE ni endpoint propio de
anulación — se anula por los endpoints existentes de ventas/compras (con la
guarda de imputaciones vivas) y se carga otro.

Nube-only (`ROUTERS_NUBE` en main.py): el nodo LAN no lo emite ni lo replica.
Los cores viven en `services/saldos_iniciales.py` (sin commit; los reusan los
migradores del legacy) — acá solo hay schemas, guardas RBAC y commit.
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.compras import CompraOut
from app.api.v1.compras import _cargar as _cargar_compra
from app.api.v1.compras import _out as _out_compra
from app.api.v1.comprobantes import ComprobanteOut
from app.api.v1.comprobantes import _cargar as _cargar_comprobante
from app.api.v1.comprobantes import _out as _out_comprobante
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import Usuario
from app.services import saldos_iniciales as ssi

router = APIRouter(prefix="", tags=["saldos-iniciales"])


# ===== Schemas =====

class SaldoInicialVentaIn(BaseModel):
    cliente_id: uuid.UUID
    importe: Decimal = Field(gt=0)
    sentido: str = Field(pattern="^(deudor|a_favor)$")  # deudor = nos debe (SAL); a_favor = SAF
    fecha: date | None = None  # default hoy; futura → 422
    observaciones: str | None = Field(None, max_length=500)
    # opcional: PV con el que numera. Sin él, el primer PV activo que la nube
    # pueda operar (los PV de un nodo LAN quedan excluidos siempre).
    punto_venta_id: uuid.UUID | None = None


class SaldoInicialCompraIn(BaseModel):
    proveedor_id: uuid.UUID
    importe: Decimal = Field(gt=0)
    sentido: str = Field(pattern="^(debemos|nos_deben)$")  # debemos = SALP; nos_deben = SAFP
    fecha: date | None = None
    observaciones: str | None = Field(None, max_length=500)


# ===== Endpoints =====

@router.post(
    "/ventas/saldos-iniciales",
    response_model=ComprobanteOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_saldo_inicial_cliente(
    body: SaldoInicialVentaIn,
    usuario: Usuario = Depends(requiere("ventas", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """SAL (deudor) / SAF (a favor) de un cliente, emitido en el acto."""
    try:
        comp = await ssi.crear_saldo_inicial_venta(
            db,
            usuario.tenant_id,
            usuario.id,
            body.cliente_id,
            body.importe,
            body.sentido,
            fecha=body.fecha,
            observaciones=body.observaciones,
            punto_venta_id=body.punto_venta_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return _out_comprobante(await _cargar_comprobante(db, usuario.tenant_id, comp.id))


@router.post(
    "/compras/saldos-iniciales",
    response_model=CompraOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_saldo_inicial_proveedor(
    body: SaldoInicialCompraIn,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """SALP (le debemos) / SAFP (nos debe) de un proveedor, registrado en el acto."""
    try:
        compra = await ssi.crear_saldo_inicial_compra(
            db,
            usuario.tenant_id,
            usuario.id,
            body.proveedor_id,
            body.importe,
            body.sentido,
            fecha=body.fecha,
            observaciones=body.observaciones,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return _out_compra(await _cargar_compra(db, usuario.tenant_id, compra.id))
