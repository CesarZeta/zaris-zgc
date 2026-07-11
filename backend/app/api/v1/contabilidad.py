"""Contabilidad (Fase 9) — plan de cuentas, mapeos, motor derivado y reportes.

Diseño en docs/DISENO-CONTABILIDAD.md: los asientos se DERIVAN de los documentos
operativos (POST /regenerar, motor en services/contabilidad.py) y son
regenerables por período mientras el período no esté cerrado. Los asientos
manuales se cargan sueltos y se anulan MARCANDO (contrato 014). El diario, el
mayor y sumas y saldos son consultas sobre asientos vivos.

Rutas estáticas ANTES de las paramétricas (regla §6 del CLAUDE.md).
RBAC `contabilidad`: GET=ver, regenerar/mapeos/manual=editar, anular/cierre=anular.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csv_export import csv_response, num
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import (
    Asiento,
    AsientoLinea,
    AsientoMapeo,
    ContabPeriodo,
    PlanCuenta,
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
    if asiento.origen_tipo != "manual":
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
