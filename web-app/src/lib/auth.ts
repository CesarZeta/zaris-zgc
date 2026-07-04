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
