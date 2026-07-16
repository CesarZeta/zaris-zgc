// Login dedicado del Punto de Venta (adelanto de F13-LAN): entra por
// POST /pos/auth/login y recibe un token de ALCANCE POS — el backend rechaza
// todo lo que esté fuera de la superficie de la caja, y la UI vive en /pos.
// El mismo formulario servirá en el nodo de sucursal (cambia solo la API base).

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, apiPost } from "../lib/api";
import { setSesion } from "../lib/auth";
import type { Sesion } from "../lib/types";
import { PosDevice } from "../modules/pos/POSHeader";
import AuthFooter from "./AuthFooter";
import ZarisLogo from "./ZarisLogo";

export default function POSLoginPage() {
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
      const sesion = await apiPost<Sesion>("/pos/auth/login", { email, password });
      setSesion({ ...sesion, login_at: new Date().toISOString() });
      navigate("/pos");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }

  return (
    <PosDevice centro>
      <form className="login-card" onSubmit={onSubmit}>
        <div className="login-marca">
          <ZarisLogo size={40} />
          <h1 className="login-logo">ZARIS</h1>
        </div>
        <p className="login-sub">ZARIS ERP · Punto de Venta</p>

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
          {cargando ? "Ingresando…" : "Abrir el POS"}
        </button>

        <p className="login-sub" style={{ marginTop: "var(--space-4)" }}>
          <Link to="/login">← Ingresar a la gestión</Link>
        </p>
        <AuthFooter />
      </form>
    </PosDevice>
  );
}
