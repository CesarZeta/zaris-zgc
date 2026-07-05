"""Libros de IVA y retenciones (Fase 5).

Los libros NO tienen tabla propia: se computan de comprobantes (ventas,
estado=emitido, tipo fiscal) y compras (estado=registrado, tipo fiscal).
Convenciones:
- Ventas: período = mes de la fecha de emisión. Compras: `periodo_iva`
  sellado al registrar (fallback: mes de la fecha).
- Las NC van con importes NEGATIVOS en el libro (los totales son suma
  directa); en el CITI van positivas (el tipo de comprobante ya las define).
- Compras B/C: el IVA no es computable — en el libro van con neto gravado y
  crédito fiscal 0 y el importe en "no gravado" (el modelo guarda el importe
  final en neto_gravado, ver services/compras.py).
- Export CSV para el contador: separador ';', decimales con coma, UTF-8 BOM
  (Excel es-AR lo abre directo).
- Export CITI (RG 3685 / libro IVA digital): 4 TXT de ancho fijo en un ZIP
  (ventas cbte 266, ventas alícuotas 62, compras cbte 325, compras alícuotas
  84). Best-effort documentado: el contador lo valida antes de presentar.
"""

import io
import uuid
import zipfile
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import (
    Cliente,
    Compra,
    CompraItem,
    Comprobante,
    Entidad,
    OrdenPago,
    Proveedor,
    Recibo,
    Retencion,
    Usuario,
)

router = APIRouter(prefix="/libros", tags=["libros"])

# tasa -> código de alícuota ARCA (tabla RG 3685)
CODIGO_ALICUOTA = {
    Decimal("0"): 3,
    Decimal("2.5"): 9,
    Decimal("5"): 8,
    Decimal("10.5"): 4,
    Decimal("21"): 5,
    Decimal("27"): 6,
}


def _periodo_rango(periodo: str) -> tuple[date, date]:
    """'YYYY-MM' -> (primer día, primer día del mes siguiente)."""
    try:
        anio, mes = periodo.split("-")
        desde = date(int(anio), int(mes), 1)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="Período inválido: usar YYYY-MM")
    hasta = date(desde.year + (desde.month == 12), desde.month % 12 + 1, 1)
    return desde, hasta


# ---------------------------------------------------------------- schemas
class AlicuotaLibro(BaseModel):
    tasa: Decimal
    base: Decimal
    importe: Decimal


class FilaLibro(BaseModel):
    id: uuid.UUID
    fecha: date
    tipo_codigo: str
    tipo_descripcion: str
    letra: str
    punto_venta: int
    numero: int
    contraparte: str  # cliente o proveedor (snapshot)
    doc_nro: str | None
    condicion_iva: str
    neto_gravado: Decimal
    no_gravado: Decimal
    exento: Decimal
    iva: Decimal
    percepciones: Decimal
    otros: Decimal
    total: Decimal
    alicuotas: list[AlicuotaLibro]


class TotalesLibro(BaseModel):
    neto_gravado: Decimal
    no_gravado: Decimal
    exento: Decimal
    iva: Decimal
    percepciones: Decimal
    otros: Decimal
    total: Decimal
    por_alicuota: list[AlicuotaLibro]


class LibroOut(BaseModel):
    periodo: str
    filas: list[FilaLibro]
    totales: TotalesLibro


class RetencionIn(BaseModel):
    tipo: str = Field(pattern="^(sufrida|practicada)$")
    regimen: str = Field(pattern="^(IVA|IIBB|Ganancias|SUSS|otro)$")
    fecha: date | None = None
    importe: Decimal = Field(gt=0)
    nro_certificado: str | None = Field(None, max_length=30)
    cliente_id: uuid.UUID | None = None
    proveedor_id: uuid.UUID | None = None
    recibo_id: uuid.UUID | None = None
    orden_pago_id: uuid.UUID | None = None
    descripcion: str | None = Field(None, max_length=120)


class RetencionOut(BaseModel):
    id: uuid.UUID
    tipo: str
    regimen: str
    fecha: date
    importe: Decimal
    nro_certificado: str | None
    cliente_id: uuid.UUID | None
    proveedor_id: uuid.UUID | None
    contraparte: str | None
    descripcion: str | None


