# Historial de Migraciones — ZGC

| # | Archivo | Local (zgc_dev) | Supabase (zaris-zgc) | Notas |
|---|---|---|---|---|
| 001 | `sql/001_nucleo_tenants_usuarios.sql` | ✅ 2026-07-03 | ⏳ pendiente (cuenta Supabase nueva en creación) | tenants, sucursales, usuarios. RLS se agrega al desplegar en Supabase. |
| 002 | `sql/002_bue_entidades_clientes.sql` | ✅ 2026-07-03 | ⏳ pendiente | BUE: entidades + contactos, provincias (códigos ARCA), zonas, condiciones_venta, rol clientes. |

Seed dev: `backend/seed_auth.py` → tenant "Empresa Demo SRL" + sucursal "Casa Central" + `admin@zgc.dev` / `123456` (aplicado en local 2026-07-03).
