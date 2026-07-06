-- 013 — Fase 8: Cheques y Bancos + cash-flow proyectado.
-- Diseño en docs/DISENO-CHEQUES-Y-BANCOS.md. Greenfield (no existía modelo de
-- cheques/bancos). Aditiva e idempotente: tablas nuevas + seed del módulo de
-- permisos `bancos` para roles de sistema existentes. Segura de aplicar sola
-- (el backend viejo no lee estas tablas ni el módulo `bancos`).

-- ============================================================================
-- 1. Cuentas bancarias propias del tenant
-- ============================================================================
create table if not exists cuentas_bancarias (
    id                uuid primary key default gen_random_uuid(),
    tenant_id         uuid        not null references tenants(id) on delete cascade,
    banco             varchar(60) not null,
    sucursal_bancaria varchar(60),
    tipo              varchar(2)  not null default 'CC' check (tipo in ('CC','CA')),
    numero            varchar(30),
    cbu               varchar(22),
    alias             varchar(40),
    moneda            varchar(3)  not null default 'ARS' check (moneda in ('ARS','USD')),
    saldo_inicial     numeric(14,2) not null default 0,
    activa            boolean     not null default true,
    observaciones     varchar(200),
    created_at        timestamptz not null default now()
);
create index if not exists idx_cuentas_bancarias_tenant on cuentas_bancarias(tenant_id);

-- ============================================================================
-- 2. Cheques (terceros y propios) con máquina de estados (§2 del diseño)
--    Se crea ANTES de banco_movimientos: éste referencia cheque_id.
--    banco_movimiento_id se agrega por ALTER al final (FK circular).
-- ============================================================================
create table if not exists cheques (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid        not null references tenants(id) on delete cascade,
    clase               varchar(8)  not null check (clase in ('tercero','propio')),
    numero              varchar(20) not null,
    banco               varchar(60) not null,
    sucursal_banco      varchar(60),
    plaza               varchar(60),
    titular             varchar(80),
    cuit_firmante       varchar(13),
    fecha_emision       date,
    fecha_pago          date        not null,       -- FECVTO: al día o diferido
    importe             numeric(14,2) not null check (importe > 0),
    moneda              varchar(3)  not null default 'ARS' check (moneda in ('ARS','USD')),
    es_echeq            boolean     not null default false,
    -- origen (de dónde entró un cheque de tercero):
    cliente_id          uuid references clientes(id),
    recibo_id           uuid references recibos(id) on delete set null,
    -- destino (según estado):
    proveedor_id        uuid references proveedores(id),
    orden_pago_id       uuid references ordenes_pago(id) on delete set null,
    cuenta_id           uuid references cuentas_bancarias(id),
    banco_movimiento_id uuid,                        -- FK agregada abajo
    estado              varchar(12) not null
                        check (estado in ('en_cartera','depositado','acreditado',
                                          'endosado','rechazado','anulado',
                                          'emitido','debitado')),
    observaciones       varchar(200),
    creado_por          uuid references usuarios(id),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);
create index if not exists idx_cheques_tenant       on cheques(tenant_id);
create index if not exists idx_cheques_estado       on cheques(tenant_id, estado);
create index if not exists idx_cheques_fecha_pago   on cheques(tenant_id, fecha_pago);
create index if not exists idx_cheques_cliente      on cheques(cliente_id);
create index if not exists idx_cheques_proveedor    on cheques(proveedor_id);
create index if not exists idx_cheques_cuenta       on cheques(cuenta_id);
create index if not exists idx_cheques_recibo       on cheques(recibo_id);
create index if not exists idx_cheques_orden_pago   on cheques(orden_pago_id);

-- ============================================================================
-- 3. Cabecera de import de extracto (trazabilidad de conciliación)
-- ============================================================================
create table if not exists extracto_imports (
    id                 uuid primary key default gen_random_uuid(),
    tenant_id          uuid        not null references tenants(id) on delete cascade,
    cuenta_id          uuid        not null references cuentas_bancarias(id) on delete cascade,
    nombre_archivo     varchar(200),
    filas_total        integer     not null default 0,
    filas_conciliadas  integer     not null default 0,
    fecha_import       timestamptz not null default now(),
    creado_por         uuid references usuarios(id)
);
create index if not exists idx_extracto_imports_cuenta on extracto_imports(cuenta_id);
create index if not exists idx_extracto_imports_tenant on extracto_imports(tenant_id);

