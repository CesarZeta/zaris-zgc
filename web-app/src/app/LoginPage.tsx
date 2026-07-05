import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, apiPost } from "../lib/api";
import { setSesion } from "../lib/auth";
import type { Sesion } from "../lib/types";
import ZarisLogo from "./ZarisLogo";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCargando(true);
    try {
      const sesion = await apiPost<Sesion>("/auth/login", { email, password });
      setSesion(sesion);
      navigate("/inicio");
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
        <p className="login-sub">Gestión Comercial</p>

        {error && <div className="login-error">{error}</div>}

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            className="input"
            type="text"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoFocus
          />
        </div>
        <div className="field">
          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button className="btn btn-primary btn-block" type="submit" disabled={cargando}>
          {cargando ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
    </div>
  );
}
