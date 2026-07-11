-- 015 — Fase 9: Contabilidad (módulo activable). Diseño en docs/DISENO-CONTABILIDAD.md.
-- Contabilidad DERIVADA: los asientos se generan desde los documentos operativos
-- con un motor regenerable (los asientos con origen_tipo != 'manual' se borran y
-- re-derivan por período — son artefactos derivados, NO documentos fuente; el
-- contrato de inmutabilidad de la 014 aplica a los documentos, no a ellos).
-- Aditiva e idempotente. Greenfield: no existía nada contable.
-- El plan de cuentas y los mapeos se siembran LAZY por tenant (GET /contabilidad/plan),
-- patrón roles RBAC — la migración no siembra datos de plan.

-- ============================================================================
-- 1. Plan de cuentas (jerárquico; seed argentino por tenant vía backend)
-- ============================================================================
create table if not exists plan_cuentas (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    codigo     varchar(15) not null,             -- jerárquico: 1.1.01
    nombre     varchar(80) not null,
    tipo       varchar(11) not null
               check (tipo in ('activo','pasivo','pn','r_positivo','r_negativo')),
    imputable  boolean     not null default true,  -- solo imputables llevan líneas
    padre_id   uuid references plan_cuentas(id),
    es_sistema boolean     not null default false, -- sembrada (renombrable, no borrable)
    activa     boolean     not null default true,
    created_at timestamptz not null default now()
);
create unique index if not exists uq_plan_cuentas_codigo on plan_cuentas(tenant_id, codigo);
create index if not exists idx_plan_cuentas_tenant on plan_cuentas(tenant_id);
create index if not exists idx_plan_cuentas_padre  on plan_cuentas(padre_id);

-- ============================================================================
-- 2. Mapeos regla → cuenta (espejo moderno de los CUENTA C6 del legacy:
--    ARTICULO.CUENTA, CONC_CAJ.CUENTA, RETENCIO.CUENTA, TARJETAS.CUENTA,
--    MAECTA.CUENTA, GASTOS, COMPRASM.CUENTA*, VENTASM.CUENTA1-3)
--    clave NULL = default de la regla (todo origen tiene fallback)
-- ============================================================================
create table if not exists asiento_mapeos (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    origen     varchar(20) not null,   -- ventas_familia | iva_debito | medio | ... (catálogo en services/contabilidad.py)
    clave      varchar(40),            -- uuid o texto según la regla; NULL = default
    cuenta_id  uuid        not null references plan_cuentas(id),
    updated_at timestamptz not null default now()
);
create unique index if not exists uq_asiento_mapeos
    on asiento_mapeos(tenant_id, origen, clave) nulls not distinct;
create index if not exists idx_asiento_mapeos_tenant on asiento_mapeos(tenant_id);

-- ============================================================================
-- 3. Asientos (materializados PERO regenerables) + líneas
--    origen_tipo/origen_id = documento fuente (idempotencia del motor);
--    'manual' = asiento cargado a mano (NUNCA lo toca la regeneración; se
--    anula marcando, contrato 014)
-- ============================================================================
create table if not exists asientos (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid         not null references tenants(id) on delete cascade,
    numero      bigint,
    fecha       date         not null,
    descripcion varchar(200),
    origen_tipo varchar(20)  not null default 'manual',
    origen_id   uuid,
    anulado_at  timestamptz,            -- solo manuales
    anulado_por uuid references usuarios(id),
    creado_por  uuid references usuarios(id),
    created_at  timestamptz  not null default now()
);
create index if not exists idx_asientos_tenant_fecha on asientos(tenant_id, fecha);
create index if not exists idx_asientos_origen on asientos(tenant_id, origen_tipo, origen_id);

create table if not exists asiento_lineas (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid          not null references tenants(id) on delete cascade,
    asiento_id uuid          not null references asientos(id) on delete cascade,
    orden      smallint      not null default 0,
    cuenta_id  uuid          not null references plan_cuentas(id),
    debe       numeric(14,2) not null default 0 check (debe >= 0),
    haber      numeric(14,2) not null default 0 check (haber >= 0),
    detalle    varchar(120),
    check (debe = 0 or haber = 0)
);
-- índice por el FK solo (regla selectin) + (tenant, cuenta) para el mayor
create index if not exists idx_asiento_lineas_asiento on asiento_lineas(asiento_id);
create index if not exists idx_asiento_lineas_cuenta  on asiento_lineas(tenant_id, cuenta_id);

-- ============================================================================
-- 4. Períodos cerrados (cierre mensual simple; reabrir = marcar, contrato 014)
-- ============================================================================
create table if not exists contab_periodos (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    periodo     date        not null,   -- 1° del mes
    cerrado_por uuid references usuarios(id),
    cerrado_at  timestamptz not null default now(),
    anulado_at  timestamptz,            -- reabierto
    anulado_por uuid references usuarios(id)
);
create unique index if not exists uq_contab_periodos
    on contab_periodos(tenant_id, periodo) where anulado_at is null;
create index if not exists idx_contab_periodos_tenant on contab_periodos(tenant_id);

-- ============================================================================
-- 5. Módulo de permisos `contabilidad` para roles de sistema existentes
--    (ESPEJO de app/core/permisos.py — F9):
--      admin/gerente → anular · consulta → ver · cajero/vendedor → (sin acceso)
-- ============================================================================
insert into rol_permisos (rol_id, tenant_id, modulo, accion)
select r.id, r.tenant_id, 'contabilidad', p.accion
from roles r
join (values
    ('admin','anular'),
    ('gerente','anular'),
    ('consulta','ver')
) as p(codigo, accion) on p.codigo = r.codigo
where r.es_sistema
on conflict (rol_id, modulo) do nothing;

-- ============================================================================
-- 6. RLS deny-all (segunda defensa, patrón 005..014)
-- ============================================================================
alter table plan_cuentas    enable row level security;
alter table asiento_mapeos  enable row level security;
alter table asientos        enable row level security;
alter table asiento_lineas  enable row level security;
alter table contab_periodos enable row level security;
