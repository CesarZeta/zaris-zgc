# ZGC — Roadmap por Fases

> Derivado de `DEFINICION-PRODUCTO.md` (discovery 2026-07-03). Principio rector de César:
> **"El cliente es el núcleo del sistema"** — la base de entidades comerciales es el core;
> todo lo demás lo rodea de un modo comercial. Las fases son verticales: cada una entrega
> algo usable, y los módulos se van integrando sobre el núcleo.

## Principio de arquitectura: Base Única de Entidades (BUE)

Análogo a la BUC de ZGE: toda persona física o jurídica (cliente, proveedor, vendedor,
transportista, contacto) existe **una sola vez** en `entidades`, con sus datos maestros
(razón social/nombre, CUIT/DNI, condición IVA, domicilios, teléfonos, emails, contactos).
Los **roles comerciales** (`clientes`, `proveedores`, `vendedores`, `transportistas`) son
tablas satélite que referencian `id_entidad` y agregan solo lo específico del rol
(lista de precios, condición de venta, límite de crédito, comisión, etc.).

- **Prohibido**: duplicar datos maestros de personas en tablas de rol.
- Una misma entidad puede ser cliente Y proveedor sin duplicarse.
- Todo lleva `tenant_id` (multi-tenant) — RLS de Supabase como segunda defensa.

---

## FASE 0 — Fundaciones ✅ (en curso)

**Entregable: repo funcionando con backend y frontend esqueleto, deployables.**

- [x] CLAUDE.md (stack, arquitectura), DEFINICION-PRODUCTO.md, esquema legacy extraído
- [ ] Repo git inicializado, estructura `backend/` + `web-app/` + `sql/` + `docs/` + `tools/`
- [ ] Backend FastAPI esqueleto (`/health`, config por entorno, CORS)
- [ ] Frontend React/Vite esqueleto
- [ ] Proyecto Supabase propio (crear al comenzar Fase 1, para no gastar la ventana de pausa free-tier sin esquema)
- [ ] Deploy inicial: Railway (backend) + GitHub Pages (frontend)

## FASE 1 — Núcleo: Tenants, Usuarios y Base Única de Entidades

**Entregable: puedo dar de alta mi empresa, mis usuarios y mi cartera de clientes completa.**

- Modelo multi-tenant: `tenants` (empresas), `sucursales`, `usuarios` + auth JWT (patrón ZGE: bcrypt directo, sin passlib) + roles/permisos por módulo
- **BUE**: `entidades` + domicilios/contactos, validación CUIT/DNI (dígito verificador), condición IVA
- Rol **cliente**: lista de precios asignada, condición de venta, límite de crédito, zona, viajante, estado (activo/bloqueado)
- Tablas de referencia: provincias, zonas, condiciones de venta, transportistas (rol)
- Pantallas: alta/edición/búsqueda de clientes (búsqueda multi-campo digits-only como la BUC de ZGE)
- Migrador v1 en `tools/`: importa CLIENTES.DBF del legacy a la BUE

## FASE 2 — Artículos y Stock

**Entregable: catálogo completo cargado (o migrado) y stock confiable.**

- Familias/subfamilias, marcas, unidades
- Maestro de artículos: código interno + código de barras, 4 listas de precios con márgenes, tasa IVA por artículo, **precios en USD + cotización** (decisión MVP), flags previstos del POS super (pesable, envase, venta por depto. — sin funcionalidad todavía)
- Depósitos, movimientos de stock (kardex), ajustes
- Cambio masivo de precios (porcentual / por margen), import desde Excel
- Migrador v2: ARTICULO.DBF + FAMILIAS + STOCK

## FASE 3 — Ventas y Facturación Electrónica

**Entregable: facturo con CAE real a mis clientes y llevo su cuenta corriente.**

- Presupuestos → facturas/NC/ND (A/B/C según condición IVA emisor/receptor)
- **pyafipws**: WSAA + WSFEv1 en homologación → producción; comprobante PDF con QR ARCA
- Cuenta corriente de clientes, cobranzas (recibos), vencimientos, saldos
- Numeración por punto de venta; comprobantes internos (presupuesto, remito) con numeración propia
- Listados: ventas, cobranzas, saldos, morosidad

## FASE 4 — Compras y Proveedores

**Entregable: registro compras, actualizo stock y costos, pago a proveedores.**

- Rol **proveedor** sobre la BUE
- Facturas/NC/ND de compra (carga manual), remitos de proveedor, actualización de costo y stock
- Cuenta corriente de proveedores, órdenes de pago, vencimientos
- Comparativo de precios por proveedor (feature querida del legacy)

## FASE 5 — Caja e IVA

**Entregable: cierro la caja del día y le entrego los libros al contador.**

- Conceptos de entrada/salida, movimientos de caja, planilla de caja diaria por sucursal
- Libros de IVA ventas y compras, resumen de retenciones (registro básico), export CITI
- Export para contador (Excel/CSV)

## FASE 6 — POS Mostrador Web (cierra el MVP)

**Entregable: una caja vendiendo rápido con lector e impresora térmica.**

- Pantalla de venta rápida (teclado-first): lector código de barras USB, multiplicador, búsqueda
- Medios de pago (efectivo, tarjeta, Mercado Pago manual), factura B/ticket con CAE
- Impresión térmica 58/80mm (diálogo del navegador; evaluar QZ Tray)
- Autorización de supervisor para anulaciones (patrón legacy)
- Arqueo simple de caja por cajero

---

## POST-MVP (orden tentativo, a repriorizar con feedback de pilotos)

| # | Fase | Contenido |
|---|---|---|
| 7 | Dashboard + móvil | Indicadores en tiempo real, experiencia responsive del dueño |
| 8 | Cheques y Bancos | Cartera de cheques, cuentas bancarias, conciliación, import extractos |
| 9 | Vendedores y comisiones | Liquidación por venta / por cobranza |
| 10 | POS Supermercado | Pesables, envases, venta por departamento, multi-caja |
| 11 | Contabilidad (módulo activable) | Plan de cuentas, asientos automáticos, libro diario, balances |
| 12 | Integraciones | Mercado Pago QR, WhatsApp, e-commerce, nodo LAN de sucursal |
| 13 | Portal de clientes + IA | Autogestión cta. cte./pedidos; reposición sugerida, anomalías, NL queries |

## Reglas de ejecución

1. Cada fase termina con demo usable y datos migrables del legacy cuando aplique.
2. El esquema PostgreSQL de cada fase se diseña mirando `docs/legacy/esquema-dbf.md` — no inventar de cero lo que el legacy ya resolvió en 20 años de uso real.
3. Nada de infraestructura paga. Si un límite free-tier aprieta, se documenta y se decide con César.
4. Los diferenciales (dashboard, IA, portal) no se adelantan: primero paridad útil con el legacy.
