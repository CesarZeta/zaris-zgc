-- 008 — Fase 5: Caja e IVA.
-- Espejo del legacy: CONC_CAJ (conceptos de caja con entrada/salida), MOVIM
-- (movimientos manuales de caja), SALCAJA (cierre/arqueo diario), RET_CLI y
-- RET_PROV (retenciones sufridas/practicadas, registro básico). Los libros de
-- IVA NO tienen tabla propia: son reportes sobre comprobantes (ventas, con
-- comprobante_alicuotas de la 006) y compras (007, ítems por tasa), como el
-- _ADMINC del legacy era un auxiliar regenerable.
--
-- La planilla de caja diaria también es un reporte: cobranzas (recibos) +
-- pagos (OP) + ventas contado del día + movimientos manuales de esta 008.
-- Solo el CIERRE del día se materializa (caja_cierres, con arqueo).

-- ===== Conceptos de caja (CONC_CAJ: CCONC/NCONC/ENT_SAL) =====
create table if not exists conceptos_caja (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    nombre     varchar(40) not null,
    tipo       varchar(7)  not null check (tipo in ('entrada','salida')),
    activo     boolean     not null default true,
    created_at timestamptz not null default now(),
    unique (tenant_id, nombre)
);
create index if not exists idx_conceptos_caja_tenant on conceptos_caja(tenant_id);

-- ===== Movimientos manuales de caja (MOVIM) =====
-- tipo sellado desde el concepto al crear (si el concepto se edita, la
-- historia no cambia). Solo movimientos MANUALES: cobranzas/pagos/ventas ya
-- viven en sus tablas y la planilla los agrega en el reporte.
create table if not exists caja_movimientos (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid          not null references tenants(id) on delete cascade,
    sucursal_id uuid          references sucursales(id),
    fecha       date          not null default current_date,
    concepto_id uuid          not null references conceptos_caja(id),
    tipo        varchar(7)    not null check (tipo in ('entrada','salida')),
    medio       varchar(15)   not null default 'efectivo' check (medio in
                ('efectivo','transferencia','cheque','tarjeta','mercadopago','otro')),
    importe     numeric(14,2) not null check (importe > 0),
    descripcion varchar(120),
    creado_por  uuid          references usuarios(id),
    created_at  timestamptz   not null default now()
);
create index if not exists idx_caja_mov_fecha on caja_movimientos(tenant_id, fecha desc);
create index if not exists idx_caja_mov_sucursal on caja_movimientos(tenant_id, sucursal_id, fecha);

-- ===== Cierres de caja (SALCAJA + arqueo) =====
-- Totales SELLADOS al cerrar (la planilla se recalcula; el cierre es la foto
-- firmada). saldo_final = saldo_inicial + entradas - salidas (solo efectivo).
-- diferencia = efectivo_contado (arqueo físico) - saldo_final.
create table if not exists caja_cierres (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid          not null references tenants(id) on delete cascade,
    sucursal_id      uuid          references sucursales(id),
    fecha            date          not null,
    saldo_inicial    numeric(14,2) not null default 0,
    entradas         numeric(14,2) not null default 0,
    salidas          numeric(14,2) not null default 0,
    saldo_final      numeric(14,2) not null default 0,
    efectivo_contado numeric(14,2),
    diferencia       numeric(14,2),
    observaciones    text,
    cerrado_por      uuid          references usuarios(id),
    created_at       timestamptz   not null default now()
);
create unique index if not exists uq_caja_cierres_sucursal
    on caja_cierres(tenant_id, sucursal_id, fecha) where sucursal_id is not null;
create unique index if not exists uq_caja_cierres_global
    on caja_cierres(tenant_id, fecha) where sucursal_id is null;

-- ===== Retenciones — registro básico (RET_CLI / RET_PROV) =====
-- sufrida: un cliente nos retuvo al cobrarle (certificado que nos entrega).
-- practicada: nosotros retuvimos al proveedor al pagarle (OP).
-- Referencias opcionales al recibo/OP; el resumen del contador sale de acá.
create table if not exists retenciones (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid          not null references tenants(id) on delete cascade,
    tipo            varchar(10)   not null check (tipo in ('sufrida','practicada')),
    regimen         varchar(10)   not null check (regimen in ('IVA','IIBB','Ganancias','SUSS','otro')),
    fecha           date          not null default current_date,
    importe         numeric(14,2) not null check (importe > 0),
    nro_certificado varchar(30),
    cliente_id      uuid          references clientes(id),
    proveedor_id    uuid          references proveedores(id),
    recibo_id       uuid          references recibos(id) on delete set null,
    orden_pago_id   uuid          references ordenes_pago(id) on delete set null,
    descripcion     varchar(120),
    creado_por      uuid          references usuarios(id),
    created_at      timestamptz   not null default now(),
    check (
        (tipo = 'sufrida'    and proveedor_id is null and orden_pago_id is null) or
        (tipo = 'practicada' and cliente_id   is null and recibo_id     is null)
    )
);
create index if not exists idx_retenciones_fecha on retenciones(tenant_id, fecha desc);

-- ===== tipos_comprobante_compra: código ARCA para libro/CITI de compras =====
-- (ventas ya lo tiene desde la 006)
alter table tipos_comprobante_compra add column if not exists codigo_arca smallint;
update tipos_comprobante_compra set codigo_arca = v.codigo_arca
from (values
    ('FCA', 1), ('FCB', 6), ('FCC', 11),
    ('NDA', 2), ('NDB', 7), ('NDC', 12),
    ('NCA', 3), ('NCB', 8), ('NCC', 13)
) as v(codigo, codigo_arca)
where tipos_comprobante_compra.codigo = v.codigo;

-- ===== RLS deny-all (segunda defensa, patrón 005/006/007) =====
do $$
declare
    t text;
begin
    foreach t in array array['conceptos_caja','caja_movimientos','caja_cierres','retenciones']
    loop
        execute format('alter table public.%I enable row level security', t);
    end loop;
end $$;
