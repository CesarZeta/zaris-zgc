"""Núcleo de transiciones de cheques (Fase 8) — SIN commit.

Patrón emitir_core (CLAUDE.md §6): estas funciones mutan la sesión pero NO
commitean, para que la cobranza (ventas), la orden de pago (compras) y los
endpoints de cheques las llamen dentro de su propia transacción sin duplicar
lógica. Cada transición escribe un ChequeEvento y, cuando toca banco, crea o
concilia un BancoMovimiento.

Máquina de estados (docs/DISENO-CHEQUES-Y-BANCOS.md §2):
  tercero: en_cartera → depositado → acreditado
                     ↘ endosado          ↘ (rechazar)
           en_cartera → rechazado / anulado
  propio:  emitido → debitado / anulado
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BancoMovimiento,
    Cheque,
    ChequeEvento,
    CuentaBancaria,
    Recibo,
)

# Estados finales (no admiten más transiciones salvo las indicadas).
ESTADOS_TERCERO = {"en_cartera", "depositado", "acreditado", "endosado", "rechazado", "anulado"}
ESTADOS_PROPIO = {"emitido", "debitado", "anulado"}


def _evento(
    cheque: Cheque,
    desde: str | None,
    hasta: str,
    detalle: str | None = None,
    banco_movimiento_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    fecha: date | None = None,
) -> ChequeEvento:
    return ChequeEvento(
        tenant_id=cheque.tenant_id,
        cheque_id=cheque.id,
        fecha=fecha or date.today(),
        estado_desde=desde,
        estado_hasta=hasta,
        detalle=detalle,
        banco_movimiento_id=banco_movimiento_id,
        creado_por=usuario_id,
    )


async def _cuenta(db: AsyncSession, tenant_id: uuid.UUID, cuenta_id: uuid.UUID) -> CuentaBancaria:
    cuenta = await db.scalar(
        select(CuentaBancaria).where(
            CuentaBancaria.id == cuenta_id,
            CuentaBancaria.tenant_id == tenant_id,
            CuentaBancaria.activa.is_(True),
        )
    )
    if cuenta is None:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada o inactiva")
    return cuenta


# ===== Altas =====

async def recibir_tercero(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    datos: dict,
    cliente_id: uuid.UUID | None = None,
    recibo_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
) -> Cheque:
    """Alta de un cheque de tercero en cartera (recibido en una cobranza o a mano).
    `datos` trae numero/banco/fecha_pago/importe/... (validado por el schema del caller)."""
    cheque = Cheque(
        tenant_id=tenant_id,
        clase="tercero",
        estado="en_cartera",
        cliente_id=cliente_id,
        recibo_id=recibo_id,
        creado_por=usuario_id,
        **datos,
    )
    db.add(cheque)
    await db.flush()
    db.add(_evento(cheque, None, "en_cartera", "Recibido en cartera", usuario_id=usuario_id))
    return cheque


async def emitir_propio(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    datos: dict,
    cuenta_id: uuid.UUID,
    proveedor_id: uuid.UUID | None = None,
    orden_pago_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
) -> Cheque:
    """Emisión de un cheque propio contra una cuenta bancaria (pasivo).
    El `banco` del cheque se toma de la cuenta (no lo pasa el caller)."""
    cuenta = await _cuenta(db, tenant_id, cuenta_id)
    datos = {**datos, "banco": cuenta.banco, "moneda": cuenta.moneda}
    cheque = Cheque(
        tenant_id=tenant_id,
        clase="propio",
        estado="emitido",
        cuenta_id=cuenta_id,
        proveedor_id=proveedor_id,
        orden_pago_id=orden_pago_id,
        creado_por=usuario_id,
        **datos,
    )
    db.add(cheque)
    await db.flush()
    db.add(
        _evento(
            cheque, None, "emitido",
            "Emitido" + (" (entregado a proveedor)" if proveedor_id else ""),
            usuario_id=usuario_id,
        )
    )
    return cheque


# ===== Transiciones de cheque de tercero =====

async def depositar(
    db: AsyncSession, *, cheque: Cheque, cuenta_id: uuid.UUID,
    fecha: date | None = None, usuario_id: uuid.UUID | None = None,
) -> BancoMovimiento:
    """en_cartera → depositado. Crea el movimiento bancario (NO conciliado aún)."""
    if cheque.clase != "tercero" or cheque.estado != "en_cartera":
        raise HTTPException(status_code=409, detail="Solo se depositan cheques de tercero en cartera")
    cuenta = await _cuenta(db, cheque.tenant_id, cuenta_id)
    if cuenta.moneda != cheque.moneda:
        raise HTTPException(status_code=422, detail="Moneda de la cuenta distinta a la del cheque")
    mov = BancoMovimiento(
        tenant_id=cheque.tenant_id,
        cuenta_id=cuenta_id,
        fecha=fecha or date.today(),
        tipo="deposito",
        importe=cheque.importe,
        descripcion=f"Depósito cheque {cheque.numero} ({cheque.banco})",
        cheque_id=cheque.id,
        origen="cheque",
        creado_por=usuario_id,
    )
    db.add(mov)
    await db.flush()
    cheque.estado = "depositado"
    cheque.cuenta_id = cuenta_id
    cheque.banco_movimiento_id = mov.id
    db.add(_evento(cheque, "en_cartera", "depositado", f"Depositado en {cuenta.banco}",
                   banco_movimiento_id=mov.id, usuario_id=usuario_id, fecha=fecha))
    return mov


async def acreditar(
    db: AsyncSession, *, cheque: Cheque, fecha: date | None = None,
    usuario_id: uuid.UUID | None = None,
) -> None:
    """depositado → acreditado. Concilia el movimiento de depósito."""
    if cheque.estado != "depositado":
        raise HTTPException(status_code=409, detail="Solo se acredita un cheque depositado")
    if cheque.banco_movimiento_id:
        mov = await db.scalar(
            select(BancoMovimiento).where(BancoMovimiento.id == cheque.banco_movimiento_id)
        )
        if mov and not mov.conciliado:
            mov.conciliado = True
            mov.fecha_conciliacion = fecha or date.today()
    cheque.estado = "acreditado"
    db.add(_evento(cheque, "depositado", "acreditado", "Acreditado por el banco",
                   banco_movimiento_id=cheque.banco_movimiento_id, usuario_id=usuario_id, fecha=fecha))


async def endosar(
    db: AsyncSession, *, cheque: Cheque, proveedor_id: uuid.UUID,
    orden_pago_id: uuid.UUID | None = None, fecha: date | None = None,
    usuario_id: uuid.UUID | None = None,
) -> None:
    """en_cartera → endosado (pago a proveedor). No toca banco."""
    if cheque.clase != "tercero" or cheque.estado != "en_cartera":
        raise HTTPException(status_code=409, detail="Solo se endosa un cheque de tercero en cartera")
    cheque.estado = "endosado"
    cheque.proveedor_id = proveedor_id
    cheque.orden_pago_id = orden_pago_id
    db.add(_evento(cheque, "en_cartera", "endosado", "Endosado a proveedor",
                   usuario_id=usuario_id, fecha=fecha))


async def rechazar(
    db: AsyncSession, *, cheque: Cheque, fecha: date | None = None,
    detalle: str | None = None, usuario_id: uuid.UUID | None = None,
) -> dict:
    """(en_cartera|depositado) → rechazado. Si vino de una cobranza, reabre la
    deuda del cliente reduciendo el 'a cuenta' del recibo (el dinero nunca entró).

    Devuelve un dict con lo que reabrió, para que el caller lo reporte."""
    if cheque.clase != "tercero" or cheque.estado not in ("en_cartera", "depositado"):
        raise HTTPException(
            status_code=409, detail="Solo se rechaza un cheque de tercero en cartera o depositado"
        )
    desde = cheque.estado
    reabierto = None
    if cheque.recibo_id:
        recibo = await db.scalar(
            select(Recibo)
            .where(Recibo.id == cheque.recibo_id, Recibo.tenant_id == cheque.tenant_id)
            .with_for_update(of=Recibo)
        )
        # Solo revierte contra 'a cuenta' disponible del recibo (el dinero del
        # cheque que aún no se imputó a una deuda concreta). Si el recibo ya
        # imputó ese importe a facturas, se exige regularización manual (evita
        # dejar recibo.total < recibo.aplicado, que rompería la cta.cte.).
        if recibo and recibo.estado == "emitido":
            disponible = recibo.total - recibo.aplicado
            if disponible >= cheque.importe:
                recibo.total = recibo.total - cheque.importe
                reabierto = {
                    "recibo_id": str(recibo.id),
                    "importe_revertido": str(cheque.importe),
                }
    cheque.estado = "rechazado"
    db.add(_evento(cheque, desde, "rechazado", detalle or "Rechazado sin fondos",
                   usuario_id=usuario_id, fecha=fecha))
    return {"reabierto": reabierto}


# ===== Transiciones de cheque propio =====

async def debitar(
    db: AsyncSession, *, cheque: Cheque, fecha: date | None = None,
    usuario_id: uuid.UUID | None = None,
) -> BancoMovimiento:
    """emitido → debitado. El banco pagó el cheque propio: movimiento débito conciliado."""
    if cheque.clase != "propio" or cheque.estado != "emitido":
        raise HTTPException(status_code=409, detail="Solo se debita un cheque propio emitido")
    if cheque.cuenta_id is None:
        raise HTTPException(status_code=422, detail="El cheque propio no tiene cuenta asociada")
    mov = BancoMovimiento(
        tenant_id=cheque.tenant_id,
        cuenta_id=cheque.cuenta_id,
        fecha=fecha or date.today(),
        tipo="debito",
        importe=cheque.importe,
        descripcion=f"Débito cheque propio {cheque.numero}",
        cheque_id=cheque.id,
        conciliado=True,
        fecha_conciliacion=fecha or date.today(),
        origen="cheque",
        creado_por=usuario_id,
    )
    db.add(mov)
    await db.flush()
    cheque.estado = "debitado"
    cheque.banco_movimiento_id = mov.id
    db.add(_evento(cheque, "emitido", "debitado", "Debitado por el banco",
                   banco_movimiento_id=mov.id, usuario_id=usuario_id, fecha=fecha))
    return mov


async def anular(
    db: AsyncSession, *, cheque: Cheque, detalle: str | None = None,
    usuario_id: uuid.UUID | None = None,
) -> None:
    """Anula un cheque (error de carga). Solo desde estados no-finales de banco."""
    if cheque.estado in ("acreditado", "debitado", "endosado", "anulado"):
        raise HTTPException(
            status_code=409, detail=f"No se puede anular un cheque {cheque.estado}"
        )
    desde = cheque.estado
    cheque.estado = "anulado"
    db.add(_evento(cheque, desde, "anulado", detalle or "Anulado", usuario_id=usuario_id))
