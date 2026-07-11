"""Fase 9 — Motor de asientos DERIVADOS (sin commit; docs/DISENO-CONTABILIDAD.md).

La contabilidad se deriva de los documentos operativos: cada builder lee una
fuente (comprobantes, recibos, compras, OP, caja, bancos, cheques, kardex,
retenciones, cierres) y arma partida doble según `asiento_mapeos`. Regenerar un
período = borrar los asientos derivados del rango y re-derivar (los manuales
nunca se tocan). Los documentos ANULADOS generan además un asiento de reversión
fechado en su `anulado_at` (por eso la mini-fase 014 selló fechas ciertas).

Convención de líneas: monto > 0 ⇒ DEBE, monto < 0 ⇒ HABER. Todo asiento se
verifica balanceado antes de insertarse; si algo no cierra o falta un mapeo,
se saltea con warning (nunca se inserta un asiento desbalanceado).

Alcance negativo v1 (documentado en el diseño §4.5): remitos internos no
derivan (stock transitorio), anticipos de clientes quedan dentro de Deudores,
sin multi-moneda contable.
"""

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActivoCategoria,
    ActivoFijo,
    Articulo,
    Asiento,
    AsientoLinea,
    AsientoMapeo,
    CajaCierre,
    CajaMovimiento,
    Cheque,
    ChequeEvento,
    Compra,
    CompraItem,
    CompraMedio,
    Comprobante,
    ComprobanteItem,
    ContabPeriodo,
    BancoMovimiento,
    OrdenPago,
    OrdenPagoMedio,
    PlanCuenta,
    Recibo,
    ReciboMedio,
    Retencion,
    StockMovimiento,
    TipoComprobante,
    TipoComprobanteCompra,
    VentaMedio,
)

D0 = Decimal("0")
C2 = Decimal("0.01")


def _r2(x: Decimal) -> Decimal:
    return Decimal(x).quantize(C2)


# ============================================================================
# Seed: plan de cuentas argentino de comercio (esqueleto) + mapeos default.
# Sembrado LAZY por tenant (GET /contabilidad/plan), patrón roles RBAC.
# ============================================================================

# (codigo, nombre, tipo, imputable, padre_codigo)
PLAN_BASE: list[tuple[str, str, str, bool, str | None]] = [
    ("1", "ACTIVO", "activo", False, None),
    ("1.1", "Caja y Bancos", "activo", False, "1"),
    ("1.1.01", "Caja", "activo", True, "1.1"),
    ("1.1.02", "Bancos cuenta corriente", "activo", True, "1.1"),
    ("1.1.03", "Valores a depositar", "activo", True, "1.1"),
    ("1.1.04", "Tarjetas a acreditar", "activo", True, "1.1"),
    ("1.1.05", "MercadoPago a acreditar", "activo", True, "1.1"),
    ("1.1.06", "Transferencias en tránsito", "activo", True, "1.1"),
    ("1.2", "Créditos", "activo", False, "1"),
    ("1.2.01", "Deudores por ventas", "activo", True, "1.2"),
    ("1.2.02", "Deudores por cheques rechazados", "activo", True, "1.2"),
    ("1.2.03", "Retenciones y percepciones a favor", "activo", True, "1.2"),
    ("1.2.04", "IVA Crédito Fiscal", "activo", True, "1.2"),
    ("1.3", "Bienes de cambio", "activo", False, "1"),
    ("1.3.01", "Mercaderías", "activo", True, "1.3"),
    ("1.4", "Bienes de uso", "activo", False, "1"),
    ("1.4.01", "Bienes de uso", "activo", True, "1.4"),
    ("1.4.02", "Amortización acumulada bienes de uso", "activo", True, "1.4"),
    ("2", "PASIVO", "pasivo", False, None),
    ("2.1", "Deudas comerciales", "pasivo", False, "2"),
    ("2.1.01", "Proveedores", "pasivo", True, "2.1"),
    ("2.1.02", "Cheques diferidos a pagar", "pasivo", True, "2.1"),
    ("2.2", "Deudas fiscales", "pasivo", False, "2"),
    ("2.2.01", "IVA Débito Fiscal", "pasivo", True, "2.2"),
    ("2.2.02", "Retenciones a depositar", "pasivo", True, "2.2"),
    ("2.2.03", "Percepciones y otros tributos", "pasivo", True, "2.2"),
    ("3", "PATRIMONIO NETO", "pn", False, None),
    ("3.1.01", "Capital", "pn", True, "3"),
    ("3.1.02", "Resultados acumulados", "pn", True, "3"),
    ("4", "INGRESOS", "r_positivo", False, None),
    ("4.1.01", "Ventas", "r_positivo", True, "4"),
    ("4.1.02", "Intereses y otros ingresos", "r_positivo", True, "4"),
    ("4.1.03", "Sobrante de caja", "r_positivo", True, "4"),
    ("5", "EGRESOS", "r_negativo", False, None),
    ("5.1.01", "Costo de mercadería vendida", "r_negativo", True, "5"),
    ("5.1.02", "Gastos generales", "r_negativo", True, "5"),
    ("5.1.03", "Gastos bancarios", "r_negativo", True, "5"),
    ("5.1.04", "Faltante de caja", "r_negativo", True, "5"),
    ("5.1.05", "Ajustes de inventario", "r_negativo", True, "5"),
    ("5.1.06", "Ajustes por redondeo", "r_negativo", True, "5"),
    ("5.1.07", "Amortizaciones del ejercicio", "r_negativo", True, "5"),
    ("5.1.08", "Resultado por baja de bienes de uso", "r_negativo", True, "5"),
]

