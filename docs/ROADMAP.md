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
- Correr backend: `cd backend; $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe -m uvicorn app.main:app --port 8021` — **sin `--reload`: reiniciar el proceso tras cada cambio de código** (o las pruebas pegan contra código viejo). Al arrancar sesión, **matar primero cualquier proceso viejo en 8021** (`Get-NetTCPConnection -LocalPort 8021` → `Stop-Process`): un backend zombie responde `/health` OK con código stale.
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

## FASE 4 — Compras y Proveedores ✅ (en producción 2026-07-05)

**Entregable: registro compras, actualizo stock y costos, pago a proveedores.** ✔ verificado con 61 pruebas de API en vivo (0 fallos, kardex al centavo) + E2E en navegador.

- [x] Rol **proveedor** sobre la BUE (migración 007): satélite de `entidades` — una entidad
  puede ser cliente Y proveedor sin duplicarse (probado en vivo). Condición de pago
  habitual reusa el catálogo `condiciones_venta` (plazos genéricos, como el legacy).
- [x] Facturas/NC/ND de compra + remitos de proveedor (COMPRASM/D y REMITOPM/D del legacy):
  carga manual del documento AJENO — letra y punto de venta/número del papel, sin ARCA.
  **Letra A: costos netos + IVA discriminado; B/C: importes finales** (IVA no computable
  al costo). Percepciones IVA/IIBB, imp. internos, otros y `redondeo` (calza con el papel)
  en cabecera; `periodo_iva` sellado para el libro de compras de Fase 5. Duplicados
  bloqueados por (proveedor, tipo, PV, número). Circuito: borrador → registrar (stock +
  costos + cta. cte. + vencimientos) → anulable con reversión mientras no tenga pagos.
- [x] Costos al registrar factura: `articulos.costo` en su convención con/sin IVA (COSTIVA),
  upsert de `articulo_proveedores` (lista neta + bonifs en cadena + última compra) y
  proveedor habitual si no tenía. La anulación NO revierte costos (puede haber compras
  posteriores; se corrige desde Artículos).
- [x] Cta. cte. de proveedores: saldos por compra, **órdenes de pago** (numeración interna
  OP-nnnnnnnn por tenant) con medios + imputaciones (parciales, a cuenta, crédito de NC
  auto-imputada contra su factura), cuenta corriente debe/haber, saldos por proveedor y
  **cuentas a pagar** (vencimientos por condición, vencidas marcadas).
- [x] **Comparativo de precios por proveedor** (ART_PROV, feature querida del legacy):
  costo neto tras bonifs en cadena, mejor precio primero, chip de habitual, carga manual
  de listas sin esperar una compra.
- [x] Frontend: módulo Proveedores (BUE, drill-down a artículos que provee) + módulo Compras
  (tabs Comprobantes / Pagos / Ctas. ctes. / Comparativo) — verificado E2E en navegador.
- [x] Deploy a prod (2026-07-05): migración 007 en Supabase (SQL Editor, la corrió César),
  backend Vercel y Pages redeployados. Smoke test E2E contra prod OK (tenant aislado
  "Smoke Test ZGC" + usuario smoke@zgc.test: login, alta proveedor BUE, endpoints de
  compras/pagos vivos contra las tablas de la 007).
- [x] Migrador PROVEEDO.DBF / ART_PROV (2026-07-05): `tools/migrar_proveedores.py`, espejo de
  migrar_clientes (BUE cross-rol: si el CUIT ya existe, el rol proveedor se cuelga de esa
  entidad). Censo y calibración en `docs/legacy/recon-proveedores.md`. Verificado E2E en dev
  con eVARISTORE (63 proveedores, 1.885 filas de comparativo, 2.381 proveedores habituales,
  idempotente); también completa `articulos.proveedor_habitual_id` desde ARTICULO.DBF.
- Diferido documentado: retenciones practicadas en la OP (RET_PROV → registro básico en
  Fase 5), unidad de compra/coeficiente, factura M, importaciones (despacho/aduana).

## FASE 5 — Caja e IVA ✅ (en producción 2026-07-05)

**Entregable: cierro la caja del día y le entrego los libros al contador.**

