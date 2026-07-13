// Tab Rendición: al volver el reparto, marcar entregada/rechazada por fila
// sobre la hoja en reparto, y cerrarla cuando no queda nada sin rendir.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { HojaRuta } from "../../lib/types";
import { useDialogos } from "../../components/dialogos";
import { ChipEntrega } from "./chips";

export default function RendicionTab() {
  const [hojas, setHojas] = useState<HojaRuta[]>([]);
  const [hojaId, setHojaId] = useState("");
  const [hoja, setHoja] = useState<HojaRuta | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { confirmar, pedirTexto, dialogos } = useDialogos();

  const cargarHojas = useCallback(async () => {
    setCargando(true);
    try {
      const { data } = await apiGet<HojaRuta[]>("/logistica/hojas?estado=en_reparto&limit=100");
      setHojas(data);
      if (data.length > 0 && !data.some((h) => h.id === hojaId)) {
        setHojaId(data[0].id);
      }
      if (data.length === 0) {
        setHojaId("");
        setHoja(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar hojas en reparto");
    } finally {
      setCargando(false);
    }
  }, [hojaId]);

  useEffect(() => {
    void cargarHojas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!hojaId) return;
    void (async () => {
      try {
        const { data } = await apiGet<HojaRuta>(`/logistica/hojas/${hojaId}`);
        setHoja(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo cargar la hoja");
      }
    })();
  }, [hojaId]);

  async function refrescar() {
    if (hojaId) {
      const { data } = await apiGet<HojaRuta>(`/logistica/hojas/${hojaId}`);
      setHoja(data);
    }
  }

  async function rendir(entregaId: string, resultado: "entregada" | "rechazada") {
    setError(null);
    try {
      if (resultado === "entregada") {
        const recibido = await pedirTexto("¿Quién recibió? (opcional)");
        if (recibido === null) return;
        await apiPost(`/logistica/entregas/${entregaId}/rendir`, {
          resultado,
          recibido_por: recibido.trim() || null,
        });
      } else {
        const motivo = await pedirTexto("Motivo del rechazo:");
        if (motivo === null || !motivo.trim()) return;
        await apiPost(`/logistica/entregas/${entregaId}/rendir`, {
          resultado,
          motivo_rechazo: motivo,
        });
      }
      await refrescar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo rendir");
    }
  }

  async function cerrar() {
    if (!hoja) return;
    if (!(await confirmar(`¿Cerrar la ${hoja.numero_formateado}? El reparto queda rendido.`)))
      return;
    setError(null);
    try {
      await apiPost(`/logistica/hojas/${hoja.id}/cerrar`, {});
      setHoja(null);
      setHojaId("");
      await cargarHojas();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar la hoja");
    }
  }

  const sinRendir = (hoja?.entregas ?? []).filter(
    (e) => !e.anulada && !["entregada", "rechazada", "reprogramada"].includes(e.estado),
  ).length;

  return (
    <>
      <div className="toolbar">
        <select className="select" value={hojaId} onChange={(ev) => setHojaId(ev.target.value)}>
          {hojas.length === 0 && <option value="">Sin repartos en la calle</option>}
          {hojas.map((h) => (
            <option key={h.id} value={h.id}>
              {h.numero_formateado} · {h.fecha} · {h.transportista_nombre}
            </option>
          ))}
        </select>
        {hoja && (
          <button className="btn btn-primary" style={{ marginLeft: "auto" }}
            disabled={sinRendir > 0} onClick={() => void cerrar()}>
            {sinRendir > 0 ? `Faltan rendir ${sinRendir}` : "Cerrar hoja"}
          </button>
        )}
      </div>
      {error && <div className="login-error">{error}</div>}
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>#</th>
              <th>Comprobante</th>
              <th>Destinatario</th>
              <th>Domicilio</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(hoja?.entregas ?? []).map((e, i) => (
              <tr key={e.id}>
                <td className="mono">{i + 1}</td>
                <td className="mono">{e.comprobante_desc}</td>
                <td>{e.destinatario}</td>
                <td>
                  {e.domicilio}
                  {e.localidad ? `, ${e.localidad}` : ""}
                  {e.recibido_por && <div className="texto-suave">Recibió: {e.recibido_por}</div>}
                  {e.motivo_rechazo && (
                    <div className="texto-suave">Rechazo: {e.motivo_rechazo}</div>
                  )}
                </td>
                <td><ChipEntrega estado={e.estado} anulada={e.anulada} /></td>
                <td className="num" style={{ whiteSpace: "nowrap" }}>
                  {e.estado === "en_reparto" && (
                    <>
                      <button className="btn btn-ghost" onClick={() => void rendir(e.id, "entregada")}>
                        Entregada
                      </button>
                      <button className="btn btn-ghost" onClick={() => void rendir(e.id, "rechazada")}>
                        Rechazada
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!cargando && !hoja && (
              <tr>
                <td colSpan={6} className="texto-suave">
                  No hay hojas de ruta en reparto. Despachá una desde el tab Hojas de ruta y
                  rendila acá cuando vuelva el reparto.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {dialogos}
    </>
  );
}
