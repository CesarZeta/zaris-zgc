// Armado de hoja de ruta: transportista + fecha + entregas PENDIENTES
// (el orden de selección es el orden del recorrido).

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Entrega, Transportista } from "../../lib/types";
import { AlertError } from "../../components/Alertas";
import { useDialogos } from "../../components/dialogos";

interface Props {
  transportistas: Transportista[];
  onCerrar: (refrescar: boolean) => void;
}

export default function HojaForm({ transportistas, onCerrar }: Props) {
  const [pendientes, setPendientes] = useState<Entrega[]>([]);
  const [seleccion, setSeleccion] = useState<string[]>([]); // orden = recorrido
  const [form, setForm] = useState({
    transportista_id: transportistas[0]?.id ?? "",
    fecha: new Date().toISOString().slice(0, 10),
    observaciones: "",
  });
  const [modificado, setModificado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await apiGet<Entrega[]>("/logistica/entregas?estado=pendiente&limit=200");
        setPendientes(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar entregas pendientes");
      }
    })();
  }, []);

  function alternar(id: string) {
    setSeleccion((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
    setModificado(true);
  }

  async function intentarCerrar() {
    if (modificado && !(await confirmar("Hay cambios sin guardar. ¿Descartar?"))) return;
    onCerrar(false);
  }

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    if (!form.transportista_id) {
      setError("Elegí el transportista");
      return;
    }
    if (seleccion.length === 0) {
      setError("Elegí al menos una entrega pendiente");
      return;
    }
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/logistica/hojas", {
        transportista_id: form.transportista_id,
        fecha: form.fecha,
        observaciones: form.observaciones.trim() || null,
        entrega_ids: seleccion,
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la hoja");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => void intentarCerrar()}>
      <form className="drawer" onClick={(ev) => ev.stopPropagation()} onSubmit={guardar}>
        <h2>Nueva hoja de ruta</h2>
        <AlertError>{error}</AlertError>

        <div className="fila-3">
          <div className="field">
            <label>Transportista *</label>
            <select className="select" value={form.transportista_id}
              onChange={(ev) => { setForm((f) => ({ ...f, transportista_id: ev.target.value })); setModificado(true); }}>
              <option value="">Elegir…</option>
              {transportistas.map((t) => (
                <option key={t.id} value={t.id}>{t.entidad.razon_social}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Fecha</label>
            <input className="input mono" type="date" value={form.fecha}
              onChange={(ev) => { setForm((f) => ({ ...f, fecha: ev.target.value })); setModificado(true); }} />
          </div>
          <div className="field">
            <label>Observaciones</label>
            <input className="input" value={form.observaciones} maxLength={200}
              onChange={(ev) => { setForm((f) => ({ ...f, observaciones: ev.target.value })); setModificado(true); }} />
          </div>
        </div>

        <div className="seccion">
          Entregas pendientes — el orden en que las marcás es el orden del recorrido
        </div>
        <div className="tabla-card" style={{ maxHeight: 280, overflowY: "auto" }}>
          <table className="tabla">
            <tbody>
              {pendientes.map((e) => {
                const pos = seleccion.indexOf(e.id);
                return (
                  <tr key={e.id} style={{ cursor: "pointer" }} onClick={() => alternar(e.id)}>
                    <td className="mono" style={{ width: 36 }}>
                      {pos >= 0 ? `${pos + 1}º` : "—"}
                    </td>
                    <td className="mono">{e.comprobante_desc}</td>
                    <td>{e.destinatario}</td>
                    <td>{e.domicilio}{e.localidad ? `, ${e.localidad}` : ""}</td>
                  </tr>
                );
              })}
              {pendientes.length === 0 && (
                <tr>
                  <td className="texto-suave">No hay entregas pendientes sin hoja.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            {guardando ? "Creando…" : `Crear hoja (${seleccion.length} entregas)`}
          </button>
        </div>
        {dialogos}
      </form>
    </div>
  );
}
