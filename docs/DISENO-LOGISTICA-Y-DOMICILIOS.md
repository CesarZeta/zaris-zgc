# ZGC — Diseño: domicilios normalizados (OSM) y módulo de Logística de entregas

> Mandato de César (2026-07-05): (1) adoptar el estándar de ZGE de normalización de
> domicilios con OpenStreetMap, "con las mismas condiciones y encuadramientos";
> (2) un módulo pequeño de logística para entregas de mercadería.
> La implementación de ZGE fue relevada completa contra su código real el 2026-07-05
> (backend `geo.py`, componentes, migraciones y lecciones de QA).
> **Estado: DISEÑO** — cuándo se implementa: §1.4 y §2.4.

## 1. Normalización de domicilios con OSM (estándar heredado de ZGE)

### 1.1 Qué hace ZGE — lo que se porta tal cual

Piezas a copiar **casi textuales** desde ZGE:

| Pieza ZGE | Qué es |
|---|---|
| `backend/app/api/routes/geo.py` | Proxy único a Nominatim: el frontend **nunca** llama a OSM directo |
| `web-app/src/lib/geoNominatim.ts` | Cliente + `parseAddress` (calle+altura / localidad / provincia) |
| `web-app/src/ui/AddressSearch.tsx` | Autocomplete con debounce 500 ms, mínimo 3 caracteres, 5 sugerencias |
| `MapaPicker.tsx` / `DireccionGeoField.tsx` | Mapa Leaflet con pin manual (opcional en ZGC v1; obligatorio para logística) |

Condiciones y encuadramientos que se heredan **idénticos**:

- **Proxy con rate limit hacia Nominatim** (política de uso: máx. 1 req/s, User-Agent
  identificable), `Accept-Language: es`, timeout 8 s, 502 amable si OSM no responde.
- **`countrycodes=ar`** siempre + `addressdetails=1`.
- **Filtro de POIs** (`solo_direcciones=true` para campos de domicilio) con las tres
  lecciones cazadas en el QA de ZGE:
  1. NO usar `layer=address` de Nominatim (excluye calles sin altura exacta, que SÍ
     son direcciones válidas → falsos "sin resultados").
  2. Pedir `limit=40` upstream y filtrar después (hay búsquedas con 15+ comercios
     antes de la primera calle).
  3. Blacklist por `class` (`amenity, shop, office, tourism, leisure, craft,
     healthcare, club, emergency, man_made`) y, cuando un resultado tiene calle
     válida pero el nombre visible arranca con un comercio, **reescribir el
     `display_name`** desde `address` en vez de descartarlo.
- **Regla de las dos vías** (CLAUDE.md ZGE §23): todo formulario que capture un
  domicilio georreferenciado ofrece buscador OSM **y** pin manual en mapa; el texto
  queda editable sin borrar las coordenadas; hint mono con lat/lon + "Quitar pin".
- **Criterio BUC** (el más estricto, aplica a la BUE de ZGC): calle/localidad/
  provincia se completan **solo desde OSM** y quedan readOnly — "si tu dirección no
  aparece, refiná la búsqueda". Sin carga manual del domicilio en el maestro.

### 1.2 Adaptaciones para ZGC (las únicas tres)

1. **User-Agent propio**: `ZGC-API/1.0 (email de contacto)` — requisito de Nominatim.
2. **Viewbox**: ZGE encierra los resultados en el municipio (`viewbox` + `bounded=1`,
   con centro/delta configurables). ZGC tiene tenants en todo el país → default
   **sin viewbox**, con **sesgo opcional por tenant**: si el tenant configura su
   ciudad (centro + delta en su config), se manda `viewbox` **sin** `bounded=1`
   (prioriza la zona sin excluir el resto — un comercio de Rosario ve primero
   "San Martín 1500, Rosario" pero puede cargar un cliente de Santa Fe).
3. **Rate limit en serverless**: el lock global de ZGE protege un proceso
   persistente; en Vercel cada invocación es efímera y el 1 req/s no se garantiza
   entre lambdas. Mitigación v1 (riesgo aceptado y documentado): debounce 500 ms +
   mínimo 3 caracteres + `limit` 5 mantienen el tráfico real muy por debajo del
   límite; el lock por-lambda queda igual (protege ráfagas dentro de una instancia).
   Si un tenant grande lo estresa: migrar a **Photon** (API compatible, sin límite
   duro) o Nominatim self-hosted — el proxy único hace que el cambio sea de un solo
   archivo.

### 1.3 Modelo de datos en ZGC

`entidades` (BUE) ya tiene `domicilio` (texto), `localidad`, `provincia_id`
(catálogo ARCA de Fase 1) y `codigo_postal`. Cambios:

- **Migración**: `entidades` += `latitud NUMERIC(10,7)`, `longitud NUMERIC(10,7)`
  (nullable). `sucursales` += ídem.
