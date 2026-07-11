# ZGC — Diseño: perfiles de POS (Estándar/Súper · Carnicería · Resto) y sucursales

> Mandato de César (2026-07-05): los puntos de venta deben ofrecer tres configuraciones
> — estándar para todo tipo de mercaderías y pesables, restaurante (mesas, mozos,
> comandas que quedan EN el POS) y carnicería (ingreso por media res, stock en kilos
> por corte) — y pertenecer a una sucursal. Extiende `DISENO-RUBROS-Y-VARIANTES.md`
> §4.1 ("el rubro decide qué POS se sirve a las cajas").
>
> Mandato de César (2026-07-11): el POS además debe poder **venderse como módulo
> independiente** (licencia POS-only para kiosco, carnicería, resto — súper no),
> sin instalación on-premise. Diseño en §7; reordena el plan de ejecución (§6-bis).
>
> **Estado: IMPLEMENTADO (2026-07-11)** — F12-a (plan por tenant, migración 018),
> F12-b (pesables/envases/depto, migración 019), F12-c (despiece, migración 020) y
> F12-d (POS resto, migración 021) están EN PRODUCCIÓN. Este doc queda como diseño de
> referencia; los detalles finales de implementación están en el ROADMAP (FASE 12).

## 0. Principios

1. **Un solo circuito fiscal.** Todos los perfiles emiten por `emitir_core`
   (CLAUDE.md §6): la venta final siempre es un comprobante de Fase 3 con CAE,
   stock, medios y sesión de caja. El perfil cambia la pantalla y las capacidades
   operativas, nunca el circuito de emisión.
2. **Lo operativo del rubro vive en el POS** (mandato explícito para resto): mesas,
   comandas, cocina, despachos NO se trasladan a la gestión central — a la gestión
   llega solo el comprobante emitido con sus medios de pago.
3. **El perfil es de la caja, con default por rubro del tenant**: `pos_cajas.perfil`
   (`estandar` | `resto`; carnicería NO es un perfil de POS, ver §2), precargado según
   `tenants.rubro`. Un mismo tenant puede mezclar (ej.: parrilla con mostrador de
   venta de carne = 1 caja resto + 1 caja estándar).
4. **El modelo de datos de gestión no se bifurca** (regla §1-ter del CLAUDE.md):
   los perfiles agregan tablas `pos_*` y capacidades de stock generales, no variantes
   del maestro ni de comprobantes.

## 1. Perfil ESTÁNDAR / SÚPER (evolución del POS actual)

Es el POS que ya está en producción (ver `MANUAL-POS.md`), completado con lo diferido
de Fase 6 (los flags ya existen en el maestro desde la migración 003):

- **Pesables por etiqueta de balanza** — la pieza clave de súper Y carnicería.
  Etiquetas EAN-13 con prefijo 20–29: `P PP CCCCC VVVVV D` (prefijo + código de
  artículo + valor embebido). Diseño:
  - Config por tenant (en Configuración): prefijo usado, si el valor embebido es
    **peso** (gramos) o **importe** (centavos), y cuántos dígitos tiene cada parte —
    las balanzas Kretz del legacy (drivers en `Revosolution Software/`) usan este
    esquema clásico.
  - Parsing en `GET /pos/buscar` (server-side, no en el front): detecta el prefijo,
    extrae código y valor, resuelve el artículo por su código de balanza y devuelve
    la línea con cantidad = peso, o cantidad = importe/precio si la etiqueta embebe
    importe. El front solo escanea, como siempre.
  - Nuevo campo `articulos.codigo_balanza` (el PLU corto que imprime la balanza),
    único por tenant.
- **Envases retornables**: al vender un artículo con `envase_articulo_id`, el POS
  agrega/sugiere la línea del envase; botón "devolución de envases" (línea negativa
  no fiscal o descuento — definir con el primer piloto contra la práctica real).
- **Venta por departamento**: tecla de departamento + importe para lo no codificado
  (`venta_por_depto` ya existe como flag).
- **Multi-caja**: ya funciona (N cajas por PV/depósito); falta solo el concepto de
  sucursal en la UI (§4).

## 2. Perfil CARNICERÍA

