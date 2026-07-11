"""POS Resto (F12-d, DISENO-POS-PERFILES.md §3) — sucesor de RestoDelivery.

La mesa es una CUENTA ABIERTA (comanda) que vive en tablas pos_* y NUNCA se
traslada a la gestión (mandato César): a la gestión llega SOLO la venta final,
emitida por `emitir_core` al cerrar la mesa — misma maquinaria del POS
mostrador (precios de servidor, letra por matriz, medios que suman el total).

- Los precios de los ítems de comanda son snapshot informativo (los resuelve
  el server con la lista de la caja al comandar); el total FISCAL se recalcula
  al cobrar, igual que en el mostrador.
- La propina (legacy PORC_PROP) es un % informativo de la comanda: NO integra
  la factura ni los medios (se rinde por fuera del arqueo fiscal).
- Envío a cocina = marcar ítems pendientes + payload para imprimir la comanda
  en la impresora del sector (el front imprime, patrón ticket).
"""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere, requiere_alguno
from app.models import (
    ArcaConfig,
    Articulo,
    ArticuloVariante,
    Comprobante,
    PosCaja,
    PosComanda,
    PosComandaItem,
    PosMesa,
    PosSalon,
    Tenant,
    Usuario,
    VentaMedio,
)
from app.api.v1.comprobantes import (
    ComprobanteOut,
    _aplicar_calculo,
    _cargar,
    _out,
)
from app.api.v1.pos import (
    MedioIn,
    VentaItemIn,
    _armar_venta,
    _caja_de,
    _cotizacion_vigente,
    _etiquetas_valores,
    _precio_final,
    _sesion_abierta_de,
)
from app.api.v1.comprobantes import emitir_core
from app.services import ventas as sv

router = APIRouter(prefix="/pos/resto", tags=["pos-resto"])


# ===== Schemas =====

class SalonIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=40)
    orden: int = 0


class SalonUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=40)
    orden: int | None = None
    activo: bool | None = None


class SalonOut(BaseModel):
    id: uuid.UUID
    nombre: str
    orden: int
    activo: bool
    model_config = {"from_attributes": True}


class MesasIn(BaseModel):
    salon_id: uuid.UUID
    cantidad: int = Field(1, ge=1, le=50)


class MesaUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=20)
    activa: bool | None = None


class MesaOut(BaseModel):
    id: uuid.UUID
    salon_id: uuid.UUID
    salon_nombre: str
    numero: int
    nombre: str | None
    activa: bool
    # estado derivado de la comanda abierta
    ocupada: bool
    comanda_id: uuid.UUID | None
    comanda_total: Decimal | None
    mozo_nombre: str | None
    abierta_at: datetime | None


class ComandaAbrirIn(BaseModel):
    caja_id: uuid.UUID
    tipo: str = Field("mesa", pattern="^(mesa|delivery|takeaway)$")
    mesa_id: uuid.UUID | None = None
    cubiertos: int | None = Field(None, ge=1, le=99)
    cliente_nombre: str | None = Field(None, max_length=80)
    telefono: str | None = Field(None, max_length=40)
    domicilio: str | None = Field(None, max_length=120)
    localidad: str | None = Field(None, max_length=60)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    observaciones: str | None = Field(None, max_length=200)


class ComandaUpdate(BaseModel):
    cubiertos: int | None = Field(None, ge=1, le=99)
    cliente_nombre: str | None = Field(None, max_length=80)
    telefono: str | None = Field(None, max_length=40)
    domicilio: str | None = Field(None, max_length=120)
    localidad: str | None = Field(None, max_length=60)
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    envio_estado: str | None = Field(None, pattern="^(en_preparacion|despachado|entregado)$")
    propina_pct: Decimal | None = Field(None, ge=0, le=100)
    observaciones: str | None = Field(None, max_length=200)


