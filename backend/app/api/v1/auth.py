import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user, hash_password, verify_password
from app.core.config import settings
from app.core.db import get_db
from app.core.permisos import permisos_efectivos
from app.models import PasswordReset, Usuario
from app.services.email_envio import EmailDeshabilitadoError, ErrorEnvioEmail, enviar_email

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


# ===== Recuperación de contraseña autoservicio (F16 — DISENO-SALIDA-DOCUMENTOS.md §5) =====

RECUPERAR_MENSAJE = (
    "Si el email está registrado, te enviamos un enlace para restablecer la contraseña"
)


class RecuperarIn(BaseModel):
    email: str


class RestablecerIn(BaseModel):
    token: str = Field(min_length=20, max_length=100)
    password: str = Field(min_length=6, max_length=72)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/recuperar")
async def recuperar_password(body: RecuperarIn, db: AsyncSession = Depends(get_db)):
    """Público. Responde SIEMPRE el mismo 200 (no filtra si el email existe).
    Con usuario válido: invalida tokens pendientes, crea uno nuevo (1 h) y
    manda el email con el link — en modo simulado queda en `email_envios`."""
    usuario = await db.scalar(select(Usuario).where(Usuario.email == body.email.lower()))
    if usuario is None or not usuario.activo:
        return {"detail": RECUPERAR_MENSAJE}

    ahora = datetime.now(timezone.utc)
    await db.execute(
        update(PasswordReset)
        .where(PasswordReset.usuario_id == usuario.id, PasswordReset.usado_at.is_(None))
        .values(usado_at=ahora)
    )
    token = secrets.token_urlsafe(32)
    db.add(
        PasswordReset(
            tenant_id=usuario.tenant_id,
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            expira_at=ahora + timedelta(hours=1),
        )
    )
    link = f"{settings.APP_URL.rstrip('/')}/restablecer?token={token}"
    cuerpo = (
        f"<p>Hola {usuario.nombre},</p>"
        f"<p>Pediste restablecer tu contraseña de ZARIS. El enlace vale por 1 hora:</p>"
        f'<p><a href="{link}">{link}</a></p>'
        f"<p>Si no fuiste vos, ignorá este mensaje — tu contraseña sigue igual.</p>"
        f"<p style='color:#777;font-size:12px'>ZARIS Gestión Comercial.</p>"
    )
    try:
        await enviar_email(
            db,
            usuario.tenant_id,
            destinatario=usuario.email,
            asunto="Restablecé tu contraseña de ZARIS",
            cuerpo_html=cuerpo,
            tipo="password_reset",
            ref_id=usuario.id,
        )
    except EmailDeshabilitadoError:
        # el modo es global: el 400 no filtra existencia de usuarios
        raise HTTPException(
            status_code=400,
            detail="El envío de emails está deshabilitado — pedile el reset a un administrador",
        )
    except ErrorEnvioEmail:
        # la evidencia del error se comitea; la respuesta NO cambia (no filtrar)
        await db.commit()
        return {"detail": RECUPERAR_MENSAJE}
    await db.commit()
    return {"detail": RECUPERAR_MENSAJE}


@router.post("/restablecer")
async def restablecer_password(body: RestablecerIn, db: AsyncSession = Depends(get_db)):
    """Público. Consume el token (un solo uso) y fija la contraseña nueva."""
    reset = await db.scalar(
        select(PasswordReset).where(PasswordReset.token_hash == _hash_token(body.token))
    )
    ahora = datetime.now(timezone.utc)
    if reset is None or reset.usado_at is not None or reset.expira_at < ahora:
        raise HTTPException(
            status_code=422, detail="Enlace inválido o vencido — pedí uno nuevo desde el login"
        )
    usuario = await db.scalar(select(Usuario).where(Usuario.id == reset.usuario_id))
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=422, detail="Enlace inválido o vencido — pedí uno nuevo desde el login"
        )
    usuario.password_hash = hash_password(body.password)
    reset.usado_at = ahora
    await db.commit()
    return {"detail": "Contraseña actualizada — ya podés ingresar"}
