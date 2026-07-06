"""Proxy único a Nominatim (OSM) — estándar de suite portado de ZGE (Fase 7).

El frontend NUNCA llama a OSM directo: este proxy aplica la política de uso de
Nominatim (1 req/s, User-Agent identificable), filtra POIs para campos de
domicilio y devuelve un shape estable. Diseño y encuadramientos heredados en
docs/DISENO-LOGISTICA-Y-DOMICILIOS.md §1; adaptaciones ZGC (§1.2):

1. User-Agent propio de ZGC.
2. Viewbox opcional POR TENANT y SIN bounded=1 (sesga sin excluir el resto del
   país; ZGE lo encierra en su municipio, ZGC tiene tenants en todo el país).
3. Rate limit por-lambda: en Vercel el lock global no se garantiza entre
   invocaciones (riesgo aceptado: debounce 500 ms + mínimo 3 chars + limit 5
   mantienen el tráfico real muy abajo del límite). Si un tenant lo estresa,
   migrar a Photon es cambiar solo este archivo.
"""

import asyncio
import logging
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import requiere_alguno
from app.models import Tenant, Usuario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geo", tags=["geo"])

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
NOMINATIM_UA = "ZGC-API/1.0 (cesar@zaris.com.ar)"
NOMINATIM_TIMEOUT = 8.0
_NOMINATIM_LOCK = asyncio.Lock()
_NOMINATIM_LAST_CALL = 0.0
_NOMINATIM_MIN_INTERVAL = 1.05  # margen sobre el 1 req/s de la política de Nominatim

# Lección de QA de ZGE: NO usar layer=address (excluye calles sin altura exacta,
# que SÍ son direcciones válidas). Se pide de más y se filtra por class.
POI_CLASS_BLACKLIST = {
    "amenity", "shop", "office", "tourism", "leisure",
    "craft", "healthcare", "club", "emergency", "man_made",
}

# La guarda cubre a todos los consumidores del buscador de domicilios:
# forms de clientes/proveedores (BUE) y ABM de sucursales (configuración).
_guard = requiere_alguno(["clientes", "proveedores", "configuracion"], "ver")


async def _nominatim_get(path: str, params: dict) -> list | dict:
    """GET a Nominatim respetando el rate-limit dentro de esta instancia."""
    global _NOMINATIM_LAST_CALL
    async with _NOMINATIM_LOCK:
        delta = time.monotonic() - _NOMINATIM_LAST_CALL
        if delta < _NOMINATIM_MIN_INTERVAL:
            await asyncio.sleep(_NOMINATIM_MIN_INTERVAL - delta)
        try:
            async with httpx.AsyncClient(timeout=NOMINATIM_TIMEOUT) as client:
                r = await client.get(
                    f"{NOMINATIM_BASE}{path}",
                    params=params,
                    headers={"User-Agent": NOMINATIM_UA, "Accept-Language": "es"},
                )
        except httpx.HTTPError:
            _NOMINATIM_LAST_CALL = time.monotonic()
            raise HTTPException(status_code=502, detail="Servicio de geocoding no disponible")
        finally:
            _NOMINATIM_LAST_CALL = time.monotonic()
    if r.status_code != 200:
        logger.warning("Nominatim %s -> HTTP %s", path, r.status_code)
        raise HTTPException(status_code=502, detail="Servicio de geocoding no disponible")
    return r.json()


def _calle_de(a: dict) -> str | None:
    return a.get("road") or a.get("pedestrian") or a.get("footway") or a.get("cycleway") or a.get("path")


def _display_name_desde_address(a: dict) -> str | None:
    """Reconstruye "calle altura, localidad, provincia, CP, país" desde address,
    ocultando el nombre del comercio que Nominatim a veces antepone."""
    calle = _calle_de(a)
    if not calle:
        return None
    partes = [f"{calle} {a['house_number']}" if a.get("house_number") else calle]
    for k in ("city", "town", "village", "hamlet", "municipality", "suburb"):
        if a.get(k):
            partes.append(a[k])
            break
    if a.get("state"):
        partes.append(a["state"])
    if a.get("postcode"):
        partes.append(a["postcode"])
    if a.get("country"):
        partes.append(a["country"])
    return ", ".join(partes)


async def geocodificar_direccion(
    db: AsyncSession, tenant_id, q: str, limit: int = 5, solo_direcciones: bool = False
) -> list[dict]:
    # Lección ZGE: pedir de más upstream y filtrar después (hay búsquedas con
    # 15+ comercios antes de la primera calle).
    upstream_limit = 40 if solo_direcciones else limit
    params = {
        "q": q,
        "format": "json",
        "limit": str(upstream_limit),
        "countrycodes": "ar",
        "addressdetails": "1",
    }
    # Sesgo opcional por tenant: viewbox SIN bounded=1 (prioriza, no excluye).
    tenant = await db.get(Tenant, tenant_id)
    if tenant and tenant.geo_centro_lat is not None and tenant.geo_centro_lon is not None:
        lat, lon = float(tenant.geo_centro_lat), float(tenant.geo_centro_lon)
        delta = float(tenant.geo_delta_grados or 0.27)
        params["viewbox"] = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"

    data = await _nominatim_get("/search", params)
    if not isinstance(data, list):
        return []

    out: list[dict] = []
    for d in data:
        cls = d.get("class")
        a = d.get("address") or {}
        display_name = d.get("display_name") or ""
        if solo_direcciones:
            if cls in POI_CLASS_BLACKLIST:
                continue
            calle = _calle_de(a)
            primer = display_name.split(",")[0].strip() if display_name else ""
            # el nombre visible no arranca por la calle ni la altura → reescribir
            if calle and primer and primer not in {calle, a.get("house_number") or ""}:
                display_name = _display_name_desde_address(a) or display_name
        out.append(
            {
                "display_name": display_name,
                "lat": float(d["lat"]) if d.get("lat") else None,
                "lon": float(d["lon"]) if d.get("lon") else None,
                "type": d.get("type"),
                "class": cls,
                "address": a,
            }
        )
        if len(out) >= limit:
            break
    return out


@router.get("/buscar")
async def buscar_direccion(
    q: str = Query(..., min_length=3),
    limit: int = Query(5, ge=1, le=10),
    solo_direcciones: bool = Query(False),
    usuario: Usuario = Depends(_guard),
    db: AsyncSession = Depends(get_db),
):
    return await geocodificar_direccion(db, usuario.tenant_id, q.strip(), limit, solo_direcciones)


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    usuario: Usuario = Depends(_guard),
):
    data = await _nominatim_get(
        "/reverse", {"lat": str(lat), "lon": str(lon), "format": "json", "addressdetails": "1"}
    )
    if not isinstance(data, dict) or data.get("error"):
        raise HTTPException(status_code=404, detail="Sin resultados")
    return {
        "display_name": data.get("display_name"),
        "address": data.get("address") or {},
        "lat": float(data["lat"]) if data.get("lat") else lat,
        "lon": float(data["lon"]) if data.get("lon") else lon,
    }
