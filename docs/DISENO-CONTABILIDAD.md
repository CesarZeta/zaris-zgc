# ZGC — Diseño de Contabilidad (F9) y contrato de contabilizabilidad

> Escrito el 2026-07-10 a partir de la decisión de César de preparar la
> contabilidad ANTES de seguir sumando módulos, y de la auditoría de
> contabilizabilidad de los 5 dominios operativos + el esquema legacy
> (6 agentes, misma fecha). **La Fase 9 (módulo Contabilidad) sigue gated**
> por su condición del ROADMAP: primer cliente de referencia pagando.
> Lo que NO espera es el contrato de este documento: rige desde la
> migración 014 para todo módulo nuevo.

## 1. Decisión de arquitectura: contabilidad DERIVADA, nunca posteo en línea

Los asientos contables se **derivan de los documentos operativos** ya
registrados (comprobantes, recibos, OP, movimientos de caja/banco, cheques,
kardex) mediante un **motor de asientos** con reglas de mapeo configurables.
Ningún módulo operativo escribe asientos dentro de su transacción.

Por qué (evidencia, no opinión):

1. **El legacy lo validó 20 años**: RevoSolution no tenía plan de cuentas, ni
   tabla de asientos, ni diario/mayor persistidos (0 hallazgos en 306 tablas
   DBF). Tenía códigos `CUENTA C6` embebidos como *config* en las tablas
   operativas (`ARTICULO.CUENTA`, `CONC_CAJ.CUENTA`, `RETENCIO.CUENTA`,
   `TARJETAS.CUENTA`, `MAECTA.CUENTA`, `GASTOS` = mapeo rubro→cuenta,
   `COMPRASM.CUENTA/CUENTANOGR/CUENTAOTRO`, `VENTASM.CUENTA1-3`) y los
   DEBE/HABER vivían en tablas de trabajo regenerables (`GV0162`/`GV0163`,
   0 registros canónicos: se rearmaban en cada corrida del reporte).
2. **Mismo patrón que ya usa ZGC**: los libros de IVA y la planilla de caja
   son reportes regenerables sin tabla propia (F5).
3. **Regla "reusar el núcleo"** (CLAUDE.md §6): el posteo vive en UN motor que
   lee documentos, no repartido en cada flujo. Postear en línea acoplaría el
   camino caliente del POS a la contabilidad.
4. **Regenerable = corregible**: si el contador cambia un mapeo, se regenera
   el período. Con posteo en firme al commitear, imposible.

Consecuencia clave: **el plan de cuentas NO necesita preexistir a los módulos
operativos**. Lo que sí debe preexistir es la *contabilizabilidad* de los
documentos — el contrato del §2.

## 2. Contrato de contabilizabilidad (checklist para TODA fase nueva)

Un documento operativo es *contabilizable* si cumple las tres propiedades.
Toda fase nueva que registre operaciones debe cumplirlas desde el día 1
(regla agregada al CLAUDE.md §6):

1. **COMPLETO** — el documento discrimina los importes que el asiento necesita
   (neto/IVA por alícuota, percepciones por tipo) y su **contrapartida
   financiera está identificada**: toda operación que mueve plata dice por qué
   medio (y contra qué cuenta bancaria si aplica).
2. **INMUTABLE** — anular = marcar con fecha cierta (`estado` +
   `anulado_at`/`anulado_por`) o contra-documento (NC espejo, contra-movimiento
   de stock). PROHIBIDO el `DELETE` físico y el `UPDATE` destructivo de
   importes de un documento emitido/registrado. Un asiento retroactivo debe
   poder fechar la reversión.
3. **MAPEABLE** — toda categoría que decide una cuenta contable es un
   catálogo con FK (concepto de caja, familia, medio, tipo de movimiento
   bancario, régimen de retención), nunca texto libre.

## 3. Estado post-migración 014 (mini-fase Contabilizabilidad, 2026-07-10)

Lo que la auditoría encontró y la 014 + su backend cerraron:

