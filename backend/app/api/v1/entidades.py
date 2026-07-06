import re
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cuit import solo_digitos
from app.core.db import get_db
from app.core.permisos import requiere_alguno
from app.models import Entidad, EntidadDomicilio, Usuario

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
    latitud: Decimal | None
    longitud: Decimal | None
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


# ===== Domicilios múltiples (Fase 7, migración 012) =====
# El domicilio plano de `entidades` sigue siendo el fiscal/principal; estos
# son adicionales (entregas, depósitos) — los consumirá Logística (F12-bis).


class DomicilioOut(BaseModel):
    id: uuid.UUID
    tipo: str
    etiqueta: str | None
    domicilio: str | None
    localidad: str | None
    provincia_id: int | None
    codigo_postal: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    predeterminado: bool
    activo: bool

    model_config = {"from_attributes": True}


class DomicilioIn(BaseModel):
    tipo: str = Field("entrega", pattern="^(fiscal|entrega|otro)$")
    etiqueta: str | None = Field(None, max_length=60)
    domicilio: str | None = Field(None, max_length=120)
    localidad: str | None = Field(None, max_length=60)
    provincia_id: int | None = None
    codigo_postal: str | None = Field(None, max_length=10)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    predeterminado: bool = False


class DomicilioUpdate(BaseModel):
    tipo: str | None = Field(None, pattern="^(fiscal|entrega|otro)$")
    etiqueta: str | None = Field(None, max_length=60)
    domicilio: str | None = Field(None, max_length=120)
    localidad: str | None = Field(None, max_length=60)
    provincia_id: int | None = None
    codigo_postal: str | None = Field(None, max_length=10)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    predeterminado: bool | None = None
    activo: bool | None = None


async def _obtener_entidad(db: AsyncSession, tenant_id: uuid.UUID, entidad_id: uuid.UUID) -> Entidad:
    entidad = await db.scalar(
        select(Entidad).where(Entidad.id == entidad_id, Entidad.tenant_id == tenant_id)
    )
    if entidad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entidad no encontrada")
    return entidad


async def _despredeterminar(db: AsyncSession, entidad_id: uuid.UUID, tipo: str, excepto: uuid.UUID | None) -> None:
    """Un solo predeterminado por (entidad, tipo)."""
    otros = await db.scalars(
        select(EntidadDomicilio).where(
            EntidadDomicilio.entidad_id == entidad_id,
            EntidadDomicilio.tipo == tipo,
            EntidadDomicilio.predeterminado.is_(True),
        )
    )
    for d in otros:
        if d.id != excepto:
            d.predeterminado = False


@router.get("/{entidad_id}/domicilios", response_model=list[DomicilioOut])
async def listar_domicilios(
    entidad_id: uuid.UUID,
    incluir_inactivos: bool = False,
    usuario: Usuario = Depends(requiere_alguno(["clientes", "proveedores"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    await _obtener_entidad(db, usuario.tenant_id, entidad_id)
    stmt = select(EntidadDomicilio).where(EntidadDomicilio.entidad_id == entidad_id)
    if not incluir_inactivos:
        stmt = stmt.where(EntidadDomicilio.activo.is_(True))
    filas = (await db.scalars(stmt.order_by(EntidadDomicilio.created_at))).all()
    return [DomicilioOut.model_validate(d) for d in filas]


@router.post(
    "/{entidad_id}/domicilios", response_model=DomicilioOut, status_code=status.HTTP_201_CREATED
)
async def crear_domicilio(
    entidad_id: uuid.UUID,
    body: DomicilioIn,
    usuario: Usuario = Depends(requiere_alguno(["clientes", "proveedores"], "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _obtener_entidad(db, usuario.tenant_id, entidad_id)
    dom = EntidadDomicilio(tenant_id=usuario.tenant_id, entidad_id=entidad_id, **body.model_dump())
    db.add(dom)
    await db.flush()  # asigna dom.id antes de despredeterminar (se excluye a sí mismo)
    if body.predeterminado:
        await _despredeterminar(db, entidad_id, body.tipo, dom.id)
    await db.commit()
    await db.refresh(dom)
    return DomicilioOut.model_validate(dom)


@router.patch("/{entidad_id}/domicilios/{domicilio_id}", response_model=DomicilioOut)
async def editar_domicilio(
    entidad_id: uuid.UUID,
    domicilio_id: uuid.UUID,
    body: DomicilioUpdate,
    usuario: Usuario = Depends(requiere_alguno(["clientes", "proveedores"], "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _obtener_entidad(db, usuario.tenant_id, entidad_id)
    dom = await db.scalar(
        select(EntidadDomicilio).where(
            EntidadDomicilio.id == domicilio_id,
            EntidadDomicilio.entidad_id == entidad_id,
            EntidadDomicilio.tenant_id == usuario.tenant_id,
        )
    )
    if dom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domicilio no encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(dom, campo, valor)
    dom.updated_at = func.now()
    if dom.predeterminado:
        await _despredeterminar(db, entidad_id, dom.tipo, dom.id)
    await db.commit()
    await db.refresh(dom)
    return DomicilioOut.model_validate(dom)
