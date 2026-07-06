# ZGC — Definición de Producto

> Resultado del cuestionario de discovery del 2026-07-03 (César + Claude).
> Complementa a `CLAUDE.md` (stack y arquitectura). Este documento define **qué** se construye y **para quién**; el roadmap por fases se deriva de acá.

## 1. Visión

ZGC es un **SaaS multi-tenant** de gestión comercial, contable y de stock para comercios argentinos, sucesor web del legacy RevoSolution. Una sola instancia en la nube sirve a todos los clientes (cada tenant = una empresa con N sucursales y N puntos de venta), con costo marginal por cliente cercano a cero — condición necesaria del modelo: **infraestructura 100% free-tier hasta que haya clientes pagando**.

Es un **producto independiente** del ecosistema ZARIS (repo, DB y auth propios). Comparte patrones y experiencia de ZGE, no infraestructura lógica.

## 1-bis. Alcance objetivo: ERP-liviano argentino (adenda 2026-07-05)

ZGC se posiciona como **ERP-liviano argentino en la nube**: le gana a los ERP grandes
(referencia competitiva: SAP Business One) en el segmento PyME/comercio por
**FIT + PRECIO + FISCAL NATIVO**, nunca por amplitud de módulos. La **simplicidad es
marca de producto, no límite**: un comercio lo opera sin consultores, y el cumplimiento
argentino (ARCA, libros, retenciones/percepciones, IIBB) viene nativo de fábrica, no
como "localización" agregada.

**Regla de crecimiento** (rectora de todo el post-MVP):

- Se extiende **HACIA ADENTRO**: finanzas (contabilidad, activos fijos, tesorería),
  fiscal (impuestos, presentaciones a fiscos) y, al final y condicionado, sueldos.
  El foso es la **localización argentina**: a los ERP internacionales les cuesta
  construirla y a los locales legacy les cuesta modernizarla.
- **NUNCA hacia afuera**: producción/MRP, gestión de proyectos/obras, gestión de
  servicios (horas, mesa de ayuda) y localización internacional quedan
  **FUERA PERMANENTE** — cero foso, segmento equivocado, mantenimiento sin retorno.

**Gates (disciplina heredada, sin excepciones):**

- El MVP sigue siendo **Fases 0–6** y no se re-scopea; toda ampliación es post-MVP.
- Ningún módulo-foso se construye antes del **primer cliente de referencia pagando**.
- Infraestructura 100% free-tier hasta que haya clientes facturando.
- Cada módulo-foso lleva **condición de activación explícita** en el ROADMAP: no se
  activa hasta que haya ingresos/capacidad que sostengan su mantenimiento perpetuo
  (padrones, paritarias, cambios normativos) y su piso de testing.

El detalle de fases, condiciones de activación y decisiones abiertas vive en `ROADMAP.md`.

## 2. Mercado objetivo

Los cuatro segmentos del legacy, con una sola base de código:

| Segmento | Qué usa intensivamente |
|---|---|
| Comercio minorista chico | POS simple, stock, caja |
| Supermercado / autoservicio | POS con pesables, envases, departamentos, multi-caja |
| Distribuidora / mayorista | Listas de precios, viajantes/comisiones, cta. cte., remitos |
| PyME comercio/servicios | Facturación electrónica, cta. cte., bancos/cheques |

**Primeros usuarios: ex clientes RevoSolution** — se les migran sus datos DBF con una **herramienta interna** (`tools/`, onboarding asistido por César, no autoservicio). La migración es pieza estratégica del go-to-market.

### 2-bis. Multipropósito por rubro (adenda 2026-07-04)

ZGC es **multipropósito**: no queda orientado a un solo vertical. Un supermercado,
una tienda de ropa/calzado, una casa de electrónica, una ferretería/repuestos y una
distribuidora usan la misma gestión central, con **customización por rubro**
(switch por tenant): presets de UI, atributos sugeridos y, a futuro, el POS que
se sirve a las cajas — los POS sí son full orientados al rubro. El habilitador
técnico es el **modelo de variantes** (talle/color/gusto/capacidad con stock y EAN
propios). Diseño, estadística de mercado y evaluación en `DISENO-RUBROS-Y-VARIANTES.md`.

**Adenda 2026-07-05 (mandato César)**: se suman dos rubros con POS orientado —
**carnicería** (ingreso por media res y despiece a kilos por corte; lo específico es
la transformación de stock en gestión, el POS es el estándar con pesables) y
**restaurante** (sucesor del RestoDelivery del legacy: mesas/mozos/comandas viven EN
el POS, a la gestión llega solo la venta final). Los POS quedan definidos en **tres
configuraciones**: estándar/súper (mercaderías y pesables), carnicería y resto, cada
caja con su perfil y su **sucursal**. Diseño completo en `DISENO-POS-PERFILES.md`.

### 2-ter. Estándares de suite adoptados de ZGE (2026-07-05)

