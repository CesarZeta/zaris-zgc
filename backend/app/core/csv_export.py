"""Export CSV para Excel es-AR — helper compartido (Fase 7).

Convención heredada de los libros de IVA (Fase 5): separador `;`, decimales con
coma, BOM UTF-8 + CRLF (así Excel es-AR lo abre directo, sin asistente de
importación). Extraído a core para el "export universal" de reportería.

A diferencia del helper original de libros.py, este ESCAPA los campos (comillas
dobles si el valor trae `;`, comillas o saltos de línea) — necesario cuando las
celdas son texto libre (razón social, domicilio) y no solo números.
"""

from decimal import Decimal

from fastapi import Response

BOM = "﻿"


def num(valor: Decimal | float | int | None) -> str:
    """Número -> "1234,56" (coma decimal). None -> "" (celda vacía)."""
    if valor is None:
        return ""
    return f"{Decimal(valor):.2f}".replace(".", ",")


def _celda(valor: object) -> str:
    s = "" if valor is None else str(valor)
    if any(c in s for c in (";", '"', "\n", "\r")):
        return '"' + s.replace('"', '""') + '"'
    return s


def csv_texto(encabezado: list[str], filas: list[list]) -> str:
    """El contenido CSV como texto (BOM + CRLF) — para empaquetar en ZIP."""
    lineas = [";".join(_celda(c) for c in encabezado)]
    lineas += [";".join(_celda(c) for c in fila) for fila in filas]
    return BOM + "\r\n".join(lineas) + "\r\n"


def csv_response(nombre: str, encabezado: list[str], filas: list[list]) -> Response:
    return Response(
        content=csv_texto(encabezado, filas).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