- [x] Migración 008 (espejo del legacy CONC_CAJ/MOVIM/SALCAJA/RET_CLI/RET_PROV):
  `conceptos_caja`, `caja_movimientos` (solo manuales; tipo sellado del concepto),
  `caja_cierres` (totales sellados + arqueo, unique por fecha/sucursal y global),
  `retenciones` (sufrida=cliente/recibo, practicada=proveedor/OP, CHECK cruzado),
  `codigo_arca` en tipos_comprobante_compra. Los libros de IVA y la planilla NO
  tienen tabla: son reportes regenerables (como el _ADMINC del legacy).
- [x] Caja: conceptos entrada/salida (alta/rename/inactivar, unicidad por tenant),
  movimientos manuales por medio, **planilla diaria** por sucursal o global (ventas
  contado ± NC + cobranzas por medio + pagos por medio + manuales; saldo = solo
  efectivo), cierre con arqueo (`diferencia = contado − saldo_final`) que bloquea
  altas/bajas de esa fecha; reabrible borrando el cierre.
- [x] Libros de IVA ventas (comprobantes emitidos fiscales, NC en negativo, totales
  por alícuota) y compras (por `periodo_iva` sellado con fallback a fecha; letra A
  con crédito fiscal por tasa, B/C a no gravado sin crédito — IVA al costo).
- [x] Retenciones registro básico: alta/baja con referencias validadas por tenant,
  resumen por tipo/régimen, CSV.
- [x] Exports para el contador: CSV separador `;` decimales con coma UTF-8 BOM
  (Excel es-AR directo) y **CITI RG 3685**: ZIP con los 4 TXT de ancho fijo
  (ventas cbte 266 / alícuotas 62, compras cbte 325 / alícuotas 84) — best-effort
  documentado, el contador valida antes de presentar.
- [x] Frontend: módulo Caja (tabs Planilla del día / Movimientos / Conceptos +
  cierre con arqueo) y módulo Libros IVA (tabs IVA Ventas / IVA Compras /
  Retenciones / Exportar con descargas autenticadas).
- [x] Verificado 2026-07-05: 48 pruebas de API en vivo en dev (0 fallos reales;
  incluye anchos CITI, coherencia de totales, aislamiento de tenant y bloqueo por
  caja cerrada) + E2E en navegador (planilla coherente, libros con datos reales).
- [x] Deploy a prod (2026-07-05): migración 008 + re-aplicación de la 005 en Supabase
  por psql via session pooler (Claude, con la password que pasó César en el chat →
  `pgpass.conf`), backend Vercel (`npx vercel deploy --prod`) y Pages redeployados.
  Smoke E2E contra prod OK: 24/24 con tenant efímero "Smoke Fase 5 ZGC" (login,
  ciclo de caja completo con arqueo/diferencia, libros vacíos coherentes, CSV+CITI,
  retenciones) — tenant creado y eliminado en la misma corrida.
- Diferido documentado: percepciones de ventas en el libro (el modelo de ventas
  aún no las discrimina — `ImpTrib` diferido de Fase 3), sucursal en OP (entran
  solo en planilla global), export Excel nativo (.xlsx; el CSV lo cubre).

## FASE 6 — POS Mostrador Web ✅ (cierra el MVP — en producción 2026-07-05)

**Entregable: una caja vendiendo rápido con lector e impresora térmica.** ✔ verificado con 42 pruebas de API en vivo (0 fallos) + regresión Fase 3 + E2E en navegador.

- [x] Migración 009: `pos_cajas` (config por caja: PV que factura, depósito, lista de
  precios, ancho ticket 58/80), `pos_sesiones` (turno de cajero: apertura con fondo →
  cierre con totales sellados; una abierta por caja/cajero), `venta_medios` (medios por
  venta contado — el hueco que la planilla de Fase 5 dejó documentado) y
  `comprobantes.pos_sesion_id`. RLS en las 3 tablas nuevas.
