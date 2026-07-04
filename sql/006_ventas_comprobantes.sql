-- 006 — Fase 3: Ventas y Facturación Electrónica ARCA.
-- Diseño de cumplimiento en docs/FACTURACION-ARCA.md (leer antes de tocar esto).
-- Espejo del legacy: VENTASM/VENTASD (comprobante+items), TABLAIVA (alícuotas),
-- NUMEROS/PREFIJOS (numeración por punto de venta), VENCIC (vencimientos),
-- RECIBOSM (recibos), FE0004 (campos CAE). Todo con tenant_id + UUID.

-- ===== Puntos de venta (PREFIJOS del legacy; ELEC -> electronico) =====
create table if not exists puntos_venta (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    sucursal_id uuid        references sucursales(id),
    numero      integer     not null check (numero between 1 and 99999),
    descripcion varchar(60) not null default '',
    electronico boolean     not null default true,  -- habilitado como "Web Services" en ARCA
    activo      boolean     not null default true,
    created_at  timestamptz not null default now(),
    unique (tenant_id, numero)
);

-- ===== Catálogo global de tipos de comprobante (sin tenant) =====
-- codigo_arca: tabla de tipos de ARCA (1/6/11 facturas, 2/7/12 ND, 3/8/13 NC).
-- signo_cta_cte: +1 suma deuda (FA/ND), -1 genera crédito (NC), 0 no toca cta. cte.
create table if not exists tipos_comprobante (
    codigo        varchar(5)  primary key,
    descripcion   varchar(40) not null,
    letra         char(1)     not null check (letra in ('A','B','C','X')),
    codigo_arca   smallint,
    clase         varchar(13) not null check (clase in
                  ('factura','nota_debito','nota_credito','presupuesto','remito','recibo')),
    signo_cta_cte smallint    not null default 0 check (signo_cta_cte in (-1, 0, 1)),
    fiscal        boolean     not null default false
);

insert into tipos_comprobante (codigo, descripcion, letra, codigo_arca, clase, signo_cta_cte, fiscal) values
    ('FA',  'Factura A',         'A',  1, 'factura',      1, true),
    ('FB',  'Factura B',         'B',  6, 'factura',      1, true),
    ('FC',  'Factura C',         'C', 11, 'factura',      1, true),
    ('NDA', 'Nota de Débito A',  'A',  2, 'nota_debito',  1, true),
    ('NDB', 'Nota de Débito B',  'B',  7, 'nota_debito',  1, true),
    ('NDC', 'Nota de Débito C',  'C', 12, 'nota_debito',  1, true),
    ('NCA', 'Nota de Crédito A', 'A',  3, 'nota_credito',-1, true),
    ('NCB', 'Nota de Crédito B', 'B',  8, 'nota_credito',-1, true),
    ('NCC', 'Nota de Crédito C', 'C', 13, 'nota_credito',-1, true),
    ('PRE', 'Presupuesto',       'X', null, 'presupuesto', 0, false),
    ('REM', 'Remito',            'X', null, 'remito',      0, false),
    ('REC', 'Recibo',            'X', null, 'recibo',     -1, false)
on conflict (codigo) do nothing;

-- ===== Numeración local por punto de venta y tipo (NUMEROS del legacy) =====
-- Para fiscales es espejo de control (manda FECompUltimoAutorizado de ARCA);
-- para internos (PRE/REM/REC) es la fuente. Se incrementa con lock de fila.
create table if not exists numeracion (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid       not null references tenants(id) on delete cascade,
    punto_venta_id uuid       not null references puntos_venta(id) on delete cascade,
    tipo_codigo    varchar(5) not null references tipos_comprobante(codigo),
    ultimo         bigint     not null default 0,
    unique (tenant_id, punto_venta_id, tipo_codigo)
);

