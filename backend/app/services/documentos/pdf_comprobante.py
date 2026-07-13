"""PDF A4 del comprobante de venta (F16 — DISENO-SALIDA-DOCUMENTOS.md §2).

Layout espejo del HTML imprimible (web-app/src/modules/ventas/impresion.ts):
RG 1415 + QR RG 4892 + transparencia fiscal Ley 27.743. Consume el MISMO
payload que arma `_payload_impresion` en api/v1/comprobantes.py — una sola
fuente de verdad del contenido; acá solo se maqueta.

fpdf2 puro Python (apto Vercel serverless). Fuentes core del estándar PDF
(Helvetica/Courier): texto latin-1 best-effort — los datos argentinos reales
lo son; lo que no mapea se reemplaza, no revienta.
"""

import io
from decimal import Decimal

import segno
from fpdf import FPDF

ANCHO = 186  # área útil A4 con margen 12
X0 = 12


# tipografía Unicode frecuente → equivalente latin-1 (lo demás cae a "?")
_TRANSLIT = str.maketrans({"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
                           "…": "...", "•": "·", "€": "EUR", " ": " "})


def _t(s: object) -> str:
    """Texto seguro para fuentes core (latin-1 best-effort)."""
    texto = str(s if s is not None else "").translate(_TRANSLIT)
    return texto.encode("latin-1", "replace").decode("latin-1")


def _num(v: object) -> str:
    """1234567.8 → '1.234.567,80' (es-AR)."""
    d = Decimal(str(v or 0))
    entero, sep, dec = f"{d:,.2f}".partition(".")
    return entero.replace(",", ".") + "," + dec


def _qr_png(url: str) -> bytes:
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=6, border=2)
    return buf.getvalue()


