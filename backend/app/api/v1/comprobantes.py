"""Comprobantes de venta (Fase 3): presupuestos, remitos, facturas/NC/ND.

Circuito: borrador (editable) → emitir (fiscales: CAE vía ARCA; internos:
numeración local) → inmutable. Un fiscal emitido NO se anula: se revierte con
nota de crédito (docs/FACTURACION-ARCA.md §6). La letra y los totales los
calcula SIEMPRE el servidor (services/ventas.py).
"""

import re
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.config import settings
from app.core.csv_export import csv_response, num
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    ArcaConfig,
    Articulo,
    ArticuloStock,
    ArticuloVariante,
    Cliente,
    Comprobante,
    ComprobanteAlicuota,
    ComprobanteItem,
    ComprobanteVencimiento,
    CondicionVenta,
    Deposito,
    Imputacion,
    PosCaja,
    PuntoVenta,
    StockMovimiento,
    SucursalNodo,
    Tenant,
    TipoComprobante,
    Usuario,
    Vendedor,
)
from app.services import stock_valor
from app.services import ventas as sv
from app.services.arca import ErrorArca, emitir_fiscal
from app.services.arca import qr as arca_qr
from app.services.arca.wsaa import ErrorWsaa
from app.services.arca.wsfev1 import ErrorWsfe

router = APIRouter(prefix="/ventas/comprobantes", tags=["comprobantes"])

CLASES_FISCALES = ("factura", "nota_debito", "nota_credito")
CLASES = CLASES_FISCALES + ("presupuesto", "remito")


# ===== Schemas =====

class ItemIn(BaseModel):
    articulo_id: uuid.UUID | None = None
    variante_id: uuid.UUID | None = None
    descripcion: str | None = Field(None, max_length=120)  # texto libre si no hay artículo
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)
    bonif_pct: Decimal = Field(Decimal("0"), ge=0, le=100)
    tasa_iva: Decimal | None = None  # default: la del artículo (o 21)


class ComprobanteIn(BaseModel):
    clase: str = Field(pattern="^(factura|nota_debito|nota_credito|presupuesto|remito)$")
    punto_venta_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    fecha: date | None = None
    contado: bool = True
    condicion_venta_id: uuid.UUID | None = None
    lista_precios: int = Field(1, ge=1, le=4)
    deposito_id: uuid.UUID | None = None
    actualiza_stock: bool = True
    moneda: str = Field("PES", pattern="^PES$")  # MVP: pesos (USD se convierte con la cotización)
    descuento_pct: Decimal = Field(Decimal("0"), ge=0, le=100)
    precios_con_iva: bool = False
    comprobante_asociado_id: uuid.UUID | None = None
    # F11: vendedor de la venta; si no viene, defaultea al habitual del cliente
    vendedor_id: uuid.UUID | None = None
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
    precio_unitario: Decimal
    bonif_pct: Decimal
    tasa_iva: Decimal
    importe_neto: Decimal
    importe_iva: Decimal
    importe_total: Decimal
    model_config = {"from_attributes": True}


class AlicuotaOut(BaseModel):
    tasa: Decimal
    codigo_arca: int
    base: Decimal
    importe: Decimal
    model_config = {"from_attributes": True}


class VencimientoOut(BaseModel):
    nro_cuota: int
    fecha_vto: date
    importe: Decimal
    model_config = {"from_attributes": True}


class ComprobanteListaOut(BaseModel):
    """Fila de grilla: el comprobante sin hijos (items/alícuotas/vencimientos).
    El detalle completo se pide por id (GET /{comp_id})."""

    id: uuid.UUID
    clase: str
    tipo_codigo: str
    tipo_descripcion: str
    letra: str
    punto_venta: int
    numero: int | None
    numero_formateado: str | None
    fecha: date
    cliente_id: uuid.UUID | None
    receptor_nombre: str
    receptor_doc_tipo: int
    receptor_doc_nro: str | None
    receptor_condicion_iva: str
    contado: bool
    condicion_venta_desc: str | None
    moneda: str
    descuento_pct: Decimal
    neto_gravado: Decimal
    iva: Decimal
    total: Decimal
    saldo: Decimal
    estado: str
    cae: str | None
    cae_vencimiento: date | None
    arca_resultado: str | None
    arca_observaciones: str | None
    comprobante_asociado_id: uuid.UUID | None
    origen_id: uuid.UUID | None
    vendedor_id: uuid.UUID | None = None
    observaciones: str | None


class ComprobanteOut(ComprobanteListaOut):
    items: list[ItemOut]
    alicuotas: list[AlicuotaOut]
    vencimientos: list[VencimientoOut]


# ===== Helpers =====

def _fmt_numero(pv: int, numero: int | None) -> str | None:
    return f"{pv:04d}-{numero:08d}" if numero is not None else None


def _campos_base(comp: Comprobante) -> dict:
    return dict(
        id=comp.id,
        clase=comp.tipo.clase,
        tipo_codigo=comp.tipo_codigo,
        tipo_descripcion=comp.tipo.descripcion,
        letra=comp.letra,
        punto_venta=comp.punto_venta.numero,
        numero=comp.numero,
        numero_formateado=_fmt_numero(comp.punto_venta.numero, comp.numero),
        fecha=comp.fecha,
        cliente_id=comp.cliente_id,
        receptor_nombre=comp.receptor_nombre,
        receptor_doc_tipo=comp.receptor_doc_tipo,
        receptor_doc_nro=comp.receptor_doc_nro,
        receptor_condicion_iva=comp.receptor_condicion_iva,
        contado=comp.contado,
        condicion_venta_desc=comp.condicion_venta_desc,
        moneda=comp.moneda,
        descuento_pct=comp.descuento_pct,
        neto_gravado=comp.neto_gravado,
        iva=comp.iva,
        total=comp.total,
        saldo=comp.saldo,
        estado=comp.estado,
        cae=comp.cae,
        cae_vencimiento=comp.cae_vencimiento,
        arca_resultado=comp.arca_resultado,
        arca_observaciones=comp.arca_observaciones,
        comprobante_asociado_id=comp.comprobante_asociado_id,
        origen_id=comp.origen_id,
        vendedor_id=comp.vendedor_id,
        observaciones=comp.observaciones,
    )


