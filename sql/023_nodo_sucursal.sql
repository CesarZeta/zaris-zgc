-- 023 — F13-LAN N1: nodo de sucursal (aparejamiento + réplica de bajada).
-- Diseño en docs/DISENO-NODO-LAN.md. Aditiva e idempotente; segura de aplicar
-- ANTES del backend nuevo (el viejo no la lee).
-- En prod: re-aplicar la 005 después (tablas nuevas ⇒ RLS + revokes PostgREST).

-- 1) Nodos de sucursal (nube): identidad y aparejamiento (§3 del diseño).
--    El token de aparejamiento se muestra UNA vez y acá solo vive su hash
--    (patrón reset-password de F6.5). `punto_venta_id` = PV PROPIO del nodo
--    para la facturación de gestión (§0-bis); los PV de las cajas POS de la
--    sucursal quedan también exclusivos del nodo mientras esté activo.
create table if not exists sucursal_nodos (
    id              uuid        primary key default gen_random_uuid(),
    tenant_id       uuid        not null references tenants(id) on delete cascade,
    sucursal_id     uuid        not null references sucursales(id),
    nombre          varchar(60) not null,
    token_hash      varchar(100) not null,
    estado          varchar(8)  not null default 'activo'
                    check (estado in ('activo', 'revocado')),
    punto_venta_id  uuid        references puntos_venta(id),
    last_seen_at    timestamptz,
    last_sync_at    timestamptz,
    version_app     varchar(20),
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
-- un solo nodo ACTIVO por sucursal (revocados quedan como historial)
create unique index if not exists uq_sucursal_nodos_activo
    on sucursal_nodos (sucursal_id) where estado = 'activo';
create index if not exists ix_sucursal_nodos_tenant on sucursal_nodos (tenant_id);
alter table sucursal_nodos enable row level security;

-- 2) Checkpoints de réplica (los usa SOLO la base local del nodo; en la nube
--    queda vacía). Sin tenant_id: un nodo replica un único tenant.
--    `extra` guarda el contexto del aparejamiento (fila '_nodo': sucursal,
--    PV propio) para que el nodo arranque offline sin re-handshake.
create table if not exists sync_checkpoints (
    tabla           text        primary key,
    hasta           timestamptz,
    filas           bigint      not null default 0,
    extra           jsonb,
    actualizado_at  timestamptz not null default now()
);
alter table sync_checkpoints enable row level security;

-- 3) updated_at para la réplica incremental (las demás tablas replicadas van
--    en modo snapshot — chicas — o solo-inicial; ver services/sync_tablas.py).
alter table articulo_variantes add column if not exists
    updated_at timestamptz not null default now();

-- 4) updated_at confiable A NIVEL DB para las tablas incrementales: hasta hoy
--    solo se seteaba en el INSERT (server_default) — un UPDATE por ORM o SQL
--    directo no lo movía y la réplica por checkpoint se perdería el cambio.
create or replace function zgc_touch_updated_at() returns trigger as $$
begin
    new.updated_at := now();
    return new;
end;
$$ language plpgsql;

do $$
declare
    t text;
begin
    foreach t in array array['entidades', 'clientes', 'articulos', 'articulo_variantes']
    loop
        execute format('drop trigger if exists trg_touch_updated_at on %I', t);
        execute format(
            'create trigger trg_touch_updated_at before update on %I
             for each row execute function zgc_touch_updated_at()', t
        );
    end loop;
end $$;