- [x] La venta POS es una factura fiscal de Fase 3 (misma tabla, mismo circuito
  ARCA/stock/cta.cte.) emitida en un paso: `POST /pos/ventas/calcular` (dry-run con el
  total EXACTO, redondeo fiscal por alícuota) → `POST /pos/ventas` (factura + CAE +
  stock + medios + sesión en una transacción; los medios deben sumar el total). El
  cajero no elige precios ni letra: precios de servidor (lista de la caja, finales con
  IVA, + diferencial de variante, × cotización si USD), letra por matriz (CF→B; cliente
  identificado F3 → A si corresponde). Refactor: `emitir_core`/`crear_nc_espejo_core`
  compartidos con los endpoints de gestión (regresión F3 verificada).
- [x] Búsqueda de mostrador `GET /pos/buscar`: EAN de variante → cód. barras → código
  interno (exactos) → texto; precio ya resuelto por caja. Multiplicador `3*` en el front.
- [x] Anulación con autorización de SUPERVISOR (patrón legacy): credenciales + nivel
  (`nivel_acceso <= 2`, semántica ZGE 1=admin/2=supervisor) → NC espejo fiscal emitida
  en el acto, stock devuelto, medios de la venta original en negativo en el arqueo.
  Gotcha cazado en E2E: credencial de supervisor inválida responde **403** (un 401
  dispara el "sesión vencida" global del front y desloguea la caja).
- [x] Arqueo por cajero: resumen vivo (tickets, anulaciones, ventas por medio, efectivo
  teórico = fondo + efectivo neto) y cierre que sella totales + `diferencia = contado −
  teórico`. La planilla de caja (F5) ahora discrimina `ventas_por_medio` (las ventas
  sin medios registrados siguen asumidas efectivo).
- [x] Frontend `/pos` fuera del shell (pantalla completa de caja, teclado-first):
  apertura con fondo, escaneo con Enter (lector USB emula teclado), multiplicador,
  picker de variantes, F3 cliente / F6 tickets+reimpresión+anulación / F8 cierre /
  F10 cobrar, modal de cobro con medios múltiples y vuelto. Cajas POS se administran
  en Configuración.
- [x] Ticket térmico 58/80mm (`ticket.ts`): layout angosto con CUIT/PV-número/CAE/
  vto/QR (solo CAE real), transparencia fiscal Ley 27.743 en B/C a CF, leyenda de
  simulado, medios y vuelto — vía diálogo de impresión del navegador. **QZ Tray
  evaluado y diferido**: el diálogo nativo cubre el MVP; QZ (impresión silenciosa)
  queda para cuando un piloto lo pida (agrega firma digital + instalación local).
- [x] Deploy a producción (2026-07-05): migración 009 + 005 re-aplicada en Supabase
  (psql via pooler, corrida por César en sesión paralela; RLS=t verificado en las 3
  tablas), backend Vercel (`/pos/cajas` responde en prod) y Pages (workflow OK;
  verificado que el bundle publicado contiene el POS). Click-through del POS en prod
  logueado: pendiente de César (DEPLOY.md § Verificaciones pendientes).
- Diferido documentado: pesables por etiqueta de balanza, envases, venta por depto.
  (POS Súper, fase 12), descuento por línea/venta en el POS (el backend ya lo soporta
  vía `descuento_pct`), identificación CF ≥ umbral RG 5700 la exige el backend (422).

## FASE 6.5 — Usuarios, Roles y Permisos por módulo (RBAC)

**Entregable: cada tenant administra sus usuarios, define roles y controla qué módulo puede ver/editar/anular cada uno.**

> Discovery 2026-07-05 (César). Diseño completo en `docs/DISENO-USUARIOS-Y-PERMISOS.md`
> — leerlo antes de implementar. Va **después del POS** (no lo frena) y **antes** del
> POST-MVP porque es transversal: todo módulo futuro debe nacer con guardas.

- Modelo **roles + permisos por módulo**, granularidad **Ver / Editar / Anular** (acumulativas).
- Migración 010: `roles`, `rol_permisos`, `usuarios.rol_id` + backfill (usuarios actuales → rol `admin`, no rompe nada de hoy) + seed de 5 roles base por tenant (admin, gerente, cajero, vendedor, consulta).
- Backend: guarda declarativa `requiere(modulo, accion)` (dependency FastAPI) aplicada a los endpoints de escritura/anulación de los 10 módulos; `rol_id` en el JWT.
- Frontend: gestor en Configuración (usuarios + roles + matriz de permisos) + sidebar filtrado por permisos.
- Convive con `nivel_acceso` del POS sin tocarlo (aditivo). Sin permisos que migrar del legacy (`PERMISOS.DBF` tiene 0 registros; solo sembrar roles base).
- Smoke E2E: crear rol limitado, asignarlo, verificar 403 en backend y sidebar recortado.

