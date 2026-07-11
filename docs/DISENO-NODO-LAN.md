# ZGC — Diseño: Nodo LAN de sucursal y POS autónomo (F13-LAN)

> Estado: **DISEÑO para revisión de César** (2026-07-11). Nada de esto está
> implementado. Origen: mandato de César del 2026-07-11 (sesión post-F12) que baja a
> tierra la arquitectura híbrida declarada el día 1 (CLAUDE.md §3, decisión
> "online y red LAN" del 2026-07-03).

## 0. Mandatos de César (2026-07-11)

1. La suite debe poder **conectar puestos en red** y **asignarles los puntos de
   venta**.
2. El POS debe tener un **endpoint propio, diferenciado del login de la suite**.
3. El puesto/nodo debe tener **autonomía de gestión**: trabajar de manera
   independiente (stock, inventario, ventas) aunque no haya conexión.
4. Al reconectar, **integra todo** (stock, inventario, ventas, demás) **con el resto
   de la gestión**, como si fuera un punto de venta más.
5. El esquema debe ser **replicable a N puntos de venta**.

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
- **Superficie del nodo recortada**: el perfil `nodo` monta SOLO los routers que el
  POS necesita (`pos`, `pos_resto`, `articulos`/`stock` en modo consulta+ajuste,
  `clientes` para identificar receptor, `auth` del POS). La gestión completa
  (compras, bancos, contabilidad…) NO se sirve desde el nodo en v1 — se usa online
  contra la nube, como hoy. Esto implementa la "autonomía de gestión" mínima del
  mandato 3 (stock e inventario locales) sin duplicar la suite entera.
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
| **N1 — Nodo mínimo** | Perfil `nodo` del backend, instalador Windows, aparejamiento (`sucursal_nodos` + token), réplica de bajada de maestros, POS servido por el nodo con `POST /pos/auth/login` | Una caja de la LAN vende contra el nodo con precios/artículos replicados (aunque la venta aún no suba sola) |
| **N2 — Sincronización completa** | Cola `sync_eventos` idempotente de subida, CAE diferido al reconectar, monitoreo del nodo en Configuración (last_seen, atraso de cola) | Corte de internet de horas: la sucursal vende, stock y ventas convergen al reconectar, CAE otorgado retroactivo |
| **N3 — Robustez y extras** | Gestión local ampliada (consultas de cta. cte. offline), CAEA evaluado, resto/carnicería offline completos, updates automáticos del nodo | Piloto multi-caja real corriendo semanas sin intervención |

El login POS dedicado (`/pos/auth/login` + scope) puede adelantarse como pieza
suelta en la nube (sirve a TODOS los tenants, con o sin nodo) — es el paso barato
que ya cumple el mandato 2.

## 8. Preguntas abiertas para César

1. **¿Gestión local completa en el nodo?** v1 propone solo POS + stock/inventario
   local (mandato 3 mínimo); la gestión entera (compras, bancos…) sigue online.
   ¿Alcanza, o la sucursal necesita cargar compras sin internet?
2. **Hardware de referencia del nodo**: ¿PC Windows dedicada existente en los
   clientes tipo (como el server del legacy)? Define el instalador de N1.
3. **¿Adelantamos el login POS dedicado** (pieza de nube, barata) antes de encarar
   el nodo entero?
4. **Prioridad vs. F12-bis Logística**: el nodo es esfuerzo ALTO (varias sesiones).
   ¿Va antes, después, o en paralelo con pilotos?

## 9. Qué NO cambia

- Los tenants 100% online siguen exactamente igual (el nodo es opt-in por sucursal).
- Ningún modelo de datos existente se modifica: se AGREGAN `sucursal_nodos` y
  `sync_eventos` (+ `scope` en el JWT). Contrato de contabilizabilidad intacto:
  los documentos que suben del nodo son los mismos documentos inmutables de siempre.
- El plan por tenant (F12-a) y las licencias POS standalone no se tocan.