| Gap (auditoría 2026-07-10) | Fix aplicado |
|---|---|
| Anular recibo/OP/NC de compra **borraba** las imputaciones (`db.delete`) y no sellaba fecha | Imputaciones se **marcan** (`anulado_at/anulado_por` en `imputaciones` e `imputaciones_compras`); `recibos`/`ordenes_pago`/`compras` sellan `anulado_at/anulado_por`. Los lectores filtran vivas; las anuladas no bloquean (p. ej. anular compra tras anular su OP) |
| Caja: DELETE físico de movimientos, retenciones y cierres (reabrir borraba el cierre sellado) | Soft-delete en los tres; unique de `caja_cierres` pasó a parcial (`WHERE anulado_at IS NULL`) → una fecha reabierta puede re-cerrarse sin perder la historia |
| Bancos: DELETE físico de movimientos manuales | Soft-delete; saldo/listados/conciliación excluyen anulados |
| Rechazo de cheque **reescribía `recibo.total`** | El total nunca se toca: `recibos.rechazado_total` acumula lo rechazado; `a_cuenta = total − aplicado − rechazado_total`. La fecha cierta queda en `cheque_eventos` |
| Kardex físico puro (sin costo por movimiento) → CMV/valuación retroactiva irreconstruible | `stock_movimientos.costo_unitario` **sellado** en cada movimiento: compras = costo REAL del ítem (neto tras bonifs; B/C el final ES el costo), resto = costo vigente normalizado (neteo IVA + USD→ARS por cotización, `services/stock_valor.py`). NULL = histórico pre-014 |
| `stock_movimientos.fecha` siempre `now()` (backdating desalineaba el kardex) | Si la fecha del documento ≠ hoy, el movimiento se sella con la fecha del papel |
| Ventas/compras CONTADO de gestión sin medio de cobro/pago (contrapartida indeterminable) | `POST /emitir` y `/registrar` aceptan `medios` opcionales (suman el total exacto); tabla nueva `compra_medios` (espejo de `venta_medios`). La UI de gestión los manda siempre (default efectivo). Compras contado con medios entran a la planilla global como pagos por su medio real; sin medios = comportamiento histórico (no retroactivo) |
| `medio='transferencia'` sin cuenta bancaria (texto libre) | `cuenta_bancaria_id` nullable en `recibo_medios`, `orden_pago_medios`, `venta_medios`, `caja_movimientos`, `compra_medios` (validado por tenant) |
| `saldo_inicial` de cuenta bancaria sin fecha de corte | `cuentas_bancarias.saldo_inicial_fecha` (para el asiento de apertura) |

**Diferido con destino explícito** (no bloquea F9):

- **Retención integrada al documento de cobro/pago** (hoy el recibo/OP no
  cuadra medios vs. total cuando hay retención; el vínculo es opcional y
  `SET NULL`) → **F10 Impuestos** (que ya prevé retenciones automáticas en OP).
- **Desglose de `otros_tributos` en ventas y jurisdicción de `percepcion_iibb`
  en compras** → F10 (percepciones `ImpTrib` + Convenio Multilateral).
- **Moneda/cotización en recibos, OP y compras** (diferencia de cambio) →
  gated por demanda de exportadores (regla multi-moneda OUT del ROADMAP).
- **ND automática por cheque rechazado** (documento formal + gastos de
  rechazo) → F9/F10; hoy el hecho queda fechado en `cheque_eventos` +
  `rechazado_total`.
- **Apareo de transferencias entre cuentas propias** (hoy `transferencia_in`
  y `_out` son movimientos sueltos) → F9 (cuenta puente o `grupo_id`).
- **PPP/FIFO**: no reconstruible retro (no había costo sellado); v1 de
  valuación = costo de reposición sellado. Capas FIFO = F9+ si un piloto lo pide.

## 4. Módulo F9 — Contabilidad (cuando se cumpla el gate)

### 4.1 Modelo (3 tablas + 2 de config)

- `plan_cuentas`: tenant_id, codigo (jerárquico `1.1.01`), nombre, tipo
  (`activo|pasivo|pn|r_positivo|r_negativo`), imputable bool, padre_id,
  activa. **Seed**: plan estándar argentino de comercio (esqueleto ~60
  cuentas), clonable/editable por tenant como los roles RBAC.
