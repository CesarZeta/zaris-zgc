# ZGC — Manual del Punto de Venta (POS Mostrador)

> Corresponde al POS de la Fase 6, en producción desde 2026-07-05. Audiencia: quien
> instala y configura ZGC para un comercio (hoy César; mañana el onboarding de pilotos)
> y quien opera la caja. Escrito el 2026-07-05, verificado contra el código real.

## 1. Qué es (y qué no es)

- El POS de ZGC es una **pantalla web** de venta rápida que vive dentro de la misma
  app (ruta `/pos`), a pantalla completa, pensada para teclado y lector de código de
  barras.
- **No hay nada que instalar en la caja**: cualquier PC con navegador moderno
  (Chrome/Edge) alcanza. No hay ejecutable, ni base de datos local, ni servicio de
  Windows — a diferencia del legacy.
- Cada venta del POS **es una factura fiscal real** (A/B/C según el cliente), emitida
  por el mismo circuito que el módulo Ventas: numeración por punto de venta, CAE
  (real o simulado según la configuración ARCA), descarga de stock, cuenta corriente
  y medios de pago para el arqueo. No existe un "ticket no fiscal".
- **Requiere internet**: el POS habla con el backend en la nube. El modo offline
  (nodo de sucursal en la LAN, CLAUDE.md §3) es diseño de arquitectura, AÚN sin
  código — si se corta internet, hoy la caja no puede facturar.

## 2. Acceso y usuarios — no hay login separado

El POS **usa la misma sesión que la gestión**. No existe un "login de caja" ni un PIN
de cajero: **el cajero es el usuario logueado**.

1. Entrar a la app (`https://cesarzeta.github.io/zaris-zgc/`) y loguearse con el
   usuario del cajero.
2. Click en **"Punto de Venta"** en la barra lateral (o ir directo a `/pos`).
3. La pantalla sale del shell de gestión y queda a pantalla completa de caja.
   Se vuelve a la gestión con "← Volver a la gestión".

Implicancias prácticas:

- **Cada cajero necesita su propio usuario** (email + contraseña). Hoy los usuarios
  se crean por script — no hay ABM en la UI; llega con la Fase 6.5 (roles y permisos).
- El `nivel_acceso` del usuario importa: **1 = admin, 2 = supervisor**, 3+ = operador.
  Anular tickets y cerrar turnos ajenos exige nivel ≤ 2.
- Un usuario puede tener **una sola sesión de caja abierta** a la vez, y una caja
  puede estar abierta por un solo cajero a la vez.

## 3. Configuración inicial (una vez por comercio)

Checklist en orden — sin cualquiera de estos, el POS no vende (los errores típicos
están en §7):

| # | Qué | Dónde |
|---|---|---|
| 1 | Empresa (tenant) con CUIT y condición IVA — define las letras que emite (RI → A/B; monotributo → C) | alta por script / onboarding asistido |
| 2 | Usuario para cada cajero, y al menos uno con nivel ≤ 2 para autorizar anulaciones | script (la UI llega con la Fase 6.5) |
| 3 | **Configuración ARCA**: modo `simulado` para operar de prueba (CAE simulado, tickets marcados PRUEBA) o certificados reales para facturar en serio | Configuración → ARCA |
| 4 | **Punto de venta** electrónico (el número que sale en el ticket: `0001-...`) | Configuración → Puntos de venta |
| 5 | **Depósito activo** — la venta descarga stock; sin depósito activo la emisión corta con error 422 | módulo Stock / setup inicial |
| 6 | **Caja POS**: nombre, punto de venta que factura (obligatorio), depósito del que descarga, lista de precios (1–4) y ancho de ticket (58/80 mm) | Configuración → Cajas POS |
| 7 | Artículos con precio cargado en la lista que usa la caja (los precios de lista son **finales, IVA incluido**) y, si hay artículos en dólares, cotización del día | módulo Artículos |

Para un entorno demo/desarrollo, `tools/demo_setup_tenant.py` crea los pasos 1–5 de
una sola vez (tenant + usuario + ARCA simulado + PV + depósito), idempotente. La caja
(paso 6) se crea desde la UI o por `POST /api/v1/pos/cajas`.

## 4. Hardware

| Dispositivo | Cómo se conecta | Notas |
|---|---|---|
| Lector de código de barras USB | Sin configuración: emula teclado | El input de escaneo del POS siempre tiene el foco; el lector "tipea" el código y su Enter final agrega la línea |
| Impresora térmica 58/80 mm | Como impresora normal de Windows | El ticket sale por el **diálogo de impresión del navegador**. Configurar la térmica como predeterminada y ajustar márgenes en el driver. La impresión silenciosa (QZ Tray) está evaluada y diferida. La impresión térmica física real aún no se probó — verificar con la impresora del primer piloto |
| Balanza etiquetadora | **Todavía no soportada** | Las etiquetas EAN con peso embebido (prefijos 20–29) son del perfil POS Súper (post-MVP, ver `DISENO-POS-PERFILES.md`). Hoy un pesable se vende tipeando el peso (la cantidad acepta decimales) |
| Cajón de dinero / display de cliente | No soportados | Suelen colgar de la impresora (RJ11); se resolverá junto con QZ Tray |