**Hallazgo de diseño**: la carnicería NO necesita un POS distinto — vende cortes
pesables igual que un súper (balanza o peso tipeado). Lo específico del rubro está en
la **gestión de stock**: el ingreso por media res y su transformación a cortes.
Por eso "carnicería" no es un valor de `pos_cajas.perfil` sino: perfil estándar con
pesables + el **despiece** en gestión + rubro `carniceria` en `tenants.rubro` (preset:
pesables on, atributos sugeridos, UI de despiece visible).

### 2.1 El negocio (lo que pidió César)

La carnicería compra **medias reses** (media vaca): la factura del frigorífico viene
en kilos de media res a un costo por kg. Después el carnicero la **despuesta** en
cortes (asado, vacío, matambre, lomo, nalga, osobuco, hueso, grasa...) y el stock y
la venta son **por corte, en kilos**. Se necesita: ingresar la media res por su costo
total, y cargar los kilos obtenidos de cada corte para llevar stock por corte.

### 2.2 Diseño: transformación de stock (despiece)

Nueva capacidad **general** del módulo Stock (no exclusiva de carnicería — sirve
igual para fraccionar una bolsa de 25 kg en paquetes de 1 kg o armar combos):

- **Nuevo tipo de movimiento `transformacion`** (ampliar el CHECK de
  `stock_movimientos.tipo`, hoy 8 tipos): una salida del artículo origen + N entradas
  de artículos destino, todas atadas por `grupo_id` (mismo patrón que la
  transferencia interdepósito de Fase 2, que ya resuelve locks y kardex).
- **Merma explícita**: `kg origen − Σ kg cortes` queda registrada en el movimiento de
  salida (observaciones + campo de merma en la pantalla). En carne real la merma es
  2–5% (hueso perdido, escurrido) — si no se registra, el stock nunca cierra.
- **Plantillas de despiece** (`despiece_plantillas` + `despiece_plantilla_cortes`,
  por tenant): artículo origen (MEDIA RES, unidad kg, `controla_stock`) + lista de
  cortes con **% de rendimiento sugerido** y **coeficiente de valor**. La plantilla
  precarga la pantalla; los kilos reales se corrigen a mano en cada ingreso.
- **Pantalla "Ingreso de media res"** (módulo Stock, visible con rubro carnicería):
  1. Se elige la plantilla + peso total + costo total (tipeado, o tomado de la
     factura de compra del frigorífico ya registrada en Fase 4).
  2. La grilla propone kilos por corte (% de la plantilla × peso), **editables**.
  3. Muestra la merma resultante en vivo.
  4. Confirmar genera la transformación (salida media res + entradas por corte) y
     actualiza el **costo por corte**.
- **Costeo proporcional al valor, no al peso**: el lomo no puede costar por kg lo
  mismo que el hueso. `costo_kg(corte) = costo_total × coef(corte) /
  Σ(coef_i × kg_i)`. Ejemplo con media res de 100 kg a $500.000:

  | Corte | kg | Coef. valor | Costo/kg asignado |
  |---|--:|--:|--:|
  | Lomo | 4 | 3,0 | $11.194 |
  | Asado | 18 | 1,5 | $5.597 |
  | Nalga | 12 | 1,8 | $6.716 |
  | ... | ... | ... | ... |
  | Hueso/grasa | 8 | 0,2 | $746 |

  (Con coef. 1,0 en todos, degrada a prorrateo simple por peso — el modo "fácil".)
- La venta de cortes es POS estándar con pesables (§1). Nada más que agregar del
  lado de la caja.

## 3. Perfil RESTO (sucesor de RevoSolution RestoDelivery)

### 3.1 Lo que hay en el legacy (relevado 2026-07-05)

Existió un producto separado: **RestoDelivery** (ejecutables 2008-2009 en
`Revosolution Software/Resto Delivery/` y backups reales de clientes en
`BAck UP CLiente/Super Restaurantes y Delivery/` y `bonafide/`). Su modelo, ya
extraído en `docs/legacy/esquema-dbf.md`:

- **`MESAS`** (§esquema, 11.637 registros reales): la mesa es una **cuenta abierta** —
  número de mesa + datos del cliente ocasional + `TOTAL` + `PORC_PROP` (propina) +
  `HORA`. Confirma el diseño: la mesa vive en el POS y al cerrar se factura.
- **`PLATOS`**: el plato es un artículo simplificado (código, descripción, precio,
  tasa IVA, `RUBRO` de carta).
