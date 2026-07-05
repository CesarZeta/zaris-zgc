// Exportes del período para el contador: CSVs de los libros (Excel es-AR) y
// CITI RG 3685 (4 TXT de ancho fijo en un ZIP, régimen de información de
// compras y ventas / libro IVA digital). El contador los valida antes de
// presentar.

import { useState } from "react";
import { ApiError, apiDescargar } from "../../lib/api";

const periodoActual = () => new Date().toISOString().slice(0, 7);

export default function ExportarTab() {
  const [periodo, setPeriodo] = useState(periodoActual());
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function bajar(path: string, nombre: string) {
    setOcupado(true);
    setError(null);
    setMensaje(null);
    try {
      await apiDescargar(path, nombre);
      setMensaje(`${nombre} descargado.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo descargar");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      <div className="toolbar">
        <input
          type="month"
          className="input"
          style={{ width: 170 }}
          value={periodo}
          onChange={(ev) => setPeriodo(ev.target.value)}
        />
      </div>

      <div className="tabla-card" style={{ padding: 16 }}>
        <h2 style={{ marginTop: 0 }}>Para el contador — {periodo}</h2>
        <table className="tabla">
          <tbody>
            <tr>
              <td>
                <b>Libro IVA Ventas (CSV)</b>
                <br />
                Todas las columnas del libro, NC en negativo. Se abre directo en Excel.
              </td>
              <td className="acciones">
                <button
                  className="btn btn-ghost"
                  disabled={ocupado}
                  onClick={() =>
                    void bajar(`/libros/iva-ventas.csv?periodo=${periodo}`, `libro-iva-ventas-${periodo}.csv`)
                  }
                >
                  Descargar
                </button>
              </td>
            </tr>
            <tr>
              <td>
                <b>Libro IVA Compras (CSV)</b>
                <br />
                Compras registradas del período fiscal (por período IVA sellado).
              </td>
              <td className="acciones">
                <button
                  className="btn btn-ghost"
                  disabled={ocupado}
                  onClick={() =>
                    void bajar(`/libros/iva-compras.csv?periodo=${periodo}`, `libro-iva-compras-${periodo}.csv`)
                  }
                >
                  Descargar
                </button>
              </td>
            </tr>
            <tr>
              <td>
                <b>CITI / Libro IVA Digital (RG 3685)</b>
                <br />
                ZIP con REGINFO_CV_VENTAS_CBTE, VENTAS_ALICUOTAS, COMPRAS_CBTE y
                COMPRAS_ALICUOTAS en ancho fijo, listos para importar en el aplicativo.
              </td>
              <td className="acciones">
                <button
                  className="btn btn-primary"
                  disabled={ocupado}
                  onClick={() => void bajar(`/libros/citi?periodo=${periodo}`, `citi-${periodo}.zip`)}
                >
                  Descargar ZIP
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </>
  );
}