def _out_lista(comp: Comprobante) -> ComprobanteListaOut:
    return ComprobanteListaOut(**_campos_base(comp))


def _out(comp: Comprobante) -> ComprobanteOut:
    return ComprobanteOut(
        **_campos_base(comp),
        items=[ItemOut.model_validate(i) for i in comp.items],
        alicuotas=[AlicuotaOut.model_validate(a) for a in comp.alicuotas],
        vencimientos=[VencimientoOut.model_validate(v) for v in comp.vencimientos],
    )


def _aplicar_busqueda(stmt, q: str):
    """q numérico (con o sin guiones) = número del comprobante; texto =
    AND multi-palabra sobre el nombre del receptor."""
    q = q.strip()
    if not q:
        return stmt
    solo_digitos = re.sub(r"\D", "", q)
    if solo_digitos and not re.sub(r"[\d\s\-]", "", q):
        # "0001-00000123" → 123 (se ignora el PV; el número puro alcanza)
        numero = int(solo_digitos[-8:]) if len(solo_digitos) > 8 else int(solo_digitos)
        return stmt.where(Comprobante.numero == numero)
    return stmt.where(
        and_(*(Comprobante.receptor_nombre.ilike(f"%{tok}%") for tok in q.split()))
    )


async def _cargar(db: AsyncSession, tenant_id: uuid.UUID, comp_id: uuid.UUID) -> Comprobante:
    # populate_existing: la sesión no expira al commit (db.py), así que las
    # relecturas post-commit deben pisar colecciones ya cargadas (vencimientos
    # e ítems agregados por fuera de la relación quedarían stale).
    comp = await db.scalar(
        select(Comprobante)
        .where(Comprobante.id == comp_id, Comprobante.tenant_id == tenant_id)
        .execution_options(populate_existing=True)
    )
    if comp is None:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return comp


async def _snapshot_receptor(
    db: AsyncSession, tenant_id: uuid.UUID, cliente_id: uuid.UUID | None
) -> dict:
    """Congela los datos del receptor desde la BUE (o consumidor final anónimo)."""
    if cliente_id is None:
        return {
            "cliente_id": None,
            "receptor_nombre": "Consumidor Final",
            "receptor_doc_tipo": 99,
            "receptor_doc_nro": None,
            "receptor_condicion_iva": "CF",
            "receptor_domicilio": None,
        }
    cliente = await db.scalar(
        select(Cliente).where(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
    )
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if cliente.bloqueado:
        raise HTTPException(status_code=409, detail="El cliente está bloqueado")
    e = cliente.entidad
    return {
        "cliente_id": cliente.id,
        "receptor_nombre": e.razon_social,
        "receptor_doc_tipo": sv.DOC_TIPO_ARCA.get(e.tipo_documento, 99),
        "receptor_doc_nro": e.nro_documento,
        "receptor_condicion_iva": e.condicion_iva,
        "receptor_domicilio": ", ".join(p for p in (e.domicilio, e.localidad) if p) or None,
    }


async def _armar_items(
    db: AsyncSession, tenant_id: uuid.UUID, items_in: list[ItemIn]
) -> list[dict]:
    """Valida artículos/variantes del tenant y completa snapshot (código,
    descripción, tasa IVA por defecto, costo)."""
    ids = [i.articulo_id for i in items_in if i.articulo_id]
    articulos: dict[uuid.UUID, Articulo] = {}
    if ids:
        filas = await db.scalars(
            select(Articulo).where(Articulo.id.in_(ids), Articulo.tenant_id == tenant_id)
        )
        articulos = {a.id: a for a in filas}
    con_variantes: set[uuid.UUID] = set()
    if ids:
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
                "precio_unitario": it.precio_unitario,
                "bonif_pct": it.bonif_pct,
                "tasa_iva": it.tasa_iva if it.tasa_iva is not None else (
                    art.tasa_iva if art else Decimal("21")
                ),
                "costo_unitario": art.costo if art else Decimal("0"),
            }
        )
    return resultado