## 5. Operación de un turno

### 5.1 Abrir la caja

Al entrar a `/pos` sin turno abierto: se elige una caja libre de la grilla (las
ocupadas aparecen deshabilitadas con "en uso"), se carga el **fondo inicial** (el
efectivo con el que arranca el cajón) y "Abrir caja". Si el cajero ya tenía un turno
abierto, entra directo a la pantalla de venta.

### 5.2 Vender

- **Escanear** (o tipear código interno / EAN / texto) + Enter: agrega la línea con
  el precio de la lista de la caja. **El precio lo fija el servidor** — el cajero no
  puede cambiarlo ni elegir la letra del comprobante.
- **Multiplicador**: `3*` y escanear (o `3*código`) = 3 unidades.
- **Pesables**: la cantidad de la línea acepta decimales (paso 0,001) — se tipea el peso.
- Artículo con **variantes** (talle/color/gusto): se abre el selector; escanear el
  EAN propio de la variante la resuelve directo.
- ↑/↓ seleccionan línea, **Supr** la quita, la cantidad se edita inline.
- **F3 — identificar cliente**: opcional para consumidor final; **obligatorio** si el
  monto supera el umbral de identificación (RG 5700, el backend lo exige) o si se
  quiere factura A (cliente RI con CUIT). La letra la decide el sistema por la matriz
  fiscal emisor × receptor.

### 5.3 Cobrar (F10)

1. El servidor recalcula el **total fiscal exacto** (puede diferir centavos del
   estimado en pantalla, por redondeo por alícuota de IVA).
2. Se cargan los **medios de pago**: efectivo, transferencia, cheque, tarjeta,
   Mercado Pago, otro — combinables; cada uno con referencia opcional (nº de cupón).
   La suma debe calzar exacto con el total ("faltan/sobran $X" guía en vivo).
3. Con efectivo: se tipea lo recibido y muestra el **vuelto**.
4. Enter confirma → se emite la factura (con CAE) → sale el ticket. Si la impresión
   falla, **la venta ya está emitida**: reimprimir desde F6.

### 5.4 Anular un ticket (requiere supervisor)

F6 → elegir el ticket → "Anular" → un usuario con **nivel ≤ 2** ingresa su email +
contraseña + el motivo. Se emite en el acto la **nota de crédito espejo** (fiscal),
el stock vuelve y la anulación aparece en negativo en el arqueo del turno. No existe
"borrar venta": lo emitido es inmutable y solo se revierte con NC — igual que en la
gestión.

### 5.5 Cerrar el turno (F8)

Muestra el resumen del turno: tickets, ventas por medio de pago y **efectivo teórico**
(fondo inicial + efectivo neto). Se cuenta el cajón, se carga el **arqueo** y el
sistema sella la **diferencia** (contado − teórico) junto con los totales. "Terminar
turno" libera la caja. Los turnos cerrados alimentan la planilla de caja del día
(módulo Caja).

## 6. Atajos de teclado

| Tecla | Acción |
|---|---|
| Enter | Agregar el código escaneado/tipeado |
| `N*` | Multiplicador para el próximo escaneo |
| F3 | Identificar cliente |
| F6 | Tickets del turno (reimpresión / anulación) |
| F8 | Cierre de turno |
| F9 | Venta por departamento (importe tipeado) |
| F10 | Cobrar |
| ↑ ↓ / Supr | Seleccionar / quitar línea |
| Esc | Cerrar el modal abierto |

## 6-bis. Perfil súper: balanza, envases y departamentos (F12-b)

- **Etiquetas de balanza**: se configuran una vez en Configuración → Etiquetas de
  balanza (prefijo 20–29, si el código embebe peso en gramos o importe en centavos,
  y cuántos dígitos tiene el PLU). Cada artículo pesable lleva su **código de
  balanza (PLU)** en el maestro. Al escanear la etiqueta EAN-13, el POS arma la
  línea solo: artículo + cantidad (kg) o cantidad = importe/precio. El PLU tipeado
  a mano también funciona como código exacto.
- **Envases retornables**: si el artículo tiene un envase asociado (maestro de
  artículos → "Envase retornable asociado"), el POS agrega la línea del envase
  junto con el producto (misma cantidad, editable). La *devolución* de envases
  queda para definir con el primer piloto.
