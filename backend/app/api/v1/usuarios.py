"""Gestor de usuarios, roles y matriz de permisos (módulo Configuración).

Diseño: docs/DISENO-USUARIOS-Y-PERMISOS.md §6. Solo accesible con permisos
sobre el módulo `configuracion` (ver = consultar, editar = administrar).

Regla anti-lockout (§8): ninguna operación puede dejar al tenant sin al menos
un usuario ACTIVO con `configuracion.editar` (o sin rol = acceso total).
"""

import re
import secrets
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.db import get_db
from app.core.permisos import (
    ACCIONES,
    MODULOS,
    invalidar_cache_permisos,
    requiere,
    sembrar_roles_base,
)
from app.models import Rol, RolPermiso, Usuario

router = APIRouter(tags=["usuarios y permisos"])


# ===== Schemas =====


class RolOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    es_sistema: bool
    activo: bool
    permisos: dict[str, str]
    usuarios: int  # cuántos usuarios del tenant lo tienen asignado


class RolCrearIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    # accion None = quitar el módulo (útil combinado con clonar_de)
    permisos: dict[str, str | None] = Field(default_factory=dict)
    clonar_de: uuid.UUID | None = None  # copia la matriz de otro rol del tenant


class RolEditarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=60)
    activo: bool | None = None


class PermisosIn(BaseModel):
    # {modulo: accion} — módulo ausente o accion null = sin acceso
    permisos: dict[str, str | None]


class UsuarioAdminOut(BaseModel):
    id: uuid.UUID
    email: str
    nombre: str
    nivel_acceso: int
    rol_id: uuid.UUID | None
    sucursal_id: uuid.UUID | None
    activo: bool

    model_config = {"from_attributes": True}


class UsuarioCrearIn(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=72)
    rol_id: uuid.UUID
    # 1=admin, 2=supervisor (autoriza anulaciones POS), 3+=operador — solo POS
    nivel_acceso: int = Field(default=3, ge=1, le=9)
    sucursal_id: uuid.UUID | None = None


class UsuarioEditarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    rol_id: uuid.UUID | None = None
    nivel_acceso: int | None = Field(default=None, ge=1, le=9)
    sucursal_id: uuid.UUID | None = None
    activo: bool | None = None


# ===== Helpers =====


def _validar_permisos(permisos: dict[str, str | None]) -> dict[str, str]:
    limpios: dict[str, str] = {}
    for modulo, accion in permisos.items():
        if modulo not in MODULOS:
            raise HTTPException(422, detail=f"Módulo inexistente: {modulo}")
        if accion is None:
            continue
        if accion not in ACCIONES:
            raise HTTPException(422, detail=f"Acción inválida: {accion} (ver/editar/anular)")
        limpios[modulo] = accion
    return limpios


async def _rol_del_tenant(db: AsyncSession, tenant_id: uuid.UUID, rol_id: uuid.UUID) -> Rol:
    rol = await db.scalar(select(Rol).where(Rol.id == rol_id, Rol.tenant_id == tenant_id))
    if rol is None:
        raise HTTPException(404, detail="Rol inexistente")
    return rol


