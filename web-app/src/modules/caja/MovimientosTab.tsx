// Movimientos manuales de caja: alta con concepto (que define entrada/salida),
// medio e importe; se pueden borrar mientras la fecha no esté cerrada.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPost } from "../../lib/api";
import type { CajaMovimiento, ConceptoCaja } from "../../lib/types";
import { MEDIOS_PAGO } from "../../lib/types";
import { useDialogos } from "../../components/dialogos";
import { etiquetaCuenta, useCuentasBancarias } from "../../components/useCuentasBancarias";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const hoy = () => new Date().toISOString().slice(0, 10);

export default function MovimientosTab() {
  const [desde, setDesde] = useState(hoy());
  const [hasta, setHasta] = useState(hoy());
  const [filas, setFilas] = useState<CajaMovimiento[]>([]);
  const [conceptos, setConceptos] = useState<ConceptoCaja[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  // alta
  const [fecha, setFecha] = useState(hoy());
  const [conceptoId, setConceptoId] = useState("");
  const [medio, setMedio] = useState("efectivo");
  const [importe, setImporte] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [cuentaBancariaId, setCuentaBancariaId] = useState("");
  const cuentas = useCuentasBancarias();

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const { data } = await apiGet<CajaMovimiento[]>(
        `/caja/movimientos?desde=${desde}&hasta=${hasta}`,
      );
      setFilas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar movimientos");
    }
  }, [desde, hasta]);

  useEffect(() => {
    void cargar();
    void (async () => {
      try {
        const { data } = await apiGet<ConceptoCaja[]>("/caja/conceptos");
        setConceptos(data);
        if (data.length > 0) setConceptoId((prev) => prev || data[0].id);
      } catch {
        /* el error visible lo da la tabla */
      }
    })();
  }, [cargar]);

  async function agregar() {
    setOcupado(true);
    setError(null);
    try {
      await apiPost("/caja/movimientos", {
        fecha,
        concepto_id: conceptoId,
        medio,
        importe,
        descripcion: descripcion.trim() || null,
        cuenta_bancaria_id:
          medio === "transferencia" && cuentaBancariaId ? cuentaBancariaId : null,
      });
      setImporte("");
      setDescripcion("");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el movimiento");
    } finally {
      setOcupado(false);
    }
  }

  async function borrar(m: CajaMovimiento) {
    if (!(await confirmar(`¿Eliminar el movimiento de ${fmt.format(Number(m.importe))}?`))) return;
    setOcupado(true);
    setError(null);
    try {
      await apiDelete(`/caja/movimientos/${m.id}`);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    } finally {
      setOcupado(false);
    }
  }

  const concepto = conceptos.find((c) => c.id === conceptoId);

  return (
    <>
      {error && <div className="login-error">{error}</div>}

      <div className="toolbar">
        <input type="date" className="input" style={{ width: 160 }} value={desde} onChange={(ev) => setDesde(ev.target.value)} />
        <span>→</span>
        <input type="date" className="input" style={{ width: 160 }} value={hasta} onChange={(ev) => setHasta(ev.target.value)} />
      </div>

      <div className="tabla-card" style={{ padding: 12, marginBottom: 12 }}>
        <div className="fila" style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
          <div className="field">
            <label>Fecha</label>
            <input type="date" className="input" value={fecha} onChange={(ev) => setFecha(ev.target.value)} />
          </div>
          <div className="field" style={{ minWidth: 200 }}>
            <label>Concepto</label>
            <select className="select" value={conceptoId} onChange={(ev) => setConceptoId(ev.target.value)}>
              {conceptos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre} ({c.tipo})
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Medio</label>
            <select className="select" value={medio} onChange={(ev) => setMedio(ev.target.value)}>
              {Object.entries(MEDIOS_PAGO).map(([v, n]) => (
                <option key={v} value={v}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          {medio === "transferencia" && cuentas.length > 0 && (
            <div className="field">
              <label>Cuenta bancaria</label>
              <select
                className="select"
                value={cuentaBancariaId}
                onChange={(ev) => setCuentaBancariaId(ev.target.value)}
              >
                <option value="">— sin especificar —</option>
                {cuentas.map((c) => (
                  <option key={c.id} value={c.id}>
                    {etiquetaCuenta(c)}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="field">
            <label>Importe</label>
            <input
              className="input mono"
              type="number"
              step="0.01"
              min="0.01"
              value={importe}
              onChange={(ev) => setImporte(ev.target.value)}
            />
          </div>
          <div className="field" style={{ flex: 1, minWidth: 180 }}>
            <label>Descripción</label>
            <input className="input" value={descripcion} onChange={(ev) => setDescripcion(ev.target.value)} />
          </div>
          <button
            className="btn btn-primary"
            disabled={ocupado || !conceptoId || !importe || Number(importe) <= 0}
            onClick={() => void agregar()}
          >
            + {concepto?.tipo === "salida" ? "Salida" : "Entrada"}
          </button>
        </div>
        {conceptos.length === 0 && (
          <div className="vacio">Primero creá conceptos de caja en la pestaña Conceptos</div>
        )}
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Concepto</th>
              <th>Tipo</th>
              <th>Medio</th>
              <th>Descripción</th>
              <th className="num">Importe</th>
              <th style={{ width: 90 }}></th>
            </tr>
          </thead>
          <tbody>
            {filas.map((m) => (
              <tr key={m.id}>
                <td className="mono">{m.fecha}</td>
                <td>{m.concepto_nombre}</td>
                <td>
                  <span className={`chip ${m.tipo === "entrada" ? "chip-ok" : "chip-anulado"}`}>
                    {m.tipo}
                  </span>
                </td>
                <td>{MEDIOS_PAGO[m.medio] ?? m.medio}</td>
                <td>{m.descripcion ?? "—"}</td>
                <td className="num mono">
                  {m.tipo === "salida" && "-"}
                  {fmt.format(Number(m.importe))}
                </td>
                <td className="acciones">
                  <button className="mini-btn" disabled={ocupado} onClick={() => void borrar(m)}>
                    borrar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filas.length === 0 && <div className="vacio">Sin movimientos en el rango</div>}
      </div>
      {dialogos}
    </>
  );
}