-- ===== Comprobantes (VENTASM + FE0004): facturas/NC/ND, presupuestos, remitos =====
-- Los datos del receptor son SNAPSHOT al momento de crear/emitir (un documento
-- fiscal no puede cambiar si después se edita la entidad). receptor_doc_tipo usa
-- los códigos ARCA: 80=CUIT, 86=CUIL, 96=DNI, 99=sin identificar.
create table if not exists comprobantes (
    id                      uuid primary key default gen_random_uuid(),
    tenant_id               uuid        not null references tenants(id) on delete cascade,
    punto_venta_id          uuid        not null references puntos_venta(id),
    tipo_codigo             varchar(5)  not null references tipos_comprobante(codigo),
    letra                   char(1)     not null,
    numero                  bigint,                 -- fiscales: lo asigna ARCA al emitir
    fecha                   date        not null default current_date,
    cliente_id              uuid        references clientes(id),
    receptor_nombre         varchar(120) not null default 'Consumidor Final',
    receptor_doc_tipo       smallint    not null default 99,
    receptor_doc_nro        varchar(11),
    receptor_condicion_iva  varchar(2)  not null default 'CF'
                            check (receptor_condicion_iva in ('RI','MT','EX','CF')),
    receptor_domicilio      varchar(180),
    contado                 boolean     not null default true,
    condicion_venta_id      uuid        references condiciones_venta(id),
    condicion_venta_desc    varchar(60),
    lista_precios           smallint    not null default 1,
    deposito_id             uuid        references depositos(id),
    actualiza_stock         boolean     not null default true,
    moneda                  char(3)     not null default 'PES' check (moneda in ('PES','DOL')),
    cotizacion              numeric(14,4) not null default 1,
    descuento_pct           numeric(5,2)  not null default 0,
    descuento_importe       numeric(14,2) not null default 0,
    neto_gravado            numeric(14,2) not null default 0,
    neto_no_gravado         numeric(14,2) not null default 0,
    exento                  numeric(14,2) not null default 0,
    iva                     numeric(14,2) not null default 0,
    otros_tributos          numeric(14,2) not null default 0,
    total                   numeric(14,2) not null default 0,
    -- Transparencia fiscal Ley 27.743 (B/C a consumidor final)
    iva_contenido           numeric(14,2),
    otros_imp_indirectos    numeric(14,2),
    -- Cta. cte.: saldo pendiente (facturas/ND: deuda; NC: crédito disponible)
    saldo                   numeric(14,2) not null default 0,
    estado                  varchar(10) not null default 'borrador'
                            check (estado in ('borrador','emitido','anulado')),
    -- ARCA (FE0004 del legacy: CAE/FECHACAE/VTOCAE/RESULTADO/MOTIVO)
    cae                     varchar(14),
    cae_vencimiento         date,
    arca_resultado          char(1),               -- A=aprobado, P=parcial, S=simulado
    arca_observaciones      text,
    arca_request            text,                  -- XML enviado (auditoría)
    arca_response           text,                  -- XML recibido (auditoría)
    comprobante_asociado_id uuid references comprobantes(id),  -- NC/ND -> factura (RG 4540)
    origen_id               uuid references comprobantes(id),  -- factura <- presupuesto, etc.
    observaciones           text,
    emitido_at              timestamptz,
    emitido_por             uuid references usuarios(id),
    creado_por              uuid references usuarios(id),
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now()
);
create unique index if not exists uq_comprobantes_numero
    on comprobantes(tenant_id, punto_venta_id, tipo_codigo, numero)
    where numero is not null;
create index if not exists idx_comprobantes_lista
    on comprobantes(tenant_id, fecha desc, created_at desc);
create index if not exists idx_comprobantes_cliente
    on comprobantes(tenant_id, cliente_id) where cliente_id is not null;
create index if not exists idx_comprobantes_saldo
    on comprobantes(tenant_id, cliente_id) where saldo <> 0;

-- ===== Ítems (VENTASD): precio_unitario SIEMPRE neto sin IVA =====
create table if not exists comprobante_items (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid          not null references tenants(id) on delete cascade,
    comprobante_id uuid          not null references comprobantes(id) on delete cascade,
    orden          smallint      not null default 0,
    articulo_id    uuid          references articulos(id),
    variante_id    uuid          references articulo_variantes(id),
    codigo         varchar(20),
    descripcion    varchar(120)  not null,
    cantidad       numeric(14,3) not null default 1,
    precio_unitario numeric(14,4) not null default 0,   -- neto (sin IVA)
    bonif_pct      numeric(5,2)  not null default 0,
    tasa_iva       numeric(5,2)  not null default 21,
    importe_neto   numeric(14,2) not null default 0,
    importe_iva    numeric(14,2) not null default 0,
    importe_total  numeric(14,2) not null default 0,
    costo_unitario numeric(14,4) not null default 0     -- para margen (COSTO del legacy)
);
create index if not exists idx_comp_items on comprobante_items(tenant_id, comprobante_id);

-- ===== Alícuotas por comprobante (TABLAIVA -> array AlicIva de WSFEv1) =====
create table if not exists comprobante_alicuotas (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid          not null references tenants(id) on delete cascade,
    comprobante_id uuid          not null references comprobantes(id) on delete cascade,
    tasa           numeric(5,2)  not null,
    codigo_arca    smallint      not null,  -- 3=0% 4=10,5% 5=21% 6=27% 8=5% 9=2,5%
    base           numeric(14,2) not null default 0,
    importe        numeric(14,2) not null default 0,
    unique (comprobante_id, tasa)
);