class ComandaItemIn(BaseModel):
    articulo_id: uuid.UUID
    variante_id: uuid.UUID | None = None
    cantidad: Decimal = Field(gt=0)
    observaciones: str | None = Field(None, max_length=120)


class ComandaItemUpdate(BaseModel):
    cantidad: Decimal | None = Field(None, gt=0)
    observaciones: str | None = Field(None, max_length=120)


class ComandaItemOut(BaseModel):
    id: uuid.UUID
    articulo_id: uuid.UUID
    variante_id: uuid.UUID | None
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    importe: Decimal
    observaciones: str | None
    estado_cocina: str


class ComandaOut(BaseModel):
    id: uuid.UUID
    caja_id: uuid.UUID
    mesa_id: uuid.UUID | None
    mesa_numero: int | None
    salon_nombre: str | None
    tipo: str
    estado: str
    mozo_id: uuid.UUID
    mozo_nombre: str
    cubiertos: int | None
    cliente_nombre: str | None
    telefono: str | None
    domicilio: str | None
    localidad: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    envio_estado: str | None
    propina_pct: Decimal
    observaciones: str | None
    comprobante_id: uuid.UUID | None
    abierta_at: datetime
    cerrada_at: datetime | None
    total: Decimal
    items: list[ComandaItemOut]


class MoverIn(BaseModel):
    mesa_id: uuid.UUID


class UnirIn(BaseModel):
    desde_comanda_id: uuid.UUID


class CobrarIn(BaseModel):
    sesion_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    descuento_pct: Decimal = Field(Decimal("0"), ge=0, le=100)
    medios: list[MedioIn] = Field(min_length=1)
    propina_pct: Decimal | None = Field(None, ge=0, le=100)


class ComandaCocinaItem(BaseModel):
    cantidad: Decimal
    descripcion: str
    observaciones: str | None


class CocinaOut(BaseModel):
    comanda_id: uuid.UUID
    mesa: str | None            # "Salón 1 · Mesa 4" | None (delivery/takeaway)
    tipo: str
    mozo_nombre: str
    hora: datetime
    items: list[ComandaCocinaItem]


class ReporteMozoOut(BaseModel):
    mozo_id: uuid.UUID
    mozo_nombre: str
    comandas: int
    total_vendido: Decimal
    propina_estimada: Decimal


# ===== Helpers =====

async def _comanda_de(
    db: AsyncSession, tenant_id: uuid.UUID, comanda_id: uuid.UUID
) -> PosComanda:
    comanda = await db.scalar(
        select(PosComanda).where(
            PosComanda.id == comanda_id, PosComanda.tenant_id == tenant_id
        )
    )
    if comanda is None:
        raise HTTPException(status_code=404, detail="Comanda no encontrada")
    return comanda


async def _comanda_abierta(
    db: AsyncSession, tenant_id: uuid.UUID, comanda_id: uuid.UUID
) -> PosComanda:
    comanda = await _comanda_de(db, tenant_id, comanda_id)
    if comanda.estado != "abierta":
        raise HTTPException(status_code=409, detail="La comanda no está abierta")
    return comanda


def _total_comanda(comanda: PosComanda) -> Decimal:
    return sum((i.cantidad * i.precio_unitario for i in comanda.items), Decimal("0"))


