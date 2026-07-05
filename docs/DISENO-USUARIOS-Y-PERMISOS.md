# ZGC — Diseño de Usuarios, Roles y Permisos por Módulo

> Discovery del 2026-07-05 (César). Modelo elegido: **Roles + permisos por módulo**,
> con granularidad **Ver / Editar / Anular**. Se implementa como **fase propia** (no frena
> el POS): agendada como **Fase 6.5** en el ROADMAP (después del POS de la Fase 6, antes
> del POST-MVP). Este documento es la especificación; leerlo antes de tocar `usuarios`,
> `auth` o cualquier guarda de endpoint.

## 0. Por qué (el gap real)

Hoy (verificado 2026-07-05):

- `usuarios.nivel_acceso` es un **smallint suelto** (default 1 = admin). Solo se usa en el
  POS para autorizar anulaciones (`nivel <= 2` = supervisor, `pos.py:63`).
- **Ningún otro endpoint controla acceso por módulo**: cualquier usuario autenticado del
  tenant ve y opera todo (Ventas, Compras, Caja, Libros IVA, Configuración…).
- El SQL 001 dejó anotado el pendiente: *"niveles/permisos por módulo se amplían en Fase 1"*.

Esto es exactamente lo que este diseño resuelve.

## 1. Lección del legacy (RevoSolution)

El esquema DBF extraído (`docs/legacy/esquema-dbf.md`) tiene DOS modelos coexistiendo:

- **`PERMISOS.DBF`** (bueno, normalizado): `USUARIO` + `PROGRAMA` + `PERMITIDO` (0/1).
  Una fila por usuario × programa. **Este es el patrón que modernizamos.**
- **`USUARIOS.DBF`** (viejo, desnormalizado): un flag booleano por programa como columna
  (`GV0090`, `STOCK`, `PRECIOS`, `EQUIS`…). **NO replicar** — columna por permiso no escala.

Modernización: en vez de `usuario × programa`, usamos **`rol × módulo × acción`** (roles para
no reconfigurar cada usuario a mano; acciones Ver/Editar/Anular para distinguir consulta de
operación de anulación).

## 2. Módulos del sistema (fuente de verdad)

Los módulos son áreas funcionales, NO endpoints. Se derivan de los 17 routers montados en
`main.py` agrupados como los ve el usuario en el sidebar. Catálogo canónico (código estable
`snake_case` — nunca se renombra una vez en prod, solo se agrega):

| Código módulo   | Nombre UI        | Routers/áreas que cubre                              |
|-----------------|------------------|------------------------------------------------------|
| `clientes`      | Clientes         | entidades (rol cliente), clientes, cobranzas         |
| `ventas`        | Ventas           | comprobantes (venta), ventas_config                  |
| `proveedores`   | Proveedores      | entidades (rol proveedor), proveedores               |
| `compras`       | Compras          | compras, pagos                                        |
| `articulos`     | Artículos        | articulos, catalogos_articulos, variantes            |
| `stock`         | Stock            | stock                                                 |
| `caja`          | Caja             | caja                                                  |
| `libros_iva`    | Libros IVA       | libros                                                |
| `pos`           | POS              | pos                                                   |
| `configuracion` | Configuración    | empresa + gestor de usuarios/roles (este módulo)     |

> El módulo `configuracion` es especial: contiene el propio gestor de usuarios/roles.
> Solo un rol con `configuracion.editar` puede administrar usuarios (evita escalada).

## 3. Acciones (granularidad Ver / Editar / Anular)

Tres niveles acumulativos por módulo:

| Acción   | Semántica                                                              |
|----------|-----------------------------------------------------------------------|
| `ver`    | Solo lectura: listar, abrir detalle, imprimir/exportar.               |
| `editar` | Crear y modificar (implica `ver`).                                    |
| `anular` | Anular comprobantes / borrar / operaciones sensibles (implica `editar`).|

Regla de implicación: `anular ⇒ editar ⇒ ver`. Un permiso `editar` sin `ver` es inválido.
Se guarda el nivel máximo alcanzado por (rol, módulo); ausencia de fila = sin acceso.

## 4. Modelo de datos (migración 010)

Todo lleva `tenant_id` (multi-tenant, CLAUDE.md §1-bis) y RLS deny-all como 2ª defensa.

```sql
-- Roles: plantillas de permisos por tenant. Un rol "system" no editable por tenant.
create table roles (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null references tenants(id) on delete cascade,
    codigo      varchar(30) not null,          -- 'admin','gerente','cajero','vendedor'...
    nombre      varchar(60) not null,
    es_sistema  boolean not null default false, -- roles base sembrados, no borrables
    activo      boolean not null default true,
    created_at  timestamptz not null default now(),
    unique (tenant_id, codigo)
);

-- Permisos: fila por (rol, módulo, nivel_máximo). Ausencia = sin acceso al módulo.
create table rol_permisos (
    rol_id   uuid not null references roles(id) on delete cascade,
    modulo   varchar(20) not null,             -- código de §2
    accion   varchar(10) not null              -- 'ver' | 'editar' | 'anular'
             check (accion in ('ver','editar','anular')),
    primary key (rol_id, modulo)
);

-- Usuario → rol. Se agrega columna a usuarios (mantenemos nivel_acceso por compat POS).
alter table usuarios add column rol_id uuid references roles(id);
```

