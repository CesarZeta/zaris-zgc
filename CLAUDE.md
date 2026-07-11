# ZGC — ZARIS Gestión Comercial

> **⚠️ REGLA RECTORA #0 — NUNCA ASUMIR, VERIFICAR SIEMPRE:** antes de afirmar, opinar o recomendar cualquier cosa sobre el código, la DB, la infra o el estado del proyecto, **verificarlo contra la realidad** (DB con `execute_sql`, código con `Read`/`Grep`, runtime con `curl`/browser, historia con `git log`). No deducir de esta doc ni de la memoria. Misma regla rectora que ZGE, declarada permanente por Cesar el 2026-05-23.

## 1. Qué es ZGC

Web app de **gestión comercial, contable y de stock** que administra puntos de venta de manera centralizada: ventas, compras, IVA, bancos, cheques, depósitos, cajas chicas, cuentas corrientes, comisiones, facturación electrónica ARCA/AFIP.

Es la reescritura moderna del software legacy **RevoSolution Gestión Comercial** (escritorio, FoxPro/xBase, Argentina). Todo el material del legacy está en `Revosolution Software/`:

- **No hay código fuente** del legacy — solo ejecutables, backups y drivers.
- Los activos reutilizables son las **tablas DBF** (306 tablas únicas: modelo de datos completo, y datos reales de clientes migrables) y los **manuales PDF** (el de V16, 118 páginas, es la especificación funcional de referencia).
- **El esquema completo del legacy ya está extraído**: `docs/legacy/esquema-dbf.md` (navegable) y `docs/legacy/esquema-dbf.json` (machine-readable, para scripts de migración). Se regenera con `python tools/extraer_esquema_dbf.py`. Consultarlo SIEMPRE antes de diseñar una tabla nueva en PostgreSQL.

### Módulos funcionales (heredados del legacy, alcance de referencia)

1. Configuración (empresa, condición IVA → facturas A/B/C, puntos de venta, numeración, usuarios y permisos por módulo, condiciones de venta, transportistas, retenciones, tarjetas, depósitos)
2. Artículos y Stock (familias/subfamilias, 4 listas de precios, cambios masivos, kardex, etiquetas código de barras, valorización, ajustes, interdepósitos, comparativo por proveedor, import Excel)
3. Proveedores / Compras (remitos, facturas/NC/ND, órdenes de pago, cta. cte., vencimientos)
4. Clientes / Ventas (presupuestos, remitos, facturación, cobranzas, cta. cte., morosidad)
5. Vendedores / Comisiones (por venta o por cobranza)
6. Cheques
7. Libros de IVA (ventas/compras, retenciones, CITI)
8. Caja y Bancos (planilla de caja diaria, movimientos, conciliación)
9. POS (supermercado/mostrador: código de barras, pesables con etiqueta de balanza, envases retornables, venta por departamento, autorización de supervisor para anulaciones)

> **Definición de producto**: el alcance del MVP, mercado objetivo, modelo SaaS multi-tenant y roadmap de diferenciales están en `docs/DEFINICION-PRODUCTO.md` (discovery del 2026-07-03). El plan de ejecución está en `docs/ROADMAP.md`. Leerlos antes de decidir alcances.

## 1-ter. Multipropósito por rubro — regla de producto (César, 2026-07-04)

ZGC no es solo para supermercados: la **gestión central es una sola y general**, con
customización por **rubro del tenant** (supermercado, indumentaria/calzado, electrónica,
ferretería/repuestos, distribuidora, general); los **POS sí son full orientados** al rubro.
El habilitador es el modelo de **variantes** de artículos (talle, color, gusto, capacidad —
con EAN y stock propios por combinación). El rubro cambia presets/UI, **nunca bifurca el
modelo de datos**. Ver `docs/DISENO-RUBROS-Y-VARIANTES.md` antes de tocar el maestro de
artículos, ventas o POS.

Mandato 2026-07-05: los POS tienen **tres configuraciones** — estándar/súper (pesables),
carnicería (despiece de media res EN GESTIÓN + POS pesable) y resto (mesas/comandas que
NUNCA se trasladan a la gestión) — y cada caja pertenece a una **sucursal**. Diseño en
`docs/DISENO-POS-PERFILES.md`. Domicilios normalizados OSM (estándar ZGE) y módulo de
logística: `docs/DISENO-LOGISTICA-Y-DOMICILIOS.md`. Manual del POS actual (instalación,
configuración, operación): `docs/MANUAL-POS.md`.

