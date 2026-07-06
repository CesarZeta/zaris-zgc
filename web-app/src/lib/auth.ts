import type { Sesion } from "./types";

const KEY = "zgc_session";

export function getSesion(): Sesion | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Sesion) : null;
  } catch {
    return null;
  }
}

export function setSesion(sesion: Sesion) {
  localStorage.setItem(KEY, JSON.stringify(sesion));
}

export function clearSesion() {
  localStorage.removeItem(KEY);
}

// ===== Permisos por módulo (Fase 6.5) =====

const NIVEL_ACCION: Record<string, number> = { ver: 1, editar: 2, anular: 3 };

/** ¿La sesión tiene `accion` sobre `modulo`? Una sesión sin mapa de permisos
 *  (logueada antes de la Fase 6.5) ve todo en la UI: el backend igual valida
 *  cada request — el frontend nunca es la única defensa. */
export function tienePermiso(modulo: string, accion: "ver" | "editar" | "anular" = "ver"): boolean {
  const sesion = getSesion();
  if (!sesion) return false;
  if (!sesion.permisos) return true;
  const nivel = sesion.permisos[modulo];
  return nivel !== undefined && (NIVEL_ACCION[nivel] ?? 0) >= NIVEL_ACCION[accion];
}
