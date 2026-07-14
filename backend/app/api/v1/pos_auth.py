"""Login POS dedicado (adelanto de F13-LAN — DISENO-NODO-LAN.md §4).

Endpoint de entrada PROPIO de la caja, separado del login de la suite (mandato
César 2026-07-11): valida contra el MISMO esquema de usuarios (BUE de seguridad
única, F6.5), exige que el usuario tenga el módulo `pos` en sus permisos
efectivos (plan ∩ rol) y emite un JWT con `scope: "pos"` que las guardas acotan
a la superficie del POS (módulo pos completo + solo-lectura de ventas/clientes).
El mismo código sirve en la nube y en el nodo de sucursal. El token de la suite
sigue operando el POS como siempre (compat).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import LoginRequest, UsuarioOut, auditar_login_fallido
from app.core.auth import create_access_token, verify_password
from app.core.db import get_db
from app.core.permisos import SCOPE_POS_APOYO, permisos_efectivos
from app.models import Usuario
from app.services import auditoria

router = APIRouter(prefix="/pos/auth", tags=["pos"])


class PosLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    scope: str = "pos"
    user: UsuarioOut
    # ya recortados al alcance de la sesión de caja (el front no ve más que esto)
    permisos: dict[str, str]


@router.post("/login", response_model=PosLoginResponse)
async def login_pos(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    usuario = await db.scalar(select(Usuario).where(Usuario.email == body.email.lower()))
    if usuario is None or not usuario.activo or not verify_password(body.password, usuario.password_hash):
        await auditar_login_fallido(db, usuario, "pos", request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contraseña incorrectos"
        )
    permisos = await permisos_efectivos(db, usuario)
    if "pos" not in permisos:
        # credencial válida pero sin acceso al POS: 403, nunca 401 (regla §6)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu usuario no tiene acceso al Punto de Venta",
        )
    recortados = {
        m: (a if m == "pos" else "ver")
        for m, a in permisos.items()
        if m == "pos" or m in SCOPE_POS_APOYO
    }
    auditoria.registrar(
        db,
        tenant_id=usuario.tenant_id,
        accion="login_ok",
        usuario=usuario,
        detalle={"origen": "pos"},
        request=request,
    )
    await db.commit()
    return PosLoginResponse(
        access_token=create_access_token(usuario, scope="pos"),
        user=UsuarioOut.model_validate(usuario),
        permisos=recortados,
    )