class ResumenRetenciones(BaseModel):
    tipo: str
    regimen: str
    cantidad: int
    total: Decimal


# ---------------------------------------------------------------- libros (queries)
def _totalizar(filas: list[FilaLibro]) -> TotalesLibro:
    por_tasa: dict[Decimal, AlicuotaLibro] = {}
    tot = dict.fromkeys(
        ("neto_gravado", "no_gravado", "exento", "iva", "percepciones", "otros", "total"),
        Decimal("0"),
    )
    for f in filas:
        for k in tot:
            tot[k] += getattr(f, k)
        for a in f.alicuotas:
            acc = por_tasa.setdefault(a.tasa, AlicuotaLibro(tasa=a.tasa, base=Decimal("0"), importe=Decimal("0")))
            acc.base += a.base
            acc.importe += a.importe
    return TotalesLibro(**tot, por_alicuota=sorted(por_tasa.values(), key=lambda a: a.tasa))


async def _libro_ventas(db: AsyncSession, tenant_id: uuid.UUID, periodo: str) -> LibroOut:
    desde, hasta = _periodo_rango(periodo)
    comps = (
        await db.scalars(
            select(Comprobante)
            .where(
                Comprobante.tenant_id == tenant_id,
                Comprobante.estado == "emitido",
                Comprobante.fecha >= desde,
                Comprobante.fecha < hasta,
            )
            .order_by(Comprobante.fecha, Comprobante.numero)
        )
    ).all()
    filas = []
    for c in comps:
        if not c.tipo.fiscal:
            continue
        signo = c.tipo.signo_cta_cte  # FA/ND +1, NC -1: las NC restan en el libro
        filas.append(
            FilaLibro(
                id=c.id,
                fecha=c.fecha,
                tipo_codigo=c.tipo_codigo,
                tipo_descripcion=c.tipo.descripcion,
                letra=c.letra,
                punto_venta=c.punto_venta.numero,
                numero=c.numero or 0,
                contraparte=c.receptor_nombre,
                doc_nro=c.receptor_doc_nro,
                condicion_iva=c.receptor_condicion_iva,
                neto_gravado=c.neto_gravado * signo,
                no_gravado=c.neto_no_gravado * signo,
                exento=c.exento * signo,
                iva=c.iva * signo,
                percepciones=Decimal("0"),
                otros=c.otros_tributos * signo,
                total=c.total * signo,
                alicuotas=[
                    AlicuotaLibro(tasa=a.tasa, base=a.base * signo, importe=a.importe * signo)
                    for a in c.alicuotas
                ],
            )
        )
    return LibroOut(periodo=periodo, filas=filas, totales=_totalizar(filas))