- Hay backups con datos reales de clientes resto para calibrar el diseño cuando se
  construya (mismo método recon que clientes/proveedores/artículos).

### 3.2 Alcance v1

- **Salones y mesas**: `pos_salones` (sectores: salón, vereda, barra) y `pos_mesas`
  (número, salón, estado: libre / ocupada / por cobrar). Grilla visual de mesas como
  pantalla principal de la caja resto.
- **Mozos**: usuarios comunes (con la Fase 6.5, rol "mozo"); cada comanda registra
  quién la tomó. Reporte de ventas por mozo EN el POS (para propinas/control).
- **Comandas**: `pos_comandas` + `pos_comanda_items` — la cuenta abierta de la mesa.
  Ítems con observaciones libres ("sin sal", "punto jugoso") y estado de cocina
  básico (pendiente/enviado). **Envío a cocina** = impresión de comanda en la
  impresora del sector (mismo mecanismo térmico del ticket, plantilla comanda).
- **Operaciones de salón**: mover cuenta de mesa, unir mesas, dividir la cuenta
  (por partes iguales v1), **propina %** (línea no fiscal en el cobro, como el
  legacy `PORC_PROP`).
- **Cierre de mesa** → pantalla de cobro del POS actual (medios múltiples, vuelto)
  → factura fiscal vía `emitir_core`. **La mesa abierta NO es un comprobante**: el
  comprobante nace recién al cobrar (evita basura de borradores fiscales).
- **Delivery / take-away**: pedido con domicilio del cliente **normalizado con OSM**
  (cruza con `DISENO-LOGISTICA-Y-DOMICILIOS.md`), estados mínimos
  (en preparación / despachado / entregado).
- **Regla dura (mandato César)**: mesas, comandas y cocina viven en tablas `pos_*`
  y NO se trasladan a la gestión. A la gestión llega SOLO la venta final
  (comprobante + medios), como cualquier venta POS. Los reportes de mesas/mozos son
  pantallas del POS, no del backoffice.

### 3.3 Diferido a v2 (documentado para no cerrar puertas)

- Recetas / descarga de insumos (el plato descuenta materia prima) — el legacy
  tampoco lo hacía; los platos pueden nacer con `controla_stock=false`.
- Modificadores estructurados con precio (hoy: observación libre).
- KDS (pantalla de cocina en vez de impresora), reservas, integración con pedidos
  online (Rappi/PedidosYa) — integraciones de canal, regla F13.
- División de cuenta por ítem.

### 3.4 Prerrequisitos

- Rubro `restaurante` en el CHECK de `tenants.rubro` + preset (era "post-MVP" en
  DISENO-RUBROS-Y-VARIANTES §4.1 — este doc lo especifica).
- `pos_cajas.perfil` (`estandar`/`resto`).
- Impresoras por sector (config de caja/salón).

## 4. Sucursales en el POS

**Estado real (verificado 2026-07-05)**: mejor de lo esperado —

- La tabla `sucursales` existe **desde la migración 001** (nombre, domicilio,
  localidad, teléfono, activa, por tenant).
- Ya tienen `sucursal_id` (nullable): `usuarios`, `depositos`, `puntos_venta`,
  `pos_cajas`, `caja_movimientos`, `caja_cierres`.
- `comprobantes` NO la tiene: la sucursal de una venta se **infiere por su punto de
  venta** (así filtra hoy la planilla de caja por sucursal). Decisión: mantener la
  inferencia, no duplicar la columna.
- Lo único que falta es **operativo**: no hay ABM de sucursales (solo se crean por
  script) ni asignación desde la UI.

**Plan (barato, F7)**:

1. ABM de sucursales en Configuración (con domicilio normalizado OSM cuando esté §1
   del doc de logística).
2. Al crear/editar una caja POS: selector de sucursal, **obligatorio si el tenant
   tiene más de una** activa.
3. Los reportes de POS/caja ya salen por sucursal vía PV — verificar que la cadena
   caja → PV → sucursal quede consistente al asignar.

**No confundir** "pertenencia a sucursal" (esto — organizativo, barato) con el
**nodo LAN de sucursal** (servidor local + sincronización para facturar sin internet,
CLAUDE.md §3): eso sigue siendo una fase propia y cara (ROADMAP F13), sin código hoy.

