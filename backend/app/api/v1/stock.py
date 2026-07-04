"""Stock: saldos por depósito (legacy STOCK.DBF), ajustes, transferencias
entre depósitos y kardex (legacy MOV_STOC.DBF).

Todo cambio de saldo pasa por un movimiento: el saldo de articulo_stock se
actualiza con la fila bloqueada (FOR UPDATE) y el movimiento sella
saldo_resultante — kardex auditable sin recalcular.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import (
    Articulo,
    ArticuloStock,
    Deposito,
    StockMovimiento,
    Usuario,
)

router = APIRouter(prefix="/stock", tags=["stock"])


# ===== Schemas =====

class StockOut(BaseModel):
    articulo_id: uuid.UUID
    deposito_id: uuid.UUID
    cantidad: Decimal
    stock_minimo: Decimal
    ubicacion: str | None
    model_config = {"from_attributes": True}


class StockFilaOut(StockOut):
    articulo_codigo: str
    articulo_descripcion: str
    deposito_codigo: str
    deposito_nombre: str


class AjusteIn(BaseModel):
    articulo_id: uuid.UUID
    deposito_id: uuid.UUID
    cantidad_final: Decimal | None = None   # modo recuento: fija el saldo
    delta: Decimal | None = None            # modo suma/resta
    observaciones: str | None = Field(None, max_length=120)

    @model_validator(mode="after")
    def _uno_de_los_dos(self):
        if (self.cantidad_final is None) == (self.delta is None):
            raise ValueError("Indicar cantidad_final (recuento) O delta (suma/resta), no ambas")
        return self


class TransferenciaIn(BaseModel):
    articulo_id: uuid.UUID
    origen_id: uuid.UUID
    destino_id: uuid.UUID
    cantidad: Decimal = Field(gt=0)
    observaciones: str | None = Field(None, max_length=120)

    @model_validator(mode="after")
    def _depositos_distintos(self):
        if self.origen_id == self.destino_id:
            raise ValueError("El depósito origen y destino deben ser distintos")
        return self


class StockConfigIn(BaseModel):
    articulo_id: uuid.UUID
    deposito_id: uuid.UUID
    stock_minimo: Decimal | None = Field(None, ge=0)
    ubicacion: str | None = Field(None, max_length=20)


class MovimientoOut(BaseModel):
    id: uuid.UUID
    articulo_id: uuid.UUID
    deposito_id: uuid.UUID
    fecha: datetime
    tipo: str
    cantidad: Decimal
    saldo_resultante: Decimal
    comprobante: str | None
    observaciones: str | None
    grupo_id: uuid.UUID | None
    model_config = {"from_attributes": True}


# ===== Helpers =====

async def _validar_articulo(db: AsyncSession, tenant_id: uuid.UUID, articulo_id: uuid.UUID) -> Articulo:
    articulo = await db.scalar(
        select(Articulo).where(Articulo.id == articulo_id, Articulo.tenant_id == tenant_id)
    )
    if articulo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artículo no encontrado")
    return articulo


async def _validar_deposito(db: AsyncSession, tenant_id: uuid.UUID, deposito_id: uuid.UUID) -> Deposito:
    deposito = await db.scalar(
        select(Deposito).where(Deposito.id == deposito_id, Deposito.tenant_id == tenant_id)
    )
    if deposito is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Depósito no encontrado")
    return deposito


async def _stock_bloqueado(
    db: AsyncSession, tenant_id: uuid.UUID, articulo_id: uuid.UUID, deposito_id: uuid.UUID
) -> ArticuloStock:
    """Devuelve la fila de saldo con lock; la crea en 0 si no existe."""
    fila = await db.scalar(
        select(ArticuloStock)
        .where(
            ArticuloStock.tenant_id == tenant_id,
            ArticuloStock.articulo_id == articulo_id,
            ArticuloStock.deposito_id == deposito_id,
        )
        .with_for_update()
    )
    if fila is None:
        fila = ArticuloStock(
            tenant_id=tenant_id, articulo_id=articulo_id, deposito_id=deposito_id, cantidad=0
        )
        db.add(fila)
        await db.flush()
    return fila


def _mover(
    db: AsyncSession,
    fila: ArticuloStock,
    tipo: str,
    delta: Decimal,
    usuario_id: uuid.UUID,
    observaciones: str | None = None,
    grupo_id: uuid.UUID | None = None,
) -> StockMovimiento:
    fila.cantidad = fila.cantidad + delta
    fila.updated_at = func.now()
    mov = StockMovimiento(
        tenant_id=fila.tenant_id,
        articulo_id=fila.articulo_id,
        deposito_id=fila.deposito_id,
        tipo=tipo,
        cantidad=delta,
        saldo_resultante=fila.cantidad,
        observaciones=observaciones,
        grupo_id=grupo_id,
        usuario_id=usuario_id,
    )
    db.add(mov)
    return mov


# ===== Endpoints =====

@router.get("", response_model=list[StockFilaOut])
async def listar_stock(
    response: Response,
    q: str = "",
    deposito_id: uuid.UUID | None = None,
    solo_bajo_minimo: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ArticuloStock, Articulo, Deposito)
        .join(Articulo, ArticuloStock.articulo_id == Articulo.id)
        .join(Deposito, ArticuloStock.deposito_id == Deposito.id)
        .where(ArticuloStock.tenant_id == usuario.tenant_id, Articulo.activo)
    )
    if deposito_id:
        stmt = stmt.where(ArticuloStock.deposito_id == deposito_id)
    if solo_bajo_minimo:
        stmt = stmt.where(
            ArticuloStock.stock_minimo > 0, ArticuloStock.cantidad < ArticuloStock.stock_minimo
        )
    if q.strip():
        patron = f"%{q.strip()}%"
        stmt = stmt.where(
            Articulo.descripcion.ilike(patron)
            | Articulo.codigo.ilike(patron)
            | Articulo.codigo_barras.ilike(patron)
        )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"

    stmt = stmt.order_by(Articulo.descripcion, Deposito.codigo).limit(min(limit, 200)).offset(offset)
    filas = (await db.execute(stmt)).all()
    return [
        StockFilaOut(
            articulo_id=st.articulo_id,
            deposito_id=st.deposito_id,
            cantidad=st.cantidad,
            stock_minimo=st.stock_minimo,
            ubicacion=st.ubicacion,
            articulo_codigo=art.codigo,
            articulo_descripcion=art.descripcion,
            deposito_codigo=dep.codigo,
            deposito_nombre=dep.nombre,
        )
        for st, art, dep in filas
    ]


@router.get("/articulo/{articulo_id}", response_model=list[StockFilaOut])
async def stock_de_articulo(
    articulo_id: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    articulo = await _validar_articulo(db, usuario.tenant_id, articulo_id)
    filas = (
        await db.execute(
            select(ArticuloStock, Deposito)
            .join(Deposito, ArticuloStock.deposito_id == Deposito.id)
            .where(
                ArticuloStock.tenant_id == usuario.tenant_id,
                ArticuloStock.articulo_id == articulo_id,
            )
            .order_by(Deposito.codigo)
        )
    ).all()
    return [
        StockFilaOut(
            articulo_id=st.articulo_id,
            deposito_id=st.deposito_id,
            cantidad=st.cantidad,
            stock_minimo=st.stock_minimo,
            ubicacion=st.ubicacion,
            articulo_codigo=articulo.codigo,
            articulo_descripcion=articulo.descripcion,
            deposito_codigo=dep.codigo,
            deposito_nombre=dep.nombre,
        )
        for st, dep in filas
    ]


@router.post("/ajuste", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def ajustar_stock(
    body: AjusteIn,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    articulo = await _validar_articulo(db, usuario.tenant_id, body.articulo_id)
    if not articulo.controla_stock:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El artículo no controla stock",
        )
    await _validar_deposito(db, usuario.tenant_id, body.deposito_id)

    fila = await _stock_bloqueado(db, usuario.tenant_id, body.articulo_id, body.deposito_id)
    delta = (
        body.cantidad_final - fila.cantidad if body.cantidad_final is not None else body.delta
    )
    if delta == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El ajuste no cambia el saldo",
        )
    mov = _mover(db, fila, "ajuste", delta, usuario.id, body.observaciones)
    await db.commit()
    return MovimientoOut.model_validate(mov)


@router.post("/transferencia", response_model=list[MovimientoOut], status_code=status.HTTP_201_CREATED)
async def transferir_stock(
    body: TransferenciaIn,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Interdepósito del legacy: una salida y una entrada atadas por grupo_id."""
    articulo = await _validar_articulo(db, usuario.tenant_id, body.articulo_id)
    if not articulo.controla_stock:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El artículo no controla stock",
        )
    await _validar_deposito(db, usuario.tenant_id, body.origen_id)
    await _validar_deposito(db, usuario.tenant_id, body.destino_id)

    # lock en orden estable para evitar deadlocks entre transferencias cruzadas
    primero, segundo = sorted((body.origen_id, body.destino_id), key=str)
    fila_1 = await _stock_bloqueado(db, usuario.tenant_id, body.articulo_id, primero)
    fila_2 = await _stock_bloqueado(db, usuario.tenant_id, body.articulo_id, segundo)
    origen = fila_1 if fila_1.deposito_id == body.origen_id else fila_2
    destino = fila_2 if origen is fila_1 else fila_1

    grupo = uuid.uuid4()
    salida = _mover(db, origen, "transferencia", -body.cantidad, usuario.id, body.observaciones, grupo)
    entrada = _mover(db, destino, "transferencia", body.cantidad, usuario.id, body.observaciones, grupo)
    await db.commit()
    return [MovimientoOut.model_validate(salida), MovimientoOut.model_validate(entrada)]


