import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.articulos import router as articulos_router
from app.api.v1.auth import router as auth_router
from app.api.v1.bancos import router as bancos_router
from app.api.v1.caja import router as caja_router
from app.api.v1.catalogos_articulos import router as catalogos_articulos_router
from app.api.v1.cheques import router as cheques_router
from app.api.v1.clientes import router as clientes_router
from app.api.v1.cobranzas import router as cobranzas_router
from app.api.v1.compras import router as compras_router
from app.api.v1.comprobantes import router as comprobantes_router
from app.api.v1.contabilidad import router as contabilidad_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.empresa import router as empresa_router
from app.api.v1.entidades import router as entidades_router
from app.api.v1.geo import router as geo_router
from app.api.v1.libros import router as libros_router
from app.api.v1.logistica import router as logistica_router
from app.api.v1.nodo_local import router as nodo_local_router
from app.api.v1.nodos import router as nodos_router
from app.api.v1.pagos import router as pagos_router
from app.api.v1.padron import router as padron_router
from app.api.v1.pos import router as pos_router
from app.api.v1.pos_auth import router as pos_auth_router
from app.api.v1.pos_resto import router as pos_resto_router
from app.api.v1.proveedores import router as proveedores_router
from app.api.v1.stock import router as stock_router
from app.api.v1.sucursales import router as sucursales_router
from app.api.v1.sync import router as sync_router
from app.api.v1.tesoreria import router as tesoreria_router
from app.api.v1.usuarios import router as usuarios_router
from app.api.v1.variantes import router as variantes_router
from app.api.v1.vendedores import router as vendedores_router
from app.api.v1.ventas_config import router as ventas_config_router
from app.core.config import settings
from app.services.sync_nodo import loop_sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    tarea_sync = None
    if settings.es_nodo:
        # réplica de bajada nube → nodo (primer ciclo inmediato, luego polling)
        tarea_sync = asyncio.create_task(loop_sync())
    yield
    if tarea_sync is not None:
        tarea_sync.cancel()


app = FastAPI(
    title="ZGC — ZARIS Gestión Comercial",
    version="0.1.0",
    lifespan=lifespan,
)

# Superficie común a ambos perfiles: lo que necesitan el POS y la facturación
# de gestión del nodo (DISENO-NODO-LAN.md §4, ajustado por §0-bis). En el nodo
# los maestros son réplica de solo lectura (middleware más abajo).
ROUTERS_COMUNES = [
    auth_router,
    entidades_router,
    clientes_router,
    catalogos_articulos_router,
    articulos_router,
    variantes_router,
    stock_router,
    empresa_router,
    ventas_config_router,
    comprobantes_router,
    cobranzas_router,
    pos_router,
    pos_auth_router,
    pos_resto_router,
    sucursales_router,
    geo_router,
    vendedores_router,
]

# Gestión completa + administración: SOLO nube (la gestión local completa en
# el nodo es el extra de N3). `sync`/`nodos` son la contraparte nube del nodo.
ROUTERS_NUBE = [
    proveedores_router,
    compras_router,
    pagos_router,
    caja_router,
    libros_router,
    logistica_router,
    usuarios_router,
    padron_router,
    dashboard_router,
    cheques_router,
    bancos_router,
    tesoreria_router,
    contabilidad_router,
    nodos_router,
    sync_router,
]

for r in ROUTERS_COMUNES:
    app.include_router(r, prefix="/api/v1")
if settings.es_nodo:
    app.include_router(nodo_local_router, prefix="/api/v1")
else:
    for r in ROUTERS_NUBE:
        app.include_router(r, prefix="/api/v1")

if settings.es_nodo:
    # "Los maestros no se editan en el nodo" (§5): réplica de solo lectura.
    # Escriben únicamente las transacciones locales (POS, facturación de
    # gestión, cobranzas, ajustes de stock) y la autenticación.
    ESCRITURA_NODO = (
        "/api/v1/auth",
        "/api/v1/pos",  # cubre /pos, /pos/auth y /pos/resto
        "/api/v1/ventas/comprobantes",
        "/api/v1/cobranzas",
        "/api/v1/stock",
        "/api/v1/nodo",
    )

    @app.middleware("http")
    async def solo_lectura_maestros(request: Request, call_next):
        if (
            request.method in ("GET", "HEAD", "OPTIONS")
            or not request.url.path.startswith("/api/")
            or request.url.path.startswith(ESCRITURA_NODO)
        ):
            return await call_next(request)
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Maestro de solo lectura en el nodo — editálo en la "
                "gestión de la nube (se replica solo)"
            },
        )


# CORS se agrega ÚLTIMO = middleware más EXTERNO: hasta los 403 del middleware
# de solo-lectura del nodo salen con headers CORS (cajas en dev cross-origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Sin esto el browser NO puede leer X-Total-Count cross-origin (Pages →
    # Vercel); el proxy de Vite en dev lo enmascara (regla §6 del CLAUDE.md).
    expose_headers=["X-Total-Count"],
)


@app.get("/health")
def health():
    return {"status": "ok", "app": "zgc-backend", "env": settings.ENV, "perfil": settings.PERFIL}


if settings.es_nodo and settings.NODO_WEB_DIR:
    from fastapi.staticfiles import StaticFiles

    class SPAStaticFiles(StaticFiles):
        """Fallback a index.html para las rutas del router de React
        (/pos/login, /pos, …): el nodo sirve el MISMO build del POS web."""

        async def get_response(self, path: str, scope):
            respuesta = await super().get_response(path, scope)
            if respuesta.status_code == 404:
                respuesta = await super().get_response("index.html", scope)
            return respuesta

    app.mount("/", SPAStaticFiles(directory=settings.NODO_WEB_DIR, html=True), name="pos-web")
