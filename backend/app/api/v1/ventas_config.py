"""Configuración de Ventas: puntos de venta (PREFIJOS del legacy) y
configuración ARCA por tenant (modo, CUIT, certificados, umbral CF)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cuit import validar_cuit
from app.core.db import get_db
from app.core.permisos import requiere, requiere_alguno
from app.models import ArcaConfig, Comprobante, CondicionVenta, PuntoVenta, Usuario
from app.services import auditoria

router = APIRouter(prefix="/ventas", tags=["ventas-config"])


# ===== Condiciones de venta (contado / cta cte con vencimientos) =====

class CondicionVentaIn(BaseModel):
    descripcion: str = Field(min_length=2, max_length=60)
    dias: list[int] = Field(min_length=1, max_length=12)  # [0,30,60] = 3 cuotas


class CondicionVentaOut(BaseModel):
    id: uuid.UUID
    descripcion: str
    dias: list[int]
    activa: bool
    model_config = {"from_attributes": True}


@router.get("/condiciones-venta", response_model=list[CondicionVentaOut])
async def listar_condiciones_venta(
    usuario: Usuario = Depends(requiere_alguno(["clientes", "ventas", "compras", "proveedores"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas = await db.scalars(
        select(CondicionVenta)
        .where(CondicionVenta.tenant_id == usuario.tenant_id, CondicionVenta.activa.is_(True))
        .order_by(CondicionVenta.descripcion)
    )
    return list(filas)


@router.post(
    "/condiciones-venta", response_model=CondicionVentaOut, status_code=status.HTTP_201_CREATED
)
async def crear_condicion_venta(
    body: CondicionVentaIn,
    usuario: Usuario = Depends(requiere_alguno(["clientes", "ventas", "compras"], "editar")),
    db: AsyncSession = Depends(get_db),
):
    cond = CondicionVenta(
        tenant_id=usuario.tenant_id,
        descripcion=body.descripcion.strip(),
        dias=sorted(set(body.dias)),
    )
    db.add(cond)
    await db.commit()
    return cond


# ===== Puntos de venta =====

class PuntoVentaIn(BaseModel):
    numero: int = Field(ge=1, le=99999)
    descripcion: str = Field("", max_length=60)
    sucursal_id: uuid.UUID | None = None
    electronico: bool = True


class PuntoVentaUpdate(BaseModel):
    descripcion: str | None = Field(None, max_length=60)
    sucursal_id: uuid.UUID | None = None
    electronico: bool | None = None
    activo: bool | None = None


class PuntoVentaOut(BaseModel):
    id: uuid.UUID
    numero: int
    descripcion: str
    sucursal_id: uuid.UUID | None
    electronico: bool
    activo: bool
    model_config = {"from_attributes": True}


@router.get("/puntos-venta", response_model=list[PuntoVentaOut])
async def listar_puntos_venta(
    usuario: Usuario = Depends(requiere_alguno(["ventas", "pos", "configuracion"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    filas = await db.scalars(
        select(PuntoVenta)
        .where(PuntoVenta.tenant_id == usuario.tenant_id)
        .order_by(PuntoVenta.numero)
    )
    return list(filas)


@router.post("/puntos-venta", response_model=PuntoVentaOut, status_code=status.HTTP_201_CREATED)
async def crear_punto_venta(
    body: PuntoVentaIn,
    request: Request,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    pv = PuntoVenta(tenant_id=usuario.tenant_id, **body.model_dump())
    db.add(pv)
    try:
        await db.flush()
        auditoria.registrar(
            db,
            tenant_id=usuario.tenant_id,
            accion="punto_venta_alta",
            usuario=usuario,
            ref_id=pv.id,
            ref_texto=f"PV {body.numero:04d}",
            detalle=body.model_dump(),
            request=request,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe el punto de venta {body.numero:04d}",
        )
    return pv


@router.put("/puntos-venta/{pv_id}", response_model=PuntoVentaOut)
async def actualizar_punto_venta(
    pv_id: uuid.UUID,
    body: PuntoVentaUpdate,
    request: Request,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    pv = await db.scalar(
        select(PuntoVenta).where(PuntoVenta.id == pv_id, PuntoVenta.tenant_id == usuario.tenant_id)
    )
    if pv is None:
        raise HTTPException(status_code=404, detail="Punto de venta no encontrado")
    cambios: dict = {}
    for campo, valor in body.model_dump(exclude_unset=True).items():
        if getattr(pv, campo) != valor:
            cambios[campo] = {"antes": getattr(pv, campo), "despues": valor}
        setattr(pv, campo, valor)
    if cambios:
        auditoria.registrar(
            db,
            tenant_id=usuario.tenant_id,
            accion="punto_venta_edicion",
            usuario=usuario,
            ref_id=pv.id,
            ref_texto=f"PV {pv.numero:04d}",
            detalle=cambios,
            request=request,
        )
    await db.commit()
    return pv


# ===== Configuración ARCA =====

class ArcaConfigIn(BaseModel):
    modo: str = Field(pattern="^(deshabilitado|simulado|homologacion|produccion)$")
    cuit: str | None = Field(None, max_length=13)
    razon_social: str | None = Field(None, max_length=80)
    iibb: str | None = Field(None, max_length=15)
    inicio_actividades: date | None = None
    concepto: int = Field(1, ge=1, le=3)
    umbral_identificar_cf: Decimal = Field(Decimal("10000000"), ge=0)
    cert_pem: str | None = None
    key_pem: str | None = None


class ArcaConfigOut(BaseModel):
    modo: str
    cuit: str | None
    razon_social: str | None
    iibb: str | None
    inicio_actividades: date | None
    concepto: int
    umbral_identificar_cf: Decimal
    tiene_certificado: bool
    tiene_clave: bool
    comprobantes_emitidos: int


def _config_out(config: ArcaConfig | None, emitidos: int) -> ArcaConfigOut:
    if config is None:
        return ArcaConfigOut(
            modo="deshabilitado",
            cuit=None,
            razon_social=None,
            iibb=None,
            inicio_actividades=None,
            concepto=1,
            umbral_identificar_cf=Decimal("10000000"),
            tiene_certificado=False,
            tiene_clave=False,
            comprobantes_emitidos=emitidos,
        )
    return ArcaConfigOut(
        modo=config.modo,
        cuit=config.cuit,
        razon_social=config.razon_social,
        iibb=config.iibb,
        inicio_actividades=config.inicio_actividades,
        concepto=config.concepto,
        umbral_identificar_cf=config.umbral_identificar_cf,
        tiene_certificado=bool(config.cert_pem),
        tiene_clave=bool(config.key_pem),
        comprobantes_emitidos=emitidos,
    )


async def _emitidos_fiscales(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    from sqlalchemy import func as sqlfunc

    return (
        await db.scalar(
            select(sqlfunc.count())
            .select_from(Comprobante)
            .where(
                Comprobante.tenant_id == tenant_id,
                Comprobante.estado == "emitido",
                Comprobante.cae.is_not(None),
            )
        )
    ) or 0


@router.get("/arca-config", response_model=ArcaConfigOut)
async def ver_arca_config(
    usuario: Usuario = Depends(requiere("configuracion", "ver")),
    db: AsyncSession = Depends(get_db),
):
    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )
    return _config_out(config, await _emitidos_fiscales(db, usuario.tenant_id))


@router.put("/arca-config", response_model=ArcaConfigOut)
async def guardar_arca_config(
    body: ArcaConfigIn,
    request: Request,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    if body.cuit:
        body.cuit = "".join(c for c in body.cuit if c.isdigit())
        if not validar_cuit(body.cuit):
            raise HTTPException(status_code=422, detail="CUIT inválido (dígito verificador)")
    if body.modo in ("homologacion", "produccion") and not body.cuit:
        raise HTTPException(
            status_code=422, detail=f"El modo {body.modo} requiere el CUIT del emisor"
        )

    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )
    datos = body.model_dump(exclude_unset=True)
    # cert/key: si vienen None u omitidos se conservan los guardados
    for sensible in ("cert_pem", "key_pem"):
        if datos.get(sensible) is None:
            datos.pop(sensible, None)
    modo_antes = config.modo if config else "deshabilitado"
    if config is None:
        config = ArcaConfig(tenant_id=usuario.tenant_id, **datos)
        db.add(config)
    else:
        for campo, valor in datos.items():
            setattr(config, campo, valor)
    # jamás el PEM en el detalle: solo el HECHO de que se cargó (diseño F17 §3)
    auditoria.registrar(
        db,
        tenant_id=usuario.tenant_id,
        accion="arca_config",
        usuario=usuario,
        ref_texto=f"modo {modo_antes} → {body.modo}",
        detalle={
            "modo_antes": modo_antes,
            "modo_despues": body.modo,
            "cargo_certificado": "cert_pem" in datos,
            "cargo_clave": "key_pem" in datos,
        },
        request=request,
    )
    await db.commit()
    return _config_out(config, await _emitidos_fiscales(db, usuario.tenant_id))
