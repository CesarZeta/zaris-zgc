# ZGC — Diseño: Nodo LAN de sucursal y POS autónomo (F13-LAN)

> Estado: **N1 IMPLEMENTADA Y EN PRODUCCIÓN (2026-07-12)** — aparejamiento,
> réplica de bajada, perfil `nodo`, PV exclusivos e instalador Windows (suite
> `tools/test_nodo_dev.py`, 52/52; manual operativo en `MANUAL-NODO.md`).
> N2 (subida + CAE diferido) y N3 (robustez) pendientes. Origen: mandato de
> César del 2026-07-11 (sesión post-F12) que baja a tierra la arquitectura
> híbrida declarada el día 1 (CLAUDE.md §3, decisión "online y red LAN" del
> 2026-07-03).

## 0. Mandatos de César (2026-07-11)

1. La suite debe poder **conectar puestos en red** y **asignarles los puntos de
   venta**.
2. El POS debe tener un **endpoint propio, diferenciado del login de la suite**.
3. El puesto/nodo debe tener **autonomía de gestión**: trabajar de manera
   independiente (stock, inventario, ventas) aunque no haya conexión.
4. Al reconectar, **integra todo** (stock, inventario, ventas, demás) **con el resto
   de la gestión**, como si fuera un punto de venta más.
5. El esquema debe ser **replicable a N puntos de venta**.

### 0-bis. Definiciones de César (2026-07-11, segunda ronda — responden §8)

