"""Reglas de dominio de Ventas (Fase 3) — ver docs/FACTURACION-ARCA.md.

Acá vive lo que NO puede decidir el usuario: la letra del comprobante, los
códigos ARCA, el cálculo de totales/alícuotas con el criterio de redondeo que
valida WSFEv1, y la numeración local con lock de fila.
"""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Numeracion

# Alícuotas de IVA vigentes → Id de la tabla de alícuotas de WSFEv1 (AlicIva.Id)
ALICUOTAS_ARCA: dict[Decimal, int] = {
    Decimal("0"): 3,
    Decimal("2.5"): 9,
    Decimal("5"): 8,
    Decimal("10.5"): 4,
    Decimal("21"): 5,
    Decimal("27"): 6,
}

# Tipo de documento de la BUE → DocTipo de ARCA
DOC_TIPO_ARCA = {"CUIT": 80, "CUIL": 86, "DNI": 96, "SD": 99}

# Condición IVA del receptor → CondicionIVAReceptorId (RG 5616/2024,
# obligatorio en el WS desde el 1/9/2026; ZGC lo envía siempre)
COND_IVA_RECEPTOR_ID = {"RI": 1, "EX": 4, "CF": 5, "MT": 6}

_DOS = Decimal("0.01")
_CUATRO = Decimal("0.0001")


def r2(valor: Decimal) -> Decimal:
    return valor.quantize(_DOS, rounding=ROUND_HALF_UP)


def letra_comprobante(condicion_emisor: str, condicion_receptor: str) -> str:
    """Matriz emisor × receptor (docs/FACTURACION-ARCA.md §3). El usuario no
    la elige: RI→RI/MT: A (RG 5003/2021); RI→EX/CF: B; emisor MT/EX: C."""
    if condicion_emisor == "RI":
        return "A" if condicion_receptor in ("RI", "MT") else "B"
    return "C"


def tipo_codigo_para(clase: str, letra: str) -> str:
    """('factura','A') -> 'FA' · ('nota_credito','B') -> 'NCB' · internos: fijo."""
    por_clase = {"factura": "F", "nota_debito": "ND", "nota_credito": "NC"}
    if clase in por_clase:
        return por_clase[clase] + letra
    return {"presupuesto": "PRE", "remito": "REM", "recibo": "REC"}[clase]


def validar_tasa(tasa: Decimal) -> Decimal:
    if tasa not in ALICUOTAS_ARCA:
        validas = ", ".join(str(t) for t in ALICUOTAS_ARCA)
        raise ValueError(f"Tasa de IVA {tasa} inválida (válidas: {validas})")
    return tasa


