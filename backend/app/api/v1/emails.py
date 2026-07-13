"""Bandeja de salida de emails (F16 — DISENO-SALIDA-DOCUMENTOS.md §3).

Solo lectura: los envíos los crean los flujos (comprobantes, recuperación de
contraseña). Observabilidad del canal y, en modo simulado, la evidencia de
qué se "envió" (el detalle trae el cuerpo para reenviarlo a mano si hace
falta). Guarda `configuracion.ver`: es infraestructura del tenant, la ve
quien administra la configuración. Solo nube (ROUTERS_NUBE).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import EmailEnvio, Usuario

router = APIRouter(prefix="/emails", tags=["emails"])


class EnvioOut(BaseModel):
    id: uuid.UUID
    destinatario: str
    asunto: str
    tipo: str
    ref_id: uuid.UUID | None
    modo: str
    estado: str
    error: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class EnvioDetalleOut(EnvioOut):
    cuerpo: str | None


@router.get("/envios", response_model=list[EnvioOut])
async def listar_envios(
    response: Response,
    tipo: str | None = Query(None, pattern="^(comprobante|password_reset)$"),
    ref_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    filtro = [EmailEnvio.tenant_id == usuario.tenant_id]
    if tipo:
        filtro.append(EmailEnvio.tipo == tipo)
    if ref_id:
        filtro.append(EmailEnvio.ref_id == ref_id)
    total = await db.scalar(select(func.count()).select_from(EmailEnvio).where(*filtro))
    response.headers["X-Total-Count"] = str(total or 0)
    filas = await db.scalars(
        select(EmailEnvio)
        .where(*filtro)
        .order_by(EmailEnvio.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(filas)


@router.get("/envios/{envio_id}", response_model=EnvioDetalleOut)
async def detalle_envio(
    envio_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    envio = await db.scalar(
        select(EmailEnvio)
        .options(undefer(EmailEnvio.cuerpo))
        .where(EmailEnvio.id == envio_id, EmailEnvio.tenant_id == usuario.tenant_id)
    )
    if envio is None:
        raise HTTPException(status_code=404, detail="Envío no encontrado")
    return envio
