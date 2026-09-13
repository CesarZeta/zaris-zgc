"""Saldo inicial de cuenta corriente (migración 029 — DISENO-CONTABILIDAD.md §7).

Vehículo para cargar la deuda/crédito VIVO de un cliente o proveedor que
llega de otro sistema (o del legacy) sin pasar por un documento fiscal. Es un
`comprobantes` / `compras` SIN ítems ni alícuotas: `total = saldo = importe`,
neto/IVA en 0, letra X, clase `saldo_inicial`, y nace ya emitido/registrado
(no hay borrador: no hay nada que editar — se anula y se carga otro).

Qué toca y qué no:
- SÍ: cuenta corriente (saldos, deudas imputables por recibos/OP, créditos
  usables como fuente), listados, backup, sugerencia de apertura contable.
- NO: ARCA, stock, libros IVA/CITI, contabilidad derivada — todo eso filtra
  `tipo.fiscal`, y estos tipos nacen con `fiscal=false, cta_cte=true`.

Los dos cores son SIN commit (patrón emitir_core): el router comitea en su
propia transacción, y los migradores del legacy los reusan in-process.
Validaciones de dominio → `ValueError` (el router lo traduce a 422); las
guardas de existencia/estado de cliente, proveedor y PV vienen de los helpers
de los routers (`_snapshot_receptor`, `_snapshot_proveedor`, `validar_pv_nodo`)
y ya responden con `HTTPException` 404/409/422.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.compras import _snapshot_proveedor
from app.api.v1.comprobantes import _snapshot_receptor
from app.core.fechas import hoy
from app.models import (
    Compra,
    CompraVencimiento,
    Comprobante,
    ComprobanteVencimiento,
    PuntoVenta,
)
from app.services import compras as sc
from app.services import ventas as sv
from app.services.pv_nodo import validar_pv_nodo

# sentido (lo que elige el usuario) → tipo del catálogo (029)
TIPOS_VENTA = {"deudor": "SAL", "a_favor": "SAF"}  # +1 nos debe / −1 le debemos
TIPOS_COMPRA = {"debemos": "SALP", "nos_deben": "SAFP"}  # +1 le debemos / −1 nos debe

CLASE = "saldo_inicial"
LETRA = "X"
_CERO = Decimal("0")


# ===== Validaciones comunes =====

def _normalizar_importe(importe) -> Decimal:
    try:
        valor = sv.r2(Decimal(str(importe)))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Importe inválido")
    if valor <= _CERO:
        raise ValueError("El importe del saldo inicial debe ser mayor a cero")
    return valor


def _normalizar_fecha(fecha: date | None) -> date:
    fecha = fecha or hoy()
    if fecha > hoy():
        raise ValueError("La fecha del saldo inicial no puede ser futura")
    return fecha


def _normalizar_observaciones(observaciones: str | None) -> str | None:
    return (observaciones or "").strip() or None


async def _resolver_pv(
    db: AsyncSession, tenant_id: uuid.UUID, punto_venta_id: uuid.UUID | None
) -> PuntoVenta:
    """PV con el que numera el saldo inicial de venta. Si el llamador no
    lo indica, el primer PV activo del tenant (por número) que la NUBE pueda
    operar. Un PV en manos de un nodo LAN queda excluido SIEMPRE: la nube
    rechaza imputar documentos de esos PV (cobranza cruzada bloqueada,
    cobranzas.py) y el saldo quedaría incobrable desde la gestión."""
    if punto_venta_id is not None:
        pv = await db.scalar(
            select(PuntoVenta).where(
                PuntoVenta.id == punto_venta_id,
                PuntoVenta.tenant_id == tenant_id,
                PuntoVenta.activo.is_(True),
            )
        )
        if pv is None:
            raise HTTPException(status_code=404, detail="Punto de venta no encontrado o inactivo")
        await validar_pv_nodo(db, tenant_id, pv.id)
        return pv

    candidatos = (
        await db.scalars(
            select(PuntoVenta)
            .where(PuntoVenta.tenant_id == tenant_id, PuntoVenta.activo.is_(True))
            .order_by(PuntoVenta.numero)
        )
    ).all()
    for pv in candidatos:
        try:
            await validar_pv_nodo(db, tenant_id, pv.id)
        except HTTPException:
            continue  # operado por un nodo: probar el siguiente
        return pv
    raise ValueError(
        "No hay un punto de venta activo disponible en la gestión para numerar "
        "el saldo inicial — dá de alta uno en Configuración"
    )


# ===== Ventas: cliente =====

async def crear_saldo_inicial_venta(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID | None,
    cliente_id: uuid.UUID,
    importe,
    sentido: str,
    fecha: date | None = None,
    observaciones: str | None = None,
    punto_venta_id: uuid.UUID | None = None,
    permitir_bloqueado: bool = False,
) -> Comprobante:
    """Crea (sin commit) el SAL (deudor, +1) o SAF (a favor, −1) de un
    cliente, ya EMITIDO, con `total = saldo = importe`. El SAL lleva un único
    vencimiento a la fecha del documento (deuda ya exigible: entra a la
    morosidad desde el día uno); el SAF no vence. Devuelve la instancia
    flusheada; el llamador comitea y relee con `populate_existing`."""
    if sentido not in TIPOS_VENTA:
        raise ValueError("Sentido inválido: usá 'deudor' o 'a_favor'")
    if cliente_id is None:
        raise ValueError("El saldo inicial requiere un cliente (no aplica a consumidor final)")
    tipo_codigo = TIPOS_VENTA[sentido]
    importe = _normalizar_importe(importe)
    fecha = _normalizar_fecha(fecha)

    # permitir_bloqueado: solo los migradores del legacy (el deudor suele estar
    # bloqueado por esa misma deuda); la API siempre pasa False → 409
    receptor = await _snapshot_receptor(db, tenant_id, cliente_id, permitir_bloqueado)
    pv = await _resolver_pv(db, tenant_id, punto_venta_id)
    numero = await sv.proximo_numero(db, tenant_id, pv.id, tipo_codigo)

    comp = Comprobante(
        tenant_id=tenant_id,
        punto_venta_id=pv.id,
        tipo_codigo=tipo_codigo,
        letra=LETRA,
        numero=numero,
        fecha=fecha,
        contado=False,
        condicion_venta_id=None,
        condicion_venta_desc=None,
        lista_precios=1,
        deposito_id=None,
        actualiza_stock=False,
        moneda="PES",
        cotizacion=Decimal("1"),
        descuento_pct=_CERO,
        descuento_importe=_CERO,
        neto_gravado=_CERO,
        neto_no_gravado=_CERO,
        exento=_CERO,
        iva=_CERO,
        otros_tributos=_CERO,
        total=importe,
        iva_contenido=None,
        otros_imp_indirectos=None,
        saldo=importe,
        estado="emitido",
        comprobante_asociado_id=None,
        origen_id=None,
        pos_sesion_id=None,
        # no es una venta de nadie: sin vendedor (la comisión por venta filtra
        # `fiscal` igual; la de cobranza toma el vendedor del recibo)
        vendedor_id=None,
        observaciones=_normalizar_observaciones(observaciones),
        emitido_at=datetime.now(timezone.utc),
        emitido_por=usuario_id,
        creado_por=usuario_id,
        **receptor,
    )
    db.add(comp)
    await db.flush()

    if tipo_codigo == "SAL":
        db.add(
            ComprobanteVencimiento(
                tenant_id=tenant_id,
                comprobante_id=comp.id,
                nro_cuota=1,
                fecha_vto=fecha,
                importe=importe,
            )
        )
        await db.flush()
    return comp


# ===== Compras: proveedor =====

async def crear_saldo_inicial_compra(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    usuario_id: uuid.UUID | None,
    proveedor_id: uuid.UUID,
    importe,
    sentido: str,
    fecha: date | None = None,
    observaciones: str | None = None,
    permitir_inactivo: bool = False,
) -> Compra:
    """Crea (sin commit) el SALP (le debemos, +1) o SAFP (nos debe, −1) de un
    proveedor, ya REGISTRADO, con `total = saldo = importe`. Numera con la
    numeración interna del tenant (`numeracion_compras` tipo SALP/SAFP) y
    `punto_venta = 0`, así el UNIQUE (tenant, proveedor, tipo, pv, numero)
    no choca. El SALP lleva un único vencimiento a la fecha; el SAFP no.
    `periodo_iva` queda NULL: no es fiscal, el libro de compras lo filtra."""
    if sentido not in TIPOS_COMPRA:
        raise ValueError("Sentido inválido: usá 'debemos' o 'nos_deben'")
    if proveedor_id is None:
        raise ValueError("El saldo inicial requiere un proveedor")
    tipo_codigo = TIPOS_COMPRA[sentido]
    importe = _normalizar_importe(importe)
    fecha = _normalizar_fecha(fecha)

    # permitir_inactivo: solo los migradores del legacy; la API pasa False → 409
    snapshot = await _snapshot_proveedor(db, tenant_id, proveedor_id, permitir_inactivo)
    numero = await sc.proximo_numero_op(db, tenant_id, tipo_codigo)

    compra = Compra(
        tenant_id=tenant_id,
        tipo_codigo=tipo_codigo,
        letra=LETRA,
        punto_venta=0,
        numero=numero,
        fecha=fecha,
        periodo_iva=None,
        contado=False,
        condicion_compra_id=None,
        condicion_desc=None,
        deposito_id=None,
        actualiza_stock=False,
        actualiza_costos=False,
        neto_gravado=_CERO,
        no_gravado=_CERO,
        exento=_CERO,
        iva=_CERO,
        percepcion_iva=_CERO,
        percepcion_iibb=_CERO,
        impuestos_internos=_CERO,
        otros_tributos=_CERO,
        redondeo=_CERO,
        total=importe,
        saldo=importe,
        estado="registrado",
        compra_asociada_id=None,
        observaciones=_normalizar_observaciones(observaciones),
        registrado_at=datetime.now(timezone.utc),
        registrado_por=usuario_id,
        creado_por=usuario_id,
        **snapshot,
    )
    db.add(compra)
    await db.flush()

    if tipo_codigo == "SALP":
        db.add(
            CompraVencimiento(
                tenant_id=tenant_id,
                compra_id=compra.id,
                nro_cuota=1,
                fecha_vto=fecha,
                importe=importe,
            )
        )
        await db.flush()
    return compra
