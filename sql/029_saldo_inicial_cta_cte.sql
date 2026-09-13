-- 029 — Saldo inicial de cuenta corriente (docs/DISENO-CONTABILIDAD.md §7,
-- bloqueante de la auditoría 2026-09-12). Aditiva e idempotente. Sin tablas
-- nuevas (NO hace falta re-aplicar la 005): una columna en cada catálogo de
-- tipos, la clase nueva en los CHECK y 4 filas de seed.
--
-- Por qué: la cta. cte. «arrancaba en cero» y no había vehículo para cargar
-- la deuda viva de un cliente/proveedor migrado sin pasar por un documento
-- fiscal (ARCA + libro IVA). El saldo inicial es un documento INTERNO que
-- participa de la cta. cte. y de nada más.
--
-- OJO deploy: el backend nuevo lee `cta_cte` en los catálogos → la 029 va
-- ANTES del push (un SELECT del modelo contra la DB sin migrar revienta en
-- TODOS los listados de ventas/compras, no solo en la feature nueva).

-- 1. «participa en cta. cte.» — antes se usaba `fiscal` como proxy
alter table tipos_comprobante
    add column if not exists cta_cte boolean not null default false;
alter table tipos_comprobante_compra
    add column if not exists cta_cte boolean not null default false;

update tipos_comprobante        set cta_cte = true where fiscal;
update tipos_comprobante_compra set cta_cte = true where fiscal;

-- Invariante: todo fiscal participa de la cta. cte. Sin esto, un tipo fiscal
-- sembrado a futuro sin cta_cte=true desaparecería EN SILENCIO de saldos y
-- morosidad (los lectores ya no filtran por fiscal).
alter table tipos_comprobante drop constraint if exists tipos_comprobante_fiscal_cta_cte_check;
alter table tipos_comprobante add constraint tipos_comprobante_fiscal_cta_cte_check
    check (not fiscal or cta_cte);
alter table tipos_comprobante_compra
    drop constraint if exists tipos_comprobante_compra_fiscal_cta_cte_check;
alter table tipos_comprobante_compra add constraint tipos_comprobante_compra_fiscal_cta_cte_check
    check (not fiscal or cta_cte);

-- 2. clase nueva en los CHECK (varchar(13): 'saldo_inicial' son 13 chars)
alter table tipos_comprobante drop constraint if exists tipos_comprobante_clase_check;
alter table tipos_comprobante add constraint tipos_comprobante_clase_check check (clase in
    ('factura','nota_debito','nota_credito','presupuesto','remito','recibo','saldo_inicial'));

alter table tipos_comprobante_compra
    drop constraint if exists tipos_comprobante_compra_clase_check;
alter table tipos_comprobante_compra add constraint tipos_comprobante_compra_clase_check
    check (clase in ('factura','nota_debito','nota_credito','remito','saldo_inicial'));

-- 3. seed: dos sentidos por circuito
insert into tipos_comprobante (codigo, descripcion, letra, codigo_arca, clase, signo_cta_cte, fiscal, cta_cte) values
    ('SAL', 'Saldo inicial deudor',  'X', null, 'saldo_inicial',  1, false, true),
    ('SAF', 'Saldo inicial a favor', 'X', null, 'saldo_inicial', -1, false, true)
on conflict (codigo) do nothing;

insert into tipos_comprobante_compra (codigo, descripcion, letra, clase, signo_cta_cte, fiscal, cta_cte) values
    ('SALP', 'Saldo inicial a pagar',  'X', 'saldo_inicial',  1, false, true),
    ('SAFP', 'Saldo inicial a favor',  'X', 'saldo_inicial', -1, false, true)
on conflict (codigo) do nothing;

-- Verificación:
--   select codigo, clase, signo_cta_cte, fiscal, cta_cte from tipos_comprobante order by 1;
--   → SAL/SAF con cta_cte y sin fiscal; PRE/REM/REC con cta_cte=false; fiscales true/true
