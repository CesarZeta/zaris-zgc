# ZGC — ZARIS Gestión Comercial

> **⚠️ REGLA RECTORA #0 — NUNCA ASUMIR, VERIFICAR SIEMPRE:** antes de afirmar, opinar o recomendar cualquier cosa sobre el código, la DB, la infra o el estado del proyecto, **verificarlo contra la realidad** (DB con `execute_sql`, código con `Read`/`Grep`, runtime con `curl`/browser, historia con `git log`). No deducir de esta doc ni de la memoria. Misma regla rectora que ZGE, declarada permanente por Cesar el 2026-05-23.

## 1. Qué es ZGC

Web app de **gestión comercial, contable y de stock** que administra puntos de venta de manera centralizada: ventas, compras, IVA, bancos, cheques, depósitos, cajas chicas, cuentas corrientes, comisiones, facturación electrónica ARCA/AFIP.

Es la reescritura moderna del software legacy **RevoSolution Gestión Comercial** (escritorio, FoxPro/xBase, Argentina). Todo el material del legacy está en `Revosolution Software/`:

- **No hay código fuente** del legacy — solo ejecutables, backups y drivers.
- Los activos reutilizables son las **tablas DBF** (306 tablas únicas: modelo de datos completo, y datos reales de clientes migrables) y los **manuales PDF** (el de V16, 118 páginas, es la especificación funcional de referencia).
- **El esquema completo del legacy ya está extraído**: `docs/legacy/esquema-dbf.md` (navegable) y `docs/legacy/esquema-dbf.json` (machine-readable, para scripts de migración). Se regenera con `python tools/extraer_esquema_dbf.py`. Consultarlo SIEMPRE antes de diseñar una tabla nueva en PostgreSQL.

### Módulos funcionales (heredados del legacy, alcance de referencia)

1. Configuración (empresa, condición IVA → facturas A/B/C, puntos de venta, numeración, usuarios y permisos por módulo, condiciones de venta, transportistas, retenciones, tarjetas, depósitos)
2. Artículos y Stock (familias/subfamilias, 4 listas de precios, cambios masivos, kardex, etiquetas código de barras, valorización, ajustes, interdepósitos, comparativo por proveedor, import Excel)
3. Proveedores / Compras (remitos, facturas/NC/ND, órdenes de pago, cta. cte., vencimientos)
4. Clientes / Ventas (presupuestos, remitos, facturación, cobranzas, cta. cte., morosidad)
5. Vendedores / Comisiones (por venta o por cobranza)
6. Cheques
7. Libros de IVA (ventas/compras, retenciones, CITI)
8. Caja y Bancos (planilla de caja diaria, movimientos, conciliación)
9. POS (supermercado/mostrador: código de barras, pesables con etiqueta de balanza, envases retornables, venta por departamento, autorización de supervisor para anulaciones)

> **Definición de producto**: el alcance del MVP, mercado objetivo, modelo SaaS multi-tenant y roadmap de diferenciales están en `docs/DEFINICION-PRODUCTO.md` (discovery del 2026-07-03). El plan de ejecución está en `docs/ROADMAP.md`. Leerlos antes de decidir alcances.

## 1-ter. Multipropósito por rubro — regla de producto (César, 2026-07-04)

ZGC no es solo para supermercados: la **gestión central es una sola y general**, con
customización por **rubro del tenant** (supermercado, indumentaria/calzado, electrónica,
ferretería/repuestos, distribuidora, general); los **POS sí son full orientados** al rubro.
El habilitador es el modelo de **variantes** de artículos (talle, color, gusto, capacidad —
con EAN y stock propios por combinación). El rubro cambia presets/UI, **nunca bifurca el
modelo de datos**. Ver `docs/DISENO-RUBROS-Y-VARIANTES.md` antes de tocar el maestro de
artículos, ventas o POS.

## 1-bis. Base Única de Entidades (BUE) — regla de arquitectura

**"El cliente es el núcleo del sistema"** (César, 2026-07-03). Toda persona física o jurídica existe **una sola vez** en `entidades` (datos maestros: nombre/razón social, CUIT/DNI, condición IVA, domicilios, contactos). Los roles comerciales (`clientes`, `proveedores`, `vendedores`, `transportistas`) son tablas satélite que referencian `id_entidad` y solo agregan lo específico del rol. **Prohibido** duplicar datos maestros de personas en tablas de rol. Análogo a la BUC de ZGE (§2 de su CLAUDE.md). Todo registro lleva `tenant_id`; RLS de Supabase como segunda línea de defensa.

## 2. Stack Tecnológico (decidido 2026-07-03)

Mismo stack que ZGE, para reusar patrones, auth y experiencia:

| Capa | Tecnología |
|---|---|
| Backend | **FastAPI** (Python 3.10+), SQLAlchemy async + asyncpg |
| DB | **PostgreSQL** — Supabase en prod (cuenta nueva, sa-east-1), Postgres local en dev |
| Frontend | **React (Vite)** |
| Hosting | Backend en **Vercel serverless región gru1/São Paulo** (decisión 2026-07-04: Railway no tiene región SP; pooler transaccional :6543 de Supabase), frontend en **GitHub Pages**, DB **Supabase** |
| Facturación electrónica | **pyafipws** (WSAA + WSFEv1) — razón de peso para backend Python |
| Auth | JWT como ZGE (`POST /auth/login`, bcrypt directo — **no passlib**) |

Consultar el `CLAUDE.md` de ZGE (`C:\Users\Cesar\Documents\ZARIS\Desarrollo\ZGE\CLAUDE.md`) para los patrones ya resueltos (auth, roles, estructura de módulos React) antes de reinventar algo.

### Diseño visual (decidido 2026-07-04): «ZARIS Heredado»

César eligió (entre 3 mockups comparados) la identidad de suite con ZGE:
- **Paleta**: crema `#f2f1ed` de fondo, tinta `#26251e`, acento único naranja `#f54e00`, dorado `#c08532` secundario, éxito `#1f8a65`, error `#cf2d56`. Superficies `--surface-100..500` y bordes rgba de tinta como en ZGE.
- **Tipografía**: Space Grotesk (display/UI) + JetBrains Mono (códigos, CUIT, importes) — copiar fuentes y `tokens.css` desde `ZGE/web-app/src/styles/` y `assets/fonts/`.
- **Forma**: radios chicos (2-4px), bordes hairline, sombras suaves; sidebar tinta oscura con ítem activo naranja.
- Regla heredada de ZGE: **el naranja es del brand** — los estados usan otros colores (éxito verde, error rojo, advertencia amarillo lejos del naranja).
- Los estados de comprobantes/clientes se codifican con chips/pills; números siempre `tabular-nums`.

## 3. Arquitectura: nube + nodo de sucursal (decidido 2026-07-03: "online y red LAN")

El POS debe poder facturar **aunque se corte internet**, igual que el legacy. La arquitectura es híbrida:

```
                 ┌──────────────── NUBE ────────────────┐
                 │  Backend central (FastAPI/Railway)    │
                 │  PostgreSQL (Supabase)                │
                 │  Gestión centralizada multi-sucursal  │
                 └───────────────▲──────────────────────┘
                                 │ sincronización
        ┌────────────────────────┴───────────────────────┐
        │  NODO SUCURSAL (PC servidor local en la LAN)    │
        │  Mismo backend FastAPI + PostgreSQL local       │
        └───▲──────────────▲──────────────▲──────────────┘
            │ LAN          │ LAN          │ LAN
         CAJA 1         CAJA 2         CAJA 3   (navegador → POS web)
```

- Las **cajas** son clientes web (React) que hablan con el **nodo de sucursal** por LAN — no dependen de internet.
- El **nodo de sucursal** sincroniza con la nube: sube ventas/movimientos, baja artículos/precios/clientes (el mismo esquema conceptual "Actualizar POS" del legacy, pero automático y continuo).
- La **gestión** (backoffice) se usa online contra la nube; en la sucursal también puede usarse contra el nodo local.
- Implicancias de diseño desde el día 1: **IDs únicos globales** (UUID) generados donde nace el dato, cada registro sellado con `sucursal_id`/`origen`, colas de sincronización idempotentes, y resolución de conflictos "la nube manda" para maestros / "el origen manda" para transacciones.
- La facturación electrónica (CAE) requiere internet: el POS factura offline como comprobante pendiente y el nodo gestiona CAE al reconectar (CAEA como alternativa a evaluar), o usa controlador fiscal físico donde aplique.

## 4. Estructura del repo (prevista, espejo de ZGE)

```
ZGC/
├── backend/        # FastAPI
├── web-app/        # React (Vite) — gestión y POS
├── sql/            # migraciones
├── docs/           # documentación funcional y técnica
├── tools/          # scripts (extracción DBF, migración de datos, etc.)
└── Revosolution Software/   # legacy de referencia (NO tocar, solo lectura)
```

## 5. Contexto fiscal argentino (siempre presente)

- Tipos de comprobante A/B/C según condición IVA del emisor y receptor; CUIT con dígito verificador.
- IVA: tasas múltiples por artículo, precios con o sin IVA incluido según configuración.
- ARCA/AFIP: factura electrónica (CAE vía WSFEv1), libros de IVA digital, retenciones/percepciones, CITI.
- Monotributo vs. Responsable Inscripto.
