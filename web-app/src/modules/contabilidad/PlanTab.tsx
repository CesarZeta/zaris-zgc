// Plan de cuentas: árbol plano ordenado por código, alta de cuentas propias
// y edición de nombre/activa. Las del plan base (es_sistema) se renombran
// pero no se inactivan ni borran.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiPost, apiPut } from "../../lib/api";
import { AlertError } from "../../components/Alertas";
import type { Cuenta } from "./tipos";
import { TIPO_LABEL } from "./tipos";

export default function PlanTab({
  cuentas,
  onRefrescar,
}: {
  cuentas: Cuenta[];
  onRefrescar: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [editando, setEditando] = useState<string | null>(null);
  const [nombreEdit, setNombreEdit] = useState("");
  const [alta, setAlta] = useState({ codigo: "", nombre: "", tipo: "activo", padre_id: "" });

  const guardarNombre = useCallback(
    async (c: Cuenta) => {
      try {
        await apiPut(`/contabilidad/plan/${c.id}`, { nombre: nombreEdit });
        setEditando(null);
        onRefrescar();
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo renombrar");
      }
    },
    [nombreEdit, onRefrescar],
  );

  useEffect(() => setError(null), [cuentas]);

  async function crear() {
    setError(null);
    try {
      await apiPost("/contabilidad/plan", {
        codigo: alta.codigo.trim(),
        nombre: alta.nombre.trim(),
        tipo: alta.tipo,
        imputable: true,
        padre_id: alta.padre_id || null,
      });
      setAlta({ codigo: "", nombre: "", tipo: "activo", padre_id: "" });
      onRefrescar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la cuenta");
    }
  }

  async function toggleActiva(c: Cuenta) {
    setError(null);
    try {
      await apiPut(`/contabilidad/plan/${c.id}`, { activa: !c.activa });
      onRefrescar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el estado");
    }
  }

  return (
    <>
      <AlertError>{error}</AlertError>
      <div className="tabla-card" style={{ padding: 12, marginBottom: 12 }}>
        <div className="fila" style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
          <div className="field">
            <label>Código</label>
            <input className="input mono" style={{ width: 120 }} placeholder="1.2.05"
              value={alta.codigo} onChange={(ev) => setAlta({ ...alta, codigo: ev.target.value })} />
          </div>
          <div className="field" style={{ flex: 1, minWidth: 200 }}>
            <label>Nombre</label>
            <input className="input" value={alta.nombre}
              onChange={(ev) => setAlta({ ...alta, nombre: ev.target.value })} />
          </div>
          <div className="field">
            <label>Tipo</label>
            <select className="select" value={alta.tipo}
              onChange={(ev) => setAlta({ ...alta, tipo: ev.target.value })}>
              {Object.entries(TIPO_LABEL).map(([v, n]) => (
                <option key={v} value={v}>{n}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Padre (opcional)</label>
            <select className="select" value={alta.padre_id}
              onChange={(ev) => setAlta({ ...alta, padre_id: ev.target.value })}>
              <option value="">—</option>
              {cuentas.filter((c) => !c.imputable).map((c) => (
                <option key={c.id} value={c.id}>{c.codigo} {c.nombre}</option>
              ))}
            </select>
          </div>
          <button className="btn btn-primary"
            disabled={!alta.codigo.trim() || alta.nombre.trim().length < 2}
            onClick={() => void crear()}>
            Agregar cuenta
          </button>
        </div>
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th style={{ width: 110 }}>Código</th>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Imputable</th>
              <th className="acciones"></th>
            </tr>
          </thead>
          <tbody>
            {cuentas.map((c) => (
              <tr key={c.id} style={{ opacity: c.activa ? 1 : 0.5 }}>
                <td className="mono">{c.codigo}</td>
                <td style={{ fontWeight: c.imputable ? 400 : 600 }}>
                  {editando === c.id ? (
                    <input
                      className="input" autoFocus value={nombreEdit}
                      onChange={(ev) => setNombreEdit(ev.target.value)}
                      onKeyDown={(ev) => {
                        if (ev.key === "Enter") void guardarNombre(c);
                        if (ev.key === "Escape") setEditando(null);
                      }}
                      onBlur={() => setEditando(null)}
                    />
                  ) : (
                    c.nombre
                  )}
                </td>
                <td>{TIPO_LABEL[c.tipo]}</td>
                <td>{c.imputable ? "Sí" : "—"}</td>
                <td className="acciones">
                  <button className="mini-btn" onClick={() => { setEditando(c.id); setNombreEdit(c.nombre); }}>
                    renombrar
                  </button>
                  {!c.es_sistema && (
                    <button className="mini-btn" onClick={() => void toggleActiva(c)}>
                      {c.activa ? "inactivar" : "reactivar"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