async def _comanda_out(db: AsyncSession, comanda: PosComanda) -> ComandaOut:
    mesa_numero = salon_nombre = None
    if comanda.mesa_id:
        fila = (
            await db.execute(
                select(PosMesa.numero, PosSalon.nombre)
                .join(PosSalon, PosSalon.id == PosMesa.salon_id)
                .where(PosMesa.id == comanda.mesa_id)
            )
        ).first()
        if fila:
            mesa_numero, salon_nombre = fila
    mozo = await db.scalar(select(Usuario.nombre).where(Usuario.id == comanda.mozo_id))
    return ComandaOut(
        id=comanda.id,
        caja_id=comanda.caja_id,
        mesa_id=comanda.mesa_id,
        mesa_numero=mesa_numero,
        salon_nombre=salon_nombre,
        tipo=comanda.tipo,
        estado=comanda.estado,
        mozo_id=comanda.mozo_id,
        mozo_nombre=mozo or "",
        cubiertos=comanda.cubiertos,
        cliente_nombre=comanda.cliente_nombre,
        telefono=comanda.telefono,
        domicilio=comanda.domicilio,
        localidad=comanda.localidad,
        latitud=comanda.latitud,
        longitud=comanda.longitud,
        envio_estado=comanda.envio_estado,
        propina_pct=comanda.propina_pct,
        observaciones=comanda.observaciones,
        comprobante_id=comanda.comprobante_id,
        abierta_at=comanda.abierta_at,
        cerrada_at=comanda.cerrada_at,
        total=_total_comanda(comanda),
        items=[
            ComandaItemOut(
                id=i.id,
                articulo_id=i.articulo_id,
                variante_id=i.variante_id,
                descripcion=i.descripcion,
                cantidad=i.cantidad,
                precio_unitario=i.precio_unitario,
                importe=i.cantidad * i.precio_unitario,
                observaciones=i.observaciones,
                estado_cocina=i.estado_cocina,
            )
            for i in comanda.items
        ],
    )


# ===== Salones y mesas (layout — config sensible del POS) =====

