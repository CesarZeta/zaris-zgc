"""POS Mostrador Web (Fase 6).

La venta POS es una factura fiscal de Fase 3 (misma tabla, mismo circuito
ARCA/stock/cta.cte.) emitida en un solo paso: el servidor calcula los
precios (lista de la caja, precios FINALES con IVA), valida que los medios
de pago sumen exactamente el total y emite el CAE registrando medios y
sesión en la misma transacción. El cajero no elige precios ni letra.

- Sesión = turno de cajero sobre una caja: apertura con fondo → ventas →
  cierre con arqueo (totales sellados; en vivo el resumen es un reporte).
- Anulación de un ticket emitido: exige credenciales de SUPERVISOR
  (nivel_acceso <= 2, semántica ZGE: 1=admin, 2=supervisor) y genera la NC
  espejo fiscal en el acto, con los medios de la venta original en negativo
  para el arqueo.
"""

import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.auth import verify_password
from app.core.db import get_db
from app.core.permisos import requiere, requiere_alguno
from app.models import (
    ArcaConfig,
    Articulo,
    ArticuloVariante,
    AtributoValor,
    Comprobante,
    Cotizacion,
    Deposito,
    PosBalanzaConfig,
    PosCaja,
    PosSesion,
    PuntoVenta,
    Sucursal,
    Tenant,
    TipoComprobante,
    Usuario,
    VentaMedio,
)
from app.api.v1.comprobantes import (
    ComprobanteOut,
    ItemIn,
    _aplicar_calculo,
    _armar_items,
    _cargar,
    _out,
    _snapshot_receptor,
    crear_nc_espejo_core,
    emitir_core,
)
from app.services import ventas as sv

router = APIRouter(prefix="/pos", tags=["pos"])

MEDIOS = ("efectivo", "transferencia", "cheque", "tarjeta", "mercadopago", "otro")
NIVEL_SUPERVISOR = 2  # 1=admin, 2=supervisor (patrón ZGE)
_C2 = Decimal("0.01")


# ===== Schemas =====

class CajaIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=40)
    sucursal_id: uuid.UUID | None = None
    punto_venta_id: uuid.UUID
    deposito_id: uuid.UUID | None = None
    lista_precios: int = Field(1, ge=1, le=4)
    ancho_ticket: int = 80
    perfil: str = Field("estandar", pattern="^(estandar|resto)$")


class CajaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=40)
    sucursal_id: uuid.UUID | None = None
    punto_venta_id: uuid.UUID | None = None
    deposito_id: uuid.UUID | None = None
    lista_precios: int | None = Field(None, ge=1, le=4)
    ancho_ticket: int | None = None
    perfil: str | None = Field(None, pattern="^(estandar|resto)$")
    activa: bool | None = None


class CajaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    sucursal_id: uuid.UUID | None
    punto_venta_id: uuid.UUID
    punto_venta_numero: int
    deposito_id: uuid.UUID | None
    lista_precios: int
    ancho_ticket: int
    perfil: str
    activa: bool
    sesion_abierta: bool


class SesionAbrirIn(BaseModel):
    caja_id: uuid.UUID
    fondo_inicial: Decimal = Field(Decimal("0"), ge=0)


class SesionOut(BaseModel):
    id: uuid.UUID
    caja_id: uuid.UUID
    caja_nombre: str
    caja_perfil: str = "estandar"
    ancho_ticket: int
    cajero_id: uuid.UUID
    cajero_nombre: str
    estado: str
    fondo_inicial: Decimal
    abierta_at: datetime
    cerrada_at: datetime | None
    cantidad_tickets: int | None
    total_ventas: Decimal | None
    cobrado_efectivo: Decimal | None
    cobrado_tarjeta: Decimal | None
    cobrado_mercadopago: Decimal | None
    cobrado_otros: Decimal | None
    efectivo_teorico: Decimal | None
    efectivo_contado: Decimal | None
    diferencia: Decimal | None
    observaciones: str | None


class TotalMedio(BaseModel):
    medio: str
    total: Decimal
    cantidad: int


class ResumenOut(BaseModel):
    sesion_id: uuid.UUID
    fondo_inicial: Decimal
    cantidad_tickets: int
    anulaciones: int
    total_ventas: Decimal        # facturas − NC
    medios: list[TotalMedio]     # cobrado por medio (NC en negativo)
    efectivo_teorico: Decimal    # fondo + efectivo neto


class SesionCerrarIn(BaseModel):
    efectivo_contado: Decimal | None = None
    observaciones: str | None = None


class VentaItemIn(BaseModel):
    articulo_id: uuid.UUID
    variante_id: uuid.UUID | None = None
    cantidad: Decimal = Field(gt=0)
    # F12-b venta por departamento: importe FINAL tipeado por el cajero. El
    # server solo lo acepta si el artículo tiene venta_por_depto=true — para
    # el resto, los precios siguen siendo de servidor (regla de la Fase 6).
    precio_unitario: Decimal | None = Field(None, gt=0)


class VentaCalcularIn(BaseModel):
    caja_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    descuento_pct: Decimal = Field(Decimal("0"), ge=0, le=100)
    items: list[VentaItemIn] = Field(min_length=1)


class MedioIn(BaseModel):
    medio: str = Field(pattern="^(efectivo|transferencia|cheque|tarjeta|mercadopago|otro)$")
    importe: Decimal = Field(gt=0)
    referencia: str | None = Field(None, max_length=60)


class VentaIn(BaseModel):
    sesion_id: uuid.UUID
    cliente_id: uuid.UUID | None = None
    descuento_pct: Decimal = Field(Decimal("0"), ge=0, le=100)
    items: list[VentaItemIn] = Field(min_length=1)
    medios: list[MedioIn] = Field(min_length=1)


