-- 011 — LOTE TÉCNICO: índices de performance (auditoría 2026-07-05).
-- Solo CREATE INDEX IF NOT EXISTS + pg_trgm: segura de aplicar sola, no
-- cambia el modelo (un backend viejo sigue funcionando igual).
--
-- Motivos (auditoría de endpoints, ROADMAP § LOTE TÉCNICO):
--   1. Los loaders selectin de SQLAlchemy emiten `where fk in (...)` SIN
--      tenant_id: un índice (tenant_id, fk) NO les sirve (regla §6 del
--      CLAUDE.md). Items de ventas/compras y medios de recibos/OP hoy
--      escanean la tabla completa en cada listado.
--   2. Búsquedas ILIKE '%…%' (maestros, typeahead, POS): GIN pg_trgm.
--      Multicolumna porque el filtro es un OR y el planner necesita índice
--      en TODAS las ramas para armar el BitmapOr.
--   3. Planilla de caja: recibos/órdenes de pago del día filtran por
--      (tenant_id, fecha) y hoy no hay índice por fecha.
--   4. Anuladas del POS: lookup de la NC espejo por comprobante_asociado_id
--      (parcial: casi todos los comprobantes lo tienen NULL).

-- ===== 1. FKs de hijos con loader selectin =====
-- (comprobante_alicuotas y *_vencimientos ya están cubiertos por sus UNIQUE
--  que arrancan por el FK; venta_medios ya los tiene de la 009.)
create index if not exists idx_comp_items_comprobante
    on comprobante_items(comprobante_id);
create index if not exists idx_compra_items_compra
    on compra_items(compra_id);
create index if not exists idx_recibo_medios_recibo
    on recibo_medios(recibo_id);
create index if not exists idx_op_medios_op
    on orden_pago_medios(orden_pago_id);

-- ===== 2. Búsqueda de texto (pg_trgm) =====
-- Disponible en Supabase y en el Postgres 17 local.
create extension if not exists pg_trgm;

-- entidades.aplicar_busqueda: OR razon_social / nombre_fantasia / email
create index if not exists idx_entidades_trgm on entidades
    using gin (razon_social gin_trgm_ops,
               nombre_fantasia gin_trgm_ops,
               email gin_trgm_ops);

-- articulos.aplicar_busqueda_articulos y GET /pos/buscar:
-- OR descripcion / codigo / codigo_barras
create index if not exists idx_articulos_trgm on articulos
    using gin (descripcion gin_trgm_ops,
               codigo gin_trgm_ops,
               codigo_barras gin_trgm_ops);

-- ===== 3. Planilla de caja (agregados del día) =====
create index if not exists idx_recibos_fecha
    on recibos(tenant_id, fecha);
create index if not exists idx_op_fecha
    on ordenes_pago(tenant_id, fecha);

-- ===== 4. Anuladas del POS (NC espejo por comprobante asociado) =====
create index if not exists idx_comprobantes_asociado
    on comprobantes(comprobante_asociado_id)
    where comprobante_asociado_id is not null;
