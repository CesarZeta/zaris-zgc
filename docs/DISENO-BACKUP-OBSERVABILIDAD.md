# F18 — Backup por tenant + observabilidad mínima

> Diseño 2026-07-14. Tercera de las 5 piezas aceptadas por César el 2026-07-13
> (fila 18 del cuadro POST-MVP): «"Descargá todo lo tuyo": argumento de venta
> contra el miedo al SaaS + obligación con el free tier de Supabase (pausa tras
> ~1 semana inactivo). Observabilidad: uptime + keep-alive + Sentry free tier».

## 1. Encuadre — dos mitades de la misma promesa

La promesa comercial del SaaS free-tier (DEFINICION-PRODUCTO.md) tiene dos
miedos que responder: **"¿y si me quedo preso?"** (lock-in de datos) y **"¿y si
un día no anda?"** (un servicio hobby sin nadie mirando). F18 responde ambos con
lo mínimo que se sostiene solo:

- **A. Backup por tenant**: un ZIP con TODOS los datos del tenant en CSV
  abrible en Excel, descargable por el administrador cuando quiera.
- **B. Observabilidad**: el backend avisa cuando se rompe (Sentry), alguien
  externo verifica que está vivo (UptimeRobot) y un latido diario impide que
  Supabase pause el proyecto por inactividad (keep-alive).

**Sin migración**: F18 no crea tablas ni columnas (la descarga queda trazada en
`audit_eventos`, que ya existe). Primera fase post-MVP sin DDL.

## 2. Parte A — Backup por tenant («Descargá todo lo tuyo»)

### 2.1 Decisión clave: dump crudo dirigido por metadata, no CSVs curados

Dos formas posibles de armar el ZIP:

1. **CSVs curados por módulo** (estilo export-contador): columnas humanas,
   joins resueltos. Legible, pero cada fase nueva exige mantener su export a
   mano — un checklist más que se puede olvidar, y un olvido acá significa
   **datos del cliente que no salen en su backup** (silencioso y grave).
2. **Dump crudo por metadata** (elegido): iterar `Base.metadata.tables`, tomar
   **toda tabla que tenga columna `tenant_id`**, y volcarla completa filtrada
   por el tenant — un CSV por tabla, columnas = columnas de la tabla.
   **Completo por construcción**: una tabla nueva de una fase futura entra al
   backup sola, sin tocar nada.

La legibilidad no se pierde: los exports curados **ya existen** por módulo
(CSVs de listados del LOTE TÉCNICO/F7, export-contador de F9-bis, libros de
IVA de F5) y siguen siendo la vía para "quiero este listado lindo". El backup
es otra cosa: la garantía de completitud. El LEEME dentro del ZIP lo explica.

### 2.2 Cobertura y exclusiones

Regla de inclusión: **tabla con columna `tenant_id`** (hoy 80 de las 85; las
que no la tienen — `provincias`, `tipos_comprobante`, `tipos_comprobante_compra`
(globales) y `sync_checkpoints` (infra local del nodo, vacía en la nube) —
quedan afuera solas). Caso especial: la fila propia de `tenants` (razón social,
CUIT, rubro, plan) SÍ entra, filtrada por `id`.

Exclusiones EXPLÍCITAS (listas `TABLAS_EXCLUIDAS` / `COLUMNAS_EXCLUIDAS` en el
servicio, cada una con su porqué en comentario):

| Qué | Por qué |
|---|---|
| tabla `arca_tokens` | tokens de autenticación WSAA vivos — secreto, y además efímeros/regenerables |
| tabla `password_resets` | hashes de tokens de reset — secreto sin valor para el dueño |
| tabla `padron_cache` | caché de datos de AFIP, no datos del tenant (se regenera) |
| columna `usuarios.password_hash` | hash bcrypt — jamás sale del sistema |
| columna `arca_config.cert_pem` / `key_pem` | certificado y clave privada ARCA — mismo mandato que el audit log (F17: «el detalle JSONB jamás lleva PEM») |
| columna `sucursal_nodos.token_hash` | hash del token de aparejamiento del nodo |

`audit_eventos` y `email_envios` **SÍ entran**: son trazas del tenant y valen
justamente cuando el cliente se va peleado.

**Guarda de completitud en la suite**: el test itera el metadata y verifica que
toda tabla con `tenant_id` está en el ZIP **o** en `TABLAS_EXCLUIDAS` — una
tabla futura no puede quedar afuera en silencio (el principio "no silent caps"
hecho assert).

