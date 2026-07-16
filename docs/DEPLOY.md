# ZGC — Runbook de deploy y operación

> Estado al 2026-07-04 (Etapa A completada). Stack: GitHub Pages → Vercel gru1 → Supabase sa-east-1.

## URLs de producción

- **App**: https://cesarzeta.github.io/zaris-zgc/ (pendiente: dominio propio `erp.zaris.com.ar`, ver §Dominio propio)
- **API**: https://zaris-zgc-api.vercel.app (health: `/health`)
- **DB**: Supabase proyecto `zaris-zgc` (cuenta nueva de César, org "ZARIS GESTION COMERCIAL", región sa-east-1)

## Dominio propio `erp.zaris.com.ar` (plan 2026-07-16, pedido de César)

Réplica del patrón ZGE (`zge.zaris.com.ar` = CNAME **DNS-only** → `cesarzeta.github.io`,
verificado por nslookup; el DNS de `zaris.com.ar` está en **Cloudflare**). Subdominio
elegido: `erp` (alineado al rebrand ZARIS ERP; alternativa descartable: `zgc`).

**Paso 0 — César (único paso manual, en Cloudflare):** crear registro
`CNAME  erp  →  cesarzeta.github.io`, **con el proxy APAGADO (nube gris / DNS only)**,
igual que `zge`. Con proxy naranja GitHub Pages no puede emitir el certificado.

**Pasos 1-5 — Claude, en una sola sesión de deploy (avisar cuando el DNS esté):**

1. Custom domain en Pages: `gh api repos/CesarZeta/zaris-zgc/pages -X PUT -f cname=erp.zaris.com.ar`
   (con `build_type=workflow` el dominio vive en la config de Pages, NO hace falta
   archivo `CNAME` en el repo — eso es solo para Pages servido desde branch, como ZGE).
2. `deploy-pages.yml`: `VITE_BASE: /zaris-zgc/` → `/` — **en el mismo deploy** que
   activa el dominio (la app pasa a servirse en la raíz; si se hace desfasado, los
   assets dan 404). La URL vieja `cesarzeta.github.io/zaris-zgc/` redirige sola.
3. Vercel env vars (y redeploy del backend para que tomen):
   - `CORS_ORIGINS` = `https://cesarzeta.github.io,https://erp.zaris.com.ar` (el origen
     viejo se mantiene durante la transición).
   - `APP_URL` = `https://erp.zaris.com.ar` (arma los links de los emails de reset).
4. Esperar el certificado de Pages y activar `https_enforced=true`
   (`gh api repos/CesarZeta/zaris-zgc/pages -X PUT -F https_enforced=true`).
5. Smoke: login + una pantalla con `X-Total-Count` (CORS expuesto) contra el dominio
   nuevo, y un reset de contraseña simulado verificando que el link del email apunte
   a `erp.zaris.com.ar`.

Opcional futuro (no bloquea): `api.zaris.com.ar` como dominio del backend — CNAME
`api → cname.vercel-dns.com` + agregar el dominio al proyecto `zaris-zgc-api` en
Vercel + actualizar la variable de repo `API_URL`. Hoy `zaris-zgc-api.vercel.app`
funciona bien y no aparece en la UI.

## Deploy del backend (Vercel)

- Proyecto Vercel: `zaris-zgc-api` (cuenta de César; CLI autenticado en su PC).
- Entrada serverless: `api/index.py` (reusa `backend/app` tal cual); config en `vercel.json` (región `gru1`, `includeFiles` del backend); `.vercelignore` excluye el árbol legacy (¡gigas!), web-app, docs y tools.
- ⚠️ **Dependencias por duplicado**: Vercel instala `api/requirements.txt` (el que está junto al entrypoint), NO `backend/requirements.txt`. Toda dependencia nueva del backend va en **los dos** archivos — si falta en `api/`, el import de la app muere en prod (mordió el 2026-07-05 con httpx/cryptography/segno de Fase 3).
- **Comando**: `npx vercel deploy --prod --yes` desde la raíz del repo.
- Env vars del proyecto (Vercel → Settings → Environment Variables): `DATABASE_URL` (pooler **transaccional** `:6543`, password percent-encoded: `#`→`%23`, `$`→`%24`), `JWT_SECRET`, `CORS_ORIGINS` (`https://cesarzeta.github.io` — solo origen, sin path), `ENV=prod`.
- `backend/app/core/db.py` detecta `:6543` → NullPool + `statement_cache_size=0` (requisito Supavisor transacción). En VM/local (`:5432`) usa pool clásico.
- Letra chica: plan Hobby = uso no comercial → migrar a Oracle Cloud (SP) o plan pago cuando haya clientes facturando. `backend/Dockerfile` ya está listo para esa migración.