## LOTE TÉCNICO — Optimización de endpoints y consistencia de UI (auditoría 2026-07-05)

**Entregable: la misma app, más rápida y más consistente — sin features nuevas.**

> Sesión de diseño 2026-07-05: auditoría completa del backend (18 routers + 9
> migraciones) y del frontend (36 componentes). Veredicto: la base es sana
> (paginación server-side en todos los listados, sin N+1 groseros, sistema visual
> coherente) — esto es afinado, no rescate. No bloquea a la 6.5 ni depende de ella;
> puede hacerse antes, junto o inmediatamente después. Detalle completo de hallazgos
> con archivo:línea en la transcripción de esa sesión.

- [ ] **Migración de índices de performance** (todos `CREATE INDEX IF NOT EXISTS`,
  segura de aplicar sola): `comprobante_items(comprobante_id)` y
  `compra_items(compra_id)` — los selectin de items no pueden usar los índices
  actuales `(tenant_id, *)` y escanean la tabla en cada listado —; GIN pg_trgm sobre
  `entidades(razon_social)` y `articulos(descripcion)` (búsquedas `ILIKE '%…%'` de
  maestros, typeahead y POS; requiere `CREATE EXTENSION pg_trgm`, disponible en
  Supabase); `recibos(tenant_id, fecha)` y `ordenes_pago(tenant_id, fecha)` +
  `recibo_medios(recibo_id)` / `orden_pago_medios(orden_pago_id)` (planilla de caja);
  parcial `comprobantes(comprobante_asociado_id) WHERE NOT NULL` (anuladas del POS).
  ⚠️ Numeración: la 010 estaba reservada para RBAC en `DISENO-USUARIOS-Y-PERMISOS.md`
  — el que se implemente primero toma el número y el otro doc se corrige.
- [ ] **Backend transversal** (bajo esfuerzo / alto impacto): `deferred()` en
  `Comprobante.arca_request/arca_response` (hoy el XML completo de WSFEv1 viaja en
  CADA select de comprobantes: listados, cta. cte., libros, POS);
  `expose_headers=["X-Total-Count"]` en el CORSMiddleware (hoy la paginación es
  invisible para el browser en ventas/compras/cobranzas/pagos); COUNT de artículos
  sin la subquery de stock_total (hoy suma el stock de todo el catálogo solo para
  contar); N+1 de cajeros en `GET /pos/sesiones`; cta. cte. con filtro de fechas en
  SQL + proyección (hoy carga TODA la historia del cliente con hijos y XML y filtra
  en Python — espejo en pagos); modelos de listado livianos sin items/alícuotas/
  vencimientos para las grillas de comprobantes (payload ~10x menor).
- [ ] **UI prioridad alta**: confirmación antes de descartar un form con datos (hoy
  un click en el backdrop tira una factura de 15 ítems); búsqueda de texto + rango
  de fechas en Ventas y Compras (hoy no se puede encontrar una factura puntual);
  vista de detalle del comprobante emitido (hoy solo se puede imprimir); paginado y
  búsqueda reales en Cobranzas/Pagos (hoy `limit=100` fijo: el recibo 101 desaparece).
- [ ] **UI consistencia**: crear `src/components/` compartidos — `Paginado` (6 copias
  hoy), `Buscador` autocomplete (4 reinventos), `ChipEstado`, `AlertError/Ok`,
  `ConfirmModal`/`PromptModal` (reemplaza los 12 `window.confirm/prompt` nativos que
  rompen la identidad visual) — y `EntidadFields` BUE común a ClienteForm/
  ProveedorForm (~120 líneas duplicadas; agregar ahí validación de CUIT con dígito
  verificador en el cliente). Exponer `condicion_venta_id`/`zona_id` en ClienteForm
  (el form de venta ya los consume y no se pueden cargar).

---

## POST-MVP — ERP-liviano argentino (reordenado 2026-07-05)

