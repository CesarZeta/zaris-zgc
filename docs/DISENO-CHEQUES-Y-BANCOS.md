# Diseño Fase 8 — Cheques y Bancos + Cash-flow proyectado

> Estado: **PROPUESTA** (2026-07-06). Decisiones de alcance tomadas por César:
> ciclo de vida **completo** de cheques · cuentas + movimientos + **conciliación por
> import** · **cash-flow proyectado** dentro de F8. Ejecución: plan → revisión → código.
> Regla rectora #0: todo lo de acá se verifica contra la realidad al implementar.

## 0. Punto de partida (verificado 2026-07-06)

- **No existe** ningún modelo de cheques ni bancos en el backend (grep en `app/models` vacío).
  F8 es greenfield sobre el modelo de datos.
- El **seam de integración ya existe**: `recibo_medios` (cobranzas de ventas),
  `orden_pago_medios` (pagos de compras) y `caja_movimientos` tienen un campo
  `medio` texto libre (`String(15)`) + `referencia`/`descripcion`. Hoy un cheque cobrado
  es solo `medio="cheque"` con el número en `referencia` — **sin entidad, sin cartera,
  sin ciclo de vida**. Ese es el gap que cierra F8.
- El **núcleo fiscal/contable no se toca**: los recibos y las OP siguen registrando el
  total y sus medios como hoy; F8 agrega la materialización del cheque como activo/pasivo
  y su circulación, colgada del medio.
- **Legacy de referencia** (`cheques.DBF`, 33 campos, y `GV0036A` con `ESTADO`): el modelo
  canónico ya distingue propio/tercero (`PROP_TER`), cartera/pasivo (`CART_PAS`),
  rechazo (`RECHAZADO`), endoso (`PASADO_A`/`FPASADO`), origen/destino
  (`CODCLI`/`CPROV`, `NCOM_ENT`/`NCOM_SAL`), firmante, CUIT y banco. No inventamos: lo
  modernizamos con estados explícitos y FKs.
- Próxima migración: **013** (la 012 fue la última aplicada en prod).

## 1. Modelo de datos (migración 013, aditiva)

Todo con `tenant_id` + RLS (segunda línea, patrón §1-bis del CLAUDE.md). UUID global.

### 1.1 `cuentas_bancarias`
Cuenta propia del tenant (para depósitos de cheques, transferencias, débitos).
```
id, tenant_id, banco (str), sucursal_bancaria (str, opc), tipo (CC | CA),
numero (str), cbu (str 22, opc), alias (str, opc), moneda (ARS | USD, default ARS),
saldo_inicial (numeric, default 0), activa (bool, default true),
observaciones, created_at
```
Sin DELETE (se inactivan; movimientos las referencian). El **saldo actual** es
`saldo_inicial + Σ movimientos` (calculado, no columna).

### 1.2 `banco_movimientos`
Movimientos de una cuenta bancaria. Signo por `tipo`.
```
id, tenant_id, cuenta_id (FK cuentas_bancarias), fecha (date),
tipo (deposito | extraccion | transferencia_in | transferencia_out | debito |
      credito | comision | ajuste),
importe (numeric, > 0; el signo lo da el tipo),
descripcion (str), referencia (str, opc),
cheque_id (FK cheques, opc — depósito/acreditación de un cheque),
conciliado (bool, default false), fecha_conciliacion (date, opc),
extracto_import_id (FK, opc — de qué import vino),
origen (str: 'manual' | 'cheque' | 'import' | 'sistema'),
creado_por, created_at
```
Índice por `(tenant_id, cuenta_id, fecha)` y por `cheque_id` solo (regla selectin del CLAUDE.md).

