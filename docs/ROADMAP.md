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

## FASE 6.5 — Usuarios, Roles y Permisos por módulo (RBAC) ✅ (implementada 2026-07-05)

**Entregable: cada tenant administra sus usuarios, define roles y controla qué módulo puede ver/editar/anular cada uno.** ✔ verificado con 62 pruebas de API en vivo (0 fallos) + E2E en navegador.

> Discovery 2026-07-05 (César). Diseño completo en `docs/DISENO-USUARIOS-Y-PERMISOS.md`.

- [x] Modelo **roles + permisos por módulo**, granularidad **Ver / Editar / Anular**
  (acumulativas: fila única por (rol, módulo) con el nivel máximo; ausencia = sin acceso).
- [x] Migración 010: `roles`, `rol_permisos` (con `tenant_id`, convención del proyecto),
  `usuarios.rol_id` + seed de 5 roles base por tenant existente (admin, gerente, cajero,
  vendedor, consulta) + backfill (usuarios actuales → `admin`) + RLS. Para tenants nuevos
  el backend siembra lazy en `GET /roles`. **`rol_id NULL` = acceso total** (compat:
  usuarios creados por scripts/SQL — seeds y smoke tenants siguen funcionando).
- [x] Backend: `app/core/permisos.py` — guarda `requiere(modulo, accion)` + `requiere_alguno`
  (catálogos compartidos: entidades, depósitos, condiciones de venta, puntos de venta) con
  cache TTL 60s por rol; aplicada a los ~118 endpoints de los 15 routers (GET→ver,
  POST/PUT/PATCH→editar, anulaciones/borrados→anular). Config sensible (ARCA, puntos de
  venta, cajas POS) exige `configuracion.editar` aunque viva en otros routers (es donde
  la UI la muestra). `rol_id` en el JWT; login devuelve `permisos` para la UI. **403,
  nunca 401** (regla §6 del CLAUDE.md, verificado: el 403 no desloguea).
- [x] Gestor de Configuración (`/usuarios`, `/roles`, `/permisos/catalogo`): alta/edición
  de usuarios con rol y nivel POS, reset de contraseña (se muestra UNA vez), roles propios
  (crear/clonar de un rol de sistema/editar matriz/eliminar sin usuarios), roles de sistema
  read-only. **Anti-lockout**: ninguna operación deja al tenant sin un usuario activo con
  `configuracion.editar` (422).
- [x] Frontend: sidebar e inicio filtrados por permisos (popover "N de 10" con permisos
  reales), página Configuración con gestor completo y bloqueo por rol.
- [x] Convive con `nivel_acceso` del POS sin tocarlo (sigue gobernando SOLO la
  autorización de supervisor). Sin permisos que migrar del legacy (PERMISOS.DBF vacío).
- [x] Verificado 2026-07-05: 62 pruebas de API en vivo (guardas por rol, matriz, clonado,
  anti-lockout, reset, aislamiento de tenant) + E2E en navegador (alta de usuario rol
  Consulta desde la UI → sidebar recortado, inicio "9 de 10", /configuracion bloqueada,
  POST 403 sin deslogueo).

## LOTE TÉCNICO — Optimización de endpoints y consistencia de UI ✅ (implementado 2026-07-06)

**Entregable: la misma app, más rápida y más consistente — sin features nuevas.** ✔ verificado con 32 pruebas de API en vivo (0 fallos) + build + E2E en navegador.

> Sesión de diseño 2026-07-05: auditoría completa del backend (18 routers + 9
> migraciones) y del frontend (36 componentes). Veredicto: la base es sana —
> esto fue afinado, no rescate.

- [x] **Migración 011 de índices de performance** (`sql/011_indices_performance.sql`,
  solo `CREATE INDEX IF NOT EXISTS` + pg_trgm — segura de aplicar sola):
  `comprobante_items(comprobante_id)` y `compra_items(compra_id)` (los selectin
  emiten `WHERE fk IN (...)` sin tenant); GIN pg_trgm **multicolumna** sobre
  `entidades(razon_social, nombre_fantasia, email)` y `articulos(descripcion,
  codigo, codigo_barras)` — multicolumna porque los filtros son OR y el BitmapOr
  necesita índice en TODAS las ramas (verificado con EXPLAIN ANALYZE: 0,9 ms sobre
  12.208 artículos); `recibos/ordenes_pago(tenant_id, fecha)` +
  `recibo_medios(recibo_id)` / `orden_pago_medios(orden_pago_id)` (planilla);
  parcial `comprobantes(comprobante_asociado_id) WHERE NOT NULL` (anuladas POS).
  `comprobante_alicuotas`/`*_vencimientos` ya estaban cubiertos por sus UNIQUE.
