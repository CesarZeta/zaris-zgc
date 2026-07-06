import re
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cuit import solo_digitos
from app.core.db import get_db
from app.core.permisos import requiere_alguno
from app.models import Entidad, Usuario

router = APIRouter(prefix="/entidades", tags=["entidades"])


class EntidadOut(BaseModel):
    id: uuid.UUID
    tipo_persona: str
    razon_social: str
    nombre_fantasia: str | None
    tipo_documento: str
    nro_documento: str | None
    condicion_iva: str
    email: str | None
    telefono_1: str | None
    telefono_2: str | None
    domicilio: str | None
    localidad: str | None
    provincia_id: int | None
    codigo_postal: str | None
    observaciones: str | None
    activo: bool

    model_config = {"from_attributes": True}


def aplicar_busqueda(stmt: Select, q: str) -> Select:
    """Patrón BUC de ZGE: si el término es numérico busca digits-only en
    documento y teléfonos; si es texto, AND multi-palabra sobre
    razón social / fantasía / email."""
    q = q.strip()
    if not q:
        return stmt
    digitos = solo_digitos(q)
    es_numerico = digitos and not re.sub(r"[\d\s\-\.\(\)\+/]", "", q)
    if es_numerico:
        tel_1 = func.regexp_replace(func.coalesce(Entidad.telefono_1, ""), r"\D", "", "g")
        tel_2 = func.regexp_replace(func.coalesce(Entidad.telefono_2, ""), r"\D", "", "g")
        return stmt.where(
            or_(
                Entidad.nro_documento.contains(digitos),
                tel_1.contains(digitos),
                tel_2.contains(digitos),
            )
        )
    condiciones = []
    for token in q.split():
        patron = f"%{token}%"
        condiciones.append(
            or_(
                Entidad.razon_social.ilike(patron),
                Entidad.nombre_fantasia.ilike(patron),
                Entidad.email.ilike(patron),
            )
        )
    return stmt.where(and_(*condiciones))


@router.get("/buscar", response_model=list[EntidadOut])
async def buscar(
    q: str = "",
    limit: int = 20,
    offset: int = 0,
    usuario: Usuario = Depends(requiere_alguno(["clientes", "proveedores"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Entidad).where(Entidad.tenant_id == usuario.tenant_id, Entidad.activo)
    stmt = aplicar_busqueda(stmt, q)
    stmt = stmt.order_by(Entidad.razon_social).limit(min(limit, 100)).offset(offset)
    entidades = (await db.scalars(stmt)).all()
    return [EntidadOut.model_validate(e) for e in entidades]