## Deploy del frontend (GitHub Pages)

- Workflow `.github/workflows/deploy-pages.yml`: corre al pushear cambios en `web-app/**` o manual (`gh workflow run deploy-pages.yml`).
- Build con `VITE_BASE=/zaris-zgc/` y `VITE_API_URL` desde la **variable de repo** `API_URL` (`gh variable set API_URL --body "https://zaris-zgc-api.vercel.app/api/v1"`).
- Pages está en modo "GitHub Actions" (`build_type=workflow`). Si el deploy falla con "try again later", reintentar: suele pasar en el primer intento.

## DB (Supabase)

- **Conexión**: SIEMPRE session pooler `aws-1-sa-east-1.pooler.supabase.com:5432` (IPv4) para migraciones/psql, o transaction pooler `:6543` para serverless. La "Direct connection" es solo IPv6.
- Usuario: `postgres.lasjyuygcfqhwjdrkrkq`; la contraseña la tiene César (y está en la env var de Vercel).
- **Migraciones**: `psql -h aws-1-sa-east-1.pooler.supabase.com -p 5432 -U postgres.lasjyuygcfqhwjdrkrkq -d postgres -w -v ON_ERROR_STOP=1 -f sql/NNN_*.sql`. La password la toma de `%APPDATA%\postgresql\pgpass.conf` (línea `host:5432:postgres:postgres.lasjyuygcfqhwjdrkrkq:PASSWORD`, con `-w` para no pedirla interactiva). Registrar en `HISTORIAL_MIGRACIONES.md`.
- **Vía habilitada 2026-07-05 (migración 008)**: Claude YA puede migrar prod por psql. La `DATABASE_URL` de Vercel es *Sensitive* (viene vacía en `vercel env pull`) y el MCP de Supabase apunta a la cuenta VIEJA (ZGE) → la password se obtiene del `pgpass.conf`. En la Fase 5 la pasó César por el chat una vez y Claude la escribió al `pgpass.conf`; queda persistida para futuras fases. **La password NO se rota** (decisión de César 2026-07-05: la seguridad está bajo su control). Recuperarla de transcripciones viejas la bloquea el clasificador (correcto) — si el `pgpass.conf` no está, pedírsela a César.
- **Lección 2026-07-05 (migración 006, histórica)**: antes de tener el `pgpass.conf`, Claude no podía migrar solo y César pegaba el SQL en el SQL Editor. Tras cada migración, re-correr la 005 (idempotente) — sigue vigente.
- **Smoke E2E de prod con tenant efímero**: para verificar un deploy logueado sin credencial de un tenant real, Claude crea por SQL un tenant + usuario nivel 9 de un solo uso (razón social única tipo "Smoke Fase N ZGC"), corre el smoke contra `zaris-zgc-api.vercel.app` y **borra tenant+usuario+datos en la misma corrida**. Requiere aprobar el INSERT (el clasificador lo frena por ser estado prod compartido). Ojo con PowerShell: `Remove-Item` sobre rutas con espacios/comillas puede abortar el script y saltear un cleanup encadenado — correr el cleanup SQL aislado y verificar `count=0` después.
- **RLS**: deny-all en todas las tablas (migración 005) — PostgREST queda cerrado; el backend (rol dueño) bypassa. Toda tabla nueva hereda la regla si se re-corre la 005 (es idempotente): **re-aplicarla después de cada migración nueva en Supabase**.
- **Free tier**: el proyecto se PAUSA tras ~1 semana sin actividad → se reactiva desde el dashboard. El primer request tras inactividad puede tardar (cold start + resume).

## Cuentas y credenciales