# Categorías de bienes de uso con vida útil sugerida (meses) — seed lazy por
# tenant junto al plan; renombrables, la vida útil real la fija cada activo.
CATEGORIAS_BASE: list[tuple[str, int]] = [
    ("Rodados", 60),
    ("Muebles y útiles", 120),
    ("Equipos de computación", 36),
    ("Instalaciones", 120),
    ("Maquinarias", 120),
    ("Inmuebles", 600),
]

# Catálogo de reglas de mapeo (para la UI) — clave NULL = default de la regla.
ORIGENES: dict[str, str] = {
    "ventas_familia": "Ventas por familia (default = sin familia)",
    "compras_familia": "Compras por familia (default = sin familia)",
    "iva_debito": "IVA Débito Fiscal",
    "iva_credito": "IVA Crédito Fiscal",
    "deudores": "Deudores por ventas (cuenta control)",
    "proveedores": "Proveedores (cuenta control)",
    "medio": "Medio de cobro/pago (efectivo/transferencia/tarjeta/mercadopago/cheque/otro)",
    "cuenta_bancaria": "Cuenta bancaria (clave = id de la cuenta)",
    "cheques_cartera": "Cheques de terceros en cartera",
    "cheques_diferidos": "Cheques propios diferidos a pagar",
    "cheques_rechazados": "Deudores por cheques rechazados",
    "concepto_caja": "Concepto de caja (clave = id del concepto)",
    "retencion": "Retenciones (clave = sufrida | practicada)",
    "percepciones": "Percepciones e imp. internos (iva/iibb/internos/otros_compra/otros_venta)",
    "banco_tipo": "Movimiento bancario manual (clave = tipo)",
    "inventario": "Mercaderías (inventario permanente)",
    "cmv": "Costo de mercadería vendida",
    "ajuste_inventario": "Ajustes de inventario",
    "diferencias_caja": "Diferencias de arqueo (sobrante | faltante)",
    "redondeo": "Ajustes por redondeo",
    "bienes_uso": "Bienes de uso (clave = id de categoría)",
    "amort_acumulada": "Amortización acumulada bienes de uso (clave = id de categoría)",
    "amort_ejercicio": "Amortizaciones del ejercicio (clave = id de categoría)",
    "baja_bienes_uso": "Resultado por baja de bienes de uso",
}

# (origen, clave, codigo_cuenta)
MAPEOS_BASE: list[tuple[str, str | None, str]] = [
    ("ventas_familia", None, "4.1.01"),
    ("compras_familia", None, "1.3.01"),
    ("iva_debito", None, "2.2.01"),
    ("iva_credito", None, "1.2.04"),
    ("deudores", None, "1.2.01"),
    ("proveedores", None, "2.1.01"),
    ("medio", "efectivo", "1.1.01"),
    ("medio", "transferencia", "1.1.02"),
    ("medio", "tarjeta", "1.1.04"),
    ("medio", "mercadopago", "1.1.05"),
    ("medio", "cheque", "1.1.03"),
    ("medio", "otro", "1.1.01"),
    ("cuenta_bancaria", None, "1.1.02"),
    ("cheques_cartera", None, "1.1.03"),
    ("cheques_diferidos", None, "2.1.02"),
    ("cheques_rechazados", None, "1.2.02"),
    ("concepto_caja", None, "5.1.02"),
    ("retencion", "sufrida", "1.2.03"),
    ("retencion", "practicada", "2.2.02"),
    ("percepciones", "iva", "1.2.03"),
    ("percepciones", "iibb", "1.2.03"),
    ("percepciones", "internos", "1.3.01"),
    ("percepciones", "otros_compra", "1.3.01"),
    ("percepciones", "otros_venta", "2.2.03"),
    ("banco_tipo", None, "5.1.02"),  # default: débitos/otros del extracto sin clasificar
    ("banco_tipo", "credito", "4.1.02"),
    ("banco_tipo", "debito", "5.1.02"),
    ("banco_tipo", "comision", "5.1.03"),
    ("banco_tipo", "extraccion", "1.1.01"),
    ("banco_tipo", "transferencia_in", "1.1.06"),
    ("banco_tipo", "transferencia_out", "1.1.06"),
    ("banco_tipo", "ajuste_positivo", "4.1.02"),
    ("banco_tipo", "ajuste_negativo", "5.1.03"),
    ("inventario", None, "1.3.01"),
    ("cmv", None, "5.1.01"),
    ("ajuste_inventario", None, "5.1.05"),
    ("diferencias_caja", "sobrante", "4.1.03"),
    ("diferencias_caja", "faltante", "5.1.04"),
    ("redondeo", None, "5.1.06"),
    ("bienes_uso", None, "1.4.01"),
    ("amort_acumulada", None, "1.4.02"),
    ("amort_ejercicio", None, "5.1.07"),
    ("baja_bienes_uso", None, "5.1.08"),
]


