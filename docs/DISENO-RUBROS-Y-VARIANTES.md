# ZGC — Multipropósito: rubros y variantes de artículos

> Mandato de César (2026-07-04): el software no debe quedar orientado solo a
> supermercados. Debe servir a retail de ropa, calzado y electrónica, entre otros.
> **Los POS son full orientados al rubro; la gestión central es general con
> customización por rubro.** Ejemplos del mandato: bebidas manejan gustos;
> la ropa maneja talles y colores.

## 1. Estadística: qué se vende en retail/e-commerce (2025-2026)

### Argentina (estudio anual CACE 2025, publicado feb-2026)

- Facturación e-commerce 2025: $35,3 billones (+60% nominal, contra 31% de inflación); 645 millones de unidades (+28%); ticket promedio $143.128.
- **Por facturación**: 1) Pasajes y turismo · 2) Alimentos, bebidas y limpieza ·
  3) Audio, imagen, consolas, TI y telefonía · 4) Artículos para el hogar ·
  5) Electrodomésticos.
- **Por unidades**: 1) Alimentos y bebidas · 2) Herramientas y construcción ·
  3) Hogar, muebles y jardín · 4) Electrodomésticos y AC · 5) Infantiles ·
  6) Accesorios para vehículos · 7) Oficina e industria · 8) **Indumentaria
  deportiva** · 9) Limpieza · 10) Belleza.
- Electrónica (celulares y computación) lidera el crecimiento.

### Global 2026

- Electrónica ~USD 922 mil millones online (la mayor categoría) · Moda/indumentaria
  ~USD 760 mil millones (segunda) · Alimentos ~USD 906 mil millones proyectado 2026 ·
  Belleza ~USD 190 mil millones. Las de mayor recurrencia de compra (alimentos,
  bebidas, belleza) son las de crecimiento más rápido.