def pdf_comprobante(payload: dict, qr_url: str | None = None) -> bytes:
    c = payload["comprobante"]
    emisor = payload["emisor"]
    discrimina = payload["discrimina_iva"]

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=X0, top=12, right=X0)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # ---- Cabecera: dos columnas + caja de letra al centro ----
    y0 = 12
    alto_cab = 34
    pdf.set_draw_color(17, 17, 17)
    pdf.rect(X0, y0, ANCHO, alto_cab)

    # columna emisor (izquierda)
    pdf.set_xy(X0 + 3, y0 + 4)
    pdf.set_font("helvetica", "B", 13)
    pdf.cell(85, 6, _t(emisor["razon_social"]), new_x="LEFT", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    if emisor.get("nombre_fantasia"):
        pdf.cell(85, 4.5, _t(emisor["nombre_fantasia"]), new_x="LEFT", new_y="NEXT")
    pdf.cell(85, 4.5, _t(emisor.get("domicilio")), new_x="LEFT", new_y="NEXT")
    pdf.cell(85, 4.5, _t(emisor.get("condicion_iva")), new_x="LEFT", new_y="NEXT")

    # columna documento (derecha, alineada R)
    pdf.set_xy(X0 + 100, y0 + 4)
    pdf.set_font("helvetica", "B", 13)
    pdf.cell(83, 6, _t(c["tipo_descripcion"]).upper(), align="R", new_x="LEFT", new_y="NEXT")
    pdf.set_x(X0 + 100)
    pdf.set_font("courier", "B", 10)
    pdf.cell(83, 5, _t(f"N° {c.get('numero_formateado') or ''}"), align="R", new_x="LEFT", new_y="NEXT")
    pdf.set_font("helvetica", "", 9)
    pdf.set_x(X0 + 100)
    pdf.cell(83, 4.5, _t(f"Fecha: {c['fecha']}"), align="R", new_x="LEFT", new_y="NEXT")
    if emisor.get("cuit"):
        pdf.set_x(X0 + 100)
        pdf.cell(83, 4.5, _t(f"CUIT: {emisor['cuit']}"), align="R", new_x="LEFT", new_y="NEXT")
    if emisor.get("iibb"):
        pdf.set_x(X0 + 100)
        pdf.cell(83, 4.5, _t(f"IIBB: {emisor['iibb']}"), align="R", new_x="LEFT", new_y="NEXT")
    if emisor.get("inicio_actividades"):
        pdf.set_x(X0 + 100)
        pdf.cell(83, 4.5, _t(f"Inicio de actividades: {emisor['inicio_actividades']}"),
                 align="R", new_x="LEFT", new_y="NEXT")

    # caja de letra (pisa el borde superior, como el HTML)
    pdf.rect(X0 + ANCHO / 2 - 7.5, y0, 15, 15)
    pdf.set_xy(X0 + ANCHO / 2 - 7.5, y0 + 2)
    pdf.set_font("helvetica", "B", 20)
    pdf.cell(15, 8, _t(c["letra"]), align="C", new_x="LEFT", new_y="NEXT")
    if payload.get("codigo_arca"):
        pdf.set_x(X0 + ANCHO / 2 - 7.5)
        pdf.set_font("helvetica", "B", 6)
        pdf.cell(15, 3, _t(f"COD. {int(payload['codigo_arca']):02d}"), align="C")

    # ---- Receptor ----
    receptor = f"{c['receptor_nombre']} — {payload['receptor_condicion_iva_desc']}"
    if c.get("receptor_doc_nro"):
        receptor += f" · Doc: {c['receptor_doc_nro']}"
    if c.get("condicion_venta_desc"):
        receptor += f" · {c['condicion_venta_desc']}"
    elif c.get("contado"):
        receptor += " · Contado"
    pdf.set_xy(X0, y0 + alto_cab)
    pdf.set_font("helvetica", "", 9.5)
    pdf.multi_cell(ANCHO, 6.5, _t(receptor), border=1)
    pdf.ln(2)

    # ---- Renglones ----
    pdf.set_font("helvetica", "", 8.5)
    encabezado = ["Código", "Descripción", "Cant.", "P. unit.", "Bonif."]
    anchos = [22, 78, 14, 22, 14]
    alineado = ["LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"]
    if discrimina:
        encabezado += ["IVA", "Importe"]
        anchos += [12, 24]
        alineado += ["RIGHT", "RIGHT"]
    else:
        encabezado += ["Importe"]
        anchos += [36]
        alineado += ["RIGHT"]

    with pdf.table(
        col_widths=tuple(anchos),
        text_align=tuple(alineado),
        borders_layout="SINGLE_TOP_LINE",
        line_height=4.6,
        padding=0.8,
    ) as table:
        fila = table.row()
        for titulo in encabezado:
            fila.cell(titulo)
        for i in items_de(c):
            fila = table.row()
            fila.cell(_t(i.get("codigo") or "-"))
            fila.cell(_t(i["descripcion"]))
            fila.cell(_num(i["cantidad"]))
            fila.cell(_num(i["precio_unitario"]))
            fila.cell(f"{_num(i['bonif_pct'])}%" if Decimal(str(i["bonif_pct"] or 0)) > 0 else "-")
            if discrimina:
                fila.cell(f"{_t(i['tasa_iva'])}%")
                fila.cell(_num(i["importe_neto"]))
            else:
                fila.cell(_num(i["importe_total"]))

    # ---- Totales (bloque derecho) ----
    pdf.ln(3)
    x_tot = X0 + ANCHO - 72
    pdf.set_font("helvetica", "", 9.5)
    if discrimina:
        _linea_total(pdf, x_tot, "Neto gravado", _num(c["neto_gravado"]))
        for a in c.get("alicuotas") or []:
            _linea_total(pdf, x_tot, f"IVA {_t(a['tasa'])}% (base {_num(a['base'])})", _num(a["importe"]))
    pdf.set_font("helvetica", "B", 12)
    _linea_total(pdf, x_tot, "TOTAL $", _num(c["total"]), tope=True)

    # ---- Transparencia fiscal (Ley 27.743) ----
    tf = payload.get("transparencia_fiscal")
    if tf:
        pdf.ln(3)
        pdf.set_font("helvetica", "", 8.5)
        pdf.multi_cell(
            ANCHO, 4.5,
            _t(
                f"{tf['titulo']}\nIVA Contenido: $ {_num(tf['iva_contenido'])} · "
                f"Otros Impuestos Nacionales Indirectos: "
                f"$ {_num(tf['otros_impuestos_nacionales_indirectos'])}"
            ),
            border=1,
        )

    # ---- Vencimientos / observaciones ----
    vtos = c.get("vencimientos") or []
    if vtos:
        pdf.ln(2)
        pdf.set_font("helvetica", "", 8.5)
        texto = "Vencimientos: " + " · ".join(
            f"cuota {v['nro_cuota']}: {v['fecha_vto']} $ {_num(v['importe'])}" for v in vtos
        )
        pdf.multi_cell(ANCHO, 4.5, _t(texto))
    if c.get("observaciones"):
        pdf.ln(2)
        pdf.set_font("helvetica", "", 8.5)
        pdf.multi_cell(ANCHO, 4.5, _t(c["observaciones"]))

    # ---- Leyendas (NO VÁLIDO / PRUEBA / PENDIENTE DE CAE) ----
    for leyenda in payload.get("leyendas") or []:
        pdf.ln(2)
        pdf.set_font("helvetica", "B", 10)
        pdf.multi_cell(ANCHO, 7, _t(leyenda), border=1, align="C")

    # ---- Pie: CAE + QR ----
    if c.get("cae") or qr_url:
        alto_pie = 30 if qr_url else 12
        if pdf.get_y() + alto_pie > 283:
            pdf.add_page()
        pdf.ln(4)
        y_pie = pdf.get_y()
        if c.get("cae"):
            pdf.set_xy(X0, y_pie + 2)
            pdf.set_font("courier", "B", 9.5)
            pdf.cell(120, 5, _t(f"CAE: {c['cae']}"), new_x="LEFT", new_y="NEXT")
            pdf.set_x(X0)
            pdf.cell(120, 5, _t(f"Vto. CAE: {c.get('cae_vencimiento') or ''}"))
        if qr_url:
            pdf.image(io.BytesIO(_qr_png(qr_url)), x=X0 + ANCHO - 28, y=y_pie, w=28)

    return bytes(pdf.output())


def items_de(c: dict) -> list[dict]:
    return c.get("items") or []


def _linea_total(pdf: FPDF, x: float, etiqueta: str, valor: str, tope: bool = False) -> None:
    pdf.set_x(x)
    if tope:
        pdf.line(x, pdf.get_y(), x + 72, pdf.get_y())
    pdf.cell(44, 6, _t(etiqueta))
    pdf.set_font("courier", pdf.font_style, pdf.font_size_pt)
    pdf.cell(28, 6, valor, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", pdf.font_style, pdf.font_size_pt)
