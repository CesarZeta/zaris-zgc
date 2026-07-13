# F16 — Salida de documentos: PDF server-side + email transaccional

> Discovery 2026-07-13 (sesión de mejoras de suite). César aceptó las 5 piezas
> recomendadas en orden de valor (ROADMAP filas 16–20); esta es la 1ª: *"en la
> práctica argentina de 2026, el cliente pide 'mandame la factura' y eso
> significa un PDF por WhatsApp o email"*. UNA pieza de infraestructura que
> resuelve de un golpe: envío de facturas, recuperación de contraseña
> autoservicio, y más adelante avisos (vencimientos, cheques por vencer) y la
> verificación de email del signup (F20).

## 1. Principios

1. **Reusar el núcleo, no copiarlo** (regla §6): el PDF se genera desde el
   MISMO payload que arma `datos_impresion` (`/ventas/comprobantes/{id}/impresion`)
   — se extrae a un helper `_payload_impresion()` que consumen ambos endpoints
   y el envío por email. Una sola fuente de verdad del contenido RG 1415
   (letra, CAE, QR RG 4892, transparencia fiscal Ley 27.743, leyendas).
2. **Patrón de modos ARCA** para el email: `deshabilitado` / **`simulado`**
   (default: registra sin enviar) / `resend` (envío real). La diferencia con
   ARCA: el email es infraestructura **global del SaaS** (env vars, no config
   por tenant) — el remitente es ZARIS, el `reply_to` es el email del tenant.
3. **Todo envío queda registrado** en `email_envios` (por tenant, con `modo`
   sellado): es la observabilidad del canal y, en simulado, la única evidencia.
4. **Dependencia nueva única**: `fpdf2` (puro Python, sin binarios — apto
   Vercel serverless; el veto a WeasyPrint/wkhtmltopdf es el mismo que a
   pyafipws). El QR del PDF sale de `segno` (ya dependencia) como PNG.

## 2. PDF server-side (`services/documentos/pdf_comprobante.py`)

- `pdf_comprobante(payload: dict) -> bytes`: A4, layout espejo del HTML de
  `web-app/src/modules/ventas/impresion.ts` (cabecera con caja de letra +
  código ARCA, emisor/receptor, tabla de renglones con IVA discriminado solo
  en letra A, totales por alícuota, transparencia fiscal, vencimientos,
  observaciones, leyendas, CAE + QR).
- Fuente: Helvetica core de PDF (sin embebido de TTF en v1 — los importes van
  en Courier para el efecto `tabular-nums`). Texto con `latin-1` best-effort
  (lo que no mapea se translitera); los datos argentinos reales son latin-1.
- `GET /ventas/comprobantes/{id}/pdf` → `application/pdf`, guarda
  `requiere("ventas","ver")`, 409 si borrador (mismo criterio que impresión),
  `Content-Disposition` con `FB-0001-00000123.pdf` (tipo + número).
- Queda montado en ROUTERS_COMUNES (el nodo también lo sirve — no necesita
  internet).

## 3. Email transaccional (`services/email_envio.py`)

- Env vars (`config.py`): `EMAIL_MODO` (deshabilitado|simulado|resend, default
  **simulado**), `RESEND_API_KEY`, `EMAIL_FROM` (default
  `ZARIS <no-reply@zaris.com.ar>` — el dominio se verifica en Resend cuando
  César dé de alta la cuenta), `APP_URL` (links en los emails; default
  `http://localhost:5173`, prod = URL de Pages).
- `enviar_email(db, tenant_id, *, destinatario, asunto, cuerpo_html, adjuntos,
  tipo, ref_id, creado_por) -> EmailEnvio` (SIN commit — patrón core):
  - `deshabilitado`: levanta `EmailDeshabilitadoError` → 400 en el endpoint
    (espejo de ARCA deshabilitado).
  - `simulado`: NO sale nada a la red; registra con `estado='simulado'` y el
    cuerpo guardado (la evidencia).
  - `resend`: `POST https://api.resend.com/emails` con httpx (adjuntos en
    base64, `reply_to` = email del tenant si tiene); `estado='enviado'` +
    `proveedor_id`, o `estado='error'` + detalle (el registro del error TAMBIÉN
    queda — el endpoint responde 502 con el detalle, patrón ErrorConexionArca).