- `asiento_mapeos`: tenant_id, origen (enum de regla), clave (uuid/texto según
  la regla), cuenta_id. Es el espejo moderno de los `CUENTA C6` del legacy.
  Reglas mínimas v1:
  | origen | clave | ejemplo |
  |---|---|---|
  | `ventas_familia` | familia_id (NULL = default) | Ventas de mercadería |
  | `iva_debito` / `iva_credito` | tasa (NULL = única) | IVA DF/CF |
  | `deudores` / `proveedores` | NULL (cuenta control) | Deudores por ventas |
  | `medio` | efectivo/transferencia/tarjeta/mercadopago/otro | Caja / Tarjetas a acreditar |
  | `cuenta_bancaria` | cuenta_bancaria_id | Banco X c/c |
  | `cheques_cartera` / `cheques_diferidos` | NULL | Valores a depositar / Cheques diferidos a pagar |
  | `concepto_caja` | concepto_id | Gastos varios |
  | `retencion` | (tipo, regimen) | Ret. IVA a favor / a depositar |
  | `compras_familia` | familia_id (NULL = default) | Mercaderías / Gastos |
  | `percepciones` | iva/iibb/internos/otros | Percepción IIBB sufrida |
  | `inventario` / `cmv` / `ajuste_inventario` | NULL | Mercaderías / CMV |
  | `diferencias_caja` | sobrante/faltante | Sobrante de caja |
  | `redondeo` | NULL | Ajuste por redondeo |
- `asientos` + `asiento_lineas`: materializados PERO regenerables. Cada
  asiento sella `origen_tipo` + `origen_id` (el documento fuente) →
  idempotencia del motor: regenerar un período = borrar los asientos
  derivados del período (nunca los manuales) y re-derivar. `fecha` = fecha
  del documento (o `anulado_at` para reversiones).
- `ejercicios`/períodos: cierre mensual simple (un período cerrado no se
  regenera y bloquea anulaciones de documentos de ese período — extiende el
  patrón de `caja_cierres`).

### 4.2 Reglas de derivación (documento → asiento)

| Documento | Asiento (esquema) |
|---|---|
| Factura de venta emitida | Deudores (o medio si contado con `venta_medios`) a Ventas por familia + IVA DF por alícuota (+ percepciones cuando existan) |
| NC de venta | Inverso, fechado en la NC |
| Recibo | Medios (Caja/Banco/Valores en cartera/Tarjetas) a Deudores; la parte a cuenta va a Anticipos de clientes |
| Anulación de recibo | Reversión fechada en `anulado_at` (las imputaciones marcadas dicen qué revertir) |
| Compra registrada | Mercaderías/Gastos por familia + IVA CF por tasa (letra A) + percepciones a Proveedores (o medio si contado con `compra_medios`) |
| OP | Proveedores a medios; anulación → reversión fechada |
| Cheque: cada `cheque_evento` | en_cartera: (dentro del recibo) · depositado: Banco a Valores · acreditado: — (conciliación) · endosado: Proveedores a Valores · rechazado: Deudores por cheques rechazados a Valores · emitido propio: (dentro de la OP, a Cheques diferidos) · debitado: Cheques diferidos a Banco |
| Movimiento de caja manual | Concepto→cuenta contra medio→cuenta; anulado = reversión fechada |
| Movimiento bancario manual | tipo→cuenta (comisión = Gastos bancarios, etc.) contra Banco |
| Venta (kardex) | CMV a Mercaderías por `costo_unitario` sellado (valuación §4.3) |
| Ajuste de inventario | Ajuste de inventario a/de Mercaderías al costo sellado |
| Cierre de caja con diferencia | Sobrante/Faltante contra Caja |
| Retención | tipo/regimen→cuenta dentro del asiento del recibo/OP asociado (v1: asiento suelto si no está vinculada) |

### 4.3 Valuación v1

