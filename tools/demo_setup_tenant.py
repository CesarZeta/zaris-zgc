r"""
Setup del tenant DEMO de ZGC (paso 1 de la carga de datos demo).

Crea, de forma idempotente, todo lo que un tenant necesita ANTES de poder
facturar (ver informe de prerequisitos): tenant + sucursal + usuario demo +
arca_config en modo simulado + punto de venta + depósito. NO carga maestros ni
comprobantes (eso lo hacen los migradores y demo_generar_operaciones.py).

Uso (convención del proyecto):
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\demo_setup_tenant.py --clave "DemosAFu4MB1!"

Imprime el tenant_id (que necesitan los migradores con --tenant-id) y las
credenciales del usuario demo. Re-ejecutarlo no duplica nada.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# permitir importar app.* corriendo desde tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.auth import hash_password  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    ArcaConfig,
    Deposito,
    PuntoVenta,
    Sucursal,
    Tenant,
    Usuario,
)

EMAIL_DEMO = "demo@zaris.com.ar"
RAZON_DEMO = "ZARIS Demo (comercio de muestra)"
CUIT_DEMO = "30712345670"  # CUIT válido de muestra (DV correcto), solo dígitos


async def main(clave: str) -> None:
    async with SessionLocal() as db:
        # --- Tenant (idempotente por razón social) ---
        tenant = await db.scalar(select(Tenant).where(Tenant.razon_social == RAZON_DEMO))
        if tenant is None:
            tenant = Tenant(
                razon_social=RAZON_DEMO,
                nombre_fantasia="ZARIS Demo",
                cuit=CUIT_DEMO,
                condicion_iva="RI",
                localidad="Rosario",
                provincia="Santa Fe",
                rubro="general",
            )
            db.add(tenant)
            await db.flush()
            print(f"[+] Tenant creado: {tenant.id}")
        else:
            print(f"[=] Tenant ya existe: {tenant.id}")

        # --- Sucursal ---
        sucursal = await db.scalar(
            select(Sucursal).where(
                Sucursal.tenant_id == tenant.id, Sucursal.nombre == "Casa Central"
            )
        )
        if sucursal is None:
            sucursal = Sucursal(tenant_id=tenant.id, nombre="Casa Central", localidad="Rosario")
            db.add(sucursal)
            await db.flush()
            print(f"[+] Sucursal creada: {sucursal.id}")
        else:
            print(f"[=] Sucursal ya existe: {sucursal.id}")

        # --- Usuario demo (email único global) ---
        usuario = await db.scalar(select(Usuario).where(Usuario.email == EMAIL_DEMO))
        if usuario is None:
            usuario = Usuario(
                tenant_id=tenant.id,
                email=EMAIL_DEMO,
                nombre="Usuario Demo",
                password_hash=hash_password(clave),
                nivel_acceso=1,
                sucursal_id=sucursal.id,
            )
            db.add(usuario)
            print(f"[+] Usuario creado: {EMAIL_DEMO}")
        else:
            # re-set de clave para que la conozcas siempre
            usuario.password_hash = hash_password(clave)
            usuario.activo = True
            print(f"[=] Usuario ya existe: {EMAIL_DEMO} (clave actualizada)")

        # --- ARCA config modo simulado (uno por tenant, unique) ---
        arca = await db.scalar(select(ArcaConfig).where(ArcaConfig.tenant_id == tenant.id))
        if arca is None:
            arca = ArcaConfig(
                tenant_id=tenant.id,
                modo="simulado",
                cuit=CUIT_DEMO,
                razon_social=RAZON_DEMO[:80],
            )
            db.add(arca)
            print("[+] ARCA config creada (modo simulado)")
        else:
            arca.modo = "simulado"
            print("[=] ARCA config ya existe (forzada a simulado)")

        # --- Punto de venta ---
        pv = await db.scalar(
            select(PuntoVenta).where(
                PuntoVenta.tenant_id == tenant.id, PuntoVenta.numero == 1
            )
        )
        if pv is None:
            pv = PuntoVenta(
                tenant_id=tenant.id,
                sucursal_id=sucursal.id,
                numero=1,
                descripcion="Casa Central",
                electronico=True,
            )
            db.add(pv)
            await db.flush()
            print(f"[+] Punto de venta creado: nro 1 ({pv.id})")
        else:
            print(f"[=] Punto de venta ya existe: nro 1 ({pv.id})")

        # --- Depósito (obligatorio para mover stock) ---
        deposito = await db.scalar(
            select(Deposito).where(Deposito.tenant_id == tenant.id, Deposito.codigo == "1")
        )
        if deposito is None:
            deposito = Deposito(
                tenant_id=tenant.id, codigo="1", nombre="Depósito Central", activo=True
            )
            db.add(deposito)
            await db.flush()
            print(f"[+] Depósito creado: cod 1 ({deposito.id})")
        else:
            print(f"[=] Depósito ya existe: cod 1 ({deposito.id})")

        await db.commit()

        print("\n=== SETUP DEMO LISTO ===")
        print(f"tenant_id     : {tenant.id}")
        print(f"punto_venta_id: {pv.id}")
        print(f"deposito_id   : {deposito.id}")
        print(f"login         : {EMAIL_DEMO} / {clave}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Setup del tenant DEMO de ZGC")
    ap.add_argument("--clave", required=True, help="Contraseña para el usuario demo")
    args = ap.parse_args()
    asyncio.run(main(args.clave))