class ItemCalculadoOut(BaseModel):
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    importe_total: Decimal


class CalculoOut(BaseModel):
    letra: str
    receptor_nombre: str
    neto_gravado: Decimal
    iva: Decimal
    total: Decimal
    items: list[ItemCalculadoOut]


class AnularIn(BaseModel):
    sesion_id: uuid.UUID
    supervisor_email: str
    supervisor_password: str
    motivo: str | None = Field(None, max_length=120)


class TicketResumenOut(BaseModel):
    id: uuid.UUID
    tipo_codigo: str
    clase: str
    letra: str
    numero_formateado: str | None
    emitido_at: datetime | None
    receptor_nombre: str
    total: Decimal
    anulada: bool


class VarianteBusqueda(BaseModel):
    variante_id: uuid.UUID
    descripcion: str            # "M / Rojo"
    codigo_barras: str | None
    precio: Decimal


class EnvaseBusqueda(BaseModel):
    """Envase retornable asociado al artículo (F12-b): el POS agrega la línea
    del envase junto con la del producto."""
    articulo_id: uuid.UUID
    codigo: str
    descripcion: str
    precio: Decimal


class ResultadoBusqueda(BaseModel):
    articulo_id: uuid.UUID
    variante_id: uuid.UUID | None
    codigo: str
    descripcion: str
    precio: Decimal
    tasa_iva: Decimal
    pesable: bool
    exacto: bool                # matcheó código de barras / código tal cual
    tiene_variantes: bool
    variantes: list[VarianteBusqueda]
    # F12-b: cantidad resuelta desde la etiqueta de balanza (peso en kg, o
    # importe/precio si la etiqueta embebe importe). None = la elige el cajero.
    cantidad: Decimal | None = None
    envase: EnvaseBusqueda | None = None


class BalanzaConfigIn(BaseModel):
    habilitado: bool = True
    prefijo: str = Field("20", pattern="^2[0-9]$")
    valor_tipo: str = Field("peso", pattern="^(peso|importe)$")
    codigo_digitos: int = Field(5, ge=3, le=7)


class BalanzaConfigOut(BaseModel):
    habilitado: bool
    prefijo: str
    valor_tipo: str
    codigo_digitos: int
    model_config = {"from_attributes": True}


class DepartamentoOut(BaseModel):
    articulo_id: uuid.UUID
    codigo: str
    descripcion: str
    tasa_iva: Decimal


# ===== Helpers =====

async def _caja_de(db: AsyncSession, tenant_id: uuid.UUID, caja_id: uuid.UUID) -> PosCaja:
    caja = await db.scalar(
        select(PosCaja).where(PosCaja.id == caja_id, PosCaja.tenant_id == tenant_id)
    )
    if caja is None or not caja.activa:
        raise HTTPException(status_code=404, detail="Caja no encontrada o inactiva")
    return caja


async def _sesion_de(db: AsyncSession, tenant_id: uuid.UUID, sesion_id: uuid.UUID) -> PosSesion:
    sesion = await db.scalar(
        select(PosSesion).where(PosSesion.id == sesion_id, PosSesion.tenant_id == tenant_id)
    )
    if sesion is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return sesion


async def _sesion_abierta_de(
    db: AsyncSession, usuario: Usuario, sesion_id: uuid.UUID
) -> PosSesion:
    sesion = await _sesion_de(db, usuario.tenant_id, sesion_id)
    if sesion.estado != "abierta":
        raise HTTPException(status_code=409, detail="La sesión de caja está cerrada")
    if sesion.cajero_id != usuario.id:
        raise HTTPException(status_code=409, detail="La sesión pertenece a otro cajero")
    return sesion


async def _cotizacion_vigente(db: AsyncSession, tenant_id: uuid.UUID) -> Decimal:
    valor = await db.scalar(
        select(Cotizacion.valor)
        .where(Cotizacion.tenant_id == tenant_id)
        .order_by(Cotizacion.vigente_desde.desc())
        .limit(1)
    )
    return valor or Decimal("1")


def _precio_final(
    art: Articulo, variante: ArticuloVariante | None, lista: int, cotizacion: Decimal
) -> Decimal:
    """Precio de mostrador: lista de la caja (+ diferencial de variante),
    convertido con la cotización vigente si el artículo está en dólares.
    Los precios de lista son FINALES (IVA incluido) — convención Fase 3."""
    precio = getattr(art, f"precio_{lista}") or Decimal("0")
    if variante is not None:
        precio = precio + (variante.dif_precio or Decimal("0"))
    if art.en_dolares:
        precio = precio * cotizacion
    return precio.quantize(_C2, rounding=ROUND_HALF_UP)


async def _etiquetas_valores(
    db: AsyncSession, tenant_id: uuid.UUID, variantes: list[ArticuloVariante]
) -> dict[uuid.UUID, str]:
    """variante_id -> 'M / Rojo' (valores en el orden guardado)."""
    ids = {
        x
        for v in variantes
        for x in (v.valor_1_id, v.valor_2_id, v.valor_3_id)
        if x is not None
    }
    if not ids:
        return {}
    filas = await db.scalars(
        select(AtributoValor).where(
            AtributoValor.id.in_(ids), AtributoValor.tenant_id == tenant_id
        )
    )
    etiquetas = {f.id: f.valor for f in filas}
    return {
        v.id: " / ".join(
            etiquetas.get(x, "?")
            for x in (v.valor_1_id, v.valor_2_id, v.valor_3_id)
            if x is not None
        )
        for v in variantes
    }