### 2.3 Formato del ZIP

```
backup-zgc-<slug-tenant>-<YYYY-MM-DD>.zip
├── LEEME.txt            ← qué es, convención CSV, dónde están los exports curados
├── manifest.csv         ← tabla; filas exportadas; truncado (Sí/No)
├── entidades.csv
├── articulos.csv
├── comprobantes.csv
├── comprobante_items.csv
└── … (un CSV por tabla incluida, nombre = nombre de tabla)
```

- **Convención CSV de la suite** (`core/csv_export.csv_texto`): separador `;`,
  BOM UTF-8, CRLF — el cliente lo abre en Excel es-AR directo. Serialización:
  fechas ISO (`YYYY-MM-DD` / timestamps ISO), UUIDs en texto, `Numeric` con
  punto decimal crudo (es un dump máquina-legible; los importes "lindos" están
  en los exports curados; se documenta en el LEEME).
- **Tope de seguridad**: 200.000 filas por tabla (holgadísimo hoy; el tenant
  más cargado — demo — tiene ~15k movimientos de stock). Si una tabla lo toca,
  el manifest lo marca `truncado=Sí` — nunca se recorta en silencio.
- Todo en memoria (`io.BytesIO` + `zipfile`, patrón export-contador): los CSV
  comprimen ~10:1 y el volumen actual está lejos de los límites de la lambda.
  Si un tenant real lo desborda algún día, la evolución es streaming o export
  asíncrono por email (F16 ya da la pieza) — se decide con César cuando exista
  el caso.

### 2.4 Endpoint y permisos

- `GET /backup/export.zip` — router nuevo `api/v1/backup.py`, **solo perfil
  nube** (NO entra a `ROUTERS_COMUNES`: el nodo sincroniza contra la nube y su
  DB local no es la fuente de verdad del tenant).
- Guarda: `requiere("configuracion", "editar")` — descargar TODO el tenant es
  la lectura más sensible del sistema; mismo criterio que la config ARCA.
  `configuracion` ya está en el plan `pos` ⇒ **las licencias POS standalone
  también tienen su backup**, sin tocar `PLANES` ni el catálogo RBAC.
- **Auditoría** (checklist F17): acción nueva `backup_descargado`
  (`configuracion`, «Backup del tenant descargado») en `ACCIONES_AUDIT`,
  `detalle = {tablas: N, filas_total: N}`. Es la primera **lectura** auditada —
  precedente que F17 dejó anotado como extensión natural. Se agrega la fila al
  §3 de DISENO-AUDITORIA.md (espejo doc↔código).

## 3. Parte B — Observabilidad mínima

Tres piezas, cero servicios pagos, cero infraestructura propia:

### 3.1 `/health/db` — el latido que toca la base

El `/health` actual (main.py) responde sin tocar la DB — no sirve ni para
keep-alive de Supabase ni para detectar "backend vivo pero base caída".
Se agrega **`GET /health/db`** (público, en main.py como `/health`):
`SELECT 1` por la sesión async + latencia en ms → `{status, db, latencia_ms}`;
si la DB no responde, 503. Corre en ambos perfiles (en el nodo mide su
Postgres local — útil para el monitoreo de sucursal).

Es público y barato (una query trivial); no expone datos ni versión de nada.

### 3.2 Keep-alive — que Supabase nunca pause

El free tier de Supabase pausa el proyecto tras ~1 semana sin actividad
(gotcha conocido de la infra, memoria del proyecto). Un hit **diario** a
`/health/db` alcanza para resetear el contador.

- **Vía elegida: Vercel Cron** (`"crons": [{"path": "/health/db", "schedule": "0 9 * * *"}]`
  en vercel.json) — plan Hobby permite crons diarios, corre contra el
  deployment de producción y no depende de nada externo.
  ⚠️ A verificar en implementación: convivencia de `crons` con la config
  legacy `builds`/`routes` del vercel.json actual. **Fallback documentado**:
  workflow de GitHub Actions con `schedule` (gotcha: GitHub deshabilita los
  workflows programados tras 60 días sin actividad en el repo — por eso no es
  la primera opción).
- UptimeRobot (§3.4) pega cada 5 min y también cuenta como actividad —
  cinturón y tiradores.

### 3.3 Sentry — enterarse de los 500 antes que el cliente

Hoy un 500 en prod es invisible salvo que alguien lo reporte. Se integra
**`sentry-sdk`** en el backend (la integración FastAPI es automática al
`sentry_sdk.init()` en main.py):

