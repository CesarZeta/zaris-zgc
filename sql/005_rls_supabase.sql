-- 005 — Hardening RLS para Supabase (cierre de Fase 0 / deploy).
--
-- El backend FastAPI se conecta directo a Postgres con el rol dueño de las
-- tablas (bypassa RLS) y aplica el aislamiento por tenant_id en cada query.
-- Esta migración es la SEGUNDA línea de defensa (CLAUDE.md §1-bis): Supabase
-- expone PostgREST con la anon key para todo el schema public, así que se
-- habilita RLS SIN políticas (deny-all) y se revocan los grants de los roles
-- de API (anon/authenticated). Resultado: la única puerta a los datos es el
-- backend.
--
-- Idempotente y segura en local (si los roles de Supabase no existen, esa
-- parte se saltea).

do $$
declare
    t record;
begin
    for t in
        select tablename from pg_tables where schemaname = 'public'
    loop
        execute format('alter table public.%I enable row level security', t.tablename);
    end loop;
end $$;

-- revocar acceso de los roles de PostgREST (solo existen en Supabase)
do $$
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        execute 'revoke all on all tables in schema public from anon';
        execute 'revoke all on all sequences in schema public from anon';
        execute 'alter default privileges in schema public revoke all on tables from anon';
        execute 'alter default privileges in schema public revoke all on sequences from anon';
    end if;
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute 'revoke all on all tables in schema public from authenticated';
        execute 'revoke all on all sequences in schema public from authenticated';
        execute 'alter default privileges in schema public revoke all on tables from authenticated';
        execute 'alter default privileges in schema public revoke all on sequences from authenticated';
    end if;
end $$;
