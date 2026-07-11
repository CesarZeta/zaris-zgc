"""Contabilidad (Fase 9) — plan de cuentas, mapeos, motor derivado y reportes.

Diseño en docs/DISENO-CONTABILIDAD.md: los asientos se DERIVAN de los documentos
operativos (POST /regenerar, motor en services/contabilidad.py) y son
regenerables por período mientras el período no esté cerrado. Los asientos
manuales se cargan sueltos y se anulan MARCANDO (contrato 014). El diario, el
mayor y sumas y saldos son consultas sobre asientos vivos.

Rutas estáticas ANTES de las paramétricas (regla §6 del CLAUDE.md).
RBAC `contabilidad`: GET=ver, regenerar/mapeos/manual=editar, anular/cierre=anular.
"""

import io
import uuid
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.bancos import SIGNO_MOV as SIGNO_BANCO
from app.api.v1.dashboard import _cobros_pendientes, _stock_valorizado
from app.core.csv_export import csv_response, csv_texto, num
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    ActivoCategoria,
    ActivoFijo,
    Asiento,
    AsientoLinea,
    AsientoMapeo,
    BancoMovimiento,
    Cheque,
    Compra,
    ContabPeriodo,
    CuentaBancaria,
    PlanCuenta,
    TipoComprobanteCompra,
    Usuario,
)
from app.services import contabilidad as sc

router = APIRouter(prefix="/contabilidad", tags=["contabilidad"])

D0 = Decimal("0")


# ===== Schemas =====

class CuentaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=15)
    nombre: str = Field(min_length=2, max_length=80)
    tipo: str = Field(pattern="^(activo|pasivo|pn|r_positivo|r_negativo)$")
    imputable: bool = True
    padre_id: uuid.UUID | None = None


class CuentaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=80)
    activa: bool | None = None


class CuentaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    tipo: str
    imputable: bool
    padre_id: uuid.UUID | None
    es_sistema: bool
    activa: bool
    model_config = {"from_attributes": True}


class MapeoIn(BaseModel):
    origen: str
    clave: str | None = Field(None, max_length=40)
    cuenta_id: uuid.UUID


class MapeoOut(BaseModel):
    id: uuid.UUID
    origen: str
    clave: str | None
    cuenta_id: uuid.UUID
    model_config = {"from_attributes": True}


class RegenerarIn(BaseModel):
    desde: date
    hasta: date


class LineaIn(BaseModel):
    cuenta_id: uuid.UUID
    debe: Decimal = Field(D0, ge=0)
    haber: Decimal = Field(D0, ge=0)
    detalle: str | None = Field(None, max_length=120)


class AsientoManualIn(BaseModel):
    fecha: date
    descripcion: str = Field(min_length=3, max_length=200)
    lineas: list[LineaIn] = Field(min_length=2)


class LineaOut(BaseModel):
    cuenta_id: uuid.UUID
    cuenta_codigo: str = ""
    cuenta_nombre: str = ""
    debe: Decimal
    haber: Decimal
    detalle: str | None


class AsientoOut(BaseModel):
    id: uuid.UUID
    numero: int | None
    fecha: date
    descripcion: str | None
    origen_tipo: str
    anulado: bool = False
    total: Decimal = D0
    lineas: list[LineaOut] = []


class CerrarPeriodoIn(BaseModel):
    periodo: date  # cualquier día del mes


class CategoriaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    vida_util_meses: int = Field(60, gt=0, le=1200)


class CategoriaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    vida_util_meses: int
    es_sistema: bool
    activa: bool
    model_config = {"from_attributes": True}


class ActivoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    categoria_id: uuid.UUID
    fecha_alta: date
    inicio_amortizacion: date | None = None  # default: 1° del mes de alta
    valor_origen: Decimal = Field(gt=0)
    valor_residual: Decimal = Field(D0, ge=0)
    vida_util_meses: int = Field(gt=0, le=1200)
    compra_id: uuid.UUID | None = None
    observaciones: str | None = Field(None, max_length=200)


class ActivoBajaIn(BaseModel):
    fecha_baja: date
    baja_motivo: str | None = Field(None, max_length=120)


class ActivoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    categoria_id: uuid.UUID
    categoria_nombre: str = ""
    fecha_alta: date
    inicio_amortizacion: date
    valor_origen: Decimal
    valor_residual: Decimal
    vida_util_meses: int
    compra_id: uuid.UUID | None
    fecha_baja: date | None
    baja_motivo: str | None
    observaciones: str | None
    anulado: bool = False
    # calculados al corte (cuadro de bienes de uso)
    amort_acumulada: Decimal = D0
    valor_contable: Decimal = D0
    model_config = {"from_attributes": True}


class AperturaIn(BaseModel):
    fecha: date
    descripcion: str = Field("Asiento de apertura", min_length=3, max_length=200)
    lineas: list[LineaIn] = Field(min_length=2)


# ===== Helpers =====

