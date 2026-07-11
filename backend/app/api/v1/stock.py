"""Stock: saldos por depósito (legacy STOCK.DBF), ajustes, transferencias
entre depósitos y kardex (legacy MOV_STOC.DBF).

Todo cambio de saldo pasa por un movimiento: el saldo de articulo_stock se
actualiza con la fila bloqueada (FOR UPDATE) y el movimiento sella
saldo_resultante — kardex auditable sin recalcular.
"""

import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    Articulo,
    ArticuloStock,
    ArticuloVariante,
    AtributoValor,
    Deposito,
    DespiecePlantilla,
    DespiecePlantillaCorte,
    StockMovimiento,
    Usuario,
)
from app.services import stock_valor

router = APIRouter(prefix="/stock", tags=["stock"])


# ===== Schemas =====

class StockOut(BaseModel):
    articulo_id: uuid.UUID
    deposito_id: uuid.UUID
    variante_id: uuid.UUID | None = None
    cantidad: Decimal
    stock_minimo: Decimal
    ubicacion: str | None
    model_config = {"from_attributes": True}


class StockFilaOut(StockOut):
    articulo_codigo: str
    articulo_descripcion: str
    deposito_codigo: str
    deposito_nombre: str
    variante_etiqueta: str | None = None


class AjusteIn(BaseModel):
    articulo_id: uuid.UUID
    deposito_id: uuid.UUID
    variante_id: uuid.UUID | None = None
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
    variante_id: uuid.UUID | None = None
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
    variante_id: uuid.UUID | None = None
    stock_minimo: Decimal | None = Field(None, ge=0)
    ubicacion: str | None = Field(None, max_length=20)


class MovimientoOut(BaseModel):
    id: uuid.UUID
    articulo_id: uuid.UUID
    deposito_id: uuid.UUID
    variante_id: uuid.UUID | None = None
    variante_etiqueta: str | None = None
    fecha: datetime
    tipo: str
    cantidad: Decimal
    saldo_resultante: Decimal
    costo_unitario: Decimal | None = None  # sellado desde la 014; NULL = histórico
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


async def _validar_variante(
    db: AsyncSession, tenant_id: uuid.UUID, articulo: Articulo, variante_id: uuid.UUID | None
) -> uuid.UUID | None:
    """Regla Fase 2.5: si el artículo tiene variantes activas, el stock se opera
    POR variante (variante_id obligatorio y del artículo); si no tiene, va sin
    variante como siempre."""
    tiene_variantes = await db.scalar(
        select(func.count())
        .select_from(ArticuloVariante)
        .where(
            ArticuloVariante.tenant_id == tenant_id,
            ArticuloVariante.articulo_id == articulo.id,
            ArticuloVariante.activo,
        )
    )
    if variante_id is None:
        if tiene_variantes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El artículo tiene variantes: indicar variante_id",
            )
        return None
    variante = await db.scalar(
        select(ArticuloVariante).where(
            ArticuloVariante.id == variante_id,
            ArticuloVariante.tenant_id == tenant_id,
            ArticuloVariante.articulo_id == articulo.id,
        )
    )
    if variante is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La variante no pertenece al artículo",
        )
    return variante.id


async def _etiquetas_valores(db: AsyncSession, tenant_id: uuid.UUID) -> dict[uuid.UUID, str]:
    filas = (
        await db.scalars(select(AtributoValor).where(AtributoValor.tenant_id == tenant_id))
    ).all()
    return {v.id: v.valor for v in filas}


def _etiqueta_de(variante: ArticuloVariante | None, valores: dict[uuid.UUID, str]) -> str | None:
    if variante is None:
        return None
    partes = [
        valores.get(x, "?")
        for x in (variante.valor_1_id, variante.valor_2_id, variante.valor_3_id)
        if x
    ]
    return " / ".join(partes)


