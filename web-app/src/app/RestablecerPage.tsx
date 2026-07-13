// Restablecer contraseña con el token del email (F16). El token es de un
// solo uso y vence a la hora; sin token válido el backend responde 422.

import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, apiPost } from "../lib/api";
import ZarisLogo from "./ZarisLogo";

export default function RestablecerPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("La contraseña debe tener al menos 6 caracteres");
      return;
    }
    if (password !== confirmar) {
      setError("Las contraseñas no coinciden");
      return;
    }
    setCargando(true);
    try {
      const res = await apiPost<{ detail: string }>("/auth/restablecer", { token, password });
      setMensaje(res.detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <div className="login-marca">
          <ZarisLogo size={40} />
          <h1 className="login-logo">ZARIS</h1>
        </div>
        <p className="login-sub">Nueva contraseña</p>

        {error && <div className="login-error">{error}</div>}

        {mensaje ? (
          <p style={{ marginTop: "var(--space-4)" }}>{mensaje}</p>
        ) : !token ? (
          <p style={{ marginTop: "var(--space-4)" }}>
            Falta el enlace del email — pedí uno nuevo desde el login.
          </p>
        ) : (
          <>
            <div className="field">
              <label htmlFor="password">Contraseña nueva</label>
              <input
                id="password"
                className="input"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
                required
              />
            </div>
            <div className="field">
              <label htmlFor="confirmar">Repetir contraseña</label>
              <input
                id="confirmar"
                className="input"
                type="password"
                autoComplete="new-password"
                value={confirmar}
                onChange={(e) => setConfirmar(e.target.value)}
                required
              />
            </div>
            <button className="btn btn-primary btn-block" type="submit" disabled={cargando}>
              {cargando ? "Guardando…" : "Guardar contraseña"}
            </button>
          </>
        )}

        <p className="login-sub" style={{ marginTop: "var(--space-4)" }}>
          <Link to="/login">← Ir al ingreso</Link>
        </p>
      </form>
    </div>
  );
}
