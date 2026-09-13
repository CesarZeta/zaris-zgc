"""Fecha y hora de NEGOCIO del sistema (fix 2026-09-13 — bloqueante de la
auditoría de pendientes).

Todos los tenants son argentinos y la nube (Vercel + Supabase) corre en UTC:
`date.today()` devolvía la fecha UTC, así que después de las 21:00 hora
argentina un ticket POS, recibo, OP, movimiento o cierre de caja se fechaba
MAÑANA (CbteFch a ARCA, libro IVA y planilla del día equivocados; a fin de mes
caía en el período de IVA siguiente). El nodo LAN, con Postgres y Python en
hora local, fechaba distinto que la nube para el mismo hecho.

Regla permanente (CLAUDE.md §6): en `backend/app` NUNCA se fecha un hecho de
negocio con `date.today()`, `datetime.now()` a secas ni `.date()` de un
timestamp — siempre `hoy()`, `ahora()` o `a_fecha_local()`. Los timestamps de
auditoría (`created_at`, `anulado_at`, …) siguen siendo UTC aware
(`datetime.now(timezone.utc)`): son instantes, no fechas de negocio.
`tools/test_fechas_dev.py` guarda la regla con un grep sobre el repo.

La zona es ÚNICA por instalación (`TZ_APP`, default Argentina): parametrizable
por env, nunca por tenant — no bifurca el modelo. En Windows (nodo LAN, dev)
la base IANA la aporta el paquete `tzdata` (está en ambos requirements).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings

ZONA = ZoneInfo(settings.TZ_APP)


def ahora() -> datetime:
    """Instante actual, aware, en la zona de negocio."""
    return datetime.now(ZONA)


def hoy() -> date:
    """Fecha de negocio de HOY (zona AR), independiente del reloj del server.
    Sirve también como `default=hoy` en columnas `Date` del ORM."""
    return ahora().date()


def a_fecha_local(ts: datetime | None) -> date | None:
    """Fecha de negocio de un timestamp. Un datetime naive se asume UTC (así
    devuelve asyncpg los `timestamptz` y así sella el ORM con
    `datetime.now(timezone.utc)`)."""
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ZONA).date()
