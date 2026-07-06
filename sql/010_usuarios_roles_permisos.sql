-- 010 — Fase 6.5: Usuarios, Roles y Permisos por módulo (RBAC).
-- Diseño: docs/DISENO-USUARIOS-Y-PERMISOS.md (discovery 2026-07-05).
--
-- Modelo: roles por tenant + permisos por (rol, módulo) con nivel máximo
-- acumulativo ('ver' < 'editar' < 'anular'; ausencia de fila = sin acceso).
-- Moderniza el PERMISOS.DBF del legacy (usuario × programa × permitido) a
-- rol × módulo × acción. NO se replica USUARIOS.DBF (flag por columna).
--
-- Compatibilidad: usuarios.nivel_acceso NO se toca — sigue gobernando la
-- autorización de supervisor del POS (pos.py). rol_id NULL = acceso total
-- (compat admin): preserva el comportamiento de hoy para usuarios creados
-- por scripts/SQL (smoke tenants, seeds) sin romper nada.
--
-- Módulos canónicos (código estable, nunca se renombra en prod):
--   clientes, ventas, proveedores, compras, articulos, stock, caja,
--   libros_iva, pos, configuracion

-- ===== Roles =====
create table if not exists roles (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid         not null references tenants(id) on delete cascade,
    codigo      varchar(30)  not null,
    nombre      varchar(60)  not null,
    es_sistema  boolean      not null default false,  -- sembrados, no editables/borrables
    activo      boolean      not null default true,
    created_at  timestamptz  not null default now(),
    unique (tenant_id, codigo)
);
create index if not exists idx_roles_tenant on roles(tenant_id);

-- ===== Permisos por módulo =====
-- Una fila por (rol, módulo) con el nivel MÁXIMO ('anular' implica 'editar'
-- implica 'ver'). tenant_id denormalizado por convención del proyecto
-- (toda tabla lleva tenant_id; RLS como segunda defensa).
create table if not exists rol_permisos (
    rol_id     uuid        not null references roles(id) on delete cascade,
    tenant_id  uuid        not null references tenants(id) on delete cascade,
    modulo     varchar(20) not null,
    accion     varchar(10) not null check (accion in ('ver','editar','anular')),
    primary key (rol_id, modulo)
);
create index if not exists idx_rol_permisos_tenant on rol_permisos(tenant_id);

-- ===== Usuario → rol =====
alter table usuarios add column if not exists rol_id uuid references roles(id);
create index if not exists idx_usuarios_rol on usuarios(rol_id);

-- ===== Seed de roles base (es_sistema) para TODOS los tenants existentes =====
-- Idempotente: on conflict do nothing. Para tenants nuevos el backend siembra
-- lazy (GET /roles siembra si el tenant no tiene ninguno).
insert into roles (tenant_id, codigo, nombre, es_sistema)
select t.id, r.codigo, r.nombre, true
from tenants t
cross join (values
    ('admin',    'Administrador'),
    ('gerente',  'Gerente'),
    ('cajero',   'Cajero'),
    ('vendedor', 'Vendedor'),
    ('consulta', 'Consulta')
) as r(codigo, nombre)
on conflict (tenant_id, codigo) do nothing;

-- Matriz de permisos de los roles base (espejo de app/core/permisos.py):
--   admin    → anular en TODOS (incluida configuracion)
--   gerente  → anular en operativos + ver configuracion (no administra usuarios)
--   cajero   → editar ventas/caja/pos/clientes + ver articulos/stock
--   vendedor → editar ventas/clientes + ver articulos/stock
--   consulta → ver en los 9 operativos (sin configuracion)
insert into rol_permisos (rol_id, tenant_id, modulo, accion)
select r.id, r.tenant_id, p.modulo, p.accion
from roles r
join (values
    ('admin','clientes','anular'),('admin','ventas','anular'),('admin','proveedores','anular'),
    ('admin','compras','anular'),('admin','articulos','anular'),('admin','stock','anular'),
    ('admin','caja','anular'),('admin','libros_iva','anular'),('admin','pos','anular'),
    ('admin','configuracion','anular'),
    ('gerente','clientes','anular'),('gerente','ventas','anular'),('gerente','proveedores','anular'),
    ('gerente','compras','anular'),('gerente','articulos','anular'),('gerente','stock','anular'),
    ('gerente','caja','anular'),('gerente','libros_iva','anular'),('gerente','pos','anular'),
    ('gerente','configuracion','ver'),
    ('cajero','ventas','editar'),('cajero','caja','editar'),('cajero','pos','editar'),
    ('cajero','clientes','editar'),('cajero','articulos','ver'),('cajero','stock','ver'),
    ('vendedor','ventas','editar'),('vendedor','clientes','editar'),
    ('vendedor','articulos','ver'),('vendedor','stock','ver'),
    ('consulta','clientes','ver'),('consulta','ventas','ver'),('consulta','proveedores','ver'),
    ('consulta','compras','ver'),('consulta','articulos','ver'),('consulta','stock','ver'),
    ('consulta','caja','ver'),('consulta','libros_iva','ver'),('consulta','pos','ver')
) as p(codigo, modulo, accion) on p.codigo = r.codigo
where r.es_sistema
on conflict (rol_id, modulo) do nothing;

-- ===== Backfill: usuarios existentes → rol admin de su tenant =====
-- Preserva el comportamiento de hoy (todo usuario ve todo).
update usuarios u
set rol_id = r.id
from roles r
where u.rol_id is null
  and r.tenant_id = u.tenant_id
  and r.codigo = 'admin'
  and r.es_sistema;

-- ===== RLS (deny-all, segunda defensa — patrón 005) =====
alter table roles enable row level security;
alter table rol_permisos enable row level security;
