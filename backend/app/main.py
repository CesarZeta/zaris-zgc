from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.api.v1.pagos import router as pagos_router
from app.api.v1.padron import router as padron_router
from app.api.v1.pos import router as pos_router
from app.api.v1.pos_resto import router as pos_resto_router
from app.api.v1.proveedores import router as proveedores_router
from app.api.v1.stock import router as stock_router
from app.api.v1.sucursales import router as sucursales_router
from app.api.v1.tesoreria import router as tesoreria_router
from app.api.v1.usuarios import router as usuarios_router
from app.api.v1.variantes import router as variantes_router
from app.api.v1.vendedores import router as vendedores_router
from app.api.v1.ventas_config import router as ventas_config_router
from app.core.config import settings

app = FastAPI(
    title="ZGC — ZARIS Gestión Comercial",
    version="0.1.0",
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(entidades_router, prefix="/api/v1")
app.include_router(clientes_router, prefix="/api/v1")
app.include_router(catalogos_articulos_router, prefix="/api/v1")
app.include_router(articulos_router, prefix="/api/v1")
app.include_router(variantes_router, prefix="/api/v1")
app.include_router(stock_router, prefix="/api/v1")
app.include_router(empresa_router, prefix="/api/v1")
app.include_router(ventas_config_router, prefix="/api/v1")
app.include_router(comprobantes_router, prefix="/api/v1")
app.include_router(cobranzas_router, prefix="/api/v1")
app.include_router(proveedores_router, prefix="/api/v1")
app.include_router(compras_router, prefix="/api/v1")
app.include_router(pagos_router, prefix="/api/v1")
app.include_router(caja_router, prefix="/api/v1")
app.include_router(libros_router, prefix="/api/v1")
app.include_router(pos_router, prefix="/api/v1")
app.include_router(pos_resto_router, prefix="/api/v1")
app.include_router(usuarios_router, prefix="/api/v1")
app.include_router(sucursales_router, prefix="/api/v1")
app.include_router(geo_router, prefix="/api/v1")
app.include_router(padron_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(cheques_router, prefix="/api/v1")
app.include_router(bancos_router, prefix="/api/v1")
app.include_router(tesoreria_router, prefix="/api/v1")
app.include_router(contabilidad_router, prefix="/api/v1")
app.include_router(vendedores_router, prefix="/api/v1")

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
    return {"status": "ok", "app": "zgc-backend", "env": settings.ENV}
