"""Sincronización nube → nodo (F13-LAN N1 — DISENO-NODO-LAN.md §5, bajada).

El nodo se autentica con su token de aparejamiento (handshake → JWT con
scope "nodo", que NO es una sesión de usuario: no pasa por get_current_user)
y baja los maestros por tabla con paginación keyset. La subida (cola de
eventos) es N2. Regla 401/403 de siempre: credencial inválida = 401; nodo
REVOCADO = 403 (autenticó, pero está fuera de línea a propósito).
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_password
from app.core.config import settings
from app.core.db import get_db
from app.models import PuntoVenta, Sucursal, SucursalNodo
from app.services.sync_tablas import (
    POR_NOMBRE,
    TABLAS_SYNC,
    TablaSync,
    columnas,
    fila_a_python,
    pk_columnas,
    serializar_fila,
)

router = APIRouter(prefix="/sync", tags=["sync"])

bearer_nodo = HTTPBearer(auto_error=False)

TOKEN_NODO_HORAS = 12
LIMITE_DEFAULT = 500
LIMITE_MAX = 2000


def _token_nodo(nodo: SucursalNodo) -> str:
    payload = {
        "nodo_id": str(nodo.id),
        "tenant_id": str(nodo.tenant_id),
        "scope": "nodo",
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_NODO_HORAS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


async def get_nodo(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_nodo),
    db: AsyncSession = Depends(get_db),
) -> SucursalNodo:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    if credentials is None:
        raise exc
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("scope") != "nodo":
            raise exc
        nodo_id = uuid.UUID(payload["nodo_id"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise exc
    nodo = await db.get(SucursalNodo, nodo_id)
    if nodo is None:
        raise exc
    if nodo.estado != "activo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nodo revocado")
    return nodo


class HandshakeIn(BaseModel):
    nodo_id: uuid.UUID
    token: str = Field(min_length=10)
    version_app: str | None = Field(None, max_length=20)


class HandshakeOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    scope: str = "nodo"
    nodo_nombre: str
    tenant_id: uuid.UUID
    sucursal_id: uuid.UUID
    sucursal_nombre: str | None
    punto_venta_id: uuid.UUID | None
    punto_venta_numero: int | None
    # informativo: qué replica esta versión de la nube (el nodo usa SU registro)
    tablas: list[dict]


@router.post("/handshake", response_model=HandshakeOut)
async def handshake(body: HandshakeIn, db: AsyncSession = Depends(get_db)):
    nodo = await db.get(SucursalNodo, body.nodo_id)
    if nodo is None or not verify_password(body.token, nodo.token_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Nodo o token inválidos"
        )
    if nodo.estado != "activo":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nodo revocado")
    nodo.last_seen_at = datetime.now(timezone.utc)
    if body.version_app:
        nodo.version_app = body.version_app
    sucursal_nombre = await db.scalar(
        select(Sucursal.nombre).where(Sucursal.id == nodo.sucursal_id)
    )
    pv_numero = None
    if nodo.punto_venta_id:
        pv_numero = await db.scalar(
            select(PuntoVenta.numero).where(PuntoVenta.id == nodo.punto_venta_id)
        )
    await db.commit()
    return HandshakeOut(
        access_token=_token_nodo(nodo),
        nodo_nombre=nodo.nombre,
        tenant_id=nodo.tenant_id,
        sucursal_id=nodo.sucursal_id,
        sucursal_nombre=sucursal_nombre,
        punto_venta_id=nodo.punto_venta_id,
        punto_venta_numero=pv_numero,
        tablas=[{"nombre": t.nombre, "modo": t.modo} for t in TABLAS_SYNC],
    )


def _cursor_a_tupla(t: TablaSync, cursor: str):
    """Cursor keyset (JSON) → tupla de valores Python tipados. Para
    incrementales es [updated_at_iso, id]; para snapshot/inicial, los PK."""
    try:
        valores = json.loads(cursor)
        if not isinstance(valores, list):
            raise ValueError
        if t.modo == "incremental":
            fila = fila_a_python(t.modelo, {"updated_at": valores[0], "id": valores[1]})
            return (fila["updated_at"], fila["id"])
        pks = pk_columnas(t.modelo)
        fila = fila_a_python(t.modelo, dict(zip(pks, valores, strict=True)))
        return tuple(fila[k] for k in pks)
    except (ValueError, KeyError, IndexError):
        raise HTTPException(status_code=422, detail="Cursor inválido")


@router.get("/bajada/{tabla}")
async def bajada(
    tabla: str,
    desde: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(LIMITE_DEFAULT, ge=1, le=LIMITE_MAX),
    nodo: SucursalNodo = Depends(get_nodo),
    db: AsyncSession = Depends(get_db),
):
    t = POR_NOMBRE.get(tabla)
    if t is None:
        raise HTTPException(status_code=404, detail=f"Tabla no replicable: {tabla}")
    modelo = t.modelo
    cols = columnas(modelo)
    stmt = select(modelo)
    if tabla == "tenants":
        stmt = stmt.where(modelo.id == nodo.tenant_id)
    elif not t.es_global:
        stmt = stmt.where(cols["tenant_id"] == nodo.tenant_id)

    if t.modo == "incremental":
        orden = (cols["updated_at"], cols["id"])
        if desde is not None:
            # >= y no >: la fila tocada en el MISMO instante del checkpoint no
            # se pierde; el upsert del nodo es idempotente ante el solape
            stmt = stmt.where(cols["updated_at"] >= desde)
    else:
        orden = tuple(cols[k] for k in pk_columnas(modelo))
    if cursor is not None:
        stmt = stmt.where(tuple_(*orden) > _cursor_a_tupla(t, cursor))
    stmt = stmt.order_by(*orden).limit(limit)

    objetos = (await db.scalars(stmt)).all()
    filas = [serializar_fila(modelo, o) for o in objetos]
    cursor_sig = None
    if len(filas) == limit:
        ultima = filas[-1]
        if t.modo == "incremental":
            cursor_sig = json.dumps([ultima["updated_at"], ultima["id"]])
        else:
            cursor_sig = json.dumps([ultima[k] for k in pk_columnas(modelo)])
    return {"tabla": tabla, "modo": t.modo, "filas": filas, "cursor": cursor_sig}


class PingIn(BaseModel):
    tablas: int = 0
    filas: int = 0
    version_app: str | None = Field(None, max_length=20)


@router.post("/ping", status_code=status.HTTP_204_NO_CONTENT)
async def ping(
    body: PingIn,
    nodo: SucursalNodo = Depends(get_nodo),
    db: AsyncSession = Depends(get_db),
):
    """Cierre de ciclo de réplica: monitoreo del nodo en Configuración."""
    ahora = datetime.now(timezone.utc)
    nodo.last_seen_at = ahora
    nodo.last_sync_at = ahora
    if body.version_app:
        nodo.version_app = body.version_app
    await db.commit()
