// Catálogo de conceptos de caja (CONC_CAJ del legacy): nombre + entrada/salida.
// No se borran (la historia los referencia): se desactivan.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPatch, apiPost } from "../../lib/api";
import type { ConceptoCaja } from "../../lib/types";

export default function ConceptosTab() {
  const [filas, setFilas] = useState<ConceptoCaja[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<"entrada" | "salida">("entrada");

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const { data } = await apiGet<ConceptoCaja[]>("/caja/conceptos?incluir_inactivos=true");
      setFilas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar conceptos");
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function agregar() {
    setOcupado(true);
    setError(null);
    try {
      await apiPost("/caja/conceptos", { nombre: nombre.trim(), tipo });
      setNombre("");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el concepto");
    } finally {
      setOcupado(false);
    }
  }

  async function alternar(c: ConceptoCaja) {
    setOcupado(true);
    setError(null);
    try {
      await apiPatch(`/caja/conceptos/${c.id}`, { activo: !c.activo });
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      {error && <div className="login-error">{error}</div>}

      <div className="toolbar">
        <input
          className="input"
          style={{ maxWidth: 280 }}
          placeholder="Nombre del concepto"
          value={nombre}
          onChange={(ev) => setNombre(ev.target.value)}
        />
        <select
          className="select toolbar-select"
          value={tipo}
          onChange={(ev) => setTipo(ev.target.value as "entrada" | "salida")}
        >
          <option value="entrada">Entrada</option>
          <option value="salida">Salida</option>
        </select>
        <button
          className="btn btn-primary"
          disabled={ocupado || nombre.trim().length < 2}
          onClick={() => void agregar()}
        >
          + Agregar
        </button>
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Estado</th>
              <th style={{ width: 110 }}></th>
            </tr>
          </thead>
          <tbody>
            {filas.map((c) => (
              <tr key={c.id} className={c.activo ? "" : "fila-anulada"}>
                <td>{c.nombre}</td>
                <td>
                  <span className={`chip ${c.tipo === "entrada" ? "chip-ok" : "chip-anulado"}`}>
                    {c.tipo}
                  </span>
                </td>
                <td>{c.activo ? "activo" : "inactivo"}</td>
                <td className="acciones">
                  <button className="mini-btn" disabled={ocupado} onClick={() => void alternar(c)}>
                    {c.activo ? "desactivar" : "activar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filas.length === 0 && (
          <div className="vacio">Sin conceptos: creá los de uso diario (retiros, gastos, aportes)</div>
        )}
      </div>
    </>
  );
}
