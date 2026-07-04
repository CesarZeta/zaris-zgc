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

## FASE 0 — Fundaciones ✅ (completada 2026-07-03, salvo deploy)

**Entregable: repo funcionando con backend y frontend esqueleto, deployables.**

- [x] CLAUDE.md (stack, arquitectura), DEFINICION-PRODUCTO.md, esquema legacy extraído
- [x] Repo git + GitHub (`CesarZeta/zaris-zgc`, público), estructura `backend/` + `web-app/` + `sql/` + `docs/` + `tools/`
- [x] Backend FastAPI (`/health` verificado, config por entorno con `ENV_FILE`)
- [x] Frontend React/Vite (build verificado)
- [ ] **PENDIENTE**: proyecto Supabase en la cuenta NUEVA de César (el free tier de la cuenta principal está lleno: ZGE + news-bot). César crea el proyecto `zaris-zgc` en sa-east-1 y pasa la connection string → replicar migraciones 001 y 002.
- [ ] **PENDIENTE**: deploy Railway (backend) + GitHub Pages (frontend)

## FASE 1 — Núcleo: Tenants, Usuarios y BUE ✅ (completada 2026-07-04)

**Entregable: puedo dar de alta mi empresa, mis usuarios y mi cartera de clientes completa.** ✔ demostrado con datos reales.

- [x] Multi-tenant: `tenants`, `sucursales`, `usuarios` + auth JWT (migración 001; bcrypt directo, patrón ZGE). Permisos por módulo: pendiente para cuando haya más módulos.
- [x] **BUE**: `entidades` + contactos, validación CUIT/DNI con dígito verificador, condición IVA (migración 002)
- [x] Rol **cliente** completo + catálogos (provincias ARCA, zonas, condiciones de venta). Viajante/transportista quedan como nota de migración hasta sus fases.
- [x] API clientes/entidades con búsqueda multi-campo digits-only (patrón BUC) — 10 pruebas en vivo
- [x] Frontend: login + shell + módulo Clientes (estilo «ZARIS Heredado») — verificado E2E en navegador
- [x] Migrador CLIENTES.DBF (`tools/migrar_clientes.py`) — calibrado con recon de datos reales y verificado adversarialmente; Omni migrado (434 clientes)

### Estado del entorno dev (para retomar)

- DB local: `zgc_dev` en PostgreSQL 17 (127.0.0.1:5432). Migraciones 001+002+003 aplicadas (ver HISTORIAL_MIGRACIONES.md).
- Usuarios dev: `admin@zgc.dev` / `123456` (tenant "Empresa Demo SRL") · `omni@zgc.dev` / `123456` (tenant "Omni (prueba)", 434 clientes migrados) · `super@zgc.dev` / `123456` (tenant "Super (prueba)", 12.208 artículos migrados).
- Correr backend: `cd backend; $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe -m uvicorn app.main:app --port 8021`
- Correr frontend: `cd web-app; npm run dev` → http://localhost:5173 (proxy `/api` → 8021)

## FASE 2 — Artículos y Stock ✅ (completada 2026-07-04)

**Entregable: catálogo completo cargado (o migrado) y stock confiable.** ✔ demostrado con los 12.208 artículos reales de Super.

- [x] Familias/subfamilias, marcas, unidades (catálogos por tenant, alta rápida desde el form)
- [x] Maestro de artículos: código interno + código de barras, 4 listas de precios con márgenes (cálculo bidireccional costo↔margen↔precio, con costo con/sin IVA), tasa IVA por artículo, **precios en USD + cotización** (tabla `cotizaciones` con historia; widget en UI), flags del POS super (pesable, envase retornable + vínculo a artículo envase, venta por depto. — sin funcionalidad todavía)
- [x] Depósitos, saldos por depósito (`articulo_stock`), kardex (`stock_movimientos` con `saldo_resultante` sellado), ajustes por recuento o delta, transferencias interdepósito (dos patas atadas por `grupo_id`, locks ordenados)
- [x] Cambio masivo de precios (3 modos: % precios / % costo / fijar margen; filtros por familia/marca/texto; vista previa dry-run) + import desde Excel (upsert por código, catálogos on-the-fly, savepoint por fila)
- [x] Migrador v2 (`tools/migrar_articulos.py`): ARTICULO.DBF + FAMILIAS + SUBFLIA + DEPOSITO + STOCK. Calibrado con recon de Super (encoding por LDID: cp1252 vs cp850; COSTIVA 1/2; UNIDAD sucia; precios literales; stock solo con contenido) y verificado adversarialmente (sumas al centavo, muestra de 30). Idempotente.
- [x] API verificada con 44 pruebas en vivo (incl. aislamiento de tenant); frontend verificado E2E en navegador.
- Nota: campos legacy diferidos con trazabilidad en observaciones: proveedor (Fase 4), unidad de compra/coeficiente (Fase 4), bonificaciones por lista, cuenta contable (módulo Contabilidad).

## FASE 2.5 — Rubros y Variantes de artículos (multipropósito)

**Entregable: una tienda de ropa carga su catálogo con talles y colores; un tenant elige su rubro y el sistema se adapta.**

> Mandato de César 2026-07-04: gestión central general con customización por rubro;
> POS full orientados al rubro. Diseño completo en `DISENO-RUBROS-Y-VARIANTES.md`
> (con estadística CACE 2025 / global 2026 y evaluación categoría por categoría).
> Va ANTES de Ventas porque las líneas de comprobante referencian variantes.

- Switch de rubro por tenant (`tenants.rubro`): presets de UI, flags visibles, atributos sugeridos y POS objetivo — sin bifurcar el modelo de datos
- Atributos por tenant (Talle, Color, Gusto, Capacidad...) con valores ordenados
- Variantes: combinación de hasta 3 atributos con EAN propio, stock propio y diferencial de precio; artículo sin variantes sigue igual que hoy
- `variante_id` nullable en `articulo_stock` y `stock_movimientos`
- Frontend: grilla matriz talle×color (carga y stock), alta masiva de combinaciones, presets por rubro
- Diferido documentado: serie/IMEI, lote/vencimiento, modificadores de resto, equivalencias de repuestos

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
