"""Reglas de dominio de Compras (Fase 4).

Acá vive lo que NO decide el usuario: el cálculo de totales según la letra
del comprobante del proveedor, la numeración interna de órdenes de pago y la
actualización de costos (artículo + articulo_proveedores) al registrar.

Criterio de letra (espejo contable de ventas):
- Letra A: los costos se cargan NETOS; el IVA se discrimina por ítem y es
  crédito fiscal (no forma parte del costo).
- Letra B/C/X: los importes son FINALES (IVA adentro, no computable): todo el
  importe es costo. neto_gravado acumula los finales e iva queda 0, igual que
  la letra C en ventas.
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Articulo, ArticuloProveedor, NumeracionCompras
from app.services.ventas import r2, validar_tasa

_CUATRO = Decimal("0.0001")
_CIEN = Decimal("100")


def _tras_bonifs(valor: Decimal, bonif_1: Decimal, bonif_2: Decimal) -> Decimal:
    """Bonificaciones en cadena del proveedor (ART_PROV/COMPRASD del legacy)."""
    return valor * (_CIEN - bonif_1) / _CIEN * (_CIEN - bonif_2) / _CIEN


def calcular_compra(
    items: list[dict],
    letra: str,
    no_gravado: Decimal = Decimal("0"),
    exento: Decimal = Decimal("0"),
    percepcion_iva: Decimal = Decimal("0"),
    percepcion_iibb: Decimal = Decimal("0"),
    impuestos_internos: Decimal = Decimal("0"),
    otros_tributos: Decimal = Decimal("0"),
    redondeo: Decimal = Decimal("0"),
) -> dict:
    """Calcula ítems y totales de un comprobante de compra.

    `items`: dicts con cantidad, costo_unitario, bonif_1, bonif_2, tasa_iva.
    Los tributos de cabecera (percepciones, internos, otros) se cargan tal
    cual figuran en el papel; `redondeo` absorbe diferencias de centavos.
    """
    items_calc: list[dict] = []
    neto_gravado = Decimal("0")
    iva_total = Decimal("0")

    for orden, it in enumerate(items):
        cantidad = Decimal(it["cantidad"])
        costo = Decimal(it["costo_unitario"]).quantize(_CUATRO, rounding=ROUND_HALF_UP)
        bonif_1 = Decimal(it.get("bonif_1") or 0)
        bonif_2 = Decimal(it.get("bonif_2") or 0)
        tasa = Decimal(it["tasa_iva"])
        if letra == "A":
            tasa = validar_tasa(tasa)

        neto = _tras_bonifs(cantidad * costo, bonif_1, bonif_2).quantize(
            _CUATRO, rounding=ROUND_HALF_UP
        )
        importe_neto = r2(neto)
        importe_iva = r2(importe_neto * tasa / _CIEN) if letra == "A" else Decimal("0")
        items_calc.append(
            {
                **it,
                "orden": orden,
                "costo_unitario": costo,
                "tasa_iva": tasa,
                "importe_neto": importe_neto,
                "importe_iva": importe_iva,
                "importe_total": importe_neto + importe_iva,
            }
        )
        neto_gravado += importe_neto
        iva_total += importe_iva

    total = (
        neto_gravado + iva_total + no_gravado + exento + percepcion_iva
        + percepcion_iibb + impuestos_internos + otros_tributos + redondeo
    )
    return {
        "items": items_calc,
        "neto_gravado": neto_gravado,
        "no_gravado": no_gravado,
        "exento": exento,
        "iva": iva_total,
        "percepcion_iva": percepcion_iva,
        "percepcion_iibb": percepcion_iibb,
        "impuestos_internos": impuestos_internos,
        "otros_tributos": otros_tributos,
        "redondeo": redondeo,
        "total": total,
    }


async def proximo_numero_op(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Reserva el próximo número de orden de pago (documento interno del
    tenant, sin punto de venta). Fila lockeada, patrón proximo_numero de ventas."""
    fila = await db.scalar(
        select(NumeracionCompras)
        .where(NumeracionCompras.tenant_id == tenant_id, NumeracionCompras.tipo == "OP")
        .with_for_update()
    )
    if fila is None:
        fila = NumeracionCompras(tenant_id=tenant_id, tipo="OP", ultimo=0)
        db.add(fila)
        await db.flush()
        fila = await db.scalar(
            select(NumeracionCompras).where(NumeracionCompras.id == fila.id).with_for_update()
        )
    fila.ultimo += 1
    return fila.ultimo


def costo_neto_unitario(
    costo_unitario: Decimal, bonif_1: Decimal, bonif_2: Decimal, tasa: Decimal, letra: str
) -> Decimal:
    """Costo unitario NETO (sin IVA) tras bonificaciones. Con letra distinta
    de A el costo cargado es final: se le extrae el IVA con la tasa del ítem
    solo para comparar/guardar en convención neta."""
    neto = _tras_bonifs(costo_unitario, bonif_1, bonif_2)
    if letra != "A":
        neto = neto / (Decimal("1") + tasa / _CIEN)
    return neto.quantize(_CUATRO, rounding=ROUND_HALF_UP)


async def actualizar_costos_articulos(db: AsyncSession, compra) -> None:
    """Al registrar una factura/ND de compra: actualiza el costo del artículo
    (en SU convención con/sin IVA, flag COSTIVA del legacy) y hace upsert de
    articulo_proveedores (lista neta + bonifs + ultima_compra) — la base del
    comparativo por proveedor."""
    ids = [i.articulo_id for i in compra.items if i.articulo_id]
    if not ids:
        return
    articulos = {
        a.id: a
        for a in await db.scalars(
            select(Articulo)
            .where(Articulo.id.in_(ids), Articulo.tenant_id == compra.tenant_id)
            .with_for_update()
        )
    }
    filas_ap = {
        ap.articulo_id: ap
        for ap in await db.scalars(
            select(ArticuloProveedor).where(
                ArticuloProveedor.tenant_id == compra.tenant_id,
                ArticuloProveedor.proveedor_id == compra.proveedor_id,
                ArticuloProveedor.articulo_id.in_(ids),
            )
        )
    }
    for item in compra.items:
        art = articulos.get(item.articulo_id) if item.articulo_id else None
        if art is None:
            continue
        neto = costo_neto_unitario(
            item.costo_unitario, item.bonif_1, item.bonif_2, item.tasa_iva, compra.letra
        )
        if compra.actualiza_costos:
            factor_iva = Decimal("1") + item.tasa_iva / _CIEN
            art.costo = (
                (neto * factor_iva) if art.costo_con_iva else neto
            ).quantize(_CUATRO, rounding=ROUND_HALF_UP)
            art.updated_at = func.now()
            if art.proveedor_habitual_id is None:
                art.proveedor_habitual_id = compra.proveedor_id

        # lista neta del proveedor: el costo del ítem SIN bonificar, en neto
        lista_neta = item.costo_unitario
        if compra.letra != "A":
            lista_neta = lista_neta / (Decimal("1") + item.tasa_iva / _CIEN)
        lista_neta = lista_neta.quantize(_CUATRO, rounding=ROUND_HALF_UP)

        ap = filas_ap.get(item.articulo_id)
        if ap is None:
            ap = ArticuloProveedor(
                tenant_id=compra.tenant_id,
                articulo_id=item.articulo_id,
                proveedor_id=compra.proveedor_id,
            )
            db.add(ap)
            filas_ap[item.articulo_id] = ap
        ap.costo = lista_neta
        ap.bonif_1 = item.bonif_1
        ap.bonif_2 = item.bonif_2
        ap.ultima_compra = compra.fecha
        ap.updated_at = func.now()
