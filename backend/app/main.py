from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="ZGC — ZARIS Gestión Comercial",
    version="0.1.0",
)

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
