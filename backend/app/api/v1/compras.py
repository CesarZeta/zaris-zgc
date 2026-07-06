"""Comprobantes de compra (Fase 4): facturas/NC/ND y remitos de proveedor.

El documento lo emite el proveedor: numeración ajena (punto_venta/numero del
papel), letra elegida por el usuario según el comprobante físico, sin ARCA.
Circuito: borrador (editable) → registrar (stock + costos + cta. cte.) →
anulable con reversión mientras no tenga pagos imputados.
Incluye el comparativo de precios por proveedor (ART_PROV del legacy).
"""

import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.csv_export import csv_response, num
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    Articulo,
    ArticuloProveedor,
    ArticuloStock,
    ArticuloVariante,
    Compra,
    CompraItem,
    CompraVencimiento,
    CondicionVenta,
    Deposito,
    Entidad,
    ImputacionCompra,
    Proveedor,
    StockMovimiento,
    TipoComprobanteCompra,
    Usuario,
)
from app.services import compras as sc

router = APIRouter(prefix="/compras", tags=["compras"])

CLASES_FISCALES = ("factura", "nota_debito", "nota_credito")
CLASES = CLASES_FISCALES + ("remito",)


# ===== Schemas =====

class ItemIn(BaseModel):
    articulo_id: uuid.UUID | None = None
    variante_id: uuid.UUID | None = None
    descripcion: str | None = Field(None, max_length=120)  # texto libre si no hay artículo
    cantidad: Decimal = Field(gt=0)
    costo_unitario: Decimal = Field(ge=0)
    bonif_1: Decimal = Field(Decimal("0"), ge=0, le=100)
    bonif_2: Decimal = Field(Decimal("0"), ge=0, le=100)
    tasa_iva: Decimal | None = None  # default: la del artículo (o 21)


class CompraIn(BaseModel):
    clase: str = Field(pattern="^(factura|nota_debito|nota_credito|remito)$")
    letra: str = Field("A", pattern="^[ABC]$")  # la del papel; remito fuerza X
    punto_venta: int = Field(0, ge=0, le=99999)
    numero: int = Field(0, ge=0)
    proveedor_id: uuid.UUID
    fecha: date | None = None
    periodo_iva: date | None = None  # default: 1° del mes de la fecha
    contado: bool = False
    condicion_compra_id: uuid.UUID | None = None
    deposito_id: uuid.UUID | None = None
    actualiza_stock: bool = True
    actualiza_costos: bool = True
    no_gravado: Decimal = Field(Decimal("0"), ge=0)
    exento: Decimal = Field(Decimal("0"), ge=0)
    percepcion_iva: Decimal = Field(Decimal("0"), ge=0)
    percepcion_iibb: Decimal = Field(Decimal("0"), ge=0)
    impuestos_internos: Decimal = Field(Decimal("0"), ge=0)
    otros_tributos: Decimal = Field(Decimal("0"), ge=0)
    redondeo: Decimal = Field(Decimal("0"), ge=-100, le=100)
    compra_asociada_id: uuid.UUID | None = None
    observaciones: str | None = None
    items: list[ItemIn] = Field(min_length=1)


class ItemOut(BaseModel):
    id: uuid.UUID
    orden: int
    articulo_id: uuid.UUID | None
    variante_id: uuid.UUID | None
    codigo: str | None
    descripcion: str
    cantidad: Decimal
    costo_unitario: Decimal
    bonif_1: Decimal
    bonif_2: Decimal
    tasa_iva: Decimal
    importe_neto: Decimal
    importe_iva: Decimal
    importe_total: Decimal
    model_config = {"from_attributes": True}


class VencimientoOut(BaseModel):
    nro_cuota: int
    fecha_vto: date
    importe: Decimal
    model_config = {"from_attributes": True}


