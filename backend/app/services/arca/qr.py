"""QR de comprobantes electrónicos — RG 4892/2020 (FACTURACION-ARCA.md §7).

Payload versión 1: JSON → Base64 → URL oficial. Solo se genera para
comprobantes con CAE real (modo simulado NUNCA lleva QR)."""

import base64
import io
import json
from datetime import date
from decimal import Decimal

import segno

URL_QR = "https://www.afip.gob.ar/fe/qr/?p="


def url_qr(
    fecha: date,
    cuit_emisor: str,
    punto_venta: int,
    tipo_arca: int,
    numero: int,
    importe: Decimal,
    moneda: str,
    cotizacion: Decimal,
    doc_tipo: int,
    doc_nro: str | None,
    cae: str,
) -> str:
    payload = {
        "ver": 1,
        "fecha": fecha.isoformat(),
        "cuit": int(cuit_emisor),
        "ptoVta": punto_venta,
        "tipoCmp": tipo_arca,
        "nroCmp": numero,
        "importe": float(importe),
        "moneda": moneda,
        "ctz": float(cotizacion),
        "tipoDocRec": doc_tipo,
        "nroDocRec": int(doc_nro or 0),
        "tipoCodAut": "E",
        "codAut": int(cae),
    }
    b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    return URL_QR + b64


def svg_qr(url: str) -> str:
    """SVG listo para incrustar en la impresión (sin descargas externas)."""
    buffer = io.BytesIO()
    segno.make(url, error="m").save(buffer, kind="svg", scale=3, border=2)
    return buffer.getvalue().decode()