Fuentes: [CACE Estadísticas](https://cace.org.ar/pages/estadisticas) ·
[Infobae — categorías 2025](https://www.infobae.com/economia/2026/02/06/las-compras-online-crecieron-60-en-2025-cuales-fueron-los-productos-y-servicios-mas-demandados/) ·
[Infobae — qué creció más](https://www.infobae.com/economia/2026/02/16/comercio-electronico-cuales-fueron-las-categorias-y-productos-que-mas-crecieron-en-la-argentina-y-cuanto-pesan-las-plataformas-chinas/) ·
[Shopify — top categorías 2026](https://www.shopify.com/ae/blog/top-online-shopping-categories) ·
[Accio — categorías online 2026](https://www.accio.com/business/top-product-categories-sold-online)

## 2. Evaluación contra el encuadre actual de ZGC

Encuadre actual (migración 003): familias/subfamilias, marcas, unidades, 4 listas
costo+margen, código de barras único, `en_dolares`+cotización, flags POS super
(pesable, envase retornable, venta por depto.), stock por depósito con kardex.

| Categoría (volumen AR/global) | ¿Encaja hoy? | Qué le falta |
|---|---|---|
| Alimentos y bebidas (AR #1 unidades) | ✅ Sí — familias, pesables, EAN por sabor (así opera el súper real) | Variantes opcionales para **gustos/presentaciones** bajo un mismo artículo padre; vencimiento/lote (post-MVP) |
| Herramientas y construcción (AR #2) | ✅ Sí — familias/marcas/unidades alcanzan | Variantes ocasionales por **medida** |
| Hogar, muebles y jardín (AR #3) | ✅ Sí | Variantes ocasionales por **color/medida** |
| Electrodomésticos (AR #4) | ✅ Sí — `en_dolares` ya resuelve lo crítico | **N° de serie** por unidad para garantía (post-MVP) |
| Electrónica / celulares / TI (global #1) | ⚠️ Parcial | Variantes por **capacidad/color**; serie/IMEI y garantía (post-MVP) |
| **Indumentaria y calzado** (global #2) | ❌ **No encaja** | **Matriz talle × color**: stock, EAN y etiqueta POR variante; curva de talles; grilla de carga rápida. Es el gap estructural |
| Infantiles / juguetería (AR #5) | ✅ Sí | Variantes ocasionales por edad/talle |
| Accesorios vehículos / repuestos (AR #6) | ✅ Sí | Atributos libres (compatibilidad); código de fabricante ya trazado |
| Belleza y cuidado personal (AR #10, global en alza) | ⚠️ Parcial | Variantes por **tono/tamaño**; vencimiento (post-MVP) |

**Conclusión**: el encuadre actual cubre bien ~6 de las 9 categorías de mayor
volumen. El gap estructural es **variantes** (talle/color/gusto/capacidad/tono),
que es exactamente lo que separa un sistema de supermercado de uno de retail
multipropósito. Serie/IMEI, lote/vencimiento y recetas de restaurante son capas
posteriores que NO requieren cambiar el modelo ahora.

## 3. Cómo lo resuelve el mercado

| Sistema | Modelo |
|---|---|
| **Shopify** | Producto + hasta 3 *options* (Size, Color, Material) → cada combinación es una *variant* con SKU, EAN, precio y stock propios. Taxonomía estándar por categoría que sugiere atributos |
| **Odoo** | Plantilla de producto + líneas de atributos → variantes generadas automáticamente, con extra de precio por valor de atributo |
| **Lightspeed / Vend** | *Matrix items*: grilla estilo/talle/color — el estándar del POS de indumentaria |
| **Square** | *Variations* (retail) + *modifiers* (gastronomía: adicionales sobre la línea, no stock) |
| **Tango Gestión (AR)** | "Artículos con escalas": escala 1 = talle, escala 2 = color |
| **Dragonfish/Zoo Logic (AR)** | Vertical de indumentaria construido enteramente sobre talles y colores |

Patrón común: **dos niveles** (artículo "padre"/modelo + variantes por combinación
de hasta ~3 atributos), donde el stock y el código de barras viven en la variante.
La gastronomía usa otro mecanismo (modificadores por línea de venta) — eso es del
POS resto, post-MVP, y no toca el maestro.

## 4. Propuesta de diseño para ZGC

### 4.1 Switch de rubro por tenant

`tenants.rubro`: `general` (default) · `supermercado` · `indumentaria_calzado` ·
`electronica` · `ferreteria_repuestos` · `distribuidora` · (`restaurante` post-MVP).

El rubro **no cambia el modelo de datos** — cambia presets y UI:
- qué secciones/flags muestra el form de artículo (pesable/envase solo en
  supermercado; grilla talle×color prominente en indumentaria; `en_dolares`
  prominente en electrónica),
- qué atributos sugiere precargados (Indumentaria: Talle con curva AR + Color;
  Electrónica: Color + Capacidad; Alimentos/bebidas: Gusto + Tamaño),
- etiquetas/vocabulario y listados,
- **qué POS se le sirve a las cajas** (Fase 6+: mostrador general, súper con
  pesables, boutique con talles, resto con mesas/modificadores).

La gestión central (backoffice) es una sola y genérica para todos los rubros.

### 4.2 Variantes de artículos (núcleo del cambio, Fase 2.5)

- `atributos` (por tenant): nombre (Talle, Color, Gusto, Capacidad, Tono...),
  orden. `atributo_valores`: valores ordenados (S, M, L, XL / Rojo, Azul / ...).
- `articulo_variantes`: artículo_id + combinación de hasta 3 valores de atributo,
  con **código de barras propio** (unique por tenant), sufijo de SKU, diferencial
  de precio opcional (± sobre las 4 listas del padre) y flag activo.
- Un artículo **sin** variantes sigue funcionando exactamente como hoy (el 100%
  de lo ya migrado no se toca). Con variantes, el padre define precios/IVA/familia
  y las variantes definen identidad de venta y stock.
- `articulo_stock` y `stock_movimientos` ganan `variante_id` **nullable**
  (null = artículo sin variantes). El kardex y las transferencias no cambian de
  lógica, solo de granularidad.
- UI: grilla matriz (talle × color) para carga y consulta rápida de stock; alta
  masiva de combinaciones; búsqueda/scan resuelve por EAN de variante.
- Ventas (Fase 3): las líneas de comprobante referencian `articulo_id` +
  `variante_id` nullable — **por esto la Fase 2.5 va antes que Ventas**.

### 4.3 Explícitamente diferido (sin cerrar puertas)

| Capacidad | Rubro que la pide | Nota de diseño |
|---|---|---|
| N° de serie / IMEI + garantías | Electrónica, electrodomésticos | Tabla satélite por unidad vendida; no toca el modelo de variantes |
| Lote y vencimiento | Alimentos, belleza, farmacia | Capa sobre `articulo_stock` (post-MVP) |
| Modificadores / recetas / combos | Restaurante | Mecanismo del POS resto, no del maestro |
| Curva de talles sugerida por compra | Indumentaria mayorista | Sobre órdenes de compra (Fase 4+) |
| Equivalencias de repuestos | Repuestos | Tabla de códigos alternativos por artículo |

## 5. Impacto en el roadmap

- **Fase 2.5 (nueva, antes de Ventas)**: migración 004 (rubro + atributos +
  variantes + variante_id en stock), API, grilla talle×color en el frontend,
  presets por rubro en el form de artículos.
- **Fase 3 (Ventas)**: líneas de comprobante con `variante_id` desde el día 1.
- **Fase 6 (POS)**: el rubro del tenant decide qué POS se sirve.
- Los 12.208 artículos migrados de "Super (prueba)" siguen válidos sin variantes.
