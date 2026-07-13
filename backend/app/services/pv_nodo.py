"""Exclusividad de puntos de venta del nodo LAN (F13-LAN — DISENO-NODO-LAN.md §3).

Mientras una sucursal tenga un nodo ACTIVO, su PV propio y los de sus cajas
POS numeran SOLO en el nodo — comprobantes Y recibos, que también numeran por
PV (si no, la secuencia colisiona al converger la subida). En el nodo rige la
inversa: solo se numera con los PV que le pertenecen. La comparten emitir_core
(comprobantes.py) y crear_recibo (cobranzas.py).
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import PosCaja, SucursalNodo


async def validar_pv_nodo(
    db: AsyncSession, tenant_id: uuid.UUID, punto_venta_id: uuid.UUID
) -> None:
    """422 si el PV no puede numerar en ESTA punta (nodo o nube)."""
    if settings.es_nodo:
        from app.services.sync_nodo import pvs_del_nodo

        pvs = await pvs_del_nodo(db)
        if pvs is None:
            raise HTTPException(
                status_code=422,
                detail="El nodo aún no sincronizó con la nube — sin contexto de aparejamiento",
            )
        if punto_venta_id not in pvs:
            raise HTTPException(
                status_code=422,
                detail="Ese punto de venta no pertenece a este nodo — usá el PV "
                "propio del nodo o el de una caja de la sucursal",
            )
        return
    nodo = await db.scalar(
        select(SucursalNodo)
        .where(
            SucursalNodo.tenant_id == tenant_id,
            SucursalNodo.estado == "activo",
            or_(
                SucursalNodo.punto_venta_id == punto_venta_id,
                SucursalNodo.sucursal_id.in_(
                    select(PosCaja.sucursal_id).where(
                        PosCaja.tenant_id == tenant_id,
                        PosCaja.punto_venta_id == punto_venta_id,
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


async def pvs_del_nodo_en_nube(db: AsyncSession, nodo: SucursalNodo) -> set[uuid.UUID]:
    """PVs que le pertenecen a un nodo, vistos DESDE LA NUBE (validación de la
    subida N2): su PV propio + los de las cajas POS de su sucursal. Incluye
    cajas inactivas: sus documentos históricos re-suben al mutar (anulación,
    CAE diferido) y no son una violación."""
    pvs: set[uuid.UUID] = set()
    if nodo.punto_venta_id:
        pvs.add(nodo.punto_venta_id)
    cajas = await db.scalars(
        select(PosCaja.punto_venta_id).where(
            PosCaja.tenant_id == nodo.tenant_id,
            PosCaja.sucursal_id == nodo.sucursal_id,
        )
    )
    pvs.update(cajas.all())
    return pvs
