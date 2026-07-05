// Módulo Caja (Fase 5): planilla de caja diaria (reporte del día + cierre con
// arqueo de efectivo), movimientos manuales por concepto y catálogo de
// conceptos. El saldo de caja es EFECTIVO; las ventas de contado se asumen
// efectivo hasta que el POS (Fase 6) registre medios por venta.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPost } from "../../lib/api";
import type { Planilla } from "../../lib/types";
import { MEDIOS_PAGO } from "../../lib/types";
import ConceptosTab from "./ConceptosTab";
import MovimientosTab from "./MovimientosTab";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const hoy = () => new Date().toISOString().slice(0, 10);

export default function CajaPage() {
  const [tab, setTab] = useState<"planilla" | "movimientos" | "conceptos">("planilla");
  const [fecha, setFecha] = useState(hoy());
  const [planilla, setPlanilla] = useState<Planilla | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [cerrando, setCerrando] = useState(false);
  const [arqueo, setArqueo] = useState("");
  const [obsCierre, setObsCierre] = useState("");

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { data } = await apiGet<Planilla>(`/caja/planilla?fecha=${fecha}`);
      setPlanilla(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar la planilla");
    } finally {
      setCargando(false);
    }
  }, [fecha]);

  useEffect(() => {
    if (tab === "planilla") void cargar();
  }, [cargar, tab]);

  async function cerrarCaja() {
    setOcupado(true);
    setError(null);
    try {
      await apiPost("/caja/cierres", {
        fecha,
        efectivo_contado: arqueo.trim() === "" ? null : arqueo,
        observaciones: obsCierre.trim() || null,
      });
      setMensaje(`Caja del ${fecha} cerrada.`);
      setCerrando(false);
      setArqueo("");
      setObsCierre("");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar la caja");
    } finally {
      setOcupado(false);
    }
  }

  async function reabrirCaja() {
    if (!planilla?.cierre) return;
    if (!window.confirm(`¿Reabrir la caja del ${fecha}? El cierre se elimina.`)) return;
    setOcupado(true);
    setError(null);
    try {
      await apiDelete(`/caja/cierres/${planilla.cierre.id}`);
      setMensaje(`Caja del ${fecha} reabierta.`);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo reabrir la caja");
    } finally {
      setOcupado(false);
    }
  }

  const p = planilla;
  const cerrada = Boolean(p?.cierre);

  return (
    <>
      <h1 className="page-title">Caja</h1>
      <div className="tabs">
        {(
          [
            ["planilla", "Planilla del día"],
            ["movimientos", "Movimientos"],
            ["conceptos", "Conceptos"],
          ] as const
        ).map(([k, label]) => (
          <button key={k} className={`tab${tab === k ? " activa" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      {tab === "planilla" && (
        <>
          <div className="toolbar">
            <input
              type="date"
              className="input"
              style={{ width: 170 }}
              value={fecha}
              onChange={(ev) => setFecha(ev.target.value)}
            />
            <div style={{ flex: 1 }} />
            {p && !cerrada && (
              <button className="btn btn-primary" disabled={ocupado} onClick={() => setCerrando(true)}>
                Cerrar caja
              </button>
            )}
            {p && cerrada && (
              <button className="btn btn-ghost" disabled={ocupado} onClick={() => void reabrirCaja()}>
                Reabrir caja
              </button>
            )}
          </div>

          {cerrada && p?.cierre && (
            <div className="import-resultado">
              Caja cerrada — saldo final {fmt.format(Number(p.cierre.saldo_final))}
              {p.cierre.efectivo_contado !== null &&
                ` · arqueo ${fmt.format(Number(p.cierre.efectivo_contado))} · diferencia ${fmt.format(
                  Number(p.cierre.diferencia ?? 0),
                )}`}
              {p.cierre.observaciones && ` · ${p.cierre.observaciones}`}
            </div>
          )}

          {p && (
            <div className="tabla-card" style={{ padding: 16 }}>
              <table className="tabla">
                <tbody>
                  <tr>
                    <td>Saldo inicial (efectivo)</td>
                    <td className="num mono">{fmt.format(Number(p.saldo_inicial))}</td>
                  </tr>
                  <tr>
                    <td>
                      Ventas de contado ({p.ventas_contado_cantidad} comprobante
                      {p.ventas_contado_cantidad === 1 ? "" : "s"})
                    </td>
                    <td className="num mono">{fmt.format(Number(p.ventas_contado_total))}</td>
                  </tr>
                  {p.ventas_por_medio.map((v) => (
                    <tr key={`v-${v.medio}`}>
                      <td className="chico" style={{ paddingLeft: 24 }}>
                        · por {MEDIOS_PAGO[v.medio] ?? v.medio} ({v.cantidad}, POS)
                      </td>
                      <td className="num mono">{fmt.format(Number(v.total))}</td>
                    </tr>
                  ))}
                  {p.cobranzas.map((c) => (
                    <tr key={`c-${c.medio}`}>
                      <td>
                        Cobranzas — {MEDIOS_PAGO[c.medio] ?? c.medio} ({c.cantidad})
                      </td>
                      <td className="num mono">{fmt.format(Number(c.total))}</td>
                    </tr>
                  ))}
                  {p.pagos.map((c) => (
                    <tr key={`p-${c.medio}`}>
                      <td>
                        Pagos a proveedores — {MEDIOS_PAGO[c.medio] ?? c.medio} ({c.cantidad})
                      </td>
                      <td className="num mono">-{fmt.format(Number(c.total))}</td>
                    </tr>
                  ))}
                  {p.movimientos.map((m) => (
                    <tr key={m.id}>
                      <td>
                        {m.tipo === "entrada" ? "Entrada" : "Salida"} — {m.concepto_nombre}
                        {m.medio !== "efectivo" && ` (${MEDIOS_PAGO[m.medio] ?? m.medio})`}
                        {m.descripcion && ` · ${m.descripcion}`}
                      </td>
                      <td className="num mono">
                        {m.tipo === "salida" && "-"}
                        {fmt.format(Number(m.importe))}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ fontWeight: 700 }}>
                    <td>Entradas de efectivo</td>
                    <td className="num mono">{fmt.format(Number(p.entradas_efectivo))}</td>
                  </tr>
                  <tr style={{ fontWeight: 700 }}>
                    <td>Salidas de efectivo</td>
                    <td className="num mono">-{fmt.format(Number(p.salidas_efectivo))}</td>
                  </tr>
                  <tr style={{ fontWeight: 700 }}>
                    <td>Saldo final (efectivo)</td>
                    <td className="num mono">{fmt.format(Number(p.saldo_final))}</td>
                  </tr>
                </tbody>
              </table>
              {!cargando &&
                p.ventas_contado_cantidad === 0 &&
                p.cobranzas.length === 0 &&
                p.pagos.length === 0 &&
                p.movimientos.length === 0 && (
                  <div className="vacio">Sin movimientos en la fecha</div>
                )}
            </div>
          )}
        </>
      )}

      {tab === "movimientos" && <MovimientosTab />}
      {tab === "conceptos" && <ConceptosTab />}

      {cerrando && (
        <div className="drawer-backdrop" onClick={() => setCerrando(false)}>
          <div className="modal" onClick={(ev) => ev.stopPropagation()}>
            <h2>Cerrar caja del {fecha}</h2>
            <p>
              Saldo final teórico (efectivo):{" "}
              <b className="mono">{p ? fmt.format(Number(p.saldo_final)) : "—"}</b>
            </p>
            <div className="field">
              <label>Efectivo contado (arqueo, opcional)</label>
              <input
                className="input mono"
                type="number"
                step="0.01"
                value={arqueo}
                onChange={(ev) => setArqueo(ev.target.value)}
                placeholder="Dejalo vacío si no hacés arqueo"
              />
            </div>
            <div className="field">
              <label>Observaciones</label>
              <input
                className="input"
                value={obsCierre}
                onChange={(ev) => setObsCierre(ev.target.value)}
              />
            </div>
            <div className="drawer-acciones">
              <button className="btn btn-ghost" onClick={() => setCerrando(false)}>
                Cancelar
              </button>
              <button className="btn btn-primary" disabled={ocupado} onClick={() => void cerrarCaja()}>
                Cerrar caja
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