## 5. Qué NO cambia

El maestro de artículos y variantes, el circuito borrador→emitir→NC espejo, la
numeración fiscal, la cta. cte., la caja/planilla y el arqueo por sesión: todos los
perfiles se montan sobre lo existente.

## 6. Orden recomendado (propuesta 2026-07-05 — superada por §6-bis)

| Pieza | Cuándo | Por qué |
|---|---|---|
| ABM sucursales + sucursal en caja | **F7** (post-MVP inmediato) — ✅ hecho en F7 | La tabla ya existe; esfuerzo bajo; ordena multi-caja ya |
| Pesables por balanza (§1) | F12 — **adelantable** apenas haya piloto súper o carnicería | Es EL hardware de ambos rubros; el resto del perfil súper puede esperar |
| Despiece carnicería (§2) | F12 — **adelantable solo**, no depende del POS | Es stock puro de gestión; junto con pesables habilita el rubro completo |
| Envases + venta por depto. | F12 | Demanda ex clientes RevoSolution |
| POS Resto (§3) | F12, al final — el más grande (UI nueva completa + tablas nuevas) | Mercado nuevo para ZGC: validar con un piloto real antes de construir |

## 7. POS como módulo independiente — plan por tenant (mandato 2026-07-11)

> Mandato de César: el POS debe poder implementarse **de manera independiente del resto
> de la suite** — vender una licencia de solo-POS a un kiosco, una carnicería o un
> restaurante, donde el usuario lleve mínimamente **stock, facturación, clientes y
> listados de ventas**. Sin instalación on-premise. Para supermercado NO aplica
> (siempre suite completa).

### 7.1 Hallazgo de diseño: es packaging, no fork

"Independiente" NO significa otra app, otro backend ni otro deploy. El mismo SaaS
multi-tenant sirve a los tenants POS-only; la independencia es **comercial y de UX**,
implementada como un **plan por tenant** que acota qué módulos existen para ese tenant.
Consecuencias directas:

- **Cero bifurcación** de código o modelo de datos (regla §1-ter del CLAUDE.md).
- **Upgrade a suite = cambiar el plan**: los datos ya están en las mismas tablas; el
  kiosco que crece "desbloquea" Compras/Bancos/Contabilidad sin migrar nada.
- Todo lo que el plan POS incluye **ya está construido** (F1–F6): el costo de F12-a es
  el mecanismo de gating + onboarding, no features.
- **NO es el nodo LAN** (CLAUDE.md §3): el mandato dice explícitamente "sin instalación
  on-premise". El tenant POS-only opera online contra la nube; facturar sin internet
  sigue siendo la fase del nodo de sucursal (F13), ortogonal a esto.

### 7.2 Mecanismo: `tenants.plan` + intersección con el RBAC existente

- **Migración**: `tenants.plan varchar(20) not null default 'suite'`
  `check (plan in ('suite','pos'))`. Aditiva e idempotente; los tenants existentes
  quedan `suite` sin tocarlos.
- **Catálogo** `PLANES: dict[str, set[str]]` en `app/core/permisos.py`, junto a
  `MODULOS` (misma regla de mantenimiento: es EL espejo; `suite` = todos los módulos).
- **`permisos_efectivos()` interseca con los módulos del plan** antes de devolver.
  Como el login ya devuelve `permisos` top-level y el nav del front ya se filtra por
  ese mapa (F6.5), **el frontend se recorta solo, sin cambios** para el gating del menú.
  Cubre también `rol_id NULL` (acceso total = todos los módulos DEL PLAN, no del sistema).
- **`requiere()`/`requiere_alguno()` chequean plan ANTES que rol**: módulo fuera del
  plan → **403** "módulo no incluido en el plan" (nunca 401, regla §6). Con esto los
  ~130 endpoints existentes quedan guardados sin tocarlos uno por uno.
- **Quién fija el plan**: ZARIS al vender (v1 por script/SQL — no hay billing).
  En Configuración → Empresa se muestra read-only ("Plan: POS" / "Plan: Suite completa").
- Los KPIs del inicio ya devuelven `null` por módulo sin permiso (F7) → el dashboard
  se adapta solo al plan.