## 1-bis. Base Única de Entidades (BUE) — regla de arquitectura

**"El cliente es el núcleo del sistema"** (César, 2026-07-03). Toda persona física o jurídica existe **una sola vez** en `entidades` (datos maestros: nombre/razón social, CUIT/DNI, condición IVA, domicilios, contactos). Los roles comerciales (`clientes`, `proveedores`, `vendedores`, `transportistas`) son tablas satélite que referencian `id_entidad` y solo agregan lo específico del rol. **Prohibido** duplicar datos maestros de personas en tablas de rol. Análogo a la BUC de ZGE (§2 de su CLAUDE.md). Todo registro lleva `tenant_id`; RLS de Supabase como segunda línea de defensa.

## 2. Stack Tecnológico (decidido 2026-07-03)

Mismo stack que ZGE, para reusar patrones, auth y experiencia:

| Capa | Tecnología |
|---|---|
| Backend | **FastAPI** (Python 3.10+), SQLAlchemy async + asyncpg |
| DB | **PostgreSQL** — Supabase en prod (cuenta nueva, sa-east-1), Postgres local en dev |
| Frontend | **React (Vite)** |
| Hosting | Backend en **Vercel serverless región gru1/São Paulo** (decisión 2026-07-04: Railway no tiene región SP; pooler transaccional :6543 de Supabase), frontend en **GitHub Pages**, DB **Supabase** |
| Facturación electrónica | **Cliente propio WSAA + WSFEv1** (`backend/app/services/arca/`: firma CMS con `cryptography` + SOAP con `httpx`) — decidido 2026-07-04: pyafipws arrastra deps incompatibles con Vercel serverless y queda como implementación de referencia. Diseño de cumplimiento en `docs/FACTURACION-ARCA.md` — **leerlo antes de tocar cualquier cosa de comprobantes** |
| Auth | JWT como ZGE (`POST /auth/login`, bcrypt directo — **no passlib**) |

Consultar el `CLAUDE.md` de ZGE (`C:\Users\Cesar\Documents\ZARIS\Desarrollo\ZGE\CLAUDE.md`) para los patrones ya resueltos (auth, roles, estructura de módulos React) antes de reinventar algo.

### Diseño visual (decidido 2026-07-04): «ZARIS Heredado»

César eligió (entre 3 mockups comparados) la identidad de suite con ZGE:
- **Paleta**: crema `#f2f1ed` de fondo, tinta `#26251e`, acento único naranja `#f54e00`, dorado `#c08532` secundario, éxito `#1f8a65`, error `#cf2d56`. Superficies `--surface-100..500` y bordes rgba de tinta como en ZGE.
- **Tipografía**: Space Grotesk (display/UI) + JetBrains Mono (códigos, CUIT, importes) — copiar fuentes y `tokens.css` desde `ZGE/web-app/src/styles/` y `assets/fonts/`.
- **Forma**: radios chicos (2-4px), bordes hairline, sombras suaves; sidebar tinta oscura con ítem activo naranja.
- Regla heredada de ZGE: **el naranja es del brand** — los estados usan otros colores (éxito verde, error rojo, advertencia amarillo lejos del naranja).
- Los estados de comprobantes/clientes se codifican con chips/pills; números siempre `tabular-nums`.

## 3. Arquitectura: nube + nodo de sucursal (decidido 2026-07-03: "online y red LAN")

El POS debe poder facturar **aunque se corte internet**, igual que el legacy. La arquitectura es híbrida:

```
                 ┌──────────────── NUBE ────────────────┐
                 │  Backend central (FastAPI/Railway)    │
                 │  PostgreSQL (Supabase)                │
                 │  Gestión centralizada multi-sucursal  │
                 └───────────────▲──────────────────────┘
                                 │ sincronización
        ┌────────────────────────┴───────────────────────┐
        │  NODO SUCURSAL (PC servidor local en la LAN)    │
        │  Mismo backend FastAPI + PostgreSQL local       │
        └───▲──────────────▲──────────────▲──────────────┘
            │ LAN          │ LAN          │ LAN
         CAJA 1         CAJA 2         CAJA 3   (navegador → POS web)
```

