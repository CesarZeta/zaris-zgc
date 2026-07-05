-- 007 — Fase 4: Compras y Proveedores.
-- Espejo del legacy: PROVEEDO (rol proveedor -> satélite BUE), ART_PROV
-- (articulo_proveedores: costos por proveedor -> comparativo), COMPRASM/COMPRASD
-- (compras + items), REMITOPM/REMITOPD (remito proveedor = compra clase remito),
-- RECIBOPM (ordenes_pago). Todo con tenant_id + UUID, patrón de la 006.
--
-- Diferencia clave con Ventas: el comprobante de compra lo emite EL PROVEEDOR
-- (numeración ajena, carga manual, sin ARCA). Circuito: borrador -> registrar
-- (stock + costos + cta. cte.) -> anulable con reversión mientras no tenga pagos.

-- ===== Rol: proveedor (satélite de la BUE, patrón clientes de la 002) =====
-- condicion_compra_id reusa el catálogo condiciones_venta: son plazos de pago
-- genéricos ("Contado", "30 días") — el legacy usaba la misma CONDICIO para ambos.
create table if not exists proveedores (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid        not null references tenants(id) on delete cascade,
    entidad_id          uuid        not null references entidades(id),
    codigo              varchar(10),                  -- CPROV del legacy; lo trae el migrador
    condicion_compra_id uuid references condiciones_venta(id),
    rubro               varchar(40),                  -- RUBRO del legacy (texto libre)
    observaciones       text,
    activo              boolean     not null default true,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    unique (tenant_id, entidad_id),                   -- una entidad es proveedor UNA vez por tenant
    unique (tenant_id, codigo)
);
create index if not exists idx_proveedores_tenant on proveedores(tenant_id);

-- ===== Artículo × proveedor (ART_PROV): base del comparativo de precios =====
-- costo = precio de lista unitario NETO (sin IVA) del proveedor; el costo real
-- comparable se deriva aplicando las bonificaciones en cadena.
create table if not exists articulo_proveedores (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid          not null references tenants(id) on delete cascade,
    articulo_id      uuid          not null references articulos(id) on delete cascade,
    proveedor_id     uuid          not null references proveedores(id) on delete cascade,
    codigo_proveedor varchar(30),                     -- CODSPROV: código del artículo en el proveedor
    costo            numeric(14,4) not null default 0,
    bonif_1          numeric(5,2)  not null default 0,
    bonif_2          numeric(5,2)  not null default 0,
    bonif_3          numeric(5,2)  not null default 0,
    ultima_compra    date,                            -- ULT_FECHA: se sella al registrar compras
    created_at       timestamptz   not null default now(),
    updated_at       timestamptz   not null default now(),
    unique (tenant_id, articulo_id, proveedor_id)
);
create index if not exists idx_artprov_articulo on articulo_proveedores(tenant_id, articulo_id);
create index if not exists idx_artprov_proveedor on articulo_proveedores(tenant_id, proveedor_id);

-- Proveedor habitual del artículo (campo legacy diferido en Fase 2)
alter table articulos add column if not exists
    proveedor_habitual_id uuid references proveedores(id);

-- ===== Catálogo global de tipos de comprobante de compra (sin tenant) =====
-- Separado de tipos_comprobante (ventas): acá la letra la trae el documento del
-- proveedor. Letra A discrimina IVA (crédito fiscal); B/C/X van por total.
-- signo_cta_cte: +1 suma deuda nuestra (FC/ND), -1 crédito a favor (NC).
create table if not exists tipos_comprobante_compra (
    codigo        varchar(5)  primary key,
    descripcion   varchar(40) not null,
    letra         char(1)     not null check (letra in ('A','B','C','X')),
    clase         varchar(13) not null check (clase in
                  ('factura','nota_debito','nota_credito','remito')),
    signo_cta_cte smallint    not null default 0 check (signo_cta_cte in (-1, 0, 1)),
    fiscal        boolean     not null default false   -- entra al libro IVA compras (Fase 5)
);

