# F17 — Auditoría de acciones (audit log)

> Diseño 2026-07-14. Segunda de las 5 piezas aceptadas por César el 2026-07-13
> (fila 17 del cuadro POST-MVP): «la mitad operativa de la inmutabilidad contable
> ya lograda: quién cambió precios masivamente, quién editó matriz de permisos,
> quién tocó config ARCA, logins fallidos». Red de seguridad ante "yo no borré eso".

## 1. Encuadre — qué audita y qué NO

Los **documentos operativos ya son su propia auditoría**: el contrato de
contabilizabilidad (mini-fase 014) los hace inmutables, toda anulación queda
marcada con `anulado_at`/`anulado_por`, y el kardex/cta.cte. traza cada efecto.
Auditar cada venta o recibo duplicaría la traza documental y llenaría la tabla
de ruido.

El audit log cubre lo que **NO deja documento**: las escrituras de
**configuración** (usuarios, roles, permisos, ARCA, puntos de venta, nodos LAN)
y los eventos de **seguridad** (logins, resets de contraseña, autorizaciones de
supervisor, cambios masivos de precios, cierres de período).

**Inmutable por construcción**: la API no expone UPDATE ni DELETE sobre
`audit_eventos`; RLS deny-all como segunda defensa (patrón 005). Sin purga en
v1 (filas chicas; si el free tier aprieta se decide con César — regla 3 del
ROADMAP).

## 2. Modelo (migración 027)

Tabla única `audit_eventos`:

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid PK | `gen_random_uuid()` |
| `tenant_id` | uuid FK tenants | CASCADE |
| `usuario_id` | uuid FK usuarios | nullable (robustez; hoy siempre resuelto — ver login fallido en §3) |
| `usuario_email` | varchar(120) | **SNAPSHOT** (patrón F12-bis): legible sin join; si el usuario se renombra/inactiva el evento no cambia. En login fallido: el email intentado |
| `accion` | varchar(40) | código del catálogo (§3) |
| `modulo` | varchar(20) | módulo RBAC del evento + `auth` (para filtrar; catálogo en código, como `MODULOS`) |
| `ref_id` | uuid | objeto afectado (usuario, rol, comprobante, nodo…) |
| `ref_texto` | varchar(200) | descripción humana: «rol Gerente», «usuario x@y.com», «312 artículos +10 %» |
| `detalle` | jsonb | parámetros / antes-después específicos de la acción. **NUNCA** claves, hashes ni certificados |
| `ip` | varchar(45) | primer valor de `x-forwarded-for` (Vercel) con fallback a `request.client.host` |
| `created_at` | timestamptz | `now()` |

Índices: `(tenant_id, created_at)` (listado) y `(tenant_id, accion)` (filtro).
Sin `updated_at`: la fila nunca muta. Tabla nueva ⇒ re-aplicar la 005 en prod.

## 3. Catálogo de acciones v1 (espejo `services/auditoria.py` ↔ este doc)

| Módulo | Acción | Cuándo | `detalle` |
|---|---|---|---|
| auth | `login_ok` | login suite y POS exitoso | `{origen: suite\|pos}` |
| auth | `login_fallido` | credencial mala en suite/POS, **solo si el email corresponde a un usuario** (motivo `clave`\|`inactivo`): un email inexistente no pertenece a ningún tenant que pueda ver el evento (los emails son globales) — ese ruido es observabilidad de plataforma (F18), no auditoría de tenant | `{origen, motivo}` |
| auth | `password_recuperacion` | solicitud autoservicio con usuario válido (la respuesta pública no filtra; el evento es interno) | — |
| auth | `password_restablecida` | token consumido | — |
| configuracion | `password_reset_admin` | reset por admin (F6.5) | ref = usuario objetivo |
| configuracion | `usuario_alta` / `usuario_edicion` | POST/PUT /usuarios | edición: campos cambiados con antes/después (`rol_id`, `activo`, `nivel_acceso`, `sucursal_id`) |
| configuracion | `rol_alta` / `rol_edicion` / `rol_borrado` | ABM de roles | alta: permisos iniciales + clonado |
| configuracion | `rol_permisos` | PUT matriz de permisos | `{antes: {...}, despues: {...}}` |
| configuracion | `arca_config` | PUT /arca-config | `{modo_antes, modo_despues, cargo_certificado: bool, cargo_clave: bool}` — jamás el PEM |
| configuracion | `punto_venta_alta` / `punto_venta_edicion` | ABM PV | número y flags |
| configuracion | `nodo_alta` / `nodo_revocado` / `nodo_token_regenerado` | nodos LAN (F13) | sucursal, PV propio |
| articulos | `precios_masivo` | cambio masivo REAL (dry_run **no** audita) | `{tipo, porcentaje, listas, filtros, afectados}` |
| articulos | `import_excel` | import de artículos | `{total_filas, creados, actualizados, errores}` |
| pos | `pos_anulacion_supervisor` | anulación autorizada en el POS | ref = comprobante anulado; `{supervisor_email, motivo}` |
| contabilidad | `periodo_cerrado` / `periodo_reabierto` | cierre/reapertura mensual | `{periodo}` |

