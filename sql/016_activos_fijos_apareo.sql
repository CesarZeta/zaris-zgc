-- 016 — F9-bis: bienes de uso + amortizaciones, y apareo de transferencias
-- entre cuentas propias. Diseño en docs/DISENO-CONTABILIDAD.md §6.
-- Aditiva e idempotente. Sin seed de datos: las categorías base se siembran
-- LAZY por tenant junto al plan de cuentas (GET /contabilidad/plan).
-- Sin permisos nuevos: activos fijos van bajo el módulo `contabilidad` y el
-- apareo bajo `bancos` (ambos sembrados en 013/015).

-- ============================================================================
-- 1. Categorías de bienes de uso (catálogo por tenant, contrato MAPEABLE:
--    la clave de los mapeos bienes_uso/amort_* es el id de la categoría)
-- ============================================================================
create table if not exists activo_categorias (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid        not null references tenants(id) on delete cascade,
    nombre          varchar(60) not null,
    vida_util_meses int         not null default 60 check (vida_util_meses > 0),
    es_sistema      boolean     not null default false,
    activa          boolean     not null default true,
    created_at      timestamptz not null default now()
);
create unique index if not exists uq_activo_categorias
    on activo_categorias(tenant_id, nombre);

-- ============================================================================
-- 2. Activos fijos (bienes de uso). El ALTA no deriva asiento (el bien entró
--    por su documento); el motor deriva amortizaciones mensuales y la baja.
--    Baja real = fecha_baja + baja_motivo; error de carga = anulado_at (014).
-- ============================================================================
create table if not exists activos_fijos (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid          not null references tenants(id) on delete cascade,
    nombre              varchar(120)  not null,
    categoria_id        uuid          not null references activo_categorias(id),
    fecha_alta          date          not null,
    inicio_amortizacion date          not null,   -- 1° del mes desde el que devenga
    valor_origen        numeric(14,2) not null check (valor_origen > 0),
    valor_residual      numeric(14,2) not null default 0 check (valor_residual >= 0),
    vida_util_meses     int           not null check (vida_util_meses > 0),
    compra_id           uuid references compras(id) on delete set null,
    fecha_baja          date,
    baja_motivo         varchar(120),
    observaciones       varchar(200),
    anulado_at          timestamptz,
    anulado_por         uuid references usuarios(id),
    creado_por          uuid references usuarios(id),
    created_at          timestamptz   not null default now(),
    check (valor_residual < valor_origen)
);
create index if not exists idx_activos_fijos_tenant on activos_fijos(tenant_id);
-- índice por el FK solo (regla selectin/joins, CLAUDE.md §6)
create index if not exists idx_activos_fijos_categoria on activos_fijos(categoria_id);

-- ============================================================================
-- 3. Apareo de transferencias entre cuentas propias (simétrico: ambos lados
--    referencian al otro). Un par apareado deriva UN asiento banco a banco,
--    sin cuenta puente.
-- ============================================================================
alter table banco_movimientos
    add column if not exists contrapartida_id uuid references banco_movimientos(id) on delete set null;
create index if not exists idx_banco_movs_contrapartida
    on banco_movimientos(contrapartida_id) where contrapartida_id is not null;

-- ============================================================================
-- 4. RLS deny-all (segunda defensa, patrón 005..015)
-- ============================================================================
alter table activo_categorias enable row level security;
alter table activos_fijos     enable row level security;
