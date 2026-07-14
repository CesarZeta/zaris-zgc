"""Backup por tenant (F18 — DISENO-BACKUP-OBSERVABILIDAD.md §2.4).

Solo nube (ROUTERS_NUBE): el nodo es réplica, la fuente de verdad del tenant
es la base central. Guarda `configuracion.editar` — descargar TODO el tenant
es la lectura más sensible del sistema (mismo criterio que la config ARCA) —
y cada descarga queda auditada (`backup_descargado`).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere
from app.models import Usuario
from app.services import auditoria
from app.services.backup import generar_backup

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("/export.zip")
async def exportar_backup(
    request: Request,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    contenido, tablas, filas_total = await generar_backup(db, usuario.tenant_id)
    auditoria.registrar(
        db,
        tenant_id=usuario.tenant_id,
        accion="backup_descargado",
        usuario=usuario,
        ref_texto=f"{tablas} tablas, {filas_total} filas",
        detalle={"tablas": tablas, "filas_total": filas_total},
        request=request,
    )
    await db.commit()
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Response(
        content=contenido,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="backup-zgc-{fecha}.zip"'},
    )
