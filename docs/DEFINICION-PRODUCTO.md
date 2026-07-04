# ZGC — Definición de Producto

> Resultado del cuestionario de discovery del 2026-07-03 (César + Claude).
> Complementa a `CLAUDE.md` (stack y arquitectura). Este documento define **qué** se construye y **para quién**; el roadmap por fases se deriva de acá.

## 1. Visión

ZGC es un **SaaS multi-tenant** de gestión comercial, contable y de stock para comercios argentinos, sucesor web del legacy RevoSolution. Una sola instancia en la nube sirve a todos los clientes (cada tenant = una empresa con N sucursales y N puntos de venta), con costo marginal por cliente cercano a cero — condición necesaria del modelo: **infraestructura 100% free-tier hasta que haya clientes pagando**.

Es un **producto independiente** del ecosistema ZARIS (repo, DB y auth propios). Comparte patrones y experiencia de ZGE, no infraestructura lógica.

## 2. Mercado objetivo

Los cuatro segmentos del legacy, con una sola base de código:

| Segmento | Qué usa intensivamente |
|---|---|
| Comercio minorista chico | POS simple, stock, caja |
| Supermercado / autoservicio | POS con pesables, envases, departamentos, multi-caja |
| Distribuidora / mayorista | Listas de precios, viajantes/comisiones, cta. cte., remitos |
| PyME comercio/servicios | Facturación electrónica, cta. cte., bancos/cheques |

**Primeros usuarios: ex clientes RevoSolution** — se les migran sus datos DBF con una **herramienta interna** (`tools/`, onboarding asistido por César, no autoservicio). La migración es pieza estratégica del go-to-market.

## 3. Alcance del MVP

El corazón del MVP es el **ciclo comercial completo en versión simple**:

- **Artículos y stock**: maestro (basado en el esquema legacy: 4 listas de precios con márgenes, código de barras, familias/subfamilias), movimientos, depósitos.
- **Precios en dólares desde el MVP**: artículos `en_dolares` + cotización del día (crítico para electrónica/repuestos/importados).
- **Clientes / Ventas**: presupuestos, facturación, cobranzas, cuenta corriente.
- **Proveedores / Compras**: facturas de compra, pagos, cuenta corriente.
- **Caja**: movimientos y planilla diaria.
- **Facturación electrónica ARCA/AFIP desde el MVP**: pyafipws (WSAA + WSFEv1), homologación primero. Comprobantes A/B/C con CAE + QR.
- **POS mostrador web**: pantalla de venta rápida en navegador — lector de código de barras USB (emula teclado, costo cero) e impresión térmica de tickets. Sin pesables/envases todavía.
- **IVA**: libros de IVA ventas/compras (el contador externo es el usuario indirecto).

### Explícitamente FUERA del MVP (fases posteriores)

| Capacidad | Nota de diseño para no cerrarse la puerta |
|---|---|
| Nodo de sucursal LAN (facturar sin internet) | UUIDs en origen, `sucursal_id` en todo, colas de sync — ya en CLAUDE.md |
| POS supermercado (pesables, envases, venta por depto., supervisor) | Los flags ya existen en el esquema de artículos |
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

## 6. Infraestructura (todo free-tier)

| Pieza | Decisión | Límite free a vigilar |
|---|---|---|
| DB | **Proyecto Supabase propio** (separado de ZGE) | 500 MB, pausa tras ~1 semana inactivo, 2 proyectos free por cuenta |
| Backend | **Railway, junto a ZGE** (servicio adicional) | Consumo compartido del plan existente |
| Frontend | **GitHub Pages** | Repo público o Pages de repo privado según plan |
| FE AFIP | Servicios web de ARCA | Gratuitos; certificado propio por tenant o emisor |

**Regla de arquitectura multi-tenant**: aislamiento por `tenant_id` (empresa) en todas las tablas + RLS de Supabase como segunda línea de defensa. Un solo esquema, una sola app.

## 7. Modelo de comercialización (futuro)

Suscripción mensual SaaS. Palancas de monetización previstas: módulo de contabilidad activable, cantidad de sucursales/cajas, integraciones premium, nodo LAN para clientes grandes (híbrido posible más adelante).
