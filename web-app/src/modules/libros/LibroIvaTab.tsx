// Libro de IVA (ventas o compras) por período mensual. Las NC van en negativo
// y los totales son suma directa de las filas (criterio del backend).

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDescargar, apiGet } from "../../lib/api";
import type { LibroIva } from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const periodoActual = () => new Date().toISOString().slice(0, 7);

export default function LibroIvaTab({ libro }: { libro: "ventas" | "compras" }) {
  const [periodo, setPeriodo] = useState(periodoActual());
  const [data, setData] = useState<LibroIva | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const res = await apiGet<LibroIva>(`/libros/iva-${libro}?periodo=${periodo}`);
      setData(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el libro");
    } finally {
      setCargando(false);
    }
  }, [libro, periodo]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function descargarCsv() {
    setOcupado(true);
    setError(null);
    try {
      await apiDescargar(
        `/libros/iva-${libro}.csv?periodo=${periodo}`,
        `libro-iva-${libro}-${periodo}.csv`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo descargar el CSV");
    } finally {
      setOcupado(false);
    }
  }

  const t = data?.totales;

  return (
    <>
      {error && <div className="login-error">{error}</div>}

      <div className="toolbar">
        <input
          type="month"
          className="input"
          style={{ width: 170 }}
          value={periodo}
          onChange={(ev) => setPeriodo(ev.target.value)}
        />
        <div style={{ flex: 1 }} />
        <button className="btn btn-ghost" disabled={ocupado || !data} onClick={() => void descargarCsv()}>
          Descargar CSV
        </button>
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Comprobante</th>
              <th>{libro === "ventas" ? "Cliente" : "Proveedor"}</th>
              <th>CUIT/Doc</th>
              <th className="num">Neto grav.</th>
              <th className="num">No grav.</th>
              <th className="num">Exento</th>
              <th className="num">IVA</th>
              <th className="num">Percep.</th>
              <th className="num">Total</th>
            </tr>
          </thead>
          <tbody>
            {data?.filas.map((f) => (
              <tr key={f.id}>
                <td className="mono">{f.fecha}</td>
                <td className="mono">
                  <b>{f.tipo_codigo}</b> {String(f.punto_venta).padStart(5, "0")}-
                  {String(f.numero).padStart(8, "0")}
                </td>
                <td>{f.contraparte}</td>
                <td className="mono">{f.doc_nro ?? "—"}</td>
                <td className="num mono">{fmt.format(Number(f.neto_gravado))}</td>
                <td className="num mono">{fmt.format(Number(f.no_gravado))}</td>
                <td className="num mono">{fmt.format(Number(f.exento))}</td>
                <td className="num mono">{fmt.format(Number(f.iva))}</td>
                <td className="num mono">{fmt.format(Number(f.percepciones))}</td>
                <td className="num mono">{fmt.format(Number(f.total))}</td>
              </tr>
            ))}
          </tbody>
          {t && data && data.filas.length > 0 && (
            <tfoot>
              <tr style={{ fontWeight: 700 }}>
                <td colSpan={4}>Totales del período</td>
                <td className="num mono">{fmt.format(Number(t.neto_gravado))}</td>
                <td className="num mono">{fmt.format(Number(t.no_gravado))}</td>
                <td className="num mono">{fmt.format(Number(t.exento))}</td>
                <td className="num mono">{fmt.format(Number(t.iva))}</td>
                <td className="num mono">{fmt.format(Number(t.percepciones))}</td>
                <td className="num mono">{fmt.format(Number(t.total))}</td>
              </tr>
              {t.por_alicuota.map((a) => (
                <tr key={a.tasa} className="fila-anulada">
                  <td colSpan={4}>IVA {fmt.format(Number(a.tasa))}%</td>
                  <td className="num mono">{fmt.format(Number(a.base))}</td>
                  <td colSpan={2}></td>
                  <td className="num mono">{fmt.format(Number(a.importe))}</td>
                  <td colSpan={2}></td>
                </tr>
              ))}
            </tfoot>
          )}
        </table>
        {!cargando && data && data.filas.length === 0 && (
          <div className="vacio">Sin comprobantes fiscales en {periodo}</div>
        )}
      </div>
    </>
  );
}