async def sembrar_plan_base(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Siembra plan + mapeos default del tenant (idempotente, sin commit)."""
    existentes = {
        c.codigo: c.id
        for c in (
            await db.scalars(select(PlanCuenta).where(PlanCuenta.tenant_id == tenant_id))
        ).all()
    }
    creadas = 0
    for codigo, nombre, tipo, imputable, padre in PLAN_BASE:
        if codigo in existentes:
            continue
        cuenta = PlanCuenta(
            tenant_id=tenant_id, codigo=codigo, nombre=nombre, tipo=tipo,
            imputable=imputable, padre_id=existentes.get(padre), es_sistema=True,
        )
        db.add(cuenta)
        await db.flush()
        existentes[codigo] = cuenta.id
        creadas += 1
    mapeos = {
        (m.origen, m.clave)
        for m in (
            await db.scalars(select(AsientoMapeo).where(AsientoMapeo.tenant_id == tenant_id))
        ).all()
    }
    for origen, clave, codigo in MAPEOS_BASE:
        if (origen, clave) in mapeos or codigo not in existentes:
            continue
        db.add(
            AsientoMapeo(
                tenant_id=tenant_id, origen=origen, clave=clave, cuenta_id=existentes[codigo]
            )
        )
    categorias = {
        c.nombre
        for c in (
            await db.scalars(
                select(ActivoCategoria).where(ActivoCategoria.tenant_id == tenant_id)
            )
        ).all()
    }
    for nombre, vida in CATEGORIAS_BASE:
        if nombre in categorias:
            continue
        db.add(
            ActivoCategoria(
                tenant_id=tenant_id, nombre=nombre, vida_util_meses=vida, es_sistema=True
            )
        )
        creadas += 1
    return creadas


# ============================================================================
# Amortización lineal mensual (diseño §6.1): cuota fija redondeada a 2
# decimales, la última absorbe el residuo. Devenga desde el mes de
# inicio_amortizacion inclusive hasta agotar vida útil o hasta el mes ANTERIOR
# a la baja. Compartida entre el motor y el cuadro de bienes de uso.
# ============================================================================

def _fin_de_mes(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def _mes_mas(d: date, n: int) -> date:
    m = d.year * 12 + (d.month - 1) + n
    return date(m // 12, m % 12 + 1, 1)


def cuotas_amortizacion(activo: ActivoFijo) -> list[tuple[date, Decimal]]:
    """[(fin_de_mes, cuota)] devengadas por el activo en toda su vida."""
    base = Decimal(activo.valor_origen) - Decimal(activo.valor_residual)
    vida = int(activo.vida_util_meses)
    if base <= 0 or vida <= 0:
        return []
    cuota = _r2(base / vida)
    inicio = activo.inicio_amortizacion.replace(day=1)
    tope_baja = activo.fecha_baja.replace(day=1) if activo.fecha_baja else None
    cuotas = []
    for i in range(vida):
        mes = _mes_mas(inicio, i)
        if tope_baja is not None and mes >= tope_baja:
            break
        monto = cuota if i < vida - 1 else base - cuota * (vida - 1)
        cuotas.append((_fin_de_mes(mes), monto))
    return cuotas


# ============================================================================
# Motor de derivación
# ============================================================================

class _Mapa:
    """Resolución mapeo → cuenta con fallback a la clave NULL de la regla."""

    def __init__(self, filas: dict[tuple[str, str | None], uuid.UUID]):
        self._m = filas

    def get(self, origen: str, clave=None) -> uuid.UUID | None:
        clave_s = str(clave) if clave is not None else None
        return self._m.get((origen, clave_s)) or self._m.get((origen, None))


async def _mapa(db: AsyncSession, tenant_id: uuid.UUID) -> _Mapa:
    filas = (
        await db.execute(
            select(AsientoMapeo.origen, AsientoMapeo.clave, AsientoMapeo.cuenta_id).where(
                AsientoMapeo.tenant_id == tenant_id
            )
        )
    ).all()
    return _Mapa({(o, c): cid for o, c, cid in filas})


async def periodos_cerrados(
    db: AsyncSession, tenant_id: uuid.UUID, desde: date, hasta: date
) -> list[date]:
    filas = (
        await db.scalars(
            select(ContabPeriodo.periodo).where(
                ContabPeriodo.tenant_id == tenant_id,
                ContabPeriodo.anulado_at.is_(None),
                ContabPeriodo.periodo >= desde.replace(day=1),
                ContabPeriodo.periodo <= hasta,
            )
        )
    ).all()
    return list(filas)


class _Batch:
    """Acumula asientos a insertar; valida balance por asiento."""

    def __init__(self, mapa: _Mapa):
        self.mapa = mapa
        self.asientos: list[tuple[date, str, str, uuid.UUID | None, list]] = []
        self.warnings: list[str] = []

    def agregar(self, fecha, desc: str, origen_tipo: str, origen_id, lineas: list) -> None:
        """lineas = [(cuenta_id|None, monto, detalle)]; monto>0 debe, <0 haber."""
        limpias = [(c, _r2(m), d) for c, m, d in lineas if _r2(m) != D0]
        if not limpias:
            return
        if any(c is None for c, _, _ in limpias):
            self.warnings.append(f"{desc}: mapeo faltante — asiento salteado")
            return
        if sum((m for _, m, _ in limpias), D0) != D0:
            self.warnings.append(f"{desc}: no balancea — asiento salteado")
            return
        self.asientos.append((fecha, desc, origen_tipo, origen_id, limpias))

    def reversion(self, fecha, desc: str, origen_tipo: str, origen_id, lineas: list) -> None:
        self.agregar(fecha, desc, origen_tipo, origen_id, [(c, -m, d) for c, m, d in lineas])


async def _familias_por_doc(db, modelo_item, campo_doc, ids: list, tenant_id):
    """{doc_id: [(familia_id|None, Σ importe_neto)]} de los ítems, para el
    mapeo por familia (residual contra el default)."""
    if not ids:
        return {}
    filas = (
        await db.execute(
            select(
                getattr(modelo_item, campo_doc),
                Articulo.familia_id,
                func.sum(modelo_item.importe_neto),
            )
            .select_from(modelo_item)
            .outerjoin(Articulo, modelo_item.articulo_id == Articulo.id)
            .where(getattr(modelo_item, campo_doc).in_(ids), modelo_item.tenant_id == tenant_id)
            .group_by(getattr(modelo_item, campo_doc), Articulo.familia_id)
        )
    ).all()
    out: dict = {}
    for doc_id, familia_id, neto in filas:
        out.setdefault(doc_id, []).append((familia_id, Decimal(neto)))
    return out


def _lineas_por_familia(mapa: _Mapa, origen: str, grupos, header_neto: Decimal, signo: int):
    """Reparte el neto entre cuentas por familia; el residual (descuentos,
    redondeos, ítems de texto libre) va a la cuenta default de la regla."""
    lineas = []
    asignado = D0
    for familia_id, neto in grupos:
        cuenta = mapa.get(origen, familia_id)
        lineas.append((cuenta, signo * neto, None))
        asignado += neto
    residual = header_neto - asignado
    if _r2(residual) != D0:
        lineas.append((mapa.get(origen), signo * residual, None))
    return lineas


async def derivar(
    db: AsyncSession, tenant_id: uuid.UUID, desde: date, hasta: date
) -> dict:
    """Regenera los asientos derivados del rango [desde, hasta] (sin commit).
    Devuelve {"asientos": n, "warnings": [...]}. El caller valida períodos."""
    mapa = await _mapa(db, tenant_id)
    b = _Batch(mapa)
    en_rango = lambda f: desde <= f <= hasta  # noqa: E731
    anulado_en_rango = lambda a: a is not None and en_rango(a.date())  # noqa: E731

    # ===== 1. Ventas fiscales emitidas (facturas/ND/NC) =====
    comps = (
        await db.scalars(
            select(Comprobante)
            .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
            .where(
                Comprobante.tenant_id == tenant_id,
                Comprobante.estado == "emitido",
                TipoComprobante.fiscal.is_(True),
                Comprobante.fecha >= desde,
                Comprobante.fecha <= hasta,
            )
        )
    ).all()
    ids = [c.id for c in comps]
    fam_v = await _familias_por_doc(db, ComprobanteItem, "comprobante_id", ids, tenant_id)
    medios_v: dict = {}
    if ids:
        for m in (
            await db.scalars(select(VentaMedio).where(VentaMedio.comprobante_id.in_(ids)))
        ).all():
            medios_v.setdefault(m.comprobante_id, []).append(m)
    cmv: dict = {}
    if ids:
        for gid, monto in (
            await db.execute(
                select(
                    StockMovimiento.grupo_id,
                    func.sum(StockMovimiento.cantidad * StockMovimiento.costo_unitario),
                )
                .where(
                    StockMovimiento.tenant_id == tenant_id,
                    StockMovimiento.grupo_id.in_(ids),
                    StockMovimiento.tipo.in_(("venta", "devolucion")),
                    StockMovimiento.costo_unitario.is_not(None),
                )
                .group_by(StockMovimiento.grupo_id)
            )
        ).all():
            cmv[gid] = Decimal(monto)
    for c in comps:
        signo = c.tipo.signo_cta_cte  # +1 fac/ND, -1 NC
        neto = c.neto_gravado + c.neto_no_gravado + c.exento
        lineas = []
        # contrapartida (debe): medios reales, o efectivo si contado, o deudores
        if c.contado:
            ms = medios_v.get(c.id)
            if ms:
                for m in ms:
                    cuenta = (
                        mapa.get("cuenta_bancaria", m.cuenta_bancaria_id)
                        if m.medio == "transferencia" and m.cuenta_bancaria_id
                        else mapa.get("cheques_cartera") if m.medio == "cheque"
                        else mapa.get("medio", m.medio)
                    )
                    lineas.append((cuenta, signo * m.importe, m.medio))
            else:
                lineas.append((mapa.get("medio", "efectivo"), signo * c.total, "contado"))
        else:
            lineas.append((mapa.get("deudores"), signo * c.total, None))
        # haber: ventas por familia + IVA + otros tributos
        lineas += _lineas_por_familia(mapa, "ventas_familia", fam_v.get(c.id, []), neto, -signo)
        lineas.append((mapa.get("iva_debito"), -signo * c.iva, None))
        lineas.append((mapa.get("percepciones", "otros_venta"), -signo * c.otros_tributos, None))
        # CMV (inventario permanente): cantidad de venta es negativa → -Σ = CMV
        monto_cmv = -cmv.get(c.id, D0)
        lineas.append((mapa.get("cmv"), monto_cmv, None))
        lineas.append((mapa.get("inventario"), -monto_cmv, None))
        etiqueta = f"{c.tipo_codigo} {c.punto_venta.numero:04d}-{(c.numero or 0):08d} {c.receptor_nombre[:40]}"
        b.agregar(c.fecha, etiqueta, "venta", c.id, lineas)

    # ===== 2. Recibos (+ reversión de anulados) =====
    recibos = (
        await db.scalars(
            select(Recibo).where(
                Recibo.tenant_id == tenant_id,
                (Recibo.fecha >= desde) & (Recibo.fecha <= hasta)
                | (Recibo.anulado_at.is_not(None)),
            )
        )
    ).all()
    for r in recibos:
        lineas = [
            (
                mapa.get("cuenta_bancaria", m.cuenta_bancaria_id)
                if m.medio == "transferencia" and m.cuenta_bancaria_id
                else mapa.get("cheques_cartera") if m.medio == "cheque"
                else mapa.get("medio", m.medio),
                Decimal(m.importe),
                m.medio,
            )
            for m in r.medios
        ]
        lineas.append((mapa.get("deudores"), -r.total, None))
        etiqueta = f"Recibo {r.punto_venta.numero:04d}-{r.numero:08d} {r.receptor_nombre[:40]}"
        # anulado sin fecha cierta (pre-014): sin original ni reversión
        if en_rango(r.fecha) and (r.estado == "emitido" or r.anulado_at is not None):
            b.agregar(r.fecha, etiqueta, "recibo", r.id, lineas)
        if anulado_en_rango(r.anulado_at):
            b.reversion(r.anulado_at.date(), f"Anulación {etiqueta}", "recibo_anulacion", r.id, lineas)

    # ===== 3. Compras registradas (+ reversión de anuladas) =====
    compras = (
        await db.scalars(
            select(Compra)
            .join(TipoComprobanteCompra, Compra.tipo_codigo == TipoComprobanteCompra.codigo)
            .where(
                Compra.tenant_id == tenant_id,
                Compra.estado.in_(("registrado", "anulado")),
                TipoComprobanteCompra.fiscal.is_(True),
                (Compra.fecha >= desde) & (Compra.fecha <= hasta)
                | (Compra.anulado_at.is_not(None)),
            )
        )
    ).all()
    ids_c = [c.id for c in compras]
    fam_c = await _familias_por_doc(db, CompraItem, "compra_id", ids_c, tenant_id)
    medios_c: dict = {}
    if ids_c:
        for m in (
            await db.scalars(select(CompraMedio).where(CompraMedio.compra_id.in_(ids_c)))
        ).all():
            medios_c.setdefault(m.compra_id, []).append(m)
    for c in compras:
        if c.estado == "anulado" and c.anulado_at is None:
            continue  # anulada pre-014, sin fecha cierta: no derivable
        signo = c.tipo.signo_cta_cte
        neto = c.neto_gravado + c.no_gravado + c.exento
        lineas = _lineas_por_familia(mapa, "compras_familia", fam_c.get(c.id, []), neto, signo)
        lineas.append((mapa.get("iva_credito"), signo * c.iva, None))
        lineas.append((mapa.get("percepciones", "iva"), signo * c.percepcion_iva, None))
        lineas.append((mapa.get("percepciones", "iibb"), signo * c.percepcion_iibb, None))
        lineas.append((mapa.get("percepciones", "internos"), signo * c.impuestos_internos, None))
        lineas.append((mapa.get("percepciones", "otros_compra"), signo * c.otros_tributos, None))
        lineas.append((mapa.get("redondeo"), signo * c.redondeo, None))
        if c.contado:
            ms = medios_c.get(c.id)
            if ms:
                for m in ms:
                    cuenta = (
                        mapa.get("cuenta_bancaria", m.cuenta_bancaria_id)
                        if m.medio == "transferencia" and m.cuenta_bancaria_id
                        else mapa.get("medio", m.medio)
                    )
                    lineas.append((cuenta, -signo * m.importe, m.medio))
            else:
                lineas.append((mapa.get("medio", "efectivo"), -signo * c.total, "contado"))
        else:
            lineas.append((mapa.get("proveedores"), -signo * c.total, None))
        etiqueta = f"{c.tipo_codigo} {c.punto_venta:04d}-{c.numero:08d} {c.proveedor_nombre[:40]}"
        if en_rango(c.fecha) and (c.estado == "registrado" or c.anulado_at is not None):
            b.agregar(c.fecha, etiqueta, "compra", c.id, lineas)
        if anulado_en_rango(c.anulado_at):
            b.reversion(c.anulado_at.date(), f"Anulación {etiqueta}", "compra_anulacion", c.id, lineas)

    # ===== 4. Órdenes de pago (+ reversión de anuladas) =====
    ops = (
        await db.scalars(
            select(OrdenPago).where(
                OrdenPago.tenant_id == tenant_id,
                (OrdenPago.fecha >= desde) & (OrdenPago.fecha <= hasta)
                | (OrdenPago.anulado_at.is_not(None)),
            )
        )
    ).all()
    ids_op = [o.id for o in ops]
    cheques_op: dict = {}
    if ids_op:
        for ch in (
            await db.scalars(select(Cheque).where(Cheque.orden_pago_id.in_(ids_op)))
        ).all():
            cheques_op.setdefault(ch.orden_pago_id, []).append(ch)
    for o in ops:
        cartera = sum(
            (c.importe for c in cheques_op.get(o.id, []) if c.clase == "tercero"), D0
        )
        propios = sum(
            (c.importe for c in cheques_op.get(o.id, []) if c.clase == "propio"), D0
        )
        lineas = [(mapa.get("proveedores"), Decimal(o.total), None)]
        resto_cheque = D0
        for m in o.medios:
            if m.medio == "cheque":
                resto_cheque += m.importe
                continue
            cuenta = (
                mapa.get("cuenta_bancaria", m.cuenta_bancaria_id)
                if m.medio == "transferencia" and m.cuenta_bancaria_id
                else mapa.get("medio", m.medio)
            )
            lineas.append((cuenta, -Decimal(m.importe), m.medio))
        if cartera:
            lineas.append((mapa.get("cheques_cartera"), -cartera, "cheques endosados"))
        if propios:
            lineas.append((mapa.get("cheques_diferidos"), -propios, "cheques propios"))
        etiqueta_resto = resto_cheque - cartera - propios
        if etiqueta_resto:
            lineas.append((mapa.get("medio", "cheque"), -etiqueta_resto, "cheque"))
        etiqueta = f"OP-{o.numero:08d} {o.proveedor_nombre[:40]}"
        # anulada sin fecha cierta (pre-014): sin original ni reversión
        if en_rango(o.fecha) and (o.estado == "emitida" or o.anulado_at is not None):
            b.agregar(o.fecha, etiqueta, "orden_pago", o.id, lineas)
        if anulado_en_rango(o.anulado_at):
            b.reversion(o.anulado_at.date(), f"Anulación {etiqueta}", "op_anulacion", o.id, lineas)

    # ===== 5. Caja: movimientos manuales (+ reversión de anulados) =====
    movs = (
        await db.scalars(
            select(CajaMovimiento).where(
                CajaMovimiento.tenant_id == tenant_id,
                (CajaMovimiento.fecha >= desde) & (CajaMovimiento.fecha <= hasta)
                | (CajaMovimiento.anulado_at.is_not(None)),
            )
        )
    ).all()
    for m in movs:
        signo = 1 if m.tipo == "entrada" else -1
        cuenta_medio = (
            mapa.get("cuenta_bancaria", m.cuenta_bancaria_id)
            if m.medio == "transferencia" and m.cuenta_bancaria_id
            else mapa.get("medio", m.medio)
        )
        lineas = [
            (cuenta_medio, signo * m.importe, m.medio),
            (mapa.get("concepto_caja", m.concepto_id), -signo * m.importe, m.concepto.nombre[:40]),
        ]
        etiqueta = f"Caja: {m.concepto.nombre[:40]}" + (f" — {m.descripcion[:40]}" if m.descripcion else "")
        if en_rango(m.fecha):
            b.agregar(m.fecha, etiqueta, "caja_mov", m.id, lineas)
        if anulado_en_rango(m.anulado_at):
            b.reversion(m.anulado_at.date(), f"Anulación {etiqueta}", "caja_anulacion", m.id, lineas)

    # ===== 6. Bancos: movimientos manuales/import (los de cheques van por eventos) =====
    SIGNO_MOV = {
        "deposito": 1, "transferencia_in": 1, "credito": 1, "ajuste_positivo": 1,
        "extraccion": -1, "transferencia_out": -1, "debito": -1, "comision": -1,
        "ajuste_negativo": -1,
    }
    bmovs = (
        await db.scalars(
            select(BancoMovimiento).where(
                BancoMovimiento.tenant_id == tenant_id,
                BancoMovimiento.origen != "cheque",
                (BancoMovimiento.fecha >= desde) & (BancoMovimiento.fecha <= hasta)
                | (BancoMovimiento.anulado_at.is_not(None)),
            )
        )
    ).all()
    # contrapartidas de transferencias apareadas (016): pueden caer fuera del
    # rango — se buscan aparte solo para conocer su cuenta destino
    pares: dict = {}
    pares_ids = {m.contrapartida_id for m in bmovs if m.contrapartida_id}
    if pares_ids:
        for cm in (
            await db.scalars(select(BancoMovimiento).where(BancoMovimiento.id.in_(pares_ids)))
        ).all():
            pares[cm.id] = cm
    for m in bmovs:
        # transferencia apareada entre cuentas propias: UN asiento banco a
        # banco anclado en la SALIDA; la entrada apareada se saltea (§6.2)
        if m.contrapartida_id and m.anulado_at is None:
            par = pares.get(m.contrapartida_id)
            if par is not None and par.anulado_at is None:
                if m.tipo == "transferencia_in":
                    continue
                if m.tipo == "transferencia_out":
                    if en_rango(m.fecha):
                        etiqueta = "Transferencia entre cuentas propias" + (
                            f" — {m.descripcion[:40]}" if m.descripcion else ""
                        )
                        b.agregar(
                            m.fecha, etiqueta, "banco_transfer", m.id,
                            [(mapa.get("cuenta_bancaria", par.cuenta_id), Decimal(m.importe), "destino"),
                             (mapa.get("cuenta_bancaria", m.cuenta_id), -Decimal(m.importe), "origen")],
                        )
                    continue
        signo = SIGNO_MOV.get(m.tipo, 1)
        lineas = [
            (mapa.get("cuenta_bancaria", m.cuenta_id), signo * m.importe, None),
            (mapa.get("banco_tipo", m.tipo), -signo * m.importe, m.tipo),
        ]
        etiqueta = f"Banco: {m.tipo}" + (f" — {m.descripcion[:40]}" if m.descripcion else "")
        if en_rango(m.fecha):
            b.agregar(m.fecha, etiqueta, "banco_mov", m.id, lineas)
        if anulado_en_rango(m.anulado_at):
            b.reversion(m.anulado_at.date(), f"Anulación {etiqueta}", "banco_anulacion", m.id, lineas)

    # ===== 7. Cheques: eventos con efecto contable propio =====
    eventos = (
        await db.execute(
            select(ChequeEvento, Cheque)
            .join(Cheque, ChequeEvento.cheque_id == Cheque.id)
            .where(
                ChequeEvento.tenant_id == tenant_id,
                ChequeEvento.fecha >= desde,
                ChequeEvento.fecha <= hasta,
                ChequeEvento.estado_hasta.in_(
                    ("depositado", "rechazado", "debitado", "en_cartera", "anulado")
                ),
            )
        )
    ).all()
    for ev, ch in eventos:
        etiqueta = f"Cheque {ch.numero} ({ch.banco[:30]}): {ev.estado_hasta}"
        if ev.estado_hasta == "en_cartera" and ch.recibo_id is None:
            # alta manual en cartera (sin recibo): contra deudores
            lineas = [(mapa.get("cheques_cartera"), Decimal(ch.importe), None),
                      (mapa.get("deudores"), -Decimal(ch.importe), None)]
        elif ev.estado_hasta == "depositado":
            lineas = [(mapa.get("cuenta_bancaria", ch.cuenta_id), Decimal(ch.importe), None),
                      (mapa.get("cheques_cartera"), -Decimal(ch.importe), None)]
        elif ev.estado_hasta == "rechazado":
            origen_fondos = (
                mapa.get("cuenta_bancaria", ch.cuenta_id)
                if ev.estado_desde == "depositado"
                else mapa.get("cheques_cartera")
            )
            lineas = [(mapa.get("cheques_rechazados"), Decimal(ch.importe), None),
                      (origen_fondos, -Decimal(ch.importe), None)]
        elif ev.estado_hasta == "debitado":
            lineas = [(mapa.get("cheques_diferidos"), Decimal(ch.importe), None),
                      (mapa.get("cuenta_bancaria", ch.cuenta_id), -Decimal(ch.importe), None)]
        elif ev.estado_hasta == "anulado" and ev.estado_desde == "en_cartera":
            lineas = [(mapa.get("deudores"), Decimal(ch.importe), None),
                      (mapa.get("cheques_cartera"), -Decimal(ch.importe), None)]
        elif ev.estado_hasta == "anulado" and ev.estado_desde == "emitido":
            lineas = [(mapa.get("cheques_diferidos"), Decimal(ch.importe), None),
                      (mapa.get("proveedores"), -Decimal(ch.importe), None)]
        else:
            continue
        b.agregar(ev.fecha, etiqueta, "cheque_evento", ev.id, lineas)

    # ===== 8. Retenciones (+ reversión de anuladas) =====
    rets = (
        await db.scalars(
            select(Retencion).where(
                Retencion.tenant_id == tenant_id,
                (Retencion.fecha >= desde) & (Retencion.fecha <= hasta)
                | (Retencion.anulado_at.is_not(None)),
            )
        )
    ).all()
    for r in rets:
        if r.tipo == "sufrida":
            lineas = [(mapa.get("retencion", "sufrida"), Decimal(r.importe), r.regimen),
                      (mapa.get("deudores"), -Decimal(r.importe), None)]
        else:
            lineas = [(mapa.get("proveedores"), Decimal(r.importe), None),
                      (mapa.get("retencion", "practicada"), -Decimal(r.importe), r.regimen)]
        etiqueta = f"Retención {r.tipo} {r.regimen}" + (f" {r.nro_certificado}" if r.nro_certificado else "")
        if en_rango(r.fecha):
            b.agregar(r.fecha, etiqueta, "retencion", r.id, lineas)
        if anulado_en_rango(r.anulado_at):
            b.reversion(r.anulado_at.date(), f"Anulación {etiqueta}", "retencion_anulacion", r.id, lineas)

    # ===== 9. Ajustes de inventario (kardex suelto con costo sellado) =====
    ajustes = (
        await db.execute(
            select(
                StockMovimiento.id,
                StockMovimiento.fecha,
                (StockMovimiento.cantidad * StockMovimiento.costo_unitario).label("monto"),
            ).where(
                StockMovimiento.tenant_id == tenant_id,
                StockMovimiento.tipo.in_(("ajuste", "inicial")),
                StockMovimiento.costo_unitario.is_not(None),
                func.date(StockMovimiento.fecha) >= desde,
                func.date(StockMovimiento.fecha) <= hasta,
            )
        )
    ).all()
    for mov_id, fecha_mov, monto in ajustes:
        monto = Decimal(monto)
        b.agregar(
            fecha_mov.date(), "Ajuste de inventario", "stock_ajuste", mov_id,
            [(mapa.get("inventario"), monto, None),
             (mapa.get("ajuste_inventario"), -monto, None)],
        )

    # ===== 10. Diferencias de arqueo (cierres de caja, + reversión de reabiertos) =====
    cierres = (
        await db.scalars(
            select(CajaCierre).where(
                CajaCierre.tenant_id == tenant_id,
                CajaCierre.diferencia.is_not(None),
                CajaCierre.diferencia != 0,
                (CajaCierre.fecha >= desde) & (CajaCierre.fecha <= hasta)
                | (CajaCierre.anulado_at.is_not(None)),
            )
        )
    ).all()
    for c in cierres:
        dif = Decimal(c.diferencia)
        clave = "sobrante" if dif > 0 else "faltante"
        lineas = [(mapa.get("medio", "efectivo"), dif, None),
                  (mapa.get("diferencias_caja", clave), -dif, None)]
        etiqueta = f"Arqueo {c.fecha.isoformat()}: {clave} de caja"
        if en_rango(c.fecha):
            b.agregar(c.fecha, etiqueta, "arqueo", c.id, lineas)
        if anulado_en_rango(c.anulado_at):
            b.reversion(c.anulado_at.date(), f"Reapertura {etiqueta}", "arqueo_anulacion", c.id, lineas)

    # ===== 11. Amortizaciones de bienes de uso (F9-bis, diseño §6.1): UN
    # asiento por mes calendario cuyo fin de mes cae en el rango, con un par de
    # líneas por activo. El alta del activo NO deriva (entró por su documento).
    activos = (
        await db.scalars(
            select(ActivoFijo).where(
                ActivoFijo.tenant_id == tenant_id,
                ActivoFijo.anulado_at.is_(None),
            )
        )
    ).all()
    por_mes: dict[date, list] = {}
    for a in activos:
        for fecha_cuota, monto in cuotas_amortizacion(a):
            if en_rango(fecha_cuota):
                por_mes.setdefault(fecha_cuota, []).append((a, monto))
    for fecha_cuota in sorted(por_mes):
        lineas = []
        for a, monto in por_mes[fecha_cuota]:
            lineas.append((mapa.get("amort_ejercicio", a.categoria_id), monto, a.nombre[:40]))
            lineas.append((mapa.get("amort_acumulada", a.categoria_id), -monto, a.nombre[:40]))
        b.agregar(
            fecha_cuota, f"Amortización bienes de uso {fecha_cuota.isoformat()[:7]}",
            "amortizacion", None, lineas,
        )

    # ===== 12. Bajas de bienes de uso: retiro del activo al valor de origen,
    # descargando la amortización acumulada devengada; el residual contable va
    # a resultado por baja. Baja por venta: el ingreso lo deriva la factura.
    for a in activos:
        if a.fecha_baja is None or not en_rango(a.fecha_baja):
            continue
        devengada = sum((m for _, m in cuotas_amortizacion(a)), D0)
        residual_contable = Decimal(a.valor_origen) - devengada
        etiqueta = f"Baja bien de uso: {a.nombre[:40]}" + (
            f" — {a.baja_motivo[:40]}" if a.baja_motivo else ""
        )
        b.agregar(
            a.fecha_baja, etiqueta, "activo_baja", a.id,
            [(mapa.get("amort_acumulada", a.categoria_id), devengada, None),
             (mapa.get("baja_bienes_uso"), residual_contable, None),
             (mapa.get("bienes_uso", a.categoria_id), -Decimal(a.valor_origen), None)],
        )

    # ===== Persistir: borrar derivados del rango y re-insertar (los manuales
    # y el asiento de apertura NUNCA se tocan) =====
    await db.execute(
        delete(Asiento).where(
            Asiento.tenant_id == tenant_id,
            Asiento.origen_tipo.notin_(("manual", "apertura")),
            Asiento.fecha >= desde,
            Asiento.fecha <= hasta,
        )
    )
    ultimo = await db.scalar(
        select(func.coalesce(func.max(Asiento.numero), 0)).where(Asiento.tenant_id == tenant_id)
    )
    numero = int(ultimo or 0)
    for fecha, desc, origen_tipo, origen_id, lineas in sorted(
        b.asientos, key=lambda a: (a[0], a[1])
    ):
        numero += 1
        asiento = Asiento(
            tenant_id=tenant_id, numero=numero, fecha=fecha, descripcion=desc[:200],
            origen_tipo=origen_tipo, origen_id=origen_id,
        )
        db.add(asiento)
        await db.flush()
        for orden, (cuenta_id, monto, detalle) in enumerate(lineas):
            db.add(
                AsientoLinea(
                    tenant_id=tenant_id, asiento_id=asiento.id, orden=orden,
                    cuenta_id=cuenta_id,
                    debe=monto if monto > 0 else D0,
                    haber=-monto if monto < 0 else D0,
                    detalle=detalle,
                )
            )
    return {"asientos": len(b.asientos), "warnings": b.warnings}