insert into tipos_comprobante_compra (codigo, descripcion, letra, clase, signo_cta_cte, fiscal) values
    ('FCA', 'Factura de Compra A', 'A', 'factura',      1, true),
    ('FCB', 'Factura de Compra B', 'B', 'factura',      1, true),
    ('FCC', 'Factura de Compra C', 'C', 'factura',      1, true),
    ('NDA', 'N. Débito Compra A',  'A', 'nota_debito',  1, true),
    ('NDB', 'N. Débito Compra B',  'B', 'nota_debito',  1, true),
    ('NDC', 'N. Débito Compra C',  'C', 'nota_debito',  1, true),
    ('NCA', 'N. Crédito Compra A', 'A', 'nota_credito',-1, true),
    ('NCB', 'N. Crédito Compra B', 'B', 'nota_credito',-1, true),
    ('NCC', 'N. Crédito Compra C', 'C', 'nota_credito',-1, true),
    ('REMP','Remito de Proveedor', 'X', 'remito',       0, false)
on conflict (codigo) do nothing;

-- ===== Compras (COMPRASM): el comprobante del proveedor, carga manual =====
-- punto_venta/numero son los del documento AJENO (PREFIJO/NCOMP del legacy).
-- Snapshot del proveedor al registrar (patrón receptor de la 006).
-- redondeo: ajuste de centavos para que el total calce con el papel.
create table if not exists compras (
    id                  uuid primary key default gen_random_uuid(),
    tenant_id           uuid        not null references tenants(id) on delete cascade,
    tipo_codigo         varchar(5)  not null references tipos_comprobante_compra(codigo),
    letra               char(1)     not null,
    punto_venta         integer     not null default 0 check (punto_venta between 0 and 99999),
    numero              bigint      not null default 0,
    fecha               date        not null default current_date,
    periodo_iva         date,                        -- MESIVA: 1° del mes p/ libro IVA compras
    proveedor_id        uuid        not null references proveedores(id),
    proveedor_nombre    varchar(120) not null default '',
    proveedor_cuit      varchar(11),
    proveedor_condicion_iva varchar(2) not null default 'RI'
                        check (proveedor_condicion_iva in ('RI','MT','EX','CF')),
    contado             boolean     not null default false,
    condicion_compra_id uuid references condiciones_venta(id),
    condicion_desc      varchar(60),
    deposito_id         uuid references depositos(id),
    actualiza_stock     boolean     not null default true,
    actualiza_costos    boolean     not null default true,
    neto_gravado        numeric(14,2) not null default 0,
    no_gravado          numeric(14,2) not null default 0,
    exento              numeric(14,2) not null default 0,
    iva                 numeric(14,2) not null default 0,
    percepcion_iva      numeric(14,2) not null default 0,   -- IMPPER
    percepcion_iibb     numeric(14,2) not null default 0,   -- INGBRU
    impuestos_internos  numeric(14,2) not null default 0,   -- IMPINT
    otros_tributos      numeric(14,2) not null default 0,   -- OTROS
    redondeo            numeric(6,2)  not null default 0,
    total               numeric(14,2) not null default 0,
    saldo               numeric(14,2) not null default 0,
    estado              varchar(10) not null default 'borrador'
                        check (estado in ('borrador','registrado','anulado')),
    compra_asociada_id  uuid references compras(id),  -- NC/ND -> factura de compra
    observaciones       text,
    registrado_at       timestamptz,
    registrado_por      uuid references usuarios(id),
    creado_por          uuid references usuarios(id),
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);
-- el mismo comprobante del proveedor no se carga dos veces (salvo anulado)
create unique index if not exists uq_compras_comprobante
    on compras(tenant_id, proveedor_id, tipo_codigo, punto_venta, numero)
    where estado <> 'anulado';
create index if not exists idx_compras_lista
    on compras(tenant_id, fecha desc, created_at desc);
create index if not exists idx_compras_proveedor on compras(tenant_id, proveedor_id);
create index if not exists idx_compras_saldo
    on compras(tenant_id, proveedor_id) where saldo <> 0;

