// Tab Hojas de ruta: armado, impresión, despacho y anulación. El detalle se
// expande en línea; la rendición del reparto vive en el tab Rendición.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Empresa, Entrega, HojaRuta, Transportista } from "../../lib/types";
import { useDialogos } from "../../components/dialogos";
import { ChipEntrega, ChipHoja } from "./chips";
import HojaForm from "./HojaForm";
import { imprimirHojaRuta } from "./impresionHoja";

interface Props {
  transportistas: Transportista[];
}

export default function HojasTab({ transportistas }: Props) {
  const [hojas, setHojas] = useState<HojaRuta[]>([]);
  const [abierta, setAbierta] = useState<HojaRuta | null>(null); // detalle expandido
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { data } = await apiGet<HojaRuta[]>("/logistica/hojas?limit=100");
      setHojas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar hojas de ruta");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function verDetalle(h: HojaRuta) {
    if (abierta?.id === h.id) {
      setAbierta(null);
      return;
    }
    try {
      const { data } = await apiGet<HojaRuta>(`/logistica/hojas/${h.id}`);
      setAbierta(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el detalle");
    }
  }

  async function accion(h: HojaRuta, verbo: string, mensaje: string) {
    if (!(await confirmar(mensaje))) return;
    try {
      await apiPost(`/logistica/hojas/${h.id}/${verbo}`, {});
      setAbierta(null);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar la acción");
    }
  }

  async function imprimir(h: HojaRuta) {
    try {
      const [{ data }, { data: empresa }] = await Promise.all([
        apiGet<HojaRuta>(`/logistica/hojas/${h.id}`),
        apiGet<Empresa>("/empresa"),
      ]);
      imprimirHojaRuta(data, empresa.razon_social);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo imprimir");
    }
  }

  return (
    <>
      <div className="toolbar">
        <span className="page-sub" style={{ margin: 0 }}>
          {cargando ? "Cargando…" : `${hojas.length} hojas de ruta`}
        </span>
        <button className="btn btn-primary" style={{ marginLeft: "auto" }}
          onClick={() => setFormAbierto(true)}>
          + Nueva hoja de ruta
        </button>
      </div>
      {error && <div className="login-error">{error}</div>}
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Número</th>
              <th>Fecha</th>
              <th>Transportista</th>
              <th className="num">Entregas</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {hojas.map((h) => (
              <>
                <tr key={h.id} style={{ cursor: "pointer" }} onClick={() => void verDetalle(h)}>
                  <td className="mono">{h.numero_formateado}</td>
                  <td className="mono">{h.fecha}</td>
                  <td>{h.transportista_nombre}</td>
                  <td className="num mono">{h.cantidad_entregas}</td>
                  <td><ChipHoja estado={h.estado} anulada={h.anulada} /></td>
                  <td className="num" style={{ whiteSpace: "nowrap" }}
                    onClick={(ev) => ev.stopPropagation()}>
                    <button className="btn btn-ghost" onClick={() => void imprimir(h)}>
                      Imprimir
                    </button>
                    {!h.anulada && h.estado === "abierta" && (
                      <>
                        <button className="btn btn-ghost"
                          onClick={() => void accion(h, "despachar",
                            `¿Despachar la ${h.numero_formateado}? Las entregas pasan a "en reparto".`)}>
                          Despachar
                        </button>
                        <button className="btn btn-ghost"
                          onClick={() => void accion(h, "anular",
                            `¿Anular la ${h.numero_formateado}? Sus entregas vuelven a pendientes.`)}>
                          Anular
                        </button>
                      </>
                    )}
                  </td>
                </tr>
                {abierta?.id === h.id && (
                  <tr key={`${h.id}-detalle`}>
                    <td colSpan={6} style={{ background: "var(--surface-200, #f7f6f3)" }}>
                      <table className="tabla">
                        <tbody>
                          {(abierta.entregas ?? []).map((e: Entrega, i: number) => (
                            <tr key={e.id}>
                              <td className="mono" style={{ width: 30 }}>{i + 1}</td>
                              <td className="mono">{e.comprobante_desc}</td>
                              <td>{e.destinatario}</td>
                              <td>{e.domicilio}{e.localidad ? `, ${e.localidad}` : ""}</td>
                              <td><ChipEntrega estado={e.estado} anulada={e.anulada} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {!cargando && hojas.length === 0 && (
              <tr>
                <td colSpan={6} className="texto-suave">
                  Sin hojas de ruta. Armá una con las entregas pendientes, imprimila para el
                  reparto y despachala; al volver se rinde en el tab Rendición.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {formAbierto && (
        <HojaForm
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