**Inventario permanente a costo de reposición sellado**: el kardex post-014
lleva `costo_unitario` neto ARS por movimiento. CMV = Σ(cantidad ×
costo_unitario) de los movimientos tipo venta. Los movimientos históricos
(costo NULL) se valorizan al costo vigente del artículo con una nota de
"apertura estimada" — o el tenant arranca la contabilidad desde una fecha de
corte con asiento de apertura (recomendado).

### 4.4 Salidas

Libro diario, mayor por cuenta, sumas y saldos, y **export al contador**
(CSV es-AR con `csv_response` de F5/F7; formato importable genérico). Balance
y activos fijos/amortizaciones completan el alcance F9 del ROADMAP.

### 4.5 Qué NO es (alcance negativo v1)

Sin posteo manual libre masivo (solo asiento manual simple), sin multi-moneda
contable, sin consolidación multi-empresa, sin cubos/BI (regla ERP-liviano:
son evoluciones gated).

## 5. Orden de implementación de F9 (cuando se active)

1. `plan_cuentas` + seed + ABM (calcado del gestor de roles).
2. `asiento_mapeos` + pantalla de mapeo con defaults sensatos (el seed mapea
   solo — el tenant ajusta después; TODO mapeo tiene fallback).
3. Motor de derivación + regeneración por período (con las 53 pruebas de la
   mini-fase como base de fixtures: cada documento de la suite debe derivar
   un asiento balanceado).
4. Diario/mayor/sumas y saldos + export.
5. Cierre de período + asiento manual simple.
6. Activos fijos + amortizaciones (alcance F9 del ROADMAP).

La prueba de fuego del diseño: **contabilizar retroactivamente el tenant DEMO
completo** (3 meses de operaciones sintéticas) sin tocar ningún módulo
operativo. Si algo no se puede derivar, es un gap del contrato §2 y se
arregla en el módulo de origen ANTES de construir encima.

## 6. F9-bis — Bienes de uso, balance, apertura, export contador y apareo (2026-07-11)

Cierra los diferidos explícitos de la F9 (v1 en producción 2026-07-11). Migración
016. Mismos principios: todo lo contable se DERIVA; los documentos fuente cumplen
el contrato §2.

### 6.1 Activos fijos (bienes de uso) + amortizaciones

- **Modelo**: `activo_categorias` (catálogo por tenant con `vida_util_meses`
  sugerida; seed lazy junto al plan: Rodados 60 · Muebles y útiles 120 · Equipos
  de computación 36 · Instalaciones 120 · Maquinarias 120 · Inmuebles 600) y
  `activos_fijos` (nombre, categoría FK —contrato MAPEABLE—, `fecha_alta`,
  `inicio_amortizacion` default 1° del mes de alta, `valor_origen`,
  `valor_residual`, `vida_util_meses`, `compra_id` opcional para trazabilidad,
  baja = `fecha_baja`+`baja_motivo`, error de carga = `anulado_at/anulado_por`).
- **El alta NO deriva asiento**: el bien entró al patrimonio por su documento
  (factura de compra —mapear la familia del ítem a la cuenta Bienes de uso—,
  asiento de apertura o asiento manual). El motor deriva SOLO amortizaciones y
  bajas — así no hay doble conteo.
- **Amortización lineal MENSUAL** (criterio v1; el legacy no amortizaba):
  cuota = (valor_origen − valor_residual) / vida_util_meses redondeada a 2
  decimales; la ÚLTIMA cuota absorbe el residuo de redondeo. Devenga desde el
  mes de `inicio_amortizacion` inclusive hasta agotar vida útil o hasta el mes
  ANTERIOR a `fecha_baja` (el mes de la baja no amortiza). El asiento es UNO
  por mes calendario — origen_tipo `amortizacion`, fechado el ÚLTIMO día del
  mes, con un par de líneas por activo (Debe Amortizaciones del ejercicio /
  Haber Amortización acumulada, detalle = nombre del activo) — y solo se genera
  cuando el fin de mes cae dentro del rango regenerado (mes en curso: aparece
  recién al regenerar con `hasta` ≥ fin de mes).
