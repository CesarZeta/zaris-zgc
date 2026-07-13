# Piloto ficticio «Supermercado ZARIS» — junio 2026

> **Qué es**: un mes completo de operación de un supermercado de barrio, generado
> con registros REALES por la API pública (`tools/piloto_supermercado.py`, seed
> determinística — pedido de César 2026-07-13). Toca todos los módulos de la
> suite y estrena F12-bis Logística. **Sueldos queda excluido** (F15 no existe).
>
> **Dónde verlo**: `https://cesarzeta.github.io/zaris-zgc/` → login
> **piloto@zgc.dev** (la clave la fijó la corrida; también existe en dev local).
> El tenant es nuevo y aislado — el demo histórico no se tocó.
>
> **Cómo se generó**: todo por API con `fecha` de junio (modo ARCA simulado);
> los tickets POS se emitieron por los endpoints POS reales y un retoque SQL
> final —acotado al tenant— corrió sesiones/tickets/kardex/logística a sus
> días de junio. Los cheques diferidos se gestionaron "hoy" (julio), como en
> la vida real. La contabilidad se regeneró DESPUÉS, sobre las fechas finales.

---

## La historia del mes (y dónde verificar cada capítulo)

### 1/6 — El súper abre sus libros

La empresa arranca con **$ 3.500.000 en Banco Galicia** y **$ 800.000 en Banco
Nación**, aportados como capital. El mismo día se registra la **heladera
exhibidora de 6 puertas** ($ 4.800.000, vida útil 10 años) como bien de uso.

- **Contabilidad → Libro diario**, filtrar junio: el primer asiento es
  *«Apertura del ejercicio — Supermercado ZARIS»* (origen `apertura`), Debe
  bancos $ 4.300.000 / Haber capital.
- **Contabilidad → Bienes de uso**: la heladera con valor de origen
  $ 4.800.000 y **una amortización mensual derivada de $ 40.000** (4.8M/120) —
  el asiento `amortizacion` del 30/6 está en el diario. El ALTA no genera
  asiento (regla F9-bis).
- **Bancos y Cheques → Cuentas**: Galicia CC y Nación CA con sus saldos.

### 3-4/6 — Primero se compra (mandato del guion)

Dos facturas A de mercadería en cuenta corriente:
**Distribuidora Litoral SA** ($ **7.465.881,50**, los secos: almacén, bebidas,
limpieza, perfumería, kiosco) y **Frigorífico Paraná SRL** ($ **5.950.004,15**,
los frescos pesables + reposición). Actualizan stock y costos.

- **Compras → Comprobantes**: las 2 facturas registradas con IVA discriminado.
- **Stock**: cualquier artículo (p. ej. *Yerba mate 1kg*) muestra existencias
  y su kardex arranca el 3/6 o 4/6 con la compra.
- **Libros IVA → IVA Compras**, período 2026-06: total $ **13.415.885,65**
  (crédito fiscal por alícuota 21% y 10,5%).

### 10/6 y 17/6 — Se les paga a los proveedores

OP a Distribuidora por **transferencia** desde Galicia (10/6) y OP a
Frigorífico con **cheque propio diferido al 17/7** (17/6), con **retención de
Ganancias practicada** ($ 42.300, certificado RP-2026-000087).

- **Compras → Pagos**: las 2 OP imputadas (las compras quedan saldadas).
- **Bancos → Cartera de cheques**, filtro *propios*: el cheque 10000001
  **emitido** (pendiente de débito — mirá que aparece como salida futura en
  **Tesorería**).
- **Libros IVA → Retenciones**: la practicada del 17/6.

### Todo el mes — Las 2 cajas venden (50 tickets)

Las cajas **Caja 1 (PV 0002)** y **Caja 2 (PV 0003)** operaron **10 jornadas**
(2, 4, 6, 9, 11, 13, 17, 20, 24 y 27 de junio), ambas cada día, con apertura
de sesión (fondo $ 50.000), **50 tickets de 3 a 10 artículos** con cantidades
y medios aleatorios (efectivo/tarjeta/transferencia/MercadoPago) y cierre con
arqueo. El guion incluyó:

