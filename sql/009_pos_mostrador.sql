-- 009 — Fase 6: POS Mostrador Web.
-- El POS vende con la MISMA maquinaria de Fase 3 (comprobantes + ARCA + stock):
-- acá solo se agrega lo que el mostrador necesita alrededor:
--   pos_cajas     → config de cada caja física (PV que factura, depósito que
--                   descarga, lista de precios, ancho del ticket térmico).
--   pos_sesiones  → turno de cajero (apertura con fondo → cierre con arqueo).
--                   Totales SELLADOS al cerrar; mientras está abierta el
--                   resumen se calcula de venta_medios (reporte, no tabla).
--   venta_medios  → medios de pago de una venta CONTADO (el hueco que la
--                   planilla de caja de Fase 5 dejó documentado: "las ventas
--                   de contado se asumen efectivo hasta que el POS registre
--                   medios por venta"). Signo por tipo de comprobante
--                   (FA/ND entra, NC devuelve) — importe siempre positivo.

-- ===== Cajas físicas =====
create table if not exists pos_cajas (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid         not null references tenants(id) on delete cascade,
    sucursal_id    uuid         references sucursales(id),
    nombre         varchar(40)  not null,
    punto_venta_id uuid         not null references puntos_venta(id),
    deposito_id    uuid         references depositos(id),
    lista_precios  smallint     not null default 1 check (lista_precios between 1 and 4),
    ancho_ticket   smallint     not null default 80 check (ancho_ticket in (58, 80)),
    activa         boolean      not null default true,
    created_at     timestamptz  not null default now(),
    unique (tenant_id, nombre)
);
create index if not exists idx_pos_cajas_tenant on pos_cajas(tenant_id);

-- ===== Sesiones de caja (turno de cajero) =====
-- Una sola sesión abierta por caja (unique parcial). El cierre sella los
-- totales del turno: ventas por medio + efectivo teórico vs. contado.
create table if not exists pos_sesiones (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid          not null references tenants(id) on delete cascade,
    caja_id             uuid          not null references pos_cajas(id),
    cajero_id           uuid          not null references usuarios(id),
    estado              varchar(7)    not null default 'abierta' check (estado in ('abierta','cerrada')),
    fondo_inicial       numeric(14,2) not null default 0 check (fondo_inicial >= 0),
    abierta_at          timestamptz   not null default now(),
    cerrada_at          timestamptz,
    cantidad_tickets    integer,
    total_ventas        numeric(14,2),
    cobrado_efectivo    numeric(14,2),
    cobrado_tarjeta     numeric(14,2),
    cobrado_mercadopago numeric(14,2),
    cobrado_otros       numeric(14,2),
    efectivo_teorico    numeric(14,2),
    efectivo_contado    numeric(14,2),
    diferencia          numeric(14,2),
    observaciones       text,
    created_at          timestamptz   not null default now()
);
create unique index if not exists uq_pos_sesion_abierta
    on pos_sesiones(caja_id) where estado = 'abierta';
create index if not exists idx_pos_sesiones_tenant on pos_sesiones(tenant_id, abierta_at desc);

-- ===== Medios de pago de ventas contado =====
-- sum(importe) = comprobante.total (lo valida la app al vender). Para
-- efectivo el importe es lo APLICADO a la venta (el vuelto no entra acá).
create table if not exists venta_medios (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid          not null references tenants(id) on delete cascade,
    comprobante_id uuid          not null references comprobantes(id) on delete cascade,
    pos_sesion_id  uuid          references pos_sesiones(id),
    medio          varchar(15)   not null check (medio in
                   ('efectivo','transferencia','cheque','tarjeta','mercadopago','otro')),
    importe        numeric(14,2) not null check (importe > 0),
    referencia     varchar(60),
    created_at     timestamptz   not null default now()
);
create index if not exists idx_venta_medios_comprobante on venta_medios(comprobante_id);
create index if not exists idx_venta_medios_sesion on venta_medios(pos_sesion_id);

-- ===== comprobantes: sello de qué sesión POS lo emitió =====
alter table comprobantes add column if not exists
    pos_sesion_id uuid references pos_sesiones(id);
create index if not exists idx_comprobantes_pos_sesion on comprobantes(pos_sesion_id)
    where pos_sesion_id is not null;

-- ===== RLS deny-all (segunda defensa, patrón 005..008) =====
do $$
declare
    t text;
begin
    foreach t in array array['pos_cajas','pos_sesiones','venta_medios']
    loop
        execute format('alter table public.%I enable row level security', t);
    end loop;
end $$;