- **Baja**: asiento origen_tipo `activo_baja` fechado en `fecha_baja`:
  Debe Amortización acumulada (todo lo devengado) + Debe Resultado por baja de
  bienes de uso (valor residual contable) a Haber Bienes de uso (valor_origen).
  Si la baja fue por VENTA, la factura deriva su ingreso por las reglas de
  ventas — v1 no aparea venta↔baja (ajuste fino por asiento manual).
- **Anular un activo** (error de carga) = marcar; al regenerar, sus asientos
  derivados desaparecen — legítimo porque son artefactos regenerables, no
  documentos (§1).
- **Cuentas nuevas del plan base** (el seed lazy las agrega a tenants ya
  sembrados): 1.4 Bienes de uso (no imputable) · 1.4.01 Bienes de uso ·
  1.4.02 Amortización acumulada bienes de uso (regularizadora) · 5.1.07
  Amortizaciones del ejercicio · 5.1.08 Resultado por baja de bienes de uso.
  Mapeos nuevos (clave = categoria_id, fallback NULL obligatorio):
  `bienes_uso`, `amort_acumulada`, `amort_ejercicio`; `baja_bienes_uso` solo
  default.
- **Cuadro de bienes de uso** (reporte + CSV): valor de origen, amortización
  acumulada devengada al corte, valor residual contable, estado.

### 6.2 Apareo de transferencias entre cuentas propias

- `banco_movimientos.contrapartida_id` (self-FK, simétrico: se setea en ambos).
  Aparear exige: ambos vivos, tipos opuestos (`transferencia_out` ↔
  `transferencia_in`), MISMO importe, cuentas DISTINTAS, ninguno ya apareado.
  Anular un movimiento apareado lo desaparea primero (el otro queda suelto).
- **Motor**: un par apareado deriva UN asiento (origen_tipo `banco_transfer`,
  fechado y anclado en el movimiento de SALIDA): Debe Banco destino / Haber
  Banco origen — sin pasar por la cuenta puente 1.1.06. El movimiento de
  entrada apareado se saltea. Sin aparear, sigue derivando por la puente (v1).

### 6.3 Balance general (estado de situación patrimonial)

`GET /contabilidad/balance?hasta=` — saldos por cuenta al corte (asientos
vivos), presentados en el árbol del plan (rollup a cuentas no imputables) para
Activo / Pasivo / PN, con el **Resultado del ejercicio** (Σ ingresos − egresos
acumulados al corte) inyectado como línea del PN. Verifica la ecuación
Activo = Pasivo + PN. Asume que la historia previa al inicio de la contabilidad
entró por asiento de apertura (§6.5). Export CSV e impresión desde el front.

### 6.4 Export al contador

`GET /contabilidad/export-contador.zip?desde&hasta` — paquete ZIP (patrón CITI
de F5) con 4 CSV es-AR: plan de cuentas, libro diario por línea, sumas y
saldos, y mayor completo (todas las cuentas con movimientos). Formato genérico
importable; NO se inventan layouts propietarios de terceros (Tango/Bejerman/
Holistor) sin la especificación real de un contador usuario — cuando un piloto
lo pida, se agrega como writer nuevo sobre las mismas consultas.

### 6.5 Asiento de apertura asistido

- `GET /contabilidad/apertura/sugerencia` propone las líneas desde los datos
  vivos del sistema: saldo por cuenta bancaria, Deudores por ventas (saldos
  cta. cte.), Proveedores (saldos cta. cte.), Valores a depositar (cheques de
  terceros en cartera), Cheques diferidos a pagar (propios emitidos),
  Mercaderías (stock valorizado) — y la contrapartida residual a Capital.
  Advertencia explícita: los saldos son al día de HOY (si la apertura se fecha
  hacia atrás, revisar a mano).
- `POST /contabilidad/apertura` crea el asiento con origen_tipo **`apertura`**:
  la regeneración NUNCA lo borra (el delete del motor excluye `manual` y
  `apertura`), se anula marcando como los manuales, y solo puede haber UNO
  vivo por tenant (409).