### 1.3 `cheques`
El corazón de F8. Un cheque, propio o de tercero, con su máquina de estados.
```
id, tenant_id,
clase (str): 'tercero' | 'propio'          -- PROP_TER del legacy
numero (str 20), banco (str), sucursal_banco (str, opc), plaza (str, opc),
titular (str, opc — firmante/EMITIDO), cuit_firmante (str, opc),
fecha_emision (date, opc), fecha_pago (date)  -- FECVTO: al día / diferido
importe (numeric > 0), moneda (ARS | USD, default ARS),
es_echeq (bool, default false),               -- e-cheq vs físico (diferencial moderno)
-- origen (de dónde entró):
cliente_id (FK clientes, opc)     -- tercero recibido en cobranza
recibo_id  (FK recibos, opc)      -- comprobante de entrada
-- destino (a dónde salió), según estado:
proveedor_id (FK proveedores, opc)  -- endosado / propio emitido a este proveedor
orden_pago_id (FK ordenes_pago, opc)
cuenta_id (FK cuentas_bancarias, opc)  -- cuenta propia (cheque propio) o de depósito
banco_movimiento_id (FK banco_movimientos, opc)  -- el movimiento que lo acreditó/debitó
estado (str)  -- ver máquina §2
observaciones, creado_por, created_at, updated_at
```
Índices: `(tenant_id, estado)`, `(tenant_id, fecha_pago)` (para cartera y cash-flow),
FKs sueltas `cliente_id` / `proveedor_id` / `cuenta_id`.

### 1.4 `cheque_eventos` (bitácora de estados)
Auditoría inmutable de cada transición (quién, cuándo, de→a, importe, contraparte).
```
id, tenant_id, cheque_id (FK), fecha (date), estado_desde, estado_hasta,
detalle (str), banco_movimiento_id (opc), creado_por, created_at
```

### 1.5 `extracto_imports`
Cabecera de cada import de extracto bancario (para trazabilidad y deshacer).
```
id, tenant_id, cuenta_id (FK), nombre_archivo (str), filas_total (int),
filas_conciliadas (int), fecha_import (timestamp), creado_por
```

## 2. Máquina de estados del cheque

### Cheque de TERCERO (activo — entra a cartera)
```
en_cartera ──depositar──▶ depositado ──acreditar──▶ acreditado (final)
     │                          │
     ├──endosar (a proveedor)──▶ endosado (final)
     ├──rechazar──────────────▶ rechazado ──(regularizar)──▶ en_cartera | perdido
     └──anular (error de carga)▶ anulado
depositado ──rechazar──▶ rechazado
```
- **en_cartera**: creado al cobrar (recibo con `medio=cheque`). Es un activo disponible.
- **depositado**: entregado al banco, aún no acreditado (genera `banco_movimiento`
  tipo `deposito` NO conciliado; el importe todavía no suma saldo "disponible" real
  hasta acreditar — se distingue en el cash-flow).
- **acreditado**: el banco lo pagó (movimiento conciliado). Final feliz.
- **endosado**: usado para pagar a un proveedor (OP con `medio=cheque` eligiendo un cheque
  de cartera). Sale de cartera sin tocar banco. Final.
- **rechazado**: sin fondos. Reabre la cuenta corriente del cliente (deuda) — **integra con
  ventas**: un rechazo genera contra-asiento en cta.cte. del cliente (queda debiendo otra vez).
- **anulado**: error de carga, revierte el cobro.

### Cheque PROPIO (pasivo — lo emito yo)
```
emitido ──debitar──▶ debitado (final)      -- el banco lo pagó
   │
   ├──entregado (a proveedor, en OP)  (sub-estado / mismo 'emitido' con proveedor_id)
   └──anular──▶ anulado
```
- **emitido**: creado al pagar una OP con cheque propio (contra una `cuenta_bancaria`).
  Es un pasivo: compromete saldo futuro de la cuenta (cash-flow).
- **debitado**: el banco lo pagó → `banco_movimiento` tipo `debito` conciliado. Final.
- **anulado**: revierte.

> Cada transición escribe `cheque_eventos` y, cuando toca banco, crea/concilia un
> `banco_movimiento`. La lógica vive en un **core sin commit** (`cheques_core.py`,
> patrón `emitir_core`/`crear_nc_espejo_core` del CLAUDE.md §6) para que la puedan
> llamar la cobranza (ventas), la OP (compras) y los endpoints de cheques dentro de su
> propia transacción, sin duplicar.