- Las **cajas** son clientes web (React) que hablan con el **nodo de sucursal** por LAN — no dependen de internet.
- El **nodo de sucursal** sincroniza con la nube: sube ventas/movimientos, baja artículos/precios/clientes (el mismo esquema conceptual "Actualizar POS" del legacy, pero automático y continuo).
- La **gestión** (backoffice) se usa online contra la nube; en la sucursal también puede usarse contra el nodo local.
- Implicancias de diseño desde el día 1: **IDs únicos globales** (UUID) generados donde nace el dato, cada registro sellado con `sucursal_id`/`origen`, colas de sincronización idempotentes, y resolución de conflictos "la nube manda" para maestros / "el origen manda" para transacciones.
- La facturación electrónica (CAE) requiere internet: el POS factura offline como comprobante pendiente y el nodo gestiona CAE al reconectar (CAEA como alternativa a evaluar), o usa controlador fiscal físico donde aplique.

## 4. Estructura del repo (prevista, espejo de ZGE)

```
ZGC/
├── backend/        # FastAPI
├── web-app/        # React (Vite) — gestión y POS
├── sql/            # migraciones
├── docs/           # documentación funcional y técnica
├── tools/          # scripts (extracción DBF, migración de datos, etc.)
└── Revosolution Software/   # legacy de referencia (NO tocar, solo lectura)
```

## 5. Contexto fiscal argentino (siempre presente)

- Tipos de comprobante A/B/C según condición IVA del emisor y receptor; CUIT con dígito verificador.
- IVA: tasas múltiples por artículo, precios con o sin IVA incluido según configuración.
- ARCA/AFIP: factura electrónica (CAE vía WSFEv1), libros de IVA digital, retenciones/percepciones, CITI.
- Monotributo vs. Responsable Inscripto.

## 6. Convenciones de API (lecciones permanentes)

- **401 es SOLO "no autenticado"** (JWT ausente/inválido): el interceptor global del
  frontend (`api.ts`) trata cualquier 401 como sesión vencida → desloguea y redirige a
  login. Toda validación de credenciales **embebidas en el body** de un request ya
  autenticado (p. ej. autorización de supervisor en el POS) responde **403** — un 401
  ahí desloguea la caja entera (bug real cazado en el E2E de Fase 6).
- **Reusar el núcleo, no copiarlo**: la emisión fiscal y la NC espejo viven en
  `emitir_core`/`crear_nc_espejo_core` (`api/v1/comprobantes.py`, sin commit adentro) —
  cualquier flujo nuevo que emita comprobantes (POS, futuras integraciones) los llama
  dentro de su propia transacción. No duplicar esa lógica. OJO scripts/tests: el
  endpoint `POST /{id}/nota-credito` devuelve la NC en **BORRADOR** — hay que emitirla
  aparte para que impacte (cta. cte., stock, comisiones; mordió en la suite F11).
- **Pruebas sobre agregados del día** (planilla, resúmenes): asertar **deltas**
  (después − antes), nunca absolutos — el día es compartido entre corridas y sesiones.
- **Números `Numeric` viajan como STRING en el JSON** de la API (SQLAlchemy los
  serializa así): al consumir la API desde un script, convertir con `float()` antes de
  comparar/operar (`precio_1 > 0` sobre un string revienta).
- **Backdating de comprobantes**: `fecha` es un campo opcional del body en ventas
  (`/ventas/comprobantes`) y compras (`/compras/comprobantes`); en modo ARCA `simulado`
  no hay validación de secuencia contra AFIP, así que se pueden generar comprobantes con
  fecha pasada por API **de forma segura** (el server mantiene numeración/stock/IVA/cta.cte).
  RESUELTO en la 014 (2026-07-10): si la fecha del documento ≠ hoy, `_mover_stock` sella
  `stock_movimientos.fecha` con la fecha del papel — ya NO hace falta el `UPDATE` post-
  generación por SQL. (Sigue sin haber FK kardex→documento; la referencia es el TEXTO
  `TIPO 0001-00000123` + `grupo_id` = id del documento.)
- **`X-Total-Count` cross-origin necesita `Access-Control-Expose-Headers`** — y el
  **proxy de Vite en dev lo enmascara** (same-origin: el CORS no aplica y todo "funciona").
  RESUELTO 2026-07-06 (LOTE TÉCNICO): `expose_headers=["X-Total-Count"]` en el
  CORSMiddleware es el fix canónico — NO volver a setear el header a mano por endpoint.
  Regla vigente: toda verificación de headers/CORS se hace contra prod o sin proxy, no en dev.
