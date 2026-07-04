from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.clientes import router as clientes_router
from app.api.v1.entidades import router as entidades_router
from app.core.config import settings

app = FastAPI(
    title="ZGC — ZARIS Gestión Comercial",
    version="0.1.0",
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(entidades_router, prefix="/api/v1")
app.include_router(clientes_router, prefix="/api/v1")

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
