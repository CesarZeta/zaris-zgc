"""Padrón ARCA por CUIT (Fase 7): autocompletar entidades BUE + validar
condición IVA. Guardado por clientes/proveedores (los que dan de alta entidades)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere_alguno
from app.models import ArcaConfig, Usuario
from app.services.arca import padron

router = APIRouter(prefix="/padron", tags=["padron"])


class PadronOut(BaseModel):
    cuit: str
    razon_social: str | None
    tipo_persona: str
    condicion_iva: str
    domicilio: str | None
    localidad: str | None
    provincia_id: int | None
    codigo_postal: str | None
    fuente: str
    desde_cache: bool = False


@router.get("/{cuit}", response_model=PadronOut)
async def consultar_padron(
    cuit: str,
    usuario: Usuario = Depends(requiere_alguno(["clientes", "proveedores"], "editar")),
    db: AsyncSession = Depends(get_db),
):
    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )
    try:
        datos = await padron.consultar_cuit(db, config, cuit)
    except ValueError as e:  # CUIT inválido (dígito verificador)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except padron.ErrorPadron as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await db.commit()  # persiste el TA cacheado si se pidió uno nuevo
    return PadronOut(**datos.__dict__)
