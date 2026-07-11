-- 020 — F12-c: despiece / transformación de stock (DISENO-POS-PERFILES.md §2).
-- Capacidad GENERAL del módulo Stock (carnicería: media res → cortes; también
-- fraccionamiento y combos): una salida del artículo origen + N entradas de
-- destinos atadas por grupo_id, con merma explícita y costeo proporcional al
-- VALOR (coeficiente por corte), no al peso.
-- Aditiva e idempotente; segura de aplicar ANTES del backend nuevo.
-- En prod: re-aplicar la 005 después (tablas nuevas ⇒ RLS + revokes PostgREST).

-- Kardex: tipo nuevo de movimiento
alter table stock_movimientos drop constraint if exists stock_movimientos_tipo_check;
alter table stock_movimientos add constraint stock_movimientos_tipo_check
    check (tipo in ('inicial','ajuste','transferencia','compra','venta',
                    'devolucion','remito','anulacion','transformacion'));

-- Plantillas de despiece: artículo origen + cortes con % de rendimiento
-- sugerido y coeficiente de valor. La plantilla PRECARGA la pantalla; los
-- kilos reales se corrigen a mano en cada ingreso.
create table if not exists despiece_plantillas (
    id                  uuid        primary key default gen_random_uuid(),
    tenant_id           uuid        not null references tenants(id) on delete cascade,
    articulo_origen_id  uuid        not null references articulos(id),
    nombre              varchar(60) not null,
    activa              boolean     not null default true,
    created_at          timestamptz not null default now(),
    unique (tenant_id, nombre)
);

create table if not exists despiece_plantilla_cortes (
    id               uuid          primary key default gen_random_uuid(),
    tenant_id        uuid          not null references tenants(id) on delete cascade,
    plantilla_id     uuid          not null references despiece_plantillas(id) on delete cascade,
    articulo_id      uuid          not null references articulos(id),
    rendimiento_pct  numeric(6,3)  not null default 0 check (rendimiento_pct >= 0),
    coef_valor       numeric(8,4)  not null default 1 check (coef_valor > 0),
    orden            smallint      not null default 0,
    -- el UNIQUE arranca por el FK del selectin y le sirve de índice (regla §6)
    unique (plantilla_id, articulo_id)
);

alter table despiece_plantillas enable row level security;
alter table despiece_plantilla_cortes enable row level security;
