// Módulo Compras (Fase 4): comprobantes del proveedor (carga manual),
// pagos, cuentas corrientes y comparativo de precios. Circuito: borrador →
// registrar (stock + costos + cta. cte.) → anulable mientras no tenga pagos.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPost } from "../../lib/api";
import type { Compra } from "../../lib/types";
import ComparativoTab from "./ComparativoTab";
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

function ChipEstado({ c }: { c: Compra }) {
  if (c.estado === "borrador") return <span className="chip chip-borrador">borrador</span>;
  if (c.estado === "anulado") return <span className="chip chip-anulado">anulado</span>;
  return <span className="chip chip-ok">registrado</span>;
}

export default function ComprasPage() {
  const [tab, setTab] = useState<"comprobantes" | "pagos" | "ctacte" | "comparativo">(
    "comprobantes",
  );
  const [clase, setClase] = useState("");
  const [estado, setEstado] = useState("");
  const [pagina, setPagina] = useState(0);
  const [filas, setFilas] = useState<Compra[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [ocupado, setOcupado] = useState(false);

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
      const { data, headers } = await apiGet<Compra[]>(`/compras/comprobantes?${params}`);
      setFilas(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar compras");
    } finally {
      setCargando(false);
    }
  }, [clase, estado, pagina]);

  useEffect(() => {
    if (tab === "comprobantes") void cargar();
  }, [cargar, tab]);

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

  function anular(c: Compra) {
    if (
      !window.confirm(
        `¿Anular ${c.tipo_descripcion} ${c.numero_formateado}? Se revierten stock y cuenta corriente.`,
      )
    )
      return;
    void accion(async () => {
      await apiPost(`/compras/comprobantes/${c.id}/anular`, {});
    });
  }

  function borrarBorrador(c: Compra) {
    if (!window.confirm("¿Eliminar este borrador?")) return;
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

      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      {tab === "comprobantes" && (
        <>
          <div className="toolbar">
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
                  <th style={{ width: 160 }}></th>
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
                      <ChipEstado c={c} />
                    </td>
                    <td className="acciones">
                      {c.estado === "borrador" && (
                        <>
                          <button className="mini-btn" disabled={ocupado} onClick={() => registrar(c)}>
                            registrar
                          </button>
                          <button
                            className="mini-btn"
                            disabled={ocupado}
                            onClick={() => borrarBorrador(c)}
                          >
                            borrar
                          </button>
                        </>
                      )}
                      {c.estado === "registrado" && (
                        <button className="mini-btn" disabled={ocupado} onClick={() => anular(c)}>
                          anular
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!cargando && filas.length === 0 && (
              <div className="vacio">Sin compras: cargá el primer comprobante de proveedor</div>
            )}
          </div>

          {total > POR_PAGINA && (
            <div className="paginado">
              <button
                className="btn btn-ghost"
                disabled={pagina === 0}
                onClick={() => setPagina(pagina - 1)}
              >
                ← Anterior
              </button>
              <span>
                {pagina * POR_PAGINA + 1}–{Math.min((pagina + 1) * POR_PAGINA, total)} de {total}
              </span>
              <button
                className="btn btn-ghost"
                disabled={(pagina + 1) * POR_PAGINA >= total}
                onClick={() => setPagina(pagina + 1)}
              >
                Siguiente →
              </button>
            </div>
          )}
        </>
      )}

      {tab === "pagos" && <PagosTab />}
      {tab === "ctacte" && <CtaCteProvTab />}
      {tab === "comparativo" && <ComparativoTab />}

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
    </>
  );
}
