# Reconocimiento de CLIENTES.DBF (legacy RevoSolution)

> Resultado del análisis paralelo del 2026-07-03 sobre los ~50 CLIENTES.DBF del árbol
> legacy (4 agentes: variantes/calidad, semántica REGCLI, catálogos, encoding/memos).
> Calibra las constantes de `tools/migrar_clientes.py`.

## Decisiones calibradas con evidencia

| Tema | Decisión | Evidencia |
|---|---|---|
| **Encoding** | `cp850` para CLIENTES.DBF | Los 18 archivos reales tienen LDID `0x02`; bytes altos (ñ í ó Ñ é º) decodifican español válido solo con cp850. **Excepción**: CONVTA puede traer texto cp1252 ('Días'→'DÝas' con cp850) — el migrador detecta el artefacto 'Ý' y relee en cp1252. |
| **REGCLI → condición IVA** | `1=RI, 2=RI, 3=CF, 4=EX, 5=CF, 6=MT`; vacío→CF | Triple: (1) el libro IVA del propio legacy (`_ADMINC`) guarda código+texto: 1='R.Inscript', 3='C.Final', 4='Exento', 6='Monotribut'; (2) cruce con letra de factura sobre ~326.000 comprobantes: 1→100% A, 3/4/6→100% B; (3) perfil de CUIT por código. 2 y 5 son categorías AFIP abolidas (2='Resp. No Inscripto' recibía A → RI; 5='No Responsable' → CF), confianza baja pero sin ocurrencias en datos reales. |
| **CUIT** | Normalizar a dígitos y validar DV; inválido → `SD` + nota en observaciones. Nunca rechazar el registro. | Omni: 352/353 válidos (formato `NN-NNNNNNNN-N`). Pero hay bases con el 100% truncados a 8-10 dígitos (demo Super), espacios internos y dígitos faltantes. |
| **CUITs duplicados** | Son legítimos (sucursales del mismo cliente). El primero se lleva el documento; los siguientes quedan SD + nota cruzada. | Omni: 5 CUITs compartidos por 10 registros activos. |
| **CODCLI** | Tratar como string, jamás castear a int | Zero-padded ('0001'), hay valores no numéricos ('-036'), huecos, y '0000' = consumidor final. |
| **Registros borrados** | NO se migran (dbfread los excluye al iterar) | 5-18% de cada archivo tiene flag de borrado (0x2A). |
| **LISTAPRE** | 0 = "sin lista" → default 1 sin aviso; 1-4 se respetan | Omni 99% en 0; Oricam/CSJORGE multivalor real 1-4. |
| **BLOQUEADO** | blank/None → False | Masivamente en blanco (163/172 en demo); nunca se observó valor 1. |
| **CONVTA** | Campos `CCOND C(2)`, `DESCOND C(26)`, `DIAS_1..12 N(3)`. Días: blank=slot sin uso; 0 antes del último >0 es vencimiento real a 0 días; sin positivos = contado `[0]`. Dedupe por descripción (códigos 12/13/14 de Oricam = '1 Días'). No reconstruir desde DESCOND (viene truncada). | 21 copias, 1 sola variante de esquema; catálogo semilla de fábrica compartido. |
| **ZONA / ZON.DBF** | ZONA es texto libre C(2) >96% vacío; **ZON.DBF NO es zonas** (son formatos de impresión FORM1/FORM2). Se migra el código como zona solo si existe. | Únicos valores vistos: '11', 'su'. |
| **PROVCLI** | Texto libre muy limpio: mapeo upper/trim/sin-acentos a las 24 ARCA + sinónimos defensivos + typo real 'BUENOS IARES' | Dominan BUENOS AIRES (497) y CAPITAL FEDERAL (282); 282 vacíos. |
| **OBSERVAC (memo FPT)** | Mapear a TEXT nullable; abrir con `ignore_missing_memofile=True` | Casi sin uso: 1 memo no vacío en 434 registros de Omni; el resto de los FPT están vacíos. |
| **CVIAJ / CTRANSP** | Los roles vendedor/transportista llegan en fases posteriores; el dato se preserva como nota `[migración] vendedor/transporte legacy: XX` en observaciones. | Omni: 4 registros con CVIAJ, 1 con CTRANSP (hallazgo de la verificación adversarial). |
| **CRED_MAX** | `0` legacy = "sin límite definido" → NULL | El 100% de Omni es 0.0; ninguna base observada usa 0 como "sin crédito autorizado". |
| **E_MAIL / teléfonos** | Email: validar formato; basura ('False') se descarta. Teléfonos: migrar crudos (formatos caóticos: '15-...', '/', 'Int 24', hasta localidades). | 12 emails no vacíos en ~1300 registros. |

## Variantes de esquema (6, núcleo común de 33 campos)

- Canónica GC ×19 (Omni): + `PERM1/PERM2/SALDOACT`
- POS ×17 y Restaurantes ×8: + `FNACIM/FALTA` (¡y en Restaurantes `CODCLI` es C(10)!)
- GC nuevas ×4: + `IBRUTOS/PAIS` (×2 además `ENVXMAIL/ENVXFTP`)
- Anchos variables: NOMCLI/CONTACTO 30↔40, DOMCLI 30/40/60.
- **Regla del migrador: mapear por NOMBRE de campo con defaults, nunca por posición.**

## Deduplicación de fuentes (CRÍTICO al migrar)

La mayoría de los 50 archivos son espejos byte-idénticos (`USB Pendrive`/`BackUp Pendrive` duplican `BAck UP CLiente`) o snapshots del mismo comercio en fechas distintas (CSJORGE aparece 3 veces; la demo Super clonada 4 veces). **Migrar POR EMPRESA eligiendo un único archivo fuente — el snapshot más nuevo/completo — jamás concatenar.**
