// Módulo Compras (Fase 4): comprobantes del proveedor (carga manual),
// pagos, cuentas corrientes y comparativo de precios. Circuito: borrador →
// registrar (stock + costos + cta. cte.) → anulable mientras no tenga pagos.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiDescargar, apiGet, apiPost } from "../../lib/api";
import type { Compra } from "../../lib/types";
import { AlertError, AlertOk } from "../../components/Alertas";
import ChipEstado from "../../components/ChipEstado";
import Paginado from "../../components/Paginado";
import { useDialogos } from "../../components/dialogos";
import ComparativoTab from "./ComparativoTab";
import CompraDetalle from "./CompraDetalle";
import CompraForm from "./CompraForm";
import CtaCteProvTab from "./CtaCteProvTab";
import PagosTab from "./PagosTab";

const POR_PAGINA = 50;
const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

const CLASES: Record<string, string> = {
  "": "Todos los documentos",
  factura: "Facturas",
  nota_credito: "Notas de crédito",
  nota_debito: "Notas de débito",
  remito: "Remitos",
};

export default function ComprasPage() {
  const [tab, setTab] = useState<"comprobantes" | "pagos" | "ctacte" | "comparativo">(
    "comprobantes",
  );
  const [clase, setClase] = useState("");
  const [estado, setEstado] = useState("");
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(0);
  const [filas, setFilas] = useState<Compra[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [detalleId, setDetalleId] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  // debounce del buscador: se aplica 350 ms después de dejar de tipear
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(qInput.trim());
      setPagina(0);
    }, 350);
    return () => clearTimeout(t);
  }, [qInput]);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: String(POR_PAGINA),
        offset: String(pagina * POR_PAGINA),
      });
      if (clase) params.set("clase", clase);
      if (estado) params.set("estado", estado);
      if (q) params.set("q", q);
      if (desde) params.set("desde", desde);
      if (hasta) params.set("hasta", hasta);
      const { data, headers } = await apiGet<Compra[]>(`/compras/comprobantes?${params}`);
      setFilas(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar compras");
    } finally {
      setCargando(false);
    }
  }, [clase, estado, q, desde, hasta, pagina]);

  useEffect(() => {
    if (tab === "comprobantes") void cargar();
  }, [cargar, tab]);

  async function exportarCsv() {
    const params = new URLSearchParams();
    if (clase) params.set("clase", clase);
    if (estado) params.set("estado", estado);
    if (q) params.set("q", q);
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
    try {
      await apiDescargar(`/compras/comprobantes/export.csv?${params}`, "compras.csv");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo exportar");
    }
  }

  async function accion(fn: () => Promise<void>) {
    setOcupado(true);
    setError(null);
    setMensaje(null);
    try {
      await fn();
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setOcupado(false);
    }
  }

  function registrar(c: Compra) {
    void accion(async () => {
      const reg = await apiPost<Compra>(`/compras/comprobantes/${c.id}/registrar`, {});
      setMensaje(
        `${reg.tipo_descripcion} ${reg.numero_formateado} de ${reg.proveedor_nombre} registrada.`,
      );
    });
  }

  async function anular(c: Compra) {
    if (
      !(await confirmar(
        `¿Anular ${c.tipo_descripcion} ${c.numero_formateado}? Se revierten stock y cuenta corriente.`,
      ))
    )
      return;
    void accion(async () => {
      await apiPost(`/compras/comprobantes/${c.id}/anular`, {});
    });
  }

  async function borrarBorrador(c: Compra) {
    if (!(await confirmar("¿Eliminar este borrador?"))) return;
    void accion(async () => {
      await apiDelete(`/compras/comprobantes/${c.id}`);
    });
  }

  return (
    <>
      <h1 className="page-title">Compras</h1>
      <div className="tabs">
        {(
          [
            ["comprobantes", "Comprobantes"],
            ["pagos", "Pagos"],
            ["ctacte", "Cuentas corrientes"],
            ["comparativo", "Comparativo"],
          ] as const
        ).map(([k, label]) => (
          <button key={k} className={`tab${tab === k ? " activa" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      <AlertError>{error}</AlertError>
      <AlertOk onCerrar={() => setMensaje(null)}>{mensaje}</AlertOk>

      {tab === "comprobantes" && (
        <>
          <div className="toolbar">
            <input
              className="input"
              style={{ maxWidth: 260 }}
              placeholder="Proveedor o número…"
              value={qInput}
              onChange={(ev) => setQInput(ev.target.value)}
            />
            <input
              className="input mono"
              type="date"
              style={{ maxWidth: 160 }}
              title="Desde"
              value={desde}
              onChange={(ev) => {
                setDesde(ev.target.value);
                setPagina(0);
              }}
            />
            <input
              className="input mono"
              type="date"
              style={{ maxWidth: 160 }}
              title="Hasta"
              value={hasta}
              onChange={(ev) => {
                setHasta(ev.target.value);
                setPagina(0);
              }}
            />
            <select
              className="select toolbar-select"
              value={clase}
              onChange={(ev) => {
                setClase(ev.target.value);
                setPagina(0);
              }}
            >
              {Object.entries(CLASES).map(([v, n]) => (
                <option key={v} value={v}>
                  {n}
                </option>
              ))}
            </select>
            <select
              className="select toolbar-select"
              value={estado}
              onChange={(ev) => {
                setEstado(ev.target.value);
                setPagina(0);
              }}
            >
              <option value="">Todos los estados</option>
              <option value="borrador">Borradores</option>
              <option value="registrado">Registrados</option>
              <option value="anulado">Anulados</option>
            </select>
            <div style={{ flex: 1 }} />
            <button className="btn btn-ghost" onClick={() => void exportarCsv()}>
              Exportar CSV
            </button>
            <button className="btn btn-primary" onClick={() => setFormAbierto(true)}>
              + Nueva compra
            </button>
          </div>

          <div className="tabla-card">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Comprobante</th>
                  <th>Fecha</th>
                  <th>Proveedor</th>
                  <th className="num">Total</th>
                  <th className="num">Saldo</th>
                  <th>Estado</th>
                  <th style={{ width: 190 }}></th>
                </tr>
              </thead>
              <tbody>
                {filas.map((c) => (
                  <tr key={c.id} className={c.estado === "anulado" ? "fila-anulada" : ""}>
                    <td className="mono">
                      <b>{c.tipo_codigo}</b> {c.numero_formateado}
                    </td>
                    <td className="mono">{c.fecha}</td>
                    <td>{c.proveedor_nombre}</td>
                    <td className="num mono">{fmt.format(Number(c.total))}</td>
                    <td className="num mono">
                      {Number(c.saldo) !== 0 ? fmt.format(Number(c.saldo)) : "—"}
                    </td>
                    <td>
                      <ChipEstado estado={c.estado} />
                    </td>
                    <td className="acciones">
                      <button className="mini-btn" onClick={() => setDetalleId(c.id)}>
                        ver
                      </button>
                      {c.estado === "borrador" && (
                        <>
                          <button className="mini-btn" disabled={ocupado} onClick={() => registrar(c)}>
                            registrar
                          </button>
                          <button
                            className="mini-btn"
                            disabled={ocupado}
                            onClick={() => void borrarBorrador(c)}
                          >
                            borrar
                          </button>
                        </>
                      )}
                      {c.estado === "registrado" && (
                        <button className="mini-btn" disabled={ocupado} onClick={() => void anular(c)}>
                          anular
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!cargando && filas.length === 0 && (
              <div className="vacio">
                {q || desde || hasta
                  ? "Sin resultados para esa búsqueda"
                  : "Sin compras: cargá el primer comprobante de proveedor"}
              </div>
            )}
          </div>

          <Paginado pagina={pagina} porPagina={POR_PAGINA} total={total} onPagina={setPagina} />
        </>
      )}

      {tab === "pagos" && <PagosTab />}
      {tab === "ctacte" && <CtaCteProvTab />}
      {tab === "comparativo" && <ComparativoTab />}

      {detalleId && <CompraDetalle id={detalleId} onCerrar={() => setDetalleId(null)} />}

      {formAbierto && (
        <CompraForm
          onCerrar={(refrescar, registrada) => {
            setFormAbierto(false);
            if (registrada) {
              setMensaje(
                `${registrada.tipo_descripcion} ${registrada.numero_formateado} de ${registrada.proveedor_nombre} registrada.`,
              );
            }
            if (refrescar) void cargar();
          }}
        />
      )}
      {dialogos}
    </>
  );
}
