# ZGC — Manual del Nodo de Sucursal (F13-LAN N1)

> Estado: **N1 en producción** (2026-07-12). Diseño completo en
> `DISENO-NODO-LAN.md`. Este manual cubre instalación, conexión de cajas y
> operación de la sub-fase N1 (nodo mínimo con réplica de bajada).

## 1. Qué es

El nodo es una **PC Windows dedicada en la sucursal** (la realidad de los
clientes, herencia del server del legacy) que corre el MISMO backend de ZGC
con perfil `nodo` + una base PostgreSQL local, y sirve el POS web a las cajas
de la LAN. Con el nodo:

- Las cajas venden contra `http://<nodo>:8021` — **sin depender de internet**.
- Los maestros (artículos, precios, clientes, usuarios, cajas, salones…) se
  **replican solos** desde la nube (polling cada 60 s, checkpoint incremental).
- La **facturación de gestión** (módulo Ventas) opera en el nodo con un **punto
  de venta propio**, distinto del de las cajas (§0-bis del diseño).
- Mientras el nodo está activo, su PV y los de las cajas POS de la sucursal
  son **exclusivos del nodo**: la nube se niega a emitir con ellos (422) para
  que la numeración nunca colisione.

### Alcance de N1 (importante)

| Ya funciona (N1) | Llega en N2/N3 |
|---|---|
| Réplica de bajada continua (nube → nodo) | **Subida** de ventas/movimientos a la nube (cola `sync_eventos`) |
| POS + facturación de gestión con PV propio, offline | CAE diferido al reconectar (hoy: modo `simulado` factura offline; con cert real la emisión fiscal requiere internet) |
| Maestros de solo lectura en el nodo (403 en escrituras) | Gestión local completa (compras, bancos…) |
| Monitoreo básico (última conexión/réplica en Configuración → Nodos) | Updates automáticos del nodo |

En N1 las ventas del nodo **quedan en la base local** (no suben solas
todavía). Para un piloto: el nodo es la autoridad de su sucursal y la nube ve
el resto; la consolidación llega con N2.

## 2. Alta del nodo en la suite (una vez, desde la nube)

1. Configuración → **Sucursales**: crear la sucursal si no existe.
2. Configuración → **Ventas / Puntos de venta**: crear un PV para el nodo
   (numeración de la facturación de gestión de esa sucursal) y un PV por caja.
3. Configuración → **Cajas POS**: crear las cajas de la sucursal con su PV y
   su sucursal.
4. Configuración → **Nodos de sucursal (LAN)** → «+ Agregar nodo»: elegir la
   sucursal, nombrar el nodo y asignarle el PV propio. **Copiar el
   `NODO_ID` y el `NODO_TOKEN`: el token se muestra una sola vez.**

## 3. Instalación en la PC de la sucursal

Requisitos: Windows 10/11, Python 3.10+, PostgreSQL 14+ (instalador oficial),
Node.js 20+ (para compilar el POS web), y un checkout del repo ZGC.

En PowerShell **como Administrador**:

```powershell
cd ZGC\tools\nodo
.\instalar_nodo.ps1 -NodoId <uuid> -NodoToken <token> `
    -NubeUrl https://zaris-zgc-api.vercel.app -PgPassword <clave de postgres>
```

El instalador (idempotente, re-correrlo actualiza):
crea la base `zgc_nodo` y aplica TODAS las migraciones de `sql/`, instala las
dependencias Python en `backend\.venv`, compila el POS web (`web-app\dist`,
mismo build de siempre: API same-origin), escribe `backend\.env.nodo`
(incluye un `JWT_SECRET` propio: las sesiones del nodo no dependen de la
nube), registra la tarea programada **«ZGC Nodo Sucursal»** (arranque
automático con Windows) y abre el puerto en el firewall.

## 4. Conectar las cajas

Cada caja es un navegador en la LAN apuntando a:

```
http://<IP-del-nodo>:8021/pos/login
```

Los cajeros entran con **los mismos usuarios y claves de la suite** (se
replican). La gestión de Ventas del nodo vive en `http://<IP-del-nodo>:8021/`
(login de la suite → módulo Ventas; los demás módulos se usan online contra
la nube, como siempre).

## 5. Operación y diagnóstico

- **Maestros**: se editan SOLO en la gestión de la nube; el nodo los replica
  (60 s). Cualquier intento de escritura de maestros en el nodo responde 403.
- **Estado de la réplica**: `GET /api/v1/nodo/estado` (logueado) — última
  réplica OK, último error, checkpoints por tabla. También en la nube:
  Configuración → Nodos (última conexión / última réplica).
- **Forzar una réplica**: `POST /api/v1/nodo/sync-ahora`.
- **Corte de internet**: el POS y la facturación local siguen; la réplica
  reintenta sola. En modo ARCA `simulado` la emisión funciona offline; con
  certificado real, la emisión fiscal del nodo requiere internet hasta que N2
  traiga el CAE diferido.
- **Logs**: la tarea corre uvicorn; `schtasks /Query /TN "ZGC Nodo Sucursal"`.

## 6. Revocar / reinstalar / actualizar

- **Revocar** (Configuración → Nodos): el nodo deja de sincronizar (403 en el
  handshake) y sus PV vuelven a emitir en la nube. Los datos locales no se
  tocan. Un nodo revocado no se reactiva: se crea uno nuevo.
- **Token comprometido o reinstalación**: «Regenerar token» (invalida el
  anterior; actualizar `NODO_TOKEN` en `backend\.env.nodo` y reiniciar).
- **Actualizar el nodo**: `git pull` en el checkout y re-correr
  `instalar_nodo.ps1` con los mismos parámetros (re-aplica migraciones,
  reinstala deps, recompila el web). Updates automáticos: N3.
