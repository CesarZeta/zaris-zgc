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
- [x] Proyecto Supabase `zaris-zgc` en la cuenta NUEVA de César, **sa-east-1** (2026-07-04). Migraciones 001-005 aplicadas, RLS deny-all en las 21 tablas, seed prod (tenant "ZARIS (principal)" + admin de César). Conexión SIEMPRE por session pooler (:5432, IPv4) o transaction pooler (:6543, serverless).
- [x] Deploy (2026-07-04): backend en **Vercel serverless región gru1/São Paulo** (`https://zaris-zgc-api.vercel.app` — Railway se descartó: no tiene región SP; proyecto `zaris-zgc-api`, cuenta Vercel de César, env vars en el proyecto) + frontend en **GitHub Pages** (`https://cesarzeta.github.io/zaris-zgc/`, workflow `deploy-pages.yml`, variable de repo `API_URL`). Login E2E online verificado. Pendiente menor: purga de commits huérfanos en GitHub (recrear repo — decisión de César).

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
- Correr backend: `cd backend; $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe -m uvicorn app.main:app --port 8021` — **sin `--reload`: reiniciar el proceso tras cada cambio de código** (o las pruebas pegan contra código viejo).
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

## FASE 2.5 — Rubros y Variantes de artículos (multipropósito) ✅ (completada 2026-07-04)

**Entregable: una tienda de ropa carga su catálogo con talles y colores; un tenant elige su rubro y el sistema se adapta.** ✔ verificado E2E (Empresa Demo SRL como tienda de indumentaria).

> Mandato de César 2026-07-04: gestión central general con customización por rubro;
> POS full orientados al rubro. Diseño completo en `DISENO-RUBROS-Y-VARIANTES.md`
> (con estadística CACE 2025 / global 2026 y evaluación categoría por categoría).
> Fue ANTES de Ventas porque las líneas de comprobante referencian variantes.

- [x] Switch de rubro por tenant (`tenants.rubro`, migración 004): 6 rubros con presets de UI y siembra idempotente de atributos sugeridos (indumentaria: Talle XS–XXL + Color) — sin bifurcar el modelo de datos. Página Configuración en el frontend.
- [x] Atributos por tenant (Talle, Color, Gusto, Capacidad...) con valores ordenados, alta rápida desde el form
- [x] Variantes: combinación de hasta 3 atributos (unique NULLS NOT DISTINCT), EAN propio (unicidad cruzada artículo↔variante en ambos sentidos), sufijo SKU autogenerado, diferencial de precio, activo
- [x] `variante_id` nullable en `articulo_stock` y `stock_movimientos`: si el artículo tiene variantes activas, ajustes/transferencias/kardex exigen variante; sin variantes, opera igual que siempre (los 12.208 artículos migrados intactos)
- [x] Frontend: chips de valores + "Generar combinaciones" (producto cartesiano idempotente), tabla de variantes con EAN/dif/stock editables inline, selector de variante en ajustes y transferencias, chips de variante en stock y kardex, flags de súper ocultos según rubro
- [x] Verificado: 35 pruebas de API en vivo + E2E en navegador (rubro, generación 3×2, XXL/Rojo desde la UI, stock por variante)
- Diferido documentado: serie/IMEI, lote/vencimiento, modificadores de resto, equivalencias de repuestos

## FASE 3 — Ventas y Facturación Electrónica 🔶 (código completo 2026-07-04; falta homologación real)

**Entregable: facturo con CAE real a mis clientes y llevo su cuenta corriente.**

> Diseño de cumplimiento normativo en `docs/FACTURACION-ARCA.md` (normativa verificada
> al 2026-07-04: RG 5616 obligatoria desde 1/9/2026 — ZGC la envía siempre —, Ley 27.743
> transparencia fiscal, RG 5700 umbral CF, RG 4892 QR, RG 5003 letra A a monotributistas).

- [x] Presupuestos → facturas/NC/ND con letra A/B/C calculada por el sistema (matriz
  emisor × receptor); comprobantes internos X (presupuesto/remito/recibo, RG 1415)
- [x] Circuito borrador → emitir → inmutable; fiscal emitido se revierte SOLO con NC
  espejo (auto-imputada contra la factura); remito/presupuesto anulables con reversión de stock
- [x] Cliente ARCA propio (WSAA firma CMS + WSFEv1 SOAP via httpx/cryptography — decisión
  documentada en FACTURACION-ARCA.md §9: pyafipws arrastra deps incompatibles con Vercel).
  Modos por tenant: deshabilitado / **simulado** (CAE prueba marcado) / homologación / producción.
  Numeración fiscal la manda ARCA (`FECompUltimoAutorizado`+1); `FECompConsultar` ante timeout.
- [x] Cuenta corriente: saldos por comprobante, recibos con medios de pago + imputaciones
  (parciales, a cuenta, crédito de NC), vencimientos por condición de venta, saldos/morosidad-lite
- [x] Stock: la factura/remito descarga (por variante si corresponde), la NC devuelve —
  kardex sellado con el número de comprobante
- [x] Impresión HTML (RG 1415): letra + cód. ARCA, CAE+vto, QR RG 4892 (solo CAE real),
  bloque transparencia fiscal Ley 27.743 en B/C a CF, leyendas X y PRUEBA
- [x] Frontend módulo Ventas (tabs Comprobantes/Cobranzas/Ctas. ctes.) + config ARCA y
  puntos de venta en Configuración — verificado E2E en navegador
- [x] Migración 006 + 66 pruebas de API en vivo (0 fallos)
- [x] Deploy a producción (2026-07-05): migración 006 + 005 en Supabase (las corrió César
  por SQL Editor), backend Vercel (`npx vercel deploy --prod`), Pages redeployado.
  Gotcha registrado: las deps del backend van TAMBIÉN en `api/requirements.txt` (es el
  que instala Vercel).
- [ ] **Homologación real** (diferido por César 2026-07-05, no bloquea): generar certificado
  con Clave Fiscal (pasos en FACTURACION-ARCA.md §8), cargarlo en Configuración → ARCA y
  probar contra wswhomo; después producción. Mientras tanto, modo simulado.
- Diferido documentado: moneda DOL en factura (se convierte con cotización), percepciones
  (`ImpTrib`), FCE MiPyME, CAEA, remito R con CAI (el X de ZGC no vale para traslado)

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