- **Autenticación y usuarios incluidos** (precisión de César 2026-07-11): el plan POS
  trae el módulo `configuracion`, que ES el gestor de usuarios y roles de F6.5 — login
  JWT, ABM de usuarios, roles con niveles Ver/Editar/Anular por módulo, anti-lockout,
  más el `nivel_acceso` de supervisor del POS. El tenant POS-only administra su propia
  seguridad con la MISMA granularidad que la suite, solo que sobre sus módulos:
  `GET /permisos/catalogo` se filtra por plan, así la matriz del editor de roles no
  muestra filas de módulos que el tenant no tiene (los roles base sembrados pueden
  tener permisos de módulos fuera del plan: son inertes por la intersección y quedan
  listos para el upgrade).

### 7.3 Matriz del plan `pos` (recomendación, César ajusta)

| Módulo | ¿Incluido? | Por qué |
|---|:-:|---|
| `pos` | ✔ | El producto. |
| `articulos` | ✔ | Catálogo, precios, variantes — "llevar stock" lo exige. |
| `stock` | ✔ | Kardex, ajustes; con rubro carnicería trae el despiece (§2). |
| `clientes` | ✔ | BUE + cta. cte. — "clientes" del mandato. |
| `ventas` | ✔ | Listados/detalle/export CSV, cobranzas, cta. cte. Ya construido; costo cero. |
| `caja` | ✔ | Planilla del día + salidas manuales: sin Compras, es la única vía de registrar los gastos del kiosco. |
| `libros_iva` | ✔ | El IVA ventas al contador es argumento de venta (fiscal nativo). El de compras queda vacío y no molesta. |
| `configuracion` | ✔ | Usuarios/roles, ARCA, PV, cajas POS, empresa. |
| `proveedores` + `compras` | ✘ | Upsell a suite. |
| `vendedores` | ✘ | Upsell. |
| `bancos` | ✘ | Upsell. |
| `contabilidad` | ✘ | Upsell (ya era módulo activable por diseño de producto). |

### 7.4 Viabilidad standalone por rubro

| Rubro | ¿Standalone? | Qué necesita |
|---|:-:|---|
| Kiosco / almacén | ✔ | **Nada nuevo salvo F12-a**: el POS actual (F6) ya cubre escaneo, medios, arqueo. Primera licencia vendible. |
| Carnicería | ✔ | F12-a + pesables (§1) + despiece (§2). El despiece vive en Stock, que está en el plan. Rubro `carniceria` al CHECK de `tenants.rubro`. |
| Resto | ✔ | F12-a + perfil resto (§3). Es el MÁS naturalmente standalone: todo lo operativo ya vivía en tablas `pos_*` por mandato. Rubro `restaurante` al CHECK. |
| Supermercado | ✘ (comercial) | Multi-caja + compras/proveedores/reposición son el corazón del negocio → siempre suite. La arquitectura no lo bloquea; es política de venta. |

### 7.5 Onboarding y ARCA del tenant POS-only

- **Onboarding v1 asistido**: generalizar `tools/demo_setup_tenant.py` a
  `tools/setup_tenant.py --plan pos --rubro carniceria ...` (tenant + admin + arca_config
  simulado + PV + depósito + caja POS default, idempotente — la orquestación ya existe).
  El registro autoservicio (signup público) queda FUERA de F12: pieza propia, gated por
  demanda real.
- **ARCA**: el tenant POS-only necesita exactamente lo mismo que cualquiera
  (`arca_config` por tenant; modo simulado hasta la homologación de fin de proyecto).
  Kiosco monotributista → factura C; la matriz de letras ya lo resuelve.

### 7.6 §6-bis — Orden de ejecución vigente (F12 en sub-fases)

| Sub-fase | Contenido | Entrega vendible |
|---|---|---|
| **F12-a** | Plan por tenant (§7.2) + `setup_tenant.py` + rubros `carniceria`/`restaurante` en el CHECK + plan visible en Configuración | **Licencia POS kiosco/almacén** (el POS F6 ya alcanza) |
| **F12-b** | Pesables por balanza + envases retornables + venta por depto. (§1) | Perfil súper completo (suite) y base de carnicería |
| **F12-c** | Despiece / transformación de stock (§2) | **Licencia POS carnicería** |
| **F12-d** | POS Resto: salones/mesas/mozos/comandas (§3) | **Licencia POS resto** — el más grande, validar con piloto |