async def _aplicar_calculo(db: AsyncSession, comp: Comprobante, calculo: dict) -> None:
    """Reemplaza ítems y alícuotas del comprobante con el cálculo del servidor.
    Inserta/borra por comprobante_id (sin tocar las colecciones: en async un
    lazy-load accidental sobre un objeto recién flusheado rompe)."""
    from sqlalchemy import delete

    await db.execute(
        delete(ComprobanteItem).where(ComprobanteItem.comprobante_id == comp.id)
    )
    await db.execute(
        delete(ComprobanteAlicuota).where(ComprobanteAlicuota.comprobante_id == comp.id)
    )
    for it in calculo["items"]:
        db.add(
            ComprobanteItem(
                comprobante_id=comp.id,
                tenant_id=comp.tenant_id,
                orden=it["orden"],
                articulo_id=it["articulo_id"],
                variante_id=it["variante_id"],
                codigo=it["codigo"],
                descripcion=it["descripcion"][:120],
                cantidad=it["cantidad"],
                precio_unitario=it["precio_unitario"],
                bonif_pct=it["bonif_pct"],
                tasa_iva=it["tasa_iva"],
                importe_neto=it["importe_neto"],
                importe_iva=it["importe_iva"],
                importe_total=it["importe_total"],
                costo_unitario=it["costo_unitario"],
            )
        )
    for al in calculo["alicuotas"]:
        db.add(
            ComprobanteAlicuota(
                comprobante_id=comp.id,
                tenant_id=comp.tenant_id,
                tasa=al["tasa"],
                codigo_arca=al["codigo_arca"],
                base=al["base"],
                importe=al["importe"],
            )
        )
    comp.neto_gravado = calculo["neto_gravado"]
    comp.neto_no_gravado = calculo["neto_no_gravado"]
    comp.exento = calculo["exento"]
    comp.iva = calculo["iva"]
    comp.otros_tributos = calculo["otros_tributos"]
    comp.total = calculo["total"]
    comp.iva_contenido = calculo["iva_contenido"]
    comp.otros_imp_indirectos = calculo["otros_imp_indirectos"]
    comp.descuento_importe = sv.r2(
        comp.total * comp.descuento_pct / (Decimal("100") - comp.descuento_pct)
    ) if comp.descuento_pct < 100 else Decimal("0")


async def _validar_asociado(
    db: AsyncSession, tenant_id: uuid.UUID, comp_in: ComprobanteIn
) -> Comprobante | None:
    if comp_in.clase not in ("nota_credito", "nota_debito"):
        return None
    if comp_in.comprobante_asociado_id is None:
        raise HTTPException(
            status_code=422,
            detail="NC/ND requiere el comprobante asociado (RG 4540)",
        )
    asociado = await _cargar(db, tenant_id, comp_in.comprobante_asociado_id)
    if asociado.estado != "emitido" or asociado.tipo.clase != "factura":
        raise HTTPException(
            status_code=422, detail="El comprobante asociado debe ser una factura emitida"
        )
    if comp_in.cliente_id != asociado.cliente_id:
        raise HTTPException(
            status_code=422, detail="La NC/ND debe ser del mismo cliente que la factura"
        )
    return asociado


async def _resolver_vendedor(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    vendedor_id: uuid.UUID | None,
    cliente_id: uuid.UUID | None,
) -> uuid.UUID | None:
    """F11: valida el vendedor del body o defaultea al habitual del cliente."""
    if vendedor_id is not None:
        existe = await db.scalar(
            select(Vendedor.id).where(
                Vendedor.id == vendedor_id, Vendedor.tenant_id == tenant_id
            )
        )
        if existe is None:
            raise HTTPException(status_code=422, detail="Vendedor inexistente")
        return vendedor_id
    if cliente_id is not None:
        return await db.scalar(
            select(Cliente.vendedor_id).where(
                Cliente.id == cliente_id, Cliente.tenant_id == tenant_id
            )
        )
    return None


# ===== CRUD de borradores =====