def calcular_comprobante(
    items: list[dict],
    letra: str,
    descuento_pct: Decimal = Decimal("0"),
    precios_con_iva: bool = False,
) -> dict:
    """Calcula ítems, alícuotas y totales.

    - `items`: dicts con cantidad, precio_unitario, bonif_pct, tasa_iva.
    - `precios_con_iva`: si el precio cargado es final, se convierte a neto
      con la tasa del ítem (el neto es lo que siempre se guarda).
    - Letra C (emisor monotributo/exento): sin discriminación — todo al neto,
      IVA 0, sin alícuotas (así lo exige el WS para código 11/12/13).
    - Redondeo criterio WSFEv1: las bases se acumulan por alícuota con 4
      decimales y se redondean a 2 POR alícuota; el IVA se calcula sobre la
      base redondeada. ImpTotal = suma exacta de las partes.
    - MVP: tasa 0 se informa como alícuota 0% (Id 3); no gravado/exento en 0.
    """
    factor_dto = (Decimal("100") - descuento_pct) / Decimal("100")
    items_calc: list[dict] = []
    bases: dict[Decimal, Decimal] = {}  # tasa -> neto acumulado (4 dec)

    for orden, it in enumerate(items):
        cantidad = Decimal(it["cantidad"])
        precio = Decimal(it["precio_unitario"])
        bonif = Decimal(it.get("bonif_pct") or 0)
        tasa = validar_tasa(Decimal(it["tasa_iva"])) if letra != "C" else Decimal(it["tasa_iva"])

        if letra != "C" and precios_con_iva:
            precio = precio / (Decimal("1") + tasa / Decimal("100"))
        precio = precio.quantize(_CUATRO, rounding=ROUND_HALF_UP)

        neto = cantidad * precio * (Decimal("100") - bonif) / Decimal("100") * factor_dto
        neto = neto.quantize(_CUATRO, rounding=ROUND_HALF_UP)
        importe_neto = r2(neto)
        importe_iva = Decimal("0") if letra == "C" else r2(importe_neto * tasa / Decimal("100"))
        items_calc.append(
            {
                **it,
                "orden": orden,
                "precio_unitario": precio,
                "tasa_iva": tasa,
                "importe_neto": importe_neto,
                "importe_iva": importe_iva,
                "importe_total": importe_neto + importe_iva,
            }
        )
        if letra != "C":
            bases[tasa] = bases.get(tasa, Decimal("0")) + neto

    alicuotas: list[dict] = []
    neto_gravado = Decimal("0")
    iva_total = Decimal("0")
    for tasa in sorted(bases):
        base = r2(bases[tasa])
        importe = r2(base * tasa / Decimal("100"))
        alicuotas.append(
            {"tasa": tasa, "codigo_arca": ALICUOTAS_ARCA[tasa], "base": base, "importe": importe}
        )
        neto_gravado += base
        iva_total += importe

    if letra == "C":
        neto_gravado = sum((i["importe_neto"] for i in items_calc), Decimal("0"))

    total = neto_gravado + iva_total
    return {
        "items": items_calc,
        "alicuotas": alicuotas,
        "neto_gravado": neto_gravado,
        "neto_no_gravado": Decimal("0"),
        "exento": Decimal("0"),
        "iva": iva_total,
        "otros_tributos": Decimal("0"),
        "total": total,
        # Transparencia fiscal Ley 27.743 (se imprime en B/C a consumidor final)
        "iva_contenido": iva_total if letra != "A" else None,
        "otros_imp_indirectos": Decimal("0") if letra != "A" else None,
    }


async def proximo_numero(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    punto_venta_id: uuid.UUID,
    tipo_codigo: str,
) -> int:
    """Reserva el próximo número local (fila lockeada). Para internos es LA
    numeración; para fiscales es espejo — el número real lo da ARCA y después
    se sincroniza con sincronizar_numero()."""
    fila = await db.scalar(
        select(Numeracion)
        .where(
            Numeracion.tenant_id == tenant_id,
            Numeracion.punto_venta_id == punto_venta_id,
            Numeracion.tipo_codigo == tipo_codigo,
        )
        .with_for_update()
    )
    if fila is None:
        fila = Numeracion(
            tenant_id=tenant_id,
            punto_venta_id=punto_venta_id,
            tipo_codigo=tipo_codigo,
            ultimo=0,
        )
        db.add(fila)
        await db.flush()
        fila = await db.scalar(
            select(Numeracion).where(Numeracion.id == fila.id).with_for_update()
        )
    fila.ultimo += 1
    return fila.ultimo


async def sincronizar_numero(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    punto_venta_id: uuid.UUID,
    tipo_codigo: str,
    numero: int,
) -> None:
    """Deja el contador local espejando el último número autorizado por ARCA."""
    fila = await db.scalar(
        select(Numeracion)
        .where(
            Numeracion.tenant_id == tenant_id,
            Numeracion.punto_venta_id == punto_venta_id,
            Numeracion.tipo_codigo == tipo_codigo,
        )
        .with_for_update()
    )
    if fila is None:
        db.add(
            Numeracion(
                tenant_id=tenant_id,
                punto_venta_id=punto_venta_id,
                tipo_codigo=tipo_codigo,
                ultimo=numero,
            )
        )
    elif numero > fila.ultimo:
        fila.ultimo = numero