- [x] **Backend transversal**: `deferred()` en `arca_request/arca_response` (el XML
  de WSFEv1 ya no viaja en ningún listado; solo se escribe al emitir);
  `expose_headers=["X-Total-Count"]` en el CORSMiddleware (fix canónico; se
  quitaron los 5 sets manuales por endpoint); COUNT de artículos sin la subquery
  de stock_total; N+1 de cajeros en `GET /pos/sesiones` (un solo SELECT por
  página); cta. cte. de clientes y proveedores con **proyección de columnas +
  fechas en SQL** (misma semántica, verificada por comparación); **listados
  livianos**: `ComprobanteListaOut`/`CompraListaOut` sin hijos + `noload()` (el
  detalle completo va por id); búsqueda `q` en ventas/compras/recibos/OPs
  (texto = AND multi-palabra sobre el nombre; dígitos = número de comprobante).
- [x] **UI prioridad alta**: confirmación antes de descartar forms con datos
  (ComprobanteForm, CompraForm, ReciboModal, OrdenPagoModal, ClienteForm,
  ProveedorForm — flag `modificado`/`hayDatos` + diálogo propio); búsqueda de
  texto (debounce 350 ms) + rango de fechas en Ventas, Compras, Cobranzas y
  Pagos; vista de detalle por id (`ComprobanteDetalle`/`CompraDetalle`: renglones,
  totales, vencimientos, CAE, imprimir); paginado real con `X-Total-Count` en
  Cobranzas/Pagos.
- [x] **UI consistencia** — `src/components/` compartidos: `Paginado`, `Buscador`
  (autocomplete genérico con debounce), `ChipEstado`, `AlertError/AlertOk`,
  `useDialogos` (confirmar/pedirTexto con identidad visual — reemplazó los 20
  `window.confirm/prompt` en 12 archivos; Enter acepta, Escape cancela) y
  `EntidadFields` BUE común a ClienteForm/ProveedorForm con **validación de
  CUIT/CUIL/DNI en el cliente** (espejo de `core/cuit.py`, inline + bloqueo de
  submit). ClienteForm expone `condicion_venta_id` y `zona_id` (endpoints nuevos
  `GET/POST /clientes/zonas` con alta rápida idempotente).

## FASE 7 — Dashboard + calidad de datos (OSM/padrón) + ABM sucursales 🔶 (código completo 2026-07-06)

**Entregable: el dueño ve sus números al entrar, carga entidades con datos limpios (padrón ARCA + domicilios OSM), administra sus sucursales y exporta cualquier listado.** ✔ verificado con 45 pruebas de API en vivo (0 fallos) + regresión + build + E2E en navegador. **Falta el deploy a prod.**

> Primer post-MVP. Las dos patas de calidad de datos (padrón ARCA + OSM) van en el
> mismo formulario de entidad, ANTES de cargar entidades masivamente. Diseño de OSM
> casi textual desde ZGE en `docs/DISENO-LOGISTICA-Y-DOMICILIOS.md §1` (con las 3
> adaptaciones ZGC: User-Agent propio, viewbox opcional por tenant SIN `bounded=1`,
> rate limit adaptado a serverless).

- [x] **Migración 012** (aditiva, idempotente): `entidades`/`sucursales` += lat/lon;
  `sucursales` += provincia_id/codigo_postal (la 001 solo tenía domicilio/localidad);
  `tenants` += geo_centro_lat/lon/delta (sesgo Nominatim opcional); tabla nueva
  `entidad_domicilios` (tipo fiscal/entrega/otro, predeterminado por tipo, snapshot-ready
  para Logística F12-bis) con RLS. Segura de aplicar sola (el backend viejo no la lee).
- [x] **Dashboard KPIs** (`GET /dashboard/kpis`): ventas del mes (fiscales netos de NC),
  cobros pendientes (saldo deudor cta.cte.), stock valorizado (Σ cantidad **positiva** ×
  costo neto — un faltante no resta valor al inventario), saldo de caja del día (efectivo
  neto: cobranzas − pagos + manuales). Cada KPI respeta el permiso de su módulo (null,
  nunca 403, para que el inicio nunca se rompa). Inicio conecta los 4 (skeleton → valores
  reales con formato `Intl` es-AR); `.kpis-grid` responsive (2 columnas en móvil).
