import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, apiPost } from "../lib/api";
import { setSesion } from "../lib/auth";
import type { Sesion } from "../lib/types";
import AuthFooter from "./AuthFooter";
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
      setSesion({ ...sesion, login_at: new Date().toISOString() });
      navigate("/inicio");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo conectar con el servidor");
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-split">
        <aside className="login-brand">
          <div className="login-marca">
            <ZarisLogo size={40} />
            <span className="login-logo">ZARIS</span>
            <span className="login-brand-erp">ERP</span>
          </div>
          <p className="login-brand-pitch">
            Gestión integral para tu empresa: ventas, compras, stock, tesorería, contabilidad y
            facturación electrónica — con puntos de venta que siguen operando sin internet.
          </p>
          <ul className="login-brand-lista">
            <li>Facturación electrónica ARCA (A/B/C)</li>
            <li>Stock multi-depósito y listas de precios</li>
            <li>Contabilidad, libros de IVA y tesorería</li>
            <li>POS multi-sucursal por rubro</li>
          </ul>
          <a
            className="login-brand-link"
            href="https://zaris.com.ar"
            target="_blank"
            rel="noreferrer"
          >
            Conocé más en zaris.com.ar →
          </a>
        </aside>

        <form className="login-card" onSubmit={onSubmit}>
          <p className="login-sub">Ingresá a tu cuenta</p>

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

          <p className="login-sub" style={{ marginTop: "var(--space-4)", marginBottom: 0 }}>
            <Link to="/recuperar">Olvidé mi contraseña</Link>
          </p>
        </form>
      </div>
      <AuthFooter />
    </div>
  );
}
