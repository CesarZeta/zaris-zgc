"""Consulta del registro de auditoría (F17 — DISENO-AUDITORIA.md §5).

Solo lectura: los eventos los crean los flujos instrumentados vía
`services/auditoria.registrar`. No hay UPDATE/DELETE — el registro es inmutable
por construcción. Guarda `configuracion.ver` (precedente: bandeja de emails
F16 — infraestructura del tenant, la ve quien administra la configuración).
Solo nube (ROUTERS_NUBE); la auditoría local del nodo queda en el nodo (v1).
"""

import json
import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csv_export import csv_response
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import AuditEvento, Usuario
from app.services.auditoria import ACCIONES_AUDIT

router = APIRouter(prefix="/auditoria", tags=["auditoria"])

MODULOS_AUDIT = sorted({m for m, _ in ACCIONES_AUDIT.values()})


class EventoOut(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID | None
    usuario_email: str | None
    accion: str
    modulo: str
    ref_id: uuid.UUID | None
    ref_texto: str | None
    detalle: dict | None
    ip: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


def _filtro(
    usuario: Usuario,
    accion: str | None,
    modulo: str | None,
    usuario_id: uuid.UUID | None,
    desde: date | None,
    hasta: date | None,
    q: str | None,
) -> list:
    filtro = [AuditEvento.tenant_id == usuario.tenant_id]
    if accion:
        filtro.append(AuditEvento.accion == accion)
    if modulo:
        filtro.append(AuditEvento.modulo == modulo)
    if usuario_id:
        filtro.append(AuditEvento.usuario_id == usuario_id)
    if desde:
        filtro.append(AuditEvento.created_at >= datetime.combine(desde, time.min, timezone.utc))
    if hasta:
        filtro.append(AuditEvento.created_at <= datetime.combine(hasta, time.max, timezone.utc))
    if q and q.strip():
        patron = f"%{q.strip()}%"
        filtro.append(
            or_(AuditEvento.usuario_email.ilike(patron), AuditEvento.ref_texto.ilike(patron))
        )
    return filtro


@router.get("/catalogo")
async def catalogo(
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
) -> dict:
    """Acciones auditables con etiqueta humana (para el filtro del front)."""
    return {
        "acciones": [
            {"codigo": codigo, "modulo": modulo, "etiqueta": etiqueta}
            for codigo, (modulo, etiqueta) in ACCIONES_AUDIT.items()
        ],
        "modulos": MODULOS_AUDIT,
    }


# Ruta estática ANTES que cualquier paramétrica (regla §6 del CLAUDE.md)
@router.get("/export.csv")
async def exportar_csv(
    accion: str | None = None,
    modulo: str | None = None,
    usuario_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas_db = (
        await db.scalars(
            select(AuditEvento)
            .where(*_filtro(usuario, accion, modulo, usuario_id, desde, hasta, q))
            .order_by(AuditEvento.created_at.desc())
            .limit(5000)
        )
    ).all()
    filas = [
        [
            e.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            e.usuario_email or "",
            e.accion,
            ACCIONES_AUDIT.get(e.accion, (e.modulo, e.accion))[1],
            e.modulo,
            e.ref_texto or "",
            json.dumps(e.detalle, ensure_ascii=False) if e.detalle else "",
            e.ip or "",
        ]
        for e in filas_db
    ]
    return csv_response(
        "auditoria.csv",
        ["Fecha (UTC)", "Usuario", "Acción", "Descripción", "Módulo", "Referencia", "Detalle", "IP"],
        filas,
    )


@router.get("/eventos", response_model=list[EventoOut])
async def listar_eventos(
    response: Response,
    accion: str | None = None,
    modulo: str | None = None,
    usuario_id: uuid.UUID | None = None,
    ref_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    if accion is not None and accion not in ACCIONES_AUDIT:
        raise HTTPException(status_code=422, detail="Acción desconocida")
    filtro = _filtro(usuario, accion, modulo, usuario_id, desde, hasta, q)
    if ref_id:
        filtro.append(AuditEvento.ref_id == ref_id)
    total = await db.scalar(select(func.count()).select_from(AuditEvento).where(*filtro))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        select(AuditEvento)
        .where(*filtro)
        .order_by(AuditEvento.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(filas)
