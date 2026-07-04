-- 004 — Fase 2.5: rubro por tenant + variantes de artículos (multipropósito).
-- Diseño en docs/DISENO-RUBROS-Y-VARIANTES.md: la gestión central es una sola;
-- el rubro cambia presets/UI. Las variantes (hasta 3 atributos: Talle, Color,
-- Gusto, Capacidad...) tienen EAN y stock propios; un artículo sin variantes
-- sigue funcionando igual que antes (variante_id NULL en stock y kardex).

-- ===== Rubro del tenant =====
alter table tenants add column if not exists rubro varchar(30) not null default 'general'
    check (rubro in ('general','supermercado','indumentaria_calzado','electronica',
                     'ferreteria_repuestos','distribuidora'));

-- ===== Atributos y valores (por tenant) =====
create table if not exists atributos (
    id        uuid primary key default gen_random_uuid(),
    tenant_id uuid        not null references tenants(id) on delete cascade,
    nombre    varchar(30) not null,          -- Talle, Color, Gusto, Capacidad...
    orden     smallint    not null default 0,
    unique (tenant_id, nombre)
);

create table if not exists atributo_valores (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    atributo_id uuid        not null references atributos(id) on delete cascade,
    valor       varchar(30) not null,        -- S, M, L / Rojo, Azul / 128GB...
    orden       smallint    not null default 0,
    unique (tenant_id, atributo_id, valor)
);

-- ===== Variantes: combinación de hasta 3 valores de atributo =====
-- El padre (articulos) define descripción, familia, IVA y las 4 listas;
-- la variante define identidad de venta (EAN propio) y ajuste de precio.
create table if not exists articulo_variantes (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid          not null references tenants(id) on delete cascade,
    articulo_id   uuid          not null references articulos(id) on delete cascade,
    valor_1_id    uuid          not null references atributo_valores(id),
    valor_2_id    uuid references atributo_valores(id),
    valor_3_id    uuid references atributo_valores(id),
    codigo_barras varchar(20),
    sku_sufijo    varchar(20),                        -- ej: "-M-ROJO"
    dif_precio    numeric(14,4) not null default 0,   -- se suma a precio_1..4 del padre
    activo        boolean       not null default true,
    created_at    timestamptz   not null default now(),
    unique nulls not distinct (tenant_id, articulo_id, valor_1_id, valor_2_id, valor_3_id)
);
create index if not exists idx_variantes_articulo on articulo_variantes(tenant_id, articulo_id);
-- EAN de variante único por tenant (la unicidad cruzada contra articulos.codigo_barras
-- se valida en la app: son dos tablas)
create unique index if not exists uq_variantes_cbarra
    on articulo_variantes(tenant_id, codigo_barras)
    where codigo_barras is not null;

-- ===== Stock y kardex por variante =====
-- variante_id NULL = artículo sin variantes (todo lo ya migrado sigue válido).
alter table articulo_stock add column if not exists variante_id
    uuid references articulo_variantes(id) on delete cascade;
alter table articulo_stock drop constraint if exists
    articulo_stock_tenant_id_articulo_id_deposito_id_key;
create unique index if not exists uq_articulo_stock_pos
    on articulo_stock(tenant_id, articulo_id, deposito_id, variante_id)
    nulls not distinct;

alter table stock_movimientos add column if not exists variante_id
    uuid references articulo_variantes(id) on delete cascade;
