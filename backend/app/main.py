from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.articulos import router as articulos_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalogos_articulos import router as catalogos_articulos_router
from app.api.v1.clientes import router as clientes_router
from app.api.v1.empresa import router as empresa_router
from app.api.v1.entidades import router as entidades_router
from app.api.v1.stock import router as stock_router
from app.api.v1.variantes import router as variantes_router
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "app": "zgc-backend", "env": settings.ENV}
