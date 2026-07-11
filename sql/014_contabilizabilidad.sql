-- 014 — Mini-fase CONTABILIZABILIDAD (pre-F9 Contabilidad).
-- Diseño en docs/DISENO-CONTABILIDAD.md. Aditiva e idempotente; segura de
-- aplicar sola (el backend viejo no lee estas columnas). Objetivo: que todo
-- documento operativo sea (a) inmutable — las anulaciones marcan, no borran —,
-- (b) valorizable — costo sellado en el kardex — y (c) mapeable a cuentas —
-- contrapartida financiera identificada (medio + cuenta bancaria).
--
-- Auditoría 2026-07-10 que originó esto: anular recibo/OP/NC borraba las
-- imputaciones físicamente; caja/retenciones/cierres/bancos tenían DELETE
-- físico; el kardex era físico puro (sin costo); ventas/compras CONTADO de
-- gestión no registraban medio; transferencias sin cuenta bancaria.

-- ============================================================================
-- 1. Anulaciones no destructivas: sello anulado_at/anulado_por
--    (el estado 'anulado/a' ya existía donde aplica; acá se agrega la FECHA
--    CIERTA de la reversión, que un asiento retroactivo necesita)
-- ============================================================================
alter table recibos              add column if not exists anulado_at  timestamptz;
alter table recibos              add column if not exists anulado_por uuid references usuarios(id);
alter table imputaciones         add column if not exists anulado_at  timestamptz;
alter table imputaciones         add column if not exists anulado_por uuid references usuarios(id);
alter table ordenes_pago         add column if not exists anulado_at  timestamptz;
alter table ordenes_pago         add column if not exists anulado_por uuid references usuarios(id);
alter table compras              add column if not exists anulado_at  timestamptz;
alter table compras              add column if not exists anulado_por uuid references usuarios(id);
alter table imputaciones_compras add column if not exists anulado_at  timestamptz;
alter table imputaciones_compras add column if not exists anulado_por uuid references usuarios(id);
alter table caja_movimientos     add column if not exists anulado_at  timestamptz;
alter table caja_movimientos     add column if not exists anulado_por uuid references usuarios(id);
alter table retenciones          add column if not exists anulado_at  timestamptz;
alter table retenciones          add column if not exists anulado_por uuid references usuarios(id);
alter table caja_cierres         add column if not exists anulado_at  timestamptz;
alter table caja_cierres         add column if not exists anulado_por uuid references usuarios(id);
alter table banco_movimientos    add column if not exists anulado_at  timestamptz;
alter table banco_movimientos    add column if not exists anulado_por uuid references usuarios(id);

-- Reabrir caja ahora MARCA el cierre (no lo borra): la unicidad por fecha
-- pasa a ignorar cierres anulados para permitir re-cerrar el mismo día.
drop index if exists uq_caja_cierres_sucursal;
create unique index if not exists uq_caja_cierres_sucursal
    on caja_cierres(tenant_id, sucursal_id, fecha)
    where sucursal_id is not null and anulado_at is null;
drop index if exists uq_caja_cierres_global;
create unique index if not exists uq_caja_cierres_global
    on caja_cierres(tenant_id, fecha)
    where sucursal_id is null and anulado_at is null;

-- Rechazo de cheque: deja de reescribir recibos.total. El importe reabierto
-- se acumula acá y el "a cuenta" disponible pasa a ser
-- total − aplicado − rechazado_total (el documento original queda intacto).
alter table recibos add column if not exists
    rechazado_total numeric(14,2) not null default 0;

-- ============================================================================
-- 2. Kardex valorizable: costo unitario NETO de IVA y en ARS, sellado al
--    momento del movimiento. NULL = movimiento histórico sin costo sellado
--    (valuación por costo de reposición solamente). Compras sellan el costo
--    REAL del documento (importe_neto/cantidad); el resto, el costo vigente
--    del artículo normalizado (neteo IVA + conversión USD por cotización).
-- ============================================================================
alter table stock_movimientos add column if not exists
    costo_unitario numeric(14,4);

-- ============================================================================
-- 3. Contrapartida financiera identificable
-- ============================================================================
-- medio='transferencia' (y tarjeta/MP si se quiere) puede señalar CONTRA QUÉ
-- cuenta bancaria fue — sin esto el motor contable no sabe a qué Banco asentar
alter table recibo_medios     add column if not exists
    cuenta_bancaria_id uuid references cuentas_bancarias(id);
alter table orden_pago_medios add column if not exists
    cuenta_bancaria_id uuid references cuentas_bancarias(id);
alter table venta_medios      add column if not exists
    cuenta_bancaria_id uuid references cuentas_bancarias(id);
alter table caja_movimientos  add column if not exists
    cuenta_bancaria_id uuid references cuentas_bancarias(id);

-- Compras CONTADO de gestión: medios de pago del documento (espejo de
-- venta_medios de la 009). Sin filas = comportamiento histórico (la planilla
-- de caja NO las asume efectivo — a diferencia de ventas — para no alterar
-- planillas ya selladas por cierres).
create table if not exists compra_medios (
    id                 uuid primary key default gen_random_uuid(),
    tenant_id          uuid          not null references tenants(id) on delete cascade,
    compra_id          uuid          not null references compras(id) on delete cascade,
    medio              varchar(15)   not null check (medio in
                       ('efectivo','transferencia','cheque','tarjeta','mercadopago','otro')),
    importe            numeric(14,2) not null check (importe > 0),
    cuenta_bancaria_id uuid references cuentas_bancarias(id),
    referencia         varchar(60),
    created_at         timestamptz   not null default now()
);
-- índice por el FK solo (regla selectin, CLAUDE.md §6)
create index if not exists idx_compra_medios_compra on compra_medios(compra_id);

-- Fecha de corte del saldo inicial de una cuenta bancaria (el asiento de
-- apertura del motor contable necesita saber "saldo inicial ¿a qué fecha?")
alter table cuentas_bancarias add column if not exists
    saldo_inicial_fecha date;

-- ============================================================================
-- 4. RLS deny-all para la tabla nueva (segunda defensa, patrón 005..013)
-- ============================================================================
alter table compra_medios enable row level security;
