-- 026 — F16: Salida de documentos (PDF + email). Diseño en docs/DISENO-SALIDA-DOCUMENTOS.md.
-- Aditiva e idempotente. Registro de emails salientes (observabilidad del canal;
-- en modo simulado es la ÚNICA evidencia) + tokens de recuperación de contraseña
-- autoservicio (solo el hash sha256 — el token en claro viaja únicamente en el
-- email). Sin módulo RBAC nuevo: la bandeja usa `configuracion.ver`, el envío de
-- comprobantes `ventas.editar`, la recuperación es pública (rate implícito: un
-- token pisa al anterior).
-- OJO deploy: el backend nuevo mapea estas tablas → la 026 va ANTES del push,
-- y después se re-aplica la 005 (tablas nuevas ⇒ RLS deny-all).

-- ============================================================================
-- 1. Emails salientes (patrón de modos ARCA: el `modo` queda SELLADO por fila)
-- ============================================================================
create table if not exists email_envios (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid         not null references tenants(id) on delete cascade,
    destinatario  varchar(120) not null,
    asunto        varchar(200) not null,
    -- cuerpo HTML completo: columna pesada, en el ORM nace deferred (regla §6)
    cuerpo        text,
    tipo          varchar(20)  not null
                  check (tipo in ('comprobante','password_reset')),
    ref_id        uuid,        -- comprobante_id o usuario_id según tipo
    modo          varchar(15)  not null,   -- simulado | resend (sellado)
    estado        varchar(10)  not null
                  check (estado in ('simulado','enviado','error')),
    error         varchar(300),
    proveedor_id  varchar(60), -- id del proveedor (Resend) cuando el envío es real
    creado_por    uuid references usuarios(id),
    created_at    timestamptz  not null default now()
);
create index if not exists idx_email_envios_tenant_fecha
    on email_envios(tenant_id, created_at);
create index if not exists idx_email_envios_ref
    on email_envios(ref_id) where ref_id is not null;

-- ============================================================================
-- 2. Recuperación de contraseña autoservicio (cierra el diferido de F6.5)
-- ============================================================================
create table if not exists password_resets (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid        not null references tenants(id) on delete cascade,
    usuario_id  uuid        not null references usuarios(id) on delete cascade,
    token_hash  varchar(64) not null unique,  -- sha256 hex del token urlsafe
    expira_at   timestamptz not null,
    usado_at    timestamptz,
    created_at  timestamptz not null default now()
);
create index if not exists idx_password_resets_usuario
    on password_resets(usuario_id);

-- ============================================================================
-- 3. RLS deny-all (segunda defensa, patrón 005..025)
-- ============================================================================
alter table email_envios    enable row level security;
alter table password_resets enable row level security;