class CompraListaOut(BaseModel):
    """Fila de grilla: la compra sin hijos (items/vencimientos). El detalle
    completo se pide por id (GET /comprobantes/{compra_id})."""

    id: uuid.UUID
    clase: str
    tipo_codigo: str
    tipo_descripcion: str
    letra: str
    punto_venta: int
    numero: int
    numero_formateado: str
    fecha: date
    periodo_iva: date | None
    proveedor_id: uuid.UUID
    proveedor_nombre: str
    proveedor_cuit: str | None
    proveedor_condicion_iva: str
    contado: bool
    condicion_desc: str | None
    actualiza_stock: bool
    actualiza_costos: bool
    neto_gravado: Decimal
    no_gravado: Decimal
    exento: Decimal
    iva: Decimal
    percepcion_iva: Decimal
    percepcion_iibb: Decimal
    impuestos_internos: Decimal
    otros_tributos: Decimal
    redondeo: Decimal
    total: Decimal
    saldo: Decimal
    estado: str
    compra_asociada_id: uuid.UUID | None
    observaciones: str | None


class CompraOut(CompraListaOut):
    items: list[ItemOut]
    vencimientos: list[VencimientoOut]


class ArticuloProveedorUpsert(BaseModel):
    articulo_id: uuid.UUID
    proveedor_id: uuid.UUID
    codigo_proveedor: str | None = Field(None, max_length=30)
    costo: Decimal = Field(Decimal("0"), ge=0)
    bonif_1: Decimal = Field(Decimal("0"), ge=0, le=100)
    bonif_2: Decimal = Field(Decimal("0"), ge=0, le=100)
    bonif_3: Decimal = Field(Decimal("0"), ge=0, le=100)


# ===== Helpers =====

def _fmt_numero(pv: int, numero: int) -> str:
    return f"{pv:04d}-{numero:08d}"


def _tipo_codigo_para(clase: str, letra: str) -> str:
    por_clase = {"factura": "FC", "nota_debito": "ND", "nota_credito": "NC"}
    if clase in por_clase:
        return por_clase[clase] + letra
    return "REMP"


def _campos_base(compra: Compra) -> dict:
    return dict(
        id=compra.id,
        clase=compra.tipo.clase,
        tipo_codigo=compra.tipo_codigo,
        tipo_descripcion=compra.tipo.descripcion,
        letra=compra.letra,
        punto_venta=compra.punto_venta,
        numero=compra.numero,
        numero_formateado=_fmt_numero(compra.punto_venta, compra.numero),
        fecha=compra.fecha,
        periodo_iva=compra.periodo_iva,
        proveedor_id=compra.proveedor_id,
        proveedor_nombre=compra.proveedor_nombre,
        proveedor_cuit=compra.proveedor_cuit,
        proveedor_condicion_iva=compra.proveedor_condicion_iva,
        contado=compra.contado,
        condicion_desc=compra.condicion_desc,
        actualiza_stock=compra.actualiza_stock,
        actualiza_costos=compra.actualiza_costos,
        neto_gravado=compra.neto_gravado,
        no_gravado=compra.no_gravado,
        exento=compra.exento,
        iva=compra.iva,
        percepcion_iva=compra.percepcion_iva,
        percepcion_iibb=compra.percepcion_iibb,
        impuestos_internos=compra.impuestos_internos,
        otros_tributos=compra.otros_tributos,
        redondeo=compra.redondeo,
        total=compra.total,
        saldo=compra.saldo,
        estado=compra.estado,
        compra_asociada_id=compra.compra_asociada_id,
        observaciones=compra.observaciones,
    )


def _out_lista(compra: Compra) -> CompraListaOut:
    return CompraListaOut(**_campos_base(compra))


def _out(compra: Compra) -> CompraOut:
    return CompraOut(
        **_campos_base(compra),
        items=[ItemOut.model_validate(i) for i in compra.items],
        vencimientos=[VencimientoOut.model_validate(v) for v in compra.vencimientos],
    )


def _aplicar_busqueda(stmt, q: str):
    """q numérico (con o sin guiones) = número del papel; texto = AND
    multi-palabra sobre el nombre del proveedor (patrón de ventas)."""
    q = q.strip()
    if not q:
        return stmt
    solo_digitos = re.sub(r"\D", "", q)
    if solo_digitos and not re.sub(r"[\d\s\-]", "", q):
        numero = int(solo_digitos[-8:]) if len(solo_digitos) > 8 else int(solo_digitos)
        return stmt.where(Compra.numero == numero)
    return stmt.where(
        and_(*(Compra.proveedor_nombre.ilike(f"%{tok}%") for tok in q.split()))
    )


