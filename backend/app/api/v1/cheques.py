"""Cheques — cartera y ciclo de vida (Fase 8).

El alta manual y las transiciones (depositar/acreditar/endosar/rechazar/anular/
debitar) delegan en app/services/cheques_core.py (sin commit). Este router abre
la transacción, aplica RBAC (`bancos`) y commitea. La materialización de cheques
desde cobranzas/OP vive en esos flujos (cobranzas.py / pagos.py), llamando al
mismo core.
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csv_export import csv_response, num
from app.core.cuit import validar_cuit
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import Cheque, ChequeEvento, Cliente, Proveedor, Usuario
from app.services import cheques_core as cc

router = APIRouter(prefix="/cheques", tags=["cheques"])


# ===== Schemas =====

class ChequeAltaIn(BaseModel):
    """Alta manual de un cheque de tercero en cartera (sin cobranza)."""
    numero: str = Field(min_length=1, max_length=20)
    banco: str = Field(min_length=1, max_length=60)
    sucursal_banco: str | None = Field(None, max_length=60)
    plaza: str | None = Field(None, max_length=60)
    titular: str | None = Field(None, max_length=80)
    cuit_firmante: str | None = Field(None, max_length=13)
    fecha_emision: date | None = None
    fecha_pago: date
    importe: Decimal = Field(gt=0)
    moneda: str = Field("ARS", pattern="^(ARS|USD)$")
    es_echeq: bool = False
    cliente_id: uuid.UUID | None = None
    observaciones: str | None = Field(None, max_length=200)


class DepositarIn(BaseModel):
    cuenta_id: uuid.UUID
    fecha: date | None = None


class AcreditarIn(BaseModel):
    fecha: date | None = None


class EndosarIn(BaseModel):
    proveedor_id: uuid.UUID
    fecha: date | None = None


class RechazarIn(BaseModel):
    fecha: date | None = None
    detalle: str | None = Field(None, max_length=200)


class DebitarIn(BaseModel):
    fecha: date | None = None


class AnularIn(BaseModel):
    detalle: str | None = Field(None, max_length=200)


class EventoOut(BaseModel):
    fecha: date
    estado_desde: str | None
    estado_hasta: str
    detalle: str | None
    model_config = {"from_attributes": True}


class ChequeOut(BaseModel):
    id: uuid.UUID
    clase: str
    numero: str
    banco: str
    titular: str | None
    fecha_emision: date | None
    fecha_pago: date
    importe: Decimal
    moneda: str
    es_echeq: bool
    estado: str
    cliente_id: uuid.UUID | None
    proveedor_id: uuid.UUID | None
    cuenta_id: uuid.UUID | None
    observaciones: str | None
    model_config = {"from_attributes": True}


# ===== Helpers =====

def _out(c: Cheque) -> ChequeOut:
    return ChequeOut.model_validate(c)


async def _cheque(db: AsyncSession, tenant_id: uuid.UUID, cheque_id: uuid.UUID) -> Cheque:
    cheque = await db.scalar(
        select(Cheque)
        .where(Cheque.id == cheque_id, Cheque.tenant_id == tenant_id)
        .with_for_update(of=Cheque)
    )
    if cheque is None:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
    return cheque


def _datos_alta(body: ChequeAltaIn) -> dict:
    if body.cuit_firmante and not validar_cuit(body.cuit_firmante):
        raise HTTPException(status_code=422, detail="CUIT del firmante inválido")
    return {
        "numero": body.numero.strip(),
        "banco": body.banco.strip(),
        "sucursal_banco": (body.sucursal_banco or "").strip() or None,
        "plaza": (body.plaza or "").strip() or None,
        "titular": (body.titular or "").strip() or None,
        "cuit_firmante": (body.cuit_firmante or "").strip() or None,
        "fecha_emision": body.fecha_emision,
        "fecha_pago": body.fecha_pago,
        "importe": body.importe,
        "moneda": body.moneda,
        "es_echeq": body.es_echeq,
        "observaciones": (body.observaciones or "").strip() or None,
    }


def _filtro_cheques(stmt, tenant_id, clase, estado, cliente_id, proveedor_id, desde, hasta, q):
    stmt = stmt.where(Cheque.tenant_id == tenant_id)
    if clase:
        stmt = stmt.where(Cheque.clase == clase)
    if estado:
        stmt = stmt.where(Cheque.estado == estado)
    if cliente_id:
        stmt = stmt.where(Cheque.cliente_id == cliente_id)
    if proveedor_id:
        stmt = stmt.where(Cheque.proveedor_id == proveedor_id)
    if desde:
        stmt = stmt.where(Cheque.fecha_pago >= desde)
    if hasta:
        stmt = stmt.where(Cheque.fecha_pago <= hasta)
    q = (q or "").strip()
    if q:
        # número exacto o banco/titular por texto (GIN trgm multicolumna, regla §6)
        stmt = stmt.where(
            or_(
                Cheque.numero.ilike(f"%{q}%"),
                Cheque.banco.ilike(f"%{q}%"),
                Cheque.titular.ilike(f"%{q}%"),
            )
        )
    return stmt


# ===== Listado y detalle =====

@router.get("", response_model=list[ChequeOut])
async def listar_cheques(
    response: Response,
    clase: str | None = None,
    estado: str | None = None,
    cliente_id: uuid.UUID | None = None,
    proveedor_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = _filtro_cheques(
        select(Cheque), usuario.tenant_id, clase, estado, cliente_id, proveedor_id, desde, hasta, q
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        stmt.order_by(Cheque.fecha_pago.asc(), Cheque.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return [_out(c) for c in filas]


@router.get("/resumen")
async def resumen_cartera(
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Totales por estado para la cartera (KPIs de la pantalla de cheques)."""
    filas = (
        await db.execute(
            select(Cheque.clase, Cheque.estado, func.count(), func.coalesce(func.sum(Cheque.importe), 0))
            .where(Cheque.tenant_id == usuario.tenant_id)
            .group_by(Cheque.clase, Cheque.estado)
        )
    ).all()
    return [
        {"clase": clase, "estado": estado, "cantidad": cant, "importe": str(imp)}
        for clase, estado, cant, imp in filas
    ]