@router.post("", response_model=ComprobanteOut, status_code=status.HTTP_201_CREATED)
async def crear_comprobante(
    body: ComprobanteIn,
    usuario: Usuario = Depends(requiere("ventas", "editar")),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.scalar(select(Tenant).where(Tenant.id == usuario.tenant_id))
    pv = await db.scalar(
        select(PuntoVenta).where(
            PuntoVenta.id == body.punto_venta_id,
            PuntoVenta.tenant_id == usuario.tenant_id,
            PuntoVenta.activo.is_(True),
        )
    )
    if pv is None:
        raise HTTPException(status_code=404, detail="Punto de venta no encontrado o inactivo")

    receptor = await _snapshot_receptor(db, usuario.tenant_id, body.cliente_id)
    asociado = await _validar_asociado(db, usuario.tenant_id, body)

    if body.clase in CLASES_FISCALES:
        letra = sv.letra_comprobante(tenant.condicion_iva, receptor["receptor_condicion_iva"])
    else:
        letra = "X"
    tipo_codigo = sv.tipo_codigo_para(body.clase, letra)

    condicion_desc = None
    if body.condicion_venta_id is not None:
        cond = await db.scalar(
            select(CondicionVenta).where(
                CondicionVenta.id == body.condicion_venta_id,
                CondicionVenta.tenant_id == usuario.tenant_id,
            )
        )
        if cond is None:
            raise HTTPException(status_code=404, detail="Condición de venta no encontrada")
        condicion_desc = cond.descripcion

    items = await _armar_items(db, usuario.tenant_id, body.items)
    try:
        calculo = sv.calcular_comprobante(
            items, letra, body.descuento_pct, body.precios_con_iva
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    comp = Comprobante(
        tenant_id=usuario.tenant_id,
        punto_venta_id=pv.id,
        tipo_codigo=tipo_codigo,
        letra=letra,
        fecha=body.fecha or date.today(),
        contado=body.contado,
        condicion_venta_id=body.condicion_venta_id,
        condicion_venta_desc=condicion_desc,
        lista_precios=body.lista_precios,
        deposito_id=body.deposito_id,
        actualiza_stock=body.actualiza_stock,
        moneda=body.moneda,
        cotizacion=Decimal("1"),
        descuento_pct=body.descuento_pct,
        comprobante_asociado_id=asociado.id if asociado else None,
        vendedor_id=await _resolver_vendedor(
            db, usuario.tenant_id, body.vendedor_id, body.cliente_id
        ),
        observaciones=body.observaciones,
        creado_por=usuario.id,
        **receptor,
    )
    db.add(comp)
    await db.flush()
    await _aplicar_calculo(db, comp, calculo)
    await db.commit()
    comp = await _cargar(db, usuario.tenant_id, comp.id)
    return _out(comp)


def _filtro_comprobantes(stmt, q, clase, estado, cliente_id, desde, hasta, con_saldo):
    if clase:
        stmt = stmt.join(TipoComprobante).where(TipoComprobante.clase == clase)
    if estado:
        stmt = stmt.where(Comprobante.estado == estado)
    if cliente_id:
        stmt = stmt.where(Comprobante.cliente_id == cliente_id)
    if desde:
        stmt = stmt.where(Comprobante.fecha >= desde)
    if hasta:
        stmt = stmt.where(Comprobante.fecha <= hasta)
    if con_saldo:
        stmt = stmt.where(Comprobante.saldo != 0)
    return _aplicar_busqueda(stmt, q)


@router.get("", response_model=list[ComprobanteListaOut])
async def listar_comprobantes(
    response: Response,
    q: str = "",
    clase: str | None = None,
    estado: str | None = None,
    cliente_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    con_saldo: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("ventas", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = _filtro_comprobantes(
        select(Comprobante).where(Comprobante.tenant_id == usuario.tenant_id),
        q, clase, estado, cliente_id, desde, hasta, con_saldo,
    )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        # noload: la grilla no muestra hijos — sin esto el selectin dispara
        # 3 queries extra y carga TODOS los renglones de la página
        stmt.options(
            noload(Comprobante.items),
            noload(Comprobante.alicuotas),
            noload(Comprobante.vencimientos),
        )
        .order_by(Comprobante.fecha.desc(), Comprobante.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return [_out_lista(c) for c in filas]


@router.get("/export.csv")
async def exportar_comprobantes_csv(
    q: str = "",
    clase: str | None = None,
    estado: str | None = None,
    cliente_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    con_saldo: bool = False,
    usuario: Usuario = Depends(requiere("ventas", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Export universal (Fase 7): las ventas que matchean el filtro actual, a CSV
    es-AR. Tope 5000 filas para no reventar la lambda (se avisa al front)."""
    stmt = _filtro_comprobantes(
        select(Comprobante).where(Comprobante.tenant_id == usuario.tenant_id),
        q, clase, estado, cliente_id, desde, hasta, con_saldo,
    )
    filas = await db.scalars(
        stmt.options(
            noload(Comprobante.items),
            noload(Comprobante.alicuotas),
            noload(Comprobante.vencimientos),
        )
        .order_by(Comprobante.fecha.desc(), Comprobante.created_at.desc())
        .limit(5000)
    )
    encabezado = [
        "Fecha", "Comprobante", "Cliente", "Doc", "Cond. IVA", "Moneda",
        "Neto gravado", "IVA", "Total", "Saldo", "Estado", "CAE",
    ]
    rows = []
    for c in filas:
        o = _out_lista(c)
        rows.append([
            o.fecha.strftime("%d/%m/%Y"),
            o.numero_formateado or f"{o.tipo_codigo} {o.punto_venta:04d}",
            o.receptor_nombre,
            o.receptor_doc_nro or "",
            o.receptor_condicion_iva,
            o.moneda,
            num(o.neto_gravado), num(o.iva), num(o.total), num(o.saldo),
            o.estado, o.cae or "",
        ])
    return csv_response("ventas.csv", encabezado, rows)


@router.get("/{comp_id}", response_model=ComprobanteOut)
async def ver_comprobante(
    comp_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("ventas", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return _out(await _cargar(db, usuario.tenant_id, comp_id))


@router.put("/{comp_id}", response_model=ComprobanteOut)
async def actualizar_borrador(
    comp_id: uuid.UUID,
    body: ComprobanteIn,
    usuario: Usuario = Depends(requiere("ventas", "editar")),
    db: AsyncSession = Depends(get_db),
):
    comp = await _cargar(db, usuario.tenant_id, comp_id)
    if comp.estado != "borrador":
        raise HTTPException(
            status_code=409,
            detail="Solo se editan borradores; un emitido se revierte con nota de crédito",
        )
    tenant = await db.scalar(select(Tenant).where(Tenant.id == usuario.tenant_id))
    receptor = await _snapshot_receptor(db, usuario.tenant_id, body.cliente_id)
    asociado = await _validar_asociado(db, usuario.tenant_id, body)

    if body.clase in CLASES_FISCALES:
        letra = sv.letra_comprobante(tenant.condicion_iva, receptor["receptor_condicion_iva"])
    else:
        letra = "X"

    items = await _armar_items(db, usuario.tenant_id, body.items)
    try:
        calculo = sv.calcular_comprobante(items, letra, body.descuento_pct, body.precios_con_iva)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    comp.tipo_codigo = sv.tipo_codigo_para(body.clase, letra)
    comp.letra = letra
    comp.fecha = body.fecha or comp.fecha
    comp.contado = body.contado
    comp.condicion_venta_id = body.condicion_venta_id
    comp.lista_precios = body.lista_precios
    comp.deposito_id = body.deposito_id
    comp.actualiza_stock = body.actualiza_stock
    comp.descuento_pct = body.descuento_pct
    comp.comprobante_asociado_id = asociado.id if asociado else None
    comp.vendedor_id = await _resolver_vendedor(
        db, usuario.tenant_id, body.vendedor_id, body.cliente_id
    )
    comp.observaciones = body.observaciones
    comp.updated_at = func.now()
    for campo, valor in receptor.items():
        setattr(comp, campo, valor)
    await _aplicar_calculo(db, comp, calculo)
    await db.commit()
    comp = await _cargar(db, usuario.tenant_id, comp_id)
    return _out(comp)


@router.delete("/{comp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_borrador(
    comp_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("ventas", "editar")),
    db: AsyncSession = Depends(get_db),
):
    comp = await _cargar(db, usuario.tenant_id, comp_id)
    if comp.estado != "borrador":
        raise HTTPException(status_code=409, detail="Solo se borran borradores")
    await db.delete(comp)
    await db.commit()


# ===== Emisión =====

async def _deposito_para_stock(db: AsyncSession, comp: Comprobante) -> Deposito:
    if comp.deposito_id is not None:
        dep = await db.scalar(
            select(Deposito).where(
                Deposito.id == comp.deposito_id, Deposito.tenant_id == comp.tenant_id
            )
        )
        if dep is not None:
            return dep
    dep = await db.scalar(
        select(Deposito)
        .where(Deposito.tenant_id == comp.tenant_id, Deposito.activo.is_(True))
        .order_by(Deposito.codigo)
        .limit(1)
    )
    if dep is None:
        raise HTTPException(
            status_code=422, detail="No hay depósito activo para descargar stock"
        )
    return dep


async def _mover_stock(
    db: AsyncSession, comp: Comprobante, usuario_id: uuid.UUID, signo: int, tipo_mov: str
) -> None:
    """Descarga (-1) o devuelve (+1) stock por cada ítem con artículo que
    controla stock. Patrón Fase 2: fila lockeada + saldo_resultante sellado."""
    deposito = await _deposito_para_stock(db, comp)
    etiqueta = f"{comp.tipo_codigo} {_fmt_numero(comp.punto_venta.numero, comp.numero)}"
    ids = [i.articulo_id for i in comp.items if i.articulo_id]
    if not ids:
        return
    articulos = {
        a.id: a
        for a in await db.scalars(
            select(Articulo).where(Articulo.id.in_(ids), Articulo.tenant_id == comp.tenant_id)
        )
    }
    # 014: costo sellado (neto de IVA, en ARS) + fecha del documento si el
    # comprobante viene backdateado (si no, el server_default now() conserva
    # el orden intra-día del kardex). El contra-movimiento de ANULACIÓN se
    # fecha HOY (el hecho ocurre hoy), nunca con la fecha del papel.
    cotizacion = Decimal("1")
    if any(a.en_dolares for a in articulos.values()):
        cotizacion = await stock_valor.cotizacion_vigente(db, comp.tenant_id)
    fecha_mov = (
        datetime.combine(comp.fecha, time.min, tzinfo=timezone.utc)
        if comp.fecha != date.today() and tipo_mov != "anulacion"
        else None
    )
    for item in comp.items:
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
                ArticuloStock.tenant_id == comp.tenant_id,
                ArticuloStock.articulo_id == item.articulo_id,
                ArticuloStock.deposito_id == deposito.id,
                filtro_variante,
            )
            .with_for_update()
        )
        if fila is None:
            fila = ArticuloStock(
                tenant_id=comp.tenant_id,
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
        mov = StockMovimiento(
            tenant_id=comp.tenant_id,
            articulo_id=item.articulo_id,
            deposito_id=deposito.id,
            variante_id=item.variante_id,
            tipo=tipo_mov,
            cantidad=delta,
            saldo_resultante=fila.cantidad,
            costo_unitario=stock_valor.costo_neto_ars(art, cotizacion),
            comprobante=etiqueta[:30],
            usuario_id=usuario_id,
            grupo_id=comp.id,
        )
        if fecha_mov is not None:
            mov.fecha = fecha_mov
        db.add(mov)


async def _generar_vencimientos(db: AsyncSession, comp: Comprobante) -> None:
    if comp.contado or comp.condicion_venta_id is None:
        return
    cond = await db.scalar(
        select(CondicionVenta).where(CondicionVenta.id == comp.condicion_venta_id)
    )
    dias = cond.dias if cond and cond.dias else [0]
    n = len(dias)
    cuota = sv.r2(comp.total / n)
    acumulado = Decimal("0")
    for i, d in enumerate(dias, start=1):
        importe = comp.total - acumulado if i == n else cuota  # la última absorbe el redondeo
        acumulado += importe
        db.add(
            ComprobanteVencimiento(
                comprobante_id=comp.id,
                tenant_id=comp.tenant_id,
                nro_cuota=i,
                fecha_vto=comp.fecha + timedelta(days=d),
                importe=importe,
            )
        )


def _validar_para_emitir(comp: Comprobante, config: ArcaConfig | None) -> None:
    if comp.estado != "borrador":
        raise HTTPException(status_code=409, detail="El comprobante ya fue emitido o anulado")
    if not comp.items:
        raise HTTPException(status_code=422, detail="El comprobante no tiene ítems")
    if not comp.tipo.fiscal:
        return
    if comp.letra == "A" and (comp.receptor_doc_tipo != 80 or not comp.receptor_doc_nro):
        raise HTTPException(
            status_code=422, detail="Un comprobante A requiere receptor con CUIT"
        )
    umbral = config.umbral_identificar_cf if config else Decimal("10000000")
    if (
        comp.receptor_condicion_iva == "CF"
        and comp.total >= umbral
        and not comp.receptor_doc_nro
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Operación ≥ ${umbral:,.0f}: identificá al consumidor final "
            "con CUIT/CUIL/DNI (RG 5700/2025)",
        )


async def _validar_pv_nodo(db: AsyncSession, comp: Comprobante) -> None:
    """Exclusividad de PV del nodo LAN (F13-LAN N1 — DISENO-NODO-LAN.md §3):
    mientras una sucursal tenga un nodo ACTIVO, su PV propio y los de sus
    cajas POS emiten SOLO en el nodo (si no, la numeración colisiona).
    En el nodo, la inversa: solo se emite con los PV que le pertenecen."""
    if settings.es_nodo:
        from app.services.sync_nodo import pvs_del_nodo

        pvs = await pvs_del_nodo(db)
        if pvs is None:
            raise HTTPException(
                status_code=422,
                detail="El nodo aún no sincronizó con la nube — sin contexto de aparejamiento",
            )
        if comp.punto_venta_id not in pvs:
            raise HTTPException(
                status_code=422,
                detail="Ese punto de venta no pertenece a este nodo — usá el PV "
                "propio del nodo o el de una caja de la sucursal",
            )
        return
    nodo = await db.scalar(
        select(SucursalNodo)
        .where(
            SucursalNodo.tenant_id == comp.tenant_id,
            SucursalNodo.estado == "activo",
            or_(
                SucursalNodo.punto_venta_id == comp.punto_venta_id,
                SucursalNodo.sucursal_id.in_(
                    select(PosCaja.sucursal_id).where(
                        PosCaja.tenant_id == comp.tenant_id,
                        PosCaja.punto_venta_id == comp.punto_venta_id,
                        PosCaja.activa.is_(True),
                        PosCaja.sucursal_id.is_not(None),
                    )
                ),
            ),
        )
        .limit(1)
    )
    if nodo is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Punto de venta operado por el nodo de sucursal «{nodo.nombre}» "
            "— emití desde el nodo, o revocá el nodo en Configuración",
        )


async def emitir_core(
    db: AsyncSession, comp: Comprobante, usuario: Usuario, config: ArcaConfig | None
) -> None:
    """Núcleo de emisión (sin commit): numeración/CAE + cta. cte. + stock.
    Lo comparten el endpoint /emitir y la venta POS (Fase 6), que lo corre
    dentro de su propia transacción junto con los medios de pago."""
    _validar_para_emitir(comp, config)
    await _validar_pv_nodo(db, comp)
    clase = comp.tipo.clase

    asociado = None
    if comp.comprobante_asociado_id is not None:
        asociado = await _cargar(db, usuario.tenant_id, comp.comprobante_asociado_id)

    numero_local = await sv.proximo_numero(
        db, usuario.tenant_id, comp.punto_venta_id, comp.tipo_codigo
    )

    if comp.tipo.fiscal:
        try:
            resultado = await emitir_fiscal(db, comp, config, numero_local, asociado)
        except ErrorArca as e:
            await db.rollback()
            raise HTTPException(status_code=422, detail=str(e))
        except (ErrorWsaa, ErrorWsfe) as e:
            await db.rollback()
            raise HTTPException(status_code=502, detail=f"Error de comunicación con ARCA: {e}")
        comp.numero = resultado.numero
        comp.cae = resultado.cae
        comp.cae_vencimiento = resultado.cae_vencimiento
        comp.arca_resultado = resultado.resultado
        comp.arca_observaciones = resultado.observaciones or None
        comp.arca_request = resultado.request_xml
        comp.arca_response = resultado.response_xml
        await sv.sincronizar_numero(
            db, usuario.tenant_id, comp.punto_venta_id, comp.tipo_codigo, resultado.numero
        )
    else:
        comp.numero = numero_local

    comp.estado = "emitido"
    comp.emitido_at = datetime.now(timezone.utc)
    comp.emitido_por = usuario.id
    comp.updated_at = func.now()

    # Cuenta corriente
    if clase in ("factura", "nota_debito"):
        comp.saldo = Decimal("0") if comp.contado else comp.total
        await _generar_vencimientos(db, comp)
    elif clase == "nota_credito":
        credito = comp.total
        if asociado is not None and asociado.saldo > 0:
            aplicado = min(credito, asociado.saldo)
            db.add(
                Imputacion(
                    tenant_id=comp.tenant_id,
                    cliente_id=comp.cliente_id,
                    credito_id=comp.id,
                    comprobante_id=asociado.id,
                    importe=aplicado,
                    creado_por=usuario.id,
                )
            )
            asociado.saldo = asociado.saldo - aplicado
            credito -= aplicado
        # si la factura fue contado (ya cobrada), el resto es devolución de
        # dinero en el momento — no queda crédito en cta. cte.
        comp.saldo = Decimal("0") if (asociado is not None and asociado.contado) else credito

    # Stock
    if comp.actualiza_stock:
        if clase in ("factura", "remito"):
            await _mover_stock(db, comp, usuario.id, -1, "venta" if clase == "factura" else "remito")
        elif clase == "nota_credito":
            await _mover_stock(db, comp, usuario.id, +1, "devolucion")


class MedioVentaIn(BaseModel):
    """Medio de cobro de una venta CONTADO de gestión (014): la contrapartida
    financiera del documento (el POS ya registra los suyos por su propio flujo)."""

    medio: str = Field(pattern="^(efectivo|transferencia|cheque|tarjeta|mercadopago|otro)$")
    importe: Decimal = Field(gt=0)
    referencia: str | None = Field(None, max_length=60)
    cuenta_bancaria_id: uuid.UUID | None = None


class EmitirIn(BaseModel):
    medios: list[MedioVentaIn] = []


@router.post("/{comp_id}/emitir", response_model=ComprobanteOut)
async def emitir_comprobante(
    comp_id: uuid.UUID,
    body: EmitirIn | None = None,
    usuario: Usuario = Depends(requiere("ventas", "editar")),
    db: AsyncSession = Depends(get_db),
):
    comp = await _cargar(db, usuario.tenant_id, comp_id)
    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )

    # Medios de cobro (014, opcional): solo contado fiscal; deben sumar el
    # total. Sin medios = comportamiento histórico (planilla los asume efectivo).
    medios = body.medios if body else []
    if medios:
        if not comp.contado or comp.tipo.clase not in CLASES_FISCALES:
            raise HTTPException(
                status_code=422,
                detail="Los medios de cobro son solo para comprobantes contado",
            )
        if sum((m.importe for m in medios), Decimal("0")) != comp.total:
            raise HTTPException(
                status_code=422, detail="Los medios deben sumar el total del comprobante"
            )
        cuentas_ids = {m.cuenta_bancaria_id for m in medios if m.cuenta_bancaria_id}
        if cuentas_ids:
            from app.models import CuentaBancaria

            validas = set(
                await db.scalars(
                    select(CuentaBancaria.id).where(
                        CuentaBancaria.id.in_(cuentas_ids),
                        CuentaBancaria.tenant_id == usuario.tenant_id,
                    )
                )
            )
            if cuentas_ids - validas:
                raise HTTPException(status_code=422, detail="Cuenta bancaria inexistente")

    await emitir_core(db, comp, usuario, config)
    if medios:
        from app.models import VentaMedio

        for m in medios:
            db.add(
                VentaMedio(
                    tenant_id=usuario.tenant_id,
                    comprobante_id=comp.id,
                    medio=m.medio,
                    importe=m.importe,
                    referencia=(m.referencia or "").strip() or None,
                    cuenta_bancaria_id=m.cuenta_bancaria_id,
                )
            )
    await db.commit()
    comp = await _cargar(db, usuario.tenant_id, comp_id)
    return _out(comp)


@router.post("/{comp_id}/anular", response_model=ComprobanteOut)
async def anular_interno(
    comp_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("ventas", "anular")),
    db: AsyncSession = Depends(get_db),
):
    """Anula un documento INTERNO emitido (presupuesto/remito). Los fiscales
    se revierten con nota de crédito — nunca se anulan (FACTURACION-ARCA §6)."""
    comp = await _cargar(db, usuario.tenant_id, comp_id)
    if comp.tipo.fiscal:
        raise HTTPException(
            status_code=409,
            detail="Un comprobante fiscal emitido no se anula: generá la nota de crédito",
        )
    if comp.estado != "emitido":
        raise HTTPException(status_code=409, detail="Solo se anulan documentos emitidos")
    if comp.tipo.clase == "remito" and comp.actualiza_stock:
        await _mover_stock(db, comp, usuario.id, +1, "anulacion")
    comp.estado = "anulado"
    comp.updated_at = func.now()
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, comp_id))


async def crear_nc_espejo_core(
    db: AsyncSession, factura: Comprobante, usuario: Usuario
) -> Comprobante:
    """Arma la NC borrador espejo de una factura emitida (reversión total).
    Sin commit: la comparten el endpoint /nota-credito y la anulación POS."""
    if factura.tipo.clase != "factura" or factura.estado != "emitido":
        raise HTTPException(status_code=409, detail="Solo se revierte una factura emitida")
    nc = Comprobante(
        tenant_id=factura.tenant_id,
        punto_venta_id=factura.punto_venta_id,
        tipo_codigo=sv.tipo_codigo_para("nota_credito", factura.letra),
        letra=factura.letra,
        fecha=date.today(),
        cliente_id=factura.cliente_id,
        receptor_nombre=factura.receptor_nombre,
        receptor_doc_tipo=factura.receptor_doc_tipo,
        receptor_doc_nro=factura.receptor_doc_nro,
        receptor_condicion_iva=factura.receptor_condicion_iva,
        receptor_domicilio=factura.receptor_domicilio,
        contado=factura.contado,
        lista_precios=factura.lista_precios,
        deposito_id=factura.deposito_id,
        actualiza_stock=factura.actualiza_stock,
        moneda=factura.moneda,
        cotizacion=factura.cotizacion,
        descuento_pct=factura.descuento_pct,
        neto_gravado=factura.neto_gravado,
        neto_no_gravado=factura.neto_no_gravado,
        exento=factura.exento,
        iva=factura.iva,
        total=factura.total,
        iva_contenido=factura.iva_contenido,
        otros_imp_indirectos=factura.otros_imp_indirectos,
        comprobante_asociado_id=factura.id,
        # F11: la NC espejo hereda el vendedor — la anulación resta comisión
        vendedor_id=factura.vendedor_id,
        observaciones=f"Reversión de {factura.tipo_codigo} "
        f"{_fmt_numero(factura.punto_venta.numero, factura.numero)}",
        creado_por=usuario.id,
    )
    db.add(nc)
    await db.flush()
    for item in factura.items:
        db.add(
            ComprobanteItem(
                comprobante_id=nc.id,
                tenant_id=nc.tenant_id,
                orden=item.orden,
                articulo_id=item.articulo_id,
                variante_id=item.variante_id,
                codigo=item.codigo,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                bonif_pct=item.bonif_pct,
                tasa_iva=item.tasa_iva,
                importe_neto=item.importe_neto,
                importe_iva=item.importe_iva,
                importe_total=item.importe_total,
                costo_unitario=item.costo_unitario,
            )
        )
    for al in factura.alicuotas:
        db.add(
            ComprobanteAlicuota(
                comprobante_id=nc.id,
                tenant_id=nc.tenant_id,
                tasa=al.tasa,
                codigo_arca=al.codigo_arca,
                base=al.base,
                importe=al.importe,
            )
        )
    return nc


@router.post("/{comp_id}/nota-credito", response_model=ComprobanteOut)
async def crear_nc_espejo(
    comp_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("ventas", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Crea la NC borrador espejo de una factura emitida (reversión total)."""
    factura = await _cargar(db, usuario.tenant_id, comp_id)
    nc = await crear_nc_espejo_core(db, factura, usuario)
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, nc.id))


@router.post("/{comp_id}/facturar", response_model=ComprobanteOut)
async def facturar_presupuesto(
    comp_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("ventas", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Convierte un presupuesto emitido en factura BORRADOR (letra y totales
    recalculados con la condición IVA actual del cliente)."""
    pre = await _cargar(db, usuario.tenant_id, comp_id)
    if pre.tipo.clase != "presupuesto" or pre.estado != "emitido":
        raise HTTPException(status_code=409, detail="Solo se factura un presupuesto emitido")
    tenant = await db.scalar(select(Tenant).where(Tenant.id == usuario.tenant_id))
    receptor = await _snapshot_receptor(db, usuario.tenant_id, pre.cliente_id)
    letra = sv.letra_comprobante(tenant.condicion_iva, receptor["receptor_condicion_iva"])
    items = [
        {
            "articulo_id": i.articulo_id,
            "variante_id": i.variante_id,
            "codigo": i.codigo,
            "descripcion": i.descripcion,
            "cantidad": i.cantidad,
            "precio_unitario": i.precio_unitario,
            "bonif_pct": i.bonif_pct,
            "tasa_iva": i.tasa_iva,
            "costo_unitario": i.costo_unitario,
        }
        for i in pre.items
    ]
    calculo = sv.calcular_comprobante(items, letra, pre.descuento_pct, False)
    factura = Comprobante(
        tenant_id=pre.tenant_id,
        punto_venta_id=pre.punto_venta_id,
        tipo_codigo=sv.tipo_codigo_para("factura", letra),
        letra=letra,
        fecha=date.today(),
        contado=pre.contado,
        condicion_venta_id=pre.condicion_venta_id,
        condicion_venta_desc=pre.condicion_venta_desc,
        lista_precios=pre.lista_precios,
        deposito_id=pre.deposito_id,
        actualiza_stock=True,
        moneda=pre.moneda,
        descuento_pct=pre.descuento_pct,
        origen_id=pre.id,
        creado_por=usuario.id,
        **receptor,
    )
    db.add(factura)
    await db.flush()
    await _aplicar_calculo(db, factura, calculo)
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, factura.id))


# ===== Impresión =====

@router.get("/{comp_id}/impresion")
async def datos_impresion(
    comp_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("ventas", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Payload completo para el HTML imprimible (FACTURACION-ARCA.md §7):
    emisor, receptor, ítems, alícuotas, CAE, QR (solo CAE real) y leyendas."""
    comp = await _cargar(db, usuario.tenant_id, comp_id)
    if comp.estado == "borrador":
        raise HTTPException(status_code=409, detail="Un borrador no se imprime")
    tenant = await db.scalar(select(Tenant).where(Tenant.id == usuario.tenant_id))
    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )

    es_simulado = comp.arca_resultado == "S"
    qr_svg = None
    if comp.tipo.fiscal and comp.cae and not es_simulado:
        cuit_emisor = (config.cuit if config else None) or tenant.cuit or "0"
        url = arca_qr.url_qr(
            fecha=comp.fecha,
            cuit_emisor=cuit_emisor,
            punto_venta=comp.punto_venta.numero,
            tipo_arca=comp.tipo.codigo_arca,
            numero=comp.numero,
            importe=comp.total,
            moneda=comp.moneda,
            cotizacion=comp.cotizacion,
            doc_tipo=comp.receptor_doc_tipo,
            doc_nro=comp.receptor_doc_nro,
            cae=comp.cae,
        )
        qr_svg = arca_qr.svg_qr(url)

    leyendas = []
    if not comp.tipo.fiscal:
        leyendas.append("DOCUMENTO NO VÁLIDO COMO FACTURA")
    if es_simulado:
        leyendas.append("COMPROBANTE NO VÁLIDO — PRUEBA (MODO SIMULADO)")
    transparencia = None
    if comp.tipo.fiscal and comp.letra != "A" and comp.receptor_condicion_iva == "CF":
        transparencia = {
            "titulo": "Régimen de Transparencia Fiscal al Consumidor (Ley 27.743)",
            "iva_contenido": str(comp.iva_contenido or 0),
            "otros_impuestos_nacionales_indirectos": str(comp.otros_imp_indirectos or 0),
        }

    condiciones_iva = {"RI": "IVA Responsable Inscripto", "MT": "Responsable Monotributo",
                       "EX": "IVA Exento", "CF": "Consumidor Final"}
    return {
        "comprobante": _out(comp).model_dump(mode="json"),
        "emisor": {
            "razon_social": (config.razon_social if config else None) or tenant.razon_social,
            "nombre_fantasia": tenant.nombre_fantasia,
            "cuit": (config.cuit if config else None) or tenant.cuit,
            "condicion_iva": condiciones_iva.get(tenant.condicion_iva, tenant.condicion_iva),
            "domicilio": ", ".join(
                p for p in (tenant.domicilio, tenant.localidad, tenant.provincia) if p
            ),
            "iibb": config.iibb if config else None,
            "inicio_actividades": (
                config.inicio_actividades.isoformat()
                if config and config.inicio_actividades
                else None
            ),
        },
        "receptor_condicion_iva_desc": condiciones_iva.get(
            comp.receptor_condicion_iva, comp.receptor_condicion_iva
        ),
        "codigo_arca": comp.tipo.codigo_arca,
        "discrimina_iva": comp.letra == "A",
        "leyendas": leyendas,
        "transparencia_fiscal": transparencia,
        "qr_svg": qr_svg,
    }