- **Normalización de domicilios con OpenStreetMap/Nominatim**, con las mismas
  condiciones y encuadramientos de ZGE (proxy backend único, filtro de POIs, regla
  de las dos vías, campos completados solo desde OSM en la BUE) y tres adaptaciones
  (User-Agent propio, viewbox opcional por tenant sin exclusión, mitigación de rate
  limit en serverless). Se implementa en F7, antes de la carga masiva de entidades.
  Diseño de porteo en `DISENO-LOGISTICA-Y-DOMICILIOS.md` §1.

## 3. Alcance del MVP

El corazón del MVP es el **ciclo comercial completo en versión simple**:

- **Artículos y stock**: maestro (basado en el esquema legacy: 4 listas de precios con márgenes, código de barras, familias/subfamilias), movimientos, depósitos.
- **Precios en dólares desde el MVP**: artículos `en_dolares` + cotización del día (crítico para electrónica/repuestos/importados).
- **Clientes / Ventas**: presupuestos, facturación, cobranzas, cuenta corriente.
- **Proveedores / Compras**: facturas de compra, pagos, cuenta corriente.
- **Caja**: movimientos y planilla diaria.
- **Facturación electrónica ARCA/AFIP desde el MVP**: cliente **propio** WSAA + WSFEv1 (`backend/app/services/arca/` — decisión 2026-07-04, ver FACTURACION-ARCA.md §9; pyafipws quedó como implementación de referencia). Comprobantes A/B/C con CAE + QR. Homologación real diferida por César (2026-07-05): prod opera en modo simulado hasta generar certificados.
- **POS mostrador web**: pantalla de venta rápida en navegador — lector de código de barras USB (emula teclado, costo cero) e impresión térmica de tickets. Sin pesables/envases todavía.
- **IVA**: libros de IVA ventas/compras (el contador externo es el usuario indirecto).

### Explícitamente FUERA del MVP (fases posteriores)

| Capacidad | Nota de diseño para no cerrarse la puerta |
|---|---|
| Nodo de sucursal LAN (facturar sin internet) | UUIDs en origen, `sucursal_id` en todo, colas de sync — ya en CLAUDE.md |
| POS por perfiles: súper (pesables/balanza, envases, venta por depto.), carnicería (despiece) y resto (mesas/comandas) | Los flags ya existen en el esquema de artículos; diseño 2026-07-05 en `DISENO-POS-PERFILES.md` (ROADMAP F12) |
| Logística de entregas (transportistas, hojas de ruta, estados) | Requiere domicilios OSM + `entidad_domicilios` (F7); diseño en `DISENO-LOGISTICA-Y-DOMICILIOS.md` (ROADMAP F12-bis) |
| Controlador fiscal físico (Hasar/Epson) y transmisión a balanzas | Requieren software puente local en Windows |
| **Contabilidad completa** (plan de cuentas, asientos, balances) | **Módulo independiente activable/desactivable por tenant** — decisión de César; potencial diferenciador de plan pago |
| Cheques, bancos, retenciones, comisiones de vendedores | Módulos de gestión fase 2 |

## 4. Diferenciales vs. legacy (roadmap post-MVP)

Elegidos los cuatro:

1. **Dashboard en tiempo real** — ventas del día por sucursal, márgenes, faltantes, morosidad. Primera pantalla del sistema.
2. **Acceso móvil del dueño** — web responsive: ver el negocio y autorizar desde el teléfono.
3. **Inteligencia artificial** — sugerencia de reposición, detección de anomalías, consultas en lenguaje natural.
4. **Portal de clientes** — el cliente del comercio consulta su cta. cte., descarga comprobantes, hace pedidos.

## 5. Integraciones (roadmap)

Elegidas las cuatro: **Mercado Pago** (QR en POS + conciliación), **e-commerce** (Tiendanube / WooCommerce / Mercado Libre — stock unificado), **WhatsApp** (comprobantes y avisos de vencimiento), **bancos** (importación de extractos para conciliación).

> Criterio 2026-07-05: son **integraciones de canal** — paridad con el mercado, no foso
> (todos los ERP argentinos las tienen). Van gated por demanda real y con la carga de
> mantenimiento perpetuo de cada API asumida explícitamente. Ver ROADMAP F13.

## 6. Infraestructura (todo free-tier)

| Pieza | Decisión | Límite free a vigilar |
|---|---|---|
| DB | **Proyecto Supabase propio** (separado de ZGE) | 500 MB, pausa tras ~1 semana inactivo, 2 proyectos free por cuenta |
| Backend | **Vercel serverless, región gru1/São Paulo** (decisión 2026-07-04; Railway descartado: no tiene región SP) | Plan Hobby = uso no comercial → migrar a plan pago u Oracle Cloud cuando haya clientes facturando |
| Frontend | **GitHub Pages** | Repo público o Pages de repo privado según plan |
| FE AFIP | Servicios web de ARCA | Gratuitos; certificado propio por tenant o emisor |

**Regla de arquitectura multi-tenant**: aislamiento por `tenant_id` (empresa) en todas las tablas + RLS de Supabase como segunda línea de defensa. Un solo esquema, una sola app.

## 7. Modelo de comercialización (futuro)

Suscripción mensual SaaS. Palancas de monetización previstas: módulo de contabilidad activable, cantidad de sucursales/cajas, integraciones premium, nodo LAN para clientes grandes (híbrido posible más adelante).
