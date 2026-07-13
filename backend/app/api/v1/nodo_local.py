"""Endpoints LOCALES del nodo de sucursal (solo se montan con PERFIL=nodo).

Estado de la réplica para la pantalla de la caja / diagnóstico en la LAN, y
disparo manual de un ciclo (lo usan la instalación y la suite de pruebas).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.permisos import requiere_alguno
from app.models import SyncCheckpoint, Usuario
from app.services.sync_nodo import (
    VERSION_APP,
    ciclo_sync,
    contar_cae_pendientes,
    contar_subida_pendiente,
    contexto_nodo,
    estado_sync,
)

router = APIRouter(prefix="/nodo", tags=["nodo"])


@router.get("/estado")
async def estado_nodo(
    usuario: Usuario = Depends(requiere_alguno(["pos", "configuracion"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    checkpoints = (
        await db.scalars(select(SyncCheckpoint).order_by(SyncCheckpoint.tabla))
    ).all()
    return {
        "version_app": VERSION_APP,
        "nube_url": settings.NUBE_URL,
        "intervalo_seg": settings.SYNC_INTERVALO_SEG,
        "contexto": await contexto_nodo(db),
        "ciclos_ok": estado_sync["ciclos_ok"],
        "ultimo_ok": estado_sync["ultimo_ok"],
        "ultimo_error": estado_sync["ultimo_error"],
        # N2: atraso local (0 = al día con la nube / sin CAE esperando)
        "subida_pendientes": await contar_subida_pendiente(db),
        "cae_pendientes": await contar_cae_pendientes(db),
        "checkpoints": [
            {
                "tabla": c.tabla,
                "hasta": c.hasta.isoformat() if c.hasta else None,
                "filas": c.filas,
                "actualizado_at": c.actualizado_at.isoformat(),
            }
            for c in checkpoints
            if c.tabla != "_nodo"
        ],
    }


@router.post("/sync-ahora")
async def sync_ahora(
    usuario: Usuario = Depends(requiere_alguno(["pos", "configuracion"], "ver")),
):
    """Ciclo de réplica bajo demanda (además del polling de fondo)."""
    try:
        resumen = await ciclo_sync()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Sync falló: {e}")
    estado_sync["ciclos_ok"] += 1
    return {"ok": True, **resumen}
