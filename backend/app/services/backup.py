"""Backup completo por tenant (F18 — DISENO-BACKUP-OBSERVABILIDAD.md §2).

Dump crudo dirigido por metadata: entra TODA tabla del modelo con columna
`tenant_id` (una tabla de una fase futura entra sola, sin checklist), menos
las exclusiones explícitas de abajo. Un CSV por tabla con la convención de la
suite (`;`, BOM UTF-8, CRLF — Excel es-AR directo) + manifest + LEEME, todo en
un ZIP en memoria (patrón export-contador de F9-bis).

La legibilidad NO es objetivo de este dump (los exports curados por módulo ya
existen): acá la promesa es completitud — "descargá TODO lo tuyo".
"""

import io
import json
import zipfile
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csv_export import csv_texto
from app.models import Base

# Tablas del tenant que NO salen en el backup — cada una con su porqué.
# Solo entran acá tablas CON tenant_id (las globales quedan afuera solas);
# la suite verifica: toda tabla con tenant_id está en el ZIP o en esta lista.
TABLAS_EXCLUIDAS: dict[str, str] = {
    "arca_tokens": "tokens de autenticación WSAA vivos — secreto y regenerable",
    "password_resets": "hashes de tokens de reset de contraseña — secreto sin valor para el dueño",
    "padron_cache": "caché de datos de AFIP — se regenera, no es dato del tenant",
}

# Columnas que se OMITEN de su tabla (la tabla sale, el secreto no).
COLUMNAS_EXCLUIDAS: set[tuple[str, str]] = {
    ("usuarios", "password_hash"),
    ("arca_config", "cert_pem"),
    ("arca_config", "key_pem"),
    ("sucursal_nodos", "token_hash"),
}

# Tope de seguridad por tabla (memoria de la lambda). Si se toca, el manifest
# lo marca `truncado=Sí` — nunca se recorta en silencio.
TOPE_FILAS = 200_000

LEEME = """BACKUP COMPLETO — ZARIS ERP (ZGC)
=================================

Este ZIP contiene TODOS los datos de su empresa: un archivo CSV por tabla del
sistema (el nombre del archivo es el nombre de la tabla) más este LEEME y un
manifest.csv con el conteo de filas exportadas por tabla.

Formato de los CSV
------------------
- Separador `;`, codificación UTF-8 con BOM — se abren directo en Excel.
- Es un volcado crudo, pensado para garantizar que sus datos son suyos:
  fechas en formato ISO (AAAA-MM-DD), importes con punto decimal e
  identificadores internos (UUID) en texto. Para listados con formato
  (importes con coma, columnas con nombres) use los exports de cada pantalla
  de la aplicación (Ventas, Compras, Libros de IVA, Contabilidad, etc.).

Qué NO incluye (por seguridad)
------------------------------
- Contraseñas de usuarios (se guardan cifradas y no salen del sistema).
- Certificado y clave privada de ARCA/AFIP.
- Tokens internos de autenticación y sincronización.
"""


def _valor(v: object) -> str:
    """Serialización cruda máquina-legible (el escape CSV lo hace csv_texto)."""
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


def tablas_del_backup() -> list:
    """Tablas del metadata que entran al ZIP (orden alfabético, determinista)."""
    return [
        t
        for t in sorted(Base.metadata.tables.values(), key=lambda t: t.name)
        if "tenant_id" in t.columns and t.name not in TABLAS_EXCLUIDAS
    ]


async def generar_backup(db: AsyncSession, tenant_id) -> tuple[bytes, int, int]:
    """Arma el ZIP completo. Devuelve (contenido, tablas, filas_total)."""
    manifest: list[list] = []
    filas_total = 0

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("LEEME.txt", LEEME)

        # La fila propia de `tenants` (razón social, CUIT, rubro, plan) es dato
        # del cliente aunque la tabla no tenga tenant_id: caso especial.
        tenants = Base.metadata.tables["tenants"]
        propios = [tenants] + tablas_del_backup()
        for tabla in propios:
            columnas = [
                c for c in tabla.columns if (tabla.name, c.name) not in COLUMNAS_EXCLUIDAS
            ]
            filtro = (
                tabla.c.id == tenant_id
                if tabla.name == "tenants"
                else tabla.c.tenant_id == tenant_id
            )
            filas_db = (
                await db.execute(
                    select(*columnas)
                    .where(filtro)
                    .order_by(*tabla.primary_key.columns)
                    .limit(TOPE_FILAS + 1)
                )
            ).all()
            truncado = len(filas_db) > TOPE_FILAS
            filas_db = filas_db[:TOPE_FILAS]
            zf.writestr(
                f"{tabla.name}.csv",
                csv_texto(
                    [c.name for c in columnas],
                    [[_valor(v) for v in fila] for fila in filas_db],
                ),
            )
            manifest.append([tabla.name, len(filas_db), "Sí" if truncado else "No"])
            filas_total += len(filas_db)

        fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        manifest_csv = csv_texto(
            [f"Backup generado {fecha}", "Filas exportadas", "Truncado"], manifest
        )
        zf.writestr("manifest.csv", manifest_csv)

    return buffer.getvalue(), len(manifest), filas_total
