-- 019 — F12-b: perfil súper/estándar completo — pesables por etiqueta de balanza,
-- envases retornables y venta por departamento (DISENO-POS-PERFILES.md §1).
-- Aditiva e idempotente; segura de aplicar ANTES del backend nuevo (el viejo no la lee).
-- En prod: re-aplicar la 005 después (tabla nueva ⇒ RLS + revokes de PostgREST).

-- PLU corto que imprime la balanza (etiquetas EAN-13 prefijo 20-29). Único por
-- tenant; parcial: NULL = artículo sin código de balanza. Se guarda normalizado
-- sin ceros a la izquierda (la etiqueta lo trae zero-padded).
alter table articulos add column if not exists codigo_balanza varchar(6);
create unique index if not exists uq_articulos_codigo_balanza
    on articulos (tenant_id, codigo_balanza) where codigo_balanza is not null;

-- Config de etiquetas de balanza por tenant (una fila por tenant; ausencia o
-- habilitado=false = parsing apagado). Esquema clásico de balanzas (Kretz y
-- compatibles, drivers del legacy): P(2) + PLU(codigo_digitos) +
-- VALOR(10-codigo_digitos) + DV = 13 dígitos. El valor embebido es peso en
-- gramos o importe en centavos según valor_tipo.
create table if not exists pos_balanza_config (
    tenant_id       uuid        primary key references tenants(id) on delete cascade,
    habilitado      boolean     not null default true,
    prefijo         varchar(2)  not null default '20' check (prefijo ~ '^2[0-9]$'),
    valor_tipo      varchar(7)  not null default 'peso' check (valor_tipo in ('peso','importe')),
    codigo_digitos  smallint    not null default 5 check (codigo_digitos between 3 and 7),
    updated_at      timestamptz not null default now()
);
alter table pos_balanza_config enable row level security;