def _dv_ean13(doce: str) -> int:
    """Dígito verificador EAN-13 sobre los primeros 12 dígitos."""
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(doce))
    return (10 - suma % 10) % 10


async def _resolver_etiqueta_balanza(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    q: str,
    caja: PosCaja,
    cotizacion: Decimal,
) -> ResultadoBusqueda | None:
    """Pesables por etiqueta de balanza (F12-b, DISENO-POS-PERFILES.md §1):
    EAN-13 `P PP CCCCC VVVVV D` con el prefijo configurado por tenant. Devuelve
    la línea con cantidad = peso (kg) o cantidad = importe/precio si la
    etiqueta embebe importe. None = no es etiqueta (sigue la búsqueda normal)."""
    if len(q) != 13 or not q.isdigit():
        return None
    cfg = await db.scalar(
        select(PosBalanzaConfig).where(PosBalanzaConfig.tenant_id == tenant_id)
    )
    if cfg is None or not cfg.habilitado or not q.startswith(cfg.prefijo):
        return None
    if int(q[12]) != _dv_ean13(q[:12]):
        return None  # DV no cierra: no es etiqueta válida
    plu = str(int(q[2 : 2 + cfg.codigo_digitos]))
    valor = Decimal(q[2 + cfg.codigo_digitos : 12])
    art = await db.scalar(
        select(Articulo).where(
            Articulo.tenant_id == tenant_id,
            Articulo.codigo_balanza == plu,
            Articulo.activo.is_(True),
        )
    )
    if art is None:
        return None
    precio = _precio_final(art, None, caja.lista_precios, cotizacion)
    if cfg.valor_tipo == "peso":
        cantidad = (valor / 1000).quantize(Decimal("0.001"))  # gramos → kg
    elif precio > 0:
        importe = valor / 100  # centavos → $
        cantidad = (importe / precio).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    else:
        cantidad = None  # sin precio no se puede derivar el peso: lo tipea el cajero
    if cantidad is not None and cantidad <= 0:
        cantidad = None
    return ResultadoBusqueda(
        articulo_id=art.id,
        variante_id=None,
        codigo=art.codigo,
        descripcion=art.descripcion,
        precio=precio,
        tasa_iva=art.tasa_iva,
        pesable=art.pesable,
        exacto=True,
        tiene_variantes=False,
        variantes=[],
        cantidad=cantidad,
    )


async def _armar_venta(
    db: AsyncSession,
    tenant: Tenant,
    caja: PosCaja,
    cliente_id: uuid.UUID | None,
    items_in: list[VentaItemIn],
    descuento_pct: Decimal,
) -> tuple[dict, dict, str]:
    """Resuelve precios de servidor + letra y calcula el comprobante completo.
    Devuelve (receptor, calculo, letra)."""
    receptor = await _snapshot_receptor(db, tenant.id, cliente_id)
    letra = sv.letra_comprobante(tenant.condicion_iva, receptor["receptor_condicion_iva"])
    cotizacion = await _cotizacion_vigente(db, tenant.id)

    art_ids = [i.articulo_id for i in items_in]
    articulos = {
        a.id: a
        for a in await db.scalars(
            select(Articulo).where(Articulo.id.in_(art_ids), Articulo.tenant_id == tenant.id)
        )
    }
    var_ids = [i.variante_id for i in items_in if i.variante_id]
    variantes: dict[uuid.UUID, ArticuloVariante] = {}
    if var_ids:
        variantes = {
            v.id: v
            for v in await db.scalars(
                select(ArticuloVariante).where(
                    ArticuloVariante.id.in_(var_ids),
                    ArticuloVariante.tenant_id == tenant.id,
                )
            )
        }
    etiquetas = await _etiquetas_valores(db, tenant.id, list(variantes.values()))

    armados: list[ItemIn] = []
    for it in items_in:
        art = articulos.get(it.articulo_id)
        if art is None or not art.activo:
            raise HTTPException(status_code=422, detail="Artículo inexistente o inactivo")
        variante = variantes.get(it.variante_id) if it.variante_id else None
        if it.variante_id and variante is None:
            raise HTTPException(status_code=422, detail="Variante inexistente en la empresa")
        # F12-b venta por departamento: el importe tipeado SOLO vale para
        # artículos-departamento; el resto mantiene precio de servidor.
        if it.precio_unitario is not None and not art.venta_por_depto:
            raise HTTPException(
                status_code=422,
                detail="Solo los departamentos (venta por depto.) admiten importe tipeado",
            )
        if art.venta_por_depto and it.precio_unitario is None:
            raise HTTPException(
                status_code=422,
                detail=f"Indicar el importe para {art.descripcion} (venta por departamento)",
            )
        descripcion = None
        if variante is not None:
            etiqueta = etiquetas.get(variante.id)
            if etiqueta:
                descripcion = f"{art.descripcion} · {etiqueta}"[:120]
        precio = (
            it.precio_unitario.quantize(_C2, rounding=ROUND_HALF_UP)
            if it.precio_unitario is not None
            else _precio_final(art, variante, caja.lista_precios, cotizacion)
        )
        armados.append(
            ItemIn(
                articulo_id=it.articulo_id,
                variante_id=it.variante_id,
                descripcion=descripcion,
                cantidad=it.cantidad,
                precio_unitario=precio,
            )
        )

    items = await _armar_items(db, tenant.id, armados)
    try:
        calculo = sv.calcular_comprobante(items, letra, descuento_pct, precios_con_iva=True)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if calculo["total"] <= 0:
        raise HTTPException(status_code=422, detail="La venta no tiene importe")
    return receptor, calculo, letra


