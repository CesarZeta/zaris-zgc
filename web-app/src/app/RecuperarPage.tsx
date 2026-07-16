// Recuperación de contraseña autoservicio (F16 — DISENO-SALIDA-DOCUMENTOS.md §5).
// El backend responde SIEMPRE el mismo mensaje (no filtra existencia de usuarios).

import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, apiPost } from "../lib/api";
import AuthFooter from "./AuthFooter";
import ZarisLogo from "./ZarisLogo";

export default function RecuperarPage() {
  const [email, setEmail] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const res = await apiPost<{ detail: string }>("/auth/recuperar", { email });
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
        <p className="login-sub">Recuperar contraseña</p>

        {error && <div className="login-error">{error}</div>}

        {mensaje ? (
          <p style={{ marginTop: "var(--space-4)" }}>{mensaje}</p>
        ) : (
          <>
            <div className="field">
              <label htmlFor="email">Email de tu usuario</label>
              <input
                id="email"
                className="input"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
                required
              />
            </div>
            <button className="btn btn-primary btn-block" type="submit" disabled={cargando}>
              {cargando ? "Enviando…" : "Enviarme el enlace"}
            </button>
          </>
        )}

        <p className="login-sub" style={{ marginTop: "var(--space-4)" }}>
          <Link to="/login">← Volver al ingreso</Link>
        </p>
      </form>
      <AuthFooter />
    </div>
  );
}
