/**
 * Fechas de NEGOCIO en el front (fix 2026-09-13, par de backend/app/core/fechas.py).
 *
 * NUNCA usar `new Date().toISOString().slice(0, 10)` para «hoy»: `toISOString`
 * es UTC, y después de las 21:00 hora argentina devuelve MAÑANA — la planilla
 * de caja, la hoja de ruta o el backup pedían el día equivocado. Estos helpers
 * usan la fecha LOCAL del navegador (la caja y la gestión están en Argentina).
 * `tools/test_fechas_dev.py` guarda la regla con un grep sobre el repo.
 */

/** yyyy-mm-dd de una fecha en la zona local del navegador. */
export function fechaISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

/** yyyy-mm-dd de HOY (local). */
export function hoyISO(): string {
  return fechaISO(new Date());
}

/** yyyy-mm-dd de hoy ± n días (local; n negativo = hacia atrás). */
export function hoyMasDiasISO(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return fechaISO(d);
}