def _calculo_out(receptor: dict, calculo: dict, letra: str) -> CalculoOut:
    return CalculoOut(
        letra=letra,
        receptor_nombre=receptor["receptor_nombre"],
        neto_gravado=calculo["neto_gravado"],
        iva=calculo["iva"],
        total=calculo["total"],
        items=[
            ItemCalculadoOut(
                descripcion=i["descripcion"],
                cantidad=i["cantidad"],
                precio_unitario=i["precio_unitario"],
                importe_total=i["importe_total"],
            )
            for i in calculo["items"]
        ],
    )


async def _resumen_sesion(db: AsyncSession, sesion: PosSesion) -> ResumenOut:
    """Arqueo vivo: agrega ventas y medios de la sesión con signo por clase
    (factura/ND suman, NC restan — mismo criterio que la planilla de caja)."""
    tickets, anulaciones, total = (
        await db.execute(
            select(
                func.count().filter(TipoComprobante.clase == "factura"),
                func.count().filter(TipoComprobante.clase == "nota_credito"),
                func.coalesce(func.sum(Comprobante.total * TipoComprobante.signo_cta_cte), 0),
            )
            .select_from(Comprobante)
            .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
            .where(
                Comprobante.pos_sesion_id == sesion.id,
                Comprobante.estado == "emitido",
            )
        )
    ).one()

    filas = (
        await db.execute(
            select(
                VentaMedio.medio,
                func.coalesce(
                    func.sum(VentaMedio.importe * TipoComprobante.signo_cta_cte), 0
                ),
                func.count(),
            )
            .select_from(VentaMedio)
            .join(Comprobante, Comprobante.id == VentaMedio.comprobante_id)
            .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
            .where(
                VentaMedio.pos_sesion_id == sesion.id,
                Comprobante.estado == "emitido",
            )
            .group_by(VentaMedio.medio)
        )
    ).all()
    medios = [TotalMedio(medio=m, total=t, cantidad=c) for m, t, c in filas]
    efectivo = sum((m.total for m in medios if m.medio == "efectivo"), Decimal("0"))
    return ResumenOut(
        sesion_id=sesion.id,
        fondo_inicial=sesion.fondo_inicial,
        cantidad_tickets=tickets,
        anulaciones=anulaciones,
        total_ventas=Decimal(total),
        medios=medios,
        efectivo_teorico=sesion.fondo_inicial + efectivo,
    )


async def _sesion_out(
    db: AsyncSession, sesion: PosSesion, cajero_nombre: str | None = None
) -> SesionOut:
    if cajero_nombre is None:
        cajero = await db.scalar(select(Usuario).where(Usuario.id == sesion.cajero_id))
        cajero_nombre = cajero.nombre if cajero else ""
    return SesionOut(
        id=sesion.id,
        caja_id=sesion.caja_id,
        caja_nombre=sesion.caja.nombre,
        caja_perfil=sesion.caja.perfil,
        ancho_ticket=sesion.caja.ancho_ticket,
        cajero_id=sesion.cajero_id,
        cajero_nombre=cajero_nombre,
        estado=sesion.estado,
        fondo_inicial=sesion.fondo_inicial,
        abierta_at=sesion.abierta_at,
        cerrada_at=sesion.cerrada_at,
        cantidad_tickets=sesion.cantidad_tickets,
        total_ventas=sesion.total_ventas,
        cobrado_efectivo=sesion.cobrado_efectivo,
        cobrado_tarjeta=sesion.cobrado_tarjeta,
        cobrado_mercadopago=sesion.cobrado_mercadopago,
        cobrado_otros=sesion.cobrado_otros,
        efectivo_teorico=sesion.efectivo_teorico,
        efectivo_contado=sesion.efectivo_contado,
        diferencia=sesion.diferencia,
        observaciones=sesion.observaciones,
    )


# ===== Cajas (configuración) =====

