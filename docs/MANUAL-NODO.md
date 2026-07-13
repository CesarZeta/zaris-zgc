# ZGC — Manual del Nodo de Sucursal (F13-LAN N1 + N2)

> Estado: **N1 + N2 en producción** (2026-07-13). Diseño completo en
> `DISENO-NODO-LAN.md`. Este manual cubre instalación, conexión de cajas y
> operación: réplica de bajada, sincronización de subida y CAE diferido.

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

### Alcance (N1 + N2 operativos)

| Ya funciona | Llega en N3 |
|---|---|
| Réplica de bajada continua (nube → nodo) de maestros y precios | Gestión local completa (compras, bancos…) |
| **Subida automática a la nube**: ventas POS y de gestión, NC, recibos, sesiones/arqueos, kardex y numeración convergen solos al reconectar (idempotente; el stock de la nube se ajusta por deltas, nunca se pisa) | Comandas del POS resto centralizadas (hoy quedan locales; la venta final SÍ sube) |
| **CAE diferido**: con ARCA caída la caja emite igual (ticket con leyenda "pendiente de autorización", sin QR) y el nodo pide el CAE retroactivo al reconectar, en orden de numeración | CAEA (anticipo quincenal) para cortes largos |
| POS + facturación de gestión con PV propio, offline | Updates automáticos del nodo |
| Maestros de solo lectura en el nodo (403 en escrituras) | |
| Monitoreo en Configuración → Nodos: última conexión/réplica + atraso (filas por subir / comprobantes sin CAE) | |

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
- **Regla de cobranza (hasta N3)**: las facturas en cta. cte. emitidas en el
  nodo se cobran EN EL NODO. Un pago registrado en la nube contra una factura
  del nodo puede ser pisado por la próxima sincronización (el origen manda
  sobre sus documentos).
- **Estado de la réplica**: `GET /api/v1/nodo/estado` (logueado) — última
  réplica OK, último error, checkpoints por tabla, filas por subir y
  comprobantes sin CAE. También en la nube: Configuración → Nodos (última
  conexión / última réplica / atraso).
- **Forzar un ciclo**: `POST /api/v1/nodo/sync-ahora` (CAE pendientes +
  bajada + subida).
- **Corte de internet**: el POS y la facturación local siguen; la réplica
  reintenta sola y al volver la conexión todo converge en el mismo ciclo.
  Si ARCA está caída (o no hay internet) los fiscales salen con la leyenda
  "COMPROBANTE PENDIENTE DE AUTORIZACIÓN ANTE ARCA" y sin QR; el CAE llega
  retroactivo. Si ARCA RECHAZA un comprobante emitido offline queda marcado
  (`arca_resultado = R`) y visible en el monitoreo: resolución manual.
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