@router.get("/salones", response_model=list[SalonOut])
async def listar_salones(
    incluir_inactivos: bool = False,
    usuario: Usuario = Depends(requiere_alguno(["pos", "configuracion"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PosSalon).where(PosSalon.tenant_id == usuario.tenant_id)
    if not incluir_inactivos:
        stmt = stmt.where(PosSalon.activo.is_(True))
    filas = (await db.scalars(stmt.order_by(PosSalon.orden, PosSalon.nombre))).all()
    return [SalonOut.model_validate(s) for s in filas]


@router.post("/salones", response_model=SalonOut, status_code=status.HTTP_201_CREATED)
async def crear_salon(
    body: SalonIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    salon = PosSalon(tenant_id=usuario.tenant_id, nombre=body.nombre.strip(), orden=body.orden)
    db.add(salon)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un salón con ese nombre")
    return SalonOut.model_validate(salon)


@router.patch("/salones/{salon_id}", response_model=SalonOut)
async def editar_salon(
    salon_id: uuid.UUID,
    body: SalonUpdate,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    salon = await db.scalar(
        select(PosSalon).where(PosSalon.id == salon_id, PosSalon.tenant_id == usuario.tenant_id)
    )
    if salon is None:
        raise HTTPException(status_code=404, detail="Salón no encontrado")
    datos = body.model_dump(exclude_unset=True)
    if "nombre" in datos and datos["nombre"]:
        datos["nombre"] = datos["nombre"].strip()
    for campo, valor in datos.items():
        setattr(salon, campo, valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un salón con ese nombre")
    return SalonOut.model_validate(salon)


@router.get("/mesas", response_model=list[MesaOut])
async def listar_mesas(
    incluir_inactivas: bool = False,
    usuario: Usuario = Depends(requiere_alguno(["pos", "configuracion"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Grilla de mesas con su estado derivado (libre/ocupada) y el resumen de
    la comanda abierta (total, mozo)."""
    stmt = (
        select(PosMesa, PosSalon.nombre)
        .join(PosSalon, PosSalon.id == PosMesa.salon_id)
        .where(PosMesa.tenant_id == usuario.tenant_id, PosSalon.activo.is_(True))
    )
    if not incluir_inactivas:
        stmt = stmt.where(PosMesa.activa.is_(True))
    filas = (await db.execute(stmt.order_by(PosSalon.orden, PosSalon.nombre, PosMesa.numero))).all()

    abiertas = {
        c.mesa_id: c
        for c in (
            await db.scalars(
                select(PosComanda).where(
                    PosComanda.tenant_id == usuario.tenant_id,
                    PosComanda.estado == "abierta",
                    PosComanda.mesa_id.is_not(None),
                )
            )
        ).all()
    }
    mozos: dict[uuid.UUID, str] = {}
    if abiertas:
        filas_m = await db.execute(
            select(Usuario.id, Usuario.nombre).where(
                Usuario.id.in_({c.mozo_id for c in abiertas.values()})
            )
        )
        mozos = {i: n for i, n in filas_m}

    salida = []
    for mesa, salon_nombre in filas:
        comanda = abiertas.get(mesa.id)
        salida.append(
            MesaOut(
                id=mesa.id,
                salon_id=mesa.salon_id,
                salon_nombre=salon_nombre,
                numero=mesa.numero,
                nombre=mesa.nombre,
                activa=mesa.activa,
                ocupada=comanda is not None,
                comanda_id=comanda.id if comanda else None,
                comanda_total=_total_comanda(comanda) if comanda else None,
                mozo_nombre=mozos.get(comanda.mozo_id) if comanda else None,
                abierta_at=comanda.abierta_at if comanda else None,
            )
        )
    return salida


@router.post("/mesas", response_model=list[MesaOut], status_code=status.HTTP_201_CREATED)
async def crear_mesas(
    body: MesasIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Alta de N mesas numeradas a continuación de la última del salón."""
    salon = await db.scalar(
        select(PosSalon).where(
            PosSalon.id == body.salon_id, PosSalon.tenant_id == usuario.tenant_id
        )
    )
    if salon is None:
        raise HTTPException(status_code=404, detail="Salón no encontrado")
    ultimo = await db.scalar(
        select(func.coalesce(func.max(PosMesa.numero), 0)).where(
            PosMesa.salon_id == salon.id
        )
    )
    nuevas = [
        PosMesa(tenant_id=usuario.tenant_id, salon_id=salon.id, numero=ultimo + 1 + i)
        for i in range(body.cantidad)
    ]
    db.add_all(nuevas)
    await db.commit()
    return [
        MesaOut(
            id=m.id,
            salon_id=m.salon_id,
            salon_nombre=salon.nombre,
            numero=m.numero,
            nombre=m.nombre,
            activa=m.activa,
            ocupada=False,
            comanda_id=None,
            comanda_total=None,
            mozo_nombre=None,
            abierta_at=None,
        )
        for m in nuevas
    ]


@router.patch("/mesas/{mesa_id}", response_model=MesaOut)
async def editar_mesa(
    mesa_id: uuid.UUID,
    body: MesaUpdate,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    fila = (
        await db.execute(
            select(PosMesa, PosSalon.nombre)
            .join(PosSalon, PosSalon.id == PosMesa.salon_id)
            .where(PosMesa.id == mesa_id, PosMesa.tenant_id == usuario.tenant_id)
        )
    ).first()
    if fila is None:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    mesa, salon_nombre = fila
    if body.activa is False:
        ocupada = await db.scalar(
            select(func.count()).select_from(PosComanda).where(
                PosComanda.mesa_id == mesa.id, PosComanda.estado == "abierta"
            )
        )
        if ocupada:
            raise HTTPException(status_code=409, detail="La mesa tiene una comanda abierta")
    datos = body.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(mesa, campo, valor)
    await db.commit()
    return MesaOut(
        id=mesa.id,
        salon_id=mesa.salon_id,
        salon_nombre=salon_nombre,
        numero=mesa.numero,
        nombre=mesa.nombre,
        activa=mesa.activa,
        ocupada=False,
        comanda_id=None,
        comanda_total=None,
        mozo_nombre=None,
        abierta_at=None,
    )


# ===== Comandas =====

@router.post("/comandas", response_model=ComandaOut, status_code=status.HTTP_201_CREATED)
async def abrir_comanda(
    body: ComandaAbrirIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    caja = await _caja_de(db, usuario.tenant_id, body.caja_id)
    mesa_id = None
    if body.tipo == "mesa":
        if body.mesa_id is None:
            raise HTTPException(status_code=422, detail="Indicar la mesa")
        mesa = await db.scalar(
            select(PosMesa).where(
                PosMesa.id == body.mesa_id,
                PosMesa.tenant_id == usuario.tenant_id,
                PosMesa.activa.is_(True),
            )
        )
        if mesa is None:
            raise HTTPException(status_code=404, detail="Mesa no encontrada o inactiva")
        mesa_id = mesa.id
    comanda = PosComanda(
        tenant_id=usuario.tenant_id,
        caja_id=caja.id,
        mesa_id=mesa_id,
        tipo=body.tipo,
        mozo_id=usuario.id,
        cubiertos=body.cubiertos,
        cliente_nombre=(body.cliente_nombre or "").strip() or None,
        telefono=(body.telefono or "").strip() or None,
        domicilio=(body.domicilio or "").strip() or None,
        localidad=(body.localidad or "").strip() or None,
        latitud=body.latitud,
        longitud=body.longitud,
        envio_estado="en_preparacion" if body.tipo == "delivery" else None,
        observaciones=(body.observaciones or "").strip() or None,
    )
    db.add(comanda)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="La mesa ya tiene una comanda abierta")
    comanda = await db.scalar(select(PosComanda).where(PosComanda.id == comanda.id))
    return await _comanda_out(db, comanda)


@router.get("/comandas", response_model=list[ComandaOut])
async def listar_comandas(
    estado: str = "abierta",
    tipo: str | None = None,
    limit: int = 50,
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PosComanda).where(
        PosComanda.tenant_id == usuario.tenant_id, PosComanda.estado == estado
    )
    if tipo:
        stmt = stmt.where(PosComanda.tipo == tipo)
    filas = (
        await db.scalars(stmt.order_by(PosComanda.abierta_at.desc()).limit(min(limit, 200)))
    ).all()
    return [await _comanda_out(db, c) for c in filas]


@router.get("/comandas/{comanda_id}", response_model=ComandaOut)
async def detalle_comanda(
    comanda_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    return await _comanda_out(db, await _comanda_de(db, usuario.tenant_id, comanda_id))


@router.patch("/comandas/{comanda_id}", response_model=ComandaOut)
async def editar_comanda(
    comanda_id: uuid.UUID,
    body: ComandaUpdate,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    comanda = await _comanda_de(db, usuario.tenant_id, comanda_id)
    datos = body.model_dump(exclude_unset=True)
    # el estado del envío se puede seguir moviendo con la comanda ya cobrada
    # (se cobra al despachar y se marca entregado después); el resto no.
    if comanda.estado != "abierta" and set(datos) - {"envio_estado"}:
        raise HTTPException(status_code=409, detail="La comanda no está abierta")
    for campo, valor in datos.items():
        setattr(comanda, campo, valor)
    await db.commit()
    return await _comanda_out(db, comanda)


@router.post("/comandas/{comanda_id}/items", response_model=ComandaOut)
async def agregar_items(
    comanda_id: uuid.UUID,
    body: list[ComandaItemIn],
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Agrega ítems a la cuenta. El precio lo resuelve el server con la lista
    de la caja de la comanda (snapshot informativo; el total fiscal exacto se
    recalcula al cobrar, regla del POS)."""
    if not body:
        raise HTTPException(status_code=422, detail="Sin ítems")
    comanda = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    caja = await _caja_de(db, usuario.tenant_id, comanda.caja_id)
    cotizacion = await _cotizacion_vigente(db, usuario.tenant_id)

    arts = {
        a.id: a
        for a in (
            await db.scalars(
                select(Articulo).where(
                    Articulo.id.in_({i.articulo_id for i in body}),
                    Articulo.tenant_id == usuario.tenant_id,
                )
            )
        ).all()
    }
    var_ids = [i.variante_id for i in body if i.variante_id]
    variantes: dict[uuid.UUID, ArticuloVariante] = {}
    if var_ids:
        variantes = {
            v.id: v
            for v in (
                await db.scalars(
                    select(ArticuloVariante).where(
                        ArticuloVariante.id.in_(var_ids),
                        ArticuloVariante.tenant_id == usuario.tenant_id,
                    )
                )
            ).all()
        }
    etiquetas = await _etiquetas_valores(db, usuario.tenant_id, list(variantes.values()))

    orden_base = max((i.orden for i in comanda.items), default=-1) + 1
    for n, it in enumerate(body):
        art = arts.get(it.articulo_id)
        if art is None or not art.activo:
            raise HTTPException(status_code=422, detail="Artículo inexistente o inactivo")
        variante = variantes.get(it.variante_id) if it.variante_id else None
        if it.variante_id and variante is None:
            raise HTTPException(status_code=422, detail="Variante inexistente en la empresa")
        descripcion = art.descripcion
        if variante is not None:
            etiqueta = etiquetas.get(variante.id)
            if etiqueta:
                descripcion = f"{art.descripcion} · {etiqueta}"[:120]
        db.add(
            PosComandaItem(
                tenant_id=usuario.tenant_id,
                comanda_id=comanda.id,
                articulo_id=it.articulo_id,
                variante_id=it.variante_id,
                descripcion=descripcion,
                cantidad=it.cantidad,
                precio_unitario=_precio_final(art, variante, caja.lista_precios, cotizacion),
                observaciones=(it.observaciones or "").strip() or None,
                orden=orden_base + n,
            )
        )
    await db.commit()
    comanda = await db.scalar(
        select(PosComanda)
        .where(PosComanda.id == comanda.id)
        .execution_options(populate_existing=True)
    )
    return await _comanda_out(db, comanda)


@router.patch("/comandas/{comanda_id}/items/{item_id}", response_model=ComandaOut)
async def editar_item(
    comanda_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ComandaItemUpdate,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    comanda = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    item = next((i for i in comanda.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
    datos = body.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(item, campo, valor)
    await db.commit()
    comanda = await db.scalar(
        select(PosComanda)
        .where(PosComanda.id == comanda.id)
        .execution_options(populate_existing=True)
    )
    return await _comanda_out(db, comanda)


@router.delete("/comandas/{comanda_id}/items/{item_id}", response_model=ComandaOut)
async def quitar_item(
    comanda_id: uuid.UUID,
    item_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """La comanda es pre-fiscal (no es un documento): quitar un ítem antes de
    cobrar es borrado físico, como corregir un renglón de un borrador."""
    comanda = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    item = next((i for i in comanda.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
    comanda.items.remove(item)
    await db.commit()
    comanda = await db.scalar(
        select(PosComanda)
        .where(PosComanda.id == comanda.id)
        .execution_options(populate_existing=True)
    )
    return await _comanda_out(db, comanda)


@router.post("/comandas/{comanda_id}/enviar-cocina", response_model=CocinaOut)
async def enviar_cocina(
    comanda_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Marca los ítems pendientes como enviados y devuelve el payload de la
    comanda para imprimir en cocina (el front imprime, patrón ticket)."""
    comanda = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    pendientes = [i for i in comanda.items if i.estado_cocina == "pendiente"]
    if not pendientes:
        raise HTTPException(status_code=409, detail="No hay ítems pendientes de enviar")
    ahora = datetime.now(timezone.utc)
    for i in pendientes:
        i.estado_cocina = "enviado"
        i.enviado_at = ahora
    await db.commit()

    mesa_txt = None
    if comanda.mesa_id:
        fila = (
            await db.execute(
                select(PosMesa.numero, PosSalon.nombre)
                .join(PosSalon, PosSalon.id == PosMesa.salon_id)
                .where(PosMesa.id == comanda.mesa_id)
            )
        ).first()
        if fila:
            mesa_txt = f"{fila[1]} · Mesa {fila[0]}"
    mozo = await db.scalar(select(Usuario.nombre).where(Usuario.id == comanda.mozo_id))
    return CocinaOut(
        comanda_id=comanda.id,
        mesa=mesa_txt,
        tipo=comanda.tipo,
        mozo_nombre=mozo or "",
        hora=ahora,
        items=[
            ComandaCocinaItem(
                cantidad=i.cantidad, descripcion=i.descripcion, observaciones=i.observaciones
            )
            for i in pendientes
        ],
    )


@router.post("/comandas/{comanda_id}/mover", response_model=ComandaOut)
async def mover_comanda(
    comanda_id: uuid.UUID,
    body: MoverIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    comanda = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    if comanda.tipo != "mesa":
        raise HTTPException(status_code=422, detail="Solo se mueven comandas de mesa")
    mesa = await db.scalar(
        select(PosMesa).where(
            PosMesa.id == body.mesa_id,
            PosMesa.tenant_id == usuario.tenant_id,
            PosMesa.activa.is_(True),
        )
    )
    if mesa is None:
        raise HTTPException(status_code=404, detail="Mesa destino no encontrada o inactiva")
    comanda.mesa_id = mesa.id
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="La mesa destino está ocupada")
    return await _comanda_out(db, comanda)


@router.post("/comandas/{comanda_id}/unir", response_model=ComandaOut)
async def unir_comandas(
    comanda_id: uuid.UUID,
    body: UnirIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Une mesas: los ítems de la comanda origen pasan a esta y aquella queda
    anulada (su mesa se libera)."""
    if body.desde_comanda_id == comanda_id:
        raise HTTPException(status_code=422, detail="No se puede unir una comanda consigo misma")
    destino = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    origen = await _comanda_abierta(db, usuario.tenant_id, body.desde_comanda_id)
    orden_base = max((i.orden for i in destino.items), default=-1) + 1
    for n, item in enumerate(list(origen.items)):
        origen.items.remove(item)
        db.add(
            PosComandaItem(
                tenant_id=item.tenant_id,
                comanda_id=destino.id,
                articulo_id=item.articulo_id,
                variante_id=item.variante_id,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                observaciones=item.observaciones,
                estado_cocina=item.estado_cocina,
                enviado_at=item.enviado_at,
                orden=orden_base + n,
            )
        )
    origen.estado = "anulada"
    origen.cerrada_at = datetime.now(timezone.utc)
    origen.observaciones = (
        f"{origen.observaciones or ''} — unida a la comanda {destino.id}"
    )[:200]
    await db.commit()
    destino = await db.scalar(
        select(PosComanda)
        .where(PosComanda.id == destino.id)
        .execution_options(populate_existing=True)
    )
    return await _comanda_out(db, destino)


@router.post("/comandas/{comanda_id}/anular", response_model=ComandaOut)
async def anular_comanda(
    comanda_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Anula una comanda ABIERTA (mesa que se levanta sin consumir, pedido
    cancelado). No toca nada fiscal: la comanda nunca llegó a comprobante."""
    comanda = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    comanda.estado = "anulada"
    comanda.cerrada_at = datetime.now(timezone.utc)
    await db.commit()
    return await _comanda_out(db, comanda)


@router.post("/comandas/{comanda_id}/cobrar", response_model=ComprobanteOut)
async def cobrar_comanda(
    comanda_id: uuid.UUID,
    body: CobrarIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Cierre de mesa: factura fiscal vía emitir_core con la maquinaria del POS
    (precios de servidor re-resueltos al cobrar, letra por matriz, medios que
    suman el total). La propina NO integra la factura ni los medios."""
    sesion = await _sesion_abierta_de(db, usuario, body.sesion_id)
    caja = await _caja_de(db, usuario.tenant_id, sesion.caja_id)
    comanda = await _comanda_abierta(db, usuario.tenant_id, comanda_id)
    if not comanda.items:
        raise HTTPException(status_code=422, detail="La comanda no tiene ítems")

    tenant = await db.scalar(select(Tenant).where(Tenant.id == usuario.tenant_id))
    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )
    items = [
        VentaItemIn(
            articulo_id=i.articulo_id, variante_id=i.variante_id, cantidad=i.cantidad
        )
        for i in comanda.items
    ]
    receptor, calculo, letra = await _armar_venta(
        db, tenant, caja, body.cliente_id, items, body.descuento_pct
    )
    cobrado = sum((m.importe for m in body.medios), Decimal("0"))
    if cobrado != calculo["total"]:
        raise HTTPException(
            status_code=409,
            detail=f"Los medios de pago (${cobrado}) no coinciden con el total "
            f"(${calculo['total']}). Recalculá el cobro.",
        )

    comp = Comprobante(
        tenant_id=usuario.tenant_id,
        punto_venta_id=caja.punto_venta_id,
        tipo_codigo=sv.tipo_codigo_para("factura", letra),
        letra=letra,
        contado=True,
        lista_precios=caja.lista_precios,
        deposito_id=caja.deposito_id,
        actualiza_stock=True,
        moneda="PES",
        cotizacion=Decimal("1"),
        descuento_pct=body.descuento_pct,
        pos_sesion_id=sesion.id,
        creado_por=usuario.id,
        **receptor,
    )
    db.add(comp)
    await db.flush()
    await _aplicar_calculo(db, comp, calculo)
    comp = await _cargar(db, usuario.tenant_id, comp.id)

    await emitir_core(db, comp, usuario, config)

    for m in body.medios:
        db.add(
            VentaMedio(
                tenant_id=usuario.tenant_id,
                comprobante_id=comp.id,
                pos_sesion_id=sesion.id,
                medio=m.medio,
                importe=m.importe,
                referencia=m.referencia,
            )
        )
    comanda.estado = "cerrada"
    comanda.cerrada_at = datetime.now(timezone.utc)
    comanda.comprobante_id = comp.id
    if body.propina_pct is not None:
        comanda.propina_pct = body.propina_pct
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, comp.id))


@router.get("/reporte-mozos", response_model=list[ReporteMozoOut])
async def reporte_mozos(
    desde: date,
    hasta: date,
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Ventas por mozo EN el POS (propinas/control) — reporte, no tabla. Suma
    los comprobantes de comandas cerradas en el rango."""
    filas = (
        await db.execute(
            select(
                PosComanda.mozo_id,
                func.count(),
                func.coalesce(func.sum(Comprobante.total), 0),
                func.coalesce(
                    func.sum(Comprobante.total * PosComanda.propina_pct / 100), 0
                ),
            )
            .select_from(PosComanda)
            .join(Comprobante, Comprobante.id == PosComanda.comprobante_id)
            .where(
                PosComanda.tenant_id == usuario.tenant_id,
                PosComanda.estado == "cerrada",
                func.date(PosComanda.cerrada_at) >= desde,
                func.date(PosComanda.cerrada_at) <= hasta,
            )
            .group_by(PosComanda.mozo_id)
        )
    ).all()
    nombres: dict[uuid.UUID, str] = {}
    if filas:
        filas_n = await db.execute(
            select(Usuario.id, Usuario.nombre).where(Usuario.id.in_({f[0] for f in filas}))
        )
        nombres = {i: n for i, n in filas_n}
    salida = [
        ReporteMozoOut(
            mozo_id=mozo_id,
            mozo_nombre=nombres.get(mozo_id, ""),
            comandas=cantidad,
            total_vendido=Decimal(total),
            propina_estimada=Decimal(propina).quantize(Decimal("0.01")),
        )
        for mozo_id, cantidad, total, propina in filas
    ]
    salida.sort(key=lambda x: x.total_vendido, reverse=True)
    return salida
