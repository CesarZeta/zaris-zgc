-- 003 — Artículos y Stock (Fase 2).
-- Diseñado sobre el legacy (docs/legacy/esquema-dbf.md): ARTICULO, FAMILIAS,
-- SUBFLIA, DEPOSITO, STOCK (saldos por depósito) y MOV_STOC (kardex).
-- Campos del legacy que se difieren a fases posteriores (anotados para el migrador):
--   CPROV/NOMPROV/CODPROVE, UNICOMP/COEFICIENT, BONIF_xx  -> Fase 4 (Compras/Proveedores)
--   CUENTA (imputación contable)                          -> módulo Contabilidad
--   NAC_IMP/NDESPACHO/ADUANA/ORIGEN, COMBUS, FOTO/DIBUJO  -> post-MVP

-- ===== Catálogos por tenant =====
create table if not exists familias (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    nombre     varchar(40) not null,           -- legacy FAMILIAS.NFAMILIA C(30)
    activa     boolean     not null default true,
    unique (tenant_id, nombre)
);

create table if not exists subfamilias (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    familia_id uuid        not null references familias(id) on delete cascade,
    nombre     varchar(40) not null,           -- legacy SUBFLIA.NSUBF C(30)
    activa     boolean     not null default true,
    unique (tenant_id, familia_id, nombre)
);

create table if not exists marcas (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    nombre     varchar(40) not null,
    activa     boolean     not null default true,
    unique (tenant_id, nombre)
);

create table if not exists unidades (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    codigo     varchar(6)  not null,           -- legacy ARTICULO.UNIDAD C(6): UN, KG, LT...
    nombre     varchar(30) not null,
    unique (tenant_id, codigo)
);

create table if not exists depositos (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    sucursal_id uuid references sucursales(id),
    codigo      varchar(4)  not null,          -- legacy DEPOSITO.CDEP C(2)
    nombre      varchar(40) not null,          -- legacy DEPOSITO.NDEP C(30)
    activo      boolean     not null default true,
    unique (tenant_id, codigo),
    unique (tenant_id, nombre)
);

-- Cotización del dólar (decisión MVP: precios en USD + cotización).
-- La vigente es la de vigente_desde más reciente.
create table if not exists cotizaciones (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid          not null references tenants(id) on delete cascade,
    valor         numeric(14,4) not null check (valor > 0),
    vigente_desde timestamptz   not null default now(),
    usuario_id    uuid references usuarios(id)
);
create index if not exists idx_cotizaciones_tenant on cotizaciones(tenant_id, vigente_desde desc);

-- ===== Maestro de artículos =====
create table if not exists articulos (
    id                   uuid primary key default gen_random_uuid(),
    tenant_id            uuid          not null references tenants(id) on delete cascade,
    codigo               varchar(20)   not null,              -- legacy CODART C(15)
    codigo_barras        varchar(20),                         -- legacy CBARRA C(20)
    descripcion          varchar(80)   not null,              -- legacy DESART C(40)
    familia_id           uuid references familias(id),
    subfamilia_id        uuid references subfamilias(id),
    marca_id             uuid references marcas(id),
    unidad_id            uuid references unidades(id),        -- legacy UNIDAD C(6)
    controla_stock       boolean       not null default true, -- legacy STOCK L
    costo                numeric(14,4) not null default 0,    -- legacy COSTO N(9,3)
    costo_con_iva        boolean       not null default false,-- legacy COSTIVA N(1)
    tasa_iva             numeric(5,2)  not null default 21,   -- legacy TASA N(5,2)
    -- 4 listas de precios: precio = costo neto * (1 + utilidad/100)  (legacy UTIL_x/PVENTA_x)
    utilidad_1           numeric(7,2)  not null default 0,
    utilidad_2           numeric(7,2)  not null default 0,
    utilidad_3           numeric(7,2)  not null default 0,
    utilidad_4           numeric(7,2)  not null default 0,
    precio_1             numeric(14,4) not null default 0,
    precio_2             numeric(14,4) not null default 0,
    precio_3             numeric(14,4) not null default 0,
    precio_4             numeric(14,4) not null default 0,
    en_dolares           boolean       not null default false,-- legacy EN_DOLARES: costo/precios en USD
    impuesto_interno     numeric(12,5) not null default 0,    -- legacy IMP_INT (monto fijo por unidad)
    -- flags previstos del POS super (sin funcionalidad en Fase 2; legacy PESABLE/VENTAXDEPT/DEVOLUCION/ENVASE)
    pesable              boolean       not null default false,
    venta_por_depto      boolean       not null default false,
    es_envase_retornable boolean       not null default false,
    envase_articulo_id   uuid references articulos(id),
    precio_actualizado_at timestamptz,                        -- legacy ULT_PRC D
    observaciones        text,                                -- legacy NOTA M
    activo               boolean       not null default true,
    created_at           timestamptz   not null default now(),
    updated_at           timestamptz   not null default now(),
    unique (tenant_id, codigo)
);
create index if not exists idx_articulos_tenant on articulos(tenant_id);
create index if not exists idx_articulos_descripcion on articulos(tenant_id, descripcion);
create unique index if not exists uq_articulos_cbarra
    on articulos(tenant_id, codigo_barras)
    where codigo_barras is not null;

-- ===== Stock: saldo por artículo y depósito (legacy STOCK.DBF) =====
create table if not exists articulo_stock (
    id           uuid primary key default gen_random_uuid(),
    tenant_id    uuid          not null references tenants(id) on delete cascade,
    articulo_id  uuid          not null references articulos(id) on delete cascade,
    deposito_id  uuid          not null references depositos(id),
    cantidad     numeric(14,3) not null default 0,   -- legacy SALDO
    stock_minimo numeric(14,3) not null default 0,   -- legacy MINIMO
    ubicacion    varchar(20),                        -- legacy UBICACION C(10)
    updated_at   timestamptz   not null default now(),
    unique (tenant_id, articulo_id, deposito_id)
);
create index if not exists idx_articulo_stock_deposito on articulo_stock(tenant_id, deposito_id);

-- ===== Kardex: movimientos de stock (legacy MOV_STOC.DBF) =====
-- cantidad con signo: positiva entra, negativa sale. saldo_resultante se sella
-- al registrar el movimiento (kardex auditable sin recalcular).
create table if not exists stock_movimientos (
    id               uuid primary key default gen_random_uuid(),
    tenant_id        uuid          not null references tenants(id) on delete cascade,
    articulo_id      uuid          not null references articulos(id) on delete cascade,
    deposito_id      uuid          not null references depositos(id),
    fecha            timestamptz   not null default now(),   -- legacy FMOV
    tipo             varchar(15)   not null                  -- legacy CCONC (concepto)
                     check (tipo in ('inicial','ajuste','transferencia','compra','venta')),
    cantidad         numeric(14,3) not null check (cantidad <> 0),
    saldo_resultante numeric(14,3) not null,
    comprobante      varchar(30),                            -- legacy NCOMP
    observaciones    varchar(120),                           -- legacy OBSERVAC C(45)
    grupo_id         uuid,          -- vincula las dos patas de una transferencia
    usuario_id       uuid references usuarios(id),
    created_at       timestamptz   not null default now()
);
create index if not exists idx_stock_mov_kardex
    on stock_movimientos(tenant_id, articulo_id, deposito_id, fecha desc);