async def _cargar(db: AsyncSession, tenant_id: uuid.UUID, compra_id: uuid.UUID) -> Compra:
    # populate_existing: mismo gotcha que ventas (sesión no expira al commit)
    compra = await db.scalar(
        select(Compra)
        .where(Compra.id == compra_id, Compra.tenant_id == tenant_id)
        .execution_options(populate_existing=True)
    )
    if compra is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return compra


async def _snapshot_proveedor(
    db: AsyncSession, tenant_id: uuid.UUID, proveedor_id: uuid.UUID
) -> dict:
    proveedor = await db.scalar(
        select(Proveedor).where(
            Proveedor.id == proveedor_id, Proveedor.tenant_id == tenant_id
        )
    )
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if not proveedor.activo:
        raise HTTPException(status_code=409, detail="El proveedor está inactivo")
    e = proveedor.entidad
    return {
        "proveedor_id": proveedor.id,
        "proveedor_nombre": e.razon_social,
        "proveedor_cuit": e.nro_documento if e.tipo_documento == "CUIT" else None,
        "proveedor_condicion_iva": e.condicion_iva,
    }


async def _armar_items(
    db: AsyncSession, tenant_id: uuid.UUID, items_in: list[ItemIn]
) -> list[dict]:
    """Valida artículos/variantes del tenant y completa snapshot (patrón ventas)."""
    ids = [i.articulo_id for i in items_in if i.articulo_id]
    articulos: dict[uuid.UUID, Articulo] = {}
    con_variantes: set[uuid.UUID] = set()
    if ids:
        filas = await db.scalars(
            select(Articulo).where(Articulo.id.in_(ids), Articulo.tenant_id == tenant_id)
        )
        articulos = {a.id: a for a in filas}
        filas_v = await db.execute(
            select(ArticuloVariante.articulo_id)
            .where(
                ArticuloVariante.tenant_id == tenant_id,
                ArticuloVariante.articulo_id.in_(ids),
                ArticuloVariante.activo.is_(True),
            )
            .distinct()
        )
        con_variantes = {x for (x,) in filas_v}

    resultado = []
    for it in items_in:
        art = None
        if it.articulo_id:
            art = articulos.get(it.articulo_id)
            if art is None:
                raise HTTPException(status_code=422, detail="Artículo inexistente en la empresa")
            if it.articulo_id in con_variantes and it.variante_id is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"'{art.descripcion}' tiene variantes: indicá cuál",
                )
            if it.variante_id is not None:
                variante = await db.scalar(
                    select(ArticuloVariante).where(
                        ArticuloVariante.id == it.variante_id,
                        ArticuloVariante.tenant_id == tenant_id,
                        ArticuloVariante.articulo_id == it.articulo_id,
                    )
                )
                if variante is None:
                    raise HTTPException(
                        status_code=422, detail="La variante no pertenece al artículo"
                    )
        elif not (it.descripcion or "").strip():
            raise HTTPException(
                status_code=422, detail="Ítem sin artículo requiere descripción"
            )
        resultado.append(
            {
                "articulo_id": it.articulo_id,
                "variante_id": it.variante_id,
                "codigo": art.codigo if art else None,
                "descripcion": (it.descripcion or "").strip() or (art.descripcion if art else ""),
                "cantidad": it.cantidad,
                "costo_unitario": it.costo_unitario,
                "bonif_1": it.bonif_1,
                "bonif_2": it.bonif_2,
                "tasa_iva": it.tasa_iva if it.tasa_iva is not None else (
                    art.tasa_iva if art else Decimal("21")
                ),
            }
        )
    return resultado


async def _aplicar_calculo(db: AsyncSession, compra: Compra, calculo: dict) -> None:
    """Reemplaza ítems con el cálculo del servidor (insert/delete por id,
    sin tocar colecciones — gotcha async de ventas)."""
    from sqlalchemy import delete

    await db.execute(delete(CompraItem).where(CompraItem.compra_id == compra.id))
    for it in calculo["items"]:
        db.add(
            CompraItem(
                compra_id=compra.id,
                tenant_id=compra.tenant_id,
                orden=it["orden"],
                articulo_id=it["articulo_id"],
                variante_id=it["variante_id"],
                codigo=it["codigo"],
                descripcion=it["descripcion"][:120],
                cantidad=it["cantidad"],
                costo_unitario=it["costo_unitario"],
                bonif_1=it["bonif_1"],
                bonif_2=it["bonif_2"],
                tasa_iva=it["tasa_iva"],
                importe_neto=it["importe_neto"],
                importe_iva=it["importe_iva"],
                importe_total=it["importe_total"],
            )
        )
    for campo in (
        "neto_gravado", "no_gravado", "exento", "iva", "percepcion_iva",
        "percepcion_iibb", "impuestos_internos", "otros_tributos", "redondeo", "total",
    ):
        setattr(compra, campo, calculo[campo])


