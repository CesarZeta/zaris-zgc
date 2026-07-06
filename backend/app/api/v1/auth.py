import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.db import get_db
from app.core.permisos import permisos_efectivos
from app.models import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    # str a propósito: el login matchea contra lo almacenado; la validación
    # estricta de email (EmailStr) corresponde al alta/edición de usuarios.
    email: str
    password: str


class UsuarioOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    nombre: str
    nivel_acceso: int
    rol_id: uuid.UUID | None
    sucursal_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UsuarioOut
    # {modulo: nivel_maximo} — el sidebar/UI se filtra con esto; el backend
    # igual verifica en cada endpoint (el frontend nunca es la única defensa).
    permisos: dict[str, str]


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    usuario = await db.scalar(select(Usuario).where(Usuario.email == body.email.lower()))
    if usuario is None or not usuario.activo or not verify_password(body.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos"
        )
    return LoginResponse(
        access_token=create_access_token(usuario),
        user=UsuarioOut.model_validate(usuario),
        permisos=await permisos_efectivos(db, usuario),
    )


@router.get("/me", response_model=UsuarioOut)
async def me(usuario: Usuario = Depends(get_current_user)):
    return UsuarioOut.model_validate(usuario)


@router.get("/permisos")
async def mis_permisos(
    usuario: Usuario = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Permisos efectivos del usuario logueado (para refrescar la UI sin re-login)."""
    return await permisos_efectivos(db, usuario)