**Compatibilidad con el POS**: `nivel_acceso` **se mantiene** — el POS ya lo usa para
autorización de supervisor en anulaciones (`pos.py`). El nuevo sistema es aditivo:
`nivel_acceso` sigue gobernando la autorización de supervisor en caja; `rol_id` gobierna
el acceso a módulos del backoffice. En una fase posterior se puede unificar
(`pos.anular` ⟺ nivel supervisor), pero **no en esta fase** para no tocar el POS en vuelo.

### Roles base sembrados (es_sistema = true) por tenant

| Rol       | Permisos                                                                 |
|-----------|--------------------------------------------------------------------------|
| `admin`   | `anular` en TODOS los módulos, incluido `configuracion`.                  |
| `gerente` | `anular` en operativos; `ver` en `configuracion` (no administra usuarios).|
| `cajero`  | `editar` en `ventas`,`caja`,`pos`,`clientes`; `ver` en `articulos`,`stock`.|
| `vendedor`| `editar` en `ventas`,`clientes`; `ver` en `articulos`,`stock`.            |
| `consulta`| `ver` en todos los operativos; sin `configuracion`.                       |

El tenant puede crear roles propios y editar los no-sistema. El seed corre en el alta de
tenant (y una migración de backfill para tenants existentes → todos los usuarios actuales
quedan con rol `admin`, preservando el comportamiento de hoy).

## 5. Enforcement en backend

Guarda declarativa, patrón dependency de FastAPI (espejo de `get_current_user`):

```python
# app/core/permisos.py
def requiere(modulo: str, accion: str = "ver"):
    async def guard(usuario: Usuario = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)) -> Usuario:
        if not await tiene_permiso(db, usuario, modulo, accion):
            raise HTTPException(403, detail=f"Sin permiso: {modulo}.{accion}")
        return usuario
    return guard
```

Uso en endpoints:

```python
@router.post("/comprobantes", ...)
async def crear(..., usuario = Depends(requiere("ventas", "editar"))): ...

@router.post("/comprobantes/{id}/anular", ...)
async def anular(..., usuario = Depends(requiere("ventas", "anular"))): ...
```

- El JWT hoy ya lleva `nivel`. Se **agrega `rol_id`** al payload para evitar un query por
  request; los permisos del rol se resuelven con una cache corta (o se leen del rol en DB —
  decisión de implementación, medir). Ante cambio de rol, el token viejo caduca por `exp`.
- **Admin bypass**: rol `admin` (o `es_sistema` con todos los permisos) no consulta tabla.
- Regla de oro: **defense in depth** — la guarda NO reemplaza a RLS ni a la validación de
  `tenant_id`; se suma.

## 6. Gestor (frontend) — dentro de Configuración

Tres pantallas bajo `configuracion` (solo visibles con `configuracion.editar`):

1. **Usuarios**: alta/baja/edición, asignar rol, activar/desactivar, **resetear contraseña**
   (genera nueva y la muestra una vez; hash bcrypt en backend). Nunca se muestra la clave
   almacenada (es irreversible).
2. **Roles**: lista de roles del tenant; crear rol propio, clonar uno base.
3. **Matriz de permisos**: grilla módulos (filas) × acción (radio Ver/Editar/Anular/—).
   Guardar → upsert en `rol_permisos`. Los roles `es_sistema` se muestran read-only con
   opción "clonar para editar".

El sidebar se filtra por permisos: un módulo sin `ver` **no aparece** en el menú (además del
403 del backend). El frontend nunca es la única defensa.

## 7. Alcance de la fase (qué entra / qué no)

**Entra:**
- Migración 010 (roles, rol_permisos, usuarios.rol_id) + backfill (usuarios actuales → admin).
- Seed de roles base por tenant.
- `app/core/permisos.py` + aplicar `requiere(...)` a los endpoints de escritura/anulación
  de todos los módulos.
- Gestor completo en Configuración (usuarios + roles + matriz).
- Filtrado del sidebar por permisos.
- Smoke E2E: crear rol limitado, asignarlo, verificar 403 y sidebar recortado.

**No entra (posible fase futura):**
- Unificar `nivel_acceso` del POS con el sistema de roles.
- Permisos a nivel sucursal (un rol distinto por sucursal).
- Auditoría/log de acciones por usuario.
- Granularidad fina por acción individual (abrir caja vs cerrar caja, etc.).

## 8. Riesgos / decisiones abiertas

- **Lockout**: si alguien se quita a sí mismo `configuracion.editar`, podría quedar el tenant
  sin admin. Mitigación: impedir que un tenant se quede con 0 usuarios con permiso de
  configuración (validación en backend al guardar).
- **Costo por request**: resolver permisos en cada llamada. Decisión: `rol_id` en el JWT +
  cache de permisos del rol en memoria del proceso (invalidación por TTL corto). Medir antes
  de complejizar.
- **Migración de datos legacy**: `PERMISOS.DBF` tiene 0 registros canónicos (los clientes no
  usaban permisos granulares) → **no hay que migrar permisos**, solo sembrar los roles base.
