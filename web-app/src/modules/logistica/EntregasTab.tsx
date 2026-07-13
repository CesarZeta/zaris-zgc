// Tab Pendientes: entregas creadas (todas, con filtro de estado) + crear
// entrega desde facturas/remitos emitidos. Rendición rápida por fila para
// entregas sueltas (sin hoja); las de hoja se rinden en el tab Rendición.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Entrega, Transportista } from "../../lib/types";
import { useDialogos } from "../../components/dialogos";
import { ChipEntrega } from "./chips";
import EntregaForm from "./EntregaForm";

interface Props {
  transportistas: Transportista[];
}

export default function EntregasTab({ transportistas }: Props) {
  const [entregas, setEntregas] = useState<Entrega[]>([]);
  const [estado, setEstado] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const { confirmar, pedirTexto, dialogos } = useDialogos();

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { data } = await apiGet<Entrega[]>(
        `/logistica/entregas?estado=${estado}&limit=200`,
      );
      setEntregas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar entregas");
    } finally {
      setCargando(false);
    }
  }, [estado]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function accion(fn: () => Promise<unknown>) {
    try {
      await fn();
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar la acción");
    }
  }

  async function rendir(e: Entrega, resultado: "entregada" | "rechazada") {
    if (resultado === "entregada") {
      const recibido = await pedirTexto("¿Quién recibió? (opcional)");
      if (recibido === null) return;
      await accion(() =>
        apiPost(`/logistica/entregas/${e.id}/rendir`, {
          resultado,
          recibido_por: recibido.trim() || null,
        }),
      );
    } else {
      const motivo = await pedirTexto("Motivo del rechazo:");
      if (motivo === null || !motivo.trim()) return;
      await accion(() =>
        apiPost(`/logistica/entregas/${e.id}/rendir`, { resultado, motivo_rechazo: motivo }),
      );
    }
  }

  async function anular(e: Entrega) {
    if (!(await confirmar(`¿Anular la entrega de ${e.comprobante_desc}?`))) return;
    await accion(() => apiPost(`/logistica/entregas/${e.id}/anular`, {}));
  }

  async function reprogramar(e: Entrega) {
    if (!(await confirmar("¿Reintentar la entrega? Se crea una entrega nueva pendiente."))) return;
    await accion(() => apiPost(`/logistica/entregas/${e.id}/reprogramar`, {}));
  }

  return (
    <>
      <div className="toolbar">
        <select className="select" value={estado} onChange={(ev) => setEstado(ev.target.value)}>
          <option value="">Todos los estados</option>
          <option value="pendiente">Pendientes</option>
          <option value="asignada">En hoja</option>
          <option value="en_reparto">En reparto</option>
          <option value="entregada">Entregadas</option>
          <option value="rechazada">Rechazadas</option>
        </select>
        <span className="page-sub" style={{ margin: 0 }}>
          {cargando ? "Cargando…" : `${entregas.length} entregas`}
        </span>
        <button className="btn btn-primary" style={{ marginLeft: "auto" }}
          onClick={() => setFormAbierto(true)}>
          + Nueva entrega
        </button>
      </div>
      {error && <div className="login-error">{error}</div>}
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Comprobante</th>
              <th>Destinatario</th>
              <th>Domicilio</th>
              <th>Hoja</th>
              <th>Transportista</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {entregas.map((e) => (
              <tr key={e.id}>
                <td className="mono">{e.comprobante_desc}</td>
                <td>{e.destinatario}</td>
                <td>
                  {e.domicilio}
                  {e.localidad ? `, ${e.localidad}` : ""}
                  {e.motivo_rechazo && (
                    <div className="texto-suave">Rechazo: {e.motivo_rechazo}</div>
                  )}
                  {e.recibido_por && (
                    <div className="texto-suave">Recibió: {e.recibido_por}</div>
                  )}
                </td>
                <td className="mono">{e.hoja_numero ? `HR-${String(e.hoja_numero).padStart(8, "0")}` : "—"}</td>
                <td>{e.transportista_nombre || "—"}</td>
                <td><ChipEntrega estado={e.estado} anulada={e.anulada} /></td>
                <td className="num" style={{ whiteSpace: "nowrap" }}>
                  {!e.anulada && !e.hoja_ruta_id && ["pendiente"].includes(e.estado) && (
                    <>
                      <button className="btn btn-ghost" onClick={() => void rendir(e, "entregada")}>
                        Entregada
                      </button>
                      <button className="btn btn-ghost" onClick={() => void rendir(e, "rechazada")}>
                        Rechazada
                      </button>
                    </>
                  )}
                  {!e.anulada && ["pendiente", "asignada"].includes(e.estado) && (
                    <button className="btn btn-ghost" onClick={() => void anular(e)}>
                      Anular
                    </button>
                  )}
                  {!e.anulada && e.estado === "rechazada" && (
                    <button className="btn btn-ghost" onClick={() => void reprogramar(e)}>
                      Reintentar
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!cargando && entregas.length === 0 && (
              <tr>
                <td colSpan={7} className="texto-suave">
                  Sin entregas. Creá una desde una factura o remito emitido — el estado del
                  reparto no toca la facturación ni la cuenta corriente.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {formAbierto && (
        <EntregaForm
          transportistas={transportistas}
          onCerrar={(refrescar) => {
            setFormAbierto(false);
            if (refrescar) void cargar();
          }}
        />
      )}
      {dialogos}
    </>
  );
}