@router.get("/cajas", response_model=list[CajaOut])
async def listar_cajas(
    incluir_inactivas: bool = False,
    usuario: Usuario = Depends(requiere_alguno(["pos", "configuracion"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PosCaja, PuntoVenta.numero).join(
        PuntoVenta, PuntoVenta.id == PosCaja.punto_venta_id
    ).where(PosCaja.tenant_id == usuario.tenant_id)
    if not incluir_inactivas:
        stmt = stmt.where(PosCaja.activa.is_(True))
    filas = (await db.execute(stmt.order_by(PosCaja.nombre))).all()
    abiertas = {
        s
        for (s,) in await db.execute(
            select(PosSesion.caja_id).where(
                PosSesion.tenant_id == usuario.tenant_id, PosSesion.estado == "abierta"
            )
        )
    }
    return [
        CajaOut(
            id=c.id,
            nombre=c.nombre,
            sucursal_id=c.sucursal_id,
            punto_venta_id=c.punto_venta_id,
            punto_venta_numero=pv_numero,
            deposito_id=c.deposito_id,
            lista_precios=c.lista_precios,
            ancho_ticket=c.ancho_ticket,
            perfil=c.perfil,
            activa=c.activa,
            sesion_abierta=c.id in abiertas,
        )
        for c, pv_numero in filas
    ]


async def _validar_refs_caja(
    db: AsyncSession, tenant_id: uuid.UUID, body: CajaIn | CajaUpdate
) -> None:
    if body.ancho_ticket is not None and body.ancho_ticket not in (58, 80):
        raise HTTPException(status_code=422, detail="Ancho de ticket: 58 u 80 mm")
    if body.punto_venta_id is not None:
        pv = await db.scalar(
            select(PuntoVenta).where(
                PuntoVenta.id == body.punto_venta_id,
                PuntoVenta.tenant_id == tenant_id,
                PuntoVenta.activo.is_(True),
            )
        )
        if pv is None:
            raise HTTPException(status_code=404, detail="Punto de venta no encontrado o inactivo")
    if body.deposito_id is not None:
        dep = await db.scalar(
            select(Deposito).where(
                Deposito.id == body.deposito_id, Deposito.tenant_id == tenant_id
            )
        )
        if dep is None:
            raise HTTPException(status_code=404, detail="Depósito no encontrado")
    if body.sucursal_id is not None:
        suc = await db.scalar(
            select(Sucursal).where(
                Sucursal.id == body.sucursal_id, Sucursal.tenant_id == tenant_id
            )
        )
        if suc is None:
            raise HTTPException(status_code=404, detail="Sucursal no encontrada")


@router.post("/cajas", response_model=CajaOut, status_code=status.HTTP_201_CREATED)
async def crear_caja(
    body: CajaIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    await _validar_refs_caja(db, usuario.tenant_id, body)
    caja = PosCaja(
        tenant_id=usuario.tenant_id,
        nombre=body.nombre.strip(),
        sucursal_id=body.sucursal_id,
        punto_venta_id=body.punto_venta_id,
        deposito_id=body.deposito_id,
        lista_precios=body.lista_precios,
        ancho_ticket=body.ancho_ticket,
        perfil=body.perfil,
    )
    db.add(caja)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una caja con ese nombre")
    pv = await db.scalar(select(PuntoVenta).where(PuntoVenta.id == caja.punto_venta_id))
    return CajaOut(
        id=caja.id,
        nombre=caja.nombre,
        sucursal_id=caja.sucursal_id,
        punto_venta_id=caja.punto_venta_id,
        punto_venta_numero=pv.numero,
        deposito_id=caja.deposito_id,
        lista_precios=caja.lista_precios,
        ancho_ticket=caja.ancho_ticket,
        perfil=caja.perfil,
        activa=caja.activa,
        sesion_abierta=False,
    )


@router.patch("/cajas/{caja_id}", response_model=CajaOut)
async def editar_caja(
    caja_id: uuid.UUID,
    body: CajaUpdate,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    caja = await db.scalar(
        select(PosCaja).where(PosCaja.id == caja_id, PosCaja.tenant_id == usuario.tenant_id)
    )
    if caja is None:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    await _validar_refs_caja(db, usuario.tenant_id, body)
    datos = body.model_dump(exclude_unset=True)
    if "nombre" in datos and datos["nombre"]:
        datos["nombre"] = datos["nombre"].strip()
    for campo, valor in datos.items():
        setattr(caja, campo, valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una caja con ese nombre")
    abierta = await db.scalar(
        select(func.count())
        .select_from(PosSesion)
        .where(PosSesion.caja_id == caja.id, PosSesion.estado == "abierta")
    )
    pv = await db.scalar(select(PuntoVenta).where(PuntoVenta.id == caja.punto_venta_id))
    return CajaOut(
        id=caja.id,
        nombre=caja.nombre,
        sucursal_id=caja.sucursal_id,
        punto_venta_id=caja.punto_venta_id,
        punto_venta_numero=pv.numero,
        deposito_id=caja.deposito_id,
        lista_precios=caja.lista_precios,
        ancho_ticket=caja.ancho_ticket,
        perfil=caja.perfil,
        activa=caja.activa,
        sesion_abierta=(abierta or 0) > 0,
    )


# ===== Balanza y departamentos (F12-b) =====

@router.get("/balanza-config", response_model=BalanzaConfigOut | None)
async def obtener_balanza_config(
    usuario: Usuario = Depends(requiere_alguno(["pos", "configuracion"], "ver")),
    db: AsyncSession = Depends(get_db),
):
    cfg = await db.scalar(
        select(PosBalanzaConfig).where(PosBalanzaConfig.tenant_id == usuario.tenant_id)
    )
    return BalanzaConfigOut.model_validate(cfg) if cfg else None


@router.put("/balanza-config", response_model=BalanzaConfigOut)
async def configurar_balanza(
    body: BalanzaConfigIn,
    usuario: Usuario = Depends(requiere("configuracion", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Upsert de la config de etiquetas de balanza del tenant (config sensible
    del POS ⇒ configuracion.editar, regla §6)."""
    cfg = await db.scalar(
        select(PosBalanzaConfig).where(PosBalanzaConfig.tenant_id == usuario.tenant_id)
    )
    if cfg is None:
        cfg = PosBalanzaConfig(tenant_id=usuario.tenant_id)
        db.add(cfg)
    cfg.habilitado = body.habilitado
    cfg.prefijo = body.prefijo
    cfg.valor_tipo = body.valor_tipo
    cfg.codigo_digitos = body.codigo_digitos
    cfg.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return BalanzaConfigOut.model_validate(cfg)


@router.get("/departamentos", response_model=list[DepartamentoOut])
async def listar_departamentos(
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Artículos-departamento (venta_por_depto): tecla de depto + importe para
    lo no codificado del mostrador."""
    filas = (
        await db.scalars(
            select(Articulo)
            .where(
                Articulo.tenant_id == usuario.tenant_id,
                Articulo.venta_por_depto.is_(True),
                Articulo.activo.is_(True),
            )
            .order_by(Articulo.descripcion)
        )
    ).all()
    return [
        DepartamentoOut(
            articulo_id=a.id, codigo=a.codigo, descripcion=a.descripcion, tasa_iva=a.tasa_iva
        )
        for a in filas
    ]


# ===== Sesiones (turno de cajero) =====

@router.post("/sesiones", response_model=SesionOut, status_code=status.HTTP_201_CREATED)
async def abrir_sesion(
    body: SesionAbrirIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    caja = await _caja_de(db, usuario.tenant_id, body.caja_id)
    ya_abierta = await db.scalar(
        select(PosSesion).where(
            PosSesion.tenant_id == usuario.tenant_id,
            PosSesion.estado == "abierta",
            or_(PosSesion.caja_id == caja.id, PosSesion.cajero_id == usuario.id),
        )
    )
    if ya_abierta is not None:
        quien = "esa caja" if ya_abierta.caja_id == caja.id else "este cajero"
        raise HTTPException(status_code=409, detail=f"Ya hay una sesión abierta para {quien}")
    sesion = PosSesion(
        tenant_id=usuario.tenant_id,
        caja_id=caja.id,
        cajero_id=usuario.id,
        fondo_inicial=body.fondo_inicial,
    )
    db.add(sesion)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya hay una sesión abierta para esa caja")
    sesion = await db.scalar(select(PosSesion).where(PosSesion.id == sesion.id))
    return await _sesion_out(db, sesion)


@router.get("/sesiones/actual", response_model=SesionOut | None)
async def sesion_actual(
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    sesion = await db.scalar(
        select(PosSesion).where(
            PosSesion.tenant_id == usuario.tenant_id,
            PosSesion.cajero_id == usuario.id,
            PosSesion.estado == "abierta",
        )
    )
    return await _sesion_out(db, sesion) if sesion else None


@router.get("/sesiones", response_model=list[SesionOut])
async def listar_sesiones(
    caja_id: uuid.UUID | None = None,
    limit: int = 30,
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PosSesion).where(PosSesion.tenant_id == usuario.tenant_id)
    if caja_id:
        stmt = stmt.where(PosSesion.caja_id == caja_id)
    filas = (
        await db.scalars(stmt.order_by(PosSesion.abierta_at.desc()).limit(min(limit, 100)))
    ).all()
    # Los cajeros de toda la página en UN select (antes: uno por sesión).
    nombres: dict[uuid.UUID, str] = {}
    if filas:
        cajeros = await db.scalars(
            select(Usuario).where(Usuario.id.in_({s.cajero_id for s in filas}))
        )
        nombres = {u.id: u.nombre for u in cajeros}
    return [await _sesion_out(db, s, nombres.get(s.cajero_id, "")) for s in filas]


@router.get("/sesiones/{sesion_id}/resumen", response_model=ResumenOut)
async def resumen_sesion(
    sesion_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    sesion = await _sesion_de(db, usuario.tenant_id, sesion_id)
    return await _resumen_sesion(db, sesion)


@router.get("/sesiones/{sesion_id}/ventas", response_model=list[TicketResumenOut])
async def ventas_de_sesion(
    sesion_id: uuid.UUID,
    limit: int = 50,
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    sesion = await _sesion_de(db, usuario.tenant_id, sesion_id)
    nc = aliased(Comprobante)
    anulada_sub = (
        select(func.count())
        .select_from(nc)
        .join(TipoComprobante, TipoComprobante.codigo == nc.tipo_codigo)
        .where(
            nc.comprobante_asociado_id == Comprobante.id,
            nc.estado == "emitido",
            TipoComprobante.clase == "nota_credito",
        )
        .correlate(Comprobante)
        .scalar_subquery()
    )
    filas = (
        await db.execute(
            select(Comprobante, anulada_sub)
            .where(
                Comprobante.pos_sesion_id == sesion.id,
                Comprobante.estado == "emitido",
            )
            .order_by(Comprobante.emitido_at.desc())
            .limit(min(limit, 200))
        )
    ).all()
    return [
        TicketResumenOut(
            id=c.id,
            tipo_codigo=c.tipo_codigo,
            clase=c.tipo.clase,
            letra=c.letra,
            numero_formateado=(
                f"{c.punto_venta.numero:04d}-{c.numero:08d}" if c.numero is not None else None
            ),
            emitido_at=c.emitido_at,
            receptor_nombre=c.receptor_nombre,
            total=c.total,
            anulada=(ncs or 0) > 0,
        )
        for c, ncs in filas
    ]


@router.post("/sesiones/{sesion_id}/cerrar", response_model=SesionOut)
async def cerrar_sesion(
    sesion_id: uuid.UUID,
    body: SesionCerrarIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    sesion = await _sesion_de(db, usuario.tenant_id, sesion_id)
    if sesion.estado != "abierta":
        raise HTTPException(status_code=409, detail="La sesión ya está cerrada")
    if sesion.cajero_id != usuario.id and usuario.nivel_acceso > NIVEL_SUPERVISOR:
        raise HTTPException(
            status_code=403, detail="Solo el cajero o un supervisor pueden cerrar la sesión"
        )
    resumen = await _resumen_sesion(db, sesion)
    por_medio = {m.medio: m.total for m in resumen.medios}
    otros = sum(
        (t for m, t in por_medio.items() if m not in ("efectivo", "tarjeta", "mercadopago")),
        Decimal("0"),
    )
    sesion.estado = "cerrada"
    sesion.cerrada_at = datetime.now(timezone.utc)
    sesion.cantidad_tickets = resumen.cantidad_tickets
    sesion.total_ventas = resumen.total_ventas
    sesion.cobrado_efectivo = por_medio.get("efectivo", Decimal("0"))
    sesion.cobrado_tarjeta = por_medio.get("tarjeta", Decimal("0"))
    sesion.cobrado_mercadopago = por_medio.get("mercadopago", Decimal("0"))
    sesion.cobrado_otros = otros
    sesion.efectivo_teorico = resumen.efectivo_teorico
    sesion.efectivo_contado = body.efectivo_contado
    sesion.diferencia = (
        body.efectivo_contado - resumen.efectivo_teorico
        if body.efectivo_contado is not None
        else None
    )
    sesion.observaciones = body.observaciones
    await db.commit()
    sesion = await db.scalar(select(PosSesion).where(PosSesion.id == sesion_id))
    return await _sesion_out(db, sesion)


# ===== Búsqueda rápida =====

@router.get("/buscar", response_model=list[ResultadoBusqueda])
async def buscar(
    q: str,
    caja_id: uuid.UUID,
    usuario: Usuario = Depends(requiere("pos", "ver")),
    db: AsyncSession = Depends(get_db),
):
    """Lookup de mostrador: código de barras de variante → código de barras
    de artículo → código interno (matches exactos), y si no, búsqueda por
    texto. El precio ya viene resuelto con la lista de la caja."""
    caja = await _caja_de(db, usuario.tenant_id, caja_id)
    cotizacion = await _cotizacion_vigente(db, usuario.tenant_id)
    q = q.strip()
    if not q:
        return []

    # 0) etiqueta de balanza EAN-13 (F12-b): prefijo configurado + DV válido
    etiqueta_balanza = await _resolver_etiqueta_balanza(
        db, usuario.tenant_id, q, caja, cotizacion
    )
    if etiqueta_balanza is not None:
        return [etiqueta_balanza]

    async def _envase_de(art: Articulo) -> EnvaseBusqueda | None:
        if art.envase_articulo_id is None:
            return None
        env = await db.scalar(
            select(Articulo).where(
                Articulo.id == art.envase_articulo_id,
                Articulo.tenant_id == usuario.tenant_id,
                Articulo.activo.is_(True),
            )
        )
        if env is None:
            return None
        return EnvaseBusqueda(
            articulo_id=env.id,
            codigo=env.codigo,
            descripcion=env.descripcion,
            precio=_precio_final(env, None, caja.lista_precios, cotizacion),
        )

    async def _con_variantes(articulo_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        if not articulo_ids:
            return set()
        filas = await db.execute(
            select(ArticuloVariante.articulo_id)
            .where(
                ArticuloVariante.tenant_id == usuario.tenant_id,
                ArticuloVariante.articulo_id.in_(articulo_ids),
                ArticuloVariante.activo.is_(True),
            )
            .distinct()
        )
        return {x for (x,) in filas}

    async def _variantes_de(art: Articulo) -> list[VarianteBusqueda]:
        filas = (
            await db.scalars(
                select(ArticuloVariante).where(
                    ArticuloVariante.tenant_id == usuario.tenant_id,
                    ArticuloVariante.articulo_id == art.id,
                    ArticuloVariante.activo.is_(True),
                )
            )
        ).all()
        etiquetas = await _etiquetas_valores(db, usuario.tenant_id, list(filas))
        return [
            VarianteBusqueda(
                variante_id=v.id,
                descripcion=etiquetas.get(v.id, ""),
                codigo_barras=v.codigo_barras,
                precio=_precio_final(art, v, caja.lista_precios, cotizacion),
            )
            for v in filas
        ]

    def _item(
        art: Articulo,
        variante: ArticuloVariante | None,
        variante_desc: str | None,
        exacto: bool,
        tiene_variantes: bool,
        variantes: list[VarianteBusqueda],
        envase: EnvaseBusqueda | None = None,
    ) -> ResultadoBusqueda:
        descripcion = art.descripcion
        if variante_desc:
            descripcion = f"{art.descripcion} · {variante_desc}"
        return ResultadoBusqueda(
            articulo_id=art.id,
            variante_id=variante.id if variante else None,
            codigo=art.codigo,
            descripcion=descripcion,
            precio=_precio_final(art, variante, caja.lista_precios, cotizacion),
            tasa_iva=art.tasa_iva,
            pesable=art.pesable,
            exacto=exacto,
            tiene_variantes=tiene_variantes,
            variantes=variantes,
            envase=envase,
        )

    # 1) código de barras de VARIANTE (exacto)
    fila = (
        await db.execute(
            select(ArticuloVariante, Articulo)
            .join(Articulo, Articulo.id == ArticuloVariante.articulo_id)
            .where(
                ArticuloVariante.tenant_id == usuario.tenant_id,
                ArticuloVariante.codigo_barras == q,
                ArticuloVariante.activo.is_(True),
                Articulo.activo.is_(True),
            )
        )
    ).first()
    if fila is not None:
        variante, art = fila
        etiquetas = await _etiquetas_valores(db, usuario.tenant_id, [variante])
        return [
            _item(art, variante, etiquetas.get(variante.id), True, True, [],
                  await _envase_de(art))
        ]

    # 2) código de barras, código interno o PLU de balanza de ARTÍCULO (exacto)
    condiciones_exactas = [
        Articulo.codigo_barras == q,
        func.upper(Articulo.codigo) == q.upper(),
    ]
    if q.isdigit():
        condiciones_exactas.append(Articulo.codigo_balanza == str(int(q)))
    art = await db.scalar(
        select(Articulo).where(
            Articulo.tenant_id == usuario.tenant_id,
            Articulo.activo.is_(True),
            or_(*condiciones_exactas),
        )
    )
    if art is not None:
        tiene = art.id in await _con_variantes([art.id])
        variantes = await _variantes_de(art) if tiene else []
        return [_item(art, None, None, True, tiene, variantes, await _envase_de(art))]

    # 3) búsqueda por texto
    patron = f"%{q}%"
    filas = (
        await db.scalars(
            select(Articulo)
            .where(
                Articulo.tenant_id == usuario.tenant_id,
                Articulo.activo.is_(True),
                or_(
                    Articulo.descripcion.ilike(patron),
                    Articulo.codigo.ilike(patron),
                    Articulo.codigo_barras.ilike(patron),
                ),
            )
            .order_by(Articulo.descripcion)
            .limit(12)
        )
    ).all()
    con_variantes = await _con_variantes([a.id for a in filas])
    resultados = []
    for a in filas:
        tiene = a.id in con_variantes
        variantes = await _variantes_de(a) if tiene else []
        resultados.append(_item(a, None, None, False, tiene, variantes, await _envase_de(a)))
    return resultados


# ===== Venta =====

@router.post("/ventas/calcular", response_model=CalculoOut)
async def calcular_venta(
    body: VentaCalcularIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Dry-run: totales EXACTOS (redondeo fiscal por alícuota) antes de cobrar.
    No escribe nada."""
    caja = await _caja_de(db, usuario.tenant_id, body.caja_id)
    tenant = await db.scalar(select(Tenant).where(Tenant.id == usuario.tenant_id))
    receptor, calculo, letra = await _armar_venta(
        db, tenant, caja, body.cliente_id, body.items, body.descuento_pct
    )
    return _calculo_out(receptor, calculo, letra)


@router.post("/ventas", response_model=ComprobanteOut, status_code=status.HTTP_201_CREATED)
async def crear_venta(
    body: VentaIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Venta de mostrador en un paso: factura + CAE + stock + medios + sesión,
    todo o nada en una transacción."""
    sesion = await _sesion_abierta_de(db, usuario, body.sesion_id)
    caja = await _caja_de(db, usuario.tenant_id, sesion.caja_id)
    tenant = await db.scalar(select(Tenant).where(Tenant.id == usuario.tenant_id))
    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )
    receptor, calculo, letra = await _armar_venta(
        db, tenant, caja, body.cliente_id, body.items, body.descuento_pct
    )

    cobrado = sum((m.importe for m in body.medios), Decimal("0"))
    if cobrado != calculo["total"]:
        raise HTTPException(
            status_code=409,
            detail=f"Los medios de pago (${cobrado}) no coinciden con el total "
            f"(${calculo['total']}). Recalculá la venta.",
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
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, comp.id))


@router.post("/ventas/{comp_id}/anular", response_model=ComprobanteOut)
async def anular_venta(
    comp_id: uuid.UUID,
    body: AnularIn,
    usuario: Usuario = Depends(requiere("pos", "editar")),
    db: AsyncSession = Depends(get_db),
):
    """Anulación de un ticket emitido con autorización de SUPERVISOR (patrón
    legacy): valida credenciales + nivel y emite la NC espejo fiscal en el
    acto, devolviendo los medios de la venta original (negativos en el arqueo
    de la sesión ACTUAL)."""
    sesion = await _sesion_abierta_de(db, usuario, body.sesion_id)

    supervisor = await db.scalar(
        select(Usuario).where(Usuario.email == body.supervisor_email.lower().strip())
    )
    # 403 y no 401: el request del cajero ESTÁ autenticado (JWT válido) — un
    # 401 acá dispara el "sesión vencida" global del frontend y desloguea la caja.
    if (
        supervisor is None
        or supervisor.tenant_id != usuario.tenant_id
        or not supervisor.activo
        or not verify_password(body.supervisor_password, supervisor.password_hash)
    ):
        raise HTTPException(status_code=403, detail="Credenciales de supervisor inválidas")
    if supervisor.nivel_acceso > NIVEL_SUPERVISOR:
        raise HTTPException(
            status_code=403, detail="El usuario no tiene nivel de supervisor"
        )

    factura = await _cargar(db, usuario.tenant_id, comp_id)
    if factura.pos_sesion_id is None:
        raise HTTPException(
            status_code=409, detail="Ese comprobante no es una venta POS"
        )
    ya = await db.scalar(
        select(func.count())
        .select_from(Comprobante)
        .join(TipoComprobante, TipoComprobante.codigo == Comprobante.tipo_codigo)
        .where(
            Comprobante.comprobante_asociado_id == factura.id,
            Comprobante.estado == "emitido",
            TipoComprobante.clase == "nota_credito",
        )
    )
    if (ya or 0) > 0:
        raise HTTPException(status_code=409, detail="El ticket ya fue anulado")

    config = await db.scalar(
        select(ArcaConfig).where(ArcaConfig.tenant_id == usuario.tenant_id)
    )
    nc = await crear_nc_espejo_core(db, factura, usuario)
    nc.pos_sesion_id = sesion.id
    motivo = f" · Motivo: {body.motivo.strip()}" if body.motivo and body.motivo.strip() else ""
    nc.observaciones = (
        f"{nc.observaciones or ''} — Anulación POS autorizada por "
        f"{supervisor.nombre}{motivo}"
    )[:500]
    nc = await _cargar(db, usuario.tenant_id, nc.id)

    await emitir_core(db, nc, usuario, config)

    # Devolución con los medios de la venta original (efectivo si no hubiera)
    medios_orig = (
        await db.scalars(
            select(VentaMedio).where(VentaMedio.comprobante_id == factura.id)
        )
    ).all()
    if medios_orig:
        for m in medios_orig:
            db.add(
                VentaMedio(
                    tenant_id=usuario.tenant_id,
                    comprobante_id=nc.id,
                    pos_sesion_id=sesion.id,
                    medio=m.medio,
                    importe=m.importe,
                    referencia=m.referencia,
                )
            )
    else:
        db.add(
            VentaMedio(
                tenant_id=usuario.tenant_id,
                comprobante_id=nc.id,
                pos_sesion_id=sesion.id,
                medio="efectivo",
                importe=factura.total,
            )
        )
    await db.commit()
    return _out(await _cargar(db, usuario.tenant_id, nc.id))
