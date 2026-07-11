-- 017 — F11: Vendedores y comisiones. Diseño en docs/DISENO-VENDEDORES-COMISIONES.md.
-- Aditiva e idempotente. Rol vendedor sobre la BUE (espejo moderno de
-- VIAJANTE.DBF), sellado del vendedor en clientes/comprobantes/recibos
-- (CVIAJ del legacy) y liquidaciones como DOCUMENTO contabilizable
-- (modernización de la tabla de trabajo GV0040).
-- OJO deploy: el backend nuevo mapea las columnas vendedor_id → la 017 va
-- ANTES del push (como la 010/014).

-- ============================================================================
-- 1. Rol vendedor sobre la BUE (patrón clientes/proveedores)
-- ============================================================================
create table if not exists vendedores (
    id           uuid primary key default gen_random_uuid(),
    tenant_id    uuid          not null references tenants(id) on delete cascade,
    entidad_id   uuid          not null references entidades(id),
    codigo       varchar(10),
    comision_pct numeric(5,2)  not null default 0 check (comision_pct >= 0),
    modalidad    varchar(8)    not null default 'venta'
                 check (modalidad in ('venta','cobranza')),
    observaciones varchar(200),
    activo       boolean       not null default true,
    created_at   timestamptz   not null default now(),
    updated_at   timestamptz   not null default now()
);
create unique index if not exists uq_vendedores_entidad on vendedores(tenant_id, entidad_id);
create unique index if not exists uq_vendedores_codigo
    on vendedores(tenant_id, codigo) where codigo is not null;
-- índice por el FK solo (regla selectin, CLAUDE.md §6)
create index if not exists idx_vendedores_entidad on vendedores(entidad_id);

-- ============================================================================
-- 2. Sellado del vendedor (espejo de CLIENTES/VENTASM/RECIBOSM.CVIAJ)
-- ============================================================================
alter table clientes     add column if not exists vendedor_id uuid references vendedores(id);
alter table comprobantes add column if not exists vendedor_id uuid references vendedores(id);
alter table recibos      add column if not exists vendedor_id uuid references vendedores(id);
create index if not exists idx_comprobantes_vendedor
    on comprobantes(vendedor_id) where vendedor_id is not null;
create index if not exists idx_recibos_vendedor
    on recibos(vendedor_id) where vendedor_id is not null;

-- ============================================================================
-- 3. Liquidaciones de comisión (documento: completo, inmutable, mapeable)
--    "Ya liquidado" = existe un ítem de una liquidación VIVA que referencia el
--    documento — los comprobantes/recibos fuente NO se mutan.
-- ============================================================================
create table if not exists comision_liquidaciones (
    id           uuid primary key default gen_random_uuid(),
    tenant_id    uuid          not null references tenants(id) on delete cascade,
    numero       bigint        not null,
    vendedor_id  uuid          not null references vendedores(id),
    modalidad    varchar(8)    not null,
    desde        date          not null,
    hasta        date          not null,
    comision_pct numeric(5,2)  not null,   -- sellado al liquidar
    base_total   numeric(14,2) not null default 0,
    total        numeric(14,2) not null default 0,
    observaciones varchar(200),
    anulado_at   timestamptz,
    anulado_por  uuid references usuarios(id),
    creado_por   uuid references usuarios(id),
    created_at   timestamptz   not null default now()
);
create unique index if not exists uq_comision_liq_numero
    on comision_liquidaciones(tenant_id, numero);
create index if not exists idx_comision_liq_vendedor on comision_liquidaciones(vendedor_id);

create table if not exists comision_liquidacion_items (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid          not null references tenants(id) on delete cascade,
    liquidacion_id uuid          not null references comision_liquidaciones(id) on delete cascade,
    comprobante_id uuid references comprobantes(id) on delete cascade,
    recibo_id      uuid references recibos(id) on delete cascade,
    fecha          date          not null,
    descripcion    varchar(120)  not null,
    base           numeric(14,2) not null,
    importe        numeric(14,2) not null,
    check (num_nonnulls(comprobante_id, recibo_id) = 1)
);
create index if not exists idx_comision_items_liq on comision_liquidacion_items(liquidacion_id);
create index if not exists idx_comision_items_comp
    on comision_liquidacion_items(comprobante_id) where comprobante_id is not null;
create index if not exists idx_comision_items_recibo
    on comision_liquidacion_items(recibo_id) where recibo_id is not null;

-- ============================================================================
-- 4. Módulo de permisos `vendedores` para roles de sistema existentes
--    (ESPEJO de app/core/permisos.py — F11):
--      admin/gerente → anular · consulta → ver · cajero/vendedor → (sin acceso)
-- ============================================================================
insert into rol_permisos (rol_id, tenant_id, modulo, accion)
select r.id, r.tenant_id, 'vendedores', p.accion
from roles r
join (values
    ('admin','anular'),
    ('gerente','anular'),
    ('consulta','ver')
) as p(codigo, accion) on p.codigo = r.codigo
where r.es_sistema
on conflict (rol_id, modulo) do nothing;

-- ============================================================================
-- 5. RLS deny-all (segunda defensa, patrón 005..016)
-- ============================================================================
alter table vendedores                 enable row level security;
alter table comision_liquidaciones     enable row level security;
alter table comision_liquidacion_items enable row level security;