- un **pesable por etiqueta de balanza** (EAN 20 + PLU 203, queso cremoso
  1,485 kg — el server resolvió el peso),
- una **venta por departamento** (*Bazar y varios*, importe tipeado $ 15.300),
- una gaseosa retornable con su **envase**,
- **descuentos F7** (−15% en una línea, −10% en una venta),
- un ticket a **cliente identificado** (Rotisería Don Pepe, RI → factura A), y
- **2 anulaciones con autorización de supervisor** (NC espejo en el acto).

Dónde verificarlo:

- **Punto de Venta**: entrá con la sesión de la suite — cajas configuradas.
- **Ventas → Comprobantes**, rango junio: los tickets FB/FA de PV 0002/0003
  intercalados con la gestión de PV 0001; las 2 NC de anulación.
- **Caja → Planilla del día**, fecha **13/6**: ventas por medio (efectivo
  $ 118.820,01 · tarjeta $ 74.390 · transferencia $ 44.170), saldo final
  $ 80.320,01, y el **cierre con diferencia de arqueo de −$ 1.500** (la Caja 1
  contó de menos esa noche — está sellado en el cierre y en la sesión POS).
- **Configuración → Cajas POS**: sesiones de junio con sus arqueos.

### 5-28/6 — La gestión factura en cuenta corriente

8 facturas mayoristas con **vendedor sellado** (Sergio Almada 2% por venta,
Valeria Quiroz 1,5% por cobranza): comedores, rotisería, hotel, geriátrico,
kioscos. Además un **presupuesto** (5/6, que se facturó el 8/6), **2 remitos**
(24 y 25/6) y una **NC total** a la venta del Club Atlético (20/6 — pedido
anulado comercialmente).

- **Ventas → Comprobantes**: filtrar junio; la NC del Club revierte su factura.
- **Clientes → Ctas. ctes.**: cada cliente con su debe/haber.

### 6-27/6 — El circuito de recaudación

Recibos de junio con todos los matices:

| Fecha | Cliente | Qué pasó |
|---|---|---|
| 12/6 | Comedor Escolar | cobro **total en efectivo** |
| 16/6 | Hotel Puerto Viejo | **cheque de tercero** al 6/7 (Banco Santander) |
| 18/6 | Kiosco La Parada | cobro **parcial** por transferencia (quedó saldo) |
| 20/6 | Geriátrico | cheque Banco Macro al 2/7… **que después rebota** |
| 24/6 | Rotisería | transferencia con **retención IVA sufrida** ($ 18.500) |
| 27/6 | Bar El Cruce | **pago a cuenta** $ 250.000 con cheque al 10/7 |

Y en julio (hoy), la gestión de la cartera: el cheque del Hotel se **depositó
en Banco Nación y acreditó**; el del Geriátrico se depositó y fue **RECHAZADO
sin fondos** — su deuda de $ **119.760** se **reabrió sola** (el recibo quedó
inmutable, contrato 014); el del Bar se **endosó** a Lácteos del Centro como
pago a cuenta.

- **Ventas → Cobranzas**: los 6 recibos.
- **Bancos → Cartera**: el acreditado (chip verde), el **rechazado** (chip
  rojo, con su evento) y el endosado.
- **Clientes → Ctas. ctes. / morosidad**: el Geriátrico debe de nuevo su
  factura; la venta del 28/6 al Bar sigue impaga → **cobros pendientes
  $ 223.385,01** (es el KPI del dashboard).
- **Libros IVA → Retenciones**: la sufrida del 24/6.

### 20-30/6 — Caja y bancos, prolijos

