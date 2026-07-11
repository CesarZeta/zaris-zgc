"""Bancos — cuentas, movimientos y conciliación por import de extracto (Fase 8).

El saldo de una cuenta es calculado (saldo_inicial + Σ movimientos con signo por
tipo), no una columna. La conciliación por import parsea un CSV genérico
(fecha;detalle;importe[;tipo]) en dos pasos: preview (propone matcheo contra
movimientos no conciliados, NO persiste) e import (crea movimientos y marca
conciliados). RBAC `bancos`.
"""

import csv
import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csv_export import csv_response, num
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import BancoMovimiento, CuentaBancaria, ExtractoImport, Usuario

router = APIRouter(prefix="/bancos", tags=["bancos"])

# Signo de cada tipo de movimiento sobre el saldo de la cuenta.
SIGNO_MOV: dict[str, int] = {
    "deposito": +1,
    "transferencia_in": +1,
    "credito": +1,
    "extraccion": -1,
    "transferencia_out": -1,
    "debito": -1,
    "comision": -1,
    "ajuste_positivo": +1,
    "ajuste_negativo": -1,
}
# Tipos que el usuario puede cargar a mano (deposito/debito los generan cheques).
TIPOS_MANUALES = (
    "extraccion", "transferencia_in", "transferencia_out",
    "credito", "comision", "ajuste_positivo", "ajuste_negativo",
)


# ===== Schemas =====

class CuentaIn(BaseModel):
    banco: str = Field(min_length=1, max_length=60)
    sucursal_bancaria: str | None = Field(None, max_length=60)
    tipo: str = Field("CC", pattern="^(CC|CA)$")
    numero: str | None = Field(None, max_length=30)
    cbu: str | None = Field(None, max_length=22)
    alias: str | None = Field(None, max_length=40)
    moneda: str = Field("ARS", pattern="^(ARS|USD)$")
    saldo_inicial: Decimal = Field(Decimal("0"))
    saldo_inicial_fecha: date | None = None  # 014: "saldo inicial ¿a qué fecha?"
    observaciones: str | None = Field(None, max_length=200)


class CuentaOut(BaseModel):
    id: uuid.UUID
    banco: str
    sucursal_bancaria: str | None
    tipo: str
    numero: str | None
    cbu: str | None
    alias: str | None
    moneda: str
    saldo_inicial: Decimal
    saldo_inicial_fecha: date | None = None
    activa: bool
    observaciones: str | None
    model_config = {"from_attributes": True}


class MovimientoIn(BaseModel):
    fecha: date | None = None
    tipo: str = Field(
        pattern="^(extraccion|transferencia_in|transferencia_out|credito|comision|ajuste_positivo|ajuste_negativo)$"
    )
    importe: Decimal = Field(gt=0)
    descripcion: str | None = Field(None, max_length=120)
    referencia: str | None = Field(None, max_length=60)


class MovimientoOut(BaseModel):
    id: uuid.UUID
    cuenta_id: uuid.UUID
    fecha: date
    tipo: str
    importe: Decimal
    signo: int = 1
    descripcion: str | None
    referencia: str | None
    cheque_id: uuid.UUID | None
    conciliado: bool
    fecha_conciliacion: date | None
    origen: str
    model_config = {"from_attributes": True}


# ===== Helpers =====

def _cuenta_out(c: CuentaBancaria) -> CuentaOut:
    return CuentaOut.model_validate(c)


def _mov_out(m: BancoMovimiento) -> MovimientoOut:
    out = MovimientoOut.model_validate(m)
    out.signo = SIGNO_MOV.get(m.tipo, 1)
    return out


async def _cuenta(db: AsyncSession, tenant_id: uuid.UUID, cuenta_id: uuid.UUID) -> CuentaBancaria:
    cuenta = await db.scalar(
        select(CuentaBancaria).where(
            CuentaBancaria.id == cuenta_id, CuentaBancaria.tenant_id == tenant_id
        )
    )
    if cuenta is None:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")
    return cuenta


async def _saldo(db: AsyncSession, cuenta: CuentaBancaria) -> Decimal:
    """saldo_inicial + Σ (importe × signo del tipo)."""
    filas = (
        await db.execute(
            select(BancoMovimiento.tipo, func.coalesce(func.sum(BancoMovimiento.importe), 0))
            .where(
                BancoMovimiento.cuenta_id == cuenta.id,
                BancoMovimiento.anulado_at.is_(None),
            )
            .group_by(BancoMovimiento.tipo)
        )
    ).all()
    saldo = Decimal(cuenta.saldo_inicial)
    for tipo, suma in filas:
        saldo += Decimal(suma) * SIGNO_MOV.get(tipo, 1)
    return saldo


