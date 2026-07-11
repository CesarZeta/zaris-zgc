-- 022 — Lote de diferidos: sucursal en órdenes de pago + cache de resultados
-- del padrón ARCA (ROADMAP diferidos de F5 y F7).
-- Aditiva e idempotente; segura de aplicar ANTES del backend nuevo (el viejo no la lee).
-- En prod: re-aplicar la 005 después (tabla nueva ⇒ RLS + revokes de PostgREST).

-- Sucursal de la orden de pago (diferido F5: las OP entraban solo en la
-- planilla global). NULL = sin sucursal: sigue entrando solo en la global.
alter table ordenes_pago add column if not exists
    sucursal_id uuid references sucursales(id);

-- Cache de consultas al padrón ARCA (ws_sr_constancia_inscripcion). Una fila
-- por (tenant, cuit); espejo del DatosPadron del servicio. `modo` sellado:
-- si el tenant cambia de modo ARCA, la fila cacheada de otro modo no se usa.
create table if not exists padron_cache (
    id             uuid        primary key default gen_random_uuid(),
    tenant_id      uuid        not null references tenants(id) on delete cascade,
    cuit           varchar(11) not null,
    modo           varchar(13) not null,
    razon_social   text,
    tipo_persona   varchar(10) not null,
    condicion_iva  varchar(5)  not null,
    domicilio      text,
    localidad      text,
    provincia_id   smallint,
    codigo_postal  varchar(10),
    fuente         varchar(10) not null,
    consultado_at  timestamptz not null default now(),
    unique (tenant_id, cuit)
);
alter table padron_cache enable row level security;