-- ============================================================================
-- 4. Movimientos bancarios (signo por tipo; depósito/débito de cheques)
-- ============================================================================
create table if not exists banco_movimientos (
    id                 uuid primary key default gen_random_uuid(),
    tenant_id          uuid        not null references tenants(id) on delete cascade,
    cuenta_id          uuid        not null references cuentas_bancarias(id) on delete cascade,
    fecha              date        not null default current_date,
    tipo               varchar(18) not null
                       check (tipo in ('deposito','extraccion','transferencia_in',
                                       'transferencia_out','debito','credito',
                                       'comision','ajuste_positivo','ajuste_negativo')),
    importe            numeric(14,2) not null check (importe > 0),  -- el signo lo da `tipo`
    descripcion        varchar(120),
    referencia         varchar(60),
    cheque_id          uuid references cheques(id) on delete set null,
    conciliado         boolean     not null default false,
    fecha_conciliacion date,
    extracto_import_id uuid references extracto_imports(id) on delete set null,
    origen             varchar(8)  not null default 'manual'
                       check (origen in ('manual','cheque','import','sistema')),
    creado_por         uuid references usuarios(id),
    created_at         timestamptz not null default now()
);
create index if not exists idx_banco_mov_cuenta on banco_movimientos(tenant_id, cuenta_id, fecha);
create index if not exists idx_banco_mov_cheque on banco_movimientos(cheque_id);
create index if not exists idx_banco_mov_import on banco_movimientos(extracto_import_id);

-- FK circular cheques.banco_movimiento_id → banco_movimientos.id (ahora que existe)
do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'cheques_banco_movimiento_id_fkey'
    ) then
        alter table cheques
            add constraint cheques_banco_movimiento_id_fkey
            foreign key (banco_movimiento_id) references banco_movimientos(id) on delete set null;
    end if;
end $$;
create index if not exists idx_cheques_banco_mov on cheques(banco_movimiento_id);

-- ============================================================================
-- 5. Bitácora de estados del cheque (auditoría inmutable)
-- ============================================================================
create table if not exists cheque_eventos (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid        not null references tenants(id) on delete cascade,
    cheque_id           uuid        not null references cheques(id) on delete cascade,
    fecha               date        not null default current_date,
    estado_desde        varchar(12),
    estado_hasta        varchar(12) not null,
    detalle             varchar(200),
    banco_movimiento_id uuid references banco_movimientos(id) on delete set null,
    creado_por          uuid references usuarios(id),
    created_at          timestamptz not null default now()
);
create index if not exists idx_cheque_eventos_cheque on cheque_eventos(cheque_id);
create index if not exists idx_cheque_eventos_tenant on cheque_eventos(tenant_id);

-- ============================================================================
-- 6. Módulo de permisos `bancos` para roles de sistema existentes
--    (ESPEJO de app/core/permisos.py — matriz F8):
--      admin/gerente → anular · cajero → editar · consulta → ver · vendedor → (sin acceso)
-- ============================================================================
insert into rol_permisos (rol_id, tenant_id, modulo, accion)
select r.id, r.tenant_id, 'bancos', p.accion
from roles r
join (values
    ('admin','anular'),
    ('gerente','anular'),
    ('cajero','editar'),
    ('consulta','ver')
) as p(codigo, accion) on p.codigo = r.codigo
where r.es_sistema
on conflict (rol_id, modulo) do nothing;

-- ============================================================================
-- 7. RLS (deny-all, segunda defensa — patrón 005)
-- ============================================================================
alter table cuentas_bancarias enable row level security;
alter table cheques           enable row level security;
alter table extracto_imports  enable row level security;
alter table banco_movimientos enable row level security;
alter table cheque_eventos    enable row level security;