@router.get("/export.csv")
async def export_cheques(
    clase: str | None = None,
    estado: str | None = None,
    cliente_id: uuid.UUID | None = None,
    proveedor_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str = "",
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = _filtro_cheques(
        select(Cheque), usuario.tenant_id, clase, estado, cliente_id, proveedor_id, desde, hasta, q
    )
    filas = (await db.scalars(stmt.order_by(Cheque.fecha_pago.asc()).limit(5000))).all()
    encabezado = ["Clase", "Número", "Banco", "Titular", "Emisión", "Pago", "Importe", "Moneda", "Estado"]
    datos = [
        [
            c.clase, c.numero, c.banco, c.titular or "",
            c.fecha_emision.isoformat() if c.fecha_emision else "",
            c.fecha_pago.isoformat(), num(c.importe), c.moneda, c.estado,
        ]
        for c in filas
    ]
    return csv_response("cheques.csv", encabezado, datos)


@router.get("/{cheque_id}")
async def detalle_cheque(
    cheque_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    cheque = await db.scalar(
        select(Cheque).where(Cheque.id == cheque_id, Cheque.tenant_id == usuario.tenant_id)
    )
    if cheque is None:
        raise HTTPException(status_code=404, detail="Cheque no encontrado")
    eventos = (
        await db.scalars(
            select(ChequeEvento)
            .where(ChequeEvento.cheque_id == cheque.id)
            .order_by(ChequeEvento.created_at.asc())
        )
    ).all()
    out = _out(cheque).model_dump()
    out["eventos"] = [EventoOut.model_validate(e).model_dump() for e in eventos]
    return out


# ===== Alta manual (tercero en cartera) =====

@router.post("", response_model=ChequeOut, status_code=status.HTTP_201_CREATED)
async def crear_cheque(
    body: ChequeAltaIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if body.cliente_id:
        existe = await db.scalar(
            select(Cliente.id).where(
                Cliente.id == body.cliente_id, Cliente.tenant_id == usuario.tenant_id
            )
        )
        if not existe:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cheque = await cc.recibir_tercero(
        db,
        tenant_id=usuario.tenant_id,
        datos=_datos_alta(body),
        cliente_id=body.cliente_id,
        usuario_id=usuario.id,
    )
    await db.commit()
    cheque = await db.scalar(select(Cheque).where(Cheque.id == cheque.id))
    return _out(cheque)


# ===== Transiciones =====

@router.post("/{cheque_id}/depositar", response_model=ChequeOut)
async def depositar_cheque(
    cheque_id: uuid.UUID,
    body: DepositarIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cheque = await _cheque(db, usuario.tenant_id, cheque_id)
    await cc.depositar(db, cheque=cheque, cuenta_id=body.cuenta_id, fecha=body.fecha, usuario_id=usuario.id)
    await db.commit()
    cheque = await db.scalar(select(Cheque).where(Cheque.id == cheque_id))
    return _out(cheque)


@router.post("/{cheque_id}/acreditar", response_model=ChequeOut)
async def acreditar_cheque(
    cheque_id: uuid.UUID,
    body: AcreditarIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cheque = await _cheque(db, usuario.tenant_id, cheque_id)
    await cc.acreditar(db, cheque=cheque, fecha=body.fecha, usuario_id=usuario.id)
    await db.commit()
    cheque = await db.scalar(select(Cheque).where(Cheque.id == cheque_id))
    return _out(cheque)


@router.post("/{cheque_id}/endosar", response_model=ChequeOut)
async def endosar_cheque(
    cheque_id: uuid.UUID,
    body: EndosarIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    existe = await db.scalar(
        select(Proveedor.id).where(
            Proveedor.id == body.proveedor_id, Proveedor.tenant_id == usuario.tenant_id
        )
    )
    if not existe:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    cheque = await _cheque(db, usuario.tenant_id, cheque_id)
    await cc.endosar(db, cheque=cheque, proveedor_id=body.proveedor_id, fecha=body.fecha, usuario_id=usuario.id)
    await db.commit()
    cheque = await db.scalar(select(Cheque).where(Cheque.id == cheque_id))
    return _out(cheque)


@router.post("/{cheque_id}/rechazar")
async def rechazar_cheque(
    cheque_id: uuid.UUID,
    body: RechazarIn,
    usuario: Usuario = Depends(requiere("bancos", "anular")),
    db: AsyncSession = Depends(get_db),
):
    cheque = await _cheque(db, usuario.tenant_id, cheque_id)
    res = await cc.rechazar(db, cheque=cheque, fecha=body.fecha, detalle=body.detalle, usuario_id=usuario.id)
    await db.commit()
    cheque = await db.scalar(select(Cheque).where(Cheque.id == cheque_id))
    return {**_out(cheque).model_dump(), **res}


@router.post("/{cheque_id}/debitar", response_model=ChequeOut)
async def debitar_cheque(
    cheque_id: uuid.UUID,
    body: DebitarIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cheque = await _cheque(db, usuario.tenant_id, cheque_id)
    await cc.debitar(db, cheque=cheque, fecha=body.fecha, usuario_id=usuario.id)
    await db.commit()
    cheque = await db.scalar(select(Cheque).where(Cheque.id == cheque_id))
    return _out(cheque)


@router.post("/{cheque_id}/anular", response_model=ChequeOut)
async def anular_cheque(
    cheque_id: uuid.UUID,
    body: AnularIn,
    usuario: Usuario = Depends(requiere("bancos", "anular")),
    db: AsyncSession = Depends(get_db),
):
    cheque = await _cheque(db, usuario.tenant_id, cheque_id)
    await cc.anular(db, cheque=cheque, detalle=body.detalle, usuario_id=usuario.id)
    await db.commit()
    cheque = await db.scalar(select(Cheque).where(Cheque.id == cheque_id))
    return _out(cheque)
