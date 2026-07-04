-- 001 — Núcleo multi-tenant: tenants (empresas), sucursales y usuarios.
-- Regla ZGC: toda tabla de negocio lleva tenant_id (CLAUDE.md §1-bis).
-- RLS se agrega en la migración de despliegue a Supabase (en local no aplica).

create table if not exists tenants (
    id              uuid primary key default gen_random_uuid(),
    razon_social    varchar(80)  not null,
    nombre_fantasia varchar(80),
    cuit            varchar(11),                 -- solo dígitos; validación de DV en la app
    condicion_iva   varchar(2)   not null default 'RI'
                    check (condicion_iva in ('RI','MT','EX')),  -- Resp.Inscripto / Monotributo / Exento
    email           varchar(120),
    telefono        varchar(40),
    domicilio       varchar(120),
    localidad       varchar(60),
    provincia       varchar(40),
    codigo_postal   varchar(10),
    activo          boolean      not null default true,
    created_at      timestamptz  not null default now(),
    updated_at      timestamptz  not null default now()
);

create table if not exists sucursales (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    nombre      varchar(60) not null,
    domicilio   varchar(120),
    localidad   varchar(60),
    telefono    varchar(40),
    activa      boolean     not null default true,
    created_at  timestamptz not null default now(),
    unique (tenant_id, nombre)
);
create index if not exists idx_sucursales_tenant on sucursales(tenant_id);

create table if not exists usuarios (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid         not null references tenants(id) on delete cascade,
    email         varchar(120) not null unique,   -- único global: un email pertenece a un tenant
    nombre        varchar(80)  not null,
    password_hash varchar(100) not null,          -- bcrypt directo (patrón ZGE, sin passlib)
    nivel_acceso  smallint     not null default 1, -- 1=Administrador; niveles/permisos por módulo se amplían en Fase 1
    sucursal_id   uuid references sucursales(id),
    activo        boolean      not null default true,
    created_at    timestamptz  not null default now(),
    updated_at    timestamptz  not null default now()
);
create index if not exists idx_usuarios_tenant on usuarios(tenant_id);
