# Recon de datos reales: PROVEEDO.DBF / ART_PROV.DBF (2026-07-05)

Reconocimiento previo a `tools/migrar_proveedores.py`, espejo del de clientes
(`recon-clientes.md`). Censo sobre TODO el árbol legacy: 46 copias de
PROVEEDO.DBF y 21 de ART_PROV.DBF.

## Censo — qué tiene datos y qué no

| Empresa | PROVEEDO (activos / con CUIT / con CCOND) | ART_PROV (filas / proveedores / artículos) |
|---|---|---|
| **Oricam** | **112 / 60 / 41** (+42 con RUBRO; el único con rubros) | 43 / 10 / 43 |
| **hhhh** (Super POS) | 105 / 104 / 0 | — |
| **eVARISTORE** | 63 / 10 / 7 | **1.932 / 52 / 1.212** (único ART_PROV real) |
| Evaristore 2008 (`Gestion Comercial Super Evaristore`) | 41 / 5 / 5 | 258 / 21 / 254 |
| Resto (Vametal, Pronokal, Omni, Cab. S. Jorge, etc.) | 1–22 regs, mayormente vacíos | vacíos |

- El backup **Super** (el de los 12.208 artículos migrados en Fase 2) tiene
  `art_prov.dbf` VACÍO — para probar el comparativo con datos reales la única
  fuente es eVARISTORE, migrando primero sus artículos al mismo tenant.
- Match de `ART_PROV.CODART` contra el `stock.DBF` de eVARISTORE: **99,9 %**
  (1.930/1.932). Contra `ARTICULO.DBF` quedan 45 filas huérfanas (artículos
  borrados del maestro pero vivos en stock/art_prov): el migrador las cuenta
  en `art_prov_sin_articulo`.
- 2 CPROV de art_prov no existen en PROVEEDO (`A/G0`, `LMIA`): filas salteadas
  con aviso (`art_prov_sin_proveedor`).

## Decisiones calibradas (encoding, mapeos)

- **Encoding**: los 46 PROVEEDO reales son LDID `0x03` → **cp1252** (a
  diferencia de CLIENTES.DBF, cp850). Verificado con muestras: «ÑUKE MAPU»,
  «MONSEÑOR BUFFANO», «Morón», «EL SALTEÑO» decodifican bien. El migrador
  detecta por LDID (byte 29) y `--encoding` fuerza.
- **REGPROV** usa la codificación de REGCLI (evidencia: cruce REGPROV×CUIT en
  Oricam/hhhh/eVARISTORE — 1 correlaciona con CUIT válido):
  `1→RI, 2→RI (abolida), 3→CF, 4→EX, 5→CF (abolida), 6→MT`.
  **0 o vacío = "sin cargar"** (52/63 en eVARISTORE, no es un código): se
  infiere RI si hay CUIT válido, CF si no.
- **Coherencia BUE** (espejo clientes): RI sin CUIT válido queda CF con aviso
  (caso real: "COCA COLA" en eVARISTORE, REGPROV=1 sin CUIT).
- **CCOND → condiciones_venta** vía CONVTA.DBF: mismo catálogo y mismo dedupe
  por descripción que el migrador de clientes (los plazos son genéricos:
  "Contado", "30, 60 Días").
- **BUE cross-rol**: si el CUIT ya existe en el tenant (p. ej. la entidad fue
  migrada como cliente), el rol proveedor se cuelga de esa entidad. Si esa
  entidad YA tiene rol proveedor (dos PROVEEDO con el mismo CUIT), el segundo
  queda como entidad aparte SD con nota — conserva su CPROV y sus filas de
  ART_PROV (caso real: AGUAS DANONE compartía CUIT con "Proveedores Varios").
- **Duplicados en ART_PROV** (mismo CPROV+CODART): gana la fila con
  `ULT_FECHA` más nueva.
- **Proveedor habitual**: `ARTICULO.DBF.CPROV → articulos.proveedor_habitual_id`
  (solo si el artículo no tiene uno) — completa el campo diferido en Fase 2.

## Qué NO se migra (y por qué)

- **Saldos legacy** (`FSALPROV_*`, `SALPROV_P/D*`, `TSALDO`): la cta. cte.
  arranca en cero; un saldo vivo se carga como comprobante de apertura manual.
- **CAI / VTOCAI**: régimen de imprenta viejo, sin equivalente en ZGC.
- **PAGOPROV.DBF / RET_PROV.DBF**: historia transaccional, fuera del alcance
  de onboarding (retenciones básicas llegan en Fase 5).
- **FORMA_PAGO / ULT_LISTA** de ART_PROV: texto libre sin destino en el modelo.

## Verificación (eVaristore en dev, 2026-07-05)

Secuencia: `migrar_articulos --crear-tenant "eVaristore (prueba)" --aplicar`
(2.387 artículos, 0 avisos) → `migrar_proveedores --tenant-id ... --aplicar`.

- 63/63 proveedores migrados, 12 condiciones, 4 contactos, 1 duplicado de CUIT
  (SD+nota), 1.885 filas de comparativo, 2.381 habituales asignados.
- Re-corrida idéntica: 0 migrados, todo salteado (idempotencia OK).
- Muestreo de costos contra el DBF crudo: coincidencia exacta (incl.
  `ultima_compra`); la única fila "faltante" del muestreo era uno de los 45
  `sin_articulo` esperados.
- Comparativo con datos reales: VILLAVICENCIO 1.5L con 7 proveedores,
  COCA COLA 2,25 con 6.