- **Todo endpoint nuevo nace con guarda RBAC** (Fase 6.5, 2026-07-05): usar
  `Depends(requiere("modulo", accion))` en lugar de `Depends(get_current_user)` —
  GET=`ver`, escritura=`editar`, anulación/borrado=`anular`; catálogos compartidos entre
  módulos con `requiere_alguno([...])`; la config sensible (ARCA, puntos de venta, cajas
  POS) exige `configuracion.editar` aunque el endpoint viva en otro router (es donde la
  UI la muestra). El catálogo de módulos vive en `app/core/permisos.py` y es ESPEJO del
  seed SQL de la migración 010 — cambiar uno exige cambiar el otro. `usuarios.rol_id
  NULL` = acceso total (compat scripts/seeds). La guarda responde 403, nunca 401.
  Al AGREGAR un módulo (F8 bancos, F9 contabilidad, F11 vendedores): las comprehensions
  de `ROLES_BASE` lo toman solas para tenants NUEVOS (iteran `MODULOS`); los existentes
  necesitan el `INSERT ... ON CONFLICT DO NOTHING` en la migración. Y las sesiones ya
  logueadas NO ven el ítem nuevo del nav hasta re-loguear (los `permisos` viajan en el
  login) — no es un bug del deploy.
- **Plan por tenant encima del RBAC** (F12-a, 2026-07-11 — POS standalone, diseño en
  `DISENO-POS-PERFILES.md` §7): `tenants.plan` (`suite`|`pos`) acota qué módulos
  EXISTEN para el tenant. El catálogo `PLANES` en `permisos.py` es ESPEJO del CHECK
  de la migración 018 (misma regla que MODULOS↔seed 010). `permisos_efectivos()` =
  **plan ∩ rol** → el login viaja recortado y el nav del front se adapta solo;
  las guardas chequean plan ANTES que rol (403 "Módulo no incluido en el plan",
  nunca 401); `/permisos/catalogo` se filtra por plan (la matriz de roles no muestra
  módulos ajenos). Al AGREGAR un módulo, además del seed de roles hay que decidir
  **si entra o no al plan `pos`** (editar `PLANES`); plan desconocido degrada a
  suite (nunca bloquear por un valor no mapeado). Los roles sembrados pueden tener
  permisos de módulos fuera del plan: son inertes y quedan listos para el upgrade.
  Alta de tenants (cualquier plan): `tools/setup_tenant.py` (idempotente, crea hasta
  la caja POS default) — `demo_setup_tenant.py` queda solo para el tenant demo.
- **Reemplazar una colección hija con UNIQUE que incluye la FK exige flush intermedio**
  (F12-c, bug real en el PUT de plantillas de despiece): asignar `padre.hijos = [nuevos]`
  con `cascade="all, delete-orphan"` puede emitir los INSERT antes que los DELETE y
  chocar el UNIQUE (fk, x). Patrón correcto: `padre.hijos = []` → `await db.flush()` →
  `padre.hijos = [nuevos]`.
- **Índices para relaciones `selectin`**: el loader emite `WHERE fk IN (...)` SIN
  `tenant_id` → un índice compuesto `(tenant_id, fk)` NO le sirve (mordió en
  `comprobante_items`/`compra_items`, migraciones 006/007). Toda tabla hija nueva lleva
  índice por el FK solo (los UNIQUE que arrancan por el FK ya lo cubren).
- **Columnas TEXT pesadas nacen `deferred`** (XML de WSFEv1, blobs): si no, viajan en
  CADA select del modelo — listados, cta. cte., libros, POS (caso real:
  `arca_request/arca_response`, aplicado 2026-07-06 en el LOTE TÉCNICO). En async,
  ASIGNAR a una columna deferred es seguro; LEERLA fuera de query exige `undefer`.
- **Búsquedas `ILIKE '%…%'` con OR multi-columna**: el GIN pg_trgm debe ser
  **multicolumna** cubriendo TODAS las ramas del OR — el planner arma un BitmapOr y si
  una rama queda sin índice, cae a seqscan (migración 011: `entidades` y `articulos`).
- **Los listados viajan livianos** (LOTE TÉCNICO): `GET /ventas/comprobantes` y
  `GET /compras/comprobantes` NO devuelven items/alícuotas/vencimientos — el detalle
  completo se pide por id. Scripts que consuman el listado esperando `items` deben
  pedir el detalle. En el front, `useDialogos` reemplaza a window.confirm/prompt
  (cero usos nativos; todo componente que lo use renderiza `{dialogos}`).
