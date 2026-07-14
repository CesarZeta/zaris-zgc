// Backup por tenant (F18 — DISENO-BACKUP-OBSERVABILIDAD.md §4): un botón que
// descarga el ZIP completo. Las descargas anteriores se ven en Auditoría
// (acción "Backup del tenant descargado") — no hay historial propio.
import { useState } from "react";
import { ApiError, apiDescargar } from "../../lib/api";
import { tienePermiso } from "../../lib/auth";

export default function BackupSection() {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const puedeEditar = tienePermiso("configuracion", "editar");

  if (!puedeEditar) return null;

  async function descargar() {
    setOcupado(true);
    setError(null);
    setMensaje(null);
    try {
      const hoy = new Date().toISOString().slice(0, 10);
      await apiDescargar("/backup/export.zip", `backup-zgc-${hoy}.zip`);
      setMensaje("Backup descargado. La descarga quedó registrada en Auditoría.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo generar el backup");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="config-card">
      <div className="seccion">Backup de datos</div>
      <p className="config-ayuda">
        Descargá un ZIP con <strong>todos los datos de tu empresa</strong>: un CSV por tabla del
        sistema (abrible en Excel) más un manifest con los conteos. No incluye contraseñas ni el
        certificado ARCA. Para listados con formato seguí usando los exports de cada pantalla —
        este backup es la garantía de que tus datos son tuyos.
      </p>
      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}
      <button className="btn btn-primary" disabled={ocupado} onClick={() => void descargar()}>
        {ocupado ? "Generando…" : "Descargar backup completo"}
      </button>
    </div>
  );
}