Criterio de extensión: toda fase nueva que agregue una escritura de
configuración o un evento de seguridad suma su acción acá y llama al servicio —
igual que el checklist de contabilizabilidad para documentos.

## 4. Mecanismo de captura

`app/services/auditoria.py` — **helper explícito, sin commit** (patrón
`emitir_core`):

```python
def registrar(db, *, tenant_id, usuario, accion, ref_id=None,
              ref_texto=None, detalle=None, request=None) -> None
```

- Agrega la fila a la **transacción del endpoint**: si el endpoint falla y
  rollbackea, el evento desaparece JUNTO con la acción — correcto, la acción no
  ocurrió. El `modulo` sale del catálogo de acciones (no se pasa a mano).
- **Excepción — eventos que deben sobrevivir a un error** (lección F16 §6, la
  que este diseño «iba a necesitar»): el **login fallido** se comitea ANTES del
  `raise HTTPException(401)` (`db.add(evento); await db.commit(); raise`).
- **NO middleware global**: el decorator sobre `requiere()` correría ANTES del
  endpoint (auditaría intentos que después dan 422) y no conoce el objeto
  afectado. La llamada explícita en los ~20 puntos sensibles es precisa,
  testeable y de blast radius mínimo.
- Los endpoints instrumentados reciben `request: Request` para sellar la IP.

**Nodo LAN**: `auth.py`/`pos_auth.py` corren también en el nodo — sus eventos se
escriben en la DB **local** del nodo y v1 NO los sube (la tabla no está en
`sync_tablas.py`). La auditoría de la nube cubre la nube; subir la del nodo
queda para N3 si el piloto lo pide.

## 5. API de consulta (`api/v1/auditoria.py`, solo nube — ROUTERS_NUBE)

Solo lectura, guarda `configuracion.ver` (precedente: bandeja de emails F16 —
infraestructura del tenant, la ve quien administra la configuración). Sin
módulo RBAC nuevo (evita el ceremonial de catálogo+seed+plan y el gerente ya
tiene `configuracion: ver`).

- `GET /auditoria/eventos` — filtros `accion`, `modulo`, `usuario_id`,
  `desde`/`hasta`, `q` (ILIKE sobre `usuario_email`/`ref_texto`), paginado
  `limit`/`offset` + `X-Total-Count`, orden `created_at desc`. `detalle`
  incluido (es chico, no amerita deferred).
- `GET /auditoria/catalogo` — acciones con etiqueta humana (para el select del
  filtro del front).
- `GET /auditoria/export.csv` — helper `csv_export` (F7), mismos filtros, tope
  5000, `detalle` serializado compacto. Declarada ANTES de cualquier ruta
  paramétrica (regla §6).

## 6. Frontend

`AuditoriaSection.tsx` en Configuración (al final de la página, patrón
`NodosSection`): tabla fecha · usuario · acción (chip con color por módulo —
nunca naranja) · descripción; fila expandible con el `detalle` JSON legible;
filtros acción/texto/rango de fechas; paginado real + botón «Exportar CSV»
(`apiDescargar`). Solo lectura — no hay nada que editar.

## 7. Verificación (suite `tools/test_f17_dev.py`)

Tenant efímero (`setup_tenant.py`) + sufijo único por corrida (§6-bis). Casos:
login ok/fallido (fila con `usuario_id` NULL y email sellado, **comiteada pese
al 401**), reset admin, matriz de permisos con antes/después, `arca_config` sin
PEM en el detalle, cambio masivo real audita / dry-run NO, PV, nodo
alta+revocación, período cierre+reapertura, anulación POS con supervisor,
recuperación de clave completa. Transversales: RBAC 403 nunca 401 (rol sin
`configuracion`), aislamiento de tenant, presencia consultada con **filtro
específico** (`?accion=...&ref_id=...`, nunca escaneando páginas), CSV con BOM,
`X-Total-Count`, y que NO existan rutas de escritura sobre eventos. Regresiones:
login POS 23/23 · mini-014 53/53 · F12-a 36/36 + build TS.

## 8. Diferido documentado

Subida de auditoría del nodo (N3), retención/purga configurable, vista de
"actividad del usuario" en el gestor de usuarios, alertas (N logins fallidos
seguidos → email al admin — la infraestructura la dio F16), auditoría de
lecturas sensibles (export masivo de datos).
