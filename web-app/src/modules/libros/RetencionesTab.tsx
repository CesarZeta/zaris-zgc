// Registro básico de retenciones (RET_CLI/RET_PROV del legacy): sufridas (el
// cliente nos retuvo al cobrar) y practicadas (retuvimos al proveedor al
// pagar). El resumen por régimen es lo que se lleva el contador.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiDescargar, apiGet, apiPost } from "../../lib/api";
import type { ResumenRetencion, Retencion } from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const hoy = () => new Date().toISOString().slice(0, 10);
const REGIMENES = ["IVA", "IIBB", "Ganancias", "SUSS", "otro"];

export default function RetencionesTab() {
  const [filas, setFilas] = useState<Retencion[]>([]);
  const [resumen, setResumen] = useState<ResumenRetencion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const [tipo, setTipo] = useState<"sufrida" | "practicada">("sufrida");
  const [regimen, setRegimen] = useState("IVA");
  const [fecha, setFecha] = useState(hoy());
  const [importe, setImporte] = useState("");
  const [certificado, setCertificado] = useState("");
  const [descripcion, setDescripcion] = useState("");

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [lista, res] = await Promise.all([
        apiGet<Retencion[]>("/libros/retenciones"),
        apiGet<ResumenRetencion[]>("/libros/retenciones/resumen"),
      ]);
      setFilas(lista.data);
      setResumen(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar retenciones");
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function agregar() {
    setOcupado(true);
    setError(null);
    try {
      await apiPost("/libros/retenciones", {
        tipo,
        regimen,
        fecha,
        importe,
        nro_certificado: certificado.trim() || null,
        descripcion: descripcion.trim() || null,
      });
      setImporte("");
      setCertificado("");
      setDescripcion("");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la retención");
    } finally {
      setOcupado(false);
    }
  }

  async function borrar(r: Retencion) {
    if (!window.confirm(`¿Eliminar la retención de ${fmt.format(Number(r.importe))}?`)) return;
    setOcupado(true);
    try {
      await apiDelete(`/libros/retenciones/${r.id}`);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo eliminar");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      {error && <div className="login-error">{error}</div>}

      {resumen.length > 0 && (
        <div className="toolbar" style={{ flexWrap: "wrap" }}>
          {resumen.map((r) => (
            <span key={`${r.tipo}-${r.regimen}`} className="chip chip-ok">
              {r.tipo} {r.regimen}: {fmt.format(Number(r.total))} ({r.cantidad})
            </span>
          ))}
          <div style={{ flex: 1 }} />
          <button
            className="btn btn-ghost"
            disabled={ocupado}
            onClick={() => void apiDescargar("/libros/retenciones.csv", "retenciones.csv")}
          >
            Descargar CSV
          </button>
        </div>
      )}

      <div className="tabla-card" style={{ padding: 12, marginBottom: 12 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
          <div className="field">
            <label>Tipo</label>
            <select className="select" value={tipo} onChange={(ev) => setTipo(ev.target.value as "sufrida" | "practicada")}>
              <option value="sufrida">Sufrida (nos retuvieron)</option>
              <option value="practicada">Practicada (retuvimos)</option>
            </select>
          </div>
          <div className="field">
            <label>Régimen</label>
            <select className="select" value={regimen} onChange={(ev) => setRegimen(ev.target.value)}>
              {REGIMENES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Fecha</label>
            <input type="date" className="input" value={fecha} onChange={(ev) => setFecha(ev.target.value)} />
          </div>
          <div className="field">
            <label>Importe</label>
            <input className="input mono" type="number" step="0.01" min="0.01" value={importe} onChange={(ev) => setImporte(ev.target.value)} />
          </div>
          <div className="field">
            <label>Certificado</label>
            <input className="input mono" value={certificado} onChange={(ev) => setCertificado(ev.target.value)} />
          </div>
          <div className="field" style={{ flex: 1, minWidth: 160 }}>
            <label>Descripción</label>
            <input className="input" value={descripcion} onChange={(ev) => setDescripcion(ev.target.value)} />
          </div>
          <button
            className="btn btn-primary"
            disabled={ocupado || !importe || Number(importe) <= 0}
            onClick={() => void agregar()}
          >
            + Registrar
          </button>
        </div>
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Tipo</th>
              <th>Régimen</th>
              <th>Contraparte</th>
              <th>Certificado</th>
              <th>Descripción</th>
              <th className="num">Importe</th>
              <th style={{ width: 90 }}></th>
            </tr>
          </thead>
          <tbody>
            {filas.map((r) => (
              <tr key={r.id}>
                <td className="mono">{r.fecha}</td>
                <td>
                  <span className={`chip ${r.tipo === "sufrida" ? "chip-ok" : "chip-borrador"}`}>
                    {r.tipo}
                  </span>
                </td>
                <td>{r.regimen}</td>
                <td>{r.contraparte ?? "—"}</td>
                <td className="mono">{r.nro_certificado ?? "—"}</td>
                <td>{r.descripcion ?? "—"}</td>
                <td className="num mono">{fmt.format(Number(r.importe))}</td>
                <td className="acciones">
                  <button className="mini-btn" disabled={ocupado} onClick={() => void borrar(r)}>
                    borrar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filas.length === 0 && <div className="vacio">Sin retenciones registradas</div>}
      </div>
    </>
  );
}
