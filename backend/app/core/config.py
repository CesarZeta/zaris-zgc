import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "dev"
    DATABASE_URL: str = ""
    JWT_SECRET: str = ""
    JWT_EXPIRES_HOURS: int = 24
    CORS_ORIGINS: str = "http://localhost:5173"

    # Perfil de ejecución (F13-LAN, DISENO-NODO-LAN.md §1): "nube" = backend
    # central (Vercel/dev de siempre); "nodo" = PC de sucursal en la LAN —
    # mismo código, montaje de routers acotado + réplica de bajada + POS web
    # servido como estáticos. El perfil cambia config, NUNCA bifurca código.
    PERFIL: str = "nube"
    NUBE_URL: str = ""  # URL del backend central (https://... o http://host:puerto)
    NODO_ID: str = ""  # uuid de sucursal_nodos (lo da el alta en Configuración)
    NODO_TOKEN: str = ""  # token de aparejamiento (se muestra UNA vez al crear)
    SYNC_INTERVALO_SEG: int = 60
    NODO_WEB_DIR: str = ""  # build de React a servir en / (vacío = solo API)
    # Hook EXCLUSIVO de la suite del nodo (test_nodo_dev.py): simula ARCA
    # caída para probar el CAE diferido sin tocar la red. Jamás en prod.
    ARCA_SIMULAR_CAIDA: bool = False

    @property
    def es_nodo(self) -> bool:
        return self.PERFIL == "nodo"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