async def _stock_bloqueado(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    articulo_id: uuid.UUID,
    deposito_id: uuid.UUID,
    variante_id: uuid.UUID | None = None,
) -> ArticuloStock:
    """Devuelve la fila de saldo con lock; la crea en 0 si no existe."""
    filtro_variante = (
        ArticuloStock.variante_id.is_(None)
        if variante_id is None
        else ArticuloStock.variante_id == variante_id
    )
    fila = await db.scalar(
        select(ArticuloStock)
        .where(
            ArticuloStock.tenant_id == tenant_id,
            ArticuloStock.articulo_id == articulo_id,
            ArticuloStock.deposito_id == deposito_id,
            filtro_variante,
        )
        .with_for_update()
    )
    if fila is None:
        fila = ArticuloStock(
            tenant_id=tenant_id,
            articulo_id=articulo_id,
            deposito_id=deposito_id,
            variante_id=variante_id,
            cantidad=0,
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
    costo_unitario: Decimal | None = None,
) -> StockMovimiento:
    fila.cantidad = fila.cantidad + delta
    fila.updated_at = func.now()
    mov = StockMovimiento(
        tenant_id=fila.tenant_id,
        articulo_id=fila.articulo_id,
        deposito_id=fila.deposito_id,
        variante_id=fila.variante_id,
        tipo=tipo,
        cantidad=delta,
        saldo_resultante=fila.cantidad,
        costo_unitario=costo_unitario,
        observaciones=observaciones,
        grupo_id=grupo_id,
        usuario_id=usuario_id,
    )
    db.add(mov)
    return mov


async def _costo_sellado(db: AsyncSession, articulo) -> Decimal:
    """Costo neto ARS vigente del artículo para sellar el movimiento (014)."""
    cotizacion = Decimal("1")
    if articulo.en_dolares:
        cotizacion = await stock_valor.cotizacion_vigente(db, articulo.tenant_id)
    return stock_valor.costo_neto_ars(articulo, cotizacion)


# ===== Endpoints =====

@router.get("", response_model=list[StockFilaOut])
async def listar_stock(
    response: Response,
    q: str = "",
    deposito_id: uuid.UUID | None = None,
    solo_bajo_minimo: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("stock", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ArticuloStock, Articulo, Deposito, ArticuloVariante)
        .join(Articulo, ArticuloStock.articulo_id == Articulo.id)
        .join(Deposito, ArticuloStock.deposito_id == Deposito.id)
        .outerjoin(ArticuloVariante, ArticuloStock.variante_id == ArticuloVariante.id)
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
            | ArticuloVariante.codigo_barras.ilike(patron)
        )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)

    stmt = stmt.order_by(Articulo.descripcion, Deposito.codigo).limit(min(limit, 200)).offset(offset)
    filas = (await db.execute(stmt)).all()
    valores = await _etiquetas_valores(db, usuario.tenant_id)
    return [
        StockFilaOut(
            articulo_id=st.articulo_id,
            deposito_id=st.deposito_id,
            variante_id=st.variante_id,
            variante_etiqueta=_etiqueta_de(var, valores),
            cantidad=st.cantidad,
            stock_minimo=st.stock_minimo,
            ubicacion=st.ubicacion,
            articulo_codigo=art.codigo,
            articulo_descripcion=art.descripcion,
            deposito_codigo=dep.codigo,
            deposito_nombre=dep.nombre,
        )
        for st, art, dep, var in filas
    ]


@router.get("/articulo/{articulo_id}", response_model=list[StockFilaOut])
async def stock_de_articulo(
    articulo_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("stock", "ver")),
    db: AsyncSession = Depends(get_db),
):
    articulo = await _validar_articulo(db, usuario.tenant_id, articulo_id)
    filas = (
        await db.execute(
            select(ArticuloStock, Deposito, ArticuloVariante)
            .join(Deposito, ArticuloStock.deposito_id == Deposito.id)
            .outerjoin(ArticuloVariante, ArticuloStock.variante_id == ArticuloVariante.id)
            .where(
                ArticuloStock.tenant_id == usuario.tenant_id,
                ArticuloStock.articulo_id == articulo_id,
            )
            .order_by(Deposito.codigo)
        )
    ).all()
    valores = await _etiquetas_valores(db, usuario.tenant_id)
    return [
        StockFilaOut(
            articulo_id=st.articulo_id,
            deposito_id=st.deposito_id,
            variante_id=st.variante_id,
            variante_etiqueta=_etiqueta_de(var, valores),
            cantidad=st.cantidad,
            stock_minimo=st.stock_minimo,
            ubicacion=st.ubicacion,
            articulo_codigo=articulo.codigo,
            articulo_descripcion=articulo.descripcion,
            deposito_codigo=dep.codigo,
            deposito_nombre=dep.nombre,
        )
        for st, dep, var in filas
    ]