- **Agregaciones que arrancan con una función escalar necesitan `.select_from()`
  explícito** (Fase 7): un `select(func.sum(...)).join(Otra, ...)` sin lado izquierdo
  entidad revienta con "Don't know how to join" — SQLAlchemy no infiere el FROM desde
  la función. Los KPIs del dashboard llevan `.select_from(TablaBase)` antes del `.join`.
- **El padrón ARCA reusa el motor fiscal** (Fase 7): `wsaa.solicitar_ta(..., servicio=
  "ws_sr_constancia_inscripcion")` — el WSAA ya es multi-servicio, no se toca. El padrón
  (`services/arca/padron.py`) sigue el mismo patrón de modos que la emisión: simulado
  (registro ficticio, dev/demo sin cert) / homologación / producción. El TA de padrón se
  cachea aparte en `arca_tokens` (servicio distinto). Endpoint `GET /padron/{cuit}`
  guardado por `clientes`/`proveedores` (los que dan de alta entidades), 400 si ARCA
  deshabilitado, 422 si el CUIT tiene DV inválido.
- **Proxy Nominatim: viewbox SIN `bounded=1` en ZGC** (Fase 7, difiere de ZGE): ZGE
  encierra los resultados en su municipio (`bounded=1` los EXCLUYE); ZGC tiene tenants en
  todo el país → el sesgo por tenant (`tenants.geo_centro_lat/lon/delta`, `PUT /empresa/geo`)
  solo prioriza la zona sin excluir el resto. El front NUNCA llama a OSM directo (proxy
  único `/geo`). Rate limit por-lambda (Vercel no garantiza el lock global entre
  invocaciones; mitigado con debounce 500 ms + mín. 3 chars + limit 5). Si un tenant lo
  estresa: migrar a Photon es cambiar solo `geo.py`.
- **Criterio BUC en domicilios** (Fase 7): calle/localidad/provincia se completan SOLO
  desde OSM y quedan readOnly (con escape "cargar a mano"); el mapeo provincia OSM →
  código ARCA del catálogo está en `lib/geo.ts` (front) y `services/arca/padron.py`
  (back, para el padrón). El domicilio plano de `entidades` sigue siendo el fiscal;
  `entidad_domicilios` (migración 012) guarda los adicionales (entregas) para Logística.
- **Stock valorizado = solo existencias positivas** (Fase 7 KPI): `SUM(GREATEST(cantidad,0)
  × costo_neto)`. Un saldo negativo (vendido sin reponer) es un faltante que se ve en el
  kardex, NO una deuda que reste valor al inventario. El costo se netea de IVA si
  `costo_con_iva`. Los datos de demo tienen stock negativo masivo (por eso importa).
- **Export CSV: helper compartido** (Fase 7): `app/core/csv_export.py` (`csv_response`/`num`)
  — separador `;`, coma decimal, BOM UTF-8 + CRLF (Excel es-AR directo) CON escape de
  celdas (comillas si el texto trae `;`/comillas/saltos — el helper viejo de `libros.py`
  no escapaba porque eran solo números). Los `.csv` de listados reusan el filtro del
  listado (`_filtro_comprobantes`/`_filtro_compras`), tope 5000 filas.
- **Rutas ESTÁTICAS antes que las paramétricas en el mismo router** (bug real F8): un
  `GET /export.csv` o `/resumen` declarado DESPUÉS de `GET /{id}` lo captura `/{id}` (intenta
  parsear "export.csv" como UUID → 422). FastAPI matchea por orden de declaración: todos los
  paths literales de un prefijo van ARRIBA del `/{id}`. Regla al escribir cualquier router.
- **Campos DERIVADOS en schemas de salida: default, no required** (bug real F8): un campo que
  NO existe en el modelo ORM pero se calcula después (ej. `signo` a partir de `tipo`) no puede
  ser `required` si el `*Out` se arma con `model_validate(orm_obj)` — la validación corre ANTES
  de poder setearlo y revienta con "Field required". Darle default y asignarlo tras validar
  (`out = Out.model_validate(m); out.signo = ...`), o construir el dict completo antes de validar.