- `AddressSearch` completa: `domicilio` ← calle + altura (`parseAddress`),
  `localidad` ← city/town/village/…, `provincia_id` ← **mapeo state→catálogo**
  (tabla de equivalencias simple: los nombres de provincia de OSM son estables),
  `codigo_postal` ← postcode si viene (editable a mano: OSM Argentina es flojo en
  CP), + lat/lon.
- Condición ZGE-BUC: domicilio/localidad/provincia **readOnly, solo desde OSM**;
  CP editable.
- **`entidad_domicilios`** (tabla nueva, requerida por Logística §2): la BUE ya
  declara "domicilios" en plural (CLAUDE.md §1-bis) pero hoy hay uno solo embebido.
  Campos: `tenant_id`, `entidad_id`, `tipo` (`fiscal` | `entrega` | `otro`),
  `etiqueta` ("Depósito Ruta 9"), mismos campos normalizados + lat/lon,
  `predeterminado`, `activo`. El domicilio plano de `entidades` queda como el
  fiscal/principal (compatibilidad total con todo lo existente); las entregas usan
  esta tabla.
- Dónde se integra en la UI: en el **`EntidadFields` compartido** que sale del lote
  técnico de UI (hoy el bloque de entidad está duplicado en ClienteForm y
  ProveedorForm — unificar primero, normalizar después, para hacerlo una sola vez).

### 1.4 Cuándo

**F7 (post-MVP inmediato)**, junto con el padrón ARCA por CUIT — son las dos patas de
calidad de datos del mismo formulario (padrón trae razón social/condición IVA; OSM
normaliza el domicilio). Conviene hacerlo **antes de cargar entidades masivamente**:
normalizar después es backfill (ZGE tuvo que escribir `geocodificar_buc.py` para eso;
si hiciera falta acá, también se porta).

## 2. Módulo de Logística de entregas

### 2.1 Alcance v1 (deliberadamente liviano)

- **Transportistas**: rol satélite de la BUE (previsto desde Fase 1, como clientes/
  proveedores): `transportistas` (`entidad_id`, vehículo/dominio, observaciones,
  activo). Sirve el fletero externo (entidad con CUIT) y el reparto propio
  (entidad = empleado/vehículo propio).
- **Entregas** (`entregas`): una por comprobante a entregar — remito o factura.
  - `comprobante_id` (FK), domicilio de entrega **snapshot** (texto normalizado +
    localidad + lat/lon copiados de `entidad_domicilios` al crearla — si el cliente
    se muda, la entrega histórica no cambia), `fecha_programada`,
    `transportista_id`, `hoja_ruta_id` (nullable), `orden` en la hoja,
    `estado`: `pendiente → asignada → en_reparto → entregada | rechazada |
    reprogramada`, `recibido_por`, `observaciones`.
- **Hojas de ruta** (`hojas_ruta`): `fecha`, `transportista_id`, `sucursal_id`
  (nullable), `estado` (abierta/en reparto/cerrada), entregas ordenadas. Imprimible
  en HTML (mismo mecanismo que los comprobantes): dirección, cliente, teléfono,
  bultos/observaciones, columna para firma.
- **UI — módulo Logística** (3 vistas):
  1. **Pendientes**: comprobantes con entrega creada (y acceso rápido a "crear
     entrega" desde remitos/facturas emitidos).
  2. **Hojas de ruta**: armado (elegir pendientes, ordenar), impresión, despacho
     (pasa todo a `en_reparto`).
  3. **Rendición**: al volver el reparto, marcar entregada/rechazada (+ motivo) por
     fila.
  - Mapa opcional con pins de las entregas del día (Leaflet ya viene con el porteo
    OSM) — ayuda a ordenar la hoja a ojo; la optimización automática de recorrido
    NO va en v1.
- **Regla de encuadre**: el estado de entrega NO toca el circuito fiscal ni la cta.
  cte. Una entrega rechazada se resuelve comercialmente (NC, re-entrega) por los
  módulos existentes; logística solo registra y ordena el reparto.

### 2.2 Por qué entra en la regla ERP-liviano

Es crecimiento **hacia adentro** del ciclo comercial (el remito ya existe desde
Fase 3 — esto lo operativiza), no un vertical nuevo: el segmento distribuidora/
mayorista es uno de los cuatro del legacy (DEFINICION-PRODUCTO §2) y el legacy tenía
transportistas en su modelo. No es MRP ni gestión de servicios.

### 2.3 Diferido a v2

Vista móvil del repartidor (marcar en calle), prueba de entrega (foto/firma),
optimización de recorridos, costo de flete por zona (el catálogo `zonas` de Fase 1
ya existe), integración con el delivery del perfil resto.

### 2.4 Dependencias y cuándo

- **Requiere**: domicilios OSM + `entidad_domicilios` (§1, F7) y el alta del rol
  transportista.
- **Activación** (regla ERP-liviano): primer cliente que reparte (distribuidora,
  mayorista, corralón). Esfuerzo estimado: una fase corta (una migración + un módulo
  React + impresión HTML), sin ARCA ni complejidad fiscal.