@router.put("/config", response_model=StockOut)
async def configurar_stock(
    body: StockConfigIn,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mínimo y ubicación por artículo/depósito (legacy STOCK.MINIMO/UBICACION)."""
    await _validar_articulo(db, usuario.tenant_id, body.articulo_id)
    await _validar_deposito(db, usuario.tenant_id, body.deposito_id)
    fila = await _stock_bloqueado(db, usuario.tenant_id, body.articulo_id, body.deposito_id)
    if body.stock_minimo is not None:
        fila.stock_minimo = body.stock_minimo
    if body.ubicacion is not None:
        fila.ubicacion = body.ubicacion.strip() or None
    fila.updated_at = func.now()
    await db.commit()
    return StockOut.model_validate(fila)


@router.get("/kardex/{articulo_id}", response_model=list[MovimientoOut])
async def kardex(
    articulo_id: uuid.UUID,
    response: Response,
    deposito_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _validar_articulo(db, usuario.tenant_id, articulo_id)
    stmt = select(StockMovimiento).where(
        StockMovimiento.tenant_id == usuario.tenant_id,
        StockMovimiento.articulo_id == articulo_id,
    )
    if deposito_id:
        stmt = stmt.where(StockMovimiento.deposito_id == deposito_id)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"

    stmt = (
        stmt.order_by(StockMovimiento.fecha.desc(), StockMovimiento.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    movimientos = (await db.scalars(stmt)).all()
    return [MovimientoOut.model_validate(m) for m in movimientos]
