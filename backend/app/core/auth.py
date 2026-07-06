import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models import Usuario

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(usuario: Usuario) -> str:
    payload = {
        "sub": str(usuario.id),
        "tenant_id": str(usuario.tenant_id),
        "nivel": usuario.nivel_acceso,
        "rol_id": str(usuario.rol_id) if usuario.rol_id else None,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    if credentials is None:
        raise exc
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise exc
    usuario = await db.scalar(select(Usuario).where(Usuario.id == user_id))
    if usuario is None or not usuario.activo:
        raise exc
    return usuario
