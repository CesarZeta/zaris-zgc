# Facturación y comprobantes — cumplimiento ARCA (ex AFIP)

> Documento de diseño de la Fase 3 (Ventas y Facturación Electrónica).
> Normativa verificada contra fuentes públicas el **2026-07-04**. Este documento es la
> referencia de cumplimiento: cualquier cambio al circuito de comprobantes se contrasta
> primero acá.

## 0. Respuesta corta a la pregunta de César

Hasta la Fase 2.5 ZGC **no emitía ningún comprobante** (solo maestros: clientes,
artículos, stock). La Fase 3 introduce los comprobantes **con el cumplimiento diseñado
desde la base**, no agregado después. Los principios:

1. **Todo comprobante fiscal (facturas, NC, ND) sale con CAE** vía WSFEv1, o no sale.
   No existe en ZGC un camino para imprimir una factura sin autorización de ARCA
   (el modo `simulado` de desarrollo marca el comprobante de forma indeleble como
   "COMPROBANTE NO VÁLIDO — PRUEBA" y jamás genera QR).
2. **Los documentos internos (presupuesto, remito interno, recibo de cobranza) se
   identifican con letra "X"** y la leyenda "DOCUMENTO NO VÁLIDO COMO FACTURA",
   exactamente como exige la RG 1415 para documentos que podrían confundirse con
   comprobantes fiscales.
3. **La letra (A/B/C) no la elige el usuario**: la calcula el sistema a partir de la
   condición de IVA del emisor (tenant) × la del receptor (entidad de la BUE), según
   las reglas vigentes (incluida RG 5003/2021: factura A a monotributistas).
4. **La numeración fiscal la manda ARCA**: antes de emitir se consulta
   `FECompUltimoAutorizado` y se usa ese número + 1. El contador local es espejo de
   control, nunca la fuente. Así no hay huecos ni duplicados posibles.

## 1. Marco normativo aplicado (verificado 2026-07-04)

| Norma | Qué exige | Cómo lo cumple ZGC |
|---|---|---|
| RG 4291/2018 | Factura electrónica obligatoria para todos los contribuyentes | Emisión vía WSAA + WSFEv1 con CAE |
| RG 2485 y manual WSFEv1 (v4.0, ARCA 2025) | Estructura de `FECAESolicitar`: importes, alícuotas, doc. receptor | Mapeo 1:1 documentado en §5 |
| **RG 5616/2024** | `CondicionIVAReceptorId` en cada comprobante. Opcional hasta el 31/8/2026, **obligatorio desde el 1/9/2026** (rechazo del WS) | ZGC lo envía **siempre**, desde el día 1 |
| **Ley 27.743 + RG 5614/2024** (Transparencia Fiscal al Consumidor, vigente 1/4/2025) | Facturas/tickets a consumidor final deben exhibir "Régimen de Transparencia Fiscal al Consumidor Ley 27.743": IVA contenido + Otros Impuestos Nacionales Indirectos | Calculado y almacenado por comprobante B/C a CF; impreso en el PDF |
| **RG 5700/2025** | Identificación del consumidor final solo obligatoria desde **$10.000.000** (CUIT/CUIL/CDI o DNI) | Umbral **parametrizado** en `arca_config.umbral_identificar_cf` (default 10.000.000), editable cuando ARCA lo actualice |
| RG 4892/2020 | Código QR en todo comprobante electrónico | Payload v1 JSON→Base64 en la URL oficial; impreso en el PDF (§7) |
| RG 5003/2021 | RI emite factura **A** a monotributistas | Matriz de letras (§3) |
| RG 4540/2019 | NC/ND deben informar comprobantes asociados (`CbtesAsoc`) | Campo `comprobante_asociado_id` obligatorio para NC/ND; se envía en el WS |
| RG 1415/2003 | Régimen general de emisión; documentos no fiscales con "X" y leyenda | Presupuestos, remitos internos y recibos de cobranza (§4) |