> Marco: `DEFINICION-PRODUCTO.md` §1-bis. ZGC crece **HACIA ADENTRO** (finanzas,
> fiscal, sueldos = foso de localización argentina) y **NUNCA hacia afuera**
> (producción/MRP, proyectos, gestión de servicios, localización internacional =
> FUERA PERMANENTE). Gate global: **ningún módulo-foso antes del primer cliente de
> referencia pagando**. Orden re-priorizable con feedback de pilotos, decisiones
> ya tomadas anotadas en cada fila.

| # | Fase | Contenido | Condición de activación |
|---|---|---|---|
| 7 | Dashboard + móvil | Indicadores en tiempo real, responsive del dueño; **export CSV/Excel universal** (base de reportería); **padrón ARCA por CUIT** (autocompletar entidades BUE, validar cond. IVA — quick win del motor fiscal); **domicilios normalizados OSM** (estándar de suite heredado de ZGE: proxy Nominatim + AddressSearch + lat/lon en entidades/sucursales + `entidad_domicilios` — ver `DISENO-LOGISTICA-Y-DOMICILIOS.md` §1; hacerlo ANTES de cargar entidades masivamente); **ABM de sucursales** (la tabla existe desde la 001, falta la UI) + sucursal en cajas POS | Post-MVP inmediato |
| 8 | Cheques y Bancos | Cartera de cheques, cuentas bancarias, conciliación, import extractos; **cash-flow proyectado** (tesorería sobre vencimientos de ventas/compras + cheques) | — |
| 9 | **Contabilidad** (módulo activable) | Plan de cuentas, asientos automáticos desde ventas/compras/caja/OP (ya registran todo), libro diario, balances; **activos fijos + amortizaciones**; **export al software del contador** (formaliza los CSV de F5) | **FOSO** — primer cliente de referencia pagando. *Adelantada de F11→F9 (decisión César 2026-07-05): mejor relación valor/mantenimiento (principios estables), palanca de plan pago, habilita F10* |
| 10 | **Impuestos** | Percepciones en ventas (`ImpTrib`, diferido de F3), retenciones practicadas **automáticas** en OP + certificados (F5 solo registra a mano), export **SICORE/SIRE**, IIBB local y **Convenio Multilateral** (liquidación informativa, SIFERE), **padrones ARBA/AGIP** (alícuota por sujeto) | **FOSO** — cliente pagando con obligaciones de agente o CM + **mantenimiento mensual de padrones comprometido**. Mantenimiento ALTO, riesgo legal medio. Pareja natural de F9 (no la bloquea: opera sobre comprobantes/OP) |
| 11 | Vendedores y comisiones | Liquidación por venta / por cobranza | — |
| 12 | **POS por perfiles** (Súper · Carnicería · Resto) | Diseño 2026-07-05 en `DISENO-POS-PERFILES.md`. **Súper**: pesables por etiqueta de balanza (EAN 20–29, config por tenant), envases retornables, venta por depto., multi-caja. **Carnicería**: NO es un POS distinto — es el **despiece/transformación de stock en gestión** (media res → kilos por corte, con merma y costeo proporcional al valor) + POS estándar con pesables; la transformación es primitiva general (sirve para fraccionar y combos). **Resto** (sucesor de RestoDelivery del legacy): POS propio con salones/mesas/mozos/comandas/propina que viven en tablas `pos_*` — a la gestión llega SOLO la venta final emitida (mandato César); rubro `restaurante` al enum | Demanda ex clientes RevoSolution; por perfil: ≥1 piloto del rubro. Balanza y despiece son **adelantables sueltos** (el despiece es stock puro, no depende del POS) |
| 12-bis | Logística de entregas | Rol transportista (BUE), `entregas` por remito/factura con domicilio snapshot + estados (pendiente→en reparto→entregada/rechazada), **hojas de ruta** imprimibles, rendición del reparto, mapa opcional. Diseño en `DISENO-LOGISTICA-Y-DOMICILIOS.md` §2. Crecimiento hacia adentro (operativiza el remito que ya existe) | Requiere domicilios OSM (F7). Activación: primer cliente que reparte (distribuidora/mayorista/corralón) |
| 13 | Integraciones de canal | **Mercado Libre** (variantes F2.5 ↔ variaciones ML 1:1; atributos estructurados/catálogo, no HTML), Tiendanube/WooCommerce, Mercado Pago QR, WhatsApp, nodo LAN de sucursal | **Canal, no foso** (paridad de mercado). Por integración: ≥2-3 clientes que la pidan; mantenimiento perpetuo de cada API asumido explícitamente |
| 14 | Portal de clientes + IA | Autogestión cta. cte./pedidos; reposición sugerida, anomalías, NL queries | Tracción |
| 15 | **Sueldos y cargas sociales** | Alcance si se construye: legajos, liquidación por convenio, F.931/SICOSS, Libro de Sueldos Digital, ART. **Build-vs-integrar ABIERTO** (ver Decisiones abiertas) | **FOSO MÁXIMO, el más condicional**: F9+F10 maduros + N clientes pagos estables + **asesoría laboral contratada**. Mantenimiento MUY ALTO (paritarias, escalas), riesgo legal ALTO |

