# ZGC — Diseño de Vendedores y Comisiones (F11)

> Escrito el 2026-07-11. Fase sin gate del ROADMAP (módulo 5 del legacy:
> "Vendedores / Comisiones — por venta o por cobranza"). Migración 017.

## 1. Qué hizo el legacy (evidencia)

- **`VIAJANTE.DBF`**: el "vendedor" del legacy — código C2, nombre, domicilio,
  teléfono y **un único % de comisión** (`COMISION N 5,2`). Nada más.
- El viajante se **sella por código** en `CLIENTES.CVIAJ` (habitual),
  `VENTASM.CVIAJ` (la venta), `RECIBOSM.CVIAJ` (la cobranza) y `PEDCLIM.CVIAJ`.
- **`GV0040`** (FMOV, AUXILIO, NCOMP, NOMCLI, NETO, COMISION): tabla de TRABAJO
  regenerable del reporte de liquidación — mismo patrón que GV0162/GV0163 en
  contabilidad. El legacy no persistía liquidaciones como documento.

## 2. Modelo ZGC (migración 017)

- **`vendedores`** — rol sobre la BUE (patrón `clientes`/`proveedores`,
  CLAUDE.md §1-bis): `entidad_id` único por tenant, `codigo` interno,
  **`comision_pct`** (el % único del legacy) y **`modalidad`**
  (`venta` | `cobranza`) — cada vendedor liquida por lo facturado o por lo
  cobrado, default `venta`. Inactivable, nunca se borra.
- **Sellado del vendedor** (espejo moderno de CVIAJ): `clientes.vendedor_id`
  (habitual), `comprobantes.vendedor_id` y `recibos.vendedor_id`. Al crear un
  comprobante o recibo sin vendedor explícito, **defaultea al habitual del
  cliente**. La **NC espejo copia el vendedor de la factura** (la anulación
  resta comisión sola).
- **Liquidación = DOCUMENTO** (contrato de contabilizabilidad, CLAUDE.md §6 —
  acá se moderniza el GV0040): `comision_liquidaciones` (número por tenant,
  vendedor, rango, modalidad y % **sellados**, totales, `anulado_at/anulado_por`)
  + `comision_liquidacion_items` (comprobante_id XOR recibo_id, base, importe).
  - **"Ya liquidado" se deriva**: un documento está liquidado si existe un ítem
    de una liquidación VIVA que lo referencia — los documentos fuente **no se
    mutan**. Anular la liquidación (marcar) los libera para re-liquidar.
- **RBAC**: módulo nuevo `vendedores` (catálogo `permisos.py` + seed 017 espejo):
  admin/gerente `anular` · consulta `ver` · cajero/vendedor sin acceso (el rol
  RBAC "vendedor" no ve las comisiones de otros).

## 3. Base comisionable (v1)

| Modalidad | Devenga sobre | Base |
|---|---|---|
| `venta` | comprobantes **fiscales emitidos** del vendedor en el rango | (neto gravado + no gravado + exento) × `signo_cta_cte` — las NC **restan** |
| `cobranza` | recibos vivos del vendedor en el rango | `total − rechazado_total` (un cheque rechazado no es cobranza) |

Comisión por ítem = base × % del vendedor (redondeo 2 dec). El total de una
liquidación puede ser negativo (período dominado por NC) — queda a favor del
comercio y el asiento se invierte solo (convención monto>0 debe del motor).

## 4. Contabilidad (la liquidación es fuente del motor)

- Cuentas nuevas del plan base (re-seed lazy): **2.1.03 Comisiones a pagar**
  (pasivo) y **5.1.09 Comisiones de vendedores** (r_negativo). Mapeos default
  `comisiones` → 5.1.09 y `comisiones_a_pagar` → 2.1.03.
- Derivación: liquidación viva → `Debe Comisiones / Haber Comisiones a pagar`
  fechada en `created_at::date`; anulada → reversión fechada en `anulado_at`
  (origen `comision` / `comision_anulacion`).
- **El PAGO de la comisión al vendedor NO se automatiza en v1**: sale por caja
  (movimiento manual con un concepto mapeado a 2.1.03) o por el medio que
  corresponda. F10/F15 lo formalizan si hace falta.

## 5. Alcance negativo v1

- POS sin vendedor (mostrador); se agrega por perfil en F12 si un piloto lo pide.
- Sin escalas de comisión (por familia/artículo/cliente), sin objetivos ni
  premios — el legacy tampoco los tenía.
- Sin migrador de `VIAJANTE.DBF` (29 filas en un backup 2009, sin documento —
  el alta manual es más barata que calibrar un migrador; si un ex cliente lo
  pide, el patrón de `migrar_proveedores.py` lo resuelve en una tarde).
- Comisión sobre presupuestos/remitos: NO (solo fiscales).
