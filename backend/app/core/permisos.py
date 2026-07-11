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
from app.models import Rol, RolPermiso, Tenant, Usuario

# Catálogo canónico de módulos (código estable: NUNCA se renombra en prod).
MODULOS: dict[str, str] = {
    "clientes": "Clientes",
    "ventas": "Ventas",
    "proveedores": "Proveedores",
    "compras": "Compras",
    "vendedores": "Vendedores",
    "articulos": "Artículos",
    "stock": "Stock",
    "caja": "Caja",
    "libros_iva": "Libros IVA",
    "pos": "POS",
    "bancos": "Bancos y Cheques",
    "contabilidad": "Contabilidad",
    "configuracion": "Configuración",
}

ACCIONES: dict[str, int] = {"ver": 1, "editar": 2, "anular": 3}

# Planes comerciales (F12-a, POS standalone — DISENO-POS-PERFILES.md §7).
# ESPEJO del CHECK de tenants.plan (migración 018): cambiar uno exige cambiar el otro.
# 'pos' = licencia solo-POS: el kiosco/carnicería/resto lleva stock, facturación,
# clientes y listados sin ver el resto de la suite. `caja` va incluida porque sin
# Compras es la única vía de registrar los gastos del día; `libros_iva` porque el
# IVA ventas al contador es argumento de venta. `configuracion` trae el gestor de
# usuarios/roles (F6.5) — el tenant POS-only administra su propia autenticación.
PLANES: dict[str, set[str]] = {
    "suite": set(MODULOS),
    "pos": {"pos", "articulos", "stock", "clientes", "ventas", "caja", "libros_iva", "configuracion"},
}

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
# Cache del plan por tenant (mismo criterio de TTL; el plan cambia por script/SQL,
# la ventana de 60s es aceptable).
_cache_plan: dict[uuid.UUID, tuple[float, str]] = {}


def invalidar_cache_permisos(rol_id: uuid.UUID | None = None) -> None:
    if rol_id is None:
        _cache.clear()
        _cache_plan.clear()
    else:
        _cache.pop(rol_id, None)


async def plan_del_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    hit = _cache_plan.get(tenant_id)
    if hit and hit[0] > time.monotonic():
        return hit[1]
    plan = await db.scalar(select(Tenant.plan).where(Tenant.id == tenant_id)) or "suite"
    _cache_plan[tenant_id] = (time.monotonic() + _CACHE_TTL, plan)
    return plan


def modulos_del_plan(plan: str) -> set[str]:
    """Módulos habilitados por el plan. Plan desconocido ⇒ suite (nunca bloquear
    por un valor viejo/nuevo no mapeado: el CHECK de la DB es la fuente de verdad)."""
    return PLANES.get(plan, set(MODULOS))


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
    """Mapa {modulo: nivel_maximo} del usuario = intersección PLAN ∩ ROL.

    Sin rol ⇒ acceso total DEL PLAN (compat scripts/seeds). Como el login devuelve
    este mapa y el nav del front se filtra por él, el plan recorta la UI solo."""
    modulos_plan = modulos_del_plan(await plan_del_tenant(db, usuario.tenant_id))
    base = dict(_TODO_ANULAR) if usuario.rol_id is None else await permisos_de_rol(db, usuario.rol_id)
    return {m: a for m, a in base.items() if m in modulos_plan}


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
        # Plan ANTES que rol: mensaje distinto (no es un problema de permisos del
        # usuario sino del plan contratado). Siempre 403, nunca 401 (regla §6).
        if modulo not in modulos_del_plan(await plan_del_tenant(db, usuario.tenant_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Módulo no incluido en el plan: {MODULOS[modulo]}",
            )
        if not _tiene(await permisos_efectivos(db, usuario), modulo, accion):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso: {MODULOS[modulo]} ({accion})",
            )
        return usuario

    return guard


def requiere_alguno(modulos: list[str], accion: str = "ver"):
    """Como `requiere`, pero alcanza con CUALQUIERA de los módulos (catálogos
    compartidos: entidades entre clientes/proveedores, puntos de venta, etc.).
    Los módulos fuera del plan del tenant no cuentan (basta que UNO esté en el
    plan y el rol lo tenga — ej.: entidades en plan `pos` pasa por clientes
    aunque proveedores quede afuera)."""
    if accion not in ACCIONES or any(m not in MODULOS for m in modulos):
        raise ValueError(f"Permiso inexistente: {modulos}.{accion}")

    async def guard(
        usuario: Usuario = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Usuario:
        del_plan = modulos_del_plan(await plan_del_tenant(db, usuario.tenant_id))
        if not any(m in del_plan for m in modulos):
            nombres = " / ".join(MODULOS[m] for m in modulos)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Módulo no incluido en el plan: {nombres}",
            )
        permisos = await permisos_efectivos(db, usuario)
        if not any(_tiene(permisos, m, accion) for m in modulos if m in del_plan):
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