- **El nodo lleva TAMBIÉN la facturación de gestión** ("facturación propiamente
  dicha", el módulo Ventas — presupuestos/facturas/NC/ND), con un **punto de
  venta PROPIO del nodo/sucursal**, distinto de los PV de las cajas POS. Cada
  canal factura con SU punto de venta y opera su stock/inventario: la
  suite/nodo con el suyo, cada caja POS con el suyo.
- **La gestión local completa** (compras, bancos, contabilidad… en el nodo) es
  un **extra deseable, no requisito** → queda para N3.
- Los puntos de venta (los POS) son módulos que pueden ser **independientes o
  conectarse a la suite** — coherente con el plan `pos` de F12-a (packaging) y
  con este nodo (offline): son las dos caras de la misma independencia.
- **Login POS dedicado: ADELANTADO** — implementado en la nube el 2026-07-11
  (mismo día): `POST /pos/auth/login` emite JWT con `scope: "pos"`; las guardas
  acotan la sesión de caja al módulo `pos` completo + solo-lectura de
  `ventas`/`clientes` (impresión de tickets, identificar receptor, OSM del
  delivery), 403 en todo lo demás (nunca 401). Front: página `/pos/login`
  («Punto de Venta»), la gestión rebota a `/pos` para sesiones de caja, y
  «Salir de la caja» desloguea al login del POS. El token de la suite sigue
  operando el POS como siempre. Suite `tools/test_pos_login_dev.py` (23).

## 1. Qué es y qué no es

- **ES** la implementación del "nodo de sucursal" de CLAUDE.md §3: una PC de la
  sucursal corre el backend + una base local; las cajas de la LAN le pegan al nodo
  por red local y el nodo sincroniza con la nube.
- **NO ES** el plan `pos` de F12-a (DISENO-POS-PERFILES.md §7): aquel es packaging
  comercial de tenants 100% online, "sin instalación on-premise". Son ortogonales:
  un tenant plan `pos` puede operar con o sin nodo, y un tenant suite también.
- **NO bifurca nada**: el nodo corre el MISMO backend FastAPI del repo (regla
  §1-ter: presets, nunca fork), con un **perfil de ejecución `nodo`** que cambia
  config, no código.

## 2. Topología y componentes

```
            NUBE (autoridad de maestros)
   FastAPI Vercel + Supabase ── gestión multi-sucursal
                 ▲
                 │ /sync (HTTPS, token de nodo)
                 ▼
   NODO SUCURSAL (PC Windows en la LAN)
   mismo backend FastAPI (perfil nodo) + PostgreSQL local
   sirve además el build estático del POS web
     ▲          ▲          ▲   (LAN, http://nodo:8021)
   CAJA 1     CAJA 2     CAJA N   (navegador → POS)
```

- **El nodo es autoridad de sus transacciones** (ventas, movimientos de stock de su
  depósito, sesiones/arqueos, comandas resto); **la nube es autoridad de los
  maestros** (artículos, precios, clientes, usuarios/roles, config de cajas/PV).
  Misma regla del día 1: "la nube manda" para maestros, "el origen manda" para
  transacciones.
- Stack del nodo: Python + PostgreSQL locales, empaquetados en un **instalador
  Windows** (la realidad del cliente: una PC en la sucursal). El detalle del
  empaquetado (servicio de Windows, updates) es parte de N1.
- El POS web es el MISMO build de React: `VITE_API_URL` apunta al nodo en vez de a
  Vercel. Cero fork de frontend.

## 3. Identidad del nodo: registro y aparejamiento (mandato 1)

- Tabla nueva **`sucursal_nodos`** (nube): `id` UUID, `tenant_id`, `sucursal_id`,
  `nombre`, `token_hash` (bcrypt del token de aparejamiento), `estado`
  (pendiente/activo/revocado), `last_seen_at`, `last_sync_at`, `version_app`. RLS.
- Alta en Configuración → Sucursales: "Agregar nodo" genera un **token de
  aparejamiento que se muestra UNA vez** (patrón reset-password de F6.5). En la
  instalación del nodo se pega el token; el nodo queda apareado a ESA sucursal.
- **Asignación de puntos de venta**: ya existe en el modelo — cada caja POS
  (`pos_cajas`) tiene su PV que factura y su sucursal (F6 + F12-d). El nodo sirve
  las cajas de SU sucursal; los PV de esas cajas pasan a ser **exclusivos del nodo**
  mientras esté activo (la nube no emite con esos PV — evita colisiones de
  numeración). La UI de cajas muestra a qué nodo queda asignada cada caja.
- Revocar el nodo desde la nube lo saca de línea (deja de sincronizar) sin tocar
  sus datos locales.

## 4. Endpoint propio del POS (mandato 2)

- **Login de caja dedicado: `POST /pos/auth/login`** — separado del `POST
  /auth/login` de la suite. Valida usuario+clave del MISMO esquema de usuarios
  (BUE de seguridad única, F6.5), pero:
  - exige permiso del módulo `pos` (403 si el rol no lo tiene),
  - pide además la **caja** en la que se abre sesión,
  - emite un JWT con `scope: pos` que las guardas de la suite rechazan (un token
    de caja no sirve para la gestión, y viceversa el de la suite sigue operando
    el POS online como hoy — compat).
- **Superficie del nodo (v1, ajustada por §0-bis)**: el perfil `nodo` monta los
  routers del POS (`pos`, `pos_resto`, `auth` del POS) **más la facturación de
  gestión** (`ventas`/comprobantes/cobranzas con el PV propio del nodo),
  `articulos`/`stock` (consulta + ajustes locales) y `clientes`. La gestión
  completa (compras, bancos, contabilidad…) NO se sirve desde el nodo en v1 —
  es el extra de N3; mientras tanto se usa online contra la nube, como hoy.
- En la nube, `POST /pos/auth/login` también existe (mismo código): un tenant sin
  nodo gana igual la pantalla de entrada propia del POS.

## 5. Sincronización (mandatos 3, 4 y 5)

Los cimientos del día 1 ya están puestos: **UUIDs generados donde nace el dato**,
todo sellado con `tenant_id`, las ventas POS con su sesión/caja, kardex con
`grupo_id`. Lo nuevo:

- **Bajada (nube → nodo), "la nube manda"**: réplica de maestros por *checkpoint
  incremental* (`updated_at` > último sync, por tabla): artículos+variantes+precios,
  clientes, usuarios/roles/permisos, config de cajas/PV/balanza, salones/mesas.
  Borrado lógico viaja como update (`activo=false`) — los maestros del proyecto ya
  se inactivan, no se borran.
- **Subida (nodo → nube), "el origen manda"**: cola de **eventos inmutables e
  idempotentes** (`sync_eventos`: id UUID, tipo, payload JSONB, creado_at,
  enviado_at). La nube aplica cada evento en su transacción con la MISMA maquinaria
  de la suite (`emitir_core` etc. — regla §6 "reusar el núcleo") y responde ACK por
  id; re-enviar un evento ya aplicado es un no-op (idempotencia por UUID). Suben:
  ventas POS (con medios y sesión), movimientos de stock locales (ajustes,
  transformaciones), sesiones/arqueos, comandas cerradas (resto).
- **Conflictos**: maestros no se editan en el nodo (readonly local, se editan en la
  gestión de la nube) → no hay conflicto de maestros en v1. Transacciones son
  inserciones inmutables con UUID → no hay conflicto posible, solo duplicado
  idempotente. El stock del depósito de la sucursal converge por reaplicación de
  movimientos (el saldo de la nube se recalcula del kardex, nunca se pisa a mano).
- **Transporte**: HTTP polling del nodo hacia la nube (pull de maestros + push de
  eventos) cada N segundos con backoff. Sin websockets ni infraestructura nueva:
  compatible con Vercel serverless y con el free tier.

## 6. Facturación offline (CAE diferido)

- Sin internet, la caja emite igual: el comprobante nace **fiscal con numeración
  del PV local** (el PV es exclusivo del nodo → la secuencia es correcta por
  construcción) y queda `cae_pendiente`. El ticket imprime la leyenda
  "Comprobante pendiente de autorización" y SIN QR (el QR exige CAE real —
  criterio F3/F6).
- Al reconectar, el nodo (o la nube al recibir el evento) pide el CAE por WSFEv1
  en orden de numeración; `FECompConsultar` ante timeout (ya implementado, F3).
  ARCA autoriza comprobantes ya numerados mientras la secuencia del PV sea
  consecutiva — exactamente el hueco que el PV-exclusivo-del-nodo garantiza.
- **CAEA** (anticipo quincenal) queda como evaluación de N3: más prolijo
  normativamente para cortes largos, pero agrega ciclo de rendición. Para cortes
  de horas, CAE diferido alcanza (mismo criterio del legacy, que facturaba offline
  y despachaba después).
- En modo `simulado` (dev/demo y tenants sin cert) todo esto es transparente.

## 7. Sub-fases propuestas

| Sub-fase | Contenido | Criterio de listo |
|---|---|---|
| **N1 — Nodo mínimo** | Perfil `nodo` del backend, instalador Windows, aparejamiento (`sucursal_nodos` + token), réplica de bajada de maestros, POS servido por el nodo (el login POS ya existe) + **facturación de gestión con el PV propio del nodo** (§0-bis) | Una caja de la LAN vende contra el nodo con precios/artículos replicados, y el nodo factura desde Ventas con su PV (aunque nada suba solo todavía) |
| **N2 — Sincronización completa** | Cola `sync_eventos` idempotente de subida, CAE diferido al reconectar, monitoreo del nodo en Configuración (last_seen, atraso de cola) | Corte de internet de horas: la sucursal vende, stock y ventas convergen al reconectar, CAE otorgado retroactivo |
| **N3 — Robustez y extras** | **Gestión local ampliada (el "extra" de §0-bis: compras, cta. cte. offline…)**, CAEA evaluado, resto/carnicería offline completos, updates automáticos del nodo | Piloto multi-caja real corriendo semanas sin intervención |

~~El login POS dedicado puede adelantarse como pieza suelta en la nube~~ →
**HECHO 2026-07-11** (ver §0-bis): `/pos/auth/login` + scope ya sirve a todos los
tenants, con o sin nodo, y es el MISMO código que servirá el nodo.

## 8. Preguntas abiertas para César

1. ~~¿Gestión local completa en el nodo?~~ → **RESPONDIDA 2026-07-11** (§0-bis):
   el nodo lleva POS + **facturación de gestión con PV propio** + stock/clientes;
   la gestión completa es un extra (N3).
2. ~~Hardware de referencia del nodo~~ → **RESPONDIDA 2026-07-12**: PC Windows
   dedicada existente en el cliente (como el server del legacy); el instalador
   de N1 (`tools/nodo/instalar_nodo.ps1`) apunta a Windows.
3. ~~¿Adelantamos el login POS dedicado?~~ → **HECHA 2026-07-11** (§0-bis).
4. ~~Prioridad vs. F12-bis Logística~~ → **RESUELTA 2026-07-12**: César ordenó
   avanzar («adelante») tras el rediseño UX del POS; N1 se construyó primero.
   La prioridad de N2 vs. F12-bis queda para la próxima decisión.

## 9. Qué NO cambia

- Los tenants 100% online siguen exactamente igual (el nodo es opt-in por sucursal).
- Ningún modelo de datos existente se modifica: se AGREGAN `sucursal_nodos` y
  `sync_eventos` (+ `scope` en el JWT). Contrato de contabilizabilidad intacto:
  los documentos que suben del nodo son los mismos documentos inmutables de siempre.
- El plan por tenant (F12-a) y las licencias POS standalone no se tocan.
