# ZGC — Runbook de deploy y operación

> Estado al 2026-07-04 (Etapa A completada). Stack: GitHub Pages → Vercel gru1 → Supabase sa-east-1.

## URLs de producción

- **App**: https://cesarzeta.github.io/zaris-zgc/
- **API**: https://zaris-zgc-api.vercel.app (health: `/health`)
- **DB**: Supabase proyecto `zaris-zgc` (cuenta nueva de César, org "ZARIS GESTION COMERCIAL", región sa-east-1)

## Deploy del backend (Vercel)

- Proyecto Vercel: `zaris-zgc-api` (cuenta de César; CLI autenticado en su PC).
- Entrada serverless: `api/index.py` (reusa `backend/app` tal cual); config en `vercel.json` (región `gru1`, `includeFiles` del backend); `.vercelignore` excluye el árbol legacy (¡gigas!), web-app, docs y tools.
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
- **Migraciones**: `psql -h aws-1-sa-east-1.pooler.supabase.com -p 5432 -U postgres.lasjyuygcfqhwjdrkrkq -d postgres -v ON_ERROR_STOP=1 -f sql/NNN_*.sql` (PGPASSWORD en el entorno). Registrar en `HISTORIAL_MIGRACIONES.md`.
- **RLS**: deny-all en todas las tablas (migración 005) — PostgREST queda cerrado; el backend (rol dueño) bypassa. Toda tabla nueva hereda la regla si se re-corre la 005 (es idempotente): **re-aplicarla después de cada migración nueva en Supabase**.
- **Free tier**: el proyecto se PAUSA tras ~1 semana sin actividad → se reactiva desde el dashboard. El primer request tras inactividad puede tardar (cold start + resume).

## Cuentas y credenciales

- Admin de la app: `chispito4ever@gmail.com` (tenant "ZARIS (principal)").
- Higiene pendiente: la contraseña de la DB circuló por el chat de la sesión del 2026-07-04 — rotarla en algún momento (Supabase → Settings → Database → Reset password) y actualizar la env var `DATABASE_URL` en Vercel + redeploy.

## Verificaciones pendientes conocidas

- Import Excel y cambio masivo de precios **en producción serverless** (límite de 10s por request en Vercel Hobby — con catálogos grandes puede requerir lotes).
- Chequeo externo de que PostgREST rechaza la anon key (requiere la anon key del proyecto).
- Purga de commits huérfanos en GitHub (César borra el repo → recrear + re-push + reconfigurar Pages y `API_URL`).