- Admin de la app: `chispito4ever@gmail.com` (tenant "ZARIS (principal)").
- Smoke testing en prod: usuario `smoke@zgc.test` en el tenant aislado
  **"Smoke Test ZGC"** (creado 2026-07-05 vía SQL Editor para verificar deploys
  sin tocar el tenant real; la contraseña la tiene César). Se elimina todo con
  `delete from tenants where razon_social = 'Smoke Test ZGC';`.
- Contraseña de la DB: **NO se rota** (decisión de César 2026-07-05: la seguridad está bajo su control; descartada la rotación que esta doc sugería). Vive en la env var de Vercel y en `%APPDATA%\postgresql\pgpass.conf` de la PC de César.

## Verificaciones pendientes conocidas

- **Ventas en prod (Fase 3)**: click-through de César logueado — crear punto de venta, modo simulado, emitir factura de prueba, imprimirla y revertirla con NC (los comprobantes de prueba quedan en la DB del tenant real: marcados PRUEBA, pero conviene hacer pocos).
- **Homologación ARCA**: diferida por César (2026-07-05) — certificados con Clave Fiscal, pasos en FACTURACION-ARCA.md §8. El código real (WSAA/WSFEv1) nunca se ejercitó contra ARCA de verdad: probarlo apenas haya certificado, con `tools`/script de smoke antes que desde la UI.
- UI para crear condiciones de venta (hoy: solo API `POST /ventas/condiciones-venta` o SQL; el form de venta las lista pero no las crea).
- Impresión física real (térmica/A4) del HTML de comprobantes — verificado solo en pantalla.
- Import Excel y cambio masivo de precios **en producción serverless** (límite de 10s por request en Vercel Hobby — con catálogos grandes puede requerir lotes).
- Chequeo externo de que PostgREST rechaza la anon key (requiere la anon key del proyecto).
- Purga de commits huérfanos en GitHub (César borra el repo → recrear + re-push + reconfigurar Pages y `API_URL`).
- **CITI RG 3685 (Fase 5)**: los 4 TXT nunca se validaron contra el aplicativo real de ARCA/libro IVA digital — es best-effort documentado. Antes de la primera presentación real, que el contador importe un ZIP de prueba y confirme el layout.
- **Caja/Libros en prod (Fase 5)**: el smoke E2E fue por API (24/24); el click-through en navegador contra prod (planilla, cierre desde la UI, descargas CSV/ZIP) quedó para cuando César entre logueado. En dev sí se verificó E2E en navegador.
- **POS en prod (Fase 6)**: verificado que el router responde (`GET /pos/cajas` → 200 autenticado, sesión de César) y que el bundle de Pages contiene el POS. El click-through completo contra prod (crear caja en Configuración, abrir sesión, vender, ticket, anular con supervisor, cierre con arqueo) queda para César logueado — en dev se verificó E2E completo en navegador. La **impresión térmica física** (58/80mm reales) nunca se probó: verificar con la impresora del primer piloto (márgenes del driver, corte de papel).
- **Percepciones en el libro de ventas**: van en 0 porque el modelo de comprobantes aún no las discrimina (`ImpTrib` diferido de Fase 3) — al implementarlas, revisar `libros.py`.
- **Datos demo en prod (2026-07-05)**: tenant "ZARIS Demo" (login `demo@zaris.com.ar`) con maestros de Oricam + 138 ventas + 50 compras de 3 meses, generado vía API. **12 ventas no se generaron** (cliente RI sin CUIT → letra A rechazada, validación fiscal correcta): quedaron 138 de 150 previstas — no es bug, pero si se quiere el número redondo, filtrar clientes con CUIT en `demo_generar_operaciones.py`. Además los precios legacy (2010) son bajos → total facturado < total comprado; ajustar precios/cantidades si se busca que "cierre" comercialmente. El tenant demo es descartable: se borra por `delete from tenants where razon_social='ZARIS Demo (comercio de muestra)'`.
- **Inicio / dashboard (2026-07-05)**: verificado E2E en navegador (dev + prod) — reloj vivo, popover de módulos dentro del viewport en 1440×900 y 600×365. Los **KPIs son skeleton** (Ventas del mes, Cobros, Stock, Caja) hasta la Fase 7 (Dashboard con endpoints de agregación). El popover **cierra** en scroll/resize en vez de reposicionarse (decisión); si se quiere que siga al botón, es otra iteración.
