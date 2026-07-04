-- 002 — Base Única de Entidades (BUE) + rol Cliente + catálogos.
-- Regla CLAUDE.md §1-bis: toda persona física/jurídica existe UNA vez en
-- entidades; los roles (clientes, proveedores, ...) son satélites por id_entidad.

-- Catálogo global (sin tenant): provincias con código ARCA/AFIP (útil para FE).
create table if not exists provincias (
    codigo_arca smallint primary key,
    nombre      varchar(40) not null unique
);
insert into provincias (codigo_arca, nombre) values
    (0,'CABA'),(1,'Buenos Aires'),(2,'Catamarca'),(3,'Córdoba'),(4,'Corrientes'),
    (5,'Entre Ríos'),(6,'Jujuy'),(7,'Mendoza'),(8,'La Rioja'),(9,'Salta'),
    (10,'San Juan'),(11,'San Luis'),(12,'Santa Fe'),(13,'Santiago del Estero'),
    (14,'Tucumán'),(16,'Chaco'),(17,'Chubut'),(18,'Formosa'),(19,'Misiones'),
    (20,'Neuquén'),(21,'La Pampa'),(22,'Río Negro'),(23,'Santa Cruz'),
    (24,'Tierra del Fuego')
on conflict (codigo_arca) do nothing;

-- ===== BUE: entidades =====
create table if not exists entidades (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid         not null references tenants(id) on delete cascade,
    tipo_persona    char(1)      not null default 'F' check (tipo_persona in ('F','J')),
    razon_social    varchar(120) not null,          -- nombre y apellido si es persona física
    nombre_fantasia varchar(80),
    tipo_documento  varchar(4)   not null default 'DNI'
                    check (tipo_documento in ('CUIT','CUIL','DNI','SD')),  -- SD = sin documento
    nro_documento   varchar(11),                    -- solo dígitos; DV validado en la app
    condicion_iva   varchar(2)   not null default 'CF'
                    check (condicion_iva in ('RI','MT','EX','CF')),  -- define letra de factura
    email           varchar(120),
    telefono_1      varchar(30),
    telefono_2      varchar(30),
    domicilio       varchar(120),
    localidad       varchar(60),
    provincia_id    smallint references provincias(codigo_arca),
    codigo_postal   varchar(10),
    observaciones   text,
    activo          boolean      not null default true,
    created_at      timestamptz  not null default now(),
    updated_at      timestamptz  not null default now()
);
create index if not exists idx_entidades_tenant on entidades(tenant_id);
-- un mismo documento no puede duplicarse dentro del tenant
create unique index if not exists uq_entidades_doc
    on entidades(tenant_id, tipo_documento, nro_documento)
    where nro_documento is not null;

create table if not exists entidad_contactos (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    entidad_id  uuid        not null references entidades(id) on delete cascade,
    nombre      varchar(80) not null,
    cargo       varchar(60),
    telefono    varchar(30),
    email       varchar(120),
    created_at  timestamptz not null default now()
);
create index if not exists idx_contactos_entidad on entidad_contactos(entidad_id);

-- ===== Catálogos por tenant =====
create table if not exists zonas (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    nombre     varchar(40) not null,
    unique (tenant_id, nombre)
);

create table if not exists condiciones_venta (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    descripcion varchar(60) not null,     -- ej: "Contado", "0-30-60 días"
    dias        integer[]   not null default '{0}',  -- vencimientos (legacy: hasta 12)
    activa      boolean     not null default true,
    unique (tenant_id, descripcion)
);

-- ===== Rol: cliente (satélite de la BUE) =====
create table if not exists clientes (
    id                 uuid primary key default gen_random_uuid(),
    tenant_id          uuid          not null references tenants(id) on delete cascade,
    entidad_id         uuid          not null references entidades(id),
    codigo             varchar(10),                    -- código interno (legacy CODCLI); lo trae el migrador
    lista_precios      smallint      not null default 1 check (lista_precios between 1 and 4),
    condicion_venta_id uuid references condiciones_venta(id),
    zona_id            uuid references zonas(id),
    descuento          numeric(5,2)  not null default 0,
    limite_credito     numeric(12,2),
    bloqueado          boolean       not null default false,
    observaciones      text,
    activo             boolean       not null default true,
    created_at         timestamptz   not null default now(),
    updated_at         timestamptz   not null default now(),
    unique (tenant_id, entidad_id),                    -- una entidad es cliente UNA vez por tenant
    unique (tenant_id, codigo)
);
create index if not exists idx_clientes_tenant on clientes(tenant_id);