Gasto de librería por caja (5/6, $ 38.500), **retiro de efectivo a Banco
Galicia** (20/6, $ 900.000 — sale de caja y entra al banco), **transferencia
entre cuentas propias** Galicia → Nación (25/6, $ 500.000) **apareada** (un
solo asiento banco a banco, sin cuenta puente), y el **extracto de junio de
Galicia importado**: concilió el depósito del 20/6 y creó la **comisión
bancaria** de $ 45.000 (30/6). Cierres de caja con arqueo los días 5, 13 y 30.

- **Caja → Movimientos / Planilla**: los manuales y los cierres.
- **Bancos → Cuentas → movimientos de Galicia**: depósito conciliado (por el
  import), transferencia con chip *apareada*, comisión del 30/6.
- **Contabilidad → Libro diario**: el asiento `banco_transfer` del 25/6.

### 26/6 — Sale el reparto (estreno de F12-bis)

Los 2 remitos + la factura del kiosco de reventa se cargaron como **entregas**
(domicilio snapshot del cliente), se armó la **hoja de ruta HR-00000001** con
el transportista **Ramón Ferreyra (Kangoo AF208KL)**, se imprimió, se despachó
y a la vuelta se rindió: **2 entregadas** (con quién recibió) y **1 rechazada**
(«Local cerrado») que se **reprogramó** — la hoja quedó **cerrada**.

- **Logística → Hojas de ruta**: HR-00000001 cerrada con sus 3 paradas
  (botón *Imprimir* para ver la hoja con columna de firma).
- **Logística → Entregas**: la rechazada (terminal) y su reintento pendiente.
- Regla verificada: nada de esto tocó la facturación ni la cta. cte.

### 30/6 y cierre — El contador recibe todo

- **Vendedores → Comisiones**: dos liquidaciones de junio — **LC-00000001
  $ 6.246,77** (Almada, 2% sobre lo facturado; la NC del Club le RESTÓ) y
  **LC-00000002 $ 7.458** (Quiroz, 1,5% sobre lo cobrado neto de rechazos).
  Son documentos contabilizables (Debe 5.1.09 / Haber 2.1.03).
- **Contabilidad**: **86 asientos derivados** regenerados de una sola pasada,
  **sumas y saldos balanceado**, **balance al 30/6 con la ecuación A = P + PN
  verificada**, y el **período junio CERRADO** (probá regenerar junio: responde
  409). El export contador (ZIP con plan/diario/sumas/mayor) baja desde el tab
  Diario.
- **Libros IVA junio**: ventas $ **2.941.339,69** (débito fiscal $ 510.480,46)
  · compras $ **13.415.885,65** · **CITI** ZIP con los 4 TXT.
- **Inicio (dashboard)**: cobros pendientes $ 223.385,01 · **stock valorizado
  $ 9.681.407,50** · ventas del mes en $ 0 (estamos en julio — correcto).
- **Tesorería**: el cash-flow proyecta el débito del cheque propio (17/7).

---

## Ficha técnica

| | |
|---|---|
| Tenant | «Supermercado ZARIS (piloto)» — plan suite, rubro supermercado |
| Maestros | 44 artículos (8 familias, 9 pesables, envase, depto.) · 10 clientes · 3 proveedores · 2 vendedores · 1 transportista · 2 bancos · 2 cajas POS |
| Operaciones | 2 compras A · 8 facturas gestión + presupuesto + 2 remitos + 1 NC · 50 tickets POS (2 anulados) en 20 sesiones · 6 recibos · 3 OP · 5 cheques (1 rechazado, 1 endosado, 1 propio diferido) · 2 retenciones · hoja de ruta rendida · 2 liquidaciones de comisión |
| Contabilidad | apertura + 86 asientos derivados balanceados · junio cerrado |
| Generador | `tools/piloto_supermercado.py` (seed fija — dev y prod dieron números idénticos) · NO re-ejecutar sobre el mismo tenant (duplica) |
| Pendiente a futuro | sueldos (F15, decisión de César: otro momento) |
