import { clearSesion, getSesion } from "./auth";

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<{ data: T; headers: Headers }> {
  const sesion = getSesion();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (sesion) headers.Authorization = `Bearer ${sesion.access_token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401 && !path.startsWith("/auth/login")) {
    clearSesion();
    window.location.href = "/login";
    throw new ApiError(401, "Sesión vencida");
  }
  if (!res.ok) {
    let detalle = `Error ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detalle = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) detalle = body.detail[0].msg;
    } catch {
      /* cuerpo no-JSON: queda el genérico */
    }
    throw new ApiError(res.status, detalle);
  }
  return { data: (await res.json()) as T, headers: res.headers };
}

export async function apiGet<T>(path: string): Promise<{ data: T; headers: Headers }> {
  return request<T>(path);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return (await request<T>(path, { method: "POST", body: JSON.stringify(body) })).data;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  return (await request<T>(path, { method: "PUT", body: JSON.stringify(body) })).data;
}
