# Esquema del legacy RevoSolution (tablas DBF)
Generado el 2026-07-04 por `tools/extraer_esquema_dbf.py`. Se analizaron 7185 archivos DBF; 306 tablas únicas. Para cada tabla se documenta la copia **canónica** (la de más registros / más reciente).

Tipos: C=Character, N=Numeric, D=Date, L=Logical, M=Memo, F=Float.

## Resumen por categoría
| Categoría | Tablas |
|---|---|
| negocio | 98 |
| facturacion electronica | 9 |
| interna (GV) | 147 |
| temporal/auxiliar | 52 |

---

# Categoría: negocio

## ACONCEPT
- Registros (canónico): **8** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\ACONCEPT.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCONC | C | 25 | 0 |
| 2 | CCONC | C | 2 | 0 |

## ADUANAS
- Registros (canónico): **59** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\ADUANAS.DBF` (mod. 2008-12-29, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CADUANA | C | 6 | 0 |
| 2 | NADUANA | C | 50 | 0 |

## AGRUPA
- Registros (canónico): **1** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Bonafide 11 2009\Super Restaurantes y Delivery\AGRUPA.DBF` (mod. 2009-11-17, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MESA | N | 10 | 0 |
| 2 | PORC_PROP | N | 5 | 2 |
| 3 | DESCUENTO | N | 2 | 0 |
| 4 | TEXTO | L | 1 | 0 |
| 5 | NTEXTO | N | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | CBARRA | C | 20 | 0 |
| 8 | DESART | C | 40 | 0 |
| 9 | AUXDESART | M | 4 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | CANTIDAD | N | 10 | 2 |
| 12 | POR_REMITO | N | 10 | 2 |
| 13 | PAUXIL | N | 10 | 2 |
| 14 | PRECIO | N | 8 | 2 |
| 15 | APRECIO | N | 8 | 2 |
| 16 | BONIF_1 | N | 5 | 2 |
| 17 | BONIF_2 | N | 5 | 2 |
| 18 | PUNIT | N | 10 | 4 |
| 19 | PARCIAL | N | 10 | 4 |
| 20 | NDESPACHO | C | 15 | 0 |
| 21 | ADUANA | C | 15 | 0 |
| 22 | TASA | N | 5 | 2 |
| 23 | SNI | N | 5 | 2 |
| 24 | KOEF | N | 7 | 4 |
| 25 | COMANDA | N | 1 | 0 |
| 26 | BEBIDA | L | 1 | 0 |
| 27 | SUM_CANTID | N | 16 | 2 |

## AJUSTES
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\AJUSTES.DBF` (mod. 2012-05-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | NRO_REC | C | 13 | 0 |
| 7 | AJUSTE_COT | N | 8 | 2 |

## ART
- Registros (canónico): **5,628** · copias en el árbol: 1 · variantes de esquema: 1
- Fuente: `Revosolution Software\Super Kelo\art.DBF` (mod. 2008-06-06, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | C | 15 | 0 |
| 2 | C | C | 15 | 0 |
| 3 | D | C | 40 | 0 |
| 4 | E | N | 20 | 15 |
| 5 | F | C | 21 | 0 |
| 6 | G | C | 15 | 0 |
| 7 | H | N | 9 | 0 |
| 8 | I | N | 15 | 2 |
| 9 | J | C | 18 | 0 |
| 10 | K | N | 20 | 15 |

## ARTICULO
- Registros (canónico): **20,815** · copias en el árbol: 51 · variantes de esquema: 5
- Fuente: `Revosolution Software\BAck UP CLiente\Poli\articulo.DBF` (mod. 2014-09-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | CBARRA | C | 20 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | FAMILIA | C | 30 | 0 |
| 6 | NSUBF | C | 30 | 0 |
| 7 | UNIDAD | C | 6 | 0 |
| 8 | UNICOMP | C | 6 | 0 |
| 9 | COEFICIENT | N | 8 | 2 |
| 10 | STOCK | L | 1 | 0 |
| 11 | EXP_UN | N | 1 | 0 |
| 12 | CPROV | C | 4 | 0 |
| 13 | NOMPROV | C | 30 | 0 |
| 14 | COSTO | N | 9 | 3 |
| 15 | COSTIVA | N | 1 | 0 |
| 16 | UTIL_1 | N | 6 | 2 |
| 17 | UTIL_2 | N | 6 | 2 |
| 18 | UTIL_3 | N | 6 | 2 |
| 19 | UTIL_4 | N | 6 | 2 |
| 20 | PVENTA_1 | N | 8 | 2 |
| 21 | PVENTA_2 | N | 8 | 2 |
| 22 | PVENTA_3 | N | 8 | 2 |
| 23 | PVENTA_4 | N | 8 | 2 |
| 24 | TASA | N | 5 | 2 |
| 25 | SNI | N | 5 | 2 |
| 26 | BONIF_11 | N | 5 | 2 |
| 27 | BONIF_12 | N | 5 | 2 |
| 28 | BONIF_21 | N | 5 | 2 |
| 29 | BONIF_22 | N | 5 | 2 |
| 30 | BONIF_31 | N | 5 | 2 |
| 31 | BONIF_32 | N | 5 | 2 |
| 32 | BONIF_41 | N | 5 | 2 |
| 33 | BONIF_42 | N | 5 | 2 |
| 34 | EN_DOLARES | L | 1 | 0 |
| 35 | ULT_PRC | D | 8 | 0 |
| 36 | NAC_IMP | N | 1 | 0 |
| 37 | NDESPACHO | C | 15 | 0 |
| 38 | ADUANA | C | 15 | 0 |
| 39 | ORIGEN | C | 15 | 0 |
| 40 | CUENTA | C | 6 | 0 |
| 41 | COMBUS | L | 1 | 0 |
| 42 | IMP_INT | N | 10 | 5 |
| 43 | IMPUESTOS | N | 6 | 2 |
| 44 | NOTA | M | 4 | 0 |
| 45 | FILE1 | M | 4 | 0 |
| 46 | STRETCH | N | 1 | 0 |
| 47 | DIBUJO | M | 4 | 0 |
| 48 | FOTO | G | 4 | 0 |
| 49 | CODPROVE | C | 15 | 0 |
| 50 | PESABLE | L | 1 | 0 |
| 51 | DEVOLUCION | L | 1 | 0 |
| 52 | VENTAXDEPT | L | 1 | 0 |
| 53 | ENVASE | C | 15 | 0 |

## ARTICULOS2
- Registros (canónico): **3,591** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\super old\faytim 2\articulos2.DBF` (mod. 2006-09-04, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | C | 16 | 0 |
| 2 | C | C | 36 | 0 |
| 3 | E | N | 20 | 15 |
| 4 | F | N | 20 | 15 |
| 5 | I | N | 4 | 2 |
| 6 | J | N | 1 | 0 |
| 7 | M | C | 20 | 0 |

## ARTICULOSUPER
- Registros (canónico): **5,465** · copias en el árbol: 1 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Poli\articulosuper.DBF` (mod. 2008-09-01, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | C | 15 | 0 |
| 2 | C | C | 15 | 0 |
| 3 | D | C | 40 | 0 |
| 4 | E | N | 11 | 2 |
| 5 | F | C | 12 | 0 |
| 6 | G | C | 28 | 0 |
| 7 | H | C | 1 | 0 |
| 8 | I | N | 10 | 1 |
| 9 | J | C | 18 | 0 |
| 10 | K | N | 20 | 15 |

## ART_PROV
- Registros (canónico): **2,032** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\art_prov.dbf` (mod. 2010-02-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | CODSPROV | C | 20 | 0 |
| 4 | COSTO | N | 8 | 2 |
| 5 | BONIF1 | N | 6 | 2 |
| 6 | BONIF2 | N | 6 | 2 |
| 7 | BONIF3 | N | 6 | 2 |
| 8 | FORMA_PAGO | C | 30 | 0 |
| 9 | ULT_LISTA | C | 8 | 0 |
| 10 | ULT_FECHA | D | 8 | 0 |

## ATACH
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\atach.DBF` (mod. 2009-01-02, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | ARQ | C | 254 | 0 |
| 2 | LOCALIZ | C | 254 | 0 |

## A_ENVIAR
- Registros (canónico): **2** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\A_ENVIAR.DBF` (mod. 2009-01-02, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 40 | 0 |
| 3 | PERIODO | C | 6 | 0 |
| 4 | ARCHIVO | C | 128 | 0 |
| 5 | ORIGINAL1 | C | 128 | 0 |
| 6 | ORIGINAL2 | C | 128 | 0 |
| 7 | ORIGINAL3 | C | 128 | 0 |
| 8 | E_MAIL | C | 60 | 0 |
| 9 | ENVIO | N | 1 | 0 |
| 10 | IMPORTE | N | 10 | 2 |

## BASE80
- Registros (canónico): **1** · copias en el árbol: 50 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\BASE80.DBF` (mod. 2004-07-19, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 150 | 0 |

## BASE90
- Registros (canónico): **3** · copias en el árbol: 50 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\BASE90.DBF` (mod. 2002-11-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 150 | 0 |

## BASE95
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\BASE95.DBF` (mod. 2001-11-27, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MENSAJE | C | 80 | 0 |

## CHEQUES
- Registros (canónico): **30** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\cheques.DBF` (mod. 2014-08-30, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | SELECC | L | 1 | 0 |
| 2 | NCHEQUE | N | 10 | 0 |
| 3 | CIA | C | 1 | 0 |
| 4 | NCTACTE | C | 15 | 0 |
| 5 | CCONC | C | 3 | 0 |
| 6 | BANCO | C | 20 | 0 |
| 7 | PLAZA | C | 20 | 0 |
| 8 | FECCHE | D | 8 | 0 |
| 9 | FECVTO | D | 8 | 0 |
| 10 | IMPCHE | N | 12 | 2 |
| 11 | DOLAR | N | 8 | 2 |
| 12 | HS_ACREDIT | N | 3 | 0 |
| 13 | PROP_TER | N | 1 | 0 |
| 14 | CART_PAS | N | 1 | 0 |
| 15 | EMITIDO | C | 30 | 0 |
| 16 | CODCLI | C | 4 | 0 |
| 17 | FRECEP | D | 8 | 0 |
| 18 | CPROV | C | 4 | 0 |
| 19 | PASADO_A | C | 30 | 0 |
| 20 | FPASADO | D | 8 | 0 |
| 21 | NCOM_ENT | C | 17 | 0 |
| 22 | TCOM_ENT | C | 1 | 0 |
| 23 | NCOM_SAL | C | 17 | 0 |
| 24 | TCOM_SAL | C | 1 | 0 |
| 25 | NMOV | C | 8 | 0 |
| 26 | NRECIBO | C | 8 | 0 |
| 27 | OPAGO | C | 8 | 0 |
| 28 | NMOV_S | C | 8 | 0 |
| 29 | RECHAZADO | N | 1 | 0 |
| 30 | FIRMANTE | C | 30 | 0 |
| 31 | CUENTA | C | 20 | 0 |
| 32 | CUIT | C | 13 | 0 |
| 33 | CUITBCO | C | 13 | 0 |

## CIERREDU
- Registros (canónico): **3** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\CIERREDU.DBF` (mod. 2008-12-31, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PERIODO | C | 6 | 0 |
| 2 | COMPRAS | L | 1 | 0 |
| 3 | VENTAS | L | 1 | 0 |

## CLASIFICA
- Registros (canónico): **6** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\CLASIFICA.DBF` (mod. 2009-05-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CLASES | C | 12 | 0 |

## CLAVES
- Registros (canónico): **1** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\CLAVES.DBF` (mod. 2008-09-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | EMAIL | C | 30 | 0 |
| 2 | FACT1 | D | 8 | 0 |
| 3 | FACT2 | D | 8 | 0 |
| 4 | FACT3 | D | 8 | 0 |

## CLIENTES
- Registros (canónico): **466** · copias en el árbol: 50 · variantes de esquema: 6
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\clientes.DBF` (mod. 2014-10-04, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 40 | 0 |
| 4 | DOMCLI | C | 40 | 0 |
| 5 | LOCCLI | C | 30 | 0 |
| 6 | PROVCLI | C | 15 | 0 |
| 7 | CONTACTO | C | 40 | 0 |
| 8 | ZONA | C | 2 | 0 |
| 9 | CVIAJ | C | 2 | 0 |
| 10 | LISTAPRE | N | 1 | 0 |
| 11 | CODPOS | C | 10 | 0 |
| 12 | TELCLI_1 | C | 15 | 0 |
| 13 | TELCLI_2 | C | 15 | 0 |
| 14 | FAX | C | 15 | 0 |
| 15 | E_MAIL | C | 45 | 0 |
| 16 | HTTP | C | 40 | 0 |
| 17 | CALIFIC | C | 10 | 0 |
| 18 | DESCUENTO | N | 5 | 2 |
| 19 | BLOQUEADO | N | 1 | 0 |
| 20 | CUITCLI | C | 13 | 0 |
| 21 | REGCLI | N | 1 | 0 |
| 22 | DNI | N | 8 | 0 |
| 23 | FSALCLI_1 | D | 8 | 0 |
| 24 | SALCLI_P1 | N | 10 | 2 |
| 25 | SALCLI_D1 | N | 10 | 2 |
| 26 | FSALCLI_2 | D | 8 | 0 |
| 27 | SALCLI_P2 | N | 10 | 2 |
| 28 | SALCLI_D2 | N | 10 | 2 |
| 29 | TSALDO | N | 1 | 0 |
| 30 | CRED_MAX | N | 10 | 2 |
| 31 | CCOND | C | 2 | 0 |
| 32 | CTRANSP | C | 3 | 0 |
| 33 | OBSERVAC | M | 10 | 0 |
| 34 | PERM1 | L | 1 | 0 |
| 35 | PERM2 | L | 1 | 0 |
| 36 | SALDOACT | N | 10 | 2 |

## COMPRASD
- Registros (canónico): **8,275** · copias en el árbol: 46 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\COMPRASD.DBF` (mod. 2010-02-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NCOMP | C | 8 | 0 |
| 3 | TCOMP | C | 1 | 0 |
| 4 | CPROV | C | 4 | 0 |
| 5 | CIA | C | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | CDEP | C | 2 | 0 |
| 8 | CANTIDAD | N | 10 | 2 |
| 9 | BONIF_1 | N | 5 | 2 |
| 10 | BONIF_2 | N | 5 | 2 |
| 11 | PCOMPRA | N | 8 | 2 |
| 12 | R_COMPRASM | N | 10 | 0 |
| 13 | PCOMPRAD | N | 8 | 2 |

## COMPRASM
- Registros (canónico): **1,101** · copias en el árbol: 46 · variantes de esquema: 5
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\COMPRASM.DBF` (mod. 2010-02-10, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | CPROV | C | 4 | 0 |
| 9 | ANULADO | C | 1 | 0 |
| 10 | CONTADO | C | 1 | 0 |
| 11 | PAGADO | C | 1 | 0 |
| 12 | PORAJUSTE | L | 1 | 0 |
| 13 | MESIVA | C | 5 | 0 |
| 14 | CCOND | C | 2 | 0 |
| 15 | IMPORTACIO | N | 1 | 0 |
| 16 | CUENTA | C | 6 | 0 |
| 17 | CUENTANOGR | C | 6 | 0 |
| 18 | CUENTAOTRO | C | 6 | 0 |
| 19 | TASA1 | N | 5 | 2 |
| 20 | TASA2 | N | 5 | 2 |
| 21 | SOBRETASA | N | 5 | 2 |
| 22 | IVA1 | N | 10 | 2 |
| 23 | IVA2 | N | 10 | 2 |
| 24 | IMPIVA_1 | N | 10 | 2 |
| 25 | IMPIVA_2 | N | 10 | 2 |
| 26 | IMPIVA_3 | N | 10 | 2 |
| 27 | SUBTOTAL | N | 10 | 2 |
| 28 | IMPPER | N | 10 | 2 |
| 29 | IMPINT | N | 10 | 2 |
| 30 | INGBRU | N | 10 | 2 |
| 31 | IMPRET | N | 10 | 2 |
| 32 | OTROS | N | 10 | 2 |
| 33 | TDOLAR | N | 10 | 2 |
| 34 | DOLAR | N | 8 | 4 |
| 35 | DIF_COT | N | 8 | 2 |
| 36 | CHEQUES | N | 9 | 2 |
| 37 | EFECTIVO | N | 9 | 2 |
| 38 | EFT_A | N | 9 | 2 |
| 39 | EFT_D | N | 9 | 2 |
| 40 | DEPOSITO | N | 9 | 2 |
| 41 | IMPBCO | N | 9 | 2 |
| 42 | CTABCO | C | 15 | 0 |
| 43 | NMOVBCO | C | 8 | 0 |
| 44 | NMOV | C | 8 | 0 |
| 45 | RUBRO | C | 20 | 0 |
| 46 | NOMPROV | C | 30 | 0 |
| 47 | CUITPROV | C | 13 | 0 |
| 48 | REGPROV | N | 1 | 0 |
| 49 | NDESPACHO | C | 15 | 0 |
| 50 | ADUANA | C | 15 | 0 |
| 51 | ORIGEN | C | 15 | 0 |
| 52 | CAI | C | 14 | 0 |
| 53 | VTOCAI | D | 8 | 0 |
| 54 | FINPUT | D | 8 | 0 |
| 55 | OBSERVAC | M | 10 | 0 |

## CONC_CAJ
- Registros (canónico): **44** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\CONC_CAJ.DBF` (mod. 2007-09-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CCONC | C | 3 | 0 |
| 2 | NCONC | C | 30 | 0 |
| 3 | ENT_SAL | N | 1 | 0 |
| 4 | CUENTA | C | 6 | 0 |

## CONC_KAR
- Registros (canónico): **19** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\CONC_KAR.DBF` (mod. 2006-08-15, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CCONC | C | 2 | 0 |
| 2 | NCONC | C | 26 | 0 |
| 3 | ENT_SAL | N | 1 | 0 |

## CONVTA
- Registros (canónico): **18** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\convta.DBF` (mod. 2007-04-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CCOND | C | 2 | 0 |
| 2 | DIAS_1 | N | 3 | 0 |
| 3 | DIAS_2 | N | 3 | 0 |
| 4 | DIAS_3 | N | 3 | 0 |
| 5 | DIAS_4 | N | 3 | 0 |
| 6 | DIAS_5 | N | 3 | 0 |
| 7 | DIAS_6 | N | 3 | 0 |
| 8 | DIAS_7 | N | 3 | 0 |
| 9 | DIAS_8 | N | 3 | 0 |
| 10 | DIAS_9 | N | 3 | 0 |
| 11 | DIAS_10 | N | 3 | 0 |
| 12 | DIAS_11 | N | 3 | 0 |
| 13 | DIAS_12 | N | 3 | 0 |
| 14 | DESCOND | C | 26 | 0 |

## CUOTAS
- Registros (canónico): **4,653** · copias en el árbol: 42 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\CUOTAS.DBF` (mod. 2010-03-06, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | CODCLI | C | 4 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | NCUOTA | C | 2 | 0 |
| 8 | FECVTO | D | 8 | 0 |
| 9 | MONTO_A | N | 10 | 2 |
| 10 | MONTO_D | N | 10 | 2 |
| 11 | A_CUENTA | N | 10 | 2 |
| 12 | A_CUENTAD | N | 10 | 2 |
| 13 | DESC_A | N | 10 | 2 |
| 14 | DESC_D | N | 10 | 2 |

## CUOTASP
- Registros (canónico): **1,096** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\CUOTASP.DBF` (mod. 2010-02-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NCOMP | C | 8 | 0 |
| 3 | TCOMP | C | 1 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | CPROV | C | 4 | 0 |
| 6 | NCUOTA | C | 2 | 0 |
| 7 | FECVTO | D | 8 | 0 |
| 8 | MONTO_A | N | 10 | 2 |
| 9 | MONTO_D | N | 10 | 2 |
| 10 | A_CUENTA | N | 10 | 2 |
| 11 | A_CUENTAD | N | 10 | 2 |
| 12 | DESC_A | N | 10 | 2 |
| 13 | DESC_D | N | 10 | 2 |

## DEPOSITO
- Registros (canónico): **10** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\DEPOSITO.DBF` (mod. 2010-06-08, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | NDEP | C | 30 | 0 |
| 3 | MARCA | L | 1 | 0 |

## DESTINOS
- Registros (canónico): **127** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\destinos.dbf` (mod. 2008-12-29, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDESTINO | C | 4 | 0 |
| 2 | NDESTINO | C | 80 | 0 |
| 3 | DESDE | D | 8 | 0 |
| 4 | HASTA | D | 8 | 0 |

## DOM_ENT
- Registros (canónico): **180** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\dom_ent.dbf` (mod. 2008-11-20, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | SUCURSAL | C | 3 | 0 |
| 3 | DOMICILIO | C | 30 | 0 |
| 4 | CPOSTAL | C | 10 | 0 |
| 5 | LOCALIDAD | C | 30 | 0 |
| 6 | TELEFONOS | C | 30 | 0 |
| 7 | CONTACTO | C | 30 | 0 |
| 8 | NOMSUC | C | 30 | 0 |

## EJEMPLO FORMATO PARA IMPORTAR ARTICULOS DESDE EXCEL
- Registros (canónico): **3** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\ejemplo formato para importar articulos desde excel.DBF` (mod. 2007-01-20, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | B | C | 15 | 0 |
| 2 | D | C | 40 | 0 |
| 3 | E | N | 6 | 2 |
| 4 | F | C | 25 | 0 |
| 5 | G | C | 6 | 0 |
| 6 | H | N | 1 | 0 |
| 7 | I | N | 2 | 0 |

## EQUIPOS
- Registros (canónico): **2** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\EQUIPOS.DBF` (mod. 2003-06-09, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | EQUIPO | C | 8 | 0 |
| 2 | ESTADO | C | 70 | 0 |

## EQUIPOS_RED
- Registros (canónico): **19** · copias en el árbol: 21 · variantes de esquema: 3
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\OMEGA\Gestion Comercial\EQUIPOS_RED.DBF` (mod. 2009-11-09, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | EQUIPO | C | 60 | 0 |
| 2 | PUNTO | N | 4 | 0 |
| 3 | FISCAL | C | 60 | 0 |
| 4 | PUERTO | C | 1 | 0 |
| 5 | REF_CLI | L | 1 | 0 |
| 6 | PCONTAB | C | 250 | 0 |
| 7 | CDEP | C | 2 | 0 |
| 8 | SALIDA_OK | L | 1 | 0 |
| 9 | ACTIVO | L | 1 | 0 |

## ERRORES
- Registros (canónico): **260** · copias en el árbol: 50 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\super old\Super POS faytim\errores.DBF` (mod. 2005-09-26, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | HORA | C | 10 | 0 |
| 3 | ERROR | C | 10 | 0 |
| 4 | PROGRAMA | C | 60 | 0 |
| 5 | LINEA | N | 4 | 0 |
| 6 | MENSAJE | C | 50 | 0 |

## FACTPEDP
- Registros (canónico): **14** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\FACTPEDP.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | NPEDIDO | C | 8 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | CANTIDAD | N | 10 | 2 |
| 8 | PRECIO | N | 10 | 2 |
| 9 | BONIF_1 | N | 6 | 2 |
| 10 | BONIF_2 | N | 6 | 2 |

## FACT_PED
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\FACT_PED.DBF` (mod. 2010-04-17, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | NPEDIDO | C | 12 | 0 |
| 6 | ITEM | C | 2 | 0 |
| 7 | CODART | C | 15 | 0 |
| 8 | CANTIDAD | N | 10 | 2 |
| 9 | PRECIO | N | 10 | 2 |
| 10 | BONIF_1 | N | 6 | 2 |
| 11 | BONIF_2 | N | 6 | 2 |

## FACT_PPT
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\FACT_PPT.DBF` (mod. 2012-05-16, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPRESUP | C | 12 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | NFACTURA | C | 12 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | CODART | C | 15 | 0 |
| 6 | CANT_FACT | N | 10 | 2 |

## FACT_RTO
- Registros (canónico): **14** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\FACT_RTO.DBF` (mod. 2009-12-09, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NREMITO | C | 12 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | NFACTURA | C | 12 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | CODART | C | 15 | 0 |
| 6 | CANT_FACT | N | 10 | 2 |
| 7 | ITEM | C | 2 | 0 |

## FAMILIAS
- Registros (canónico): **65** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\super old\Faytim viejo andando reemplazar param de possss\POS\familias.dbf` (mod. 2007-10-16, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NFAMILIA | C | 30 | 0 |

## GASTOS
- Registros (canónico): **18** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Revosolution Gestion Comercial\GASTOS.DBF` (mod. 2010-04-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NRUBRO | C | 20 | 0 |
| 2 | CUENTA | C | 6 | 0 |

## IMPORTACION 01-04-2008
- Registros (canónico): **1,106** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\importacion 01-04-2008.DBF` (mod. 2008-05-16, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | C | 21 | 0 |
| 2 | B | C | 33 | 0 |
| 3 | C | C | 63 | 0 |
| 4 | E | N | 20 | 15 |
| 5 | F | N | 20 | 15 |
| 6 | G | N | 20 | 15 |
| 7 | H | N | 20 | 15 |
| 8 | I | N | 5 | 1 |
| 9 | J | N | 12 | 0 |
| 10 | K | N | 4 | 0 |
| 11 | L | N | 12 | 0 |
| 12 | M | C | 16 | 0 |

## IMPRESORAS
- Registros (canónico): **152** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\OMEGA\Gestion Comercial\IMPRESORAS.DBF` (mod. 2009-11-09, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | EQUIPO | C | 30 | 0 |
| 2 | PROCESO | C | 40 | 0 |
| 3 | IMPRESORA | C | 100 | 0 |

## MAECTA
- Registros (canónico): **7** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\maecta.DBF` (mod. 2012-05-16, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCUENTA | C | 15 | 0 |
| 2 | BANCO | C | 30 | 0 |
| 3 | FSALDO | D | 8 | 0 |
| 4 | SALDO | N | 10 | 2 |
| 5 | TSALDO | N | 1 | 0 |
| 6 | TIPO | N | 1 | 0 |
| 7 | OBSERVAC | M | 10 | 0 |
| 8 | CUENTA | C | 6 | 0 |
| 9 | CUIT | C | 13 | 0 |

## MARCA
- Registros (canónico): **5** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\MARCA.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | C | 10 | 0 |
| 2 | TIPOCOMP | C | 25 | 0 |
| 3 | DEBE | N | 10 | 2 |
| 4 | HABER | N | 10 | 2 |
| 5 | SALDO | N | 10 | 2 |

## MESAS
- Registros (canónico): **11,637** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Bonafide 11 2009\Super Restaurantes y Delivery\MESAS.DBF` (mod. 2009-11-17, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MESA | N | 10 | 0 |
| 2 | CODCLI | C | 10 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | DOMCLI | C | 40 | 0 |
| 5 | LOCCLI | C | 30 | 0 |
| 6 | PROVCLI | C | 15 | 0 |
| 7 | CONTACTO | C | 30 | 0 |
| 8 | GIRO | C | 30 | 0 |
| 9 | CVIAJ | C | 2 | 0 |
| 10 | NOMVIAJ | C | 30 | 0 |
| 11 | CODPOS | C | 10 | 0 |
| 12 | TELCLI_1 | C | 15 | 0 |
| 13 | TELCLI_2 | C | 15 | 0 |
| 14 | FAX | C | 15 | 0 |
| 15 | E_MAIL | C | 45 | 0 |
| 16 | DESCUENTO | N | 5 | 2 |
| 17 | CUITCLI | C | 22 | 0 |
| 18 | IVA | C | 10 | 0 |
| 19 | REGCLI | N | 1 | 0 |
| 20 | DNI | N | 8 | 0 |
| 21 | TOTAL | N | 10 | 2 |
| 22 | PORC_PROP | N | 5 | 2 |
| 23 | HORA | C | 5 | 0 |

## MOVCTAD
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\MOVCTAD.DBF` (mod. 2012-05-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | ITEM | C | 3 | 0 |
| 4 | NCHEQUE | N | 10 | 0 |
| 5 | IMPCHE | N | 10 | 2 |

## MOVCTAM
- Registros (canónico): **11** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\movctam.DBF` (mod. 2010-05-28, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | NCUENTA | C | 15 | 0 |
| 3 | FMOV | D | 8 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | CCONC | C | 3 | 0 |
| 6 | EFECTIVO | N | 10 | 2 |
| 7 | COMEN | C | 30 | 0 |
| 8 | BCO | N | 1 | 0 |

## MOVIM
- Registros (canónico): **2,066** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\movim.DBF` (mod. 2018-07-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | FMOV | D | 8 | 0 |
| 4 | COMEN | C | 33 | 0 |
| 5 | CCONC | C | 3 | 0 |
| 6 | EFT_A | N | 10 | 2 |
| 7 | EFT_D | N | 10 | 2 |
| 8 | TARJETAS | N | 10 | 2 |
| 9 | CAJA | N | 1 | 0 |
| 10 | DOLAR | N | 8 | 3 |

## MOVIMD
- Registros (canónico): **28** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\movimd.DBF` (mod. 2014-08-30, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | ITEM | C | 3 | 0 |
| 4 | NCHEQUE | N | 10 | 0 |

## MOV_STOC
- Registros (canónico): **442,482** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\mov_stoc.DBF` (mod. 2010-09-13, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCOMP | C | 20 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CDEP | C | 2 | 0 |
| 5 | CCONC | C | 2 | 0 |
| 6 | CANTIDAD | N | 10 | 2 |
| 7 | OBSERVAC | C | 45 | 0 |
| 8 | NDESPACHO | C | 15 | 0 |

## NUMEROS
- Registros (canónico): **30** · copias en el árbol: 38 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\numeros.DBF` (mod. 2018-07-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CIA | C | 1 | 0 |
| 2 | TCOMP | C | 1 | 0 |
| 3 | LETRA | C | 1 | 0 |
| 4 | PREFIJO | C | 4 | 0 |
| 5 | ULTIMO | N | 8 | 0 |
| 6 | EN_USO | L | 1 | 0 |

## OP_COMP
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\OP_COMP.DBF` (mod. 2012-05-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NRECIBO | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | CPROV | C | 4 | 0 |
| 4 | PREFIJO | C | 4 | 0 |
| 5 | NCOMP | C | 8 | 0 |
| 6 | TCOMP | C | 1 | 0 |
| 7 | NCUOTA | C | 2 | 0 |
| 8 | FECVTO | D | 8 | 0 |
| 9 | MONTO_A | N | 9 | 2 |
| 10 | MONTO_D | N | 9 | 2 |
| 11 | DESC_A | N | 8 | 2 |
| 12 | DESC_D | N | 8 | 2 |

## PAGOCLI
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\PAGOCLI.DBF` (mod. 2007-05-07, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCHEQUE | N | 10 | 0 |
| 2 | BANCO | C | 20 | 0 |
| 3 | PLAZA | C | 20 | 0 |
| 4 | FECVTO | D | 8 | 0 |
| 5 | FECCHE | D | 8 | 0 |
| 6 | IMPCHE | N | 12 | 2 |
| 7 | FIRMANTE | C | 30 | 0 |
| 8 | CUENTA | C | 20 | 0 |
| 9 | CUIT | C | 13 | 0 |

## PAGOPROV
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\PAGOPROV.DBF` (mod. 2007-08-22, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCHEQUE | N | 10 | 0 |
| 2 | NCTACTE | C | 15 | 0 |
| 3 | BANCO | C | 20 | 0 |
| 4 | PLAZA | C | 20 | 0 |
| 5 | FECVTO | D | 8 | 0 |
| 6 | FECCHE | D | 8 | 0 |
| 7 | IMPCHE | N | 12 | 2 |
| 8 | PROP_TER | N | 1 | 0 |
| 9 | CUIT | C | 13 | 0 |

## PEDCLID
- Registros (canónico): **8** · copias en el árbol: 21 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\PEDCLID.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CANT_PED | N | 10 | 2 |
| 5 | CANT_ENT | N | 10 | 2 |
| 6 | PRECIO | N | 10 | 2 |
| 7 | BONIF_1 | N | 5 | 2 |
| 8 | BONIF_2 | N | 5 | 2 |
| 9 | PARCIAL | N | 10 | 2 |
| 10 | CANCELADO | L | 1 | 0 |

## PEDCLIM
- Registros (canónico): **5** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\PEDCLIM.DBF` (mod. 2002-08-18, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | FPEDIDO | D | 8 | 0 |
| 4 | FENTREGA | D | 8 | 0 |
| 5 | CVIAJ | C | 2 | 0 |
| 6 | CCOND | C | 2 | 0 |
| 7 | DESCUENTO | N | 5 | 2 |
| 8 | TOTAL | N | 10 | 2 |
| 9 | OBSERVAC | M | 10 | 0 |

## PEDPRVD
- Registros (canónico): **20** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\PEDPRVD.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | CPROV | C | 4 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CANT_PED | N | 10 | 2 |
| 5 | CANT_ENT | N | 10 | 2 |
| 6 | PRECIO | N | 10 | 2 |
| 7 | BONIF_1 | N | 6 | 2 |
| 8 | BONIF_2 | N | 6 | 2 |
| 9 | PARCIAL | N | 10 | 2 |
| 10 | CANCELADO | L | 1 | 0 |

## PEDPRVM
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\pedprvm.dbf` (mod. 2006-03-29, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | CPROV | C | 4 | 0 |
| 3 | FPEDIDO | D | 8 | 0 |
| 4 | FENTREGA | D | 8 | 0 |
| 5 | CCOND | C | 2 | 0 |
| 6 | DESCUENTO | N | 5 | 2 |
| 7 | TOTAL | N | 11 | 2 |
| 8 | OBSERVAC | M | 10 | 0 |
| 9 | SOLICITA | C | 30 | 0 |
| 10 | IMPIVA_1 | N | 10 | 2 |
| 11 | IVA_1 | N | 10 | 2 |

## PERMISOS
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\PERMISOS.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | USUARIO | C | 8 | 0 |
| 2 | PROGRAMA | C | 10 | 0 |
| 3 | PERMITIDO | N | 1 | 0 |

## PLANILLA ARTICULOS
- Registros (canónico): **11** · copias en el árbol: 5 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Corp BsAs\Super POS\planilla articulos.DBF` (mod. 2008-09-25, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | N | 2 | 0 |
| 2 | B | N | 14 | 0 |
| 3 | C | C | 46 | 0 |
| 4 | E | N | 6 | 3 |
| 5 | F | N | 7 | 3 |
| 6 | I | N | 2 | 0 |
| 7 | J | N | 2 | 0 |
| 8 | M | C | 11 | 0 |

## PLATOS
- Registros (canónico): **2** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\PLATOS.DBF` (mod. 2003-03-01, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 10 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | OBSERVA | M | 4 | 0 |
| 4 | PVENTA_1 | N | 10 | 2 |
| 5 | TASA | N | 5 | 2 |
| 6 | RUBRO | C | 30 | 0 |

## PORAJUST
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\PORAJUST.DBF` (mod. 2012-05-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | NRO_OP | C | 8 | 0 |
| 7 | AJUSTE_COT | N | 8 | 2 |

## PRECIOS SYRA
- Registros (canónico): **80** · copias en el árbol: 17 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\precios syra.DBF` (mod. 2005-10-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | C | 11 | 0 |
| 2 | C | C | 104 | 0 |
| 3 | F | N | 8 | 3 |
| 4 | L | N | 11 | 0 |
| 5 | M | C | 89 | 0 |

## PREFIJOS
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\PREFIJOS.DBF` (mod. 2008-11-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | ELEC | L | 1 | 0 |

## PRESUPD
- Registros (canónico): **735** · copias en el árbol: 21 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\PRESUPD.DBF` (mod. 2010-09-09, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NCOMP | C | 8 | 0 |
| 3 | CIA | C | 1 | 0 |
| 4 | CODART | C | 15 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | CANTIDAD | N | 10 | 2 |
| 7 | BONIF_1 | N | 5 | 2 |
| 8 | BONIF_2 | N | 5 | 2 |
| 9 | PVENTA | N | 9 | 2 |
| 10 | EN_DOLARES | L | 1 | 0 |
| 11 | NDESPACHO | C | 15 | 0 |
| 12 | ADUANA | C | 15 | 0 |
| 13 | TASA | N | 5 | 2 |
| 14 | SNI | N | 5 | 2 |

## PRESUPM
- Registros (canónico): **118** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\PRESUPM.DBF` (mod. 2010-09-09, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NCOMP | C | 8 | 0 |
| 3 | CIA | C | 1 | 0 |
| 4 | FMOV | D | 8 | 0 |
| 5 | CODCLI | C | 4 | 0 |
| 6 | CCOND | C | 2 | 0 |
| 7 | CVIAJ | C | 2 | 0 |
| 8 | NFACTURA | C | 13 | 0 |
| 9 | TASA | N | 5 | 2 |
| 10 | SNI | N | 5 | 2 |
| 11 | IMPIVA_1 | N | 10 | 2 |
| 12 | IMPIVA_3 | N | 10 | 2 |
| 13 | IMP_SNI | N | 9 | 2 |
| 14 | SUBTOTAL | N | 10 | 2 |
| 15 | ANTES_DTO | N | 10 | 2 |
| 16 | IMP_DTO | N | 10 | 2 |
| 17 | POR_DTO | N | 5 | 2 |
| 18 | TDOLAR | N | 10 | 2 |
| 19 | DOLAR | N | 9 | 3 |
| 20 | RUBRO | C | 20 | 0 |
| 21 | NOMCLI | C | 30 | 0 |
| 22 | CUITCLI | C | 13 | 0 |
| 23 | REGCLI | N | 1 | 0 |
| 24 | TEXTO1 | M | 10 | 0 |
| 25 | IMPTEXTO1 | N | 9 | 2 |
| 26 | TASA1 | N | 5 | 2 |
| 27 | TEXTO2 | M | 10 | 0 |
| 28 | IMPTEXTO2 | N | 9 | 2 |
| 29 | TASA2 | N | 5 | 2 |
| 30 | TEXTO3 | M | 10 | 0 |
| 31 | IMPTEXTO3 | N | 9 | 2 |
| 32 | TASA3 | N | 5 | 2 |
| 33 | CUENTA1 | C | 6 | 0 |
| 34 | CUENTA2 | C | 6 | 0 |
| 35 | CUENTA3 | C | 6 | 0 |

## PRODUCTOS
- Registros (canónico): **490** · copias en el árbol: 7 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\productos.DBF` (mod. 2007-05-03, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | N | 20 | 2 |
| 2 | C | C | 34 | 0 |
| 3 | F | N | 20 | 15 |
| 4 | I | N | 2 | 0 |

## PROVEEDO
- Registros (canónico): **115** · copias en el árbol: 46 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\PROVEEDO.DBF` (mod. 2010-08-27, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | NOMPROV | C | 30 | 0 |
| 3 | DOMPROV | C | 35 | 0 |
| 4 | LOCPROV | C | 25 | 0 |
| 5 | PROVIN | C | 15 | 0 |
| 6 | CONTACTO | C | 40 | 0 |
| 7 | CODPOS | C | 10 | 0 |
| 8 | TELPROV_1 | C | 15 | 0 |
| 9 | TELPROV_2 | C | 15 | 0 |
| 10 | TELPROV_3 | C | 15 | 0 |
| 11 | TELPROV_4 | C | 15 | 0 |
| 12 | FAX | C | 15 | 0 |
| 13 | CCOND | C | 2 | 0 |
| 14 | E_MAIL | C | 45 | 0 |
| 15 | HTTP | C | 40 | 0 |
| 16 | CUITPROV | C | 13 | 0 |
| 17 | REGPROV | N | 1 | 0 |
| 18 | FSALPROV_1 | D | 8 | 0 |
| 19 | SALPROV_P1 | N | 10 | 2 |
| 20 | SALPROV_D1 | N | 10 | 2 |
| 21 | FSALPROV_2 | D | 8 | 0 |
| 22 | SALPROV_P2 | N | 10 | 2 |
| 23 | SALPROV_D2 | N | 10 | 2 |
| 24 | TSALDO | N | 1 | 0 |
| 25 | OBSERVAC | M | 10 | 0 |
| 26 | RUBRO | C | 20 | 0 |
| 27 | CAI | C | 14 | 0 |
| 28 | VTOCAI | D | 8 | 0 |

## PROVIN
- Registros (canónico): **26** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\PROVIN.DBF` (mod. 2007-07-26, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PROVIN | C | 15 | 0 |

## RC_COMP
- Registros (canónico): **4,129** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\RC_COMP.DBF` (mod. 2010-02-21, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFREC | C | 4 | 0 |
| 2 | NRECIBO | C | 8 | 0 |
| 3 | CIA | C | 1 | 0 |
| 4 | CODCLI | C | 4 | 0 |
| 5 | LETRA | C | 1 | 0 |
| 6 | PREFIJO | C | 4 | 0 |
| 7 | NCOMP | C | 8 | 0 |
| 8 | TCOMP | C | 1 | 0 |
| 9 | NCUOTA | C | 2 | 0 |
| 10 | FECVTO | D | 8 | 0 |
| 11 | MONTO_A | N | 9 | 2 |
| 12 | MONTO_D | N | 9 | 2 |
| 13 | DESC_A | N | 8 | 2 |
| 14 | DESC_D | N | 8 | 2 |

## RECIBOPD
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\RECIBOPD.DBF` (mod. 2010-05-03, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NRECIBO | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | NCHEQUE | N | 10 | 0 |

## RECIBOPM
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\recibopm.DBF` (mod. 2010-05-03, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NRECIBO | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | TRECIBO | C | 1 | 0 |
| 4 | FRECIBO | D | 8 | 0 |
| 5 | CPROV | C | 4 | 0 |
| 6 | MONTO_A | N | 12 | 2 |
| 7 | MONTO_D | N | 12 | 2 |
| 8 | DESC_A | N | 10 | 2 |
| 9 | DESC_D | N | 10 | 2 |
| 10 | APLICADO_A | N | 10 | 2 |
| 11 | APLICADO_D | N | 10 | 2 |
| 12 | EFECTIVO_A | N | 12 | 2 |
| 13 | EFECTIVO_D | N | 12 | 2 |
| 14 | DOLAR | N | 8 | 4 |
| 15 | NRO_ASIENT | C | 6 | 0 |
| 16 | NMOV | C | 8 | 0 |
| 17 | SALDO_ANT | L | 1 | 0 |
| 18 | TASA | N | 5 | 2 |
| 19 | NOMPROV | C | 30 | 0 |
| 20 | CUITPROV | C | 13 | 0 |
| 21 | REGPROV | N | 1 | 0 |
| 22 | A_CUENTA | N | 10 | 2 |
| 23 | AJUSTE_COT | N | 8 | 2 |
| 24 | COMPAJUSTE | C | 14 | 0 |
| 25 | DEPOSITO | N | 10 | 2 |
| 26 | IMPBCO | N | 10 | 2 |
| 27 | CTABCO | C | 15 | 0 |
| 28 | NMOVBCO | C | 8 | 0 |
| 29 | OBSERVAC | C | 40 | 0 |

## RECIBOSD
- Registros (canónico): **21** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\RECIBOSD.DBF` (mod. 2014-08-05, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NRECIBO | C | 8 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | NCHEQUE | N | 10 | 0 |

## RECIBOSM
- Registros (canónico): **1,097** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\RECIBOSM.DBF` (mod. 2010-02-21, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NRECIBO | C | 8 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | TRECIBO | C | 1 | 0 |
| 6 | FRECIBO | D | 8 | 0 |
| 7 | CODCLI | C | 4 | 0 |
| 8 | TASA | N | 5 | 2 |
| 9 | MONTO_A | N | 12 | 2 |
| 10 | MONTO_D | N | 12 | 2 |
| 11 | DESC_A | N | 10 | 2 |
| 12 | DESC_D | N | 10 | 2 |
| 13 | APLICADO_A | N | 10 | 2 |
| 14 | APLICADO_D | N | 10 | 2 |
| 15 | EFECTIVO_A | N | 12 | 2 |
| 16 | EFECTIVO_D | N | 12 | 2 |
| 17 | IMPBCO | N | 10 | 2 |
| 18 | IMPTAR | N | 10 | 2 |
| 19 | NRO_ASIENT | C | 6 | 0 |
| 20 | NMOV | C | 8 | 0 |
| 21 | DOLAR | N | 8 | 4 |
| 22 | AJUSTE_COT | N | 8 | 2 |
| 23 | COMPAJUSTE | C | 14 | 0 |
| 24 | CVIAJ | C | 2 | 0 |
| 25 | LIQUIDA | L | 1 | 0 |
| 26 | SALDO_ANT | L | 1 | 0 |
| 27 | NOMCLI | C | 30 | 0 |
| 28 | CUITCLI | C | 13 | 0 |
| 29 | REGCLI | N | 1 | 0 |
| 30 | PROVCLI | C | 15 | 0 |
| 31 | A_CUENTA | N | 10 | 2 |
| 32 | CTABCO | C | 15 | 0 |
| 33 | NMOVBCO | C | 8 | 0 |
| 34 | LOTE | C | 5 | 0 |
| 35 | CUPON | C | 15 | 0 |
| 36 | CRED_DEB | N | 1 | 0 |
| 37 | TARJETA | C | 20 | 0 |
| 38 | CANT_CUOTA | N | 2 | 0 |
| 39 | OBSERVAC | C | 40 | 0 |

## RECURSOS
- Registros (canónico): **2** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\RECURSOS.DBF` (mod. 2002-09-05, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NOMBRE | C | 40 | 0 |

## REMITOPD
- Registros (canónico): **2** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\REMITOPD.DBF` (mod. 2009-11-30, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NCOMP | C | 8 | 0 |
| 3 | CPROV | C | 4 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | CODART | C | 15 | 0 |
| 6 | CDEP | C | 2 | 0 |
| 7 | CANTIDAD | N | 10 | 2 |

## REMITOPM
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\REMITOPM.DBF` (mod. 2010-05-31, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | CPROV | C | 4 | 0 |
| 7 | NOMPROV | C | 30 | 0 |
| 8 | FKARDEX | D | 8 | 0 |
| 9 | OBSERVAC | M | 10 | 0 |

## REMITOSD
- Registros (canónico): **14** · copias en el árbol: 21 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\remitosd.DBF` (mod. 2009-12-09, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | CIA | C | 1 | 0 |
| 4 | CODART | C | 15 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | CANTIDAD | N | 10 | 2 |
| 7 | PRECIO | N | 10 | 2 |
| 8 | EN_DOLARES | L | 1 | 0 |
| 9 | NDESPACHO | C | 15 | 0 |
| 10 | ADUANA | C | 15 | 0 |
| 11 | TASA | N | 5 | 2 |
| 12 | ITEM | C | 2 | 0 |

## REMITOSM
- Registros (canónico): **11** · copias en el árbol: 21 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\REMITOSM.DBF` (mod. 2010-07-12, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | CIA | C | 1 | 0 |
| 4 | FMOV | D | 8 | 0 |
| 5 | CODCLI | C | 4 | 0 |
| 6 | TREMITO | C | 1 | 0 |
| 7 | CTRANSP | C | 3 | 0 |
| 8 | CDEP1 | C | 2 | 0 |
| 9 | CDEP2 | C | 2 | 0 |
| 10 | CONTROLO | C | 20 | 0 |
| 11 | VAL_DEC | N | 8 | 2 |
| 12 | BULTOS | N | 3 | 0 |
| 13 | OBSERVAC | M | 10 | 0 |
| 14 | DOLAR | N | 8 | 3 |
| 15 | PENDIENTE | L | 1 | 0 |
| 16 | PROVEEDOR | L | 1 | 0 |
| 17 | OCOMPRA | C | 15 | 0 |

## RETENCIO
- Registros (canónico): **4** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\RETENCIO.DBF` (mod. 2006-07-11, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CRET | C | 2 | 0 |
| 2 | NRET | C | 25 | 0 |
| 3 | CUENTA | C | 6 | 0 |

## RET_CLI
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\RET_CLI.DBF` (mod. 2012-05-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NRECIBO | C | 8 | 0 |
| 3 | LETRA | C | 1 | 0 |
| 4 | PREFIJO | C | 4 | 0 |
| 5 | NCOMP | C | 8 | 0 |
| 6 | TCOMP | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | RETENCION | C | 25 | 0 |
| 9 | IMPORTE | N | 10 | 2 |
| 10 | FRETEN | D | 8 | 0 |
| 11 | NRETEN | C | 12 | 0 |

## RET_PROV
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\RET_PROV.DBF` (mod. 2012-05-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | NRECIBO | C | 8 | 0 |
| 3 | LETRA | C | 1 | 0 |
| 4 | PREFIJO | C | 4 | 0 |
| 5 | NCOMP | C | 8 | 0 |
| 6 | TCOMP | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | RETENCION | C | 25 | 0 |
| 9 | IMPORTE | N | 10 | 2 |

## RUBROS
- Registros (canónico): **5** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\RUBROS.DBF` (mod. 2002-11-29, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NRUBRO | C | 20 | 0 |

## SALCAJA
- Registros (canónico): **68** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Super\SALCAJA.DBF` (mod. 2007-12-19, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | EFT_A | N | 10 | 2 |
| 3 | EFT_D | N | 10 | 2 |
| 4 | CHEQUES | N | 10 | 2 |

## STOCK
- Registros (canónico): **127,580** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Super\stock.DBF` (mod. 2007-12-19, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | CDEP | C | 2 | 0 |
| 3 | UBICACION | C | 10 | 0 |
| 4 | MINIMO | N | 10 | 2 |
| 5 | FSALDO | D | 8 | 0 |
| 6 | SALDO | N | 10 | 2 |

## SUBFLIA
- Registros (canónico): **33** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\SUBFLIA.DBF` (mod. 2009-12-02, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NFAMILIA | C | 30 | 0 |
| 2 | NSUBF | C | 30 | 0 |

## TABLAIVA
- Registros (canónico): **187,860** · copias en el árbol: 50 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\tablaiva.dbf` (mod. 2018-07-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | TASA | N | 5 | 2 |
| 6 | SNI | N | 5 | 2 |
| 7 | NETO | N | 10 | 2 |
| 8 | IVA | N | 10 | 2 |
| 9 | SOBRETASA | N | 10 | 2 |

## TARJETAS
- Registros (canónico): **11** · copias en el árbol: 50 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\tarjetas.dbf` (mod. 2010-05-05, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NTARJETA | C | 20 | 0 |
| 2 | BANCO | C | 20 | 0 |
| 3 | RETENCION | N | 5 | 2 |
| 4 | CUENTA | C | 6 | 0 |
| 5 | CRED_DEB | N | 1 | 0 |
| 6 | RECAR01 | N | 6 | 2 |
| 7 | RECAR02 | N | 6 | 2 |
| 8 | RECAR03 | N | 6 | 2 |
| 9 | RECAR04 | N | 6 | 2 |
| 10 | RECAR05 | N | 6 | 2 |
| 11 | RECAR06 | N | 6 | 2 |
| 12 | RECAR07 | N | 6 | 2 |
| 13 | RECAR08 | N | 6 | 2 |
| 14 | RECAR09 | N | 6 | 2 |
| 15 | RECAR10 | N | 6 | 2 |
| 16 | RECAR11 | N | 6 | 2 |
| 17 | RECAR12 | N | 6 | 2 |

## TRANSPOR
- Registros (canónico): **5** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\TRANSPOR.DBF` (mod. 2008-10-29, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CTRANSP | C | 3 | 0 |
| 2 | NTRANSP | C | 30 | 0 |
| 3 | DTRANSP | C | 30 | 0 |
| 4 | CUITRANSP | C | 13 | 0 |
| 5 | TELTRANSP | C | 30 | 0 |
| 6 | FAXTRANSP | C | 20 | 0 |
| 7 | LOCTRANSP | C | 20 | 0 |
| 8 | CONTACTO | C | 30 | 0 |

## UNC
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\unc.dbf` (mod. 2010-04-17, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | EQUIPO | C | 30 | 0 |
| 2 | PUNTO | N | 4 | 0 |
| 3 | FISCAL | C | 50 | 0 |
| 4 | COM | N | 1 | 0 |

## USUARIOS
- Registros (canónico): **7** · copias en el árbol: 50 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\USUARIOS.DBF` (mod. 2010-05-05, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | USUARIO | C | 8 | 0 |
| 2 | CONTRA | C | 4 | 0 |
| 3 | GV0090 | L | 1 | 0 |
| 4 | GV0002 | L | 1 | 0 |
| 5 | GV0016 | L | 1 | 0 |
| 6 | GV0050 | L | 1 | 0 |
| 7 | GV0006 | L | 1 | 0 |
| 8 | GV0007 | L | 1 | 0 |
| 9 | GV0022 | L | 1 | 0 |
| 10 | GV0013 | L | 1 | 0 |
| 11 | SINCODIF | L | 1 | 0 |
| 12 | ESTAD | L | 1 | 0 |
| 13 | GV0500 | L | 1 | 0 |
| 14 | GV0501 | L | 1 | 0 |
| 15 | STOCK | L | 1 | 0 |
| 16 | PRECIOS | L | 1 | 0 |
| 17 | EQUIS | L | 1 | 0 |
| 18 | GV0098 | L | 1 | 0 |
| 19 | GV0094 | L | 1 | 0 |
| 20 | GV0040 | L | 1 | 0 |
| 21 | GV0035 | L | 1 | 0 |
| 22 | GV0036 | L | 1 | 0 |
| 23 | IMPORTAR | L | 1 | 0 |

## VENCIC
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\VENCIC.DBF` (mod. 2006-07-05, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | TIPOCOMP | C | 30 | 0 |
| 3 | LETRA | C | 1 | 0 |
| 4 | PREFIJO | C | 4 | 0 |
| 5 | NCOMP | C | 8 | 0 |
| 6 | TCOMP | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | TOTAL | N | 10 | 2 |
| 9 | NCUOTA | C | 2 | 0 |
| 10 | FECVTO | D | 8 | 0 |
| 11 | IMPCUOTA | N | 10 | 2 |
| 12 | PAGADO | N | 10 | 2 |
| 13 | SALDO | N | 10 | 2 |
| 14 | DESCUENTO | N | 10 | 2 |
| 15 | NETO | N | 10 | 2 |
| 16 | SELECC | C | 12 | 0 |
| 17 | DOLAR | N | 10 | 4 |
| 18 | MARCADO | L | 1 | 0 |

## VENCIC1
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\vencic1.dbf` (mod. 2005-01-20, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | REGISTRO | C | 10 | 0 |

## VENCIP
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\vencip.DBF` (mod. 2007-06-27, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | TIPOCOMP | C | 30 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | FMOV | D | 8 | 0 |
| 7 | TOTAL | N | 10 | 2 |
| 8 | NCUOTA | C | 2 | 0 |
| 9 | FECVTO | D | 8 | 0 |
| 10 | IMPCUOTA | N | 10 | 2 |
| 11 | PAGADO | N | 10 | 2 |
| 12 | SALDO | N | 10 | 2 |
| 13 | DESCUENTO | N | 10 | 2 |
| 14 | NETO | N | 10 | 2 |
| 15 | SELECC | L | 1 | 0 |
| 16 | LETRA | C | 1 | 0 |

## VENCIP1
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\vencip1.dbf` (mod. 2005-01-20, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | REGISTRO | C | 10 | 0 |

## VENTASD
- Registros (canónico): **449,683** · copias en el árbol: 50 · variantes de esquema: 7
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\ventasd.DBF` (mod. 2010-09-13, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | CIA | C | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | CDEP | C | 2 | 0 |
| 9 | CANTIDAD | N | 10 | 2 |
| 10 | BONIF_1 | N | 5 | 2 |
| 11 | BONIF_2 | N | 5 | 2 |
| 12 | PVENTA | N | 9 | 2 |
| 13 | PVENTA_D | N | 9 | 2 |
| 14 | POR_REMITO | N | 10 | 2 |
| 15 | NDESPACHO | C | 15 | 0 |
| 16 | ADUANA | C | 15 | 0 |
| 17 | TASA | N | 5 | 2 |
| 18 | SNI | N | 5 | 2 |
| 19 | COSTO | N | 9 | 2 |

## VENTASM
- Registros (canónico): **139,753** · copias en el árbol: 50 · variantes de esquema: 9
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\VENTASM.DBF` (mod. 2010-02-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | CODCLI | C | 4 | 0 |
| 9 | ANULADO | C | 1 | 0 |
| 10 | CONTADO | C | 1 | 0 |
| 11 | PAGADO | C | 1 | 0 |
| 12 | PORAJUSTE | L | 1 | 0 |
| 13 | ACT_STOCK | C | 1 | 0 |
| 14 | CCOND | C | 2 | 0 |
| 15 | CVIAJ | C | 2 | 0 |
| 16 | LIQUIDA | L | 1 | 0 |
| 17 | NRO_PRESUP | C | 12 | 0 |
| 18 | TASA | N | 5 | 2 |
| 19 | SNI | N | 5 | 2 |
| 20 | BIEN_USO | L | 1 | 0 |
| 21 | IMPIVA_1 | N | 10 | 2 |
| 22 | IMPIVA_3 | N | 10 | 2 |
| 23 | IMP_SNI | N | 9 | 2 |
| 24 | SUBTOTAL | N | 10 | 2 |
| 25 | ANTES_DTO | N | 10 | 2 |
| 26 | IMP_DTO | N | 10 | 2 |
| 27 | POR_DTO | N | 5 | 2 |
| 28 | TDOLAR | N | 10 | 2 |
| 29 | DOLAR | N | 8 | 4 |
| 30 | DIF_COT | N | 8 | 2 |
| 31 | CHEQUES | N | 9 | 2 |
| 32 | EFECTIVO | N | 9 | 2 |
| 33 | EFT_A | N | 9 | 2 |
| 34 | EFT_D | N | 9 | 2 |
| 35 | NMOV | C | 8 | 0 |
| 36 | RUBRO | C | 20 | 0 |
| 37 | NOMCLI | C | 40 | 0 |
| 38 | CUITCLI | C | 13 | 0 |
| 39 | REGCLI | N | 1 | 0 |
| 40 | PROVCLI | C | 15 | 0 |
| 41 | TEXTO1 | M | 4 | 0 |
| 42 | IMPTEXTO1 | N | 9 | 2 |
| 43 | TASA1 | N | 5 | 2 |
| 44 | TEXTO2 | M | 4 | 0 |
| 45 | IMPTEXTO2 | N | 9 | 2 |
| 46 | TASA2 | N | 5 | 2 |
| 47 | TEXTO3 | M | 4 | 0 |
| 48 | IMPTEXTO3 | N | 9 | 2 |
| 49 | TASA3 | N | 5 | 2 |
| 50 | CUENTA1 | C | 6 | 0 |
| 51 | CUENTA2 | C | 6 | 0 |
| 52 | CUENTA3 | C | 6 | 0 |
| 53 | TARJETA | C | 20 | 0 |
| 54 | CUPON | C | 20 | 0 |
| 55 | IMPTAR | N | 10 | 2 |
| 56 | RECARGO | N | 10 | 2 |
| 57 | CUOTAS | N | 2 | 0 |
| 58 | LOTE | C | 5 | 0 |
| 59 | CRED_DEB | N | 1 | 0 |
| 60 | CTABCO | C | 15 | 0 |
| 61 | IMPBCO | N | 10 | 2 |
| 62 | NMOVBCO | C | 8 | 0 |
| 63 | NRECIBO | C | 8 | 0 |
| 64 | IMPSALDO | N | 8 | 2 |
| 65 | COSTO | N | 10 | 2 |
| 66 | OCOMPRA | C | 15 | 0 |
| 67 | FECHAHORA | T | 8 | 0 |

## VIAJANTE
- Registros (canónico): **29** · copias en el árbol: 50 · variantes de esquema: 3
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Bonafide 11 2009\Super Restaurantes y Delivery\VIAJANTE.DBF` (mod. 2009-10-27, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CVIAJ | C | 2 | 0 |
| 2 | NOMVIAJ | C | 30 | 0 |
| 3 | DOMVIAJ | C | 30 | 0 |
| 4 | TELVIAJ | C | 30 | 0 |
| 5 | COMISION | N | 5 | 2 |

## ZON
- Registros (canónico): **2** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\ZON.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NOMBRE | C | 8 | 0 |
| 2 | DESCRIP | C | 30 | 0 |

---

# Categoría: facturacion electronica

## ERR_FE
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\err_fe.DBF` (mod. 2009-01-02, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | RENGLON | C | 250 | 0 |

## F136HIST
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\F136HIST.DBF` (mod. 2008-12-31, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | F136 | C | 24 | 0 |
| 2 | RESPUESTA | C | 128 | 0 |

## FE0001
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\FE0001.DBF` (mod. 2008-12-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 228 | 0 |
| 2 | CAMPO2 | C | 62 | 0 |

## FE0003A
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\fe0003a.DBF` (mod. 2008-12-12, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 245 | 0 |
| 2 | CAMPO2 | C | 45 | 0 |

## FE0003B
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\fe0003b.DBF` (mod. 2008-12-12, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 189 | 0 |

## FE0003C
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\fe0003c.DBF` (mod. 2008-12-12, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 253 | 0 |
| 2 | CAMPO2 | C | 122 | 0 |

## FE0003D
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\fe0003d.DBF` (mod. 2008-12-12, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 240 | 0 |
| 2 | CAMPO2 | C | 129 | 0 |

## FE0004
- Registros (canónico): **2** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\Fe0004.DBF` (mod. 2009-01-02, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | CODCLI | C | 4 | 0 |
| 9 | ANULADO | C | 1 | 0 |
| 10 | CONTADO | C | 1 | 0 |
| 11 | PAGADO | C | 1 | 0 |
| 12 | PORAJUSTE | L | 1 | 0 |
| 13 | ACT_STOCK | C | 1 | 0 |
| 14 | CCOND | C | 2 | 0 |
| 15 | CVIAJ | C | 2 | 0 |
| 16 | LIQUIDA | L | 1 | 0 |
| 17 | NRO_PRESUP | C | 12 | 0 |
| 18 | TASA | N | 5 | 2 |
| 19 | SNI | N | 5 | 2 |
| 20 | BIEN_USO | L | 1 | 0 |
| 21 | IMPIVA_1 | N | 10 | 2 |
| 22 | IMPIVA_3 | N | 10 | 2 |
| 23 | IMP_SNI | N | 9 | 2 |
| 24 | SUBTOTAL | N | 10 | 2 |
| 25 | ANTES_DTO | N | 10 | 2 |
| 26 | IMP_DTO | N | 10 | 2 |
| 27 | POR_DTO | N | 5 | 2 |
| 28 | TDOLAR | N | 10 | 2 |
| 29 | DOLAR | N | 8 | 4 |
| 30 | DIF_COT | N | 8 | 2 |
| 31 | CHEQUES | N | 9 | 2 |
| 32 | EFECTIVO | N | 9 | 2 |
| 33 | EFT_A | N | 9 | 2 |
| 34 | EFT_D | N | 9 | 2 |
| 35 | NMOV | C | 8 | 0 |
| 36 | RUBRO | C | 20 | 0 |
| 37 | NOMCLI | C | 40 | 0 |
| 38 | CUITCLI | C | 13 | 0 |
| 39 | REGCLI | N | 1 | 0 |
| 40 | PROVCLI | C | 15 | 0 |
| 41 | TEXTO1 | M | 4 | 0 |
| 42 | IMPTEXTO1 | N | 9 | 2 |
| 43 | TASA1 | N | 5 | 2 |
| 44 | TEXTO2 | M | 4 | 0 |
| 45 | IMPTEXTO2 | N | 9 | 2 |
| 46 | TASA2 | N | 5 | 2 |
| 47 | TEXTO3 | M | 4 | 0 |
| 48 | IMPTEXTO3 | N | 9 | 2 |
| 49 | TASA3 | N | 5 | 2 |
| 50 | CUENTA1 | C | 6 | 0 |
| 51 | CUENTA2 | C | 6 | 0 |
| 52 | CUENTA3 | C | 6 | 0 |
| 53 | TARJETA | C | 20 | 0 |
| 54 | CUPON | C | 20 | 0 |
| 55 | IMPTAR | N | 10 | 2 |
| 56 | RECARGO | N | 10 | 2 |
| 57 | CUOTAS | N | 2 | 0 |
| 58 | LOTE | C | 5 | 0 |
| 59 | CRED_DEB | N | 1 | 0 |
| 60 | CTABCO | C | 15 | 0 |
| 61 | IMPBCO | N | 10 | 2 |
| 62 | NMOVBCO | C | 8 | 0 |
| 63 | NRECIBO | C | 8 | 0 |
| 64 | IMPSALDO | N | 8 | 2 |
| 65 | COSTO | N | 10 | 2 |
| 66 | OCOMPRA | C | 15 | 0 |
| 67 | MEDIO_TRAN | C | 40 | 0 |
| 68 | EMBARQUE | C | 40 | 0 |
| 69 | LOCCLI | C | 30 | 0 |
| 70 | CODPOS | C | 10 | 0 |
| 71 | DOMCLI | C | 60 | 0 |
| 72 | ELECTRO | N | 1 | 0 |
| 73 | CAE | C | 14 | 0 |
| 74 | FECHACAE | D | 8 | 0 |
| 75 | VTOCAE | D | 8 | 0 |
| 76 | SERVICIO | N | 1 | 0 |
| 77 | NSOLICITUD | N | 4 | 0 |
| 78 | RESULTADO | C | 1 | 0 |
| 79 | COD_MOTIVO | C | 8 | 0 |
| 80 | MOTIVO | C | 11 | 0 |
| 81 | FRECHAZO | D | 8 | 0 |
| 82 | FDESDE | D | 8 | 0 |
| 83 | FHASTA | D | 8 | 0 |
| 84 | FPAGO | D | 8 | 0 |
| 85 | DNI | C | 8 | 0 |
| 86 | CONTROLAD | C | 1 | 0 |
| 87 | CAI | C | 14 | 0 |
| 88 | FCAI | D | 8 | 0 |
| 89 | FANULA | D | 8 | 0 |

## SOL_CAE
- Registros (canónico): **1** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\SOL_CAE.DBF` (mod. 2009-01-09, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NSOLICITUD | N | 4 | 0 |
| 3 | PERIODO | C | 6 | 0 |

---

# Categoría: interna (GV)

## GV000220
- Registros (canónico): **2** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV000220.DBF` (mod. 2009-10-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | CODCLI | C | 4 | 0 |
| 7 | ANULADO | C | 1 | 0 |
| 8 | NOMCLI | C | 30 | 0 |
| 9 | CODART | C | 15 | 0 |
| 10 | CDEP | C | 2 | 0 |
| 11 | CANTIDAD | N | 10 | 2 |
| 12 | BONIF_1 | N | 6 | 2 |
| 13 | BONIF_2 | N | 6 | 2 |
| 14 | PVENTA | N | 9 | 2 |
| 15 | PVENTA_D | N | 9 | 2 |

## GV0002A
- Registros (canónico): **10** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0002A.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | NDEP | C | 30 | 0 |
| 3 | KARDEX | N | 10 | 2 |
| 4 | STOCK | N | 10 | 2 |
| 5 | UBICACION | C | 10 | 0 |
| 6 | MINIMO | N | 10 | 2 |
| 7 | FSALDO | D | 8 | 0 |
| 8 | SALDO | N | 10 | 2 |
| 9 | FALTAN | N | 10 | 2 |

## GV0002B
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GV0002B.DBF` (mod. 2007-03-29, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCOMP | C | 20 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | AUXILIO | C | 10 | 0 |
| 4 | CONCEPTO | C | 26 | 0 |
| 5 | ENTRADA | N | 10 | 2 |
| 6 | SALIDA | N | 10 | 2 |
| 7 | SALDO | N | 10 | 2 |
| 8 | OBSERVAC | C | 45 | 0 |

## GV0002C
- Registros (canónico): **3** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0002C.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCOMP | C | 20 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | AUXILIO | C | 10 | 0 |
| 4 | CONCEPTO | C | 25 | 0 |
| 5 | ENTRADA | N | 10 | 2 |
| 6 | SALIDA | N | 10 | 2 |
| 7 | SALDO | N | 10 | 2 |
| 8 | OBSERVAC | C | 20 | 0 |

## GV0002D
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0002D.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | AUXILIO | C | 10 | 0 |
| 3 | NCOMP | C | 20 | 0 |
| 4 | NOMPROV | C | 30 | 0 |
| 5 | NDESPACHO | C | 20 | 0 |
| 6 | CANTIDAD | N | 10 | 2 |
| 7 | PRECIO | N | 10 | 2 |
| 8 | BONIF_1 | N | 6 | 2 |
| 9 | BONIF_2 | N | 6 | 2 |
| 10 | TOTAL | N | 10 | 2 |
| 11 | ADUANA | C | 20 | 0 |

## GV0002E
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0002E.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | AUXILIO | C | 10 | 0 |
| 3 | NCOMP | C | 20 | 0 |
| 4 | NOMPROV | C | 30 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | PRECIO | N | 10 | 2 |
| 7 | BONIF_1 | N | 6 | 2 |
| 8 | BONIF_2 | N | 6 | 2 |
| 9 | TOTAL | N | 10 | 2 |

## GV0002G
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0002G.DBF` (mod. 2006-07-07, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 35 | 0 |
| 3 | TIPOCOMP | C | 27 | 0 |
| 4 | FECHA | C | 10 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | CANTIDAD | N | 8 | 2 |
| 7 | PRECIO | N | 9 | 2 |
| 8 | PARCIAL | N | 10 | 2 |

## GV0003
- Registros (canónico): **5** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\gv0003.dbf` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | FAMILIA | C | 25 | 0 |
| 5 | UNIDAD | C | 5 | 0 |
| 6 | CPROV | C | 4 | 0 |
| 7 | NOMPROV | C | 30 | 0 |
| 8 | COSTO | N | 8 | 2 |
| 9 | UTIL_1 | N | 5 | 2 |
| 10 | UTIL_2 | N | 5 | 2 |
| 11 | PVENTA_1 | N | 8 | 2 |
| 12 | PVENTA_2 | N | 8 | 2 |
| 13 | BONIF_11 | N | 5 | 2 |
| 14 | BONIF_12 | N | 5 | 2 |
| 15 | BONIF_21 | N | 5 | 2 |
| 16 | BONIF_22 | N | 5 | 2 |

## GV0004
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0004.DBF` (mod. 2008-06-25, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | IMPRIMIR | L | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | CODPROVE | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | FAMILIA | C | 51 | 0 |
| 6 | UNIDAD | C | 5 | 0 |
| 7 | NOMPROV | C | 30 | 0 |
| 8 | STOCK | N | 10 | 2 |
| 9 | UBICACION | C | 10 | 0 |
| 10 | AUXILIO | C | 51 | 0 |
| 11 | MINIMO | N | 10 | 2 |
| 12 | REPONER | N | 10 | 2 |
| 13 | PRECIO | N | 8 | 2 |
| 14 | TOTAL | N | 10 | 2 |
| 15 | COSTO | N | 10 | 3 |
| 16 | VALOR | N | 10 | 2 |

## GV0005
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0005.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | IMPRIMIR | L | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | FAMILIA | C | 51 | 0 |
| 5 | UNIDAD | C | 6 | 0 |
| 6 | NOMPROV | C | 30 | 0 |
| 7 | STOCK | N | 10 | 2 |
| 8 | UBICACION | C | 10 | 0 |
| 9 | AUXILIO | C | 51 | 0 |
| 10 | MINIMO | N | 10 | 2 |
| 11 | REPONER | N | 10 | 2 |
| 12 | PRECIO | N | 8 | 2 |
| 13 | TOTAL | N | 10 | 2 |

## GV0005A
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0005A.DBF` (mod. 2006-09-08, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | FAMILIA | C | 51 | 0 |
| 4 | UNIDAD | C | 6 | 0 |
| 5 | NOMPROV | C | 30 | 0 |
| 6 | UBICACION | C | 15 | 0 |
| 7 | STOCK | N | 10 | 2 |
| 8 | STK01 | N | 10 | 2 |
| 9 | STK02 | N | 10 | 2 |
| 10 | STK03 | N | 10 | 2 |
| 11 | STK04 | N | 10 | 2 |
| 12 | STK05 | N | 10 | 2 |
| 13 | STK06 | N | 10 | 2 |
| 14 | STK07 | N | 10 | 2 |
| 15 | STK08 | N | 10 | 2 |
| 16 | STK09 | N | 10 | 2 |
| 17 | STK10 | N | 10 | 2 |
| 18 | COSTO | N | 9 | 2 |
| 19 | PVENTA_1 | N | 9 | 2 |
| 20 | PVENTA_2 | N | 9 | 2 |

## GV0007
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 5
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0007.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 6 | 0 |
| 4 | CDEP | C | 2 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | POR_REMITO | N | 10 | 2 |
| 7 | PRECIO | N | 9 | 3 |
| 8 | COSTIVA | N | 1 | 0 |
| 9 | BONIF_1 | N | 6 | 2 |
| 10 | BONIF_2 | N | 6 | 2 |
| 11 | PARCIAL | N | 11 | 3 |
| 12 | ACT_COSTO | L | 1 | 0 |
| 13 | ACT_PRECIO | N | 1 | 0 |
| 14 | UTIL_1 | N | 6 | 2 |
| 15 | UTIL_2 | N | 6 | 2 |
| 16 | UTIL_3 | N | 6 | 2 |
| 17 | UTIL_4 | N | 6 | 2 |
| 18 | PVENTA_1 | N | 10 | 2 |
| 19 | PVENTA_2 | N | 10 | 2 |
| 20 | PVENTA_3 | N | 10 | 2 |
| 21 | PVENTA_4 | N | 10 | 2 |
| 22 | BONIF_11 | N | 5 | 2 |
| 23 | BONIF_12 | N | 5 | 2 |
| 24 | BONIF_21 | N | 5 | 2 |
| 25 | BONIF_22 | N | 5 | 2 |
| 26 | BONIF_31 | N | 5 | 2 |
| 27 | BONIF_32 | N | 5 | 2 |
| 28 | BONIF_41 | N | 5 | 2 |
| 29 | BONIF_42 | N | 5 | 2 |
| 30 | EN_DOLARES | L | 1 | 0 |

## GV0008
- Registros (canónico): **5** · copias en el árbol: 46 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0008.DBF` (mod. 2009-07-29, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMERO | L | 1 | 0 |
| 2 | IMPRIMIR | L | 1 | 0 |
| 3 | IMPRIMIR1 | L | 1 | 0 |
| 4 | IMPRIMIR2 | L | 1 | 0 |
| 5 | IMPRIMIR3 | L | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | FAMILIA | C | 30 | 0 |
| 9 | NSUBF | C | 30 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | AUXILIO2 | C | 30 | 0 |
| 12 | AUXILIO3 | C | 30 | 0 |
| 13 | NOMPROV | C | 30 | 0 |
| 14 | SIGNO | C | 3 | 0 |
| 15 | PRECIO | N | 8 | 2 |
| 16 | CONIVA | N | 8 | 2 |
| 17 | UBICACION | C | 10 | 0 |
| 18 | AUXILIO | C | 30 | 0 |
| 19 | OBSERVAC | M | 10 | 0 |

## GV0009
- Registros (canónico): **5** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\gv0009.dbf` (mod. 2001-08-20, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMERO | L | 1 | 0 |
| 2 | IMPRIMIR | L | 1 | 0 |
| 3 | IMPRIMIR1 | L | 1 | 0 |
| 4 | IMPRIMIR2 | L | 1 | 0 |
| 5 | IMPRIMIR3 | L | 1 | 0 |
| 6 | CODART | C | 10 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | FAMILIA | C | 30 | 0 |
| 9 | NSUBF | C | 30 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | AUXILIO2 | C | 30 | 0 |
| 12 | AUXILIO3 | C | 30 | 0 |
| 13 | NOMPROV | C | 30 | 0 |
| 14 | PRECIO | N | 8 | 2 |
| 15 | CONIVA | N | 8 | 2 |
| 16 | UBICACION | C | 10 | 0 |
| 17 | AUXILIO | C | 30 | 0 |

## GV0010
- Registros (canónico): **3** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0010.DBF` (mod. 2004-06-08, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TIPOCOMP | C | 30 | 0 |
| 2 | FECCUOTA | C | 10 | 0 |
| 3 | SALDO | N | 9 | 2 |
| 4 | DESCUENTO | N | 9 | 2 |
| 5 | NETO | N | 9 | 2 |
| 6 | NCHEQUE | N | 10 | 0 |
| 7 | FECVTO | C | 10 | 0 |
| 8 | IMPCHE | N | 9 | 2 |
| 9 | PROP_TER | N | 1 | 0 |
| 10 | CUIT | C | 13 | 0 |

## GV0011
- Registros (canónico): **23** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0011.DBF` (mod. 2006-07-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | CPROV | C | 4 | 0 |
| 3 | NOMPROV | C | 30 | 0 |
| 4 | TELEFONO | C | 30 | 0 |
| 5 | FMOV | C | 10 | 0 |
| 6 | FECVTO | C | 10 | 0 |
| 7 | TIPOCOMP | C | 25 | 0 |
| 8 | IMPCUOTA | N | 11 | 2 |
| 9 | PAGADO | N | 11 | 2 |
| 10 | SALDO | N | 11 | 2 |
| 11 | ACUMULADO | N | 11 | 2 |
| 12 | TOTAL | N | 11 | 2 |

## GV0011B
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0011B.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | CPROV | C | 4 | 0 |
| 3 | NOMPROV | C | 30 | 0 |
| 4 | TELEFONO | C | 25 | 0 |
| 5 | FECVTO | C | 10 | 0 |
| 6 | TIPOCOMP | C | 25 | 0 |
| 7 | IMPCUOTA | N | 10 | 2 |
| 8 | PAGADO | N | 10 | 2 |
| 9 | SALDO | N | 10 | 2 |
| 10 | ACUMULADO | N | 10 | 2 |
| 11 | TOTAL | N | 10 | 2 |

## GV0012
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0012.DBF` (mod. 2006-07-05, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | TELEFONO | C | 25 | 0 |
| 5 | FECVTO | C | 10 | 0 |
| 6 | TIPOCOMP | C | 28 | 0 |
| 7 | IMPCUOTA | N | 10 | 2 |
| 8 | PAGADO | N | 10 | 2 |
| 9 | SALDO | N | 10 | 2 |
| 10 | ACUMULADO | N | 11 | 2 |
| 11 | TOTAL | N | 11 | 2 |
| 12 | FMOV | C | 10 | 0 |

## GV0012A
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0012A.DBF` (mod. 2002-01-17, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | TELEFONO | C | 25 | 0 |
| 5 | FECVTO | C | 10 | 0 |
| 6 | TIPOCOMP | C | 30 | 0 |
| 7 | IMPCUOTA | N | 10 | 2 |
| 8 | PAGADO | N | 10 | 2 |
| 9 | SALDO | N | 10 | 2 |
| 10 | ACUMULADO | N | 10 | 2 |
| 11 | TOTAL | N | 10 | 2 |

## GV0012B
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0012B.DBF` (mod. 2002-01-17, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | TELEFONO | C | 25 | 0 |
| 5 | FECVTO | C | 10 | 0 |
| 6 | TIPOCOMP | C | 30 | 0 |
| 7 | IMPCUOTA | N | 10 | 2 |
| 8 | PAGADO | N | 10 | 2 |
| 9 | SALDO | N | 10 | 2 |
| 10 | ACUMULADO | N | 10 | 2 |
| 11 | TOTAL | N | 10 | 2 |

## GV0012C
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0012C.DBF` (mod. 2002-01-17, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 30 | 0 |

## GV0013
- Registros (canónico): **1** · copias en el árbol: 46 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\gv0013.DBF` (mod. 2007-04-12, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PAGINA | C | 8 | 0 |
| 2 | AUXILIO | D | 8 | 0 |
| 3 | NCOMP | C | 22 | 0 |
| 4 | FMOV | C | 10 | 0 |
| 5 | NOMPROV | C | 30 | 0 |
| 6 | CUIT | C | 13 | 0 |
| 7 | CAI | C | 14 | 0 |
| 8 | VTOCAI | D | 8 | 0 |
| 9 | CONDIVA | C | 10 | 0 |
| 10 | NETO | N | 10 | 2 |
| 11 | TASA | N | 5 | 2 |
| 12 | IVA | N | 9 | 2 |
| 13 | NOGRAV | N | 10 | 2 |
| 14 | SOBRETASA | N | 9 | 2 |
| 15 | SNI | N | 9 | 2 |
| 16 | IMPPER | N | 9 | 2 |
| 17 | IMPINT | N | 9 | 2 |
| 18 | INGBRU | N | 9 | 2 |
| 19 | IMPRET | N | 9 | 2 |
| 20 | OTROS | N | 9 | 2 |
| 21 | TOTAL | N | 10 | 2 |
| 22 | ACUM1 | N | 11 | 2 |
| 23 | ACUM2 | N | 11 | 2 |
| 24 | ACUM3 | N | 11 | 2 |
| 25 | ACUM4 | N | 11 | 2 |
| 26 | ACUM5 | N | 11 | 2 |
| 27 | ACUM6 | N | 11 | 2 |
| 28 | ACUM7 | N | 11 | 2 |
| 29 | ACUM8 | N | 11 | 2 |
| 30 | ACUM9 | N | 11 | 2 |
| 31 | KACUM1 | N | 11 | 2 |
| 32 | KACUM2 | N | 11 | 2 |
| 33 | KACUM3 | N | 11 | 2 |
| 34 | KACUM4 | N | 11 | 2 |
| 35 | KACUM5 | N | 11 | 2 |
| 36 | KACUM6 | N | 11 | 2 |
| 37 | KACUM7 | N | 11 | 2 |
| 38 | KACUM8 | N | 11 | 2 |
| 39 | KACUM9 | N | 11 | 2 |
| 40 | CUENTA | C | 6 | 0 |
| 41 | CUENTANOGR | C | 6 | 0 |
| 42 | CUENTAOTRO | C | 6 | 0 |
| 43 | COSTO_NETO | N | 11 | 2 |
| 44 | DIFERENCIA | N | 11 | 2 |

## GV0013A
- Registros (canónico): **3** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\gv0013a.dbf` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | NCOMP | C | 22 | 0 |
| 3 | FMOV | C | 10 | 0 |
| 4 | NOMPROV | C | 30 | 0 |
| 5 | CUIT | C | 13 | 0 |
| 6 | CONDIVA | C | 10 | 0 |
| 7 | NETO | N | 9 | 2 |
| 8 | TASA | N | 5 | 2 |
| 9 | IVA | N | 9 | 2 |
| 10 | SOBRETASA | N | 9 | 2 |
| 11 | SNI | N | 9 | 2 |
| 12 | IMPPER | N | 9 | 2 |
| 13 | IMPINT | N | 9 | 2 |
| 14 | TOTAL | N | 9 | 2 |

## GV0014
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0014.DBF` (mod. 2005-04-19, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 10 | 0 |
| 4 | CDEP | C | 2 | 0 |
| 5 | NDEP | C | 30 | 0 |
| 6 | CCONC | C | 2 | 0 |
| 7 | CONCEPTO | C | 25 | 0 |
| 8 | CANTIDAD | N | 10 | 2 |
| 9 | OBSERVAC | C | 50 | 0 |

## GV0016
- Registros (canónico): **7** · copias en el árbol: 25 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\Gv0016.DBF` (mod. 2008-10-15, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODCLI | C | 10 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | DOMCLI | C | 40 | 0 |
| 5 | LOCCLI | C | 30 | 0 |
| 6 | PROVCLI | C | 15 | 0 |
| 7 | CONTACTO | C | 30 | 0 |
| 8 | ZONA | C | 2 | 0 |
| 9 | CVIAJ | C | 2 | 0 |
| 10 | LISTAPRE | N | 1 | 0 |
| 11 | CODPOS | C | 10 | 0 |
| 12 | TELCLI_1 | C | 15 | 0 |
| 13 | TELCLI_2 | C | 15 | 0 |
| 14 | FAX | C | 15 | 0 |
| 15 | E_MAIL | C | 45 | 0 |
| 16 | HTTP | C | 40 | 0 |
| 17 | CALIFIC | C | 10 | 0 |
| 18 | DESCUENTO | N | 5 | 2 |
| 19 | BLOQUEADO | N | 1 | 0 |
| 20 | CUITCLI | C | 13 | 0 |
| 21 | REGCLI | N | 1 | 0 |
| 22 | DNI | N | 8 | 0 |
| 23 | FSALCLI_1 | D | 8 | 0 |
| 24 | SALCLI_P1 | N | 10 | 2 |
| 25 | SALCLI_D1 | N | 10 | 2 |
| 26 | FSALCLI_2 | D | 8 | 0 |
| 27 | SALCLI_P2 | N | 10 | 2 |
| 28 | SALCLI_D2 | N | 10 | 2 |
| 29 | TSALDO | N | 1 | 0 |
| 30 | CRED_MAX | N | 10 | 2 |
| 31 | CCOND | C | 2 | 0 |
| 32 | CTRANSP | C | 3 | 0 |
| 33 | OBSERVAC | M | 4 | 0 |
| 34 | FNACIM | D | 8 | 0 |
| 35 | FALTA | D | 8 | 0 |
| 36 | IVA | C | 20 | 0 |

## GV0016A
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0016A.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMERO | L | 1 | 0 |
| 2 | FECHA | D | 8 | 0 |
| 3 | NCOMP | C | 26 | 0 |
| 4 | CODART | C | 15 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | UNIDAD | C | 6 | 0 |
| 7 | CANTIDAD | N | 8 | 2 |
| 8 | PRECIO | N | 10 | 2 |
| 9 | BONIF_1 | N | 6 | 2 |
| 10 | BONIF_2 | N | 6 | 2 |
| 11 | PARCIAL | N | 10 | 2 |
| 12 | TOTAL | N | 10 | 2 |
| 13 | OBSERVAC | C | 30 | 0 |

## GV0017
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0017.DBF` (mod. 2005-04-22, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 10 | 0 |
| 4 | CANTIDAD | N | 10 | 2 |
| 5 | PRECIO | N | 8 | 2 |
| 6 | STOCK | N | 10 | 2 |

## GV0018
- Registros (canónico): **30** · copias en el árbol: 21 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0018.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | CBARRA | C | 20 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | UNIDAD | C | 10 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | PRECIO | N | 11 | 4 |
| 7 | NDESPACHO | C | 20 | 0 |
| 8 | ADUANA | C | 20 | 0 |
| 9 | STOCK | N | 10 | 2 |
| 10 | UBICACION | C | 10 | 0 |
| 11 | PESO | N | 12 | 2 |
| 12 | UNIDAD2 | C | 6 | 0 |
| 13 | PARCIAL | N | 10 | 2 |
| 14 | BONIF_1 | N | 6 | 2 |
| 15 | BONIF_2 | N | 6 | 2 |
| 16 | KPARCIAL | N | 10 | 4 |
| 17 | KPRECIO | N | 10 | 4 |
| 18 | PESIF | L | 1 | 0 |
| 19 | PUNIT | N | 10 | 4 |
| 20 | TASA | N | 5 | 2 |
| 21 | EN_DOLARES | L | 1 | 0 |
| 22 | PRESUPUEST | C | 12 | 0 |
| 23 | CODANTER | C | 15 | 0 |
| 24 | NTEXTO | N | 2 | 0 |
| 25 | ITEM | C | 2 | 0 |
| 26 | NUEVOCPO | C | 10 | 0 |
| 27 | NPEDIDO | C | 12 | 0 |
| 28 | KOEF | N | 5 | 2 |

## GV0019
- Registros (canónico): **2** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0019.DBF` (mod. 2006-07-31, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TIPOCOMP | C | 30 | 0 |
| 2 | FECCUOTA | C | 10 | 0 |
| 3 | SALDO | N | 9 | 2 |
| 4 | DESCUENTO | N | 9 | 2 |
| 5 | NETO | N | 9 | 2 |
| 6 | NCHEQUE | N | 10 | 0 |
| 7 | FECVTO | C | 10 | 0 |
| 8 | IMPCHE | N | 9 | 2 |

## GV0020
- Registros (canónico): **4** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0020.DBF` (mod. 2009-06-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | FMOV | D | 8 | 0 |
| 7 | TIPOCOMP | C | 36 | 0 |
| 8 | DEBE | N | 10 | 2 |
| 9 | HABER | N | 10 | 2 |
| 10 | SALDO | N | 10 | 2 |
| 11 | OBSERVAC | C | 60 | 0 |
| 12 | PIC | C | 15 | 0 |

## GV0021
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0021.DBF` (mod. 2009-09-21, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NRECIBO | C | 13 | 0 |
| 3 | NOMCLI | C | 25 | 0 |
| 4 | FMOV | D | 8 | 0 |
| 5 | RETENCION | C | 25 | 0 |
| 6 | IMPORTE | N | 10 | 2 |
| 7 | NRETEN | C | 12 | 0 |
| 8 | CUIT | C | 13 | 0 |

## GV0021A
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0021A.DBF` (mod. 2009-09-21, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NRECIBO | C | 13 | 0 |
| 3 | NOMCLI | C | 25 | 0 |
| 4 | FMOV | C | 10 | 0 |
| 5 | RETENCION | C | 25 | 0 |
| 6 | IMPORTE | N | 10 | 2 |
| 7 | NRETEN | C | 12 | 0 |
| 8 | CUIT | C | 13 | 0 |

## GV0022
- Registros (canónico): **1** · copias en el árbol: 46 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0022.DBF` (mod. 2008-12-12, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PAGINA | C | 8 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | AUXILIO | C | 25 | 0 |
| 4 | NCOMP | C | 22 | 0 |
| 5 | FECHA | D | 8 | 0 |
| 6 | FMOV | C | 10 | 0 |
| 7 | NOMCLI | C | 31 | 0 |
| 8 | CUIT | C | 13 | 0 |
| 9 | CONDIVA | C | 11 | 0 |
| 10 | REGCLI | N | 1 | 0 |
| 11 | PROVCLI | C | 15 | 0 |
| 12 | NETO | N | 9 | 2 |
| 13 | EXENTO | N | 9 | 2 |
| 14 | TASA | C | 6 | 0 |
| 15 | IVA | N | 9 | 2 |
| 16 | SOBRETASA | N | 9 | 2 |
| 17 | SNI | N | 9 | 2 |
| 18 | IMPPER | N | 9 | 2 |
| 19 | IMPINT | N | 9 | 2 |
| 20 | TOTAL | N | 9 | 2 |
| 21 | ACUM1 | N | 9 | 2 |
| 22 | ACUM2 | N | 9 | 2 |
| 23 | ACUM3 | N | 9 | 2 |
| 24 | ACUM4 | N | 9 | 2 |
| 25 | ACUM5 | N | 9 | 2 |
| 26 | KACUM1 | N | 9 | 2 |
| 27 | KACUM2 | N | 9 | 2 |
| 28 | KACUM3 | N | 9 | 2 |
| 29 | KACUM4 | N | 9 | 2 |
| 30 | KACUM5 | N | 9 | 2 |
| 31 | TCOMP | C | 1 | 0 |

## GV0022A
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\GV0022A.DBF` (mod. 2014-09-30, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PAGINA | C | 8 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | AUXILIO | C | 25 | 0 |
| 4 | NCOMP | C | 22 | 0 |
| 5 | FECHA | D | 8 | 0 |
| 6 | FMOV | C | 10 | 0 |
| 7 | NOMCLI | C | 31 | 0 |
| 8 | CUIT | C | 13 | 0 |
| 9 | CONDIVA | C | 10 | 0 |
| 10 | REGCLI | N | 1 | 0 |
| 11 | PROVCLI | C | 15 | 0 |
| 12 | NETO | N | 9 | 2 |
| 13 | EXENTO | N | 9 | 2 |
| 14 | TASA | C | 6 | 0 |
| 15 | IVA | N | 9 | 2 |
| 16 | SOBRETASA | N | 9 | 2 |
| 17 | SNI | N | 9 | 2 |
| 18 | IMPPER | N | 9 | 2 |
| 19 | IMPINT | N | 9 | 2 |
| 20 | TOTAL | N | 9 | 2 |
| 21 | ACUM1 | N | 9 | 2 |
| 22 | ACUM2 | N | 9 | 2 |
| 23 | ACUM3 | N | 9 | 2 |
| 24 | ACUM4 | N | 9 | 2 |
| 25 | ACUM5 | N | 9 | 2 |
| 26 | KACUM1 | N | 9 | 2 |
| 27 | KACUM2 | N | 9 | 2 |
| 28 | KACUM3 | N | 9 | 2 |
| 29 | KACUM4 | N | 9 | 2 |
| 30 | KACUM5 | N | 9 | 2 |

## GV0022J
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0022j.dbf` (mod. 2003-01-22, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NZETA | C | 15 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | REGCLI | N | 1 | 0 |
| 4 | DESDE | C | 8 | 0 |
| 5 | HASTA | C | 8 | 0 |
| 6 | FMOV | C | 10 | 0 |
| 7 | NETO_1 | N | 10 | 2 |
| 8 | IVA_1 | N | 10 | 2 |
| 9 | TOTAL_1 | N | 10 | 2 |
| 10 | NETO_2 | N | 10 | 2 |
| 11 | IVA_2 | N | 10 | 2 |
| 12 | TOTAL_2 | N | 10 | 2 |
| 13 | NETO_3 | N | 10 | 2 |
| 14 | IVA_3 | N | 10 | 2 |
| 15 | TOTAL_3 | N | 10 | 2 |
| 16 | NETO_4 | N | 10 | 2 |
| 17 | IVA_4 | N | 10 | 2 |
| 18 | TOTAL_4 | N | 10 | 2 |
| 19 | NETO_5 | N | 10 | 2 |
| 20 | IVA_5 | N | 10 | 2 |
| 21 | TOTAL_5 | N | 10 | 2 |
| 22 | NETO_6 | N | 10 | 2 |
| 23 | IVA_6 | N | 10 | 2 |
| 24 | TOTAL_6 | N | 10 | 2 |
| 25 | NETO_7 | N | 10 | 2 |
| 26 | IVA_7 | N | 10 | 2 |
| 27 | TOTAL_7 | N | 10 | 2 |
| 28 | TOTAL | N | 10 | 2 |
| 29 | LETRA | C | 1 | 0 |

## GV0022K
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\gv0022k.dbf` (mod. 2004-07-27, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODIGO | C | 1 | 0 |
| 2 | TITULO | C | 30 | 0 |
| 3 | TASA | N | 5 | 2 |
| 4 | NETO | N | 10 | 2 |
| 5 | EXENTO | N | 10 | 2 |
| 6 | IVA | N | 10 | 2 |
| 7 | TOTAL | N | 10 | 2 |

## GV0023
- Registros (canónico): **7** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0023.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PAGINA | C | 8 | 0 |
| 2 | AUXILIO | D | 8 | 0 |
| 3 | LETRA | C | 1 | 0 |
| 4 | NCOMP | C | 22 | 0 |
| 5 | FMOV | C | 10 | 0 |
| 6 | NOMCLI | C | 30 | 0 |
| 7 | CUIT | C | 13 | 0 |
| 8 | CONDIVA | C | 10 | 0 |
| 9 | NETO | N | 9 | 2 |
| 10 | TASA | N | 5 | 2 |
| 11 | IVA | N | 9 | 2 |
| 12 | SOBRETASA | N | 9 | 2 |
| 13 | SNI | N | 9 | 2 |
| 14 | TOTAL | N | 9 | 2 |

## GV0023A
- Registros (canónico): **9** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0023A.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | NCOMP | C | 22 | 0 |
| 3 | FMOV | C | 10 | 0 |
| 4 | NOMCLI | C | 30 | 0 |
| 5 | CUIT | C | 13 | 0 |
| 6 | CONDIVA | C | 10 | 0 |
| 7 | NETO | N | 9 | 2 |
| 8 | TASA | N | 5 | 2 |
| 9 | IVA | N | 9 | 2 |
| 10 | SOBRETASA | N | 9 | 2 |
| 11 | SNI | N | 9 | 2 |
| 12 | TOTAL | N | 9 | 2 |

## GV0023J
- Registros (canónico): **0** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\gv0023j.dbf` (mod. 2002-05-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | DESDE | C | 8 | 0 |
| 3 | HASTA | C | 15 | 0 |
| 4 | FMOV | D | 8 | 0 |
| 5 | NETO | N | 10 | 2 |
| 6 | IVA | N | 10 | 2 |
| 7 | EXENTO | N | 10 | 2 |
| 8 | TOTAL | N | 10 | 2 |

## GV0024
- Registros (canónico): **5** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0024.DBF` (mod. 2008-08-06, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | FECHA | C | 10 | 0 |
| 3 | TIPOCOMP | C | 36 | 0 |
| 4 | DEBE | N | 10 | 2 |
| 5 | HABER | N | 10 | 2 |
| 6 | SALDO | N | 12 | 2 |
| 7 | OBSERVAC | C | 40 | 0 |
| 8 | TCOMP | C | 1 | 0 |

## GV0025
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 5
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0025.DBF` (mod. 2009-10-14, FoxPro con memo (FPT))

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TEXTO | L | 1 | 0 |
| 2 | NTEXTO | N | 1 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CBARRA | C | 20 | 0 |
| 5 | NREMITO | C | 12 | 0 |
| 6 | PRESUPUEST | C | 12 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | AUXDESART | M | 10 | 0 |
| 9 | UNIDAD | C | 6 | 0 |
| 10 | CANTIDAD | N | 10 | 2 |
| 11 | POR_REMITO | N | 10 | 2 |
| 12 | PAUXIL | N | 10 | 2 |
| 13 | PRECIO | N | 12 | 4 |
| 14 | APRECIO | N | 8 | 2 |
| 15 | BONIF_1 | N | 6 | 2 |
| 16 | BONIF_2 | N | 6 | 2 |
| 17 | PUNIT | N | 13 | 7 |
| 18 | PARCIAL | N | 13 | 7 |
| 19 | NDESPACHO | C | 20 | 0 |
| 20 | ADUANA | C | 20 | 0 |
| 21 | TASA | N | 5 | 2 |
| 22 | SNI | N | 5 | 2 |
| 23 | KOEF | N | 7 | 4 |
| 24 | PESIF | L | 1 | 0 |
| 25 | KPRECIO | N | 10 | 2 |
| 26 | STOCK | N | 10 | 2 |
| 27 | KPARCIAL | N | 9 | 2 |
| 28 | TD1 | C | 50 | 0 |
| 29 | TD2 | C | 50 | 0 |
| 30 | TD3 | C | 50 | 0 |
| 31 | TD4 | C | 50 | 0 |
| 32 | CODANTER | C | 15 | 0 |
| 33 | ITEM | C | 2 | 0 |
| 34 | ANTERIOR | N | 12 | 4 |
| 35 | NPEDIDO | C | 12 | 0 |
| 36 | AUX_KOEF | N | 5 | 2 |

## GV0025B
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0025B.DBF` (mod. 2002-08-07, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | FREMITO | D | 8 | 0 |
| 4 | MARCA | L | 1 | 0 |
| 5 | VAL_DEC | N | 8 | 2 |

## GV0025C
- Registros (canónico): **2** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GV0025C.DBF` (mod. 2006-11-23, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 10 | 0 |
| 4 | CANTIDAD | N | 10 | 2 |
| 5 | PRECIO | N | 8 | 2 |
| 6 | BONIF_1 | N | 5 | 2 |
| 7 | BONIF_2 | N | 5 | 2 |
| 8 | PUNIT | N | 8 | 2 |
| 9 | PARCIAL | N | 8 | 2 |

## GV0025D
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\gv0025d.DBF` (mod. 2007-03-28, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CANT_FACT | N | 10 | 2 |
| 5 | PRECIO | N | 10 | 2 |
| 6 | ITEM | C | 2 | 0 |
| 7 | PARCIAL | N | 10 | 2 |

## GV0025E
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0025E.DBF` (mod. 2002-08-18, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NCOMP | C | 8 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CANT_FACT | N | 10 | 2 |

## GV0025F
- Registros (canónico): **0** · copias en el árbol: 6 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0025F.DBF` (mod. 2009-10-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | CANTIDAD | N | 10 | 2 |
| 4 | PRECIO | N | 10 | 2 |
| 5 | BONIF_1 | N | 6 | 2 |
| 6 | BONIF_2 | N | 6 | 2 |
| 7 | PARCIAL | N | 10 | 2 |

## GV0026
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0026.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 10 | 0 |
| 4 | CDEP | C | 2 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | POR_REMITO | N | 10 | 2 |
| 7 | PRECIO | N | 8 | 2 |
| 8 | BONIF_1 | N | 6 | 2 |
| 9 | BONIF_2 | N | 6 | 2 |
| 10 | PARCIAL | N | 8 | 2 |

## GV0027
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0027.DBF` (mod. 2006-07-11, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | C | 10 | 0 |
| 2 | DETALLE | C | 30 | 0 |
| 3 | FECVTO | C | 10 | 0 |
| 4 | FECHAVTO | D | 8 | 0 |
| 5 | DIAS | N | 4 | 0 |
| 6 | VENCIDO | N | 10 | 2 |
| 7 | ADEUDADO | N | 10 | 2 |
| 8 | IMPORTE | N | 10 | 2 |
| 9 | CORRIENTE | N | 10 | 2 |
| 10 | OVER30 | N | 10 | 2 |
| 11 | OVER60 | N | 10 | 2 |
| 12 | OVER90 | N | 10 | 2 |
| 13 | OVER120 | N | 10 | 2 |

## GV0027B
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0027b.DBF` (mod. 2006-07-11, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 30 | 0 |
| 3 | FECHA | C | 10 | 0 |
| 4 | FECHAVTO | D | 8 | 0 |
| 5 | DETALLE | C | 30 | 0 |
| 6 | FECVTO | C | 10 | 0 |
| 7 | DIAS | N | 4 | 0 |
| 8 | VENCIDO | N | 10 | 2 |
| 9 | IMPORTE | N | 10 | 2 |
| 10 | ADEUDADO | N | 10 | 2 |
| 11 | CORRIENTE | N | 10 | 2 |
| 12 | OVER30 | N | 10 | 2 |
| 13 | OVER60 | N | 10 | 2 |
| 14 | OVER90 | N | 10 | 2 |
| 15 | OVER120 | N | 10 | 2 |

## GV0028
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0028.DBF` (mod. 2006-06-22, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | IMPRIMIR | L | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | FAMILIA | C | 51 | 0 |
| 5 | UNIDAD | C | 6 | 0 |
| 6 | NOMPROV | C | 30 | 0 |
| 7 | STOCK | N | 10 | 2 |
| 8 | UBICACION | C | 10 | 0 |
| 9 | AUXILIO | C | 51 | 0 |
| 10 | MINIMO | N | 10 | 2 |
| 11 | REPONER | N | 10 | 2 |
| 12 | PRECIO | N | 10 | 2 |
| 13 | TOTAL | N | 12 | 2 |
| 14 | CORTE | N | 12 | 2 |

## GV0029
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 5
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0029.DBF` (mod. 2009-10-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TEXTO | L | 1 | 0 |
| 2 | NTEXTO | N | 1 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CBARRA | C | 20 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | AUXDESART | M | 4 | 0 |
| 7 | UNIDAD | C | 6 | 0 |
| 8 | CANTIDAD | N | 10 | 2 |
| 9 | POR_REMITO | N | 10 | 2 |
| 10 | PAUXIL | N | 10 | 2 |
| 11 | PRECIO | N | 12 | 4 |
| 12 | APRECIO | N | 8 | 2 |
| 13 | BONIF_1 | N | 6 | 2 |
| 14 | BONIF_2 | N | 6 | 2 |
| 15 | PUNIT | N | 13 | 7 |
| 16 | PARCIAL | N | 13 | 7 |
| 17 | NDESPACHO | C | 20 | 0 |
| 18 | ADUANA | C | 20 | 0 |
| 19 | ORIGEN | C | 20 | 0 |
| 20 | TASA | N | 5 | 2 |
| 21 | SNI | N | 5 | 2 |
| 22 | KOEF | N | 7 | 4 |
| 23 | PESIF | L | 1 | 0 |
| 24 | KPRECIO | N | 10 | 2 |
| 25 | STOCK | N | 10 | 2 |
| 26 | KPARCIAL | N | 9 | 2 |
| 27 | CODANTER | C | 15 | 0 |
| 28 | ANTERIOR | N | 12 | 4 |

## GV0029B
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0029B.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | FREMITO | D | 8 | 0 |
| 4 | MARCA | C | 1 | 0 |
| 5 | VAL_DEC | N | 8 | 2 |

## GV0030
- Registros (canónico): **3** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0030.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCHEQUE | N | 10 | 0 |
| 2 | BANCO | C | 20 | 0 |
| 3 | PLAZA | C | 20 | 0 |
| 4 | FECCHE | C | 10 | 0 |
| 5 | FECVTO | C | 10 | 0 |
| 6 | IMPCHE | N | 12 | 2 |
| 7 | ACUMULADO | N | 12 | 2 |
| 8 | EMITIDO | C | 20 | 0 |
| 9 | PASADO_A | C | 20 | 0 |
| 10 | RECHAZADO | C | 2 | 0 |

## GV0032
- Registros (canónico): **2** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0032.DBF` (mod. 2002-11-16, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCHEQUE | N | 10 | 0 |
| 2 | BANCO | C | 20 | 0 |
| 3 | PLAZA | C | 20 | 0 |
| 4 | FECCHE | D | 8 | 0 |
| 5 | FECVTO | D | 8 | 0 |
| 6 | IMPCHE | N | 12 | 2 |
| 7 | ACUMULADO | N | 12 | 2 |
| 8 | EMITIDO | C | 20 | 0 |
| 9 | PASADO_A | C | 20 | 0 |
| 10 | RECHAZADO | C | 2 | 0 |

## GV0034
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0034.DBF` (mod. 2006-04-19, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | DETALLE | L | 1 | 0 |
| 2 | CODCLI | C | 10 | 0 |
| 3 | NOMCLI | C | 40 | 0 |
| 4 | FMOV | D | 8 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | TIPOCOMP | C | 13 | 0 |
| 7 | VAL_DEC | N | 10 | 2 |
| 8 | BULTOS | N | 9 | 2 |
| 9 | CANTIDAD | N | 6 | 0 |
| 10 | CONTROLO | C | 20 | 0 |
| 11 | CANT_FACT | N | 6 | 0 |
| 12 | CANT_PEND | N | 6 | 0 |

## GV0035
- Registros (canónico): **1** · copias en el árbol: 46 · variantes de esquema: 5
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0035.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 6 | 0 |
| 4 | CANTIDAD | N | 10 | 2 |
| 5 | PRECIO | N | 10 | 2 |
| 6 | BONIF_1 | N | 6 | 2 |
| 7 | BONIF_2 | N | 6 | 2 |
| 8 | PARCIAL | N | 11 | 2 |
| 9 | NTEXTO | N | 2 | 0 |
| 10 | KOEF | N | 7 | 4 |
| 11 | CANT_ENT | N | 10 | 2 |
| 12 | PENDIENTE | N | 10 | 2 |

## GV0035A
- Registros (canónico): **3** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0035A.DBF` (mod. 2008-04-03, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCHEQUE | C | 15 | 0 |
| 2 | BANCO | C | 25 | 0 |
| 3 | FECCHE | C | 10 | 0 |
| 4 | FECVTO | C | 10 | 0 |
| 5 | IMPCHE | N | 10 | 2 |
| 6 | ESTADO | C | 30 | 0 |

## GV0035B
- Registros (canónico): **1** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0035B.DBF` (mod. 2006-07-31, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TIPOCOMP | C | 40 | 0 |
| 2 | FECVTO | C | 10 | 0 |
| 3 | APLICADO | N | 10 | 2 |

## GV0035C
- Registros (canónico): **2,390** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\GV0035C.DBF` (mod. 2008-12-26, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | NCOMP | C | 30 | 0 |
| 3 | OBSERVAC | C | 60 | 0 |

## GV0035D
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0035D.DBF` (mod. 2005-12-07, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NRECIBO | C | 13 | 0 |
| 2 | FRECIBO | D | 8 | 0 |
| 3 | EFECTIVO | N | 10 | 2 |
| 4 | NTARJETA | C | 20 | 0 |
| 5 | ITARJETA | N | 10 | 2 |
| 6 | DEPOSITO | N | 10 | 2 |
| 7 | NCHEQUE | C | 10 | 0 |
| 8 | FCHEQUE | D | 8 | 0 |
| 9 | ICHEQUE | N | 10 | 2 |
| 10 | BANCO | C | 20 | 0 |

## GV0036
- Registros (canónico): **1** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0036.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 10 | 0 |
| 4 | CANTIDAD | N | 10 | 2 |
| 5 | PRECIO | N | 9 | 2 |
| 6 | BONIF_1 | N | 6 | 2 |
| 7 | BONIF_2 | N | 6 | 2 |
| 8 | PARCIAL | N | 11 | 2 |

## GV0036A
- Registros (canónico): **3** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0036A.DBF` (mod. 2006-07-29, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCHEQUE | C | 10 | 0 |
| 2 | BANCO | C | 25 | 0 |
| 3 | FECCHE | C | 10 | 0 |
| 4 | FECVTO | C | 10 | 0 |
| 5 | IMPCHE | N | 10 | 2 |
| 6 | ESTADO | C | 30 | 0 |

## GV0036B
- Registros (canónico): **2** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0036B.DBF` (mod. 2006-07-29, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TIPOCOMP | C | 40 | 0 |
| 2 | FECVTO | C | 10 | 0 |
| 3 | APLICADO | N | 11 | 2 |

## GV0036C
- Registros (canónico): **16** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\gv0036c.DBF` (mod. 2008-12-18, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | NCOMP | C | 30 | 0 |
| 3 | OBSERVAC | C | 60 | 0 |

## GV0038
- Registros (canónico): **20** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0038.DBF` (mod. 2006-07-03, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | NRECIBO | C | 8 | 0 |
| 3 | FRECIBO | C | 10 | 0 |
| 4 | NOMPROV | C | 30 | 0 |
| 5 | CUITCHEQ | C | 13 | 0 |
| 6 | CHEQUES | N | 11 | 2 |
| 7 | EFECTIVO | N | 11 | 2 |
| 8 | IMPBCO | N | 11 | 2 |
| 9 | TOTAL | N | 12 | 2 |
| 10 | COMPROBANT | C | 51 | 0 |
| 11 | IMPORTE | N | 11 | 2 |
| 12 | DESCUENTO | N | 9 | 2 |
| 13 | RETENCION | N | 9 | 2 |
| 14 | NETO | N | 10 | 2 |
| 15 | CUITPROV | C | 13 | 0 |
| 16 | DEPOSITO | N | 10 | 2 |

## GV0038B
- Registros (canónico): **10** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0038B.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | NRECIBO | C | 8 | 0 |
| 3 | FRECIBO | C | 10 | 0 |
| 4 | NOMPROV | C | 30 | 0 |
| 5 | CHEQUES | N | 9 | 2 |
| 6 | EFECTIVO | N | 9 | 2 |
| 7 | TOTAL | N | 9 | 2 |
| 8 | COMPROBANT | C | 32 | 0 |
| 9 | IMPORTE | N | 9 | 2 |
| 10 | DESCUENTO | N | 9 | 2 |
| 11 | NETO | N | 9 | 2 |

## GV0039
- Registros (canónico): **2** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0039.DBF` (mod. 2006-06-23, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | NRECIBO | C | 13 | 0 |
| 3 | FRECIBO | C | 10 | 0 |
| 4 | NOMCLI | C | 40 | 0 |
| 5 | CHEQUES | N | 10 | 2 |
| 6 | EFECTIVO | N | 10 | 2 |
| 7 | TARJETA | N | 10 | 2 |
| 8 | IMPBCO | N | 10 | 2 |
| 9 | TOTAL | N | 11 | 2 |
| 10 | COMPROBANT | C | 32 | 0 |
| 11 | IMPORTE | N | 10 | 2 |
| 12 | DESCUENTO | N | 10 | 2 |
| 13 | RETENCION | N | 10 | 2 |
| 14 | NETO | N | 10 | 2 |

## GV0040
- Registros (canónico): **1,979** · copias en el árbol: 46 · variantes de esquema: 4
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Bonafide 11 2009\Super Restaurantes y Delivery\GV0040.DBF` (mod. 2009-02-05, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | T | 8 | 0 |
| 2 | AUXILIO | C | 17 | 0 |
| 3 | NCOMP | C | 20 | 0 |
| 4 | NOMCLI | C | 40 | 0 |
| 5 | NETO | N | 8 | 2 |
| 6 | COMISION | N | 8 | 2 |

## GV0041
- Registros (canónico): **8** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0041.DBF` (mod. 2006-07-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | AUXILIO | C | 10 | 0 |
| 3 | NCOMP | C | 20 | 0 |
| 4 | NOMCLI | C | 40 | 0 |
| 5 | NETO | N | 10 | 2 |

## GV0044
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GV0044.DBF` (mod. 2007-08-21, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | DETALLE | L | 1 | 0 |
| 2 | CODCLI | C | 10 | 0 |
| 3 | NOMCLI | C | 40 | 0 |
| 4 | FMOV | D | 8 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | TIPOCOMP | C | 13 | 0 |
| 7 | NFACTURA | C | 20 | 0 |
| 8 | VAL_DEC | N | 10 | 2 |
| 9 | BULTOS | N | 9 | 2 |
| 10 | CANTIDAD | N | 6 | 0 |
| 11 | CONTROLO | C | 20 | 0 |
| 12 | CANT_FACT | N | 6 | 0 |
| 13 | CANT_PEND | N | 6 | 0 |

## GV0045
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GV0045.DBF` (mod. 2007-06-29, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | IMPRIMIR | L | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | FAMILIA | C | 25 | 0 |
| 5 | UNIDAD | C | 5 | 0 |
| 6 | NOMPROV | C | 30 | 0 |
| 7 | AUXILIO | C | 30 | 0 |
| 8 | NSUBF | C | 30 | 0 |
| 9 | CODPROVE | C | 15 | 0 |

## GV0045A
- Registros (canónico): **2,145** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Bonafide 11 2009\Super Restaurantes y Delivery\gv0045a.dbf` (mod. 2008-11-28, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | FECHAHORA | T | 8 | 0 |
| 7 | EFT_A | N | 9 | 2 |
| 8 | IMPTAR | N | 10 | 2 |
| 9 | TARJETA | C | 20 | 0 |
| 10 | CHEQUES | N | 9 | 2 |
| 11 | SUBTOTAL | N | 10 | 2 |

## GV0046
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0046.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCOMP | C | 20 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | UNIDAD | C | 6 | 0 |
| 6 | CDEP | C | 2 | 0 |
| 7 | CCONC | C | 2 | 0 |
| 8 | NCONC | C | 26 | 0 |
| 9 | ENTRADA | N | 10 | 2 |
| 10 | SALIDA | N | 10 | 2 |
| 11 | OBSERVAC | C | 20 | 0 |

## GV0050
- Registros (canónico): **1,059,820** · copias en el árbol: 33 · variantes de esquema: 7
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\OXIMO\Bonafide\Super Restaurantes y Delivery\GV0050.DBF` (mod. 2009-02-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MESA | N | 10 | 0 |
| 2 | PORC_PROP | N | 5 | 2 |
| 3 | DESCUENTO | N | 2 | 0 |
| 4 | TEXTO | L | 1 | 0 |
| 5 | NTEXTO | N | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | CBARRA | C | 20 | 0 |
| 8 | DESART | C | 40 | 0 |
| 9 | AUXDESART | M | 4 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | CANTIDAD | N | 10 | 2 |
| 12 | POR_REMITO | N | 10 | 2 |
| 13 | PAUXIL | N | 10 | 2 |
| 14 | PRECIO | N | 8 | 2 |
| 15 | APRECIO | N | 8 | 2 |
| 16 | BONIF_1 | N | 5 | 2 |
| 17 | BONIF_2 | N | 5 | 2 |
| 18 | PUNIT | N | 10 | 4 |
| 19 | PARCIAL | N | 10 | 4 |
| 20 | NDESPACHO | C | 15 | 0 |
| 21 | ADUANA | C | 15 | 0 |
| 22 | TASA | N | 5 | 2 |
| 23 | SNI | N | 5 | 2 |
| 24 | KOEF | N | 7 | 4 |
| 25 | COMANDA | N | 1 | 0 |
| 26 | BEBIDA | L | 1 | 0 |

## GV0050B
- Registros (canónico): **0** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\GV0050B.DBF` (mod. 2001-06-22, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | FREMITO | D | 8 | 0 |
| 4 | MARCA | C | 1 | 0 |
| 5 | VAL_DEC | N | 8 | 2 |
| 6 | OBSER | C | 15 | 0 |

## GV0055
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0055.DBF` (mod. 2009-10-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TEXTO | L | 1 | 0 |
| 2 | NTEXTO | N | 1 | 0 |
| 3 | ITEM | C | 2 | 0 |
| 4 | CODART | C | 15 | 0 |
| 5 | LISTA | N | 1 | 0 |
| 6 | CBARRA | C | 20 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | PRODUCTO | C | 30 | 0 |
| 9 | NOMPROV | C | 30 | 0 |
| 10 | AUXDESART | M | 4 | 0 |
| 11 | UNIDAD | C | 20 | 0 |
| 12 | CANTIDAD | N | 10 | 2 |
| 13 | CANT_ENT | N | 10 | 2 |
| 14 | PENDIENTE | N | 10 | 2 |
| 15 | PAUXIL | N | 10 | 2 |
| 16 | PRECIO | N | 10 | 4 |
| 17 | APRECIO | N | 8 | 2 |
| 18 | BONIF_1 | N | 6 | 2 |
| 19 | BONIF_2 | N | 6 | 2 |
| 20 | PUNIT | N | 13 | 7 |
| 21 | PARCIAL | N | 13 | 7 |
| 22 | NDESPACHO | C | 15 | 0 |
| 23 | ADUANA | C | 15 | 0 |
| 24 | ORIGEN | C | 15 | 0 |
| 25 | TASA | N | 5 | 2 |
| 26 | SNI | N | 5 | 2 |
| 27 | KOEF | N | 7 | 4 |
| 28 | PESIF | L | 1 | 0 |
| 29 | KPRECIO | N | 10 | 2 |
| 30 | STOCK | N | 10 | 2 |
| 31 | KPARCIAL | N | 9 | 2 |
| 32 | CODANTER | C | 15 | 0 |
| 33 | CANCELADO | L | 1 | 0 |
| 34 | ESTADO | C | 20 | 0 |
| 35 | PRESUPUEST | C | 12 | 0 |

## GV0055B
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GV0055B.DBF` (mod. 2007-03-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | FREMITO | D | 8 | 0 |
| 4 | MARCA | C | 1 | 0 |
| 5 | VAL_DEC | N | 8 | 2 |

## GV0055C
- Registros (canónico): **0** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\gv0055c.dbf` (mod. 2007-03-27, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | COMPROBANT | C | 35 | 0 |
| 3 | CANTIDAD | N | 8 | 2 |
| 4 | PRECIO | N | 9 | 2 |

## GV0056
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0056.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | CANT_PED | N | 10 | 2 |
| 4 | CANT_ENT | N | 10 | 2 |
| 5 | PENDIENTE | N | 10 | 2 |
| 6 | PRECIO | N | 10 | 2 |
| 7 | BONIF_1 | N | 6 | 2 |
| 8 | BONIF_2 | N | 6 | 2 |
| 9 | PARCIAL | N | 10 | 2 |
| 10 | CANCELADO | C | 2 | 0 |

## GV0056A
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0056A.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | FPEDIDO | C | 10 | 0 |
| 3 | FENTREGA | C | 10 | 0 |
| 4 | CODCLI | C | 4 | 0 |
| 5 | NOMCLI | C | 30 | 0 |
| 6 | CANT_PED | N | 9 | 2 |
| 7 | CANT_ENT | N | 9 | 2 |
| 8 | PENDIENTE | N | 9 | 2 |
| 9 | PRECIO | N | 9 | 2 |
| 10 | BONIF_1 | N | 6 | 2 |
| 11 | BONIF_2 | N | 6 | 2 |
| 12 | NETO | N | 9 | 2 |

## GV0056B
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0056B.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | FPEDIDO | C | 10 | 0 |
| 3 | FENTREGA | C | 10 | 0 |
| 4 | CODART | C | 15 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | CANT_PED | N | 9 | 2 |
| 7 | CANT_ENT | N | 9 | 2 |
| 8 | PENDIENTE | N | 9 | 2 |
| 9 | PRECIO | N | 9 | 2 |
| 10 | BONIF_1 | N | 6 | 2 |
| 11 | BONIF_2 | N | 6 | 2 |
| 12 | NETO | N | 9 | 2 |

## GV0057A
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0057A.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | NPEDIDO | C | 12 | 0 |
| 3 | FPEDIDO | C | 10 | 0 |
| 4 | FENTREGA | C | 10 | 0 |
| 5 | CODCLI | C | 10 | 0 |
| 6 | NOMCLI | C | 40 | 0 |
| 7 | CANT_PED | N | 9 | 2 |
| 8 | CANT_ENT | N | 9 | 2 |
| 9 | PENDIENTE | N | 9 | 2 |
| 10 | PRECIO | N | 9 | 2 |
| 11 | BONIF_1 | N | 6 | 2 |
| 12 | BONIF_2 | N | 6 | 2 |
| 13 | NETO | N | 9 | 2 |
| 14 | IMPORTE | N | 9 | 2 |

## GV0057B
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0057B.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | NPEDIDO | C | 8 | 0 |
| 3 | FPEDIDO | C | 10 | 0 |
| 4 | FENTREGA | C | 10 | 0 |
| 5 | CODART | C | 15 | 0 |
| 6 | DESART | C | 40 | 0 |
| 7 | CANT_PED | N | 9 | 2 |
| 8 | CANT_ENT | N | 9 | 2 |
| 9 | PENDIENTE | N | 9 | 2 |
| 10 | PRECIO | N | 9 | 2 |
| 11 | BONIF_1 | N | 6 | 2 |
| 12 | BONIF_2 | N | 6 | 2 |
| 13 | NETO | N | 9 | 2 |
| 14 | IMPORTE | N | 9 | 2 |

## GV0065
- Registros (canónico): **8** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\gv0065.dbf` (mod. 2008-03-17, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TEXTO | L | 1 | 0 |
| 2 | NTEXTO | N | 1 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CBARRA | C | 20 | 0 |
| 5 | NREMITO | C | 12 | 0 |
| 6 | PRESUPUEST | C | 12 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | AUXDESART | M | 4 | 0 |
| 9 | UNIDAD | C | 6 | 0 |
| 10 | CANTIDAD | N | 10 | 2 |
| 11 | POR_REMITO | N | 10 | 2 |
| 12 | PAUXIL | N | 10 | 2 |
| 13 | PRECIO | N | 12 | 4 |
| 14 | APRECIO | N | 8 | 2 |
| 15 | BONIF_1 | N | 5 | 2 |
| 16 | BONIF_2 | N | 5 | 2 |
| 17 | PUNIT | N | 13 | 7 |
| 18 | PARCIAL | N | 13 | 7 |
| 19 | NDESPACHO | C | 15 | 0 |
| 20 | ADUANA | C | 15 | 0 |
| 21 | TASA | N | 5 | 2 |
| 22 | SNI | N | 5 | 2 |
| 23 | KOEF | N | 7 | 4 |
| 24 | PESIF | L | 1 | 0 |
| 25 | KPRECIO | N | 10 | 2 |
| 26 | STOCK | N | 10 | 2 |
| 27 | KPARCIAL | N | 9 | 2 |
| 28 | TD1 | C | 50 | 0 |
| 29 | TD2 | C | 50 | 0 |
| 30 | TD3 | C | 50 | 0 |
| 31 | TD4 | C | 50 | 0 |
| 32 | CODANTER | C | 15 | 0 |

## GV0070
- Registros (canónico): **5** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0070.DBF` (mod. 2006-07-03, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | NOMPROV | C | 30 | 0 |
| 3 | DOMPROV | C | 30 | 0 |
| 4 | TELEFONO | C | 25 | 0 |
| 5 | SALDO | N | 13 | 2 |

## GV0072
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\gv0072.DBF` (mod. 2014-05-20, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 40 | 0 |
| 3 | DOMCLI | C | 40 | 0 |
| 4 | LOCCLI | C | 30 | 0 |
| 5 | PROVCLI | C | 15 | 0 |
| 6 | CONTACTO | C | 40 | 0 |
| 7 | CODPOS | C | 10 | 0 |
| 8 | TELCLI_1 | C | 15 | 0 |
| 9 | TELCLI_2 | C | 15 | 0 |
| 10 | FAX | C | 15 | 0 |
| 11 | CALIFIC | C | 7 | 0 |
| 12 | DESCUENTO | N | 5 | 2 |
| 13 | BLOQUEADO | N | 1 | 0 |
| 14 | CUITCLI | C | 13 | 0 |
| 15 | REGCLI | N | 1 | 0 |
| 16 | FSALCLI | D | 8 | 0 |
| 17 | SALCLI_P | N | 10 | 2 |
| 18 | SALCLI_D | N | 10 | 2 |
| 19 | CRED_MAX | N | 10 | 2 |
| 20 | CCOND | C | 2 | 0 |
| 21 | CTRANSP | C | 3 | 0 |
| 22 | E_MAIL | C | 40 | 0 |
| 23 | ZONA | C | 2 | 0 |

## GV0073
- Registros (canónico): **3** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0073.DBF` (mod. 2006-05-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 40 | 0 |
| 3 | DOMCLI | C | 40 | 0 |
| 4 | TELEFONO | C | 25 | 0 |
| 5 | SALDO | N | 11 | 2 |

## GV0079
- Registros (canónico): **6** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0079.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 30 | 0 |
| 3 | SALDO_ANT | N | 9 | 2 |
| 4 | DEUD_VENC | N | 9 | 2 |
| 5 | DEUD_NOVE | N | 9 | 2 |
| 6 | ANTICIPOS | N | 9 | 2 |
| 7 | SALDO_ACT | N | 9 | 2 |
| 8 | CH_CARTERA | N | 9 | 2 |
| 9 | CH_PASADOS | N | 9 | 2 |
| 10 | TOTAL_CHEQ | N | 9 | 2 |
| 11 | TOTAL | N | 9 | 2 |
| 12 | CRED_MAX | N | 9 | 2 |
| 13 | EXCEDIDO | N | 9 | 2 |

## GV0080
- Registros (canónico): **1** · copias en el árbol: 46 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\GV0080.DBF` (mod. 2006-08-11, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | TIPOCOMP | C | 25 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | NETO | N | 12 | 2 |
| 7 | TOTAL | N | 12 | 2 |

## GV0081
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0081.DBF` (mod. 2006-06-22, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | POSICION | C | 4 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 40 | 0 |
| 4 | NETO | N | 12 | 2 |
| 5 | TOTAL | N | 12 | 2 |

## GV0081B
- Registros (canónico): **1** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0081B.DBF` (mod. 2002-05-18, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | OLEGRAPH | G | 4 | 0 |

## GV0082
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0082.DBF` (mod. 2006-06-22, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | POSICION | C | 4 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | UNIDAD | C | 5 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | ACUM | N | 11 | 2 |
| 7 | PPPV | N | 8 | 2 |
| 8 | TOTAL | N | 11 | 2 |

## GV0083
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\gv0083.dbf` (mod. 2004-08-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | CPROV | C | 4 | 0 |
| 3 | NOMPROV | C | 31 | 0 |
| 4 | TIPOCOMP | C | 25 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | NETO | N | 10 | 2 |
| 7 | TOTAL | N | 10 | 2 |

## GV0084
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GV0084.DBF` (mod. 2007-08-02, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | RAYA | L | 1 | 0 |
| 2 | CPROV | C | 4 | 0 |
| 3 | NOMPROV | C | 31 | 0 |
| 4 | TIPOCOMP | C | 22 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | FECHA | C | 10 | 0 |
| 7 | NETO | N | 10 | 2 |
| 8 | TOTAL | N | 11 | 2 |
| 9 | TIVA | N | 10 | 2 |
| 10 | OTROS | N | 10 | 2 |

## GV0084A
- Registros (canónico): **0** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GV0084A.DBF` (mod. 2007-08-02, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NOMPROV | C | 30 | 0 |
| 2 | NETO | N | 13 | 2 |
| 3 | TIVA | N | 13 | 2 |
| 4 | TOTAL | N | 13 | 2 |
| 5 | OTROS | N | 12 | 2 |

## GV0085
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0085.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | POSICION | C | 4 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | UNIDAD | C | 5 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | ACUM | N | 10 | 2 |
| 7 | PPPV | N | 8 | 2 |
| 8 | TOTAL | N | 10 | 2 |

## GV0085A
- Registros (canónico): **76** · copias en el árbol: 25 · variantes de esquema: 3
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\OXIMO\Bonafide\Super Restaurantes y Delivery\gv0085a.dbf` (mod. 2009-02-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | FECHAHORA | T | 8 | 0 |
| 7 | EFT_A | N | 9 | 2 |
| 8 | IMPTAR | N | 10 | 2 |
| 9 | TARJETA | C | 20 | 0 |
| 10 | CHEQUES | N | 9 | 2 |
| 11 | SUBTOTAL | N | 10 | 2 |

## GV0086
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0086.DBF` (mod. 2004-08-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | FECHA | C | 10 | 0 |
| 3 | NCOMP | C | 17 | 0 |
| 4 | FORMA | C | 30 | 0 |
| 5 | TOTAL | N | 10 | 2 |
| 6 | CODART | C | 15 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | CANTIDAD | N | 9 | 2 |
| 9 | PRECIO | N | 8 | 2 |
| 10 | LISTA | N | 8 | 2 |
| 11 | VARIACION | N | 3 | 0 |
| 12 | COSTO | N | 8 | 2 |
| 13 | UTILIDAD | N | 3 | 0 |
| 14 | DOLAR | N | 9 | 4 |
| 15 | UTIL_P | N | 11 | 2 |
| 16 | UTILPPPC | N | 11 | 2 |
| 17 | UTILPPPP | N | 6 | 2 |
| 18 | PPPC | N | 10 | 2 |

## GV0087
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\GV0087.DBF` (mod. 2005-11-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | POSICION | C | 4 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | FAMILIA | C | 30 | 0 |
| 6 | UNIDAD | C | 5 | 0 |
| 7 | CANTIDAD | N | 10 | 2 |
| 8 | ACUM | N | 10 | 2 |
| 9 | PPPV | N | 8 | 2 |
| 10 | TOTAL | N | 10 | 2 |
| 11 | TOT_COSTO | N | 10 | 2 |
| 12 | GANANCIA | N | 10 | 2 |
| 13 | PORCENTAJE | N | 8 | 2 |
| 14 | COSTO | N | 10 | 2 |

## GV0088
- Registros (canónico): **0** · copias en el árbol: 46 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\gv0088.dbf` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | POSICION | C | 4 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | UNIDAD | C | 5 | 0 |
| 6 | FAMILIA | C | 30 | 0 |
| 7 | CANTIDAD | N | 10 | 2 |
| 8 | ACUM | N | 10 | 2 |
| 9 | PPPV | N | 8 | 2 |
| 10 | TOTAL | N | 10 | 2 |

## GV0101
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0101.DBF` (mod. 2002-08-18, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMERO | L | 1 | 0 |
| 2 | IMPRIMIR | L | 1 | 0 |
| 3 | IMPRIMIR1 | L | 1 | 0 |
| 4 | IMPRIMIR2 | L | 1 | 0 |
| 5 | IMPRIMIR3 | L | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | FAMILIA | C | 30 | 0 |
| 9 | NSUBF | C | 30 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | AUXILIO2 | C | 30 | 0 |
| 12 | AUXILIO3 | C | 30 | 0 |
| 13 | CANT1 | N | 8 | 2 |
| 14 | CANT2 | N | 8 | 2 |
| 15 | CANT3 | N | 8 | 2 |
| 16 | CANT4 | N | 8 | 2 |
| 17 | CANT5 | N | 8 | 2 |
| 18 | ACUM1 | N | 10 | 2 |
| 19 | ACUM2 | N | 10 | 2 |
| 20 | ACUM3 | N | 10 | 2 |
| 21 | ACUM4 | N | 10 | 2 |
| 22 | ACUM5 | N | 10 | 2 |
| 23 | PRECIO1 | N | 8 | 2 |
| 24 | PRECIO2 | N | 8 | 2 |
| 25 | PRECIO3 | N | 8 | 2 |
| 26 | PRECIO4 | N | 8 | 2 |
| 27 | PRECIO5 | N | 8 | 2 |
| 28 | PVENTA | N | 8 | 2 |
| 29 | MEJOR | N | 8 | 2 |
| 30 | MARGEN | N | 6 | 2 |
| 31 | AUXILIO | C | 30 | 0 |

## GV0102
- Registros (canónico): **11,160** · copias en el árbol: 38 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\gv0102.dbf` (mod. 2010-02-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 10 | 0 |
| 2 | CBARRA | C | 13 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | PVENTA_1 | N | 8 | 2 |
| 5 | PVENTA_2 | N | 8 | 2 |
| 6 | EAN13 | C | 16 | 0 |
| 7 | COPIAS | N | 3 | 0 |
| 8 | C39 | C | 15 | 0 |
| 9 | I2OF5 | C | 30 | 0 |

## GV0102A
- Registros (canónico): **11,136** · copias en el árbol: 38 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\gv0102a.dbf` (mod. 2010-02-03, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 10 | 0 |
| 2 | CBARRA | C | 13 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | PVENTA_1 | N | 8 | 2 |
| 5 | PVENTA_2 | N | 8 | 2 |
| 6 | EAN13 | C | 16 | 0 |
| 7 | COPIAS | N | 3 | 0 |

## GV0112
- Registros (canónico): **1,078** · copias en el árbol: 5 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\gv0112.dbf` (mod. 2009-12-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 10 | 0 |
| 2 | CBARRA | C | 13 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | PVENTA_1 | N | 8 | 2 |
| 5 | PVENTA_2 | N | 8 | 2 |
| 6 | EAN13 | C | 16 | 0 |
| 7 | COPIAS | N | 3 | 0 |
| 8 | C39 | C | 15 | 0 |
| 9 | I2OF5 | C | 30 | 0 |

## GV0112A
- Registros (canónico): **2** · copias en el árbol: 5 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Oricam\Gestion Comercial\gv0112a.dbf` (mod. 2008-05-20, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 10 | 0 |
| 2 | CBARRA | C | 13 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | PVENTA_1 | N | 8 | 2 |
| 5 | PVENTA_2 | N | 8 | 2 |
| 6 | EAN13 | C | 16 | 0 |
| 7 | COPIAS | N | 3 | 0 |

## GV0113B
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0113B.DBF` (mod. 2003-10-10, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CUENTA | C | 6 | 0 |
| 2 | NOMCTA | C | 30 | 0 |
| 3 | IMPORTE | N | 11 | 2 |
| 4 | NOGRAV | N | 11 | 2 |

## GV0122
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\gv0122.DBF` (mod. 2007-08-01, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMVEZ | L | 1 | 0 |
| 2 | TITULO | C | 30 | 0 |
| 3 | AUXILIO | C | 1 | 0 |
| 4 | FMOV | D | 8 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | TIPOCOMP | C | 30 | 0 |
| 7 | NCOMP | C | 30 | 0 |
| 8 | CODCLI | C | 4 | 0 |
| 9 | NOMCLI | C | 40 | 0 |
| 10 | TOTAL | N | 11 | 2 |
| 11 | FECHAHORA | T | 8 | 0 |

## GV0150
- Registros (canónico): **340** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\GV0150.DBF` (mod. 2010-03-23, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MESA | N | 10 | 0 |
| 2 | PORC_PROP | N | 5 | 2 |
| 3 | DESCUENTO | N | 2 | 0 |
| 4 | TEXTO | L | 1 | 0 |
| 5 | NTEXTO | N | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | CBARRA | C | 20 | 0 |
| 8 | DESART | C | 40 | 0 |
| 9 | AUXDESART | M | 4 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | CANTIDAD | N | 10 | 2 |
| 12 | POR_REMITO | N | 10 | 2 |
| 13 | PAUXIL | N | 10 | 2 |
| 14 | PRECIO | N | 8 | 2 |
| 15 | APRECIO | N | 8 | 2 |
| 16 | BONIF_1 | N | 5 | 2 |
| 17 | BONIF_2 | N | 5 | 2 |
| 18 | PUNIT | N | 10 | 4 |
| 19 | PARCIAL | N | 10 | 4 |
| 20 | NDESPACHO | C | 15 | 0 |
| 21 | ADUANA | C | 15 | 0 |
| 22 | TASA | N | 5 | 2 |
| 23 | SNI | N | 5 | 2 |
| 24 | KOEF | N | 7 | 4 |
| 25 | COMANDA | N | 1 | 0 |
| 26 | BEBIDA | L | 1 | 0 |

## GV0151
- Registros (canónico): **5** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\GV0151.DBF` (mod. 2010-03-23, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MESA | N | 10 | 0 |
| 2 | CODCLI | C | 10 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | DOMCLI | C | 40 | 0 |
| 5 | LOCCLI | C | 30 | 0 |
| 6 | PROVCLI | C | 15 | 0 |
| 7 | CONTACTO | C | 30 | 0 |
| 8 | GIRO | C | 30 | 0 |
| 9 | CVIAJ | C | 2 | 0 |
| 10 | NOMVIAJ | C | 30 | 0 |
| 11 | CODPOS | C | 10 | 0 |
| 12 | TELCLI_1 | C | 15 | 0 |
| 13 | TELCLI_2 | C | 15 | 0 |
| 14 | FAX | C | 15 | 0 |
| 15 | E_MAIL | C | 45 | 0 |
| 16 | DESCUENTO | N | 5 | 2 |
| 17 | CUITCLI | C | 22 | 0 |
| 18 | IVA | C | 10 | 0 |
| 19 | REGCLI | N | 1 | 0 |
| 20 | DNI | N | 8 | 0 |
| 21 | TOTAL | N | 10 | 2 |
| 22 | PORC_PROP | N | 5 | 2 |
| 23 | HORA | C | 5 | 0 |

## GV0156
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0156.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | CANT_PED | N | 10 | 2 |
| 4 | CANT_ENT | N | 10 | 2 |
| 5 | PENDIENTE | N | 10 | 2 |
| 6 | PRECIO | N | 10 | 4 |
| 7 | BONIF_1 | N | 6 | 2 |
| 8 | BONIF_2 | N | 6 | 2 |
| 9 | PARCIAL | N | 10 | 3 |
| 10 | CANCELADO | C | 2 | 0 |
| 11 | CANTIDAD | N | 10 | 2 |
| 12 | PUNIT | N | 10 | 3 |

## GV0156A
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0156A.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | FPEDIDO | C | 10 | 0 |
| 3 | FENTREGA | C | 10 | 0 |
| 4 | CPROV | C | 4 | 0 |
| 5 | NOMPROV | C | 30 | 0 |
| 6 | CANT_PED | N | 9 | 2 |
| 7 | CANT_ENT | N | 9 | 2 |
| 8 | PENDIENTE | N | 9 | 2 |
| 9 | PRECIO | N | 9 | 2 |
| 10 | BONIF_1 | N | 6 | 2 |
| 11 | BONIF_2 | N | 6 | 2 |
| 12 | NETO | N | 9 | 2 |

## GV0156B
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0156B.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NPEDIDO | C | 8 | 0 |
| 2 | FPEDIDO | C | 10 | 0 |
| 3 | FENTREGA | C | 10 | 0 |
| 4 | CODART | C | 15 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | CANT_PED | N | 9 | 2 |
| 7 | CANT_ENT | N | 9 | 2 |
| 8 | PENDIENTE | N | 9 | 2 |
| 9 | PRECIO | N | 10 | 4 |
| 10 | BONIF_1 | N | 6 | 2 |
| 11 | BONIF_2 | N | 6 | 2 |
| 12 | NETO | N | 10 | 4 |

## GV0157A
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0157A.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | NPEDIDO | C | 8 | 0 |
| 3 | FPEDIDO | C | 10 | 0 |
| 4 | FENTREGA | C | 10 | 0 |
| 5 | CPROV | C | 10 | 0 |
| 6 | NOMPROV | C | 40 | 0 |
| 7 | CANT_PED | N | 9 | 2 |
| 8 | CANT_ENT | N | 9 | 2 |
| 9 | PENDIENTE | N | 9 | 2 |
| 10 | PRECIO | N | 10 | 4 |
| 11 | BONIF_1 | N | 6 | 2 |
| 12 | BONIF_2 | N | 6 | 2 |
| 13 | NETO | N | 10 | 4 |
| 14 | IMPORTE | N | 9 | 2 |

## GV0157B
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0157B.DBF` (mod. 2009-10-14, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | NPEDIDO | C | 8 | 0 |
| 3 | FPEDIDO | C | 10 | 0 |
| 4 | FENTREGA | C | 10 | 0 |
| 5 | CODART | C | 15 | 0 |
| 6 | DESART | C | 40 | 0 |
| 7 | CANT_PED | N | 9 | 2 |
| 8 | CANT_ENT | N | 9 | 2 |
| 9 | PENDIENTE | N | 9 | 2 |
| 10 | PRECIO | N | 10 | 4 |
| 11 | BONIF_1 | N | 6 | 2 |
| 12 | BONIF_2 | N | 6 | 2 |
| 13 | NETO | N | 10 | 4 |
| 14 | IMPORTE | N | 9 | 2 |

## GV0158
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0158.DBF` (mod. 2009-10-14, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TEXTO | L | 1 | 0 |
| 2 | NTEXTO | N | 1 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | CBARRA | C | 20 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | AUXDESART | M | 4 | 0 |
| 7 | UNIDAD | C | 6 | 0 |
| 8 | CANTIDAD | N | 10 | 2 |
| 9 | POR_REMITO | N | 10 | 2 |
| 10 | PAUXIL | N | 10 | 2 |
| 11 | PRECIO | N | 10 | 4 |
| 12 | APRECIO | N | 8 | 2 |
| 13 | BONIF_1 | N | 6 | 2 |
| 14 | BONIF_2 | N | 6 | 2 |
| 15 | PUNIT | N | 13 | 7 |
| 16 | PARCIAL | N | 13 | 7 |
| 17 | NDESPACHO | C | 15 | 0 |
| 18 | ADUANA | C | 15 | 0 |
| 19 | ORIGEN | C | 15 | 0 |
| 20 | TASA | N | 5 | 2 |
| 21 | SNI | N | 5 | 2 |
| 22 | KOEF | N | 7 | 4 |
| 23 | PESIF | L | 1 | 0 |
| 24 | KPRECIO | N | 10 | 2 |
| 25 | STOCK | N | 10 | 2 |
| 26 | KPARCIAL | N | 9 | 2 |
| 27 | COSTO | N | 8 | 2 |
| 28 | UTIL_1 | N | 8 | 2 |
| 29 | PESOS | N | 8 | 2 |

## GV0158B
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0158b.dbf` (mod. 2000-12-07, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NREMITO | C | 8 | 0 |
| 3 | FREMITO | D | 8 | 0 |
| 4 | MARCA | C | 1 | 0 |
| 5 | VAL_DEC | N | 8 | 2 |

## GV0161
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0161.DBF` (mod. 2008-04-08, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CTABCO | C | 15 | 0 |
| 2 | IMPBCO | N | 11 | 2 |
| 3 | CHEQUES | N | 11 | 2 |

## GV0162
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0162.DBF` (mod. 2006-04-28, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CUENTA | C | 6 | 0 |
| 2 | NCUENTA | C | 30 | 0 |
| 3 | IMPORTE | N | 10 | 2 |
| 4 | NMOV | C | 8 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | AUXILIO | C | 30 | 0 |
| 7 | ACUM | N | 11 | 2 |
| 8 | CHEQUES | N | 11 | 2 |

## GV0163
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0163.DBF` (mod. 2008-10-21, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CCONC | C | 3 | 0 |
| 2 | CUENTA | C | 6 | 0 |
| 3 | NCUENTA | C | 15 | 0 |
| 4 | IMPORTE | N | 11 | 2 |
| 5 | DEBE | N | 11 | 2 |
| 6 | HABER | N | 11 | 2 |
| 7 | CHEQUES | N | 11 | 2 |
| 8 | NCONC | C | 43 | 0 |
| 9 | AUXILIO | C | 40 | 0 |
| 10 | FMOV | D | 8 | 0 |

## GV0177
- Registros (canónico): **0** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\gv0177.dbf` (mod. 2003-01-04, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 10 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 10 | 0 |
| 4 | CANTIDAD | N | 10 | 4 |
| 5 | PRECIO | N | 10 | 4 |

## GV0180
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0180.DBF` (mod. 2003-12-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | IMPRIMIR | L | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | FAMILIA | C | 51 | 0 |
| 5 | UNIDAD | C | 6 | 0 |
| 6 | NOMPROV | C | 30 | 0 |
| 7 | STOCK | N | 10 | 2 |
| 8 | UBICACION | C | 10 | 0 |
| 9 | AUXILIO | C | 51 | 0 |
| 10 | MINIMO | N | 10 | 2 |
| 11 | REPONER | N | 10 | 2 |
| 12 | PRECIO | N | 8 | 2 |
| 13 | TOTAL | N | 10 | 2 |
| 14 | INVENTARIO | N | 10 | 2 |
| 15 | TOCADO | L | 1 | 0 |

## GV0181
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0181.DBF` (mod. 2006-07-05, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | POSICION | C | 4 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | FAMILIA | C | 30 | 0 |
| 6 | UNIDAD | C | 5 | 0 |
| 7 | CANTIDAD | N | 10 | 2 |
| 8 | ACUM | N | 10 | 2 |
| 9 | PPPV | N | 9 | 3 |
| 10 | TOTAL | N | 10 | 2 |
| 11 | COSTO | N | 9 | 3 |
| 12 | TCOSTO | N | 10 | 2 |
| 13 | GANANCIA | N | 10 | 2 |
| 14 | PORC | N | 7 | 2 |

## GV0182
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0182.DBF` (mod. 2005-11-01, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | NOMCLI | C | 30 | 0 |
| 3 | COMPROBANT | C | 25 | 0 |
| 4 | NETO | N | 10 | 2 |
| 5 | COSTO | N | 10 | 2 |
| 6 | GANANCIA | N | 10 | 2 |
| 7 | PORCENTAJE | N | 8 | 2 |

## GV0185
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0185.DBF` (mod. 2006-06-22, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 40 | 0 |
| 3 | CODART | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | PRECIO | N | 10 | 2 |
| 7 | PARCIAL | N | 11 | 2 |

## GV0186
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0186.dbf` (mod. 2003-06-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | POSICION | C | 4 | 0 |
| 2 | FAMILIA | C | 30 | 0 |
| 3 | NSUBF | C | 30 | 0 |
| 4 | UNIDAD | C | 5 | 0 |
| 5 | CANTIDAD | N | 10 | 2 |
| 6 | ACUM | N | 10 | 2 |
| 7 | PPPV | N | 8 | 2 |
| 8 | TOTAL | N | 10 | 2 |

## GV0187
- Registros (canónico): **0** · copias en el árbol: 25 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\gv0187.dbf` (mod. 2007-08-07, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TITULO | L | 1 | 0 |
| 2 | POSICION | C | 4 | 0 |
| 3 | NSUBF | C | 30 | 0 |
| 4 | FAMILIA | C | 30 | 0 |
| 5 | UNIDAD | C | 5 | 0 |
| 6 | CANTIDAD | N | 10 | 2 |
| 7 | ACUM | N | 11 | 2 |
| 8 | PPPV | N | 8 | 2 |
| 9 | TOTAL | N | 11 | 2 |
| 10 | STOCK | N | 10 | 2 |
| 11 | COEFI | N | 10 | 4 |
| 12 | AUXILIO | C | 50 | 0 |

## GV0188
- Registros (canónico): **1** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0188.dbf` (mod. 2003-07-24, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | POSICION | C | 4 | 0 |
| 2 | CPROV | C | 4 | 0 |
| 3 | NOMPROV | C | 30 | 0 |
| 4 | NETO | N | 10 | 2 |
| 5 | TOTAL | N | 10 | 2 |

## GV0200
- Registros (canónico): **36** · copias en el árbol: 21 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0200.dbf` (mod. 2003-01-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CCONC | C | 3 | 0 |
| 2 | NCONC | C | 30 | 0 |
| 3 | ENT_SAL | C | 8 | 0 |
| 4 | CUENTA | C | 6 | 0 |

## GV0201
- Registros (canónico): **100** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0201.DBF` (mod. 2006-09-06, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | ITEM | C | 3 | 0 |
| 2 | NCHEQUE | N | 10 | 0 |
| 3 | BANCO | C | 25 | 0 |
| 4 | IMPCHE | N | 10 | 2 |
| 5 | PLAZA | C | 25 | 0 |
| 6 | FECCHE | D | 8 | 0 |
| 7 | FECVTO | D | 8 | 0 |
| 8 | BORRADO | C | 1 | 0 |
| 9 | PROP_TER | N | 1 | 0 |
| 10 | NCTACTE | C | 15 | 0 |
| 11 | FECCHE2 | C | 10 | 0 |

## GV0201A
- Registros (canónico): **2** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0201A.DBF` (mod. 2003-10-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | COMEN | C | 30 | 0 |
| 4 | CCONC | C | 3 | 0 |
| 5 | EFT_A | N | 10 | 2 |
| 6 | EFT_D | N | 10 | 2 |
| 7 | NCONC | C | 20 | 0 |

## GV0201B
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0201B.DBF` (mod. 2002-08-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | COMEN | C | 30 | 0 |
| 4 | CCONC | C | 3 | 0 |
| 5 | EFT_A | N | 10 | 2 |
| 6 | EFT_D | N | 10 | 2 |
| 7 | NCHEQUE | N | 10 | 0 |
| 8 | BANCO | C | 20 | 0 |
| 9 | PLAZA | C | 20 | 0 |
| 10 | FECCHE | D | 8 | 0 |
| 11 | FECVTO | D | 8 | 0 |
| 12 | IMPCHE | N | 10 | 2 |

## GV0203
- Registros (canónico): **100** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0203.DBF` (mod. 2006-09-09, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | ITEM | C | 3 | 0 |
| 2 | NCHEQUE | N | 10 | 0 |
| 3 | BANCO | C | 25 | 0 |
| 4 | IMPCHE | N | 10 | 2 |
| 5 | PLAZA | C | 25 | 0 |
| 6 | FECCHE | D | 8 | 0 |
| 7 | FECVTO | D | 8 | 0 |
| 8 | BORRADO | C | 1 | 0 |
| 9 | PROP_TER | N | 1 | 0 |
| 10 | A | C | 10 | 0 |
| 11 | FECCHE2 | C | 10 | 0 |

## GV0203A
- Registros (canónico): **2** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0203a.DBF` (mod. 2006-09-09, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | COMEN | C | 30 | 0 |
| 4 | CCONC | C | 3 | 0 |
| 5 | EFT_A | N | 11 | 2 |
| 6 | EFT_D | N | 10 | 2 |
| 7 | NCONC | C | 27 | 0 |
| 8 | NCUENTA | C | 15 | 0 |

## GV0203B
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\gv0203B.DBF` (mod. 2006-09-09, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | FMOV | D | 8 | 0 |
| 3 | COMEN | C | 50 | 0 |
| 4 | CCONC | C | 3 | 0 |
| 5 | EFT_A | N | 11 | 2 |
| 6 | EFT_D | N | 10 | 2 |
| 7 | NCHEQUE | N | 10 | 0 |
| 8 | BANCO | C | 20 | 0 |
| 9 | PLAZA | C | 20 | 0 |
| 10 | FECCHE | D | 8 | 0 |
| 11 | FECVTO | D | 8 | 0 |
| 12 | IMPCHE | N | 10 | 2 |

## GV0204
- Registros (canónico): **42** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\GV0204.DBF` (mod. 2003-09-30, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | AUXNMOV | C | 8 | 0 |
| 3 | COMEN | C | 33 | 0 |
| 4 | NCONC | C | 30 | 0 |
| 5 | EFT_A_E | N | 10 | 2 |
| 6 | EFT_D_E | N | 10 | 2 |
| 7 | TARJETA | N | 10 | 2 |
| 8 | EFT_A_S | N | 10 | 2 |
| 9 | EFT_D_S | N | 10 | 2 |
| 10 | NCHEQUE | N | 10 | 0 |
| 11 | PROP_TER | N | 1 | 0 |
| 12 | CART_PAS | N | 1 | 0 |
| 13 | FECVTO | C | 10 | 0 |
| 14 | IMPCHE_S | N | 10 | 2 |
| 15 | IMPCHE_E | N | 10 | 2 |

## GV0204B
- Registros (canónico): **2** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\GV0204B.DBF` (mod. 2003-09-30, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TARJETA | C | 20 | 0 |
| 2 | CUPON | C | 20 | 0 |
| 3 | CUOTAS | N | 2 | 0 |
| 4 | IMPTAR | N | 10 | 2 |
| 5 | TIPOCOMP | C | 30 | 0 |

## GV0205
- Registros (canónico): **11** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0205.DBF` (mod. 2009-07-23, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | FECHA | C | 10 | 0 |
| 3 | TIPOCOMP | C | 80 | 0 |
| 4 | DEBE | N | 10 | 2 |
| 5 | HABER | N | 10 | 2 |
| 6 | SALDO | N | 10 | 2 |

## GV0206
- Registros (canónico): **35** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\Super Kelo\GV0206.DBF` (mod. 2007-12-18, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TARJETA | C | 20 | 0 |
| 2 | FECHA | D | 8 | 0 |
| 3 | CUPON | C | 20 | 0 |
| 4 | TIPOCOMP | C | 25 | 0 |
| 5 | IMPORTE | N | 10 | 2 |
| 6 | CUOTAS | N | 2 | 0 |
| 7 | LOTE | C | 5 | 0 |
| 8 | CRED_DEB | C | 5 | 0 |

## GV0206B
- Registros (canónico): **39** · copias en el árbol: 29 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\GV0206b.DBF` (mod. 2012-06-16, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TARJETA | C | 20 | 0 |
| 2 | FECHA | D | 8 | 0 |
| 3 | CUPON | C | 20 | 0 |
| 4 | TIPOCOMP | C | 25 | 0 |
| 5 | IMPORTE | N | 10 | 2 |
| 6 | CUOTAS | N | 2 | 0 |
| 7 | LOTE | C | 5 | 0 |
| 8 | CRED_DEB | C | 5 | 0 |

## GV0207
- Registros (canónico): **0** · copias en el árbol: 6 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0207.DBF` (mod. 2006-09-28, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | FECHA | C | 10 | 0 |
| 3 | SALDOC | N | 12 | 2 |
| 4 | SALDOB | N | 12 | 2 |
| 5 | INGRESOS | N | 12 | 2 |
| 6 | CARTERA | N | 12 | 2 |
| 7 | PROPIOS | N | 12 | 2 |
| 8 | PAGOS | N | 12 | 2 |
| 9 | COBRANZAS | N | 12 | 2 |
| 10 | EGRESOS | N | 12 | 2 |
| 11 | SUELDOS | N | 12 | 2 |
| 12 | IMPUESTOS | N | 12 | 2 |

## GV0207A
- Registros (canónico): **0** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\gv0207a.dbf` (mod. 2006-09-28, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | FECHA | C | 10 | 0 |
| 3 | SALDOC | N | 12 | 2 |
| 4 | SALDOB | N | 12 | 2 |
| 5 | INGRESOS | N | 12 | 2 |
| 6 | CARTERA | N | 12 | 2 |
| 7 | PROPIOS | N | 12 | 2 |
| 8 | PAGOS | N | 12 | 2 |
| 9 | COBRANZAS | N | 12 | 2 |
| 10 | EGRESOS | N | 12 | 2 |
| 11 | SUELDOS | N | 12 | 2 |
| 12 | IMPUESTOS | N | 12 | 2 |
| 13 | SALDO | N | 12 | 2 |
| 14 | ACUM | N | 12 | 2 |

## GV0220
- Registros (canónico): **0** · copias en el árbol: 29 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\gv0220.DBF` (mod. 2008-05-08, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | RAYA | L | 1 | 0 |
| 2 | NMOV | C | 8 | 0 |
| 3 | FECHA | C | 10 | 0 |
| 4 | AUXILIO | D | 8 | 0 |
| 5 | COMEN | C | 60 | 0 |
| 6 | EFT_A_E | N | 10 | 2 |
| 7 | EFT_D_E | N | 10 | 2 |
| 8 | CHEQUES_E | N | 10 | 2 |
| 9 | EFT_A_S | N | 10 | 2 |
| 10 | EFT_D_S | N | 10 | 2 |
| 11 | CHEQUES_S | N | 10 | 2 |
| 12 | NCUENTA | C | 15 | 0 |
| 13 | TARJETAS | N | 12 | 2 |

## GV0222
- Registros (canónico): **1** · copias en el árbol: 12 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\gv0222.dbf` (mod. 2007-01-30, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PAGINA | C | 8 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | AUXILIO | C | 25 | 0 |
| 4 | NCOMP | C | 22 | 0 |
| 5 | FECHA | D | 8 | 0 |
| 6 | FMOV | C | 10 | 0 |
| 7 | NOMCLI | C | 30 | 0 |
| 8 | CUIT | C | 13 | 0 |
| 9 | REGCLI | N | 1 | 0 |
| 10 | NETO | N | 10 | 2 |
| 11 | EXENTO | N | 10 | 2 |
| 12 | TASA | C | 6 | 0 |
| 13 | IVA | N | 10 | 2 |
| 14 | TOTAL | N | 10 | 2 |
| 15 | TCOMP | C | 1 | 0 |
| 16 | SUBTOTAL | N | 12 | 2 |
| 17 | ALICUOTAS | N | 1 | 0 |
| 18 | CUIT_OK | L | 1 | 0 |

## GV0222A
- Registros (canónico): **0** · copias en el árbol: 12 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\gv0222a.dbf` (mod. 2007-01-29, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CAMPO | C | 253 | 0 |
| 2 | CAMPO2 | C | 145 | 0 |

## GV0223
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\GV0223.DBF` (mod. 2010-01-12, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | DETALLE | L | 1 | 0 |
| 2 | CODCLI | C | 15 | 0 |
| 3 | NOMCLI | C | 40 | 0 |
| 4 | FECHA | D | 8 | 0 |
| 5 | TIPOCOMP | C | 13 | 0 |
| 6 | CANTIDAD | N | 9 | 2 |
| 7 | NDEVOL | C | 13 | 0 |
| 8 | DEVOLUCION | N | 9 | 2 |

## GV0251B
- Registros (canónico): **11** · copias en el árbol: 29 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\GV0251B.DBF` (mod. 2006-09-09, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | FMOV | C | 10 | 0 |
| 3 | COMEN | C | 30 | 0 |
| 4 | NCUENTA | C | 15 | 0 |
| 5 | BANCO | C | 20 | 0 |
| 6 | IMPCHE | N | 10 | 2 |
| 7 | NCHEQUE | N | 10 | 0 |
| 8 | FECVTO | C | 10 | 0 |
| 9 | EFT_A | N | 10 | 2 |
| 10 | EFT_D | N | 10 | 2 |

## GVSERIE
- Registros (canónico): **2** · copias en el árbol: 6 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\GVSERIE.DBF` (mod. 2007-02-21, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | CIA | C | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | CDEP | C | 2 | 0 |
| 9 | CANTIDAD | N | 10 | 2 |
| 10 | BONIF_1 | N | 5 | 2 |
| 11 | BONIF_2 | N | 5 | 2 |
| 12 | PVENTA | N | 13 | 6 |
| 13 | PVENTA_D | N | 13 | 6 |
| 14 | POR_REMITO | N | 10 | 2 |
| 15 | NDESPACHO | C | 15 | 0 |
| 16 | ADUANA | C | 15 | 0 |
| 17 | TASA | N | 5 | 2 |
| 18 | SNI | N | 5 | 2 |
| 19 | COSTO | N | 9 | 2 |

---

# Categoría: temporal/auxiliar

## AMALIA
- Registros (canónico): **934** · copias en el árbol: 7 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\amalia.DBF` (mod. 2007-04-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | A | C | 11 | 0 |
| 2 | B | C | 16 | 0 |
| 3 | C | C | 59 | 0 |
| 4 | D | N | 7 | 0 |
| 5 | E | N | 20 | 15 |
| 6 | F | N | 20 | 15 |

## AUXART
- Registros (canónico): **10** · copias en el árbol: 6 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Vametal\Gestion Comercial\AUXART.DBF` (mod. 2009-05-28, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | CBARRA | C | 20 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | FAMILIA | C | 30 | 0 |
| 6 | NSUBF | C | 30 | 0 |
| 7 | UNIDAD | C | 6 | 0 |
| 8 | UNICOMP | C | 6 | 0 |
| 9 | COEFICIENT | N | 8 | 2 |
| 10 | STOCK | L | 1 | 0 |
| 11 | EXP_UN | N | 1 | 0 |
| 12 | CPROV | C | 4 | 0 |
| 13 | NOMPROV | C | 30 | 0 |
| 14 | COSTO | N | 9 | 3 |
| 15 | COSTIVA | N | 1 | 0 |
| 16 | UTIL_1 | N | 6 | 2 |
| 17 | UTIL_2 | N | 6 | 2 |
| 18 | UTIL_3 | N | 6 | 2 |
| 19 | UTIL_4 | N | 6 | 2 |
| 20 | PVENTA_1 | N | 8 | 2 |
| 21 | PVENTA_2 | N | 8 | 2 |
| 22 | PVENTA_3 | N | 8 | 2 |
| 23 | PVENTA_4 | N | 8 | 2 |
| 24 | TASA | N | 5 | 2 |
| 25 | SNI | N | 5 | 2 |
| 26 | BONIF_11 | N | 5 | 2 |
| 27 | BONIF_12 | N | 5 | 2 |
| 28 | BONIF_21 | N | 5 | 2 |
| 29 | BONIF_22 | N | 5 | 2 |
| 30 | BONIF_31 | N | 5 | 2 |
| 31 | BONIF_32 | N | 5 | 2 |
| 32 | BONIF_41 | N | 5 | 2 |
| 33 | BONIF_42 | N | 5 | 2 |
| 34 | EN_DOLARES | L | 1 | 0 |
| 35 | ULT_PRC | D | 8 | 0 |
| 36 | NAC_IMP | N | 1 | 0 |
| 37 | NDESPACHO | C | 20 | 0 |
| 38 | ADUANA | C | 20 | 0 |
| 39 | ORIGEN | C | 20 | 0 |
| 40 | CUENTA | C | 6 | 0 |
| 41 | COMBUS | L | 1 | 0 |
| 42 | IMP_INT | N | 10 | 5 |
| 43 | IMPUESTOS | N | 6 | 2 |
| 44 | NOTA | M | 4 | 0 |
| 45 | FILE1 | M | 4 | 0 |
| 46 | STRETCH | N | 1 | 0 |
| 47 | DIBUJO | M | 4 | 0 |
| 48 | FOTO | G | 4 | 0 |
| 49 | CODPROVE | C | 15 | 0 |

## AUXICTA
- Registros (canónico): **0** · copias en el árbol: 1 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXICTA.DBF` (mod. 2008-08-16, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | NUMERO | C | 5 | 0 |
| 3 | DETALLE | C | 10 | 0 |
| 4 | DEBE | N | 12 | 2 |
| 5 | HABER | N | 12 | 2 |
| 6 | SALDO | N | 12 | 2 |

## AUXICTE
- Registros (canónico): **1** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXICTE.DBF` (mod. 2009-01-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | NUMERO | C | 5 | 0 |
| 3 | DETALLE | C | 10 | 0 |
| 4 | DEBE | N | 12 | 2 |
| 5 | HABER | N | 12 | 2 |
| 6 | SALDO | N | 12 | 2 |

## AUXICUA
- Registros (canónico): **0** · copias en el árbol: 1 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXICUA.DBF` (mod. 2008-09-13, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CUENTA | C | 3 | 0 |
| 2 | FECHA | D | 8 | 0 |
| 3 | DEBE | N | 10 | 2 |
| 4 | HABER | N | 10 | 2 |
| 5 | DETALLE | C | 35 | 0 |

## AUXICUE
- Registros (canónico): **0** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXICUE.DBF` (mod. 2008-09-13, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | DEBE | N | 10 | 2 |
| 3 | HABER | N | 10 | 2 |
| 4 | DETALLE | C | 35 | 0 |

## AUXIDIA
- Registros (canónico): **46** · copias en el árbol: 1 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXIDIA.DBF` (mod. 2008-08-15, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | DEBE | N | 10 | 2 |
| 3 | HABER | N | 10 | 2 |
| 4 | SALDO | N | 10 | 2 |
| 5 | CODIGO | C | 3 | 0 |
| 6 | NOMBRE | C | 25 | 0 |
| 7 | DETALLE | C | 35 | 0 |

## AUXIIMP
- Registros (canónico): **626** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXIDBF-NTX\AUXIIMP.DBF` (mod. 2007-12-06, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | CODIGO | C | 4 | 0 |
| 3 | FACTURA | C | 5 | 0 |
| 4 | NOMBRE | C | 20 | 0 |
| 5 | IMPORTE | N | 10 | 2 |
| 6 | TOTAL | N | 12 | 2 |

## AUXIIVA
- Registros (canónico): **66** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXIDBF-NTX\AUXIIVA.DBF` (mod. 2003-08-12, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | COMPROBAN | C | 2 | 0 |
| 3 | TIPO | C | 4 | 0 |
| 4 | AOBIVA | C | 1 | 0 |
| 5 | FACTURA | C | 13 | 0 |
| 6 | CLIENTE | C | 4 | 0 |
| 7 | NOMBRE | C | 30 | 0 |
| 8 | CUIT | C | 13 | 0 |
| 9 | IVA | C | 2 | 0 |
| 10 | BRUTO21 | N | 10 | 2 |
| 11 | BRUTO10 | N | 10 | 2 |
| 12 | IVAAL21 | N | 10 | 2 |
| 13 | IVAAL10 | N | 10 | 2 |
| 14 | TOTAL | N | 10 | 2 |

## AUXIIVC
- Registros (canónico): **0** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXI-ELSA\AUXIIVC.DBF` (mod. 2007-10-06, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | NUMERO | C | 13 | 0 |
| 3 | TC | C | 3 | 0 |
| 4 | AOBIVA | C | 1 | 0 |
| 5 | NOMBRE | C | 27 | 0 |
| 6 | CUIT | C | 13 | 0 |
| 7 | TOTAL | N | 15 | 2 |
| 8 | N_GR_21 | N | 15 | 2 |
| 9 | N_GR_27 | N | 15 | 2 |
| 10 | N_GR_105 | N | 15 | 2 |
| 11 | EXENTO | N | 15 | 2 |
| 12 | IVA_21 | N | 15 | 2 |
| 13 | IVA_27 | N | 15 | 2 |
| 14 | IVA_105 | N | 15 | 2 |
| 15 | PER_GCIA | N | 15 | 2 |
| 16 | PER_IVA | N | 15 | 2 |
| 17 | PER_IBRU | N | 15 | 2 |
| 18 | ABASTO | N | 15 | 2 |
| 19 | I_INTERN | N | 15 | 2 |
| 20 | RET_IVA | N | 15 | 2 |
| 21 | RET_GCIA | N | 15 | 2 |
| 22 | RET_IBRU | N | 15 | 2 |

## AUXIIVE
- Registros (canónico): **0** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\IVAS\AUXI.VS.ELSA- LIBERAR\AUXIIVE.DBF` (mod. 2009-06-15, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHA | D | 8 | 0 |
| 2 | COMPROBAN | C | 2 | 0 |
| 3 | TIPO | C | 4 | 0 |
| 4 | AOBIVA | C | 1 | 0 |
| 5 | FACTURA | C | 13 | 0 |
| 6 | CLIENTE | C | 4 | 0 |
| 7 | NOMBRE | C | 30 | 0 |
| 8 | CUIT | C | 13 | 0 |
| 9 | IVA | C | 2 | 0 |
| 10 | BRUTO21 | N | 10 | 2 |
| 11 | BRUTO10 | N | 10 | 2 |
| 12 | IVAAL21 | N | 10 | 2 |
| 13 | IVAAL10 | N | 10 | 2 |
| 14 | TOTAL | N | 10 | 2 |

## AUXILIO
- Registros (canónico): **0** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\super old\faytim 2\AUXILIO.DBF` (mod. 2002-10-28, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | CODCLI | C | 4 | 0 |
| 9 | ANULADO | C | 1 | 0 |
| 10 | CONTADO | C | 1 | 0 |
| 11 | PAGADO | C | 1 | 0 |
| 12 | PORAJUSTE | L | 1 | 0 |
| 13 | ACT_STOCK | C | 1 | 0 |
| 14 | CCOND | C | 2 | 0 |
| 15 | CVIAJ | C | 2 | 0 |
| 16 | LIQUIDA | L | 1 | 0 |
| 17 | NRO_PRESUP | C | 12 | 0 |
| 18 | TASA | N | 5 | 2 |
| 19 | SNI | N | 5 | 2 |
| 20 | IMPIVA_1 | N | 10 | 2 |
| 21 | IMPIVA_3 | N | 10 | 2 |
| 22 | IMP_SNI | N | 9 | 2 |
| 23 | SUBTOTAL | N | 10 | 2 |
| 24 | ANTES_DTO | N | 10 | 2 |
| 25 | IMP_DTO | N | 10 | 2 |
| 26 | POR_DTO | N | 5 | 2 |
| 27 | IMP_INT | N | 10 | 3 |
| 28 | IMPUESTOS | N | 10 | 3 |
| 29 | TDOLAR | N | 10 | 2 |
| 30 | DOLAR | N | 8 | 4 |
| 31 | DIF_COT | N | 8 | 2 |
| 32 | CHEQUES | N | 9 | 2 |
| 33 | EFECTIVO | N | 9 | 2 |
| 34 | EFT_A | N | 9 | 2 |
| 35 | EFT_D | N | 9 | 2 |
| 36 | NMOV | C | 8 | 0 |
| 37 | RUBRO | C | 20 | 0 |
| 38 | NOMCLI | C | 30 | 0 |
| 39 | CUITCLI | C | 13 | 0 |
| 40 | REGCLI | N | 1 | 0 |
| 41 | PROVCLI | C | 15 | 0 |
| 42 | TEXTO1 | M | 4 | 0 |
| 43 | IMPTEXTO1 | N | 9 | 2 |
| 44 | TASA1 | N | 5 | 2 |
| 45 | TEXTO2 | M | 4 | 0 |
| 46 | IMPTEXTO2 | N | 9 | 2 |
| 47 | TASA2 | N | 5 | 2 |
| 48 | TEXTO3 | M | 4 | 0 |
| 49 | IMPTEXTO3 | N | 9 | 2 |
| 50 | TASA3 | N | 5 | 2 |
| 51 | CUENTA1 | C | 6 | 0 |
| 52 | CUENTA2 | C | 6 | 0 |
| 53 | CUENTA3 | C | 6 | 0 |
| 54 | TARJETA | C | 20 | 0 |
| 55 | CUPON | C | 20 | 0 |
| 56 | IMPTAR | N | 10 | 2 |
| 57 | RECARGO | N | 10 | 2 |
| 58 | CUOTAS | N | 2 | 0 |

## AUXILIO1
- Registros (canónico): **22** · copias en el árbol: 14 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\AUXILIO1.DBF` (mod. 2008-06-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | CBARRA | C | 20 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | FAMILIA | C | 30 | 0 |
| 6 | NSUBF | C | 30 | 0 |
| 7 | UNIDAD | C | 6 | 0 |
| 8 | UNICOMP | C | 6 | 0 |
| 9 | COEFICIENT | N | 8 | 2 |
| 10 | STOCK | N | 8 | 2 |
| 11 | MINIMO | N | 8 | 2 |
| 12 | INVENTARIO | N | 8 | 2 |
| 13 | EXP_UN | N | 1 | 0 |
| 14 | CPROV | C | 4 | 0 |
| 15 | NOMPROV | C | 30 | 0 |
| 16 | COSTO | N | 8 | 2 |
| 17 | COSTIVA | N | 1 | 0 |
| 18 | UTIL_1 | N | 6 | 2 |
| 19 | UTIL_2 | N | 6 | 2 |
| 20 | UTIL_3 | N | 6 | 2 |
| 21 | UTIL_4 | N | 6 | 2 |
| 22 | PVENTA_1 | N | 8 | 2 |
| 23 | PVENTA_2 | N | 8 | 2 |
| 24 | PVENTA_3 | N | 8 | 2 |
| 25 | PVENTA_4 | N | 8 | 2 |
| 26 | EN_DOLARES | L | 1 | 0 |
| 27 | ULT_PRC | D | 8 | 0 |
| 28 | TASA | N | 5 | 2 |
| 29 | SNI | N | 5 | 2 |
| 30 | BONIF_11 | N | 5 | 2 |
| 31 | BONIF_12 | N | 5 | 2 |
| 32 | BONIF_21 | N | 5 | 2 |
| 33 | BONIF_22 | N | 5 | 2 |
| 34 | BONIF_31 | N | 5 | 2 |
| 35 | BONIF_32 | N | 5 | 2 |
| 36 | BONIF_41 | N | 5 | 2 |
| 37 | BONIF_42 | N | 5 | 2 |
| 38 | NAC_IMP | N | 1 | 0 |
| 39 | NDESPACHO | C | 15 | 0 |
| 40 | ADUANA | C | 15 | 0 |
| 41 | ORIGEN | C | 15 | 0 |
| 42 | LLEVAR_STK | L | 1 | 0 |
| 43 | BEBIDA | L | 1 | 0 |
| 44 | CODSPROV | C | 15 | 0 |

## AUXILIO2
- Registros (canónico): **0** · copias en el árbol: 14 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\AUXILIO2.DBF` (mod. 2008-06-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | LETRA | C | 1 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | CODART | C | 15 | 0 |
| 8 | DESART | C | 40 | 0 |
| 9 | CDEP | C | 2 | 0 |
| 10 | CANTIDAD | N | 10 | 2 |
| 11 | BONIF_1 | N | 5 | 2 |
| 12 | BONIF_2 | N | 5 | 2 |
| 13 | PVENTA | N | 9 | 2 |
| 14 | POR_REMITO | N | 10 | 2 |
| 15 | NDESPACHO | C | 15 | 0 |
| 16 | ADUANA | C | 15 | 0 |
| 17 | TASA | N | 5 | 2 |
| 18 | SNI | N | 5 | 2 |

## AUXILIO3
- Registros (canónico): **0** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\AUXILIO3.DBF` (mod. 2008-06-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NCOMP | C | 8 | 0 |
| 3 | TCOMP | C | 1 | 0 |
| 4 | CPROV | C | 4 | 0 |
| 5 | CIA | C | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | CDEP | C | 2 | 0 |
| 8 | CANTIDAD | N | 10 | 2 |
| 9 | BONIF_1 | N | 5 | 2 |
| 10 | BONIF_2 | N | 5 | 2 |
| 11 | PCOMPRA | N | 8 | 2 |

## AUXILIO4
- Registros (canónico): **0** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\AUXILIO4.DBF` (mod. 2008-06-11, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MESA | N | 10 | 0 |
| 2 | CODCLI | C | 10 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | DOMCLI | C | 40 | 0 |
| 5 | LOCCLI | C | 30 | 0 |
| 6 | PROVCLI | C | 15 | 0 |
| 7 | CONTACTO | C | 30 | 0 |
| 8 | GIRO | C | 30 | 0 |
| 9 | CVIAJ | C | 2 | 0 |
| 10 | NOMVIAJ | C | 30 | 0 |
| 11 | CODPOS | C | 10 | 0 |
| 12 | TELCLI_1 | C | 15 | 0 |
| 13 | TELCLI_2 | C | 15 | 0 |
| 14 | FAX | C | 15 | 0 |
| 15 | E_MAIL | C | 45 | 0 |
| 16 | DESCUENTO | N | 5 | 2 |
| 17 | CUITCLI | C | 22 | 0 |
| 18 | IVA | C | 10 | 0 |
| 19 | REGCLI | N | 1 | 0 |
| 20 | DNI | N | 8 | 0 |
| 21 | TOTAL | N | 10 | 2 |
| 22 | PORC_PROP | N | 5 | 2 |
| 23 | HORA | C | 5 | 0 |

## AUXMOV
- Registros (canónico): **4** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\AUXMOV.DBF` (mod. 2012-05-16, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | FMOV | D | 8 | 0 |
| 4 | COMEN | C | 33 | 0 |
| 5 | CCONC | C | 3 | 0 |
| 6 | EFT_A | N | 10 | 2 |
| 7 | EFT_D | N | 10 | 2 |
| 8 | TARJETAS | N | 10 | 2 |
| 9 | CAJA | N | 1 | 0 |
| 10 | DOLAR | N | 8 | 3 |

## AUXMOV2
- Registros (canónico): **10** · copias en el árbol: 10 · variantes de esquema: 3
- Fuente: `Revosolution Software\Super Kelo\AUXMOV2.DBF` (mod. 2007-09-21, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | CODCLI | C | 4 | 0 |
| 9 | ANULADO | C | 1 | 0 |
| 10 | CONTADO | C | 1 | 0 |
| 11 | PAGADO | C | 1 | 0 |
| 12 | PORAJUSTE | L | 1 | 0 |
| 13 | ACT_STOCK | C | 1 | 0 |
| 14 | CCOND | C | 2 | 0 |
| 15 | CVIAJ | C | 2 | 0 |
| 16 | LIQUIDA | L | 1 | 0 |
| 17 | NRO_PRESUP | C | 12 | 0 |
| 18 | TASA | N | 5 | 2 |
| 19 | SNI | N | 5 | 2 |
| 20 | BIEN_USO | L | 1 | 0 |
| 21 | IMPIVA_1 | N | 10 | 2 |
| 22 | IMPIVA_3 | N | 10 | 2 |
| 23 | IMP_SNI | N | 9 | 2 |
| 24 | SUBTOTAL | N | 10 | 2 |
| 25 | ANTES_DTO | N | 10 | 2 |
| 26 | IMP_DTO | N | 10 | 2 |
| 27 | POR_DTO | N | 5 | 2 |
| 28 | TDOLAR | N | 10 | 2 |
| 29 | DOLAR | N | 8 | 4 |
| 30 | DIF_COT | N | 8 | 2 |
| 31 | CHEQUES | N | 9 | 2 |
| 32 | EFECTIVO | N | 9 | 2 |
| 33 | EFT_A | N | 9 | 2 |
| 34 | EFT_D | N | 9 | 2 |
| 35 | NMOV | C | 8 | 0 |
| 36 | RUBRO | C | 20 | 0 |
| 37 | NOMCLI | C | 40 | 0 |
| 38 | CUITCLI | C | 13 | 0 |
| 39 | REGCLI | N | 1 | 0 |
| 40 | PROVCLI | C | 15 | 0 |
| 41 | TEXTO1 | M | 4 | 0 |
| 42 | IMPTEXTO1 | N | 9 | 2 |
| 43 | TASA1 | N | 5 | 2 |
| 44 | TEXTO2 | M | 4 | 0 |
| 45 | IMPTEXTO2 | N | 9 | 2 |
| 46 | TASA2 | N | 5 | 2 |
| 47 | TEXTO3 | M | 4 | 0 |
| 48 | IMPTEXTO3 | N | 9 | 2 |
| 49 | TASA3 | N | 5 | 2 |
| 50 | CUENTA1 | C | 6 | 0 |
| 51 | CUENTA2 | C | 6 | 0 |
| 52 | CUENTA3 | C | 6 | 0 |
| 53 | TARJETA | C | 20 | 0 |
| 54 | CUPON | C | 20 | 0 |
| 55 | IMPTAR | N | 10 | 2 |
| 56 | RECARGO | N | 10 | 2 |
| 57 | CUOTAS | N | 2 | 0 |
| 58 | LOTE | C | 5 | 0 |
| 59 | CRED_DEB | N | 1 | 0 |
| 60 | CTABCO | C | 15 | 0 |
| 61 | IMPBCO | N | 10 | 2 |
| 62 | NMOVBCO | C | 8 | 0 |
| 63 | NRECIBO | C | 8 | 0 |
| 64 | IMPSALDO | N | 8 | 2 |
| 65 | COSTO | N | 10 | 2 |
| 66 | OCOMPRA | C | 15 | 0 |
| 67 | FECHAHORA | T | 8 | 0 |

## AUXMOV3
- Registros (canónico): **0** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\AUXMOV3.DBF` (mod. 2010-06-07, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | SELECC | L | 1 | 0 |
| 2 | NCHEQUE | N | 10 | 0 |
| 3 | CIA | C | 1 | 0 |
| 4 | NCTACTE | C | 15 | 0 |
| 5 | CCONC | C | 3 | 0 |
| 6 | BANCO | C | 20 | 0 |
| 7 | PLAZA | C | 20 | 0 |
| 8 | FECCHE | D | 8 | 0 |
| 9 | FECVTO | D | 8 | 0 |
| 10 | IMPCHE | N | 12 | 2 |
| 11 | DOLAR | N | 8 | 2 |
| 12 | HS_ACREDIT | N | 3 | 0 |
| 13 | PROP_TER | N | 1 | 0 |
| 14 | CART_PAS | N | 1 | 0 |
| 15 | EMITIDO | C | 30 | 0 |
| 16 | CODCLI | C | 4 | 0 |
| 17 | FRECEP | D | 8 | 0 |
| 18 | CPROV | C | 4 | 0 |
| 19 | PASADO_A | C | 30 | 0 |
| 20 | FPASADO | D | 8 | 0 |
| 21 | NCOM_ENT | C | 17 | 0 |
| 22 | TCOM_ENT | C | 1 | 0 |
| 23 | NCOM_SAL | C | 17 | 0 |
| 24 | TCOM_SAL | C | 1 | 0 |
| 25 | NMOV | C | 8 | 0 |
| 26 | NRECIBO | C | 8 | 0 |
| 27 | OPAGO | C | 8 | 0 |
| 28 | NMOV_S | C | 8 | 0 |
| 29 | RECHAZADO | N | 1 | 0 |
| 30 | FIRMANTE | C | 30 | 0 |
| 31 | CUENTA | C | 20 | 0 |
| 32 | CUIT | C | 13 | 0 |
| 33 | CUITBCO | C | 13 | 0 |
| 34 | CDEP | C | 2 | 0 |

## C1
- Registros (canónico): **22** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\C1.DBF` (mod. 2018-07-04, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | CIA | C | 1 | 0 |
| 3 | FMOV | D | 8 | 0 |
| 4 | COMEN | C | 33 | 0 |
| 5 | CCONC | C | 3 | 0 |
| 6 | EFT_A | N | 10 | 2 |
| 7 | EFT_D | N | 10 | 2 |
| 8 | TARJETAS | N | 10 | 2 |
| 9 | CAJA | N | 1 | 0 |
| 10 | DOLAR | N | 8 | 3 |

## C2
- Registros (canónico): **0** · copias en el árbol: 21 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\C2.DBF` (mod. 2018-07-04, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NMOV | C | 8 | 0 |
| 2 | NCUENTA | C | 15 | 0 |
| 3 | FMOV | D | 8 | 0 |
| 4 | CIA | C | 1 | 0 |
| 5 | CCONC | C | 3 | 0 |
| 6 | EFECTIVO | N | 10 | 2 |
| 7 | COMEN | C | 30 | 0 |
| 8 | BCO | N | 1 | 0 |

## CACA
- Registros (canónico): **6** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\CACA.DBF` (mod. 2008-10-25, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MESA | N | 10 | 0 |
| 2 | PORC_PROP | N | 5 | 2 |
| 3 | DESCUENTO | N | 2 | 0 |
| 4 | TEXTO | L | 1 | 0 |
| 5 | NTEXTO | N | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | CBARRA | C | 20 | 0 |
| 8 | DESART | C | 40 | 0 |
| 9 | AUXDESART | M | 4 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | CANTIDAD | N | 10 | 2 |
| 12 | POR_REMITO | N | 10 | 2 |
| 13 | PAUXIL | N | 10 | 2 |
| 14 | PRECIO | N | 8 | 2 |
| 15 | APRECIO | N | 8 | 2 |
| 16 | BONIF_1 | N | 5 | 2 |
| 17 | BONIF_2 | N | 5 | 2 |
| 18 | PUNIT | N | 10 | 4 |
| 19 | PARCIAL | N | 10 | 4 |
| 20 | NDESPACHO | C | 15 | 0 |
| 21 | ADUANA | C | 15 | 0 |
| 22 | TASA | N | 5 | 2 |
| 23 | SNI | N | 5 | 2 |
| 24 | KOEF | N | 7 | 4 |
| 25 | COMANDA | N | 1 | 0 |
| 26 | BEBIDA | L | 1 | 0 |
| 27 | SUM_CANTID | N | 16 | 2 |

## CONSULTA
- Registros (canónico): **2** · copias en el árbol: 8 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\bonafide\Super Restaurantes y Delivery\Consulta.DBF` (mod. 2008-06-02, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FECHAHORA | T | 8 | 0 |
| 2 | DOMCLI | C | 40 | 0 |
| 3 | CODCLI | C | 10 | 0 |
| 4 | SUBTOTAL | N | 10 | 2 |
| 5 | NOMVIAJ | C | 30 | 0 |

## EQUIS
- Registros (canónico): **838** · copias en el árbol: 50 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\equis.DBF` (mod. 2010-02-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NZETA | C | 8 | 0 |
| 3 | FMOV | D | 8 | 0 |
| 4 | TOTAL | N | 10 | 2 |
| 5 | IMPIVA | N | 10 | 2 |

## FALSA
- Registros (canónico): **1** · copias en el árbol: 10 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\FALSA.DBF` (mod. 2007-01-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | REGISTRO | C | 10 | 0 |

## FOXUSER
- Registros (canónico): **118** · copias en el árbol: 51 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\FOXUSER.DBF` (mod. 2020-03-25, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TYPE | C | 12 | 0 |
| 2 | ID | C | 12 | 0 |
| 3 | NAME | M | 4 | 0 |
| 4 | READONLY | L | 1 | 0 |
| 5 | CKVAL | N | 6 | 0 |
| 6 | DATA | M | 4 | 0 |
| 7 | UPDATED | D | 8 | 0 |

## LISTADO
- Registros (canónico): **8,194** · copias en el árbol: 25 · variantes de esquema: 3
- Fuente: `Revosolution Software\BAck UP CLiente\super old\Super POS faytim\Listado.DBF` (mod. 2005-09-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | CBARRA | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | COMBUS | L | 1 | 0 |
| 6 | FAMILIA | C | 30 | 0 |
| 7 | NSUBF | C | 30 | 0 |
| 8 | UNIDAD | C | 6 | 0 |
| 9 | UNICOMP | C | 6 | 0 |
| 10 | COEFICIENT | N | 8 | 2 |
| 11 | STOCK | N | 9 | 2 |
| 12 | MINIMO | N | 9 | 2 |
| 13 | EXP_UN | N | 1 | 0 |
| 14 | CPROV | C | 4 | 0 |
| 15 | NOMPROV | C | 30 | 0 |
| 16 | COSTO | N | 9 | 2 |
| 17 | COSTIVA | N | 1 | 0 |
| 18 | UTIL_1 | N | 6 | 2 |
| 19 | UTIL_2 | N | 6 | 2 |
| 20 | UTIL_3 | N | 6 | 2 |
| 21 | UTIL_4 | N | 6 | 2 |
| 22 | PVENTA_1 | N | 9 | 2 |
| 23 | PVENTA_2 | N | 9 | 2 |
| 24 | PVENTA_3 | N | 9 | 2 |
| 25 | PVENTA_4 | N | 9 | 2 |
| 26 | TASA | N | 5 | 2 |
| 27 | SNI | N | 5 | 2 |
| 28 | BONIF_11 | N | 5 | 2 |
| 29 | BONIF_12 | N | 5 | 2 |
| 30 | BONIF_21 | N | 5 | 2 |
| 31 | BONIF_22 | N | 5 | 2 |
| 32 | BONIF_31 | N | 5 | 2 |
| 33 | BONIF_32 | N | 5 | 2 |
| 34 | BONIF_41 | N | 5 | 2 |
| 35 | BONIF_42 | N | 5 | 2 |
| 36 | IMP_INT | N | 9 | 5 |
| 37 | IMPUESTOS | N | 6 | 2 |
| 38 | EN_DOLARES | L | 1 | 0 |
| 39 | ULT_PRC | D | 8 | 0 |
| 40 | NAC_IMP | N | 1 | 0 |
| 41 | NDESPACHO | C | 15 | 0 |
| 42 | ADUANA | C | 15 | 0 |
| 43 | ORIGEN | C | 15 | 0 |
| 44 | CUENTA | C | 6 | 0 |
| 45 | CODSPROV | C | 15 | 0 |
| 46 | INVENTARIO | N | 9 | 2 |

## MI_EQUIS
- Registros (canónico): **10** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\CSJORGE\POS\MI_EQUIS.DBF` (mod. 2012-04-05, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FAMILIA | C | 30 | 0 |
| 2 | IMPORTE | N | 10 | 2 |

## TEMPTEXT
- Registros (canónico): **449** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\temptext.DBF` (mod. 2007-01-22, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TESTLINE | C | 200 | 0 |

## TEMPVIEW
- Registros (canónico): **73** · copias en el árbol: 46 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Corp BsAs\Super POS\tempview.DBF` (mod. 2008-08-09, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | TESTNAME | C | 40 | 0 |
| 2 | TESTFILE | C | 100 | 0 |
| 3 | TESTFIND | C | 80 | 0 |
| 4 | TESTOBJ | C | 25 | 0 |
| 5 | TESTPARENT | C | 25 | 0 |
| 6 | TESTMEMO | M | 4 | 0 |
| 7 | TESTFIELD | C | 15 | 0 |
| 8 | TESTREC | N | 6 | 0 |
| 9 | LISTEXT | L | 1 | 0 |
| 10 | FILETYPE | C | 3 | 0 |

## ZETAS
- Registros (canónico): **592** · copias en el árbol: 50 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion\zetas.DBF` (mod. 2010-02-10, dBASE III/FoxPro sin memo)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PREFIJO | C | 4 | 0 |
| 2 | NZETA | C | 8 | 0 |
| 3 | FMOV | D | 8 | 0 |
| 4 | TOTAL | N | 10 | 2 |
| 5 | IMPIVA | N | 10 | 2 |

## _ADMA
- Registros (canónico): **5,465** · copias en el árbol: 40 · variantes de esquema: 12
- Fuente: `Revosolution Software\Super Kelo\_ADMA.DBF` (mod. 2008-07-08, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMERO | L | 1 | 0 |
| 2 | IMPRIMIR | L | 1 | 0 |
| 3 | IMPRIMIR1 | L | 1 | 0 |
| 4 | IMPRIMIR2 | L | 1 | 0 |
| 5 | IMPRIMIR3 | L | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | FAMILIA | C | 30 | 0 |
| 9 | NSUBF | C | 30 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | AUXILIO2 | C | 30 | 0 |
| 12 | AUXILIO3 | C | 30 | 0 |
| 13 | NOMPROV | C | 30 | 0 |
| 14 | SIGNO | C | 3 | 0 |
| 15 | PRECIO | N | 8 | 2 |
| 16 | CONIVA | N | 8 | 2 |
| 17 | UBICACION | C | 10 | 0 |
| 18 | AUXILIO | C | 30 | 0 |

## _ADMB
- Registros (canónico): **5,465** · copias en el árbol: 40 · variantes de esquema: 11
- Fuente: `Revosolution Software\Super Kelo\_ADMB.DBF` (mod. 2008-07-08, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMERO | L | 1 | 0 |
| 2 | IMPRIMIR | L | 1 | 0 |
| 3 | IMPRIMIR1 | L | 1 | 0 |
| 4 | IMPRIMIR2 | L | 1 | 0 |
| 5 | IMPRIMIR3 | L | 1 | 0 |
| 6 | CODART | C | 15 | 0 |
| 7 | DESART | C | 40 | 0 |
| 8 | FAMILIA | C | 30 | 0 |
| 9 | NSUBF | C | 30 | 0 |
| 10 | UNIDAD | C | 6 | 0 |
| 11 | AUXILIO2 | C | 30 | 0 |
| 12 | AUXILIO3 | C | 30 | 0 |
| 13 | NOMPROV | C | 30 | 0 |
| 14 | SIGNO | C | 3 | 0 |
| 15 | PRECIO | N | 8 | 2 |
| 16 | CONIVA | N | 8 | 2 |
| 17 | UBICACION | C | 10 | 0 |
| 18 | AUXILIO | C | 30 | 0 |

## _ADMC
- Registros (canónico): **8,693** · copias en el árbol: 38 · variantes de esquema: 8
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Super\_ADMC.DBF` (mod. 2009-11-24, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PAGINA | C | 8 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | AUXILIO | C | 25 | 0 |
| 4 | NCOMP | C | 22 | 0 |
| 5 | FECHA | D | 8 | 0 |
| 6 | FMOV | C | 10 | 0 |
| 7 | NOMCLI | C | 31 | 0 |
| 8 | CUIT | C | 13 | 0 |
| 9 | CONDIVA | C | 10 | 0 |
| 10 | REGCLI | N | 1 | 0 |
| 11 | PROVCLI | C | 15 | 0 |
| 12 | NETO | N | 9 | 2 |
| 13 | EXENTO | N | 9 | 2 |
| 14 | TASA | C | 6 | 0 |
| 15 | IVA | N | 9 | 2 |
| 16 | SOBRETASA | N | 9 | 2 |
| 17 | SNI | N | 9 | 2 |
| 18 | IMPPER | N | 9 | 2 |
| 19 | IMPINT | N | 9 | 2 |
| 20 | TOTAL | N | 9 | 2 |
| 21 | ACUM1 | N | 9 | 2 |
| 22 | ACUM2 | N | 9 | 2 |
| 23 | ACUM3 | N | 9 | 2 |
| 24 | ACUM4 | N | 9 | 2 |
| 25 | ACUM5 | N | 9 | 2 |
| 26 | KACUM1 | N | 9 | 2 |
| 27 | KACUM2 | N | 9 | 2 |
| 28 | KACUM3 | N | 9 | 2 |
| 29 | KACUM4 | N | 9 | 2 |
| 30 | KACUM5 | N | 9 | 2 |

## _ADMD
- Registros (canónico): **77** · copias en el árbol: 40 · variantes de esquema: 6
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\OXIMO\Bonafide\Super Restaurantes y Delivery\_ADMD.DBF` (mod. 2009-01-09, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NZETA | C | 15 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | REGCLI | N | 1 | 0 |
| 4 | DESDE | C | 8 | 0 |
| 5 | HASTA | C | 8 | 0 |
| 6 | FMOV | C | 10 | 0 |
| 7 | NETO_1 | N | 10 | 2 |
| 8 | IVA_1 | N | 10 | 2 |
| 9 | TOTAL_1 | N | 10 | 2 |
| 10 | NETO_2 | N | 10 | 2 |
| 11 | IVA_2 | N | 10 | 2 |
| 12 | TOTAL_2 | N | 10 | 2 |
| 13 | NETO_3 | N | 10 | 2 |
| 14 | IVA_3 | N | 10 | 2 |
| 15 | TOTAL_3 | N | 10 | 2 |
| 16 | NETO_4 | N | 10 | 2 |
| 17 | IVA_4 | N | 10 | 2 |
| 18 | TOTAL_4 | N | 10 | 2 |
| 19 | NETO_5 | N | 10 | 2 |
| 20 | IVA_5 | N | 10 | 2 |
| 21 | TOTAL_5 | N | 10 | 2 |
| 22 | NETO_6 | N | 10 | 2 |
| 23 | IVA_6 | N | 10 | 2 |
| 24 | TOTAL_6 | N | 10 | 2 |
| 25 | NETO_7 | N | 10 | 2 |
| 26 | IVA_7 | N | 10 | 2 |
| 27 | TOTAL_7 | N | 10 | 2 |
| 28 | TOTAL | N | 10 | 2 |

## _ADME
- Registros (canónico): **51** · copias en el árbol: 40 · variantes de esquema: 4
- Fuente: `Revosolution Software\Gestion Comercial Super Evaristore\SuperGestion\_ADME.DBF` (mod. 2008-06-22, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 35 | 0 |
| 3 | TIPOCOMP | C | 27 | 0 |
| 4 | FECHA | C | 10 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | CANTIDAD | N | 8 | 2 |
| 7 | PRECIO | N | 9 | 2 |
| 8 | PARCIAL | N | 10 | 2 |

## _ADMF
- Registros (canónico): **123** · copias en el árbol: 40 · variantes de esquema: 3
- Fuente: `Revosolution Software\USB Pendrive Revosolution\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\_ADMF.DBF` (mod. 2010-03-06, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | AUXILIO | D | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | TELEFONO | C | 25 | 0 |
| 5 | FECVTO | C | 10 | 0 |
| 6 | TIPOCOMP | C | 30 | 0 |
| 7 | IMPCUOTA | N | 10 | 2 |
| 8 | PAGADO | N | 10 | 2 |
| 9 | SALDO | N | 10 | 2 |
| 10 | ACUMULADO | N | 10 | 2 |
| 11 | TOTAL | N | 10 | 2 |

## _ADMG
- Registros (canónico): **128** · copias en el árbol: 40 · variantes de esquema: 5
- Fuente: `Revosolution Software\USB Pendrive Revosolution\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\_ADMG.DBF` (mod. 2010-03-03, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | FMOV | D | 8 | 0 |
| 7 | TIPOCOMP | C | 36 | 0 |
| 8 | DEBE | N | 10 | 2 |
| 9 | HABER | N | 10 | 2 |
| 10 | SALDO | N | 10 | 2 |
| 11 | OBSERVAC | C | 40 | 0 |
| 12 | PIC | C | 15 | 0 |

## _ADMH
- Registros (canónico): **573** · copias en el árbol: 6 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Cab S Jorge 0302010\Gestion Comercial\_ADMH.DBF` (mod. 2009-10-29, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | LETRA | C | 1 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | NCOMP | C | 8 | 0 |
| 4 | TCOMP | C | 1 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | FMOV | D | 8 | 0 |
| 7 | TIPOCOMP | C | 36 | 0 |
| 8 | DEBE | N | 10 | 2 |
| 9 | HABER | N | 10 | 2 |
| 10 | SALDO | N | 10 | 2 |
| 11 | OBSERVAC | C | 40 | 0 |
| 12 | PIC | C | 15 | 0 |

## _ADMI
- Registros (canónico): **9** · copias en el árbol: 15 · variantes de esquema: 2
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Super\_ADMI.DBF` (mod. 2009-11-24, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 6 | 0 |
| 4 | CANTIDAD | N | 10 | 2 |
| 5 | PRECIO | N | 10 | 2 |
| 6 | BONIF_1 | N | 5 | 2 |
| 7 | BONIF_2 | N | 5 | 2 |
| 8 | PARCIAL | N | 11 | 2 |
| 9 | NTEXTO | N | 2 | 0 |

## _ADMINA
- Registros (canónico): **376** · copias en el árbol: 17 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\_ADMINA.DBF` (mod. 2007-05-22, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | MARCA | C | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | CBARRA | C | 15 | 0 |
| 4 | DESART | C | 40 | 0 |
| 5 | COMBUS | L | 1 | 0 |
| 6 | FAMILIA | C | 30 | 0 |
| 7 | NSUBF | C | 30 | 0 |
| 8 | UNIDAD | C | 6 | 0 |
| 9 | UNICOMP | C | 6 | 0 |
| 10 | COEFICIENT | N | 8 | 2 |
| 11 | STOCK | N | 9 | 2 |
| 12 | MINIMO | N | 9 | 2 |
| 13 | EXP_UN | N | 1 | 0 |
| 14 | CPROV | C | 4 | 0 |
| 15 | NOMPROV | C | 30 | 0 |
| 16 | COSTO | N | 9 | 2 |
| 17 | COSTIVA | N | 1 | 0 |
| 18 | UTIL_1 | N | 6 | 2 |
| 19 | UTIL_2 | N | 6 | 2 |
| 20 | UTIL_3 | N | 6 | 2 |
| 21 | UTIL_4 | N | 6 | 2 |
| 22 | PVENTA_1 | N | 9 | 2 |
| 23 | PVENTA_2 | N | 9 | 2 |
| 24 | PVENTA_3 | N | 9 | 2 |
| 25 | PVENTA_4 | N | 9 | 2 |
| 26 | TASA | N | 5 | 2 |
| 27 | SNI | N | 5 | 2 |
| 28 | BONIF_11 | N | 5 | 2 |
| 29 | BONIF_12 | N | 5 | 2 |
| 30 | BONIF_21 | N | 5 | 2 |
| 31 | BONIF_22 | N | 5 | 2 |
| 32 | BONIF_31 | N | 5 | 2 |
| 33 | BONIF_32 | N | 5 | 2 |
| 34 | BONIF_41 | N | 5 | 2 |
| 35 | BONIF_42 | N | 5 | 2 |
| 36 | IMP_INT | N | 9 | 5 |
| 37 | IMPUESTOS | N | 6 | 2 |
| 38 | EN_DOLARES | L | 1 | 0 |
| 39 | ULT_PRC | D | 8 | 0 |
| 40 | NAC_IMP | N | 1 | 0 |
| 41 | NDESPACHO | C | 15 | 0 |
| 42 | ADUANA | C | 15 | 0 |
| 43 | ORIGEN | C | 15 | 0 |
| 44 | CUENTA | C | 6 | 0 |
| 45 | CODSPROV | C | 15 | 0 |
| 46 | INVENTARIO | N | 9 | 2 |

## _ADMINB
- Registros (canónico): **98** · copias en el árbol: 17 · variantes de esquema: 4
- Fuente: `Revosolution Software\BAck UP CLiente\super old\Super POS faytim\_ADMINB.DBF` (mod. 2005-09-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | IMPRIMIR | L | 1 | 0 |
| 2 | CODART | C | 15 | 0 |
| 3 | DESART | C | 40 | 0 |
| 4 | FAMILIA | C | 51 | 0 |
| 5 | UNIDAD | C | 6 | 0 |
| 6 | NOMPROV | C | 30 | 0 |
| 7 | STOCK | N | 10 | 2 |
| 8 | UBICACION | C | 10 | 0 |
| 9 | AUXILIO | C | 51 | 0 |
| 10 | MINIMO | N | 10 | 2 |
| 11 | REPONER | N | 10 | 2 |
| 12 | PRECIO | N | 8 | 2 |
| 13 | TOTAL | N | 10 | 2 |
| 14 | CORTE | N | 10 | 2 |

## _ADMINC
- Registros (canónico): **114** · copias en el árbol: 17 · variantes de esquema: 3
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\Super POS 08 2009\Super POS\_ADMINC.DBF` (mod. 2009-08-05, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | FMOV | D | 8 | 0 |
| 2 | CODCLI | C | 4 | 0 |
| 3 | NOMCLI | C | 30 | 0 |
| 4 | TIPOCOMP | C | 25 | 0 |
| 5 | FECHA | C | 10 | 0 |
| 6 | NETO | N | 12 | 2 |
| 7 | TOTAL | N | 12 | 2 |

## _ADMIND
- Registros (canónico): **26** · copias en el árbol: 17 · variantes de esquema: 2
- Fuente: `Revosolution Software\BAck UP CLiente\hhhh\Super POS\_ADMIND.DBF` (mod. 2011-05-24, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NZETA | C | 15 | 0 |
| 2 | PREFIJO | C | 4 | 0 |
| 3 | REGCLI | N | 1 | 0 |
| 4 | DESDE | C | 8 | 0 |
| 5 | HASTA | C | 8 | 0 |
| 6 | FMOV | C | 10 | 0 |
| 7 | NETO_1 | N | 10 | 2 |
| 8 | IVA_1 | N | 10 | 2 |
| 9 | TOTAL_1 | N | 10 | 2 |
| 10 | NETO_2 | N | 10 | 2 |
| 11 | IVA_2 | N | 10 | 2 |
| 12 | TOTAL_2 | N | 10 | 2 |
| 13 | NETO_3 | N | 10 | 2 |
| 14 | IVA_3 | N | 10 | 2 |
| 15 | TOTAL_3 | N | 10 | 2 |
| 16 | NETO_4 | N | 10 | 2 |
| 17 | IVA_4 | N | 10 | 2 |
| 18 | TOTAL_4 | N | 10 | 2 |
| 19 | NETO_5 | N | 10 | 2 |
| 20 | IVA_5 | N | 10 | 2 |
| 21 | TOTAL_5 | N | 10 | 2 |
| 22 | NETO_6 | N | 10 | 2 |
| 23 | IVA_6 | N | 10 | 2 |
| 24 | TOTAL_6 | N | 10 | 2 |
| 25 | NETO_7 | N | 10 | 2 |
| 26 | IVA_7 | N | 10 | 2 |
| 27 | TOTAL_7 | N | 10 | 2 |
| 28 | TOTAL | N | 10 | 2 |

## _ADMINE
- Registros (canónico): **27** · copias en el árbol: 17 · variantes de esquema: 2
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\POSSSS\Super POS\_ADMINE.DBF` (mod. 2007-12-18, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODCLI | C | 4 | 0 |
| 2 | NOMCLI | C | 30 | 0 |
| 3 | TIPOCOMP | C | 27 | 0 |
| 4 | FECHA | C | 10 | 0 |
| 5 | FMOV | D | 8 | 0 |
| 6 | CANTIDAD | N | 8 | 2 |
| 7 | PRECIO | N | 8 | 2 |
| 8 | PARCIAL | N | 8 | 2 |

## _ADMINF
- Registros (canónico): **2** · copias en el árbol: 13 · variantes de esquema: 1
- Fuente: `Revosolution Software\Punto De Venta\2009\Super POS\_ADMINF.DBF` (mod. 2009-08-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | PRIMERO | L | 1 | 0 |
| 2 | FECHA | C | 10 | 0 |
| 3 | NCOMP | C | 26 | 0 |
| 4 | CODART | C | 15 | 0 |
| 5 | DESART | C | 40 | 0 |
| 6 | UNIDAD | C | 6 | 0 |
| 7 | CANTIDAD | N | 8 | 2 |
| 8 | PRECIO | N | 10 | 2 |
| 9 | BONIF_1 | N | 5 | 2 |
| 10 | BONIF_2 | N | 5 | 2 |
| 11 | PARCIAL | N | 10 | 2 |
| 12 | TOTAL | N | 10 | 2 |
| 13 | OBSERVAC | C | 30 | 0 |

## _ADMING
- Registros (canónico): **0** · copias en el árbol: 11 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\hhhh\Super POS\_ADMING.DBF` (mod. 2011-04-29, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CDEP | C | 2 | 0 |
| 2 | LETRA | C | 1 | 0 |
| 3 | PREFIJO | C | 4 | 0 |
| 4 | NCOMP | C | 8 | 0 |
| 5 | TCOMP | C | 1 | 0 |
| 6 | CIA | C | 1 | 0 |
| 7 | FMOV | D | 8 | 0 |
| 8 | CPROV | C | 4 | 0 |
| 9 | ANULADO | C | 1 | 0 |
| 10 | CONTADO | C | 1 | 0 |
| 11 | PAGADO | C | 1 | 0 |
| 12 | PORAJUSTE | L | 1 | 0 |
| 13 | MESIVA | C | 5 | 0 |
| 14 | CCOND | C | 2 | 0 |
| 15 | IMPORTACIO | N | 1 | 0 |
| 16 | CUENTA | C | 6 | 0 |
| 17 | CUENTANOGR | C | 6 | 0 |
| 18 | CUENTAOTRO | C | 6 | 0 |
| 19 | TASA1 | N | 5 | 2 |
| 20 | TASA2 | N | 5 | 2 |
| 21 | SOBRETASA | N | 5 | 2 |
| 22 | IVA1 | N | 10 | 2 |
| 23 | IVA2 | N | 10 | 2 |
| 24 | IMPIVA_1 | N | 10 | 2 |
| 25 | IMPIVA_2 | N | 10 | 2 |
| 26 | IMPIVA_3 | N | 10 | 2 |
| 27 | SUBTOTAL | N | 10 | 2 |
| 28 | IMPPER | N | 10 | 2 |
| 29 | IMPINT | N | 10 | 2 |
| 30 | INGBRU | N | 10 | 2 |
| 31 | IMPRET | N | 10 | 2 |
| 32 | OTROS | N | 10 | 2 |
| 33 | TDOLAR | N | 10 | 2 |
| 34 | DOLAR | N | 8 | 4 |
| 35 | DIF_COT | N | 8 | 2 |
| 36 | CHEQUES | N | 9 | 2 |
| 37 | EFECTIVO | N | 9 | 2 |
| 38 | EFT_A | N | 9 | 2 |
| 39 | EFT_D | N | 9 | 2 |
| 40 | IMPBCO | N | 9 | 2 |
| 41 | CTABCO | C | 15 | 0 |
| 42 | NMOVBCO | C | 8 | 0 |
| 43 | NMOV | C | 8 | 0 |
| 44 | RUBRO | C | 20 | 0 |
| 45 | NOMPROV | C | 30 | 0 |
| 46 | CUITPROV | C | 13 | 0 |
| 47 | REGPROV | N | 1 | 0 |
| 48 | NDESPACHO | C | 15 | 0 |
| 49 | ADUANA | C | 15 | 0 |
| 50 | ORIGEN | C | 15 | 0 |

## _ADMK
- Registros (canónico): **2** · copias en el árbol: 15 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial\_ADMK.DBF` (mod. 2013-12-18, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | NCHEQUE | C | 10 | 0 |
| 2 | BANCO | C | 25 | 0 |
| 3 | FECCHE | C | 10 | 0 |
| 4 | FECVTO | C | 10 | 0 |
| 5 | IMPCHE | N | 10 | 2 |
| 6 | ESTADO | C | 30 | 0 |

## _ADMW
- Registros (canónico): **0** · copias en el árbol: 2 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\Pronokal\Gestion Comercial\_ADMW.DBF` (mod. 2007-08-01, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | COSTO | N | 8 | 2 |
| 3 | CODSPROV | C | 20 | 0 |
| 4 | FORMA_PAGO | C | 30 | 0 |
| 5 | ULT_LISTA | C | 8 | 0 |
| 6 | ULT_FECHA | D | 8 | 0 |
| 7 | NOMPROV | C | 35 | 0 |

## _DARIOA
- Registros (canónico): **4** · copias en el árbol: 1 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\_DARIOA.DBF` (mod. 2010-11-08, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 6 | 0 |
| 4 | CANTIDAD | N | 10 | 2 |
| 5 | PRECIO | N | 8 | 2 |
| 6 | BONIF_1 | N | 5 | 2 |
| 7 | BONIF_2 | N | 5 | 2 |
| 8 | PARCIAL | N | 8 | 2 |

## _GABRIELAA
- Registros (canónico): **1** · copias en el árbol: 1 · variantes de esquema: 1
- Fuente: `Revosolution Software\BAck UP CLiente\3gcom\Super POS\_GABRIELAA.DBF` (mod. 2011-02-26, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CODART | C | 15 | 0 |
| 2 | DESART | C | 40 | 0 |
| 3 | UNIDAD | C | 6 | 0 |
| 4 | CANTIDAD | N | 10 | 2 |
| 5 | PRECIO | N | 8 | 2 |
| 6 | BONIF_1 | N | 5 | 2 |
| 7 | BONIF_2 | N | 5 | 2 |
| 8 | PARCIAL | N | 8 | 2 |

## _MARCELO_UNO_W
- Registros (canónico): **2** · copias en el árbol: 4 · variantes de esquema: 1
- Fuente: `Revosolution Software\USB Pendrive Revosolution\Super Backups\OMEGA\Gestion Comercial\_MARCELO_uno_W.DBF` (mod. 2008-09-05, Visual FoxPro)

| # | Campo | Tipo | Long | Dec |
|--:|---|---|--:|--:|
| 1 | CPROV | C | 4 | 0 |
| 2 | COSTO | N | 8 | 2 |
| 3 | CODSPROV | C | 20 | 0 |
| 4 | FORMA_PAGO | C | 30 | 0 |
| 5 | ULT_LISTA | C | 8 | 0 |
| 6 | ULT_FECHA | D | 8 | 0 |
| 7 | NOMPROV | C | 35 | 0 |