async def _cuentas_por_id(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    filas = (
        await db.scalars(select(PlanCuenta).where(PlanCuenta.tenant_id == tenant_id))
    ).all()
    return {c.id: c for c in filas}


def _asiento_out(a: Asiento, cuentas: dict) -> AsientoOut:
    lineas = []
    total = D0
    for ln in a.lineas:
        c = cuentas.get(ln.cuenta_id)
        lineas.append(
            LineaOut(
                cuenta_id=ln.cuenta_id,
                cuenta_codigo=c.codigo if c else "",
                cuenta_nombre=c.nombre if c else "",
                debe=ln.debe,
                haber=ln.haber,
                detalle=ln.detalle,
            )
        )
        total += ln.debe
    return AsientoOut(
        id=a.id, numero=a.numero, fecha=a.fecha, descripcion=a.descripcion,
        origen_tipo=a.origen_tipo, anulado=a.anulado_at is not None,
        total=total, lineas=lineas,
    )


async def _periodo_cerrado(db: AsyncSession, tenant_id: uuid.UUID, fecha: date) -> bool:
    return (
        await db.scalar(
            select(func.count())
            .select_from(ContabPeriodo)
            .where(
                ContabPeriodo.tenant_id == tenant_id,
                ContabPeriodo.periodo == fecha.replace(day=1),
                ContabPeriodo.anulado_at.is_(None),
            )
        )
    ) > 0


# ===== Plan de cuentas =====

@router.get("/plan", response_model=list[CuentaOut])
async def listar_plan(
    incluir_inactivas: bool = False,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    # siembra lazy del plan base + mapeos default (patrón roles RBAC)
    if await sc.sembrar_plan_base(db, usuario.tenant_id):
        await db.commit()
    stmt = select(PlanCuenta).where(PlanCuenta.tenant_id == usuario.tenant_id)
    if not incluir_inactivas:
        stmt = stmt.where(PlanCuenta.activa.is_(True))
    filas = (await db.scalars(stmt.order_by(PlanCuenta.codigo))).all()
    return [CuentaOut.model_validate(c) for c in filas]


@router.post("/plan", response_model=CuentaOut, status_code=status.HTTP_201_CREATED)
async def crear_cuenta(
    body: CuentaIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if body.padre_id is not None:
        padre = await db.scalar(
            select(PlanCuenta).where(
                PlanCuenta.id == body.padre_id, PlanCuenta.tenant_id == usuario.tenant_id
            )
        )
        if padre is None:
            raise HTTPException(status_code=422, detail="Cuenta padre inexistente")
    existe = await db.scalar(
        select(PlanCuenta.id).where(
            PlanCuenta.tenant_id == usuario.tenant_id, PlanCuenta.codigo == body.codigo.strip()
        )
    )
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese código")
    cuenta = PlanCuenta(
        tenant_id=usuario.tenant_id, codigo=body.codigo.strip(), nombre=body.nombre.strip(),
        tipo=body.tipo, imputable=body.imputable, padre_id=body.padre_id,
    )
    db.add(cuenta)
    await db.commit()
    await db.refresh(cuenta)
    return CuentaOut.model_validate(cuenta)


@router.put("/plan/{cuenta_id}", response_model=CuentaOut)
async def editar_cuenta(
    cuenta_id: uuid.UUID,
    body: CuentaUpdate,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cuenta = await db.scalar(
        select(PlanCuenta).where(
            PlanCuenta.id == cuenta_id, PlanCuenta.tenant_id == usuario.tenant_id
        )
    )
    if cuenta is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if body.nombre is not None:
        cuenta.nombre = body.nombre.strip()
    if body.activa is not None:
        if cuenta.es_sistema and not body.activa:
            raise HTTPException(status_code=422, detail="Las cuentas del plan base no se inactivan")
        cuenta.activa = body.activa
    await db.commit()
    await db.refresh(cuenta)
    return CuentaOut.model_validate(cuenta)


# ===== Mapeos =====

@router.get("/origenes")
async def listar_origenes(
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
):
    return [{"origen": o, "descripcion": d} for o, d in sc.ORIGENES.items()]


@router.get("/mapeos", response_model=list[MapeoOut])
async def listar_mapeos(
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    if await sc.sembrar_plan_base(db, usuario.tenant_id):
        await db.commit()
    filas = (
        await db.scalars(
            select(AsientoMapeo)
            .where(AsientoMapeo.tenant_id == usuario.tenant_id)
            .order_by(AsientoMapeo.origen, AsientoMapeo.clave)
        )
    ).all()
    return [MapeoOut.model_validate(m) for m in filas]


@router.put("/mapeos", response_model=MapeoOut)
async def upsert_mapeo(
    body: MapeoIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if body.origen not in sc.ORIGENES:
        raise HTTPException(status_code=422, detail="Origen de mapeo inexistente")
    cuenta = await db.scalar(
        select(PlanCuenta).where(
            PlanCuenta.id == body.cuenta_id,
            PlanCuenta.tenant_id == usuario.tenant_id,
            PlanCuenta.imputable.is_(True),
        )
    )
    if cuenta is None:
        raise HTTPException(status_code=422, detail="La cuenta debe existir y ser imputable")
    clave = (body.clave or "").strip() or None
    mapeo = await db.scalar(
        select(AsientoMapeo).where(
            AsientoMapeo.tenant_id == usuario.tenant_id,
            AsientoMapeo.origen == body.origen,
            AsientoMapeo.clave == clave if clave else AsientoMapeo.clave.is_(None),
        )
    )
    if mapeo is None:
        mapeo = AsientoMapeo(tenant_id=usuario.tenant_id, origen=body.origen, clave=clave)
        db.add(mapeo)
    mapeo.cuenta_id = body.cuenta_id
    mapeo.updated_at = func.now()
    await db.commit()
    await db.refresh(mapeo)
    return MapeoOut.model_validate(mapeo)


# ===== Motor =====

@router.post("/regenerar")
async def regenerar(
    body: RegenerarIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if body.desde > body.hasta:
        raise HTTPException(status_code=422, detail="Rango de fechas inválido")
    if (body.hasta - body.desde).days > 400:
        raise HTTPException(status_code=422, detail="Rango máximo: 400 días")
    if await sc.sembrar_plan_base(db, usuario.tenant_id):
        await db.flush()
    cerrados = await sc.periodos_cerrados(db, usuario.tenant_id, body.desde, body.hasta)
    if cerrados:
        raise HTTPException(
            status_code=409,
            detail=f"Período cerrado en el rango: {', '.join(p.isoformat()[:7] for p in cerrados)}",
        )
    resumen = await sc.derivar(db, usuario.tenant_id, body.desde, body.hasta)
    await db.commit()
    return resumen


# ===== Asientos (diario) =====

@router.get("/asientos", response_model=list[AsientoOut])
async def listar_asientos(
    response: Response,
    desde: date | None = None,
    hasta: date | None = None,
    origen: str | None = None,
    incluir_anulados: bool = False,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Asiento).where(Asiento.tenant_id == usuario.tenant_id)
    if not incluir_anulados:
        stmt = stmt.where(Asiento.anulado_at.is_(None))
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(Asiento.fecha <= hasta)
    if origen:
        stmt = stmt.where(Asiento.origen_tipo == origen)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = (
        await db.scalars(
            stmt.order_by(Asiento.fecha.desc(), Asiento.numero.desc())
            .limit(min(limit, 200))
            .offset(offset)
        )
    ).all()
    cuentas = await _cuentas_por_id(db, usuario.tenant_id)
    return [_asiento_out(a, cuentas) for a in filas]


@router.get("/diario.csv")
async def diario_csv(
    desde: date,
    hasta: date,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas = (
        await db.scalars(
            select(Asiento)
            .where(
                Asiento.tenant_id == usuario.tenant_id,
                Asiento.anulado_at.is_(None),
                Asiento.fecha >= desde,
                Asiento.fecha <= hasta,
            )
            .order_by(Asiento.fecha.asc(), Asiento.numero.asc())
            .limit(5000)
        )
    ).all()
    cuentas = await _cuentas_por_id(db, usuario.tenant_id)
    encabezado = ["Nro", "Fecha", "Descripción", "Cuenta", "Nombre", "Debe", "Haber"]
    datos = []
    for a in filas:
        for ln in a.lineas:
            c = cuentas.get(ln.cuenta_id)
            datos.append([
                a.numero or "", a.fecha.strftime("%d/%m/%Y"), a.descripcion or "",
                c.codigo if c else "", c.nombre if c else "",
                num(ln.debe), num(ln.haber),
            ])
    return csv_response("libro-diario.csv", encabezado, datos)


@router.post("/asientos", response_model=AsientoOut, status_code=status.HTTP_201_CREATED)
async def crear_asiento_manual(
    body: AsientoManualIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if await _periodo_cerrado(db, usuario.tenant_id, body.fecha):
        raise HTTPException(status_code=409, detail="El período de esa fecha está cerrado")
    total_debe = sum((l.debe for l in body.lineas), D0)
    total_haber = sum((l.haber for l in body.lineas), D0)
    if total_debe != total_haber or total_debe == 0:
        raise HTTPException(status_code=422, detail="El asiento debe balancear (debe = haber > 0)")
    if any(l.debe > 0 and l.haber > 0 for l in body.lineas):
        raise HTTPException(status_code=422, detail="Cada línea va al debe O al haber")
    cuentas = await _cuentas_por_id(db, usuario.tenant_id)
    for l in body.lineas:
        c = cuentas.get(l.cuenta_id)
        if c is None or not c.imputable or not c.activa:
            raise HTTPException(status_code=422, detail="Cuenta inexistente o no imputable")
    ultimo = await db.scalar(
        select(func.coalesce(func.max(Asiento.numero), 0)).where(
            Asiento.tenant_id == usuario.tenant_id
        )
    )
    asiento = Asiento(
        tenant_id=usuario.tenant_id, numero=int(ultimo or 0) + 1, fecha=body.fecha,
        descripcion=body.descripcion.strip(), origen_tipo="manual", creado_por=usuario.id,
    )
    db.add(asiento)
    await db.flush()
    for orden, l in enumerate(body.lineas):
        db.add(
            AsientoLinea(
                tenant_id=usuario.tenant_id, asiento_id=asiento.id, orden=orden,
                cuenta_id=l.cuenta_id, debe=l.debe, haber=l.haber,
                detalle=(l.detalle or "").strip() or None,
            )
        )
    await db.commit()
    asiento = await db.scalar(select(Asiento).where(Asiento.id == asiento.id))
    return _asiento_out(asiento, cuentas)


@router.get("/asientos/{asiento_id}", response_model=AsientoOut)
async def detalle_asiento(
    asiento_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    asiento = await db.scalar(
        select(Asiento).where(
            Asiento.id == asiento_id, Asiento.tenant_id == usuario.tenant_id
        )
    )
    if asiento is None:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    return _asiento_out(asiento, await _cuentas_por_id(db, usuario.tenant_id))


@router.post("/asientos/{asiento_id}/anular", response_model=AsientoOut)
async def anular_asiento(
    asiento_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("contabilidad", "anular")),
    db: AsyncSession = Depends(get_db),
):
    asiento = await db.scalar(
        select(Asiento).where(
            Asiento.id == asiento_id,
            Asiento.tenant_id == usuario.tenant_id,
            Asiento.anulado_at.is_(None),
        )
    )
    if asiento is None:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    if asiento.origen_tipo not in ("manual", "apertura"):
        raise HTTPException(
            status_code=409,
            detail="Los asientos derivados no se anulan: se anula el documento y se regenera",
        )
    if await _periodo_cerrado(db, usuario.tenant_id, asiento.fecha):
        raise HTTPException(status_code=409, detail="El período de esa fecha está cerrado")
    asiento.anulado_at = datetime.now(timezone.utc)
    asiento.anulado_por = usuario.id
    await db.commit()
    asiento = await db.scalar(select(Asiento).where(Asiento.id == asiento_id))
    return _asiento_out(asiento, await _cuentas_por_id(db, usuario.tenant_id))


# ===== Reportes =====

@router.get("/sumas-y-saldos")
async def sumas_y_saldos(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(
            AsientoLinea.cuenta_id,
            func.coalesce(func.sum(AsientoLinea.debe), 0),
            func.coalesce(func.sum(AsientoLinea.haber), 0),
        )
        .select_from(AsientoLinea)
        .join(Asiento, AsientoLinea.asiento_id == Asiento.id)
        .where(
            AsientoLinea.tenant_id == usuario.tenant_id,
            Asiento.anulado_at.is_(None),
        )
        .group_by(AsientoLinea.cuenta_id)
    )
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(Asiento.fecha <= hasta)
    filas = (await db.execute(stmt)).all()
    cuentas = await _cuentas_por_id(db, usuario.tenant_id)
    out = []
    tot_debe = tot_haber = D0
    for cuenta_id, debe, haber in filas:
        c = cuentas.get(cuenta_id)
        debe, haber = Decimal(debe), Decimal(haber)
        saldo = debe - haber
        tot_debe += debe
        tot_haber += haber
        out.append({
            "cuenta_id": str(cuenta_id),
            "codigo": c.codigo if c else "",
            "nombre": c.nombre if c else "",
            "tipo": c.tipo if c else "",
            "debe": str(debe),
            "haber": str(haber),
            "saldo_deudor": str(saldo if saldo > 0 else D0),
            "saldo_acreedor": str(-saldo if saldo < 0 else D0),
        })
    out.sort(key=lambda x: x["codigo"])
    return {
        "filas": out,
        "total_debe": str(tot_debe),
        "total_haber": str(tot_haber),
        "balanceado": tot_debe == tot_haber,
    }


@router.get("/mayor/{cuenta_id}")
async def mayor(
    cuenta_id: uuid.UUID,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = 200,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    cuenta = await db.scalar(
        select(PlanCuenta).where(
            PlanCuenta.id == cuenta_id, PlanCuenta.tenant_id == usuario.tenant_id
        )
    )
    if cuenta is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    stmt = (
        select(Asiento.fecha, Asiento.numero, Asiento.descripcion, AsientoLinea.debe,
               AsientoLinea.haber, AsientoLinea.detalle)
        .select_from(AsientoLinea)
        .join(Asiento, AsientoLinea.asiento_id == Asiento.id)
        .where(
            AsientoLinea.tenant_id == usuario.tenant_id,
            AsientoLinea.cuenta_id == cuenta_id,
            Asiento.anulado_at.is_(None),
        )
    )
    if desde:
        stmt = stmt.where(Asiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(Asiento.fecha <= hasta)
    filas = (
        await db.execute(stmt.order_by(Asiento.fecha.asc(), Asiento.numero.asc()).limit(min(limit, 1000)))
    ).all()
    movimientos = []
    saldo = D0
    for fecha, numero, desc, debe, haber, detalle in filas:
        saldo += Decimal(debe) - Decimal(haber)
        movimientos.append({
            "fecha": fecha.isoformat(),
            "numero": numero,
            "descripcion": desc,
            "detalle": detalle,
            "debe": str(debe),
            "haber": str(haber),
            "saldo": str(saldo),
        })
    return {
        "cuenta": {"id": str(cuenta.id), "codigo": cuenta.codigo, "nombre": cuenta.nombre},
        "movimientos": movimientos,
        "saldo": str(saldo),
    }


# ===== Bienes de uso (F9-bis, diseño §6.1) =====
# Rutas estáticas de /activos ANTES de las paramétricas (regla §6 del CLAUDE.md).

@router.get("/activos/categorias", response_model=list[CategoriaOut])
async def listar_categorias(
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    if await sc.sembrar_plan_base(db, usuario.tenant_id):
        await db.commit()
    filas = (
        await db.scalars(
            select(ActivoCategoria)
            .where(ActivoCategoria.tenant_id == usuario.tenant_id, ActivoCategoria.activa.is_(True))
            .order_by(ActivoCategoria.nombre)
        )
    ).all()
    return [CategoriaOut.model_validate(c) for c in filas]


@router.post("/activos/categorias", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
async def crear_categoria(
    body: CategoriaIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    existe = await db.scalar(
        select(ActivoCategoria.id).where(
            ActivoCategoria.tenant_id == usuario.tenant_id,
            ActivoCategoria.nombre == body.nombre.strip(),
        )
    )
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")
    cat = ActivoCategoria(
        tenant_id=usuario.tenant_id, nombre=body.nombre.strip(),
        vida_util_meses=body.vida_util_meses,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoriaOut.model_validate(cat)


def _activo_out(a: ActivoFijo, categorias: dict, corte: date) -> ActivoOut:
    out = ActivoOut.model_validate(a)
    cat = categorias.get(a.categoria_id)
    out.categoria_nombre = cat.nombre if cat else ""
    out.anulado = a.anulado_at is not None
    out.amort_acumulada = sum(
        (m for f, m in sc.cuotas_amortizacion(a) if f <= corte), D0
    )
    out.valor_contable = Decimal(a.valor_origen) - out.amort_acumulada
    return out


async def _activos_cuadro(
    db: AsyncSession, tenant_id: uuid.UUID, corte: date, incluir_anulados: bool
) -> list[ActivoOut]:
    stmt = select(ActivoFijo).where(ActivoFijo.tenant_id == tenant_id)
    if not incluir_anulados:
        stmt = stmt.where(ActivoFijo.anulado_at.is_(None))
    filas = (await db.scalars(stmt.order_by(ActivoFijo.fecha_alta, ActivoFijo.nombre))).all()
    categorias = {
        c.id: c
        for c in (
            await db.scalars(
                select(ActivoCategoria).where(ActivoCategoria.tenant_id == tenant_id)
            )
        ).all()
    }
    return [_activo_out(a, categorias, corte) for a in filas]


@router.get("/activos/cuadro.csv")
async def cuadro_activos_csv(
    corte: date | None = None,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas = await _activos_cuadro(db, usuario.tenant_id, corte or date.today(), False)
    encabezado = ["Bien", "Categoría", "Alta", "Vida útil (meses)", "Valor origen",
                  "Valor residual", "Amort. acumulada", "Valor contable", "Baja"]
    datos = [
        [a.nombre, a.categoria_nombre, a.fecha_alta.strftime("%d/%m/%Y"), a.vida_util_meses,
         num(a.valor_origen), num(a.valor_residual), num(a.amort_acumulada),
         num(a.valor_contable), a.fecha_baja.strftime("%d/%m/%Y") if a.fecha_baja else ""]
        for a in filas
    ]
    return csv_response("bienes-de-uso.csv", encabezado, datos)


@router.get("/activos", response_model=list[ActivoOut])
async def listar_activos(
    corte: date | None = None,
    incluir_anulados: bool = False,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return await _activos_cuadro(db, usuario.tenant_id, corte or date.today(), incluir_anulados)


@router.post("/activos", response_model=ActivoOut, status_code=status.HTTP_201_CREATED)
async def crear_activo(
    body: ActivoIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if body.valor_residual >= body.valor_origen:
        raise HTTPException(status_code=422, detail="El valor residual debe ser menor al de origen")
    cat = await db.scalar(
        select(ActivoCategoria).where(
            ActivoCategoria.id == body.categoria_id,
            ActivoCategoria.tenant_id == usuario.tenant_id,
        )
    )
    if cat is None:
        raise HTTPException(status_code=422, detail="Categoría inexistente")
    if body.compra_id is not None:
        compra = await db.scalar(
            select(Compra.id).where(
                Compra.id == body.compra_id, Compra.tenant_id == usuario.tenant_id
            )
        )
        if compra is None:
            raise HTTPException(status_code=422, detail="Compra inexistente")
    activo = ActivoFijo(
        tenant_id=usuario.tenant_id, nombre=body.nombre.strip(), categoria_id=body.categoria_id,
        fecha_alta=body.fecha_alta,
        inicio_amortizacion=(body.inicio_amortizacion or body.fecha_alta).replace(day=1),
        valor_origen=body.valor_origen, valor_residual=body.valor_residual,
        vida_util_meses=body.vida_util_meses, compra_id=body.compra_id,
        observaciones=(body.observaciones or "").strip() or None, creado_por=usuario.id,
    )
    db.add(activo)
    await db.commit()
    await db.refresh(activo)
    return _activo_out(activo, {cat.id: cat}, date.today())


@router.put("/activos/{activo_id}", response_model=ActivoOut)
async def editar_activo(
    activo_id: uuid.UUID,
    body: ActivoIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    activo = await db.scalar(
        select(ActivoFijo).where(
            ActivoFijo.id == activo_id,
            ActivoFijo.tenant_id == usuario.tenant_id,
            ActivoFijo.anulado_at.is_(None),
        )
    )
    if activo is None:
        raise HTTPException(status_code=404, detail="Bien de uso no encontrado")
    if activo.fecha_baja is not None:
        raise HTTPException(status_code=409, detail="El bien está dado de baja")
    if body.valor_residual >= body.valor_origen:
        raise HTTPException(status_code=422, detail="El valor residual debe ser menor al de origen")
    cat = await db.scalar(
        select(ActivoCategoria).where(
            ActivoCategoria.id == body.categoria_id,
            ActivoCategoria.tenant_id == usuario.tenant_id,
        )
    )
    if cat is None:
        raise HTTPException(status_code=422, detail="Categoría inexistente")
    activo.nombre = body.nombre.strip()
    activo.categoria_id = body.categoria_id
    activo.fecha_alta = body.fecha_alta
    activo.inicio_amortizacion = (body.inicio_amortizacion or body.fecha_alta).replace(day=1)
    activo.valor_origen = body.valor_origen
    activo.valor_residual = body.valor_residual
    activo.vida_util_meses = body.vida_util_meses
    activo.observaciones = (body.observaciones or "").strip() or None
    await db.commit()
    await db.refresh(activo)
    return _activo_out(activo, {cat.id: cat}, date.today())


@router.post("/activos/{activo_id}/baja", response_model=ActivoOut)
async def baja_activo(
    activo_id: uuid.UUID,
    body: ActivoBajaIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    activo = await db.scalar(
        select(ActivoFijo).where(
            ActivoFijo.id == activo_id,
            ActivoFijo.tenant_id == usuario.tenant_id,
            ActivoFijo.anulado_at.is_(None),
        )
    )
    if activo is None:
        raise HTTPException(status_code=404, detail="Bien de uso no encontrado")
    if activo.fecha_baja is not None:
        raise HTTPException(status_code=409, detail="El bien ya está dado de baja")
    if body.fecha_baja < activo.fecha_alta:
        raise HTTPException(status_code=422, detail="La baja no puede ser anterior al alta")
    activo.fecha_baja = body.fecha_baja
    activo.baja_motivo = (body.baja_motivo or "").strip() or None
    await db.commit()
    await db.refresh(activo)
    categorias = {
        c.id: c
        for c in (
            await db.scalars(
                select(ActivoCategoria).where(ActivoCategoria.tenant_id == usuario.tenant_id)
            )
        ).all()
    }
    return _activo_out(activo, categorias, date.today())


@router.post("/activos/{activo_id}/anular", response_model=ActivoOut)
async def anular_activo(
    activo_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("contabilidad", "anular")),
    db: AsyncSession = Depends(get_db),
):
    """Error de carga: se marca (014). Al regenerar, sus asientos derivados
    desaparecen — son artefactos regenerables, no documentos."""
    activo = await db.scalar(
        select(ActivoFijo).where(
            ActivoFijo.id == activo_id,
            ActivoFijo.tenant_id == usuario.tenant_id,
            ActivoFijo.anulado_at.is_(None),
        )
    )
    if activo is None:
        raise HTTPException(status_code=404, detail="Bien de uso no encontrado")
    activo.anulado_at = datetime.now(timezone.utc)
    activo.anulado_por = usuario.id
    await db.commit()
    await db.refresh(activo)
    categorias = {
        c.id: c
        for c in (
            await db.scalars(
                select(ActivoCategoria).where(ActivoCategoria.tenant_id == usuario.tenant_id)
            )
        ).all()
    }
    return _activo_out(activo, categorias, date.today())


# ===== Balance general (F9-bis, diseño §6.3) =====

async def _balance_data(db: AsyncSession, tenant_id: uuid.UUID, hasta: date) -> dict:
    """Saldos al corte presentados en el árbol del plan, con el resultado del
    ejercicio inyectado en el PN. Asume apertura para la historia previa."""
    filas = (
        await db.execute(
            select(
                AsientoLinea.cuenta_id,
                func.coalesce(func.sum(AsientoLinea.debe - AsientoLinea.haber), 0),
            )
            .select_from(AsientoLinea)
            .join(Asiento, AsientoLinea.asiento_id == Asiento.id)
            .where(
                AsientoLinea.tenant_id == tenant_id,
                Asiento.anulado_at.is_(None),
                Asiento.fecha <= hasta,
            )
            .group_by(AsientoLinea.cuenta_id)
        )
    ).all()
    propio = {cuenta_id: Decimal(s) for cuenta_id, s in filas}
    cuentas = (
        await db.scalars(select(PlanCuenta).where(PlanCuenta.tenant_id == tenant_id))
    ).all()
    hijos: dict = {}
    for c in cuentas:
        hijos.setdefault(c.padre_id, []).append(c)
    rolled: dict = {}

    def _rollup(c: PlanCuenta) -> Decimal:
        if c.id in rolled:
            return rolled[c.id]
        total = propio.get(c.id, D0)
        for h in hijos.get(c.id, []):
            total += _rollup(h)
        rolled[c.id] = total
        return total

    for c in cuentas:
        _rollup(c)

    secciones = []
    totales: dict[str, Decimal] = {}
    for tipo in ("activo", "pasivo", "pn"):
        signo = 1 if tipo == "activo" else -1  # pasivo/PN se presentan por su saldo acreedor
        filas_sec = []
        total = D0
        for c in sorted((x for x in cuentas if x.tipo == tipo), key=lambda x: x.codigo):
            saldo = rolled.get(c.id, D0) * signo
            if saldo == 0:
                continue
            filas_sec.append({
                "cuenta_id": str(c.id), "codigo": c.codigo, "nombre": c.nombre,
                "nivel": c.codigo.count("."), "imputable": c.imputable, "saldo": str(saldo),
            })
            if c.padre_id is None:
                total += saldo
        totales[tipo] = total
        secciones.append({"tipo": tipo, "total": str(total), "cuentas": filas_sec})

    resultado = -sum(
        (rolled.get(c.id, D0) for c in cuentas if c.tipo in ("r_positivo", "r_negativo") and c.padre_id is None),
        D0,
    )
    pn_total = totales["pn"] + resultado
    return {
        "hasta": hasta.isoformat(),
        "secciones": secciones,
        "activo_total": str(totales["activo"]),
        "pasivo_total": str(totales["pasivo"]),
        "resultado_ejercicio": str(resultado),
        "pn_total": str(pn_total),
        "ecuacion_ok": totales["activo"] == totales["pasivo"] + pn_total,
    }


@router.get("/balance")
async def balance(
    hasta: date | None = None,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return await _balance_data(db, usuario.tenant_id, hasta or date.today())


@router.get("/balance.csv")
async def balance_csv(
    hasta: date | None = None,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    data = await _balance_data(db, usuario.tenant_id, hasta or date.today())
    encabezado = ["Sección", "Código", "Cuenta", "Saldo"]
    datos = []
    etiquetas = {"activo": "ACTIVO", "pasivo": "PASIVO", "pn": "PATRIMONIO NETO"}
    for sec in data["secciones"]:
        for f in sec["cuentas"]:
            datos.append([etiquetas[sec["tipo"]], f["codigo"], f["nombre"], num(Decimal(f["saldo"]))])
        datos.append([etiquetas[sec["tipo"]], "", "TOTAL", num(Decimal(sec["total"]))])
    datos.append(["PATRIMONIO NETO", "", "Resultado del ejercicio", num(Decimal(data["resultado_ejercicio"]))])
    datos.append(["", "", "PN + Resultado", num(Decimal(data["pn_total"]))])
    return csv_response(f"balance-{data['hasta']}.csv", encabezado, datos)


# ===== Export al contador (F9-bis, diseño §6.4): ZIP con 4 CSV genéricos =====

@router.get("/export-contador.zip")
async def export_contador(
    desde: date,
    hasta: date,
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    cuentas = await _cuentas_por_id(db, usuario.tenant_id)

    plan_csv = csv_texto(
        ["Código", "Nombre", "Tipo", "Imputable"],
        [[c.codigo, c.nombre, c.tipo, "Sí" if c.imputable else "No"]
         for c in sorted(cuentas.values(), key=lambda x: x.codigo)],
    )

    asientos = (
        await db.scalars(
            select(Asiento)
            .where(
                Asiento.tenant_id == usuario.tenant_id,
                Asiento.anulado_at.is_(None),
                Asiento.fecha >= desde,
                Asiento.fecha <= hasta,
            )
            .order_by(Asiento.fecha.asc(), Asiento.numero.asc())
            .limit(20000)
        )
    ).all()
    diario_filas = []
    mayor_filas = []
    for a in asientos:
        for ln in a.lineas:
            c = cuentas.get(ln.cuenta_id)
            diario_filas.append([
                a.numero or "", a.fecha.strftime("%d/%m/%Y"), a.descripcion or "",
                c.codigo if c else "", c.nombre if c else "",
                num(ln.debe), num(ln.haber),
            ])
            mayor_filas.append([
                c.codigo if c else "", c.nombre if c else "",
                a.fecha.strftime("%d/%m/%Y"), a.numero or "", a.descripcion or "",
                ln.detalle or "", num(ln.debe), num(ln.haber),
            ])
    mayor_filas.sort(key=lambda f: (f[0], f[2][6:] + f[2][3:5] + f[2][:2], f[3] or 0))
    diario_csv = csv_texto(
        ["Nro", "Fecha", "Descripción", "Cuenta", "Nombre", "Debe", "Haber"], diario_filas
    )
    mayor_csv = csv_texto(
        ["Cuenta", "Nombre", "Fecha", "Nro", "Descripción", "Detalle", "Debe", "Haber"],
        mayor_filas,
    )

    sumas: dict = {}
    for a in asientos:
        for ln in a.lineas:
            deb, hab = sumas.get(ln.cuenta_id, (D0, D0))
            sumas[ln.cuenta_id] = (deb + ln.debe, hab + ln.haber)
    sumas_filas = []
    for cuenta_id, (deb, hab) in sumas.items():
        c = cuentas.get(cuenta_id)
        saldo = deb - hab
        sumas_filas.append([
            c.codigo if c else "", c.nombre if c else "", num(deb), num(hab),
            num(saldo if saldo > 0 else D0), num(-saldo if saldo < 0 else D0),
        ])
    sumas_filas.sort(key=lambda f: f[0])
    sumas_csv = csv_texto(
        ["Código", "Nombre", "Debe", "Haber", "Saldo deudor", "Saldo acreedor"], sumas_filas
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("plan-de-cuentas.csv", plan_csv)
        zf.writestr("libro-diario.csv", diario_csv)
        zf.writestr("sumas-y-saldos.csv", sumas_csv)
        zf.writestr("mayor.csv", mayor_csv)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="contabilidad-{desde}-{hasta}.zip"'
        },
    )


# ===== Asiento de apertura asistido (F9-bis, diseño §6.5) =====

@router.get("/apertura/sugerencia")
async def apertura_sugerencia(
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Propone las líneas de apertura desde los datos vivos del sistema.
    Los saldos son al día de HOY — si la apertura se fecha hacia atrás,
    revisarlos a mano."""
    if await sc.sembrar_plan_base(db, usuario.tenant_id):
        await db.commit()
    tenant_id = usuario.tenant_id
    mapa = await sc._mapa(db, tenant_id)
    cuentas = await _cuentas_por_id(db, tenant_id)
    por_codigo = {c.codigo: c for c in cuentas.values()}

    lineas: list[tuple[uuid.UUID | None, Decimal, str]] = []

    bancarias = (
        await db.scalars(
            select(CuentaBancaria).where(
                CuentaBancaria.tenant_id == tenant_id, CuentaBancaria.activa.is_(True)
            )
        )
    ).all()
    for cb in bancarias:
        movs = (
            await db.execute(
                select(BancoMovimiento.tipo, func.coalesce(func.sum(BancoMovimiento.importe), 0))
                .where(
                    BancoMovimiento.cuenta_id == cb.id,
                    BancoMovimiento.anulado_at.is_(None),
                )
                .group_by(BancoMovimiento.tipo)
            )
        ).all()
        saldo = Decimal(cb.saldo_inicial)
        for tipo, suma in movs:
            saldo += Decimal(suma) * SIGNO_BANCO.get(tipo, 1)
        if saldo != 0:
            lineas.append(
                (mapa.get("cuenta_bancaria", cb.id), saldo,
                 f"{cb.banco} {cb.numero or ''}".strip())
            )

    deudores = await _cobros_pendientes(db, tenant_id)
    if deudores:
        lineas.append((mapa.get("deudores"), Decimal(deudores), "Saldos de clientes"))

    proveedores = await db.scalar(
        select(func.coalesce(func.sum(Compra.saldo * TipoComprobanteCompra.signo_cta_cte), 0))
        .select_from(Compra)
        .join(TipoComprobanteCompra, TipoComprobanteCompra.codigo == Compra.tipo_codigo)
        .where(
            Compra.tenant_id == tenant_id,
            Compra.estado == "registrado",
            Compra.saldo > 0,
        )
    )
    if proveedores:
        lineas.append((mapa.get("proveedores"), -Decimal(proveedores), "Saldos de proveedores"))

    cartera = await db.scalar(
        select(func.coalesce(func.sum(Cheque.importe), 0)).where(
            Cheque.tenant_id == tenant_id, Cheque.clase == "tercero",
            Cheque.estado == "en_cartera",
        )
    )
    if cartera:
        lineas.append((mapa.get("cheques_cartera"), Decimal(cartera), "Cheques de terceros en cartera"))

    diferidos = await db.scalar(
        select(func.coalesce(func.sum(Cheque.importe), 0)).where(
            Cheque.tenant_id == tenant_id, Cheque.clase == "propio",
            Cheque.estado == "emitido",
        )
    )
    if diferidos:
        lineas.append((mapa.get("cheques_diferidos"), -Decimal(diferidos), "Cheques propios pendientes de débito"))

    stock = await _stock_valorizado(db, tenant_id)
    if stock:
        lineas.append((mapa.get("inventario"), Decimal(stock).quantize(Decimal("0.01")), "Stock valorizado"))

    residual = sum((m for _, m, _ in lineas), D0)
    capital = por_codigo.get("3.1.01")
    if residual != 0 and capital is not None:
        lineas.append((capital.id, -residual, "Contrapartida (capital)"))

    out = []
    for cuenta_id, monto, detalle in lineas:
        c = cuentas.get(cuenta_id)
        out.append({
            "cuenta_id": str(cuenta_id) if cuenta_id else None,
            "cuenta_codigo": c.codigo if c else "",
            "cuenta_nombre": c.nombre if c else "",
            "debe": str(monto) if monto > 0 else "0",
            "haber": str(-monto) if monto < 0 else "0",
            "detalle": detalle,
        })
    return {
        "lineas": out,
        "advertencia": "Los saldos sugeridos son al día de HOY. Si la apertura se fecha hacia atrás, revisalos a mano.",
    }


@router.post("/apertura", response_model=AsientoOut, status_code=status.HTTP_201_CREATED)
async def crear_apertura(
    body: AperturaIn,
    usuario: Usuario = Depends(requiere("contabilidad", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Asiento de apertura: origen_tipo `apertura` — la regeneración nunca lo
    borra, se anula marcando y solo puede haber UNO vivo por tenant."""
    existente = await db.scalar(
        select(Asiento.id).where(
            Asiento.tenant_id == usuario.tenant_id,
            Asiento.origen_tipo == "apertura",
            Asiento.anulado_at.is_(None),
        )
    )
    if existente:
        raise HTTPException(
            status_code=409,
            detail="Ya hay un asiento de apertura vivo — anulalo antes de crear otro",
        )
    if await _periodo_cerrado(db, usuario.tenant_id, body.fecha):
        raise HTTPException(status_code=409, detail="El período de esa fecha está cerrado")
    total_debe = sum((l.debe for l in body.lineas), D0)
    total_haber = sum((l.haber for l in body.lineas), D0)
    if total_debe != total_haber or total_debe == 0:
        raise HTTPException(status_code=422, detail="El asiento debe balancear (debe = haber > 0)")
    if any(l.debe > 0 and l.haber > 0 for l in body.lineas):
        raise HTTPException(status_code=422, detail="Cada línea va al debe O al haber")
    cuentas = await _cuentas_por_id(db, usuario.tenant_id)
    for l in body.lineas:
        c = cuentas.get(l.cuenta_id)
        if c is None or not c.imputable or not c.activa:
            raise HTTPException(status_code=422, detail="Cuenta inexistente o no imputable")
    ultimo = await db.scalar(
        select(func.coalesce(func.max(Asiento.numero), 0)).where(
            Asiento.tenant_id == usuario.tenant_id
        )
    )
    asiento = Asiento(
        tenant_id=usuario.tenant_id, numero=int(ultimo or 0) + 1, fecha=body.fecha,
        descripcion=body.descripcion.strip(), origen_tipo="apertura", creado_por=usuario.id,
    )
    db.add(asiento)
    await db.flush()
    for orden, l in enumerate(body.lineas):
        db.add(
            AsientoLinea(
                tenant_id=usuario.tenant_id, asiento_id=asiento.id, orden=orden,
                cuenta_id=l.cuenta_id, debe=l.debe, haber=l.haber,
                detalle=(l.detalle or "").strip() or None,
            )
        )
    await db.commit()
    asiento = await db.scalar(select(Asiento).where(Asiento.id == asiento.id))
    return _asiento_out(asiento, cuentas)


# ===== Períodos =====

@router.get("/periodos")
async def listar_periodos(
    usuario: Usuario = Depends(requiere("contabilidad", "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas = (
        await db.scalars(
            select(ContabPeriodo)
            .where(
                ContabPeriodo.tenant_id == usuario.tenant_id,
                ContabPeriodo.anulado_at.is_(None),
            )
            .order_by(ContabPeriodo.periodo.desc())
        )
    ).all()
    return [{"id": str(p.id), "periodo": p.periodo.isoformat(),
             "cerrado_at": p.cerrado_at.isoformat()} for p in filas]


@router.post("/periodos/cerrar", status_code=status.HTTP_201_CREATED)
async def cerrar_periodo(
    body: CerrarPeriodoIn,
    usuario: Usuario = Depends(requiere("contabilidad", "anular")),
    db: AsyncSession = Depends(get_db),
):
    periodo = body.periodo.replace(day=1)
    if await _periodo_cerrado(db, usuario.tenant_id, periodo):
        raise HTTPException(status_code=409, detail="Ese período ya está cerrado")
    p = ContabPeriodo(tenant_id=usuario.tenant_id, periodo=periodo, cerrado_por=usuario.id)
    db.add(p)
    await db.commit()
    return {"id": str(p.id), "periodo": periodo.isoformat()}


@router.post("/periodos/{periodo_id}/reabrir", status_code=status.HTTP_200_OK)
async def reabrir_periodo(
    periodo_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("contabilidad", "anular")),
    db: AsyncSession = Depends(get_db),
):
    p = await db.scalar(
        select(ContabPeriodo).where(
            ContabPeriodo.id == periodo_id,
            ContabPeriodo.tenant_id == usuario.tenant_id,
            ContabPeriodo.anulado_at.is_(None),
        )
    )
    if p is None:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    # reabrir = marcar (contrato 014); la historia del cierre queda
    p.anulado_at = datetime.now(timezone.utc)
    p.anulado_por = usuario.id
    await db.commit()
    return {"ok": True}