-- ===== Ítems (COMPRASD): costo_unitario NETO si letra A; FINAL si B/C =====
create table if not exists compra_items (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid          not null references tenants(id) on delete cascade,
    compra_id      uuid          not null references compras(id) on delete cascade,
    orden          smallint      not null default 0,
    articulo_id    uuid          references articulos(id),
    variante_id    uuid          references articulo_variantes(id),
    codigo         varchar(20),
    descripcion    varchar(120)  not null,
    cantidad       numeric(14,3) not null default 1,
    costo_unitario numeric(14,4) not null default 0,
    bonif_1        numeric(5,2)  not null default 0,   -- bonifs en cadena del proveedor
    bonif_2        numeric(5,2)  not null default 0,
    tasa_iva       numeric(5,2)  not null default 21,
    importe_neto   numeric(14,2) not null default 0,
    importe_iva    numeric(14,2) not null default 0,
    importe_total  numeric(14,2) not null default 0
);
create index if not exists idx_compra_items on compra_items(tenant_id, compra_id);

-- ===== Vencimientos de la compra (cuentas a pagar) =====
create table if not exists compra_vencimientos (
    id        uuid primary key default gen_random_uuid(),
    tenant_id uuid          not null references tenants(id) on delete cascade,
    compra_id uuid          not null references compras(id) on delete cascade,
    nro_cuota smallint      not null default 1,
    fecha_vto date          not null,
    importe   numeric(14,2) not null,
    unique (compra_id, nro_cuota)
);

-- ===== Numeración de documentos internos de Compras (OP) =====
-- Sin punto de venta: la OP es un documento interno del tenant.
create table if not exists numeracion_compras (
    id        uuid primary key default gen_random_uuid(),
    tenant_id uuid       not null references tenants(id) on delete cascade,
    tipo      varchar(5) not null,
    ultimo    bigint     not null default 0,
    unique (tenant_id, tipo)
);

-- ===== Órdenes de pago (RECIBOPM): espejo de recibos de la 006 =====
create table if not exists ordenes_pago (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid          not null references tenants(id) on delete cascade,
    numero           bigint        not null,
    fecha            date          not null default current_date,
    proveedor_id     uuid          not null references proveedores(id),
    proveedor_nombre varchar(120)  not null,
    total            numeric(14,2) not null,
    aplicado         numeric(14,2) not null default 0,  -- suma imputada (resto = a cuenta)
    estado           varchar(10)   not null default 'emitida'
                     check (estado in ('emitida','anulada')),
    observaciones    text,
    creado_por       uuid          references usuarios(id),
    created_at       timestamptz   not null default now(),
    unique (tenant_id, numero)
);
create index if not exists idx_op_proveedor on ordenes_pago(tenant_id, proveedor_id);

create table if not exists orden_pago_medios (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid          not null references tenants(id) on delete cascade,
    orden_pago_id uuid          not null references ordenes_pago(id) on delete cascade,
    medio         varchar(15)   not null check (medio in
                  ('efectivo','transferencia','cheque','tarjeta','mercadopago','otro')),
    importe       numeric(14,2) not null,
    referencia    varchar(60)   -- nro. cheque / nro. operación
);

-- ===== Imputaciones de compras: qué pago/crédito cancela qué compra =====
-- Origen: una OP o una NC de compra (exactamente uno) — patrón imputaciones 006.
create table if not exists imputaciones_compras (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid          not null references tenants(id) on delete cascade,
    proveedor_id  uuid          not null references proveedores(id),
    orden_pago_id uuid          references ordenes_pago(id) on delete cascade,
    credito_id    uuid          references compras(id) on delete cascade,
    compra_id     uuid          not null references compras(id) on delete cascade,
    importe       numeric(14,2) not null check (importe > 0),
    fecha         date          not null default current_date,
    creado_por    uuid          references usuarios(id),
    created_at    timestamptz   not null default now(),
    check (num_nonnulls(orden_pago_id, credito_id) = 1)
);
create index if not exists idx_impcompras_compra on imputaciones_compras(tenant_id, compra_id);
create index if not exists idx_impcompras_op on imputaciones_compras(tenant_id, orden_pago_id);

-- ===== RLS deny-all (segunda defensa, patrón 005/006) =====
do $$
declare
    t text;
begin
    foreach t in array array['proveedores','articulo_proveedores',
        'tipos_comprobante_compra','compras','compra_items','compra_vencimientos',
        'numeracion_compras','ordenes_pago','orden_pago_medios','imputaciones_compras']
    loop
        execute format('alter table public.%I enable row level security', t);
    end loop;
end $$;
