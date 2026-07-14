"""ABM de nodos de sucursal (F13-LAN N1 — DISENO-NODO-LAN.md §3).

Config sensible (`configuracion.editar`, como cajas POS y puntos de venta).
El token de aparejamiento se muestra UNA sola vez al crear/regenerar (patrón
reset-password de F6.5): acá solo persiste su hash bcrypt. Revocar deja el
nodo fuera de línea (el handshake responde 403) sin tocar sus datos locales.
"""

import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import PosCaja, PuntoVenta, Sucursal, SucursalNodo, Usuario
from app.services import auditoria

router = APIRouter(prefix="/nodos", tags=["nodos"])


class NodoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    sucursal_id: uuid.UUID
    sucursal_nombre: str | None = None
    punto_venta_id: uuid.UUID | None
    punto_venta_numero: int | None = None
    estado: str
    last_seen_at: datetime | None
    last_sync_at: datetime | None
    version_app: str | None
    # monitoreo N2 (lo reporta el ping del ciclo): 0 = al día
    subida_pendientes: int = 0
    cae_pendientes: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class NodoCreadoOut(NodoOut):
    # SOLO en la respuesta del alta/regeneración — no se puede volver a ver
    token: str


class NodoIn(BaseModel):
    sucursal_id: uuid.UUID
    nombre: str = Field(min_length=1, max_length=60)
    # PV propio del nodo para la facturación de gestión (§0-bis). Opcional:
    # sin PV el nodo solo opera las cajas POS de la sucursal.
    punto_venta_id: uuid.UUID | None = None


def _nuevo_token() -> str:
    return f"nodo_{secrets.token_urlsafe(32)}"


async def _out(db: AsyncSession, nodo: SucursalNodo) -> NodoOut:
    out = NodoOut.model_validate(nodo)
    out.sucursal_nombre = await db.scalar(
        select(Sucursal.nombre).where(Sucursal.id == nodo.sucursal_id)
    )
    if nodo.punto_venta_id:
        out.punto_venta_numero = await db.scalar(
            select(PuntoVenta.numero).where(PuntoVenta.id == nodo.punto_venta_id)
        )
    return out


@router.get("", response_model=list[NodoOut])
async def listar_nodos(
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    nodos = (
        await db.scalars(
            select(SucursalNodo)
            .where(SucursalNodo.tenant_id == usuario.tenant_id)
            .order_by(SucursalNodo.created_at)
        )
    ).all()
    return [await _out(db, n) for n in nodos]


@router.post("", response_model=NodoCreadoOut, status_code=status.HTTP_201_CREATED)
async def crear_nodo(
    body: NodoIn,
    request: Request,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    sucursal = await db.scalar(
        select(Sucursal).where(
            Sucursal.id == body.sucursal_id, Sucursal.tenant_id == usuario.tenant_id
        )
    )
    if sucursal is None:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    if body.punto_venta_id is not None:
        pv = await db.scalar(
            select(PuntoVenta).where(
                PuntoVenta.id == body.punto_venta_id,
                PuntoVenta.tenant_id == usuario.tenant_id,
            )
        )
        if pv is None:
            raise HTTPException(status_code=404, detail="Punto de venta no encontrado")
        usado_por_caja = await db.scalar(
            select(PosCaja.id).where(
                PosCaja.tenant_id == usuario.tenant_id,
                PosCaja.punto_venta_id == body.punto_venta_id,
                PosCaja.activa.is_(True),
            )
        )
        if usado_por_caja:
            raise HTTPException(
                status_code=422,
                detail="Ese punto de venta lo usa una caja POS — el PV propio del "
                "nodo debe ser distinto de los de las cajas",
            )
    activo = await db.scalar(
        select(SucursalNodo).where(
            SucursalNodo.sucursal_id == body.sucursal_id,
            SucursalNodo.estado == "activo",
        )
    )
    if activo is not None:
        raise HTTPException(
            status_code=409,
            detail=f"La sucursal ya tiene el nodo activo «{activo.nombre}» — revocalo primero",
        )
    token = _nuevo_token()
    nodo = SucursalNodo(
        tenant_id=usuario.tenant_id,
        sucursal_id=body.sucursal_id,
        nombre=body.nombre.strip(),
        token_hash=hash_password(token),
        punto_venta_id=body.punto_venta_id,
    )
    db.add(nodo)
    await db.flush()
    auditoria.registrar(
        db,
        tenant_id=usuario.tenant_id,
        accion="nodo_alta",
        usuario=usuario,
        ref_id=nodo.id,
        ref_texto=f"nodo {nodo.nombre} · sucursal {sucursal.nombre}",
        detalle={"sucursal_id": body.sucursal_id, "punto_venta_id": body.punto_venta_id},
        request=request,
    )
    await db.commit()
    out = NodoCreadoOut(**(await _out(db, nodo)).model_dump(), token=token)
    return out


@router.post("/{nodo_id}/revocar", response_model=NodoOut)
async def revocar_nodo(
    nodo_id: uuid.UUID,
    request: Request,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    nodo = await db.scalar(
        select(SucursalNodo).where(
            SucursalNodo.id == nodo_id, SucursalNodo.tenant_id == usuario.tenant_id
        )
    )
    if nodo is None:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    nodo.estado = "revocado"
    auditoria.registrar(
        db,
        tenant_id=usuario.tenant_id,
        accion="nodo_revocado",
        usuario=usuario,
        ref_id=nodo.id,
        ref_texto=f"nodo {nodo.nombre}",
        request=request,
    )
    await db.commit()
    return await _out(db, nodo)


@router.post("/{nodo_id}/regenerar-token", response_model=NodoCreadoOut)
async def regenerar_token(
    nodo_id: uuid.UUID,
    request: Request,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Invalida el token anterior (reinstalación del nodo). Solo nodos activos."""
    nodo = await db.scalar(
        select(SucursalNodo).where(
            SucursalNodo.id == nodo_id, SucursalNodo.tenant_id == usuario.tenant_id
        )
    )
    if nodo is None:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    if nodo.estado != "activo":
        raise HTTPException(status_code=422, detail="El nodo está revocado")
    token = _nuevo_token()
    nodo.token_hash = hash_password(token)
    auditoria.registrar(
        db,
        tenant_id=usuario.tenant_id,
        accion="nodo_token_regenerado",
        usuario=usuario,
        ref_id=nodo.id,
        ref_texto=f"nodo {nodo.nombre}",
        request=request,
    )
    await db.commit()
    return NodoCreadoOut(**(await _out(db, nodo)).model_dump(), token=token)
