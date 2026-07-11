-- 021 — F12-d: POS Resto (DISENO-POS-PERFILES.md §3) — sucesor del legacy
-- RestoDelivery. Salones, mesas, comandas y sus ítems viven en tablas pos_*
-- y NUNCA se trasladan a la gestión (mandato César): a la gestión llega SOLO
-- la venta final emitida por emitir_core al cerrar la mesa.
-- Aditiva e idempotente; segura de aplicar ANTES del backend nuevo.
-- En prod: re-aplicar la 005 después (tablas nuevas ⇒ RLS + revokes PostgREST).

-- Perfil de la caja: estandar (mostrador, el POS de F6) | resto (mesas/comandas).
alter table pos_cajas add column if not exists perfil varchar(10) not null default 'estandar';
alter table pos_cajas drop constraint if exists pos_cajas_perfil_check;
alter table pos_cajas add constraint pos_cajas_perfil_check
    check (perfil in ('estandar', 'resto'));

-- Sectores del local (salón, vereda, barra)
create table if not exists pos_salones (
    id          uuid        primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    nombre      varchar(40) not null,
    orden       smallint    not null default 0,
    activo      boolean     not null default true,
    created_at  timestamptz not null default now(),
    unique (tenant_id, nombre)
);

create table if not exists pos_mesas (
    id          uuid        primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    salon_id    uuid        not null references pos_salones(id) on delete cascade,
    numero      integer     not null,
    nombre      varchar(20),
    activa      boolean     not null default true,
    created_at  timestamptz not null default now(),
    unique (salon_id, numero)
);

-- La comanda es la CUENTA ABIERTA de la mesa (legacy MESAS.DBF) o un pedido
-- delivery/takeaway. No es un comprobante: el comprobante nace al cobrar.
create table if not exists pos_comandas (
    id              uuid         primary key default gen_random_uuid(),
    tenant_id       uuid         not null references tenants(id) on delete cascade,
    caja_id         uuid         not null references pos_cajas(id),
    mesa_id         uuid         references pos_mesas(id),
    tipo            varchar(10)  not null default 'mesa'
                    check (tipo in ('mesa', 'delivery', 'takeaway')),
    estado          varchar(10)  not null default 'abierta'
                    check (estado in ('abierta', 'cerrada', 'anulada')),
    mozo_id         uuid         not null references usuarios(id),
    cubiertos       smallint,
    cliente_nombre  varchar(80),
    telefono        varchar(40),
    -- domicilio snapshot para delivery (normalizado OSM en el front, criterio BUC)
    domicilio       varchar(120),
    localidad       varchar(60),
    latitud         numeric(10, 7),
    longitud        numeric(10, 7),
    envio_estado    varchar(15)
                    check (envio_estado in ('en_preparacion', 'despachado', 'entregado')),
    propina_pct     numeric(5, 2) not null default 0,
    observaciones   varchar(200),
    comprobante_id  uuid         references comprobantes(id),
    abierta_at      timestamptz  not null default now(),
    cerrada_at      timestamptz,
    check (tipo != 'mesa' or mesa_id is not null)
);
-- una sola comanda ABIERTA por mesa
create unique index if not exists uq_pos_comandas_mesa_abierta
    on pos_comandas (mesa_id) where estado = 'abierta' and mesa_id is not null;
create index if not exists ix_pos_comandas_tenant_estado
    on pos_comandas (tenant_id, estado);

create table if not exists pos_comanda_items (
    id               uuid          primary key default gen_random_uuid(),
    tenant_id        uuid          not null references tenants(id) on delete cascade,
    comanda_id       uuid          not null references pos_comandas(id) on delete cascade,
    articulo_id      uuid          not null references articulos(id),
    variante_id      uuid          references articulo_variantes(id),
    descripcion      varchar(120)  not null,
    cantidad         numeric(12, 3) not null check (cantidad > 0),
    precio_unitario  numeric(14, 2) not null,
    observaciones    varchar(120),
    estado_cocina    varchar(10)   not null default 'pendiente'
                     check (estado_cocina in ('pendiente', 'enviado')),
    enviado_at       timestamptz,
    orden            smallint      not null default 0,
    created_at       timestamptz   not null default now()
);
-- índice del FK para el selectin (regla §6: el loader emite WHERE fk IN (...))
create index if not exists ix_pos_comanda_items_comanda on pos_comanda_items (comanda_id);

alter table pos_salones enable row level security;
alter table pos_mesas enable row level security;
alter table pos_comandas enable row level security;
alter table pos_comanda_items enable row level security;
