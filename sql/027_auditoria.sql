-- 027 — F17: Auditoría de acciones (audit log). Diseño en docs/DISENO-AUDITORIA.md.
-- Aditiva e idempotente. Una sola tabla INMUTABLE por construcción (la API no
-- expone UPDATE/DELETE; sin updated_at): escrituras de configuración y eventos
-- de seguridad que NO dejan documento (los documentos operativos ya son su
-- propia auditoría — contrato de contabilizabilidad 014).
-- OJO deploy: el backend nuevo mapea esta tabla → la 027 va ANTES del push,
-- y después se re-aplica la 005 (tabla nueva ⇒ RLS deny-all).

create table if not exists audit_eventos (
    id             uuid primary key default gen_random_uuid(),
    tenant_id      uuid         not null references tenants(id) on delete cascade,
    usuario_id     uuid         references usuarios(id),
    -- SNAPSHOT: legible sin join; si el usuario se renombra el evento no cambia.
    -- En login fallido: el email intentado.
    usuario_email  varchar(120),
    accion         varchar(40)  not null,  -- catálogo en services/auditoria.py (espejo del diseño §3)
    modulo         varchar(20)  not null,  -- módulo RBAC del evento + 'auth'
    ref_id         uuid,                   -- objeto afectado (usuario, rol, comprobante, nodo…)
    ref_texto      varchar(200),           -- descripción humana del efecto
    detalle        jsonb,                  -- parámetros / antes-después; NUNCA claves ni certificados
    ip             varchar(45),
    created_at     timestamptz  not null default now()
);
create index if not exists idx_audit_eventos_tenant_fecha
    on audit_eventos(tenant_id, created_at);
create index if not exists idx_audit_eventos_tenant_accion
    on audit_eventos(tenant_id, accion);

-- RLS deny-all (segunda defensa, patrón 005..026)
alter table audit_eventos enable row level security;