@router.post("/ajuste", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED)
async def ajustar_stock(
    body: AjusteIn,
    usuario: Usuario = Depends(requiere("stock", "editar")),
    db: AsyncSession = Depends(get_db),
):
    articulo = await _validar_articulo(db, usuario.tenant_id, body.articulo_id)
    if not articulo.controla_stock:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El artículo no controla stock",
        )
    await _validar_deposito(db, usuario.tenant_id, body.deposito_id)
    variante_id = await _validar_variante(db, usuario.tenant_id, articulo, body.variante_id)

    fila = await _stock_bloqueado(
        db, usuario.tenant_id, body.articulo_id, body.deposito_id, variante_id
    )
    delta = (
        body.cantidad_final - fila.cantidad if body.cantidad_final is not None else body.delta
    )
    if delta == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El ajuste no cambia el saldo",
        )
    costo = await _costo_sellado(db, articulo)
    mov = _mover(db, fila, "ajuste", delta, usuario.id, body.observaciones,
                 costo_unitario=costo)
    await db.commit()
    out = MovimientoOut.model_validate(mov)
    if mov.variante_id:
        valores = await _etiquetas_valores(db, usuario.tenant_id)
        variante = await db.get(ArticuloVariante, mov.variante_id)
        out.variante_etiqueta = _etiqueta_de(variante, valores)
    return out


