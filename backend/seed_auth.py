r"""
Seed de desarrollo: tenant demo + sucursal + usuario ADMIN.

Uso (convención ZGE):
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe seed_auth.py

Credenciales dev: admin@zgc.dev / 123456
"""

import asyncio

from sqlalchemy import select

from app.core.auth import hash_password
from app.core.db import SessionLocal
from app.models import Sucursal, Tenant, Usuario


async def main():
    async with SessionLocal() as db:
        existente = await db.scalar(select(Usuario).where(Usuario.email == "admin@zgc.dev"))
        if existente:
            print("Seed ya aplicado (admin@zgc.dev existe).")
            return

        tenant = Tenant(
            razon_social="Empresa Demo SRL",
            nombre_fantasia="Demo",
            cuit="30000000007",
            condicion_iva="RI",
            localidad="Buenos Aires",
            provincia="Buenos Aires",
        )
        db.add(tenant)
        await db.flush()

        sucursal = Sucursal(tenant_id=tenant.id, nombre="Casa Central")
        db.add(sucursal)
        await db.flush()

        admin = Usuario(
            tenant_id=tenant.id,
            email="admin@zgc.dev",
            nombre="Administrador",
            password_hash=hash_password("123456"),
            nivel_acceso=1,
            sucursal_id=sucursal.id,
        )
        db.add(admin)
        await db.commit()
        print(f"Seed OK — tenant {tenant.id}, sucursal {sucursal.id}, usuario admin@zgc.dev / 123456")


if __name__ == "__main__":
    asyncio.run(main())