- Patrón de modos de la casa (EMAIL_MODO): env var **`SENTRY_DSN`** — vacía
  (default) = deshabilitado, no-op total; seteada = activo. Cero cambio de
  comportamiento hasta que César provisione la cuenta.
- `sentry-sdk` es Python puro → apto Vercel. Va a **ambos** requirements
  (`backend/requirements.txt` **y** `api/requirements.txt` — el que instala
  Vercel es el segundo, gotcha F3).
- `send_default_pii=False` y `environment=settings.ENV`. Sin tracing/APM en
  v1 (solo errores): el volumen free tier (5k eventos/mes) se cuida solo.
- **Front diferido**: los errores de UI los ve el usuario y los reporta; el
  valor está en los 500 silenciosos del backend. `@sentry/react` queda anotado
  como evolución si aparece la necesidad.

### 3.4 Uptime externo — UptimeRobot (provisión César, sin código)

Monitor free (50 monitores, intervalo 5 min) sobre:
1. `https://<backend Vercel>/health/db` — backend + DB
2. `https://<frontend Pages>/` — el sitio

Alerta por email al caerse. Bonus: el ping de 5 min mantiene la lambda tibia
(menos cold starts) y cuenta como actividad Supabase.

## 4. UI — Configuración → sección «Backup»

`BackupSection.tsx` (patrón de las secciones existentes), visible con
`configuracion.editar`:

- Botón **«Descargar backup completo»** → descarga el ZIP (mismo mecanismo de
  descarga con auth que los CSV/export-contador existentes).
- Texto corto: qué incluye, qué no (claves/certificados), y que los exports
  por módulo siguen en cada pantalla.
- Las descargas anteriores se ven en la sección Auditoría (F17) filtrando la
  acción — no se duplica un historial propio.

Sin pantalla de observabilidad en v1: Sentry y UptimeRobot tienen sus propios
dashboards; duplicarlos adentro es mantenimiento sin valor.

## 5. Plan de pruebas

`tools/test_f18_dev.py` (tenant efímero + sufijo único, patrón F16/F17):

1. **Backup**: seed mínimo (entidad, artículo, factura emitida, recibo) →
   descargar ZIP → abrirlo con `zipfile`: manifest presente, conteos > 0 en
   las tablas sembradas, columnas sensibles AUSENTES en `usuarios.csv` /
   `arca_config.csv`, tablas excluidas ausentes.
2. **Guarda de completitud**: metadata vs. contenido del ZIP + `TABLAS_EXCLUIDAS`
   (§2.2) — falla si una tabla con `tenant_id` no está en ninguno de los dos.
3. **RBAC**: usuario sin `configuracion.editar` → 403 (nunca 401).
4. **Auditoría**: la descarga deja `backup_descargado` consultable por el
   viewer de F17.
5. **Health**: `/health/db` responde 200 con `latencia_ms` numérica.
6. **Regresiones**: batería estándar; el router es nube-only y no toca
   `ROUTERS_COMUNES`, pero main.py cambia (health) ⇒ corre también
   `test_nodo_dev.py` (criterio de cierre F17).
7. **Smoke prod** (previa corrida local completa — criterio F17): descarga
   real del ZIP en el tenant Smoke, `/health/db` 200, probe de openapi con
   `/backup/export.zip`.

## 6. Pendientes de provisión (César, sin código — se suman a Resend de F16)

| Qué | Dónde | Resultado |
|---|---|---|
| Cuenta Sentry free + proyecto | sentry.io | `SENTRY_DSN` como env var en Vercel |
| Cuenta UptimeRobot free + 2 monitores | uptimerobot.com | alertas por email |

El código entra ANTES y funciona sin esto (Sentry deshabilitado por DSN vacío;
keep-alive por cron no depende de nadie).

## 7. Fuera de alcance v1 (anotado, no prometido)

- **Restore/import del ZIP**: el backup es garantía de salida, no mecanismo de
  migración; un restore serio es un proyecto en sí (orden de FKs, colisiones).
- **Backups programados server-side** (guardar ZIPs periódicos en storage):
  exige storage y ciclo de retención; el modelo v1 es pull a demanda.
- **Sentry en el front** (§3.3) y **alertas propias por email** (UptimeRobot y
  Sentry ya notifican).
- **Subir la auditoría del nodo** al backup de nube: la tabla del nodo es
  local (diferido N3 de F13-LAN).
