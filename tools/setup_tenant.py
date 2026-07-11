r"""
Setup de un tenant de ZGC (onboarding asistido, F12-a — generalización de
demo_setup_tenant.py, que queda para el tenant demo).

Crea, de forma idempotente, todo lo que un tenant necesita para operar y
facturar: tenant (con plan y rubro) + sucursal + usuario admin + roles base
RBAC + arca_config en modo simulado + punto de venta + depósito + caja POS.
Es la vía v1 para vender una licencia (no hay signup público ni billing):

    licencia POS-only (kiosco / carnicería / resto)  ->  --plan pos
    suite completa                                   ->  --plan suite (default)

Uso (convención del proyecto):
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\setup_tenant.py `
        --razon "Kiosco San Martín" --email "dueno@kiosco.com" --clave "..." `
        --plan pos --rubro general

El plan se puede cambiar después por SQL (`update tenants set plan=...`):
upgrade a suite = los módulos aparecen al re-loguear; los datos ya estaban.
Re-ejecutarlo no duplica nada (idempotente por razón social / email / números).
"""

import argparse
import asyncio
import sys
from pathlib import Path

# permitir importar app.* corriendo desde tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select  # noqa: E402

from app.api.v1.empresa import RUBROS  # noqa: E402
from app.core.auth import hash_password  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.core.permisos import PLANES, sembrar_roles_base  # noqa: E402
from app.models import (  # noqa: E402
    ArcaConfig,
    Deposito,
    PosCaja,
    PuntoVenta,
    Sucursal,
    Tenant,
    Usuario,
)

CUIT_PLACEHOLDER = "30712345670"  # DV válido; reemplazar al cargar el CUIT real


async def main(args: argparse.Namespace) -> None:
    async with SessionLocal() as db:
        # --- Tenant (idempotente por razón social) ---
        tenant = await db.scalar(select(Tenant).where(Tenant.razon_social == args.razon))
        if tenant is None:
            tenant = Tenant(
                razon_social=args.razon,
                nombre_fantasia=args.fantasia or args.razon,
                cuit=args.cuit,
                condicion_iva=args.condicion_iva,
                localidad=args.localidad,
                rubro=args.rubro,
                plan=args.plan,
            )
            db.add(tenant)
            await db.flush()
            print(f"[+] Tenant creado: {tenant.id} (plan={args.plan}, rubro={args.rubro})")
        else:
            tenant.plan = args.plan
            tenant.rubro = args.rubro
            print(f"[=] Tenant ya existe: {tenant.id} (plan/rubro actualizados a {args.plan}/{args.rubro})")

        # --- Roles base RBAC (lazy-seed idéntico al de GET /roles) ---
        creados = await sembrar_roles_base(db, tenant.id)
        print(f"[{'+' if creados else '='}] Roles base: {creados} creados")

        # --- Sucursal ---
        sucursal = await db.scalar(
            select(Sucursal).where(
                Sucursal.tenant_id == tenant.id, Sucursal.nombre == "Casa Central"
            )
        )
        if sucursal is None:
            sucursal = Sucursal(tenant_id=tenant.id, nombre="Casa Central", localidad=args.localidad)
            db.add(sucursal)
            await db.flush()
            print(f"[+] Sucursal creada: {sucursal.id}")
        else:
            print(f"[=] Sucursal ya existe: {sucursal.id}")

        # --- Usuario admin (email único global; rol_id NULL = acceso total DEL PLAN) ---
        usuario = await db.scalar(select(Usuario).where(Usuario.email == args.email))
        if usuario is None:
            usuario = Usuario(
                tenant_id=tenant.id,
                email=args.email,
                nombre=args.nombre_usuario,
                password_hash=hash_password(args.clave),
                nivel_acceso=1,
                sucursal_id=sucursal.id,
            )
            db.add(usuario)
            print(f"[+] Usuario creado: {args.email}")
        elif usuario.tenant_id != tenant.id:
            print(f"[!] ABORT: {args.email} ya existe en OTRO tenant ({usuario.tenant_id})")
            await db.rollback()
            sys.exit(1)
        else:
            usuario.password_hash = hash_password(args.clave)
            usuario.activo = True
            print(f"[=] Usuario ya existe: {args.email} (clave actualizada)")

        # --- ARCA config modo simulado (uno por tenant, unique) ---
        arca = await db.scalar(select(ArcaConfig).where(ArcaConfig.tenant_id == tenant.id))
        if arca is None:
            arca = ArcaConfig(
                tenant_id=tenant.id,
                modo="simulado",
                cuit=args.cuit,
                razon_social=args.razon[:80],
            )
            db.add(arca)
            print("[+] ARCA config creada (modo simulado)")
        else:
            print(f"[=] ARCA config ya existe (modo {arca.modo})")

        # --- Punto de venta ---
        pv = await db.scalar(
            select(PuntoVenta).where(PuntoVenta.tenant_id == tenant.id, PuntoVenta.numero == 1)
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

        # --- Depósito (obligatorio para mover stock; sin él, emitir da 422) ---
        deposito = await db.scalar(
            select(Deposito).where(Deposito.tenant_id == tenant.id, Deposito.codigo == "1")
        )
        if deposito is None:
            deposito = Deposito(tenant_id=tenant.id, codigo="1", nombre="Depósito Central", activo=True)
            db.add(deposito)
            await db.flush()
            print(f"[+] Depósito creado: cod 1 ({deposito.id})")
        else:
            print(f"[=] Depósito ya existe: cod 1 ({deposito.id})")

        # --- Caja POS default (la licencia POS sale vendible lista para operar) ---
        caja = await db.scalar(
            select(PosCaja).where(PosCaja.tenant_id == tenant.id, PosCaja.nombre == "Caja 1")
        )
        if caja is None:
            caja = PosCaja(
                tenant_id=tenant.id,
                sucursal_id=sucursal.id,
                nombre="Caja 1",
                punto_venta_id=pv.id,
                deposito_id=deposito.id,
            )
            db.add(caja)
            await db.flush()
            print(f"[+] Caja POS creada: Caja 1 ({caja.id})")
        else:
            print(f"[=] Caja POS ya existe: Caja 1 ({caja.id})")

        await db.commit()

        print("\n=== SETUP LISTO ===")
        print(f"tenant_id     : {tenant.id}")
        print(f"plan / rubro  : {tenant.plan} / {tenant.rubro}")
        print(f"punto_venta_id: {pv.id}")
        print(f"deposito_id   : {deposito.id}")
        print(f"pos_caja_id   : {caja.id}")
        print(f"login         : {args.email} / (la clave provista)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Setup de un tenant ZGC (onboarding asistido)")
    ap.add_argument("--razon", required=True, help="Razón social del tenant")
    ap.add_argument("--email", required=True, help="Email del usuario admin")
    ap.add_argument("--clave", required=True, help="Contraseña del usuario admin (mín. 6)")
    ap.add_argument("--plan", default="suite", choices=sorted(PLANES), help="Plan comercial")
    ap.add_argument("--rubro", default="general", choices=sorted(RUBROS), help="Rubro del tenant")
    ap.add_argument("--cuit", default=CUIT_PLACEHOLDER, help="CUIT (solo dígitos)")
    ap.add_argument("--condicion-iva", default="RI", help="RI / MO / EX ...")
    ap.add_argument("--localidad", default=None)
    ap.add_argument("--fantasia", default=None, help="Nombre de fantasía")
    ap.add_argument("--nombre-usuario", default="Administrador")
    args = ap.parse_args()
    asyncio.run(main(args))