- [x] **Padrón ARCA por CUIT** (`GET /padron/{cuit}`, `services/arca/padron.py`): WSAA ya
  era multi-servicio → TA para `ws_sr_constancia_inscripcion`. Modo simulado (registro
  ficticio determinístico, dev/demo sin cert) / homologación / producción (SOAP real,
  patrón espejo de wsfev1). Trae razón social, tipo persona, condición IVA (mapeo de
  impuestos activos), domicilio; mapea provincia del padrón → código ARCA. Botón "ARCA"
  junto al CUIT en `EntidadFields` (habilitado solo con DV válido).
- [x] **Domicilios OSM** (`GET /geo/buscar|reverse`, proxy único, `lib/geo.ts` +
  `AddressSearch.tsx`): debounce 500 ms / mín. 3 chars / 5 sugerencias, filtro de POIs
  (blacklist por `class` + reescritura de display_name), sesgo opcional por tenant
  (`PUT /empresa/geo`, viewbox SIN `bounded=1`). `parseAddress` + mapeo provincia OSM →
  catálogo ARCA. En `EntidadFields` y `SucursalesSection`: criterio BUC (calle/localidad/
  provincia solo desde OSM, readOnly) con escape "cargar a mano" y "quitar pin". Mapa
  Leaflet diferido a Logística (F12-bis) — v1 sin dependencia npm nueva.
- [x] **ABM sucursales** (`sucursales.py`, CRUD calcado del de cajas POS): la tabla existía
  desde la 001 sin UI. Listado consumido por el picker de sucursal en cajas POS (nuevo
  select) y disponible para usuarios. `SucursalesSection` en Configuración con el mismo
  AddressSearch. Sin DELETE (se desactivan: usuarios/cajas/movimientos las referencian).
- [x] **Domicilios múltiples de entidad** (`entidades/{id}/domicilios` CRUD): un
  predeterminado por tipo; el domicilio plano de `entidades` sigue siendo el fiscal.
- [x] **Export CSV universal** (`app/core/csv_export.py`, extraído del helper de F5 con
  escape robusto para texto libre): `GET /ventas/comprobantes/export.csv` y
  `/compras/comprobantes/export.csv` (mismos filtros del listado, tope 5000 filas).
  Botón "Exportar CSV" en los toolbars de Ventas y Compras (usa `apiDescargar`).
- [x] Verificado 2026-07-06: 45 pruebas de API en vivo (ABM sucursales + 409/422,
  padrón simulado + DV, dashboard KPIs, geo real contra OSM + q corto 422, domicilios
  múltiples + predeterminado único, sesgo geo + validaciones, export CSV con BOM/`;`) +
  regresión de listados de ventas/compras (refactorizados a `_filtro_*`) + build TS limpio
  + E2E en navegador (KPIs reales, AddressSearch → Av. Corrientes con mapeo a CABA + coords
  + readOnly, padrón trae razón social/cond. IVA, sucursal creada con domicilio normalizado,
  CSV 200 con 151 filas).
- [ ] **Deploy a prod**: migración 012 por psql via session pooler ANTES del push +
  re-aplicar 005; luego push (Vercel + Pages); smoke E2E contra prod.
- Diferido documentado: mapa Leaflet (con Logística F12-bis), export .xlsx nativo (el CSV
  lo cubre), export CSV de clientes/proveedores/artículos (el patrón queda armado), padrón
  con cache de resultados (hoy solo cachea el TA).

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
| 7 ✅ | Dashboard + móvil | Indicadores en tiempo real, responsive del dueño; **export CSV/Excel universal** (base de reportería); **padrón ARCA por CUIT** (autocompletar entidades BUE, validar cond. IVA — quick win del motor fiscal); **domicilios normalizados OSM** (estándar de suite heredado de ZGE: proxy Nominatim + AddressSearch + lat/lon en entidades/sucursales + `entidad_domicilios` — ver `DISENO-LOGISTICA-Y-DOMICILIOS.md` §1; hacerlo ANTES de cargar entidades masivamente); **ABM de sucursales** (la tabla existe desde la 001, falta la UI) + sucursal en cajas POS | **CÓDIGO COMPLETO 2026-07-06** (ver detalle abajo) |
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