- Tabla `email_envios` (migración 026): tenant_id, destinatario, asunto,
  `cuerpo` TEXT **deferred** (regla §6 de columnas pesadas), tipo
  (`comprobante`|`password_reset`), ref_id (uuid libre: comprobante o usuario),
  modo sellado, estado, error, proveedor_id, creado_por, created_at. RLS.
- `GET /emails/envios` (router nuevo `emails.py`, solo nube, guarda
  `configuracion.ver`; filtros tipo/ref_id, listado SIN cuerpo) y
  `GET /emails/envios/{id}` (CON cuerpo, undefer) — bandeja de salida para
  auditoría y, en simulado, para que un admin reenvíe a mano el contenido.

## 4. Envío de comprobantes

- `POST /ventas/comprobantes/{id}/enviar` body `{email?: string}`, guarda
  `requiere("ventas","editar")`:
  - 409 borrador. Destinatario = body.email o email de la entidad del cliente
    (`cliente_id → clientes.entidad_id → entidades.email`); sin ninguno → 422
    "El cliente no tiene email registrado".
  - Genera el PDF (helper compartido) y lo manda como adjunto; asunto
    `"{Tipo} {número} — {razón social del emisor}"`; cuerpo HTML breve con
    total y leyenda de simulado cuando corresponde.
  - Devuelve el registro (`estado` incluido: la UI avisa si fue simulado).
- UI: en `ComprobanteDetalle`, botones **PDF** (descarga autenticada) y
  **Enviar por email** (modal con destinatario editable precargado).

## 5. Recuperación de contraseña autoservicio

- Tabla `password_resets` (026): tenant_id, usuario_id, `token_hash` (sha256
  del token urlsafe de 32 bytes — NUNCA el token en claro), expira_at (1 h),
  usado_at, created_at. RLS.
- `POST /auth/recuperar` body `{email}` — **público, siempre 200** con el
  mismo mensaje (no filtra existencia de usuarios). Si el usuario existe y
  está activo: invalida tokens pendientes, crea uno nuevo y manda el email
  con link `{APP_URL}/restablecer?token=…` (tipo `password_reset`).
- `POST /auth/restablecer` body `{token, password}` (mín. 6): valida hash +
  vigencia + no usado → actualiza `password_hash`, marca `usado_at`. 422
  token inválido/vencido/usado.
- Front: link "Olvidé mi contraseña" en el login → `/recuperar`; página
  `/restablecer` lee `?token=`. Sin pistas de clave.
- El reset asistido por admin (F6.5) sigue intacto.

## 6. Qué NO entra en v1 (diferidos documentados)

- **WhatsApp Business API** (adjuntar el PDF por WhatsApp requiere proveedor
  pago tipo Twilio/360dialog): v1 = descargar el PDF y compartirlo a mano.
- PDF de recibos, OP y presupuestos de compra (el helper genérico queda listo;
  se agregan cuando un piloto los pida — el de VENTAS es el que piden primero).
- Avisos programados (vencimientos, cheques por vencer): necesitan scheduler
  (Vercel cron) — van con F18 observabilidad o pedido de piloto.
- UI de bandeja de salida en Configuración (el endpoint ya existe).
- Plantillas de email por tenant (logo propio, colores): con el primer plan pago.

## 7. Activación del envío real (pendiente César)

1. Crear cuenta free en **Resend** (3.000 emails/mes gratis; alternativa
   Brevo 300/día) y verificar el dominio `zaris.com.ar` (DNS: SPF + DKIM).
2. En Vercel (proyecto `zaris-zgc-api`): `EMAIL_MODO=resend`,
   `RESEND_API_KEY=re_…`, `EMAIL_FROM=ZARIS <no-reply@zaris.com.ar>`,
   `APP_URL=https://cesarzeta.github.io/zaris-zgc`.
3. Redeploy. Sin tocar código: el modo es env-level.
