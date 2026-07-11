// Liquidaciones de comisión (F11): elegir vendedor + rango → preview de
// pendientes (el server recalcula al liquidar) → liquidar. Listado con
// detalle expandible, anulación marcada y export CSV.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDescargar, apiGet, apiPost } from "../../lib/api";
import { AlertError, AlertOk } from "../../components/Alertas";
import Paginado from "../../components/Paginado";
import { useDialogos } from "../../components/dialogos";
import type { ComisionLiquidacion, ComisionPendiente, Vendedor } from "../../lib/types";

const POR_PAGINA = 50;
const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const hoy = () => new Date().toISOString().slice(0, 10);
const primeroDelMes = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};

export default function LiquidacionesTab({ vendedores }: { vendedores: Vendedor[] }) {
  const [vendedorId, setVendedorId] = useState("");
  const [desde, setDesde] = useState(primeroDelMes());
  const [hasta, setHasta] = useState(hoy());
  const [pendientes, setPendientes] = useState<ComisionPendiente[] | null>(null);
  const [filas, setFilas] = useState<ComisionLiquidacion[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [abierta, setAbierta] = useState<ComisionLiquidacion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  const cargar = useCallback(async () => {
    try {
      const { data, headers } = await apiGet<ComisionLiquidacion[]>(
        `/vendedores/liquidaciones?limit=${POR_PAGINA}&offset=${pagina * POR_PAGINA}&incluir_anuladas=true`,
      );
      setFilas(data);
      setTotal(Number(headers.get("X-Total-Count") || 0));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar liquidaciones");
    }
  }, [pagina]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function verPendientes() {
    if (!vendedorId) return;
    setError(null);
    setPendientes(null);
    try {
      const { data } = await apiGet<ComisionPendiente[]>(
        `/vendedores/${vendedorId}/comisiones/pendientes?desde=${desde}&hasta=${hasta}`,
      );
      setPendientes(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron calcular los pendientes");
    }
  }

  async function liquidar() {
    const v = vendedores.find((x) => x.id === vendedorId);
    if (
      !v ||
      !(await confirmar(
        `¿Liquidar las comisiones de ${v.entidad.razon_social} del ${desde} al ${hasta}? El % y la modalidad quedan sellados en el documento.`,
      ))
    )
      return;
    setOcupado(true);
    setError(null);
    try {
      const lq = await apiPost<ComisionLiquidacion>(
        `/vendedores/${vendedorId}/liquidaciones`,
        { desde, hasta },
      );
      setAviso(`Liquidación ${lq.numero_formateado} creada: $ ${fmt.format(Number(lq.total))}`);
      setPendientes(null);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo liquidar");
    } finally {
      setOcupado(false);
    }
  }

  async function anular(lq: ComisionLiquidacion) {
    if (
      !(await confirmar(
        `¿Anular la liquidación ${lq.numero_formateado}? Los documentos vuelven a estar pendientes.`,
      ))
    )
      return;
    try {
      await apiPost(`/vendedores/liquidaciones/${lq.id}/anular`, {});
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo anular");
    }
  }

  async function verDetalle(lq: ComisionLiquidacion) {
    try {
      const { data } = await apiGet<ComisionLiquidacion>(`/vendedores/liquidaciones/${lq.id}`);
      setAbierta(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el detalle");
    }
  }

  const totalPend = (pendientes ?? []).reduce((s, p) => s + Number(p.importe), 0);

  return (
    <>
      <AlertError>{error}</AlertError>
      <AlertOk>{aviso}</AlertOk>

      <div className="toolbar">
        <select className="select" value={vendedorId} onChange={(ev) => { setVendedorId(ev.target.value); setPendientes(null); }}>
          <option value="">— vendedor —</option>
          {vendedores.map((v) => (
            <option key={v.id} value={v.id}>
              {v.entidad.razon_social} · {v.comision_pct}% por {v.modalidad}
            </option>
          ))}
        </select>
        <input type="date" className="input" style={{ width: 150 }} value={desde}
          onChange={(ev) => setDesde(ev.target.value)} />
        <span>→</span>
        <input type="date" className="input" style={{ width: 150 }} value={hasta}
          onChange={(ev) => setHasta(ev.target.value)} />
        <button className="btn" disabled={!vendedorId} onClick={() => void verPendientes()}>
          Calcular pendientes
        </button>
        {pendientes !== null && pendientes.length > 0 && (
          <button className="btn btn-primary" disabled={ocupado} onClick={() => void liquidar()}>
            {ocupado ? "Liquidando…" : `Liquidar $ ${fmt.format(totalPend)}`}
          </button>
        )}
      </div>

      {pendientes !== null && (
        <div className="tabla-card" style={{ marginBottom: 16 }}>
          <table className="tabla tabla-mini">
            <thead>
              <tr><th>Fecha</th><th>Documento</th><th className="num">Base</th><th className="num">Comisión</th></tr>
            </thead>
            <tbody>
              {pendientes.map((p, i) => (
                <tr key={i}>
                  <td className="mono">{p.fecha}</td>
                  <td>{p.descripcion}</td>
                  <td className="num mono">$ {fmt.format(Number(p.base))}</td>
                  <td className="num mono">$ {fmt.format(Number(p.importe))}</td>
                </tr>
              ))}
              {pendientes.length === 0 && (
                <tr><td colSpan={4} className="texto-suave">Sin documentos pendientes de comisión en el rango.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <h2>Liquidaciones</h2>
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Número</th>
              <th>Fecha</th>
              <th>Vendedor</th>
              <th>Período</th>
              <th className="num">%</th>
              <th className="num">Base</th>
              <th className="num">Comisión</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filas.map((lq) => (
              <tr key={lq.id} style={{ opacity: lq.anulada ? 0.5 : 1, cursor: "pointer" }}
                onClick={() => void verDetalle(lq)}>
                <td className="mono">{lq.numero_formateado}{lq.anulada ? " (anulada)" : ""}</td>
                <td className="mono">{lq.fecha}</td>
                <td>{lq.vendedor_nombre}</td>
                <td className="mono">{lq.desde} → {lq.hasta}</td>
                <td className="num mono">{lq.comision_pct}</td>
                <td className="num mono">$ {fmt.format(Number(lq.base_total))}</td>
                <td className="num mono">$ {fmt.format(Number(lq.total))}</td>
                <td style={{ whiteSpace: "nowrap" }} onClick={(ev) => ev.stopPropagation()}>
                  <button className="mini-btn" onClick={() => void apiDescargar(
                    `/vendedores/liquidaciones/${lq.id}/export.csv`, `liquidacion-${lq.numero_formateado}.csv`)}>
                    csv
                  </button>{" "}
                  {!lq.anulada && (
                    <button className="mini-btn" onClick={() => void anular(lq)}>anular</button>
                  )}
                </td>
              </tr>
            ))}
            {filas.length === 0 && (
              <tr><td colSpan={8} className="texto-suave">Sin liquidaciones todavía.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <Paginado total={total} porPagina={POR_PAGINA} pagina={pagina} onPagina={setPagina} />

      {abierta && (
        <div className="drawer-backdrop" onClick={() => setAbierta(null)}>
          <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
            <h2>{abierta.numero_formateado} — {abierta.vendedor_nombre}</h2>
            <p className="hint-mono">
              {abierta.desde} → {abierta.hasta} · {abierta.comision_pct}% por {abierta.modalidad}
              {abierta.anulada ? " · ANULADA" : ""}
            </p>
            <div className="tabla-card" style={{ maxHeight: 360, overflow: "auto" }}>
              <table className="tabla tabla-mini">
                <thead>
                  <tr><th>Fecha</th><th>Documento</th><th className="num">Base</th><th className="num">Comisión</th></tr>
                </thead>
                <tbody>
                  {(abierta.items ?? []).map((p, i) => (
                    <tr key={i}>
                      <td className="mono">{p.fecha}</td>
                      <td>{p.descripcion}</td>
                      <td className="num mono">$ {fmt.format(Number(p.base))}</td>
                      <td className="num mono">$ {fmt.format(Number(p.importe))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="toolbar">
              <span className="mono" style={{ marginLeft: "auto" }}>
                Base $ {fmt.format(Number(abierta.base_total))} · Comisión $ {fmt.format(Number(abierta.total))}
              </span>
            </div>
            <div className="drawer-acciones">
              <button className="btn btn-ghost" onClick={() => setAbierta(null)}>Cerrar</button>
            </div>
          </div>
        </div>
      )}
      {dialogos}
    </>
  );
}
