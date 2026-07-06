// Mensajes estándar de página: error (rojo) y éxito (verde, descartable).
// Renderizan null si no hay contenido, así el llamador no necesita el `&&`.

import type { ReactNode } from "react";

export function AlertError({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <div className="login-error">{children}</div>;
}

export function AlertOk({
  children,
  onCerrar,
}: {
  children: ReactNode;
  onCerrar?: () => void;
}) {
  if (!children) return null;
  return (
    <div className="import-resultado">
      {children}
      {onCerrar && (
        <button type="button" className="btn-cerrar" onClick={onCerrar} aria-label="Cerrar">
          ✕
        </button>
      )}
    </div>
  );
}