async def _validar_asociada(
    db: AsyncSession, tenant_id: uuid.UUID, body: CompraIn
) -> Compra | None:
    """NC/ND de compra puede referenciar la factura que ajusta (opcional: el
    papel del proveedor existe igual sin ese dato)."""
    if body.compra_asociada_id is None:
        return None
    if body.clase not in ("nota_credito", "nota_debito"):
        raise HTTPException(
            status_code=422, detail="Solo NC/ND llevan compra asociada"
        )
    asociada = await _cargar(db, tenant_id, body.compra_asociada_id)
    if asociada.estado != "registrado" or asociada.tipo.clase != "factura":
        raise HTTPException(
            status_code=422, detail="La compra asociada debe ser una factura registrada"
        )
    if body.proveedor_id != asociada.proveedor_id:
        raise HTTPException(
            status_code=422, detail="La NC/ND debe ser del mismo proveedor que la factura"
        )
    return asociada


def _validar_numeracion(body: CompraIn) -> None:
    if body.clase in CLASES_FISCALES and body.numero < 1:
        raise HTTPException(
            status_code=422, detail="Cargá el número del comprobante del proveedor"
        )


async def _condicion_desc(
    db: AsyncSession, tenant_id: uuid.UUID, condicion_id: uuid.UUID | None
) -> str | None:
    if condicion_id is None:
        return None
    cond = await db.scalar(
        select(CondicionVenta).where(
            CondicionVenta.id == condicion_id, CondicionVenta.tenant_id == tenant_id
        )
    )
    if cond is None:
        raise HTTPException(status_code=404, detail="Condición de compra no encontrada")
    return cond.descripcion


def _calcular(body: CompraIn, items: list[dict], letra: str) -> dict:
    try:
        return sc.calcular_compra(
            items,
            letra,
            no_gravado=body.no_gravado,
            exento=body.exento,
            percepcion_iva=body.percepcion_iva,
            percepcion_iibb=body.percepcion_iibb,
            impuestos_internos=body.impuestos_internos,
            otros_tributos=body.otros_tributos,
            redondeo=body.redondeo,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ===== CRUD de borradores =====

@router.post("/comprobantes", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
async def crear_compra(
    body: CompraIn,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    _validar_numeracion(body)
    snapshot = await _snapshot_proveedor(db, usuario.tenant_id, body.proveedor_id)
    await _validar_asociada(db, usuario.tenant_id, body)
    condicion_desc = await _condicion_desc(db, usuario.tenant_id, body.condicion_compra_id)

    letra = "X" if body.clase == "remito" else body.letra
    items = await _armar_items(db, usuario.tenant_id, body.items)
    calculo = _calcular(body, items, letra)

    compra = Compra(
        tenant_id=usuario.tenant_id,
        tipo_codigo=_tipo_codigo_para(body.clase, letra),
        letra=letra,
        punto_venta=body.punto_venta,
        numero=body.numero,
        fecha=body.fecha or date.today(),
        periodo_iva=body.periodo_iva,
        contado=body.contado,
        condicion_compra_id=body.condicion_compra_id,
        condicion_desc=condicion_desc,
        deposito_id=body.deposito_id,
        actualiza_stock=body.actualiza_stock,
        actualiza_costos=body.actualiza_costos,
        compra_asociada_id=body.compra_asociada_id,
        observaciones=body.observaciones,
        creado_por=usuario.id,
        **snapshot,
    )
    db.add(compra)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ese comprobante del proveedor ya está cargado (mismo tipo, punto de venta y número)",
        )
    await _aplicar_calculo(db, compra, calculo)
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, compra.id))