- **Contrato de CONTABILIZABILIDAD** (mini-fase 014, 2026-07-10 — leer
  `docs/DISENO-CONTABILIDAD.md` antes de crear cualquier documento operativo nuevo): todo
  documento nace (1) COMPLETO — importes discriminados + contrapartida financiera identificada
  (medio, y `cuenta_bancaria_id` si aplica) —, (2) INMUTABLE — anular = `estado` +
  `anulado_at`/`anulado_por` o contra-documento; PROHIBIDO `db.delete` y el UPDATE destructivo
  de importes de un documento emitido/registrado; TODO lector filtra `anulado_at IS NULL`,
  incluidos los checks de bloqueo (si no, las anuladas bloquean para siempre) — y
  (3) MAPEABLE — toda categoría que decida una cuenta contable es FK a catálogo, no texto
  libre. Los movimientos de stock sellan `costo_unitario` neto ARS (`services/stock_valor.py`)
  y la fecha del documento si viene backdateado — PERO el contra-movimiento de ANULACIÓN se
  fecha HOY, nunca con la fecha del papel (el hecho ocurre hoy; bug cazado en la revisión de
  la 014). La contabilidad (F9) se DERIVA de los documentos con un motor regenerable
  (`services/contabilidad.py`); ningún módulo postea asientos en línea. Toda regla de
  `asiento_mapeos` DEBE tener fila default (clave NULL) — un origen sin fallback saltea
  asientos con warning (mordió con los débitos de extracto importado).
- **Marcas de "ya procesado" se DERIVAN, nunca mutan el documento fuente** (F11,
  extensión del contrato de inmutabilidad): un documento está liquidado/exportado/
  procesado si existe un ítem VIVO del documento procesador que lo referencia
  (patrón `comision_liquidacion_items`) — anular el procesador (marcar) libera los
  documentos solo. Nada de flags booleanos sobre comprobantes/recibos emitidos.

## 6-bis. Carga de datos y scripts contra la DB (lecciones permanentes)

- **Orden de migradores en un mismo tenant: CLIENTES antes que PROVEEDORES.** Bug real
  (2026-07-05): `migrar_clientes.py` NO reusa entidades existentes por documento — solo
  dedupea dentro del rol cliente —, así que corriendo después de proveedores, un CUIT
  compartido revienta `uq_entidades_doc` y aborta la transacción. `migrar_proveedores.py`
  SÍ reusa entidades (patrón BUE, `entidades_reusadas_bue`). Artículos es independiente.
  (Arreglar el migrador de clientes para que reuse por doc queda como deuda técnica.)
- **Borrar entidades de un tenant**: primero `update articulos set proveedor_habitual_id=null`
  y `delete articulo_proveedores` (FK `articulos_proveedor_habitual_id_fkey`), luego roles
  (clientes/proveedores), luego `entidad_contactos`, luego `entidades`.
- **Correr scripts (migradores) contra PROD**: no hay `.env.prod` en el repo. Armar uno
  temporal con la `DATABASE_URL` de Supabase (session pooler `:5432`, password del
  `%APPDATA%\postgresql\pgpass.conf` **percent-encoded** con `urllib.parse.quote`).
  **BORRARLO al terminar** — tiene la password en claro (está en `.gitignore` por `.env.*`,
  pero igual eliminarlo). La generación de operaciones sí va por la API pública (Vercel),
  no por SQL directo.
- **Setup de un tenant para poder facturar** (no existe como un solo comando): tenant +
  usuario + `arca_config` modo simulado + punto de venta + depósito activo. Lo orquesta
  `tools/demo_setup_tenant.py` (idempotente). Sin depósito activo, `emitir` da 422.
- **psql local (dev)**: no está en el PATH — usar
  `"C:\Program Files\PostgreSQL\17\bin\psql.exe"`; la credencial de `zgc_dev` está en
  `backend/.env.local` (pasarla por `$env:PGPASSWORD`; el pgpass solo tiene la de prod).
