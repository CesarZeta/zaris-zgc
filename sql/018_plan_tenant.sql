-- 018 — F12-a: POS standalone — plan por tenant + rubros carniceria/restaurante.
-- Diseño en docs/DISENO-POS-PERFILES.md §7: el POS se vende como módulo independiente
-- (licencia solo-POS para kiosco/carnicería/resto) implementado como PACKAGING, no fork:
-- `tenants.plan` acota qué módulos existen para el tenant (intersección con el RBAC de
-- la 010 en app/core/permisos.py — catálogo PLANES, espejo de este CHECK).
-- Aditiva e idempotente; segura de aplicar ANTES del backend nuevo (el viejo no la lee).
-- Los tenants existentes quedan en 'suite' (todos los módulos, comportamiento actual).

alter table tenants add column if not exists plan varchar(20) not null default 'suite';
alter table tenants drop constraint if exists tenants_plan_check;
alter table tenants add constraint tenants_plan_check
    check (plan in ('suite', 'pos'));

-- Rubros nuevos para los perfiles de POS (F12): carnicería (despiece en gestión +
-- POS pesable) y restaurante (mesas/comandas locales al POS). Presets en empresa.py.
alter table tenants drop constraint if exists tenants_rubro_check;
alter table tenants add constraint tenants_rubro_check
    check (rubro in ('general', 'supermercado', 'indumentaria_calzado', 'electronica',
                     'ferreteria_repuestos', 'distribuidora', 'carniceria', 'restaurante'));