- **Venta por departamento** (F9): para lo no codificado. Se marcan artículos con
  "Venta por departamento" (uno por rubro de mostrador, ej. VARIOS 21%); en la
  caja, F9 → elegir departamento → tipear el importe final. Es el ÚNICO caso en
  que el cajero tipea un precio.

## 6-ter. POS Resto (F12-d)

Una caja con **perfil resto** (Configuración → Cajas POS) abre la pantalla de
salón en vez del mostrador:

1. **Configurar el salón** (una vez): Configuración → Salones y mesas — crear
   salones (Salón, Vereda, Barra…) y agregar mesas por lote (numeración automática).
2. **Operar**: la grilla muestra las mesas por salón (libre / ocupada con total y
   mozo). Tocar una mesa libre abre la comanda; los platos se buscan como en el
   mostrador y admiten observaciones ("sin sal"). **Enviar a cocina** imprime la
   comanda con los ítems nuevos. Mover/unir mesas desde el panel de la comanda.
3. **Pedidos** (pestaña): delivery y para llevar, con domicilio normalizado (OSM)
   y estados en preparación → despachado → entregado.
4. **Cobrar**: cierra la mesa con la pantalla de cobro de siempre (medios múltiples,
   vuelto) y emite la factura fiscal. La **propina %** es informativa (no integra la
   factura ni el arqueo). La pestaña **Mozos** muestra ventas y propinas por mozo.
5. Nada del salón (mesas, comandas, cocina) viaja a la gestión central: solo la
   venta final emitida.

## 7. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| "No hay cajas configuradas" | Falta el paso 6 del checklist | Configuración → Cajas POS |
| La caja aparece "en uso" | Otro cajero tiene turno abierto en esa caja | Que lo cierre él, o lo cierra un usuario nivel ≤ 2 |
| Error al cobrar por depósito | No hay depósito activo (paso 5) | Activar/crear un depósito |
| "Recalculá la venta" al cobrar | El total cambió entre el cálculo y la confirmación | Reabrir el cobro (recalcula solo) |
| Pide identificar al cliente | Venta a CF por encima del umbral RG 5700 | F3 e identificar con DNI/CUIT |
| Credencial de supervisor rechazada | Usuario sin nivel ≤ 2, inactivo o de otra empresa | Verificar el usuario autorizante |
| El ticket no salió impreso | Diálogo de impresión cancelado / impresora | F6 → reimprimir (la venta está emitida igual) |
| "Sesión vencida" en medio del turno | JWT vencido | Re-loguearse: el turno abierto se retoma solo |
| Se deslogueó la caja al anular | NO debe pasar (el backend responde 403, nunca 401, justamente para esto) | Reportarlo como bug |

## 8. Limitaciones actuales y qué viene

- **Sin internet no se factura** (el nodo de sucursal LAN es diseño, sin código — ROADMAP F13).
- Impresión con diálogo del navegador (QZ Tray diferido hasta que un piloto lo pida).
- Descuentos por línea/venta: el backend ya los soporta (`descuento_pct`), el POS aún
  no los expone en pantalla.
- Devolución de envases retornables (línea negativa o descuento): a definir con el
  primer piloto contra la práctica real.
- Resto v2 (diferidos documentados): recetas/descarga de insumos, modificadores con
  precio, KDS, reservas, división de cuenta por ítem, integración pedidos online (F13).

## 9. Apéndice técnico (desarrollo / troubleshooting)

- Frontend: `web-app/src/modules/pos/POSPage.tsx` (una página con las 7 vistas/modales),
  ticket en `web-app/src/modules/pos/ticket.ts`, cajas en `pos/CajasSection.tsx`
  (montado en Configuración). Ruta `/pos` fuera del AppShell.
- Backend: `backend/app/api/v1/pos.py`, prefijo `/api/v1/pos`. Endpoints clave:
  `GET /pos/cajas`, `POST /pos/sesiones`, `GET /pos/sesiones/actual`, `GET /pos/buscar`,
  `POST /pos/ventas/calcular` (dry-run), `POST /pos/ventas`, `POST /pos/ventas/{id}/anular`,
  `POST /pos/sesiones/{id}/cerrar`.
- Tablas (migración `sql/009_pos_mostrador.sql`): `pos_cajas`, `pos_sesiones`
  (índice único parcial: una sesión abierta por caja), `venta_medios`,
  `comprobantes.pos_sesion_id`.
- La venta POS llama a `emitir_core` (`api/v1/comprobantes.py`) en **una** transacción:
  factura + CAE + stock + medios + sesión, todo o nada.
- La autorización de supervisor responde **403** (nunca 401: un 401 dispara el
  "sesión vencida" global del frontend y desloguearía la caja — lección de Fase 6).
- Setup mínimo por script: `tools/demo_setup_tenant.py` (idempotente).