# ===== Cuentas =====

@router.get("/cuentas", response_model=list[CuentaOut])
async def listar_cuentas(
    incluir_inactivas: bool = False,
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CuentaBancaria).where(CuentaBancaria.tenant_id == usuario.tenant_id)
    if not incluir_inactivas:
        stmt = stmt.where(CuentaBancaria.activa.is_(True))
    filas = await db.scalars(stmt.order_by(CuentaBancaria.banco.asc()))
    return [_cuenta_out(c) for c in filas]


@router.post("/cuentas", response_model=CuentaOut, status_code=status.HTTP_201_CREATED)
async def crear_cuenta(
    body: CuentaIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cuenta = CuentaBancaria(
        tenant_id=usuario.tenant_id,
        banco=body.banco.strip(),
        sucursal_bancaria=(body.sucursal_bancaria or "").strip() or None,
        tipo=body.tipo,
        numero=(body.numero or "").strip() or None,
        cbu=(body.cbu or "").strip() or None,
        alias=(body.alias or "").strip() or None,
        moneda=body.moneda,
        saldo_inicial=body.saldo_inicial,
        saldo_inicial_fecha=body.saldo_inicial_fecha,
        observaciones=(body.observaciones or "").strip() or None,
    )
    db.add(cuenta)
    await db.commit()
    cuenta = await db.scalar(select(CuentaBancaria).where(CuentaBancaria.id == cuenta.id))
    return _cuenta_out(cuenta)


@router.put("/cuentas/{cuenta_id}", response_model=CuentaOut)
async def editar_cuenta(
    cuenta_id: uuid.UUID,
    body: CuentaIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cuenta = await _cuenta(db, usuario.tenant_id, cuenta_id)
    cuenta.banco = body.banco.strip()
    cuenta.sucursal_bancaria = (body.sucursal_bancaria or "").strip() or None
    cuenta.tipo = body.tipo
    cuenta.numero = (body.numero or "").strip() or None
    cuenta.cbu = (body.cbu or "").strip() or None
    cuenta.alias = (body.alias or "").strip() or None
    cuenta.moneda = body.moneda
    cuenta.saldo_inicial = body.saldo_inicial
    cuenta.saldo_inicial_fecha = body.saldo_inicial_fecha
    cuenta.observaciones = (body.observaciones or "").strip() or None
    await db.commit()
    cuenta = await db.scalar(select(CuentaBancaria).where(CuentaBancaria.id == cuenta_id))
    return _cuenta_out(cuenta)


@router.post("/cuentas/{cuenta_id}/inactivar", response_model=CuentaOut)
async def inactivar_cuenta(
    cuenta_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    cuenta = await _cuenta(db, usuario.tenant_id, cuenta_id)
    cuenta.activa = not cuenta.activa  # toggle (reactivar también)
    await db.commit()
    cuenta = await db.scalar(select(CuentaBancaria).where(CuentaBancaria.id == cuenta_id))
    return _cuenta_out(cuenta)


@router.get("/cuentas/{cuenta_id}")
async def detalle_cuenta(
    cuenta_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    cuenta = await _cuenta(db, usuario.tenant_id, cuenta_id)
    saldo = await _saldo(db, cuenta)
    out = _cuenta_out(cuenta).model_dump()
    out["saldo_actual"] = str(saldo)
    return out


# ===== Movimientos =====

@router.get("/cuentas/{cuenta_id}/movimientos", response_model=list[MovimientoOut])
async def listar_movimientos(
    cuenta_id: uuid.UUID,
    response: Response,
    conciliado: bool | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limit: int = 50,
    offset: int = 0,
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    await _cuenta(db, usuario.tenant_id, cuenta_id)
    stmt = select(BancoMovimiento).where(
        BancoMovimiento.cuenta_id == cuenta_id,
        BancoMovimiento.tenant_id == usuario.tenant_id,
        BancoMovimiento.anulado_at.is_(None),
    )
    if conciliado is not None:
        stmt = stmt.where(BancoMovimiento.conciliado.is_(conciliado))
    if desde:
        stmt = stmt.where(BancoMovimiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(BancoMovimiento.fecha <= hasta)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        stmt.order_by(BancoMovimiento.fecha.desc(), BancoMovimiento.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return [_mov_out(m) for m in filas]


@router.post(
    "/cuentas/{cuenta_id}/movimientos",
    response_model=MovimientoOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_movimiento(
    cuenta_id: uuid.UUID,
    body: MovimientoIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _cuenta(db, usuario.tenant_id, cuenta_id)
    mov = BancoMovimiento(
        tenant_id=usuario.tenant_id,
        cuenta_id=cuenta_id,
        fecha=body.fecha or date.today(),
        tipo=body.tipo,
        importe=body.importe,
        descripcion=(body.descripcion or "").strip() or None,
        referencia=(body.referencia or "").strip() or None,
        origen="manual",
        creado_por=usuario.id,
    )
    db.add(mov)
    await db.commit()
    mov = await db.scalar(select(BancoMovimiento).where(BancoMovimiento.id == mov.id))
    return _mov_out(mov)


@router.post("/movimientos/{mov_id}/conciliar", response_model=MovimientoOut)
async def conciliar_movimiento(
    mov_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    mov = await db.scalar(
        select(BancoMovimiento)
        .where(
            BancoMovimiento.id == mov_id,
            BancoMovimiento.tenant_id == usuario.tenant_id,
            BancoMovimiento.anulado_at.is_(None),
        )
        .with_for_update(of=BancoMovimiento)
    )
    if mov is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    mov.conciliado = not mov.conciliado
    mov.fecha_conciliacion = date.today() if mov.conciliado else None
    await db.commit()
    mov = await db.scalar(select(BancoMovimiento).where(BancoMovimiento.id == mov_id))
    return _mov_out(mov)


@router.delete("/movimientos/{mov_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_movimiento(
    mov_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("bancos", "anular")),
    db: AsyncSession = Depends(get_db),
):
    mov = await db.scalar(
        select(BancoMovimiento).where(
            BancoMovimiento.id == mov_id,
            BancoMovimiento.tenant_id == usuario.tenant_id,
            BancoMovimiento.anulado_at.is_(None),
        )
    )
    if mov is None:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    # Solo movimientos manuales no conciliados (los de cheques se revierten por
    # el ciclo del cheque, no borrando el movimiento).
    if mov.origen != "manual":
        raise HTTPException(status_code=409, detail="Solo se borran movimientos manuales")
    if mov.conciliado:
        raise HTTPException(status_code=409, detail="Desconciliar antes de borrar")
    # 014: eliminar = marcar (queda como historia con fecha cierta)
    mov.anulado_at = datetime.now(timezone.utc)
    mov.anulado_por = usuario.id
    await db.commit()


# ===== Conciliación por import de extracto (CSV genérico) =====

def _parsear_extracto(contenido: bytes) -> list[dict]:
    """CSV genérico: columnas fecha;detalle;importe (importe firmado: negativo =
    débito). Detecta separador ; o , y encabezado. Fecha ISO o dd/mm/aaaa."""
    texto = contenido.decode("utf-8-sig", errors="replace")
    muestra = texto[:2000]
    sep = ";" if muestra.count(";") >= muestra.count(",") else ","
    filas = []
    reader = csv.reader(io.StringIO(texto), delimiter=sep)
    for i, campos in enumerate(reader):
        if len(campos) < 3:
            continue
        f_raw, detalle, imp_raw = campos[0].strip(), campos[1].strip(), campos[2].strip()
        # saltear encabezado
        if i == 0 and not any(c.isdigit() for c in f_raw):
            continue
        fecha = _parse_fecha(f_raw)
        importe = _parse_importe(imp_raw)
        if fecha is None or importe is None:
            continue
        filas.append({"fecha": fecha, "detalle": detalle, "importe": importe})
    return filas


def _parse_fecha(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_importe(s: str) -> Decimal | None:
    s = s.replace(" ", "")
    # es-AR: 1.234,56 → 1234.56 ; también acepta 1234.56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _tipo_por_signo(importe: Decimal) -> tuple[str, Decimal]:
    """Extracto trae importe firmado → (tipo, importe_positivo)."""
    if importe < 0:
        return "debito", -importe
    return "credito", importe


@router.post("/cuentas/{cuenta_id}/extracto/preview")
async def preview_extracto(
    cuenta_id: uuid.UUID,
    archivo: UploadFile,
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Parsea el CSV y propone, por cada fila, si matchea un movimiento no
    conciliado existente (misma fecha ±3 días e igual importe/signo). NO persiste."""
    await _cuenta(db, usuario.tenant_id, cuenta_id)
    filas = _parsear_extracto(await archivo.read())
    pendientes = (
        await db.scalars(
            select(BancoMovimiento).where(
                BancoMovimiento.cuenta_id == cuenta_id,
                BancoMovimiento.tenant_id == usuario.tenant_id,
                BancoMovimiento.conciliado.is_(False),
                BancoMovimiento.anulado_at.is_(None),
            )
        )
    ).all()
    propuestas = []
    usados: set[uuid.UUID] = set()
    for fila in filas:
        tipo, imp_pos = _tipo_por_signo(fila["importe"])
        match = None
        for m in pendientes:
            if m.id in usados:
                continue
            if Decimal(m.importe) == imp_pos and abs((m.fecha - fila["fecha"]).days) <= 3:
                match = m
                break
        if match:
            usados.add(match.id)
        propuestas.append(
            {
                "fecha": fila["fecha"].isoformat(),
                "detalle": fila["detalle"],
                "importe": str(fila["importe"]),
                "tipo": tipo,
                "match_movimiento_id": str(match.id) if match else None,
                "accion": "conciliar" if match else "crear",
            }
        )
    return {
        "cuenta_id": str(cuenta_id),
        "filas_total": len(propuestas),
        "con_match": sum(1 for p in propuestas if p["match_movimiento_id"]),
        "propuestas": propuestas,
    }


class ImportItemIn(BaseModel):
    fecha: date
    detalle: str | None = None
    importe: Decimal  # firmado
    tipo: str
    match_movimiento_id: uuid.UUID | None = None
    accion: str = Field(pattern="^(conciliar|crear|omitir)$")


class ImportIn(BaseModel):
    nombre_archivo: str | None = None
    items: list[ImportItemIn]


@router.post("/cuentas/{cuenta_id}/extracto/import", status_code=status.HTTP_201_CREATED)
async def import_extracto(
    cuenta_id: uuid.UUID,
    body: ImportIn,
    usuario: Usuario = Depends(requiere("bancos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Confirma el import: por cada item concilia el match o crea el movimiento."""
    await _cuenta(db, usuario.tenant_id, cuenta_id)
    imp = ExtractoImport(
        tenant_id=usuario.tenant_id,
        cuenta_id=cuenta_id,
        nombre_archivo=(body.nombre_archivo or "").strip() or None,
        filas_total=len(body.items),
        creado_por=usuario.id,
    )
    db.add(imp)
    await db.flush()
    conciliados = 0
    creados = 0
    for it in body.items:
        if it.accion == "omitir":
            continue
        if it.accion == "conciliar" and it.match_movimiento_id:
            mov = await db.scalar(
                select(BancoMovimiento).where(
                    BancoMovimiento.id == it.match_movimiento_id,
                    BancoMovimiento.cuenta_id == cuenta_id,
                    BancoMovimiento.tenant_id == usuario.tenant_id,
                    BancoMovimiento.anulado_at.is_(None),
                )
            )
            if mov and not mov.conciliado:
                mov.conciliado = True
                mov.fecha_conciliacion = it.fecha
                mov.extracto_import_id = imp.id
                conciliados += 1
        elif it.accion == "crear":
            tipo, imp_pos = _tipo_por_signo(it.importe)
            db.add(
                BancoMovimiento(
                    tenant_id=usuario.tenant_id,
                    cuenta_id=cuenta_id,
                    fecha=it.fecha,
                    tipo=tipo,
                    importe=imp_pos,
                    descripcion=(it.detalle or "").strip()[:120] or None,
                    conciliado=True,
                    fecha_conciliacion=it.fecha,
                    extracto_import_id=imp.id,
                    origen="import",
                    creado_por=usuario.id,
                )
            )
            creados += 1
    imp.filas_conciliadas = conciliados + creados
    await db.commit()
    return {"import_id": str(imp.id), "conciliados": conciliados, "creados": creados}


# ===== Export CSV de movimientos =====

@router.get("/cuentas/{cuenta_id}/movimientos/export.csv")
async def export_movimientos(
    cuenta_id: uuid.UUID,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(requiere("bancos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    await _cuenta(db, usuario.tenant_id, cuenta_id)
    stmt = select(BancoMovimiento).where(
        BancoMovimiento.cuenta_id == cuenta_id,
        BancoMovimiento.tenant_id == usuario.tenant_id,
        BancoMovimiento.anulado_at.is_(None),
    )
    if desde:
        stmt = stmt.where(BancoMovimiento.fecha >= desde)
    if hasta:
        stmt = stmt.where(BancoMovimiento.fecha <= hasta)
    filas = (await db.scalars(stmt.order_by(BancoMovimiento.fecha.asc()).limit(5000))).all()
    encabezado = ["Fecha", "Tipo", "Importe", "Signo", "Descripción", "Conciliado"]
    datos = [
        [
            m.fecha.isoformat(), m.tipo, num(m.importe), SIGNO_MOV.get(m.tipo, 1),
            m.descripcion or "", "Sí" if m.conciliado else "No",
        ]
        for m in filas
    ]
    return csv_response("movimientos_bancarios.csv", encabezado, datos)
