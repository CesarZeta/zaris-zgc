"""Permisos por módulo (RBAC de Fase 6.5) — diseño en docs/DISENO-USUARIOS-Y-PERMISOS.md.

Modelo: rol por usuario + una fila (rol, módulo) con el nivel MÁXIMO alcanzado.
Niveles acumulativos: anular ⇒ editar ⇒ ver. Ausencia de fila = sin acceso.

Compatibilidad (aditivo, no rompe nada de hoy):
- `usuario.rol_id IS NULL` ⇒ acceso total. Cubre usuarios creados por scripts/SQL
  (seeds, smoke tenants) y el período entre migración y asignación de roles.
- `usuarios.nivel_acceso` NO participa acá: sigue gobernando SOLO la autorización
  de supervisor del POS (anulaciones con credenciales embebidas, pos.py).

La guarda devuelve 403 (nunca 401: el interceptor del frontend trata 401 como
sesión vencida y desloguea — CLAUDE.md §6).
"""

import time
import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import Rol, RolPermiso, Usuario

# Catálogo canónico de módulos (código estable: NUNCA se renombra en prod).
MODULOS: dict[str, str] = {
    "clientes": "Clientes",
    "ventas": "Ventas",
    "proveedores": "Proveedores",
    "compras": "Compras",
    "articulos": "Artículos",
    "stock": "Stock",
    "caja": "Caja",
    "libros_iva": "Libros IVA",
    "pos": "POS",
    "bancos": "Bancos y Cheques",
    "configuracion": "Configuración",
}

ACCIONES: dict[str, int] = {"ver": 1, "editar": 2, "anular": 3}

_TODO_ANULAR: dict[str, str] = {m: "anular" for m in MODULOS}

# Roles base sembrados por tenant (es_sistema=true). Espejo del seed de la
# migración 010 — cambiar acá exige migración de datos para tenants existentes.
ROLES_BASE: list[tuple[str, str, dict[str, str]]] = [
    ("admin", "Administrador", dict(_TODO_ANULAR)),
    (
        "gerente",
        "Gerente",
        {**{m: "anular" for m in MODULOS if m != "configuracion"}, "configuracion": "ver"},
    ),
    (
        "cajero",
        "Cajero",
        {
            "ventas": "editar",
            "caja": "editar",
            "pos": "editar",
            "clientes": "editar",
            "bancos": "editar",
            "articulos": "ver",
            "stock": "ver",
        },
    ),
    (
        "vendedor",
        "Vendedor",
        {"ventas": "editar", "clientes": "editar", "articulos": "ver", "stock": "ver"},
    ),
    ("consulta", "Consulta", {m: "ver" for m in MODULOS if m != "configuracion"}),
]

# Cache in-process de permisos por rol (TTL corto). En Vercel serverless el
# proceso es efímero; en dev/nodo el TTL acota la ventana de staleness tras
# editar la matriz desde otra instancia.
_CACHE_TTL = 60.0
_cache: dict[uuid.UUID, tuple[float, dict[str, str]]] = {}


def invalidar_cache_permisos(rol_id: uuid.UUID | None = None) -> None:
    if rol_id is None:
        _cache.clear()
    else:
        _cache.pop(rol_id, None)


async def permisos_de_rol(db: AsyncSession, rol_id: uuid.UUID) -> dict[str, str]:
    hit = _cache.get(rol_id)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    filas = (
        await db.execute(select(RolPermiso.modulo, RolPermiso.accion).where(RolPermiso.rol_id == rol_id))
    ).all()
    permisos = {modulo: accion for modulo, accion in filas}
    _cache[rol_id] = (time.monotonic() + _CACHE_TTL, permisos)
    return permisos


async def permisos_efectivos(db: AsyncSession, usuario: Usuario) -> dict[str, str]:
    """Mapa {modulo: nivel_maximo} del usuario. Sin rol ⇒ acceso total (compat)."""
    if usuario.rol_id is None:
        return dict(_TODO_ANULAR)
    return await permisos_de_rol(db, usuario.rol_id)


def _tiene(permisos: dict[str, str], modulo: str, accion: str) -> bool:
    nivel = permisos.get(modulo)
    return nivel is not None and ACCIONES[nivel] >= ACCIONES[accion]


def requiere(modulo: str, accion: str = "ver"):
    """Dependency de FastAPI: exige `accion` sobre `modulo` o responde 403."""
    if modulo not in MODULOS or accion not in ACCIONES:  # typo = error al importar
        raise ValueError(f"Permiso inexistente: {modulo}.{accion}")

    async def guard(
        usuario: Usuario = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Usuario:
        if not _tiene(await permisos_efectivos(db, usuario), modulo, accion):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso: {MODULOS[modulo]} ({accion})",
            )
        return usuario

    return guard


def requiere_alguno(modulos: list[str], accion: str = "ver"):
    """Como `requiere`, pero alcanza con CUALQUIERA de los módulos (catálogos
    compartidos: entidades entre clientes/proveedores, puntos de venta, etc.)."""
    if accion not in ACCIONES or any(m not in MODULOS for m in modulos):
        raise ValueError(f"Permiso inexistente: {modulos}.{accion}")

    async def guard(
        usuario: Usuario = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Usuario:
        permisos = await permisos_efectivos(db, usuario)
        if not any(_tiene(permisos, m, accion) for m in modulos):
            nombres = " / ".join(MODULOS[m] for m in modulos)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso: {nombres} ({accion})",
            )
        return usuario

    return guard


async def sembrar_roles_base(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Siembra los roles base del tenant (idempotente, sin commit). Devuelve
    cuántos roles creó. La migración 010 cubre los tenants existentes; esto
    cubre tenants nuevos (lazy en GET /roles y disponible para tools)."""
    existentes = {
        r.codigo
        for r in (await db.scalars(select(Rol).where(Rol.tenant_id == tenant_id))).all()
    }
    creados = 0
    for codigo, nombre, permisos in ROLES_BASE:
        if codigo in existentes:
            continue
        rol = Rol(tenant_id=tenant_id, codigo=codigo, nombre=nombre, es_sistema=True)
        db.add(rol)
        await db.flush()
        for modulo, accion in permisos.items():
            db.add(RolPermiso(rol_id=rol.id, tenant_id=tenant_id, modulo=modulo, accion=accion))
        creados += 1
    return creados