- **Levantar el backend local para probar en vivo** (gotcha Windows/Git Bash, F8): el config
  (`app/core/config.py`) lee el archivo `ENV_FILE` (default `.env`), y en el repo solo existe
  `.env.local` → sin `.env`, `JWT_SECRET` queda vacío y el LOGIN da 500 ("HMAC key must not be
  empty"). Los `export VAR=...` / `ENV_FILE=... uvicorn &` NO se propagan al proceso backgroundeado
  con `&` en este shell. Solución fiable: `cp backend/.env.local backend/.env` antes de levantar
  uvicorn (y borrarlo al terminar). OJO: un uvicorn viejo puede quedar sirviendo el puerto y
  responder con config vieja → `taskkill //F //IM python.exe` antes de relanzar si algo "no toma".
  Para tener un login usable en dev: `python tools/demo_setup_tenant.py --clave X` fija la clave
  de `demo@zaris.com.ar` y arma tenant+PV+depósito+arca. El proxy de Vite apunta a `localhost:8021`.
- **El deploy de PROD lo hace Claude de punta a punta** (mandato de César 2026-07-06 en la
  Fase 8; NO volver a pedirle que deje el deploy): el MCP de Supabase de las sesiones ve las
  cuentas ZGE/news-bot pero **NO el proyecto ZGC** (cuenta separada, sa-east-1, ref
  `lasjyuygcfqhwjdrkrkq`) — PERO psql SÍ conecta con el pgpass usando `-w` (no-password), así
  que Claude aplica la migración por psql session pooler y hace el `git push` él mismo.
  Flujo: (1) `psql -h aws-1-sa-east-1.pooler.supabase.com -p 5432 -U postgres.<ref> -d postgres
  -w -f sql/NNN.sql` (la migración SIEMPRE va ANTES del push), (2) verificar contra prod,
  (3) `git push origin master` (Vercel + Pages redeployan), (4) smoke prod + click-through.
  Aplicado con éxito en F8 (migración 013 + smoke 12/12). El pgpass NO se rota ni se imprime.
- **psql a PROD por session pooler: flags SEPARADOS, no URL-string** (gotcha 2026-07-06): si
  se le pasa la `DATABASE_URL` como un string y no trae la password embebida (o es un
  placeholder), psql cae a conectar como el usuario del SO y pide *"Contraseña para usuario
  Cesar"* (que NO es la de Windows ni ninguna válida). El fix es conectar con
  `-h aws-1-sa-east-1.pooler.supabase.com -p 5432 -U postgres.<ref> -d postgres -f archivo.sql`
  — los cuatro valores deben matchear EXACTO la línea del pgpass para que encuentre la password
  sola. Y los meta-comandos de psql (`\dt`, `\d+`) NO corren en PowerShell: para verificar desde
  afuera usar `psql ... -c "SELECT ..."` (una consulta, no la sesión interactiva).
- **Alta de usuarios: por la API, no por SQL** (2026-07-06): `POST /usuarios` (con un admin del
  tenant) respeta el hash bcrypt, el anti-lockout y las validaciones. El email valida con
  `EmailStr` de Pydantic → **`.test` (y otros TLD reservados RFC 2606) dan 422**; para usuarios
  de prueba usar `@zgc.dev`. `password` exige mín. 6 chars. Los 5 usuarios de prueba de prod
  (uno por rol) están documentados en la memoria del proyecto.
- **Suites en vivo: todo recurso NOMBRADO que crea el test lleva el sufijo único de la
  corrida** (uuid), no solo emails/CUITs — si la suite crashea a mitad, el cleanup no
  corre y los huérfanos rompen los conteos de la re-corrida (mordió en Fase 6.5 con un
  rol "Depósito" huérfano de una corrida anterior). AMPLIADA en F9-bis: también los
  **VALORES que el backend usa como clave de matching** (importes en candidatos de
  apareo, fechas de búsqueda) llevan valor único por corrida — los huérfanos de corridas
  anteriores contaminan los resultados aunque tengan nombre distinto. Y al testear un
  código de error específico (p. ej. 409 "ya apareado"), el fixture debe SATISFACER las
  validaciones previas del endpoint (o dispara el 422 anterior y el test miente).
  AMPLIADA en F12-a: la **PRESENCIA de un registro en un agregado compartido se
  consulta con su filtro específico** (`?origen=stock_ajuste&limit=1`), NUNCA
  escaneando una página del listado — la suite F9 asertaba orígenes sobre una página
  `limit=200` del día y con 351 asientos acumulados por la batería de regresión el
  registro buscado caía fuera de la página (la prueba fallaba con el motor sano).
- **`git add -A -- ':!ruta'` ABORTA (exit 1) si la ruta está gitignoreada** (F9): el
  pathspec de exclusión hace que git intente evaluar el archivo ignorado y corta con el
  hint "paths are ignored". Si el archivo ya está en `.gitignore`, `git add -A` solo alcanza.
- **NUNCA editar archivos UTF-8 con pipelines de PowerShell 5.1** (F9-bis):
  `(Get-Content f) -replace ... | Set-Content -Encoding utf8 f` lee el UTF-8 sin BOM
  como ANSI y lo re-escribe → **mojibake** en todos los acentos (Ã­, Ã³). Para editar
  archivos del repo usar SIEMPRE las herramientas de edición (Edit/Write), no shell.
- **Commits multilínea: mensaje a archivo + `git commit -F`** (F12-a): un here-string
  `@'...'@` pasado al tool de PowerShell puede llegar mal parseado (las líneas del
  mensaje se interpretan como comandos sueltos — un `- PLANES...` intentó ejecutarse).
  Escribir el mensaje a un archivo temporal (scratchpad) y commitear con `-F ruta`.
  AMPLIADA en F12: el archivo del mensaje se escribe con la herramienta Write, NUNCA
  con `Out-File -Encoding utf8` (PS 5.1 mete BOM y el BOM queda DENTRO del mensaje —
  primera línea del commit 45345a7 arrancó con `﻿`).
- **Heredocs (`<< 'EOF'`) en el tool de Bash de este entorno NO son confiables** (F12):
  un `cat >> archivo << 'EOF'` con contenido largo cortó con "unexpected EOF while
  looking for matching quote". Misma regla que los pipelines de PowerShell: todo
  contenido de archivo se escribe con Write/Edit, el shell no toca archivos del repo.
- **NUNCA recortar la salida de una suite con `| Select-Object -First N`** (lote
  diferidos 2026-07-11): al recibir N objetos PowerShell cierra el pipe y MATA el
  proceso upstream a mitad de corrida — la suite parece crashear (exit 255,
  traceback a mitad) con el código sano. Para ver solo el inicio: redirigir a
  archivo (`> out.txt`) y `Get-Content -TotalCount/-Tail`. `Select-Object -Last N`
  sí es seguro (espera a que el proceso termine).

## 7. Deploy y frontend (lecciones permanentes)

- **El deploy de GitHub Pages falla transitoriamente** (`actions/deploy-pages@v4`:
  "Deployment failed, try again later", `error_count: 10`) con frecuencia ~50%. **No es el
  código** — verificar que el job `build` dio `success` y re-lanzar con
  `gh run rerun <id> --failed`. No tocar nada.
- **Push a `master` = deploy a producción**: redeploya el backend en Vercel siempre; el
  workflow de Pages SOLO corre si el push toca `web-app/**` (filtro `paths:` en
  deploy-pages.yml — que un push de solo docs no genere run en `gh run list` NO es un
  fallo). Antes de pushear, si el modelo agregó columnas/tablas, **la migración va
  SIEMPRE primero**. Probe barato de "¿Vercel ya sirve el backend nuevo?" (mejora F9 del
  probe 401/404 del LOTE TÉCNICO): `curl /openapi.json | grep <ruta-o-campo-nuevo>` — es
  público, no necesita token y detecta cambios de schema, no solo rutas nuevas. Matiz que mordió en Fase 6.5: una columna nueva en un modelo YA
  mapeado (ej. `usuarios.rol_id`) rompe TODOS los SELECT de esa tabla contra una DB sin
  migrar — en `usuarios` eso es el LOGIN entero, no solo la feature nueva. Verificarlo
  con psql antes del push.
- **Popover/dropdown dentro de un contenedor con `overflow:hidden`** (p.ej. el hero del
  inicio, que lo tiene para las órbitas animadas): un hijo con `position:absolute` se
  RECORTA. Usar `position:fixed` anclado a las coords del botón (`getBoundingClientRect`
  en el onClick) + clamp horizontal y vertical al viewport. Verificar en ventana chica.
- **Tokens de tipografía**: solo existen `--size-hero`, `--size-subhead`, `--size-title-sm`,
  `--size-ui`, `--size-btn`, `--size-caption` (NO `--size-title`). Usar una var inexistente
  cae al default heredado y descuadra el diseño — verificar el nombre contra `tokens.css`.
- **HMR de Vite en dev deja componentes stale**: al verificar cambios de estado/handlers en
  el navegador, si un click "no hace nada", **recargar la página completa** antes de
  concluir que hay un bug (pasó 2-3 veces en esta sesión: el handler nuevo no estaba
  adjunto por HMR).
- **`git push` colgado con el remoto accesible = credential manager pidiendo credenciales
  interactivas** (F11): `ls-remote`/`fetch` andan pero el push cuelga minutos sin error —
  el Windows Credential Manager quedó esperando un prompt tras un 401 en el receive-pack
  (visible con `GIT_TRACE=1 GIT_CURL_VERBOSE=1`). Fix que funciona sin tocar la config
  global: `git -c credential.helper= -c credential.helper='!gh auth git-credential' push`
  (usa el token del gh CLI, que no expira a mitad de sesión). No insistir con reintentos
  a ciegas: diagnosticar con trace al segundo intento fallido.