Fuentes consultadas (2026-07-04): comunicado ARCA sobre RG 5616 en el
[grupo de pyafipws](https://groups.google.com/g/pyafipws/c/zmRENlmt9Y4) y
[afipsdk — error 10242](https://afipsdk.com/blog/factura-electronica-solucion-a-error-10242/)
(obligatoriedad 1/9/2026); [ARCA — transparencia fiscal](https://servicioscf.afip.gob.ar/publico/sitio/contenido/novedad/ver.aspx?id=4709)
y [argentina.gob.ar](https://www.argentina.gob.ar/noticias/transparencia-fiscal-arca-reglamenta-el-regimen-que-obliga-discriminar-el-iva-en-las);
[umbral consumidor final $10M — RG 5700/2025](https://blogdelcontador.com.ar/news-45898-arca-eleva-a-10-millones-el-limite-para-identificar-al-consumidor-final-en-comprobantes)
y [tusfacturas.app (julio 2026)](https://www.tusfacturas.app/cual-es-el-limite-facturacion-afip-a-consumidor-final-sin-especificar-datos.html).

## 2. Matriz de comprobantes de ZGC

| Documento | Letra | Cód. ARCA | Fiscal | Numeración | Cta. cte. |
|---|---|---|---|---|---|
| Factura A / B / C | A/B/C | 1 / 6 / 11 | ✅ CAE | ARCA (por pto. vta.) | debe (+) |
| Nota de Débito A / B / C | A/B/C | 2 / 7 / 12 | ✅ CAE | ARCA | debe (+) |
| Nota de Crédito A / B / C | A/B/C | 3 / 8 / 13 | ✅ CAE | ARCA | haber (−) |
| Presupuesto | X | — | ❌ interno | local por pto. vta. | no |
| Remito interno | X | — | ❌ interno | local por pto. vta. | no |
| Recibo de cobranza | X | — | ❌ interno | local por pto. vta. | haber (−) |

**Remito de traslado**: el remito "X" de ZGC documenta la entrega y descarga stock, pero
**no es documento de traslado válido en ruta**. Para transporte de mercadería rige el
remito "R" con CAI de imprenta (RG 1415/RG 100) o el remito electrónico donde aplique.
Se le informa al tenant en la pantalla de remitos. (Evaluar remito electrónico y COT
ARBA post-MVP.)

**Recibo fiscal (tipo 4/9)**: los "Recibos A/B" electrónicos existen para quienes
facturan servicios mediante recibo. Fuera del alcance del MVP (gestión comercial de
bienes): nuestros recibos son constancias de cobranza (documento no fiscal, RG 1415).

## 3. Letra del comprobante — matriz emisor × receptor

Calculada por `app/services/ventas.py::letra_comprobante()`. El usuario no puede
forzarla.

| Emisor \ Receptor | RI | Monotributo | Exento | Consumidor Final |
|---|---|---|---|---|
| **RI** | A | A (RG 5003/2021) | B | B |
| **Monotributo** | C | C | C | C |
| **Exento** | C | C | C | C |

- Con letra **A** el IVA se discrimina por alícuota; el receptor debe tener CUIT válido
  (dígito verificador ya validado por la BUE desde Fase 1).
- Con letra **B/C** el precio es final (IVA contenido). Para receptor CF con total ≥
  umbral RG 5700 se exige DNI/CUIT en el comprobante (bloqueo en la emisión).
- Condición IVA del receptor → `CondicionIVAReceptorId`: RI→1, EX→4, CF→5, MT→6.
- Tipo de documento del receptor → `DocTipo`: CUIT→80, CUIL→86, DNI→96, sin
  identificar→99 (DocNro 0, solo B/C bajo el umbral).

## 4. Documentos internos (RG 1415)

Presupuestos, remitos internos y recibos llevan: letra "X" visible, leyenda
**"DOCUMENTO NO VÁLIDO COMO FACTURA"**, numeración propia por punto de venta
(independiente de la fiscal). No llevan QR ni CAE y el PDF no imita el formato fiscal.

## 5. Mapeo a WSFEv1 (`FECAESolicitar`)

Un solo lugar arma el request: `app/services/arca/wsfev1.py`. Mapeo:

| Campo WS | Origen en ZGC |
|---|---|
| `PtoVta` | `puntos_venta.numero` (habilitado como "Web Services" en ARCA) |
| `CbteTipo` | `tipos_comprobante.codigo_arca` |
| `Concepto` | 1 (Productos) — parametrizable a 2/3 con `FchServDesde/Hasta/FchVtoPago` |
| `DocTipo` / `DocNro` | snapshot del receptor en el comprobante (§3) |
| `CbteDesde=CbteHasta` | `FECompUltimoAutorizado + 1` (consultado en la emisión) |
| `CbteFch` | fecha del comprobante (±5 días que permite el WS para concepto 1) |
| `ImpNeto` | Σ neto gravado (2 dec.) |
| `ImpTotConc` | Σ no gravado |
| `ImpOpEx` | Σ exento |
| `ImpIVA` | Σ IVA de `comprobante_alicuotas` |
| `ImpTrib` | otros tributos (0 en MVP) |
| `ImpTotal` | suma exacta de los anteriores (validado antes de enviar) |
| `MonId` / `MonCotiz` | 'PES'/1 — 'DOL' + cotización cuando la venta es en USD (con `CanMisMonExt`/pago según RG 5616) |
| `CondicionIVAReceptorId` | **siempre** (§3) |
| `Iva[]` (AlicIva) | una entrada por alícuota: Id ARCA (3=0%, 4=10,5%, 5=21%, 6=27%, 8=5%, 9=2,5%), BaseImp, Importe — espejo de la tabla `comprobante_alicuotas` (patrón TABLAIVA del legacy) |
| `CbtesAsoc[]` | para NC/ND: tipo/pto.vta./número del comprobante asociado (RG 4540) |

**Redondeo**: los netos se acumulan por alícuota con precisión `numeric(14,4)` y se
redondean a 2 decimales **por alícuota** (half-up); el IVA se calcula sobre la base ya
redondeada; `ImpTotal` es la suma de las partes redondeadas. Es el criterio que valida
el WS (evita el rechazo 10048 por diferencias de centavos).

**Facturas C** (emisor MT/EX): sin discriminación — `ImpNeto` = total, `ImpIVA` = 0,
sin array de alícuotas.

**Idempotencia ante timeouts**: si la llamada muere después de enviar, ANTES de
reintentar se consulta `FECompConsultar` por (tipo, pto. vta., número): si ARCA ya lo
autorizó, se toma ese CAE y no se vuelve a solicitar. El request y response XML de cada
emisión quedan guardados (`comprobantes.arca_request/arca_response`) para auditoría.

## 6. Estados y anulación

`borrador → emitido` (con CAE) — los borradores se editan/borran libremente; un
comprobante **emitido es inmutable**: no se edita ni se "anula" — se revierte con
**nota de crédito** (así lo exige el régimen; el botón "Anular" de un emitido genera la
NC espejo). `anulado` existe solo para documentos internos (presupuesto/remito/recibo).

## 7. QR y PDF (RG 4892 + RG 1415 + Ley 27.743)

- QR: JSON v1 `{ver:1, fecha, cuit, ptoVta, tipoCmp, nroCmp, importe, moneda, ctz,
  tipoDocRec, nroDocRec, tipoCodAut:"E", codAut}` → Base64 → 
  `https://www.afip.gob.ar/fe/qr/?p=...` — generado en backend (lib `segno`, SVG).
- El PDF/impresión incluye: razón social, domicilio, CUIT, IIBB, inicio de actividades,
  condición IVA del emisor; letra grande con código de comprobante; datos del receptor;
  detalle; para **A**: netos + IVA discriminado por alícuota; para **B/C a CF**: bloque
  "Régimen de Transparencia Fiscal al Consumidor Ley 27.743" con IVA contenido y Otros
  Impuestos Nacionales Indirectos; CAE + vencimiento + QR.
- La impresión se resuelve con HTML imprimible desde el frontend (patrón ZGE); el
  backend entrega todos los datos + el SVG del QR en `GET /ventas/comprobantes/{id}/impresion`.

## 8. Modos de operación ARCA (`arca_config.modo` por tenant)

| Modo | Uso | CAE | Endpoints |
|---|---|---|---|
| `deshabilitado` | tenant sin FE configurada | bloquea emisión fiscal | — |
| `simulado` | desarrollo/demo | `CAE 99999999999999` + marca **PRUEBA** en DB, UI e impresión; sin QR | — |
| `homologacion` | pruebas reales contra ARCA | CAE de homologación (sin validez) | `wsaahomo.afip.gov.ar` / `wswhomo.afip.gov.ar` |
| `produccion` | operación real | CAE válido | `wsaa.afip.gov.ar` / `servicios1.afip.gov.ar` |

**Certificados** (los gestiona César / cada tenant; ZGC guarda cert+clave en
`arca_config`):

```
# 1. Generar clave y CSR (una vez por tenant emisor)
openssl genrsa -out zgc.key 2048
openssl req -new -key zgc.key -subj "/C=AR/O=<razón social>/CN=zgc/serialNumber=CUIT <cuit>" -out zgc.csr
# 2. Homologación: cargar el CSR en WSASS (autoservicio) → obtener zgc.crt
# 3. Producción: "Administración de Certificados Digitales" con Clave Fiscal 3
# 4. En ambos: asociar el certificado al servicio "wsfe" (Administrador de Relaciones)
# 5. Habilitar un punto de venta "Web Services" en ARCA (Comprobantes en línea → ABM ptos. vta.)
```

## 9. Decisión técnica: cliente WSAA/WSFEv1 propio (no el paquete pyafipws)

El stack (CLAUDE.md §2) nombraba **pyafipws**. Al implementar se decidió (2026-07-04)
escribir un cliente propio y liviano (`app/services/arca/`) que habla los mismos
protocolos (WSAA: TRA firmado CMS/PKCS#7; WSFEv1: SOAP 1.1), porque:

1. **Vercel serverless**: pyafipws arrastra dependencias legacy (pysimplesoap,
   histórico M2Crypto) problemáticas en ese runtime; nuestro cliente usa solo `httpx`
   (ya en el stack) + `cryptography` (firma CMS estándar).
2. El contrato WSFEv1 es estable y chico (4 métodos usados); pyafipws queda como
   **implementación de referencia** contra la que se contrastan los XML.
3. El TA (token+sign, vigencia 12 h) se cachea por tenant+servicio en `arca_tokens`.

La razón de fondo de "backend Python" no cambia: el ecosistema AFIP/ARCA en Python es
el mejor documentado (pyafipws, manuales, foros).

## 10. Qué queda explícitamente fuera del MVP (documentado, no olvidado)

- Percepciones/retenciones en la factura (`ImpTrib` queda en 0; registro de retenciones
  recibidas llega con Fase 5 — Libros de IVA).
- FCE MiPyME (RG 4367), exportación (WSFEXv1), bonos fiscales, turismo.
- CAEA (contingencia offline masiva) — el POS offline (Fase 6+) facturará al reconectar;
  CAEA se evalúa para el nodo de sucursal.
- Remito electrónico (cárnico/harinero/azucarero) y COT ARBA.
- Moneda extranjera con cancelación en la misma moneda (RG 5616): MVP factura en PES o
  DOL con cotización; el pago se registra en PES.
