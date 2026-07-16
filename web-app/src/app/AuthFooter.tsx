// Pie común de las pantallas de acceso (login gestión/POS, recuperar,
// restablecer): versión del software, copyright y link a la landing.
import { APP_VERSION } from "../lib/version";

export default function AuthFooter() {
  return (
    <p className="auth-footer">
      ZARIS ERP <span className="auth-footer-version">v{APP_VERSION}</span> · ©{" "}
      {new Date().getFullYear()} ZARIS ·{" "}
      <a href="https://zaris.com.ar" target="_blank" rel="noreferrer">
        zaris.com.ar
      </a>
    </p>
  );
}