@router.post("/transferencia", response_model=list[MovimientoOut], status_code=status.HTTP_201_CREATED)
async def transferir_stock(
    body: TransferenciaIn,
    usuario: Usuario = Depends(requiere("stock", "editar")),
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
    variante_id = await _validar_variante(db, usuario.tenant_id, articulo, body.variante_id)

    # lock en orden estable para evitar deadlocks entre transferencias cruzadas
    primero, segundo = sorted((body.origen_id, body.destino_id), key=str)
    fila_1 = await _stock_bloqueado(db, usuario.tenant_id, body.articulo_id, primero, variante_id)
    fila_2 = await _stock_bloqueado(db, usuario.tenant_id, body.articulo_id, segundo, variante_id)
    origen = fila_1 if fila_1.deposito_id == body.origen_id else fila_2
    destino = fila_2 if origen is fila_1 else fila_1

    grupo = uuid.uuid4()
    costo = await _costo_sellado(db, articulo)
    salida = _mover(db, origen, "transferencia", -body.cantidad, usuario.id,
                    body.observaciones, grupo, costo_unitario=costo)
    entrada = _mover(db, destino, "transferencia", body.cantidad, usuario.id,
                     body.observaciones, grupo, costo_unitario=costo)
    await db.commit()
    return [MovimientoOut.model_validate(salida), MovimientoOut.model_validate(entrada)]


@router.put("/config", response_model=StockOut)
async def configurar_stock(
    body: StockConfigIn,
    usuario: Usuario = Depends(requiere("stock", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Mínimo y ubicación por artículo/depósito (legacy STOCK.MINIMO/UBICACION)."""
    articulo = await _validar_articulo(db, usuario.tenant_id, body.articulo_id)
    await _validar_deposito(db, usuario.tenant_id, body.deposito_id)
    variante_id = await _validar_variante(db, usuario.tenant_id, articulo, body.variante_id)
    fila = await _stock_bloqueado(
        db, usuario.tenant_id, body.articulo_id, body.deposito_id, variante_id
    )
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
    variante_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("stock", "ver")),
    db: AsyncSession = Depends(get_db),
):
    await _validar_articulo(db, usuario.tenant_id, articulo_id)
    stmt = select(StockMovimiento).where(
        StockMovimiento.tenant_id == usuario.tenant_id,
        StockMovimiento.articulo_id == articulo_id,
    )
    if deposito_id:
        stmt = stmt.where(StockMovimiento.deposito_id == deposito_id)
    if variante_id:
        stmt = stmt.where(StockMovimiento.variante_id == variante_id)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)

    stmt = (
        stmt.order_by(StockMovimiento.fecha.desc(), StockMovimiento.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    movimientos = (await db.scalars(stmt)).all()
    valores = await _etiquetas_valores(db, usuario.tenant_id)
    variantes = {
        v.id: v
        for v in (
            await db.scalars(
                select(ArticuloVariante).where(
                    ArticuloVariante.tenant_id == usuario.tenant_id,
                    ArticuloVariante.articulo_id == articulo_id,
                )
            )
        ).all()
    }
    salida = []
    for m in movimientos:
        out = MovimientoOut.model_validate(m)
        out.variante_etiqueta = _etiqueta_de(variantes.get(m.variante_id), valores)
        salida.append(out)
    return salida


# ===== Despiece / transformación de stock (F12-c, DISENO-POS-PERFILES.md §2) =====
#
# Capacidad GENERAL: una salida del artículo origen + N entradas de destinos,
# todas atadas por grupo_id (patrón transferencia). Merma explícita = origen −
# Σ cortes. Costeo proporcional al VALOR: costo_kg(corte) = costo_total ×
# coef(corte) / Σ(coef_i × kg_i) — con coef 1,0 degrada a prorrateo por peso.
# La contabilidad NO deriva asientos de la transformación: es neutra en valor
# (la merma queda absorbida en el costo de los cortes).

_C4 = Decimal("0.0001")


class PlantillaCorteIn(BaseModel):
    articulo_id: uuid.UUID
    rendimiento_pct: Decimal = Field(Decimal("0"), ge=0, le=100)
    coef_valor: Decimal = Field(Decimal("1"), gt=0)


class PlantillaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    articulo_origen_id: uuid.UUID
    cortes: list[PlantillaCorteIn] = Field(min_length=1)
    activa: bool = True

    @model_validator(mode="after")
    def _coherente(self):
        ids = [c.articulo_id for c in self.cortes]
        if len(set(ids)) != len(ids):
            raise ValueError("Hay cortes repetidos en la plantilla")
        if self.articulo_origen_id in ids:
            raise ValueError("El artículo origen no puede ser un corte de sí mismo")
        if sum((c.rendimiento_pct for c in self.cortes), Decimal("0")) > 100:
            raise ValueError("Los rendimientos sugeridos suman más del 100%")
        return self


class PlantillaCorteOut(BaseModel):
    articulo_id: uuid.UUID
    articulo_codigo: str
    articulo_descripcion: str
    rendimiento_pct: Decimal
    coef_valor: Decimal


class PlantillaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    articulo_origen_id: uuid.UUID
    origen_codigo: str
    origen_descripcion: str
    activa: bool
    cortes: list[PlantillaCorteOut]


class TransformacionCorteIn(BaseModel):
    articulo_id: uuid.UUID
    variante_id: uuid.UUID | None = None
    cantidad: Decimal = Field(gt=0)
    coef_valor: Decimal = Field(Decimal("1"), gt=0)


class TransformacionIn(BaseModel):
    deposito_id: uuid.UUID
    articulo_origen_id: uuid.UUID
    variante_id: uuid.UUID | None = None
    cantidad_origen: Decimal = Field(gt=0)
    # costo total del origen consumido (p. ej. el de la factura del
    # frigorífico). Default: costo vigente del artículo × cantidad.
    costo_total: Decimal | None = Field(None, ge=0)
    cortes: list[TransformacionCorteIn] = Field(min_length=1)
    actualiza_costos: bool = True
    observaciones: str | None = Field(None, max_length=100)

    @model_validator(mode="after")
    def _coherente(self):
        llaves = [(c.articulo_id, c.variante_id) for c in self.cortes]
        if len(set(llaves)) != len(llaves):
            raise ValueError("Hay cortes repetidos")
        if any(c.articulo_id == self.articulo_origen_id for c in self.cortes):
            raise ValueError("El artículo origen no puede estar entre los cortes")
        return self


class CostoCorteOut(BaseModel):
    articulo_id: uuid.UUID
    costo_unitario: Decimal


class TransformacionOut(BaseModel):
    grupo_id: uuid.UUID
    merma: Decimal
    costo_total: Decimal
    salida: MovimientoOut
    entradas: list[MovimientoOut]
    costos_corte: list[CostoCorteOut]


async def _plantilla_out(db: AsyncSession, p: DespiecePlantilla) -> PlantillaOut:
    ids = [p.articulo_origen_id] + [c.articulo_id for c in p.cortes]
    arts = {
        a.id: a
        for a in (await db.scalars(select(Articulo).where(Articulo.id.in_(ids)))).all()
    }
    origen = arts[p.articulo_origen_id]
    return PlantillaOut(
        id=p.id,
        nombre=p.nombre,
        articulo_origen_id=p.articulo_origen_id,
        origen_codigo=origen.codigo,
        origen_descripcion=origen.descripcion,
        activa=p.activa,
        cortes=[
            PlantillaCorteOut(
                articulo_id=c.articulo_id,
                articulo_codigo=arts[c.articulo_id].codigo,
                articulo_descripcion=arts[c.articulo_id].descripcion,
                rendimiento_pct=c.rendimiento_pct,
                coef_valor=c.coef_valor,
            )
            for c in p.cortes
        ],
    )


async def _validar_articulos_plantilla(
    db: AsyncSession, tenant_id: uuid.UUID, body: PlantillaIn
) -> None:
    ids = {body.articulo_origen_id} | {c.articulo_id for c in body.cortes}
    encontrados = {
        a.id
        for a in (
            await db.scalars(
                select(Articulo).where(Articulo.id.in_(ids), Articulo.tenant_id == tenant_id)
            )
        ).all()
    }
    if encontrados != ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hay artículos que no existen en la empresa",
        )


@router.get("/despiece-plantillas", response_model=list[PlantillaOut])
async def listar_plantillas(
    incluir_inactivas: bool = False,
    usuario: Usuario = Depends(requiere("stock", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DespiecePlantilla).where(DespiecePlantilla.tenant_id == usuario.tenant_id)
    if not incluir_inactivas:
        stmt = stmt.where(DespiecePlantilla.activa.is_(True))
    plantillas = (await db.scalars(stmt.order_by(DespiecePlantilla.nombre))).all()
    return [await _plantilla_out(db, p) for p in plantillas]


@router.post(
    "/despiece-plantillas", response_model=PlantillaOut, status_code=status.HTTP_201_CREATED
)
async def crear_plantilla(
    body: PlantillaIn,
    usuario: Usuario = Depends(requiere("stock", "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _validar_articulos_plantilla(db, usuario.tenant_id, body)
    p = DespiecePlantilla(
        tenant_id=usuario.tenant_id,
        nombre=body.nombre.strip(),
        articulo_origen_id=body.articulo_origen_id,
        activa=body.activa,
        cortes=[
            DespiecePlantillaCorte(
                tenant_id=usuario.tenant_id,
                articulo_id=c.articulo_id,
                rendimiento_pct=c.rendimiento_pct,
                coef_valor=c.coef_valor,
                orden=i,
            )
            for i, c in enumerate(body.cortes)
        ],
    )
    db.add(p)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una plantilla con ese nombre")
    p = await db.scalar(select(DespiecePlantilla).where(DespiecePlantilla.id == p.id))
    return await _plantilla_out(db, p)


@router.put("/despiece-plantillas/{plantilla_id}", response_model=PlantillaOut)
async def editar_plantilla(
    plantilla_id: uuid.UUID,
    body: PlantillaIn,
    usuario: Usuario = Depends(requiere("stock", "editar")),
    db: AsyncSession = Depends(get_db),
):
    p = await db.scalar(
        select(DespiecePlantilla).where(
            DespiecePlantilla.id == plantilla_id,
            DespiecePlantilla.tenant_id == usuario.tenant_id,
        )
    )
    if p is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    await _validar_articulos_plantilla(db, usuario.tenant_id, body)
    p.nombre = body.nombre.strip()
    p.articulo_origen_id = body.articulo_origen_id
    p.activa = body.activa
    # borrar los cortes viejos ANTES de insertar los nuevos: sin el flush
    # intermedio, el INSERT puede correr antes que el DELETE y chocar el
    # UNIQUE (plantilla_id, articulo_id)
    p.cortes = []
    await db.flush()
    p.cortes = [
        DespiecePlantillaCorte(
            tenant_id=usuario.tenant_id,
            articulo_id=c.articulo_id,
            rendimiento_pct=c.rendimiento_pct,
            coef_valor=c.coef_valor,
            orden=i,
        )
        for i, c in enumerate(body.cortes)
    ]
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una plantilla con ese nombre")
    p = await db.scalar(select(DespiecePlantilla).where(DespiecePlantilla.id == plantilla_id))
    return await _plantilla_out(db, p)


@router.post(
    "/transformacion", response_model=TransformacionOut, status_code=status.HTTP_201_CREATED
)
async def transformar_stock(
    body: TransformacionIn,
    usuario: Usuario = Depends(requiere("stock", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Despiece/fraccionamiento: consume el origen y da de alta los cortes en
    el mismo depósito, con costeo proporcional al valor. El ingreso de media
    res de carnicería es esta operación con la plantilla precargada."""
    origen = await _validar_articulo(db, usuario.tenant_id, body.articulo_origen_id)
    if not origen.controla_stock:
        raise HTTPException(status_code=422, detail="El artículo origen no controla stock")
    await _validar_deposito(db, usuario.tenant_id, body.deposito_id)
    var_origen = await _validar_variante(db, usuario.tenant_id, origen, body.variante_id)

    suma_cortes = sum((c.cantidad for c in body.cortes), Decimal("0"))
    if suma_cortes > body.cantidad_origen:
        raise HTTPException(
            status_code=422,
            detail="Los cortes suman más que la cantidad de origen (merma negativa)",
        )
    merma = body.cantidad_origen - suma_cortes

    arts_corte: dict[uuid.UUID, Articulo] = {
        a.id: a
        for a in (
            await db.scalars(
                select(Articulo).where(
                    Articulo.id.in_({c.articulo_id for c in body.cortes}),
                    Articulo.tenant_id == usuario.tenant_id,
                )
            )
        ).all()
    }
    variantes_corte: list[uuid.UUID | None] = []
    for c in body.cortes:
        art = arts_corte.get(c.articulo_id)
        if art is None or not art.activo:
            raise HTTPException(status_code=422, detail="Corte inexistente o inactivo")
        if not art.controla_stock:
            raise HTTPException(
                status_code=422, detail=f"El corte {art.descripcion} no controla stock"
            )
        variantes_corte.append(
            await _validar_variante(db, usuario.tenant_id, art, c.variante_id)
        )

    cotizacion = await stock_valor.cotizacion_vigente(db, usuario.tenant_id)
    costo_total = (
        body.costo_total
        if body.costo_total is not None
        else stock_valor.costo_neto_ars(origen, cotizacion) * body.cantidad_origen
    ).quantize(_C4, rounding=ROUND_HALF_UP)

    # costo_kg(corte) = costo_total × coef / Σ(coef_i × kg_i)
    denominador = sum((c.coef_valor * c.cantidad for c in body.cortes), Decimal("0"))
    costos_corte = [
        (costo_total * c.coef_valor / denominador).quantize(_C4, rounding=ROUND_HALF_UP)
        for c in body.cortes
    ]

    # locks en orden estable (patrón transferencia) para evitar deadlocks
    pendientes: dict[tuple[str, str], tuple[uuid.UUID, uuid.UUID | None]] = {
        (str(origen.id), str(var_origen or "")): (origen.id, var_origen)
    }
    for c, v in zip(body.cortes, variantes_corte):
        pendientes[(str(c.articulo_id), str(v or ""))] = (c.articulo_id, v)
    filas: dict[tuple[str, str], ArticuloStock] = {}
    for llave in sorted(pendientes):
        art_id, var_id = pendientes[llave]
        filas[llave] = await _stock_bloqueado(
            db, usuario.tenant_id, art_id, body.deposito_id, var_id
        )

    grupo = uuid.uuid4()
    obs = (body.observaciones or "").strip()
    obs_salida = f"Merma {merma}" + (f" · {obs}" if obs else "")
    costo_unit_origen = (costo_total / body.cantidad_origen).quantize(
        _C4, rounding=ROUND_HALF_UP
    )
    salida = _mover(
        db,
        filas[(str(origen.id), str(var_origen or ""))],
        "transformacion",
        -body.cantidad_origen,
        usuario.id,
        obs_salida[:120],
        grupo,
        costo_unitario=costo_unit_origen,
    )
    entradas = []
    for c, v, costo_kg in zip(body.cortes, variantes_corte, costos_corte):
        entradas.append(
            _mover(
                db,
                filas[(str(c.articulo_id), str(v or ""))],
                "transformacion",
                c.cantidad,
                usuario.id,
                obs[:120] or None,
                grupo,
                costo_unitario=costo_kg,
            )
        )

    # costo por corte en la convención del artículo (con/sin IVA, USD) — mismo
    # criterio que la factura de compra (F4): actualiza costo, no precios.
    if body.actualiza_costos:
        for c, costo_kg in zip(body.cortes, costos_corte):
            art = arts_corte[c.articulo_id]
            nuevo = costo_kg
            if art.costo_con_iva and art.tasa_iva:
                nuevo = nuevo * (1 + Decimal(art.tasa_iva) / 100)
            if art.en_dolares and cotizacion:
                nuevo = nuevo / cotizacion
            art.costo = nuevo.quantize(_C4, rounding=ROUND_HALF_UP)
            art.updated_at = func.now()

    await db.commit()
    return TransformacionOut(
        grupo_id=grupo,
        merma=merma,
        costo_total=costo_total,
        salida=MovimientoOut.model_validate(salida),
        entradas=[MovimientoOut.model_validate(e) for e in entradas],
        costos_corte=[
            CostoCorteOut(articulo_id=c.articulo_id, costo_unitario=costo_kg)
            for c, costo_kg in zip(body.cortes, costos_corte)
        ],
    )
