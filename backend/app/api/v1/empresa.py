"""Configuración de la empresa (tenant): rubro y presets de customización.

Regla de producto (CLAUDE.md §1-ter): la gestión central es una sola; el rubro
cambia presets/UI, nunca el modelo de datos. Al elegir un rubro se siembran los
atributos sugeridos (idempotente) para que la carga de variantes arranque lista.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.core.permisos import requiere
from app.models import Atributo, AtributoValor, Tenant, Usuario

router = APIRouter(prefix="/empresa", tags=["empresa"])

# Presets por rubro: qué muestra la UI y qué atributos se siembran.
# variantes_destacadas: el form de artículos abre la sección de variantes expandida.
# flags_pos_super: muestra pesable / envase retornable / venta por depto.
RUBROS: dict[str, dict] = {
    "general": {
        "nombre": "Comercio general",
        "flags_pos_super": False,
        "variantes_destacadas": False,
        "en_dolares_destacado": False,
        "atributos_sugeridos": {},
    },
    "supermercado": {
        "nombre": "Supermercado / autoservicio",
        "flags_pos_super": True,
        "variantes_destacadas": False,
        "en_dolares_destacado": False,
        "atributos_sugeridos": {"Gusto": [], "Tamaño": []},
    },
    "indumentaria_calzado": {
        "nombre": "Indumentaria y calzado",
        "flags_pos_super": False,
        "variantes_destacadas": True,
        "en_dolares_destacado": False,
        "atributos_sugeridos": {
            "Talle": ["XS", "S", "M", "L", "XL", "XXL"],
            "Color": ["Negro", "Blanco", "Azul", "Rojo", "Gris"],
        },
    },
    "electronica": {
        "nombre": "Electrónica y telefonía",
        "flags_pos_super": False,
        "variantes_destacadas": True,
        "en_dolares_destacado": True,
        "atributos_sugeridos": {"Color": [], "Capacidad": ["64GB", "128GB", "256GB"]},
    },
    "ferreteria_repuestos": {
        "nombre": "Ferretería / repuestos",
        "flags_pos_super": False,
        "variantes_destacadas": False,
        "en_dolares_destacado": True,
        "atributos_sugeridos": {"Medida": []},
    },
    "distribuidora": {
        "nombre": "Distribuidora / mayorista",
        "flags_pos_super": False,
        "variantes_destacadas": False,
        "en_dolares_destacado": False,
        "atributos_sugeridos": {"Gusto": [], "Presentación": []},
    },
}


class EmpresaOut(BaseModel):
    id: uuid.UUID
    razon_social: str
    nombre_fantasia: str | None
    rubro: str
    geo_centro_lat: Decimal | None = None
    geo_centro_lon: Decimal | None = None
    geo_delta_grados: Decimal | None = None
    model_config = {"from_attributes": True}


class RubroIn(BaseModel):
    rubro: str


class GeoSesgoIn(BaseModel):
    """Sesgo geográfico opcional para el buscador de domicilios (Fase 7):
    prioriza la zona del comercio SIN excluir el resto del país. Los tres
    campos en NULL = sin sesgo."""

    geo_centro_lat: Decimal | None = None
    geo_centro_lon: Decimal | None = None
    geo_delta_grados: Decimal | None = None


@router.get("", response_model=EmpresaOut)
async def obtener_empresa(
    usuario: Usuario = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, usuario.tenant_id)
    return EmpresaOut.model_validate(tenant)


@router.get("/rubros")
async def listar_rubros():
    return [
        {"codigo": codigo, **{k: v for k, v in preset.items() if k != "atributos_sugeridos"}}
        for codigo, preset in RUBROS.items()
    ]


@router.put("/geo", response_model=EmpresaOut)
async def configurar_geo(
    body: GeoSesgoIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    tiene_lat = body.geo_centro_lat is not None
    tiene_lon = body.geo_centro_lon is not None
    if tiene_lat != tiene_lon:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Centro geográfico incompleto: lat y lon van juntos (o ambos vacíos)",
        )
    if tiene_lat and not (-90 <= body.geo_centro_lat <= 90 and -180 <= body.geo_centro_lon <= 180):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Coordenadas fuera de rango")
    if body.geo_delta_grados is not None and not (0 < body.geo_delta_grados <= 5):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Delta en grados: mayor a 0 y hasta 5 (≈500 km)",
        )
    tenant = await db.get(Tenant, usuario.tenant_id)
    tenant.geo_centro_lat = body.geo_centro_lat
    tenant.geo_centro_lon = body.geo_centro_lon
    tenant.geo_delta_grados = body.geo_delta_grados
    await db.commit()
    return EmpresaOut.model_validate(tenant)


@router.put("/rubro", response_model=EmpresaOut)
async def cambiar_rubro(
    body: RubroIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if body.rubro not in RUBROS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rubro inválido; opciones: {', '.join(RUBROS)}",
        )
    tenant = await db.get(Tenant, usuario.tenant_id)
    tenant.rubro = body.rubro

    # sembrar atributos sugeridos del rubro (idempotente: no duplica ni pisa)
    existentes = {
        a.nombre: a
        for a in (await db.scalars(select(Atributo).where(Atributo.tenant_id == tenant.id))).all()
    }
    for orden, (nombre, valores) in enumerate(RUBROS[body.rubro]["atributos_sugeridos"].items()):
        atributo = existentes.get(nombre)
        if atributo is None:
            atributo = Atributo(tenant_id=tenant.id, nombre=nombre, orden=orden)
            db.add(atributo)
            await db.flush()
        valores_existentes = {
            v.valor
            for v in (
                await db.scalars(
                    select(AtributoValor).where(AtributoValor.atributo_id == atributo.id)
                )
            ).all()
        }
        for i, valor in enumerate(valores):
            if valor not in valores_existentes:
                db.add(
                    AtributoValor(
                        tenant_id=tenant.id, atributo_id=atributo.id, valor=valor, orden=i
                    )
                )
    await db.commit()
    tenant = await db.get(Tenant, usuario.tenant_id)
    return EmpresaOut.model_validate(tenant)