-- ===== Vencimientos / cuotas (VENCIC) =====
create table if not exists comprobante_vencimientos (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid          not null references tenants(id) on delete cascade,
    comprobante_id uuid          not null references comprobantes(id) on delete cascade,
    nro_cuota      smallint      not null default 1,
    fecha_vto      date          not null,
    importe        numeric(14,2) not null,
    unique (comprobante_id, nro_cuota)
);

-- ===== Recibos de cobranza (RECIBOSM) — documento interno X =====
create table if not exists recibos (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid          not null references tenants(id) on delete cascade,
    punto_venta_id  uuid          not null references puntos_venta(id),
    numero          bigint        not null,
    fecha           date          not null default current_date,
    cliente_id      uuid          not null references clientes(id),
    receptor_nombre varchar(120)  not null,
    total           numeric(14,2) not null,
    aplicado        numeric(14,2) not null default 0,  -- suma de imputaciones (resto = a cuenta)
    estado          varchar(10)   not null default 'emitido'
                    check (estado in ('emitido','anulado')),
    observaciones   text,
    creado_por      uuid          references usuarios(id),
    created_at      timestamptz   not null default now(),
    unique (tenant_id, punto_venta_id, numero)
);
create index if not exists idx_recibos_cliente on recibos(tenant_id, cliente_id);

-- Medios de pago del recibo (efectivo/transferencia/cheque/tarjeta...)
create table if not exists recibo_medios (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid          not null references tenants(id) on delete cascade,
    recibo_id  uuid          not null references recibos(id) on delete cascade,
    medio      varchar(15)   not null check (medio in
               ('efectivo','transferencia','cheque','tarjeta','mercadopago','otro')),
    importe    numeric(14,2) not null,
    referencia varchar(60)   -- nro. cheque / lote-cupón / nro. operación
);

-- ===== Imputaciones: qué cobranza/crédito cancela qué comprobante =====
-- Origen: un recibo O una NC (exactamente uno). Al insertar, la app descuenta
-- comprobantes.saldo (deuda) y recibos.aplicado o el saldo de la NC (crédito).
create table if not exists imputaciones (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid          not null references tenants(id) on delete cascade,
    cliente_id     uuid          not null references clientes(id),
    recibo_id      uuid          references recibos(id) on delete cascade,
    credito_id     uuid          references comprobantes(id) on delete cascade,
    comprobante_id uuid          not null references comprobantes(id) on delete cascade,
    importe        numeric(14,2) not null check (importe > 0),
    fecha          date          not null default current_date,
    creado_por     uuid          references usuarios(id),
    created_at     timestamptz   not null default now(),
    check (num_nonnulls(recibo_id, credito_id) = 1)
);
create index if not exists idx_imputaciones_comp on imputaciones(tenant_id, comprobante_id);
create index if not exists idx_imputaciones_recibo on imputaciones(tenant_id, recibo_id);

-- ===== Configuración ARCA por tenant =====
create table if not exists arca_config (
    id                     uuid primary key default gen_random_uuid(),
    tenant_id              uuid        not null unique references tenants(id) on delete cascade,
    modo                   varchar(13) not null default 'deshabilitado'
                           check (modo in ('deshabilitado','simulado','homologacion','produccion')),
    cuit                   varchar(11),
    razon_social           varchar(80),
    iibb                   varchar(15),
    inicio_actividades     date,
    concepto               smallint    not null default 1 check (concepto in (1,2,3)),
    umbral_identificar_cf  numeric(14,2) not null default 10000000,  -- RG 5700/2025
    cert_pem               text,
    key_pem                text,
    created_at             timestamptz not null default now(),
    updated_at             timestamptz not null default now()
);

-- Tickets de acceso WSAA cacheados (vigencia 12 h) por tenant/servicio/modo
create table if not exists arca_tokens (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    servicio   varchar(10) not null default 'wsfe',
    modo       varchar(13) not null,
    token      text        not null,
    sign       text        not null,
    expira     timestamptz not null,
    created_at timestamptz not null default now(),
    unique (tenant_id, servicio, modo)
);

-- ===== Kardex: tipos de movimiento que agrega Ventas =====
alter table stock_movimientos drop constraint if exists stock_movimientos_tipo_check;
alter table stock_movimientos add constraint stock_movimientos_tipo_check
    check (tipo in ('inicial','ajuste','transferencia','compra','venta',
                    'devolucion','remito','anulacion'));

-- ===== RLS deny-all (segunda defensa, patrón 005; los grants ya están
-- revocados por default privileges de la 005 en prod) =====
do $$
declare
    t text;
begin
    foreach t in array array['puntos_venta','tipos_comprobante','numeracion',
        'comprobantes','comprobante_items','comprobante_alicuotas',
        'comprobante_vencimientos','recibos','recibo_medios','imputaciones',
        'arca_config','arca_tokens']
    loop
        execute format('alter table public.%I enable row level security', t);
    end loop;
end $$;