## 3. Integración con lo existente (sin romper el núcleo)

- **Cobranza de ventas** (`recibos` + `recibo_medios`): cuando un medio es `cheque`, el
  endpoint acepta opcionalmente los datos del cheque → llama `cheques_core.recibir_tercero`
  → crea el cheque `en_cartera` linkeado al recibo. Compat: si no manda datos de cheque,
  se comporta como hoy (solo el medio, sin materializar). **Cero cambios rompientes.**
- **Orden de pago de compras** (`ordenes_pago` + `orden_pago_medios`): un medio `cheque`
  puede (a) **endosar** un cheque de cartera existente (elige `cheque_id`) o (b) **emitir**
  un cheque propio contra una `cuenta_bancaria`. El core resuelve ambos.
- **Caja (F5)**: un cheque **no es efectivo** — no entra a la planilla de caja como
  movimiento de efectivo (ya hoy `caja_movimientos.medio` lo distingue). El depósito/
  acreditación afecta **banco**, no caja. Se documenta para no doble-contar.
- **Dashboard (F7)**: nuevos KPIs candidatos (no obligatorios en F8): "cheques en cartera"
  (Σ terceros `en_cartera`), "cheques a depositar hoy", "saldo bancario". Cada uno con su
  permiso `bancos.ver` (null si no lo tiene, nunca 403 — regla F7).

## 4. Endpoints (RBAC desde el día 1 — módulo nuevo `bancos`)

Todo endpoint nace con `Depends(requiere("bancos", accion))` (regla CLAUDE.md §6). El
catálogo de módulos en `app/core/permisos.py` **y** el seed de la migración 010 suman
`bancos` (ESPEJO obligatorio: cambiar uno exige el otro). GET=`ver`, escritura=`editar`,
anulación/rechazo=`anular`.

```
# Cuentas bancarias
GET    /bancos/cuentas                 (ver)     listado liviano
POST   /bancos/cuentas                 (editar)
PUT    /bancos/cuentas/{id}            (editar)
POST   /bancos/cuentas/{id}/inactivar  (editar)
GET    /bancos/cuentas/{id}            (ver)     detalle + saldo calculado

# Movimientos bancarios
GET    /bancos/cuentas/{id}/movimientos (ver)    con filtro fecha/conciliado
POST   /bancos/cuentas/{id}/movimientos (editar) manual (transferencia, débito, comisión)
POST   /bancos/movimientos/{id}/conciliar (editar)
DELETE /bancos/movimientos/{id}          (anular) solo si origen=manual y no conciliado

# Conciliación por import de extracto
POST   /bancos/cuentas/{id}/extracto/preview (ver)   parsea CSV, propone matcheo, NO persiste
POST   /bancos/cuentas/{id}/extracto/import  (editar) confirma y crea movimientos + concilia

# Cheques
GET    /cheques                        (ver)     cartera + filtros (clase/estado/fecha/contraparte)
POST   /cheques                        (editar)  alta manual de cheque de tercero en cartera
GET    /cheques/{id}                   (ver)     detalle + eventos
POST   /cheques/{id}/depositar         (editar)  elige cuenta → banco_movimiento
POST   /cheques/{id}/acreditar         (editar)  concilia el depósito
POST   /cheques/{id}/endosar           (editar)  a un proveedor (opc dentro de una OP)
POST   /cheques/{id}/rechazar          (anular)  reabre cta.cte. del cliente
POST   /cheques/{id}/anular            (anular)
GET    /cheques/export.csv             (ver)     helper csv_export (F7), filtros del listado

# Cash-flow proyectado (tesorería)
GET    /tesoreria/cashflow             (ver)     ver §5
```

## 5. Cash-flow proyectado (tesorería)

Reporte, **no** tabla. Proyecta el saldo de tesorería día a día (o por semana/mes) sobre
lo que YA está registrado — sin pedir datos nuevos:

**Saldo inicial** = efectivo en caja (F5) + Σ saldos de cuentas bancarias.
**Entradas proyectadas** (por fecha):
- Vencimientos de cta.cte. de **clientes** (saldos deudores de ventas a crédito).
- Cheques de **tercero** en cartera → por `fecha_pago` (a depositar/acreditar).
**Salidas proyectadas** (por fecha):
- Vencimientos de cta.cte. de **proveedores** (saldos por OP pendientes / facturas a pagar).
- Cheques **propios** `emitido` → por `fecha_pago` (a debitar).

Salida: serie temporal `[{fecha, entradas, salidas, saldo_proyectado}]` + detalle
expandible por concepto. Parámetros: `desde`/`hasta`, `granularidad` (dia|semana|mes).
Guardado por `bancos.ver` (o un `tesoreria.ver` si preferís separarlo — **decisión menor,
propongo reusar `bancos`**). Agregaciones que arrancan con función escalar llevan
`.select_from()` explícito (lección Fase 7).

## 6. Frontend (React) — «ZARIS Heredado»

- Nuevo módulo **`bancos/`** con página "Bancos y Cheques" (el ítem ya existe como `soon`
  en el sidebar de `AppShell` — solo hay que activarlo con su `modulo: "bancos"`).
- Tabs: **Cartera de cheques** (tabla con chips de estado por color — NUNCA naranja, que es
  brand; verde acreditado, rojo rechazado, etc.) · **Cuentas bancarias** (ABM + movimientos +
  conciliación) · **Tesorería** (cash-flow, tabla + mini-serie).
- Acciones del cheque = botones que abren diálogos (`useDialogos`, cero `window.confirm`).
- Importes `tabular-nums` + JetBrains Mono; números por `Intl` es-AR.
- Conciliación por import: input de archivo → preview con matcheo propuesto → confirmar.

## 7. Plan de ejecución (orden)

1. **Migración 013** (`sql/013_cheques_bancos.sql`) + modelos SQLAlchemy + RLS. Aditiva,
   idempotente, segura de aplicar sola (el backend viejo no la lee) — **va a prod ANTES**
   del push del backend (regla §7). La aplica César por psql (el MCP no ve el proyecto ZGC).
2. **Módulo `bancos` en el catálogo de permisos** (`permisos.py` + seed migración 010 espejo;
   como es tenant existente, un pequeño `INSERT ... ON CONFLICT` para los roles de sistema).
3. **`cheques_core.py`** (transiciones sin commit) + endpoints de cheques.
4. **Bancos**: cuentas, movimientos, conciliación (preview/import CSV).
5. **Integración**: cobranza de ventas y OP de compras aceptan/emiten cheques por el core.
6. **Cash-flow** `/tesoreria/cashflow`.
7. **Frontend**: módulo bancos (3 tabs) + activar ítem del sidebar.
8. **Pruebas en vivo** (patrón de las fases previas): suite API contra dev con sufijo único
   por corrida, deltas en agregados, regresión de recibos/OP; luego smoke contra prod
   post-deploy. E2E navegador de la cartera + conciliación + cash-flow.
9. **Cierre**: ROADMAP + HISTORIAL + memoria juntos; verificación visual en prod.

## 8. Decisiones abiertas (menores, para confirmar al implementar)

- **e-cheq**: incluyo el flag `es_echeq` desde ya (diferencial moderno, costo cero), pero
  sin integración con el sistema de e-cheq del banco (fuera de alcance F8; solo registro).
- **Formato de extracto**: arranco con **CSV genérico** (columnas mapeables: fecha, detalle,
  importe, tipo). Formatos propietarios por banco (Galicia/Santander/etc.) quedan como
  patrón extensible, no en F8.
- **Módulo de permiso del cash-flow**: propongo reusar `bancos.ver` (no crear `tesoreria`).
- **Multimoneda**: cuentas y cheques llevan `moneda` pero F8 opera en ARS; USD queda
  registrable pero sin conversión en el cash-flow (coherente con el "OUT salvo exportadores"
  del ROADMAP).
```