def _filtro_compras(stmt, q, clase, estado, proveedor_id, desde, hasta, con_saldo):
    if clase:
        stmt = stmt.join(TipoComprobanteCompra).where(TipoComprobanteCompra.clase == clase)
    if estado:
        stmt = stmt.where(Compra.estado == estado)
    if proveedor_id:
        stmt = stmt.where(Compra.proveedor_id == proveedor_id)
    if desde:
        stmt = stmt.where(Compra.fecha >= desde)
    if hasta:
        stmt = stmt.where(Compra.fecha <= hasta)
    if con_saldo:
        stmt = stmt.where(Compra.saldo != 0)
    return _aplicar_busqueda(stmt, q)


@router.get("/comprobantes", response_model=list[CompraListaOut])
async def listar_compras(
    response: Response,
    q: str = "",
    clase: str | None = None,
    estado: str | None = None,
    proveedor_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    con_saldo: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = _filtro_compras(
        select(Compra).where(Compra.tenant_id == usuario.tenant_id),
        q, clase, estado, proveedor_id, desde, hasta, con_saldo,
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        # noload: la grilla no muestra hijos (patrón de ventas)
        stmt.options(noload(Compra.items), noload(Compra.vencimientos))
        .order_by(Compra.fecha.desc(), Compra.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return [_out_lista(c) for c in filas]


@router.get("/comprobantes/export.csv")
async def exportar_compras_csv(
    q: str = "",
    clase: str | None = None,
    estado: str | None = None,
    proveedor_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    con_saldo: bool = False,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Export universal (Fase 7): las compras del filtro actual a CSV es-AR
    (tope 5000 filas)."""
    stmt = _filtro_compras(
        select(Compra).where(Compra.tenant_id == usuario.tenant_id),
        q, clase, estado, proveedor_id, desde, hasta, con_saldo,
    )
    filas = await db.scalars(
        stmt.options(noload(Compra.items), noload(Compra.vencimientos))
        .order_by(Compra.fecha.desc(), Compra.created_at.desc())
        .limit(5000)
    )
    encabezado = [
        "Fecha", "Comprobante", "Proveedor", "CUIT", "Cond. IVA",
        "Neto gravado", "No gravado", "Exento", "IVA", "Percepciones",
        "Total", "Saldo", "Estado",
    ]
    rows = []
    for c in filas:
        o = _out_lista(c)
        percep = o.percepcion_iva + o.percepcion_iibb
        rows.append([
            o.fecha.strftime("%d/%m/%Y"),
            o.numero_formateado,
            o.proveedor_nombre,
            o.proveedor_cuit or "",
            o.proveedor_condicion_iva,
            num(o.neto_gravado), num(o.no_gravado), num(o.exento), num(o.iva),
            num(percep), num(o.total), num(o.saldo), o.estado,
        ])
    return csv_response("compras.csv", encabezado, rows)


@router.get("/comprobantes/{compra_id}", response_model=CompraOut)
async def ver_compra(
    compra_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return _out(await _cargar(db, usuario.tenant_id, compra_id))


@router.put("/comprobantes/{compra_id}", response_model=CompraOut)
async def actualizar_borrador(
    compra_id: uuid.UUID,
    body: CompraIn,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    compra = await _cargar(db, usuario.tenant_id, compra_id)
    if compra.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se editan borradores")
    _validar_numeracion(body)
    snapshot = await _snapshot_proveedor(db, usuario.tenant_id, body.proveedor_id)
    await _validar_asociada(db, usuario.tenant_id, body)
    condicion_desc = await _condicion_desc(db, usuario.tenant_id, body.condicion_compra_id)

    letra = "X" if body.clase == "remito" else body.letra
    items = await _armar_items(db, usuario.tenant_id, body.items)
    calculo = _calcular(body, items, letra)

    compra.tipo_codigo = _tipo_codigo_para(body.clase, letra)
    compra.letra = letra
    compra.punto_venta = body.punto_venta
    compra.numero = body.numero
    compra.fecha = body.fecha or compra.fecha
    compra.periodo_iva = body.periodo_iva
    compra.contado = body.contado
    compra.condicion_compra_id = body.condicion_compra_id
    compra.condicion_desc = condicion_desc
    compra.deposito_id = body.deposito_id
    compra.actualiza_stock = body.actualiza_stock
    compra.actualiza_costos = body.actualiza_costos
    compra.compra_asociada_id = body.compra_asociada_id
    compra.observaciones = body.observaciones
    compra.updated_at = func.now()
    for campo, valor in snapshot.items():
        setattr(compra, campo, valor)
    await _aplicar_calculo(db, compra, calculo)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ese comprobante del proveedor ya está cargado (mismo tipo, punto de venta y número)",
        )
    return _out(await _cargar(db, usuario.tenant_id, compra_id))


@router.delete("/comprobantes/{compra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_borrador(
    compra_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    compra = await _cargar(db, usuario.tenant_id, compra_id)
    if compra.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se borran borradores")
    await db.delete(compra)
    await db.commit()


# ===== Registro (el "emitir" de compras) =====

async def _deposito_para_stock(db: AsyncSession, compra: Compra) -> Deposito:
    if compra.deposito_id is not None:
        dep = await db.scalar(
            select(Deposito).where(
                Deposito.id == compra.deposito_id, Deposito.tenant_id == compra.tenant_id
            )
        )
        if dep is not None:
            return dep
    dep = await db.scalar(
        select(Deposito)
        .where(Deposito.tenant_id == compra.tenant_id, Deposito.activo.is_(True))
        .order_by(Deposito.codigo)
        .limit(1)
    )
    if dep is None:
        raise HTTPException(
            status_code=422, detail="No hay depósito activo para ingresar stock"
        )
    return dep


async def _mover_stock(
    db: AsyncSession, compra: Compra, usuario_id: uuid.UUID, signo: int, tipo_mov: str
) -> None:
    """Ingresa (+1) o descarga (-1) stock por ítem con artículo que controla
    stock. Patrón Fase 2/3: fila lockeada + saldo_resultante sellado."""
    deposito = await _deposito_para_stock(db, compra)
    etiqueta = f"{compra.tipo_codigo} {_fmt_numero(compra.punto_venta, compra.numero)}"
    ids = [i.articulo_id for i in compra.items if i.articulo_id]
    if not ids:
        return
    articulos = {
        a.id: a
        for a in await db.scalars(
            select(Articulo).where(
                Articulo.id.in_(ids), Articulo.tenant_id == compra.tenant_id
            )
        )
    }
    for item in compra.items:
        art = articulos.get(item.articulo_id) if item.articulo_id else None
        if art is None or not art.controla_stock:
            continue
        filtro_variante = (
            ArticuloStock.variante_id.is_(None)
            if item.variante_id is None
            else ArticuloStock.variante_id == item.variante_id
        )
        fila = await db.scalar(
            select(ArticuloStock)
            .where(
                ArticuloStock.tenant_id == compra.tenant_id,
                ArticuloStock.articulo_id == item.articulo_id,
                ArticuloStock.deposito_id == deposito.id,
                filtro_variante,
            )
            .with_for_update()
        )
        if fila is None:
            fila = ArticuloStock(
                tenant_id=compra.tenant_id,
                articulo_id=item.articulo_id,
                deposito_id=deposito.id,
                variante_id=item.variante_id,
                cantidad=0,
            )
            db.add(fila)
            await db.flush()
        delta = item.cantidad * signo
        fila.cantidad = fila.cantidad + delta
        fila.updated_at = func.now()
        db.add(
            StockMovimiento(
                tenant_id=compra.tenant_id,
                articulo_id=item.articulo_id,
                deposito_id=deposito.id,
                variante_id=item.variante_id,
                tipo=tipo_mov,
                cantidad=delta,
                saldo_resultante=fila.cantidad,
                comprobante=etiqueta[:30],
                usuario_id=usuario_id,
                grupo_id=compra.id,
            )
        )


async def _generar_vencimientos(db: AsyncSession, compra: Compra) -> None:
    if compra.contado or compra.condicion_compra_id is None:
        return
    cond = await db.scalar(
        select(CondicionVenta).where(CondicionVenta.id == compra.condicion_compra_id)
    )
    dias = cond.dias if cond and cond.dias else [0]
    n = len(dias)
    cuota = sc.r2(compra.total / n)
    acumulado = Decimal("0")
    for i, d in enumerate(dias, start=1):
        importe = compra.total - acumulado if i == n else cuota  # la última absorbe el redondeo
        acumulado += importe
        db.add(
            CompraVencimiento(
                compra_id=compra.id,
                tenant_id=compra.tenant_id,
                nro_cuota=i,
                fecha_vto=compra.fecha + timedelta(days=d),
                importe=importe,
            )
        )


@router.post("/comprobantes/{compra_id}/registrar", response_model=CompraOut)
async def registrar_compra(
    compra_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    compra = await _cargar(db, usuario.tenant_id, compra_id)
    if compra.estado != "borrador":
        raise HTTPException(status_code=409, detail="La compra ya fue registrada o anulada")
    if not compra.items:
        raise HTTPException(status_code=422, detail="La compra no tiene ítems")
    clase = compra.tipo.clase

    asociada = None
    if compra.compra_asociada_id is not None:
        asociada = await _cargar(db, usuario.tenant_id, compra.compra_asociada_id)

    compra.estado = "registrado"
    compra.periodo_iva = compra.periodo_iva or compra.fecha.replace(day=1)
    compra.registrado_at = datetime.now(timezone.utc)
    compra.registrado_por = usuario.id
    compra.updated_at = func.now()

    # Cuenta corriente del proveedor
    if clase in ("factura", "nota_debito"):
        compra.saldo = Decimal("0") if compra.contado else compra.total
        await _generar_vencimientos(db, compra)
    elif clase == "nota_credito":
        credito = compra.total
        if asociada is not None and asociada.saldo > 0:
            aplicado = min(credito, asociada.saldo)
            db.add(
                ImputacionCompra(
                    tenant_id=compra.tenant_id,
                    proveedor_id=compra.proveedor_id,
                    credito_id=compra.id,
                    compra_id=asociada.id,
                    importe=aplicado,
                    creado_por=usuario.id,
                )
            )
            asociada.saldo = asociada.saldo - aplicado
            credito -= aplicado
        # factura contado (ya pagada): el resto es plata que devuelve el
        # proveedor en el momento — no queda crédito en cta. cte.
        compra.saldo = Decimal("0") if (asociada is not None and asociada.contado) else credito

    # Stock
    if compra.actualiza_stock:
        if clase == "factura":
            await _mover_stock(db, compra, usuario.id, +1, "compra")
        elif clase == "remito":
            await _mover_stock(db, compra, usuario.id, +1, "remito")
        elif clase == "nota_credito":
            await _mover_stock(db, compra, usuario.id, -1, "devolucion")

    # Costos + comparativo (solo facturas: la NC devuelve, la ND ajusta importes)
    if clase == "factura":
        await sc.actualizar_costos_articulos(db, compra)

    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, compra_id))


@router.post("/comprobantes/{compra_id}/anular", response_model=CompraOut)
async def anular_compra(
    compra_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("compras", "anular")),
    db: AsyncSession = Depends(get_db),
):
    """Anula una compra registrada revirtiendo stock y cta. cte. El costo del
    artículo NO se revierte (puede haber compras posteriores); se corrige
    desde Artículos si hace falta."""
    compra = await _cargar(db, usuario.tenant_id, compra_id)
    if compra.estado != "registrado":
        raise HTTPException(status_code=409, detail="Solo se anula una compra registrada")
    clase = compra.tipo.clase

    pagos = (
        await db.scalars(
            select(ImputacionCompra).where(
                ImputacionCompra.tenant_id == usuario.tenant_id,
                ImputacionCompra.compra_id == compra.id,
            )
        )
    ).all()
    if pagos:
        raise HTTPException(
            status_code=409,
            detail="La compra tiene pagos/créditos imputados: anulá primero la orden de pago o desimputá",
        )

    if clase == "nota_credito":
        # revertir las imputaciones donde esta NC fue el crédito
        imputaciones = (
            await db.scalars(
                select(ImputacionCompra).where(
                    ImputacionCompra.tenant_id == usuario.tenant_id,
                    ImputacionCompra.credito_id == compra.id,
                )
            )
        ).all()
        for imp in imputaciones:
            deuda = await db.scalar(
                select(Compra).where(Compra.id == imp.compra_id).with_for_update(of=Compra)
            )
            deuda.saldo = deuda.saldo + imp.importe
            await db.delete(imp)

    if compra.actualiza_stock:
        if clase in ("factura", "remito"):
            await _mover_stock(db, compra, usuario.id, -1, "anulacion")
        elif clase == "nota_credito":
            await _mover_stock(db, compra, usuario.id, +1, "anulacion")

    compra.estado = "anulado"
    compra.saldo = Decimal("0")
    compra.updated_at = func.now()
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, compra_id))


# ===== Comparativo de precios por proveedor (ART_PROV) =====

@router.get("/comparativo/{articulo_id}")
async def comparativo_articulo(
    articulo_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("compras", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Qué proveedor vende este artículo más barato (costo neto tras bonifs)."""
    articulo = await db.scalar(
        select(Articulo).where(
            Articulo.id == articulo_id, Articulo.tenant_id == usuario.tenant_id
        )
    )
    if articulo is None:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")

    filas = (
        await db.execute(
            select(ArticuloProveedor, Proveedor, Entidad)
            .join(Proveedor, ArticuloProveedor.proveedor_id == Proveedor.id)
            .join(Entidad, Proveedor.entidad_id == Entidad.id)
            .where(
                ArticuloProveedor.tenant_id == usuario.tenant_id,
                ArticuloProveedor.articulo_id == articulo_id,
            )
        )
    ).all()

    from app.api.v1.proveedores import costo_neto

    resultado = []
    for ap, prov, ent in filas:
        resultado.append(
            {
                "articulo_proveedor_id": str(ap.id),
                "proveedor_id": str(prov.id),
                "proveedor_codigo": prov.codigo,
                "proveedor_nombre": ent.razon_social,
                "codigo_proveedor": ap.codigo_proveedor,
                "costo_lista": str(ap.costo),
                "bonif_1": str(ap.bonif_1),
                "bonif_2": str(ap.bonif_2),
                "bonif_3": str(ap.bonif_3),
                "costo_neto": str(costo_neto(ap)),
                "ultima_compra": ap.ultima_compra.isoformat() if ap.ultima_compra else None,
                "habitual": articulo.proveedor_habitual_id == prov.id,
            }
        )
    resultado.sort(key=lambda r: Decimal(r["costo_neto"]))
    return {
        "articulo": {
            "id": str(articulo.id),
            "codigo": articulo.codigo,
            "descripcion": articulo.descripcion,
            "costo_actual": str(articulo.costo),
            "costo_con_iva": articulo.costo_con_iva,
        },
        "proveedores": resultado,
    }


@router.put("/articulo-proveedor", status_code=status.HTTP_201_CREATED)
async def upsert_articulo_proveedor(
    body: ArticuloProveedorUpsert,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Carga manual de la relación artículo × proveedor (sin esperar una compra)."""
    articulo = await db.scalar(
        select(Articulo).where(
            Articulo.id == body.articulo_id, Articulo.tenant_id == usuario.tenant_id
        )
    )
    if articulo is None:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    proveedor = await db.scalar(
        select(Proveedor).where(
            Proveedor.id == body.proveedor_id, Proveedor.tenant_id == usuario.tenant_id
        )
    )
    if proveedor is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    ap = await db.scalar(
        select(ArticuloProveedor).where(
            ArticuloProveedor.tenant_id == usuario.tenant_id,
            ArticuloProveedor.articulo_id == body.articulo_id,
            ArticuloProveedor.proveedor_id == body.proveedor_id,
        )
    )
    if ap is None:
        ap = ArticuloProveedor(
            tenant_id=usuario.tenant_id,
            articulo_id=body.articulo_id,
            proveedor_id=body.proveedor_id,
        )
        db.add(ap)
    ap.codigo_proveedor = (body.codigo_proveedor or "").strip() or None
    ap.costo = body.costo
    ap.bonif_1 = body.bonif_1
    ap.bonif_2 = body.bonif_2
    ap.bonif_3 = body.bonif_3
    ap.updated_at = func.now()
    await db.commit()
    return {"ok": True, "id": str(ap.id)}


@router.delete("/articulo-proveedor/{ap_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_articulo_proveedor(
    ap_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("compras", "editar")),
    db: AsyncSession = Depends(get_db),
):
    ap = await db.scalar(
        select(ArticuloProveedor).where(
            ArticuloProveedor.id == ap_id, ArticuloProveedor.tenant_id == usuario.tenant_id
        )
    )
    if ap is None:
        raise HTTPException(status_code=404, detail="Relación no encontrada")
    await db.delete(ap)
    await db.commit()