async def _verificar_no_lockout(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Tras flush: debe quedar ≥1 usuario activo con configuracion.editar
    (rol_id NULL cuenta: es acceso total)."""
    con_admin = await db.scalar(
        select(func.count())
        .select_from(Usuario)
        .outerjoin(
            RolPermiso,
            (RolPermiso.rol_id == Usuario.rol_id)
            & (RolPermiso.modulo == "configuracion")
            & (RolPermiso.accion.in_(["editar", "anular"])),
        )
        .where(
            Usuario.tenant_id == tenant_id,
            Usuario.activo.is_(True),
            (Usuario.rol_id.is_(None)) | (RolPermiso.rol_id.is_not(None)),
        )
    )
    if not con_admin:
        raise HTTPException(
            422,
            detail="La operación dejaría al tenant sin ningún usuario activo que pueda "
            "administrar Configuración. Asigná antes ese permiso a otro usuario.",
        )


# ===== Catálogo (para armar la matriz en la UI) =====


@router.get("/permisos/catalogo")
async def catalogo_permisos(usuario: Usuario = Depends(requiere("configuracion", "ver"))):
    return {
        "modulos": [{"codigo": c, "nombre": n} for c, n in MODULOS.items()],
        "acciones": list(ACCIONES),
    }


# ===== Roles =====


async def _roles_out(db: AsyncSession, tenant_id: uuid.UUID) -> list[RolOut]:
    roles = (
        await db.scalars(
            select(Rol).where(Rol.tenant_id == tenant_id).order_by(Rol.es_sistema.desc(), Rol.nombre)
        )
    ).all()
    permisos = (
        await db.execute(
            select(RolPermiso.rol_id, RolPermiso.modulo, RolPermiso.accion).where(
                RolPermiso.tenant_id == tenant_id
            )
        )
    ).all()
    usuarios_por_rol = dict(
        (
            await db.execute(
                select(Usuario.rol_id, func.count())
                .where(Usuario.tenant_id == tenant_id, Usuario.rol_id.is_not(None))
                .group_by(Usuario.rol_id)
            )
        ).all()
    )
    por_rol: dict[uuid.UUID, dict[str, str]] = {}
    for rol_id, modulo, accion in permisos:
        por_rol.setdefault(rol_id, {})[modulo] = accion
    return [
        RolOut(
            id=r.id,
            codigo=r.codigo,
            nombre=r.nombre,
            es_sistema=r.es_sistema,
            activo=r.activo,
            permisos=por_rol.get(r.id, {}),
            usuarios=usuarios_por_rol.get(r.id, 0),
        )
        for r in roles
    ]


@router.get("/roles", response_model=list[RolOut])
async def listar_roles(
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    # Lazy-seed: un tenant nuevo (creado por script/SQL) recibe los roles base acá.
    if await sembrar_roles_base(db, usuario.tenant_id):
        await db.commit()
    return await _roles_out(db, usuario.tenant_id)


@router.post("/roles", response_model=list[RolOut], status_code=status.HTTP_201_CREATED)
async def crear_rol(
    body: RolCrearIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    _validar_permisos(body.permisos)  # valida módulos/acciones (None = quitar)
    permisos: dict[str, str] = {}
    if body.clonar_de:
        origen = await _rol_del_tenant(db, usuario.tenant_id, body.clonar_de)
        filas = (
            await db.execute(
                select(RolPermiso.modulo, RolPermiso.accion).where(RolPermiso.rol_id == origen.id)
            )
        ).all()
        permisos = {modulo: accion for modulo, accion in filas}
    for modulo, accion in body.permisos.items():  # overlay sobre el clon
        if accion is None:
            permisos.pop(modulo, None)
        else:
            permisos[modulo] = accion

    codigo = re.sub(r"[^a-z0-9]+", "_", body.nombre.lower()).strip("_")[:30] or "rol"
    existentes = {
        r for (r,) in (
            await db.execute(select(Rol.codigo).where(Rol.tenant_id == usuario.tenant_id))
        ).all()
    }
    if codigo in existentes:
        sufijo = 2
        while f"{codigo[:27]}_{sufijo}" in existentes:
            sufijo += 1
        codigo = f"{codigo[:27]}_{sufijo}"

    rol = Rol(tenant_id=usuario.tenant_id, codigo=codigo, nombre=body.nombre, es_sistema=False)
    db.add(rol)
    await db.flush()
    for modulo, accion in permisos.items():
        db.add(RolPermiso(rol_id=rol.id, tenant_id=usuario.tenant_id, modulo=modulo, accion=accion))
    await db.commit()
    return await _roles_out(db, usuario.tenant_id)


@router.put("/roles/{rol_id}", response_model=list[RolOut])
async def editar_rol(
    rol_id: uuid.UUID,
    body: RolEditarIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    rol = await _rol_del_tenant(db, usuario.tenant_id, rol_id)
    if rol.es_sistema:
        raise HTTPException(422, detail="Los roles de sistema no se editan; cloná uno propio.")
    if body.nombre is not None:
        rol.nombre = body.nombre
    if body.activo is not None:
        rol.activo = body.activo
    await db.commit()
    return await _roles_out(db, usuario.tenant_id)


@router.put("/roles/{rol_id}/permisos", response_model=list[RolOut])
async def guardar_permisos(
    rol_id: uuid.UUID,
    body: PermisosIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    rol = await _rol_del_tenant(db, usuario.tenant_id, rol_id)
    if rol.es_sistema:
        raise HTTPException(422, detail="Los roles de sistema no se editan; cloná uno propio.")
    nuevos = _validar_permisos(body.permisos)

    actuales = (await db.scalars(select(RolPermiso).where(RolPermiso.rol_id == rol.id))).all()
    por_modulo = {p.modulo: p for p in actuales}
    for modulo, fila in por_modulo.items():
        if modulo not in nuevos:
            await db.delete(fila)
    for modulo, accion in nuevos.items():
        if modulo in por_modulo:
            por_modulo[modulo].accion = accion
        else:
            db.add(RolPermiso(rol_id=rol.id, tenant_id=usuario.tenant_id, modulo=modulo, accion=accion))

    await db.flush()
    await _verificar_no_lockout(db, usuario.tenant_id)
    await db.commit()
    invalidar_cache_permisos(rol.id)
    return await _roles_out(db, usuario.tenant_id)


@router.delete("/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_rol(
    rol_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    rol = await _rol_del_tenant(db, usuario.tenant_id, rol_id)
    if rol.es_sistema:
        raise HTTPException(422, detail="Los roles de sistema no se borran.")
    asignados = await db.scalar(
        select(func.count()).select_from(Usuario).where(Usuario.rol_id == rol.id)
    )
    if asignados:
        raise HTTPException(422, detail=f"El rol tiene {asignados} usuario(s) asignado(s).")
    await db.delete(rol)
    await db.commit()
    invalidar_cache_permisos(rol.id)


# ===== Usuarios =====


@router.get("/usuarios", response_model=list[UsuarioAdminOut])
async def listar_usuarios(
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas = (
        await db.scalars(
            select(Usuario).where(Usuario.tenant_id == usuario.tenant_id).order_by(Usuario.email)
        )
    ).all()
    return [UsuarioAdminOut.model_validate(u) for u in filas]


@router.post("/usuarios", response_model=UsuarioAdminOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    body: UsuarioCrearIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    email = body.email.lower()
    if await db.scalar(select(Usuario).where(Usuario.email == email)):
        raise HTTPException(422, detail="Ya existe un usuario con ese email.")
    rol = await _rol_del_tenant(db, usuario.tenant_id, body.rol_id)
    if not rol.activo:
        raise HTTPException(422, detail="El rol está inactivo.")
    nuevo = Usuario(
        tenant_id=usuario.tenant_id,
        email=email,
        nombre=body.nombre,
        password_hash=hash_password(body.password),
        nivel_acceso=body.nivel_acceso,
        rol_id=rol.id,
        sucursal_id=body.sucursal_id,
    )
    db.add(nuevo)
    await db.commit()
    return UsuarioAdminOut.model_validate(nuevo)


@router.put("/usuarios/{usuario_id}", response_model=UsuarioAdminOut)
async def editar_usuario(
    usuario_id: uuid.UUID,
    body: UsuarioEditarIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    objetivo = await db.scalar(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == usuario.tenant_id)
    )
    if objetivo is None:
        raise HTTPException(404, detail="Usuario inexistente")
    if body.nombre is not None:
        objetivo.nombre = body.nombre
    if body.rol_id is not None:
        rol = await _rol_del_tenant(db, usuario.tenant_id, body.rol_id)
        if not rol.activo:
            raise HTTPException(422, detail="El rol está inactivo.")
        objetivo.rol_id = rol.id
    if body.nivel_acceso is not None:
        objetivo.nivel_acceso = body.nivel_acceso
    if body.sucursal_id is not None:
        objetivo.sucursal_id = body.sucursal_id
    if body.activo is not None:
        objetivo.activo = body.activo

    await db.flush()
    await _verificar_no_lockout(db, usuario.tenant_id)
    await db.commit()
    return UsuarioAdminOut.model_validate(objetivo)


@router.post("/usuarios/{usuario_id}/reset-password")
async def resetear_password(
    usuario_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Genera una contraseña nueva y la devuelve UNA vez (no se puede recuperar
    la almacenada: bcrypt es irreversible)."""
    objetivo = await db.scalar(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == usuario.tenant_id)
    )
    if objetivo is None:
        raise HTTPException(404, detail="Usuario inexistente")
    # sin caracteres ambiguos (0/O, 1/l/I) — se dicta por teléfono
    alfabeto = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
    password = "".join(secrets.choice(alfabeto) for _ in range(10))
    objetivo.password_hash = hash_password(password)
    await db.commit()
    return {"password": password}