### Gaps evaluados 2026-07-05 (clasificación foso / canal / fuera)

| Capacidad | Veredicto |
|---|---|
| BI / reportería propia | **FOSO-light, evolución de F7** — export universal ya, vistas guardadas + envío programado cuando haya plan pago. NO report-builder/cubos propio temprano (mantenimiento alto, free-tier no banca OLAP) |
| Activos fijos / amortizaciones | **IN — dentro de F9** (mantenimiento bajo, paridad SAP B1 ante el contador) |
| Flujo de fondos proyectado | **IN — dentro de F8** (vista de tesorería, no fase propia) |
| Multi-empresa (usuario ↔ N tenants) / consolidación | **IN diferido** — switch de empresa barato cuando haya demanda de estudios contables; consolidación va con Contabilidad/BI |
| Multi-moneda completa (mayor multimoneda) | **OUT salvo demanda de exportadores** — se mantiene precios USD + factura DOL (diferida F3); WSFEX ya estaba fuera |
| Factura recurrente / abonos (Concepto 2/3) | **IN feature menor de Ventas**, gated por pedido de cliente real (el cliente WSFEv1 ya lo soporta parametrizado) |
| Producción/MRP, proyectos/obras, gestión de servicios, localización internacional | **FUERA PERMANENTE** (regla hacia-afuera) |

### Decisiones abiertas (César)

1. **Sueldos: build vs. integrar** — ABIERTA. *Construir*: foso total y captura de plan
   pago, pero mantenimiento perpetuo brutal y responsabilidad legal que exige asesoría
   laboral permanente. *Integrar* (export de novedades al liquidador del contador /
   import de asientos y recibos): ~20% del costo, ZGC sigue siendo el hub, foso menor
   pero suficiente al inicio. Recomendación de Claude: **integrar primero, construir
   solo si el volumen de clientes lo paga**. Se decide recién al activar F15.
2. ~~Prioridad de Contabilidad~~ — **RESUELTA 2026-07-05: adelantada a F9** (era F11).
3. ~~Alcance de "integración fiscal"~~ — **RESUELTA 2026-07-05: ambas** — profundizar
   fiscos nativos (padrón en F7; SIRE/SICORE/padrones en F10; libro IVA digital sobre
   el CITI de F5) **y** export al software del contador (F9).

## Reglas de ejecución

1. Cada fase termina con demo usable y datos migrables del legacy cuando aplique.
2. El esquema PostgreSQL de cada fase se diseña mirando `docs/legacy/esquema-dbf.md` — no inventar de cero lo que el legacy ya resolvió en 20 años de uso real.
3. Nada de infraestructura paga. Si un límite free-tier aprieta, se documenta y se decide con César.
4. Los diferenciales (dashboard, IA, portal) no se adelantan: primero paridad útil con el legacy.
5. **Regla ERP-liviano (2026-07-05)**: crecer hacia adentro (finanzas/fiscal/sueldos),
   nunca hacia afuera (MRP/proyectos/servicios/internacional). Ningún módulo-foso antes
   del primer cliente de referencia pagando, y cada foso con su condición de activación
   cumplida — el mantenimiento perpetuo (padrones, paritarias, APIs de canal) se asume
   explícitamente o el módulo no se construye.