async def _libro_compras(db: AsyncSession, tenant_id: uuid.UUID, periodo: str) -> LibroOut:
    desde, hasta = _periodo_rango(periodo)
    # período: periodo_iva sellado; fallback mes de la fecha (compras viejas)
    compras = (
        await db.scalars(
            select(Compra)
            .where(
                Compra.tenant_id == tenant_id,
                Compra.estado == "registrado",
                (Compra.periodo_iva == desde)
                | (Compra.periodo_iva.is_(None) & (Compra.fecha >= desde) & (Compra.fecha < hasta)),
            )
            .order_by(Compra.fecha, Compra.numero)
        )
    ).all()
    ids = [c.id for c in compras]
    items_por_compra: dict[uuid.UUID, list[CompraItem]] = {}
    if ids:
        for it in (
            await db.scalars(select(CompraItem).where(CompraItem.compra_id.in_(ids)))
        ).all():
            items_por_compra.setdefault(it.compra_id, []).append(it)

    filas = []
    for c in compras:
        if not c.tipo.fiscal:
            continue
        signo = c.tipo.signo_cta_cte  # FC/ND +1, NC -1
        percepciones = c.percepcion_iva + c.percepcion_iibb
        otros = c.impuestos_internos + c.otros_tributos + c.redondeo
        if c.letra == "A":
            neto, iva, no_gravado = c.neto_gravado, c.iva, c.no_gravado
            por_tasa: dict[Decimal, AlicuotaLibro] = {}
            for it in items_por_compra.get(c.id, []):
                acc = por_tasa.setdefault(
                    it.tasa_iva, AlicuotaLibro(tasa=it.tasa_iva, base=Decimal("0"), importe=Decimal("0"))
                )
                acc.base += it.importe_neto * signo
                acc.importe += it.importe_iva * signo
            alicuotas = sorted(por_tasa.values(), key=lambda a: a.tasa)
        else:
            # B/C: IVA al costo, sin crédito fiscal; el "neto" del modelo es
            # el importe final -> va como no gravado en el libro
            neto, iva = Decimal("0"), Decimal("0")
            no_gravado = c.neto_gravado + c.no_gravado
            alicuotas = []
        filas.append(
            FilaLibro(
                id=c.id,
                fecha=c.fecha,
                tipo_codigo=c.tipo_codigo,
                tipo_descripcion=c.tipo.descripcion,
                letra=c.letra,
                punto_venta=c.punto_venta,
                numero=c.numero,
                contraparte=c.proveedor_nombre,
                doc_nro=c.proveedor_cuit,
                condicion_iva=c.proveedor_condicion_iva,
                neto_gravado=neto * signo,
                no_gravado=no_gravado * signo,
                exento=c.exento * signo,
                iva=iva * signo,
                percepciones=percepciones * signo,
                otros=otros * signo,
                total=c.total * signo,
                alicuotas=alicuotas,
            )
        )
    return LibroOut(periodo=periodo, filas=filas, totales=_totalizar(filas))


