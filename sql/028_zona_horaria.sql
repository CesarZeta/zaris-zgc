-- 028 — Zona horaria de NEGOCIO en la base (fix fechas UTC, 2026-09-13).
-- Idempotente, sin tablas nuevas (no hace falta re-aplicar la 005/RLS).
--
-- Por qué: Supabase corre en UTC. Todo `default current_date` de los
-- documentos (comprobantes, recibos, OP, caja, bancos, entregas) y todo
-- `func.date(timestamptz)` de las consultas (logística, resto, kardex,
-- comisiones) resolvía la fecha UTC: después de las 21:00 hora argentina el
-- hecho quedaba fechado MAÑANA. El backend ahora manda siempre la fecha desde
-- `core/fechas.py` (zona `TZ_APP`); esta migración alinea la DB con la misma
-- zona para que los defaults y casts que ejecuta Postgres coincidan.
--
-- Dos niveles, del más específico al más general (Postgres aplica primero la
-- config de rol+base, después la de rol, después la de base):
--   1. ROL: el rol que conecta el backend (`current_user`: `postgres` en
--      Supabase vía pooler, `postgres` en dev/nodo). Un rol SIEMPRE puede
--      cambiar sus propios defaults — es la vía garantizada.
--   2. BASE: mejor esfuerzo. En Supabase la base `postgres` es de
--      `supabase_admin`, no de `postgres` → «must be owner of database»; se
--      captura y se avisa (el nivel 1 ya cubre al backend). En dev/nodo el
--      dueño es postgres y aplica.
-- Toma en las sesiones NUEVAS: reiniciar/redeployar el backend después.

do $$
begin
    execute format('alter role %I set timezone to %L',
                   current_user, 'America/Argentina/Buenos_Aires');
    raise notice '028: timezone fijada para el rol %', current_user;

    begin
        execute format('alter database %I set timezone to %L',
                       current_database(), 'America/Argentina/Buenos_Aires');
        raise notice '028: timezone fijada para la base %', current_database();
    exception when insufficient_privilege then
        raise notice '028: sin privilegio para ALTER DATABASE % (dueño ajeno, p. ej. Supabase) — alcanza con el rol', current_database();
    end;
end $$;

-- Verificación (en una sesión NUEVA): select current_setting('TimeZone');
--   → America/Argentina/Buenos_Aires
-- Config persistida: select rolname, setconfig from pg_db_role_setting s
--   left join pg_roles r on r.oid = s.setrole;
