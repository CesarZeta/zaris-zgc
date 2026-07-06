-- 012 — Fase 7: domicilios normalizados OSM (diseño en
-- docs/DISENO-LOGISTICA-Y-DOMICILIOS.md §1) + geo en sucursales + sesgo por tenant.
-- Aditiva e idempotente: solo ADD COLUMN nullable + tabla nueva.

-- lat/lon en entidades (BUE): se completan SOLO desde OSM (criterio BUC).
alter table entidades add column if not exists latitud  numeric(10,7);
alter table entidades add column if not exists longitud numeric(10,7);

-- sucursales: domicilio normalizado completo (espejo de entidades) + geo.
-- provincia_id/codigo_postal no existían (la 001 solo tenía domicilio/localidad).
alter table sucursales add column if not exists provincia_id  smallint references provincias(codigo_arca);
alter table sucursales add column if not exists codigo_postal varchar(10);
alter table sucursales add column if not exists latitud       numeric(10,7);
alter table sucursales add column if not exists longitud      numeric(10,7);

-- Sesgo geográfico opcional del tenant (diseño §1.2, adaptación 2): si está
-- configurado, el proxy Nominatim manda viewbox SIN bounded=1 (prioriza la
-- zona sin excluir el resto del país). NULL = sin sesgo (default ZGC).
alter table tenants add column if not exists geo_centro_lat   numeric(10,7);
alter table tenants add column if not exists geo_centro_lon   numeric(10,7);
alter table tenants add column if not exists geo_delta_grados numeric(6,4);

-- Domicilios múltiples por entidad (la BUE declara "domicilios" en plural
-- desde el día 1; requerido por Logística F12-bis para entregas con snapshot).
-- El domicilio plano de `entidades` sigue siendo el fiscal/principal.
create table if not exists entidad_domicilios (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid        not null references tenants(id) on delete cascade,
    entidad_id     uuid        not null references entidades(id) on delete cascade,
    tipo           varchar(10) not null default 'entrega'
                   check (tipo in ('fiscal','entrega','otro')),
    etiqueta       varchar(60),                 -- ej: "Depósito Ruta 9"
    domicilio      varchar(120),
    localidad      varchar(60),
    provincia_id   smallint references provincias(codigo_arca),
    codigo_postal  varchar(10),
    latitud        numeric(10,7),
    longitud       numeric(10,7),
    predeterminado boolean     not null default false,
    activo         boolean     not null default true,
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);
-- índice por el FK solo (regla §6 CLAUDE.md: los selectin emiten WHERE fk IN sin tenant)
create index if not exists idx_entidad_domicilios_entidad on entidad_domicilios(entidad_id);
create index if not exists idx_entidad_domicilios_tenant  on entidad_domicilios(tenant_id);

alter table entidad_domicilios enable row level security;
