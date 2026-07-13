-- 024 — F13-LAN N2: sincronización completa (subida nodo → nube + CAE
-- diferido + monitoreo). Diseño en docs/DISENO-NODO-LAN.md §5-§6.
-- Aditiva e idempotente; segura de aplicar ANTES del backend nuevo.
-- No crea tablas nuevas: no hace falta re-aplicar la 005.

-- 1) updated_at para el checkpoint de subida en las tablas MUTABLES que no lo
--    tenían (recibos cambia aplicado/estado, sesiones POS cierran con arqueo,
--    imputaciones se anulan con marca). comprobantes ya lo tiene desde la 006.
alter table recibos add column if not exists
    updated_at timestamptz not null default now();
alter table pos_sesiones add column if not exists
    updated_at timestamptz not null default now();
alter table imputaciones add column if not exists
    updated_at timestamptz not null default now();
-- numeracion sube como ESPEJO LWW del nodo: así la nube retoma la secuencia
-- sola cuando el nodo se revoca (sin esto, el primer emitir post-revocación
-- colisiona el UNIQUE de comprobantes — bug cazado por la suite N2)
alter table numeracion add column if not exists
    updated_at timestamptz not null default now();

-- 2) updated_at confiable a nivel DB (mismo trigger de la 023): sin esto un
--    UPDATE por ORM/SQL no lo mueve y la subida por checkpoint pierde cambios.
do $$
declare
    t text;
begin
    foreach t in array array['comprobantes', 'recibos', 'pos_sesiones', 'imputaciones', 'numeracion']
    loop
        execute format('drop trigger if exists trg_touch_updated_at on %I', t);
        execute format(
            'create trigger trg_touch_updated_at before update on %I
             for each row execute function zgc_touch_updated_at()', t
        );
    end loop;
end $$;

-- 3) Monitoreo del nodo en Configuración: atraso reportado por el ping del
--    ciclo de réplica (0 = al día; cae_pendientes > 0 = ARCA inalcanzable
--    desde el nodo o comprobantes esperando CAE diferido).
alter table sucursal_nodos add column if not exists
    subida_pendientes integer not null default 0;
alter table sucursal_nodos add column if not exists
    cae_pendientes integer not null default 0;