@router.get("/iva-ventas", response_model=LibroOut)
async def libro_iva_ventas(
    periodo: str,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _libro_ventas(db, usuario.tenant_id, periodo)


@router.get("/iva-compras", response_model=LibroOut)
async def libro_iva_compras(
    periodo: str,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _libro_compras(db, usuario.tenant_id, periodo)


# ---------------------------------------------------------------- CSV
def _n(valor: Decimal) -> str:
    """Decimal -> string con coma decimal (Excel es-AR)."""
    return f"{valor:.2f}".replace(".", ",")


def _csv_response(nombre: str, encabezado: list[str], filas: list[list[str]]) -> Response:
    lineas = [";".join(encabezado)] + [";".join(f) for f in filas]
    contenido = "﻿" + "\r\n".join(lineas) + "\r\n"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


_COLS_LIBRO = [
    "Fecha", "Tipo", "Letra", "PV", "Número", "Razón social", "CUIT/Doc",
    "Cond. IVA", "Neto gravado", "No gravado", "Exento", "IVA",
    "Percepciones", "Otros", "Total",
]


def _libro_a_csv(libro: LibroOut, nombre: str) -> Response:
    filas = [
        [
            f.fecha.strftime("%d/%m/%Y"),
            f.tipo_descripcion,
            f.letra,
            f"{f.punto_venta:05d}",
            f"{f.numero:08d}",
            f.contraparte,
            f.doc_nro or "",
            f.condicion_iva,
            _n(f.neto_gravado),
            _n(f.no_gravado),
            _n(f.exento),
            _n(f.iva),
            _n(f.percepciones),
            _n(f.otros),
            _n(f.total),
        ]
        for f in libro.filas
    ]
    t = libro.totales
    filas.append(
        ["", "", "", "", "", "TOTALES", "", "", _n(t.neto_gravado), _n(t.no_gravado),
         _n(t.exento), _n(t.iva), _n(t.percepciones), _n(t.otros), _n(t.total)]
    )
    return _csv_response(nombre, _COLS_LIBRO, filas)


@router.get("/iva-ventas.csv")
async def libro_iva_ventas_csv(
    periodo: str,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    libro = await _libro_ventas(db, usuario.tenant_id, periodo)
    return _libro_a_csv(libro, f"libro-iva-ventas-{periodo}.csv")


@router.get("/iva-compras.csv")
async def libro_iva_compras_csv(
    periodo: str,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    libro = await _libro_compras(db, usuario.tenant_id, periodo)
    return _libro_a_csv(libro, f"libro-iva-compras-{periodo}.csv")


# ---------------------------------------------------------------- CITI (RG 3685)
def _imp(valor: Decimal, ancho: int = 15) -> str:
    """Importe CITI: entero de `ancho`, últimos 2 dígitos decimales, sin signo."""
    centavos = int((abs(valor) * 100).quantize(Decimal("1")))
    return str(centavos).rjust(ancho, "0")


def _txt(valor: str | None, ancho: int) -> str:
    s = (valor or "").ljust(ancho)[:ancho]
    return s.encode("ascii", "replace").decode("ascii")


def _citi_ventas(comps: list[Comprobante]) -> tuple[str, str]:
    cbtes, alics = [], []
    for c in comps:
        alicuotas = [a for a in c.alicuotas]
        tipo = f"{c.tipo.codigo_arca or 0:03d}"
        pv = f"{c.punto_venta.numero:05d}"
        nro = f"{c.numero or 0:020d}"
        doc_tipo = f"{c.receptor_doc_tipo:02d}"
        doc_nro = (c.receptor_doc_nro or "0").rjust(20, "0")
        vto = (c.vencimientos[0].fecha_vto if c.vencimientos else c.fecha).strftime("%Y%m%d")
        if alicuotas:
            cod_op = " "
        elif c.exento > 0:
            cod_op = "E"
        else:
            cod_op = "N"
        cant = len(alicuotas) if alicuotas else 1
        cbtes.append(
            c.fecha.strftime("%Y%m%d")
            + tipo + pv + nro + nro  # número hasta = mismo comprobante
            + doc_tipo + doc_nro
            + _txt(c.receptor_nombre, 30)
            + _imp(c.total)
            + _imp(c.neto_no_gravado)
            + _imp(Decimal("0"))  # percepción a no categorizados
            + _imp(c.exento)
            + _imp(Decimal("0"))  # percepciones nacionales
            + _imp(Decimal("0"))  # percepciones IIBB
            + _imp(Decimal("0"))  # percepciones municipales
            + _imp(Decimal("0"))  # impuestos internos
            + _txt(c.moneda or "PES", 3)
            + str(int((c.cotizacion or Decimal("1")) * 10**6)).rjust(10, "0")
            + str(cant)
            + cod_op
            + _imp(c.otros_tributos)
            + vto
        )
        if alicuotas:
            for a in alicuotas:
                alics.append(tipo + pv + nro + _imp(a.base) + f"{a.codigo_arca:04d}" + _imp(a.importe))
        else:
            alics.append(tipo + pv + nro + _imp(Decimal("0")) + "0003" + _imp(Decimal("0")))
    return "\r\n".join(cbtes), "\r\n".join(alics)


def _citi_compras(
    compras: list[Compra], items_por_compra: dict[uuid.UUID, list[CompraItem]]
) -> tuple[str, str]:
    cbtes, alics = [], []
    for c in compras:
        tipo = f"{c.tipo.codigo_arca or 0:03d}"
        pv = f"{c.punto_venta:05d}"
        nro = f"{c.numero:020d}"
        doc_tipo = "80" if c.proveedor_cuit else "99"
        doc_nro = (c.proveedor_cuit or "0").rjust(20, "0")
        # alícuotas solo para letra A (crédito fiscal); B/C: 1 registro en 0%
        por_tasa: dict[Decimal, list[Decimal]] = {}
        if c.letra == "A":
            for it in items_por_compra.get(c.id, []):
                acc = por_tasa.setdefault(it.tasa_iva, [Decimal("0"), Decimal("0")])
                acc[0] += it.importe_neto
                acc[1] += it.importe_iva
        credito_fiscal = c.iva if c.letra == "A" else Decimal("0")
        no_neto = c.no_gravado if c.letra == "A" else c.neto_gravado + c.no_gravado
        cant = len(por_tasa) if por_tasa else 1
        cbtes.append(
            c.fecha.strftime("%Y%m%d")
            + tipo + pv + nro
            + _txt("", 16)  # despacho de importación (diferido)
            + doc_tipo + doc_nro
            + _txt(c.proveedor_nombre, 30)
            + _imp(c.total)
            + _imp(no_neto)
            + _imp(c.exento)
            + _imp(c.percepcion_iva)
            + _imp(Decimal("0"))  # percepciones otros impuestos nacionales
            + _imp(c.percepcion_iibb)
            + _imp(Decimal("0"))  # percepciones municipales
            + _imp(c.impuestos_internos)
            + "PES"
            + "0001000000"  # tipo de cambio 1.000000
            + str(cant)
            + (" " if por_tasa else ("E" if c.exento > 0 else "N"))
            + _imp(credito_fiscal)
            + _imp(c.otros_tributos + c.redondeo)
            + "0" * 11  # CUIT corredor
            + _txt("", 30)  # denominación corredor
            + _imp(Decimal("0"))  # IVA comisión
        )
        if por_tasa:
            for tasa, (base, importe) in sorted(por_tasa.items()):
                cod = CODIGO_ALICUOTA.get(tasa, 5)
                alics.append(tipo + pv + nro + doc_tipo + doc_nro + _imp(base) + f"{cod:04d}" + _imp(importe))
        else:
            alics.append(tipo + pv + nro + doc_tipo + doc_nro + _imp(Decimal("0")) + "0003" + _imp(Decimal("0")))
    return "\r\n".join(cbtes), "\r\n".join(alics)


@router.get("/citi")
async def export_citi(
    periodo: str,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    desde, hasta = _periodo_rango(periodo)
    comps = [
        c
        for c in (
            await db.scalars(
                select(Comprobante)
                .where(
                    Comprobante.tenant_id == usuario.tenant_id,
                    Comprobante.estado == "emitido",
                    Comprobante.fecha >= desde,
                    Comprobante.fecha < hasta,
                )
                .order_by(Comprobante.fecha, Comprobante.numero)
            )
        ).all()
        if c.tipo.fiscal
    ]
    compras = [
        c
        for c in (
            await db.scalars(
                select(Compra)
                .where(
                    Compra.tenant_id == usuario.tenant_id,
                    Compra.estado == "registrado",
                    (Compra.periodo_iva == desde)
                    | (Compra.periodo_iva.is_(None) & (Compra.fecha >= desde) & (Compra.fecha < hasta)),
                )
                .order_by(Compra.fecha, Compra.numero)
            )
        ).all()
        if c.tipo.fiscal
    ]
    items_por_compra: dict[uuid.UUID, list[CompraItem]] = {}
    if compras:
        for it in (
            await db.scalars(
                select(CompraItem).where(CompraItem.compra_id.in_([c.id for c in compras]))
            )
        ).all():
            items_por_compra.setdefault(it.compra_id, []).append(it)

    v_cbte, v_alic = _citi_ventas(comps)
    c_cbte, c_alic = _citi_compras(compras, items_por_compra)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("REGINFO_CV_VENTAS_CBTE.txt", v_cbte)
        zf.writestr("REGINFO_CV_VENTAS_ALICUOTAS.txt", v_alic)
        zf.writestr("REGINFO_CV_COMPRAS_CBTE.txt", c_cbte)
        zf.writestr("REGINFO_CV_COMPRAS_ALICUOTAS.txt", c_alic)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="citi-{periodo}.zip"'},
    )


# ---------------------------------------------------------------- retenciones
async def _ret_out(db: AsyncSession, r: Retencion) -> RetencionOut:
    contraparte = None
    if r.cliente_id:
        contraparte = await db.scalar(
            select(Entidad.razon_social).join(Cliente, Cliente.entidad_id == Entidad.id).where(Cliente.id == r.cliente_id)
        )
    elif r.proveedor_id:
        contraparte = await db.scalar(
            select(Entidad.razon_social).join(Proveedor, Proveedor.entidad_id == Entidad.id).where(Proveedor.id == r.proveedor_id)
        )
    return RetencionOut(
        id=r.id,
        tipo=r.tipo,
        regimen=r.regimen,
        fecha=r.fecha,
        importe=r.importe,
        nro_certificado=r.nro_certificado,
        cliente_id=r.cliente_id,
        proveedor_id=r.proveedor_id,
        contraparte=contraparte,
        descripcion=r.descripcion,
    )


@router.get("/retenciones", response_model=list[RetencionOut])
async def listar_retenciones(
    desde: date | None = None,
    hasta: date | None = None,
    tipo: str | None = None,
    limit: int = 100,
    offset: int = 0,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Retencion).where(Retencion.tenant_id == usuario.tenant_id)
    if desde:
        stmt = stmt.where(Retencion.fecha >= desde)
    if hasta:
        stmt = stmt.where(Retencion.fecha <= hasta)
    if tipo:
        stmt = stmt.where(Retencion.tipo == tipo)
    stmt = stmt.order_by(Retencion.fecha.desc(), Retencion.created_at.desc())
    filas = (await db.scalars(stmt.limit(min(limit, 500)).offset(offset))).all()
    return [await _ret_out(db, r) for r in filas]


@router.post("/retenciones", response_model=RetencionOut, status_code=status.HTTP_201_CREATED)
async def crear_retencion(
    body: RetencionIn,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.tipo == "sufrida" and (body.proveedor_id or body.orden_pago_id):
        raise HTTPException(status_code=422, detail="Una retención sufrida es de un cliente/recibo")
    if body.tipo == "practicada" and (body.cliente_id or body.recibo_id):
        raise HTTPException(status_code=422, detail="Una retención practicada es de un proveedor/OP")
    # referencias del propio tenant (las FK no cruzan tenants por sí solas)
    for modelo, valor in ((Cliente, body.cliente_id), (Proveedor, body.proveedor_id),
                          (Recibo, body.recibo_id), (OrdenPago, body.orden_pago_id)):
        if valor is not None:
            fila = await db.scalar(
                select(modelo.id).where(modelo.id == valor, modelo.tenant_id == usuario.tenant_id)
            )
            if fila is None:
                raise HTTPException(status_code=422, detail="Referencia inexistente en este tenant")

    retencion = Retencion(
        tenant_id=usuario.tenant_id,
        tipo=body.tipo,
        regimen=body.regimen,
        fecha=body.fecha or date.today(),
        importe=body.importe,
        nro_certificado=body.nro_certificado,
        cliente_id=body.cliente_id,
        proveedor_id=body.proveedor_id,
        recibo_id=body.recibo_id,
        orden_pago_id=body.orden_pago_id,
        descripcion=body.descripcion,
        creado_por=usuario.id,
    )
    db.add(retencion)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=422, detail="Datos de retención inválidos")
    await db.refresh(retencion)
    return await _ret_out(db, retencion)


@router.delete("/retenciones/{retencion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_retencion(
    retencion_id: uuid.UUID,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    retencion = await db.scalar(
        select(Retencion).where(
            Retencion.id == retencion_id, Retencion.tenant_id == usuario.tenant_id
        )
    )
    if retencion is None:
        raise HTTPException(status_code=404, detail="Retención no encontrada")
    await db.delete(retencion)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/retenciones/resumen", response_model=list[ResumenRetenciones])
async def resumen_retenciones(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    stmt = (
        select(Retencion.tipo, Retencion.regimen, sqlfunc.count(), sqlfunc.sum(Retencion.importe))
        .where(Retencion.tenant_id == usuario.tenant_id)
        .group_by(Retencion.tipo, Retencion.regimen)
        .order_by(Retencion.tipo, Retencion.regimen)
    )
    if desde:
        stmt = stmt.where(Retencion.fecha >= desde)
    if hasta:
        stmt = stmt.where(Retencion.fecha <= hasta)
    return [
        ResumenRetenciones(tipo=t, regimen=r, cantidad=c, total=s)
        for t, r, c, s in (await db.execute(stmt)).all()
    ]


@router.get("/retenciones.csv")
async def retenciones_csv(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filas_db = await listar_retenciones(
        desde=desde, hasta=hasta, tipo=None, limit=500, offset=0, usuario=usuario, db=db
    )
    filas = [
        [
            r.fecha.strftime("%d/%m/%Y"),
            r.tipo,
            r.regimen,
            r.contraparte or "",
            r.nro_certificado or "",
            _n(r.importe),
            r.descripcion or "",
        ]
        for r in filas_db
    ]
    encabezado = ["Fecha", "Tipo", "Régimen", "Contraparte", "Certificado", "Importe", "Descripción"]
    return _csv_response("retenciones.csv", encabezado, filas)
