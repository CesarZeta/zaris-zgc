-- 025 — F12-bis: Logística de entregas. Diseño en docs/DISENO-LOGISTICA-Y-DOMICILIOS.md §2.
-- Aditiva e idempotente. Rol transportista sobre la BUE (patrón vendedores/017),
-- entregas con domicilio SNAPSHOT (si el cliente se muda, la entrega histórica
-- no cambia) y hojas de ruta imprimibles. Regla de encuadre: el estado de
-- entrega NO toca el circuito fiscal ni la cta. cte. (logística solo registra
-- y ordena el reparto).
-- OJO deploy: el backend nuevo mapea estas tablas → la 025 va ANTES del push
-- (como la 017), y después se re-aplica la 005 (tablas nuevas ⇒ RLS deny-all).

-- ============================================================================
-- 1. Rol transportista sobre la BUE (patrón vendedores; sirve el fletero
--    externo con CUIT y el reparto propio — entidad = empleado/vehículo)
-- ============================================================================
create table if not exists transportistas (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid         not null references tenants(id) on delete cascade,
    entidad_id    uuid         not null references entidades(id),
    codigo        varchar(10),
    vehiculo      varchar(60),
    dominio       varchar(15),
    observaciones varchar(200),
    activo        boolean      not null default true,
    created_at    timestamptz  not null default now(),
    updated_at    timestamptz  not null default now()
);
create unique index if not exists uq_transportistas_entidad
    on transportistas(tenant_id, entidad_id);
create unique index if not exists uq_transportistas_codigo
    on transportistas(tenant_id, codigo) where codigo is not null;
-- índice por el FK solo (regla selectin, CLAUDE.md §6)
create index if not exists idx_transportistas_entidad on transportistas(entidad_id);

-- ============================================================================
-- 2. Hojas de ruta (documento del reparto: numeración por tenant, anulable
--    marcada — contrato 014)
-- ============================================================================
create table if not exists hojas_ruta (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid         not null references tenants(id) on delete cascade,
    numero           bigint       not null,
    fecha            date         not null default current_date,
    transportista_id uuid         not null references transportistas(id),
    sucursal_id      uuid references sucursales(id),
    estado           varchar(10)  not null default 'abierta'
                     check (estado in ('abierta','en_reparto','cerrada')),
    observaciones    varchar(200),
    anulado_at       timestamptz,
    anulado_por      uuid references usuarios(id),
    creado_por       uuid references usuarios(id),
    created_at       timestamptz  not null default now(),
    updated_at       timestamptz  not null default now()
);
create unique index if not exists uq_hojas_ruta_numero on hojas_ruta(tenant_id, numero);
create index if not exists idx_hojas_ruta_transportista on hojas_ruta(transportista_id);
create index if not exists idx_hojas_ruta_fecha on hojas_ruta(tenant_id, fecha);

-- ============================================================================
-- 3. Entregas: una por comprobante a entregar (remito o factura EMITIDOS).
--    Domicilio snapshot copiado de entidad_domicilios/entidades al crearla.
--    Estados: pendiente → asignada (en hoja) → en_reparto → entregada |
--    rechazada; reprogramada = terminal (la reemplaza una entrega nueva).
-- ============================================================================
create table if not exists entregas (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid         not null references tenants(id) on delete cascade,
    comprobante_id   uuid         not null references comprobantes(id),
    -- snapshot del destino (texto normalizado OSM o libre + lat/lon)
    destinatario     varchar(120) not null,
    domicilio        varchar(180) not null,
    localidad        varchar(60),
    telefono         varchar(30),
    latitud          numeric(10,7),
    longitud         numeric(10,7),
    fecha_programada date,
    transportista_id uuid references transportistas(id),
    hoja_ruta_id     uuid references hojas_ruta(id),
    orden            smallint     not null default 0,
    estado           varchar(12)  not null default 'pendiente'
                     check (estado in ('pendiente','asignada','en_reparto',
                                       'entregada','rechazada','reprogramada')),
    bultos           varchar(60),
    recibido_por     varchar(80),
    motivo_rechazo   varchar(200),
    observaciones    varchar(200),
    rendida_at       timestamptz,
    anulado_at       timestamptz,
    anulado_por      uuid references usuarios(id),
    creado_por       uuid references usuarios(id),
    created_at       timestamptz  not null default now(),
    updated_at       timestamptz  not null default now()
);
-- una sola entrega ACTIVA por comprobante (las rechazadas/reprogramadas/anuladas
-- no bloquean el reintento)
create unique index if not exists uq_entregas_comprobante_viva
    on entregas(comprobante_id)
    where anulado_at is null and estado in ('pendiente','asignada','en_reparto','entregada');
create index if not exists idx_entregas_comprobante on entregas(comprobante_id);
create index if not exists idx_entregas_hoja on entregas(hoja_ruta_id) where hoja_ruta_id is not null;
create index if not exists idx_entregas_estado on entregas(tenant_id, estado);

-- ============================================================================
-- 4. Módulo de permisos `logistica` para roles de sistema existentes
--    (ESPEJO de app/core/permisos.py — F12-bis):
--      admin/gerente → anular · consulta → ver · cajero/vendedor → (sin acceso)
--    Los tenants NUEVOS lo toman solos de ROLES_BASE (comprehensions).
-- ============================================================================
insert into rol_permisos (rol_id, tenant_id, modulo, accion)
select r.id, r.tenant_id, 'logistica', p.accion
from roles r
join (values
    ('admin','anular'),
    ('gerente','anular'),
    ('consulta','ver')
) as p(codigo, accion) on p.codigo = r.codigo
where r.es_sistema
on conflict (rol_id, modulo) do nothing;

-- ============================================================================
-- 5. RLS deny-all (segunda defensa, patrón 005..024)
-- ============================================================================
alter table transportistas enable row level security;
alter table hojas_ruta     enable row level security;
alter table entregas       enable row level security;
