from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Serverless (Vercel/Lambda) usa el pooler TRANSACCIONAL de Supabase (:6543):
# sin pool propio (NullPool) y sin prepared statements (Supavisor en modo
# transacción). En VM/local (:5432) el pool clásico de SQLAlchemy.
if ":6543/" in settings.DATABASE_URL:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
else:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
