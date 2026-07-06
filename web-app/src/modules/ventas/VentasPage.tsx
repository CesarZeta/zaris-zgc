// Módulo Ventas (Fase 3): comprobantes (facturas/NC/ND, presupuestos,
// remitos), cobranzas y cuentas corrientes. Circuito: borrador → emitir
// (fiscales con CAE vía ARCA) → inmutable; reversión solo por NC.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPost } from "../../lib/api";
import type { Comprobante, ImpresionPayload, PuntoVenta } from "../../lib/types";
import { AlertError, AlertOk } from "../../components/Alertas";
import ChipEstado from "../../components/ChipEstado";
import Paginado from "../../components/Paginado";
import { useDialogos } from "../../components/dialogos";
import CobranzasTab from "./CobranzasTab";
import ComprobanteDetalle from "./ComprobanteDetalle";
import ComprobanteForm from "./ComprobanteForm";
import CtaCteTab from "./CtaCteTab";
import { imprimirComprobante } from "./impresion";

const POR_PAGINA = 50;
const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

const CLASES: Record<string, string> = {
  "": "Todos los documentos",
  factura: "Facturas",
  nota_credito: "Notas de crédito",
  nota_debito: "Notas de débito",
  presupuesto: "Presupuestos",
  remito: "Remitos",
};

export default function VentasPage() {
  const [tab, setTab] = useState<"comprobantes" | "cobranzas" | "ctacte">("comprobantes");
  const [puntosVenta, setPuntosVenta] = useState<PuntoVenta[]>([]);
  const [clase, setClase] = useState("");
  const [estado, setEstado] = useState("");
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(0);
  const [filas, setFilas] = useState<Comprobante[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [detalleId, setDetalleId] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const { confirmar, pedirTexto, dialogos } = useDialogos();

  useEffect(() => {
    void apiGet<PuntoVenta[]>("/ventas/puntos-venta").then(({ data }) =>
      setPuntosVenta(data.filter((pv) => pv.activo)),
    );
  }, []);

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
      const { data, headers } = await apiGet<Comprobante[]>(`/ventas/comprobantes?${params}`);
      setFilas(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar comprobantes");
    } finally {
      setCargando(false);
    }
  }, [clase, estado, q, desde, hasta, pagina]);

  useEffect(() => {
    if (tab === "comprobantes") void cargar();
  }, [cargar, tab]);

  async function crearPuntoVentaInicial() {
    const numero = await pedirTexto(
      "Número del punto de venta (el habilitado en ARCA para Web Services):",
      "1",
    );
    if (!numero) return;
    try {
      const pv = await apiPost<PuntoVenta>("/ventas/puntos-venta", {
        numero: Number(numero),
        descripcion: "Principal",
        electronico: true,
      });
      setPuntosVenta([pv]);
      setMensaje(`Punto de venta ${String(pv.numero).padStart(4, "0")} creado.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el punto de venta");
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

  function emitir(c: Comprobante) {
    void accion(async () => {
      const emitido = await apiPost<Comprobante>(`/ventas/comprobantes/${c.id}/emitir`, {});
      setMensaje(
        `${emitido.tipo_descripcion} ${emitido.numero_formateado} emitida` +
          (emitido.cae ? ` — CAE ${emitido.cae}` : ""),
      );
    });
  }

  function imprimir(c: Comprobante) {
    void accion(async () => {
      const { data } = await apiGet<ImpresionPayload>(`/ventas/comprobantes/${c.id}/impresion`);
      imprimirComprobante(data);
    });
  }

  async function notaCredito(c: Comprobante) {
    if (
      !(await confirmar(
        `Se crea la nota de crédito espejo (borrador) de ${c.tipo_codigo} ${c.numero_formateado}. ¿Continuar?`,
      ))
    )
      return;
    void accion(async () => {
      await apiPost(`/ventas/comprobantes/${c.id}/nota-credito`, {});
      setMensaje("Nota de crédito creada como borrador: revisala y emitila.");
    });
  }

  async function anular(c: Comprobante) {
    if (!(await confirmar(`¿Anular ${c.tipo_descripcion} ${c.numero_formateado}?`))) return;
    void accion(async () => {
      await apiPost(`/ventas/comprobantes/${c.id}/anular`, {});
    });
  }

  function facturarPresupuesto(c: Comprobante) {
    void accion(async () => {
      await apiPost(`/ventas/comprobantes/${c.id}/facturar`, {});
      setMensaje("Factura borrador creada desde el presupuesto.");
    });
  }

  async function borrarBorrador(c: Comprobante) {
    if (!(await confirmar("¿Eliminar este borrador?"))) return;
    void accion(async () => {
      await apiDelete(`/ventas/comprobantes/${c.id}`);
    });
  }

  if (puntosVenta.length === 0 && !cargando) {
    return (
      <>
        <h1 className="page-title">Ventas</h1>
        <div className="vacio">
          <p>Para empezar a vender hay que crear un punto de venta.</p>
          <p style={{ marginTop: 8 }}>
            <button className="btn btn-primary" onClick={() => void crearPuntoVentaInicial()}>
              Crear punto de venta
            </button>
          </p>
        </div>
        {dialogos}
      </>
    );
  }

  return (
    <>
      <h1 className="page-title">Ventas</h1>
      <div className="tabs">
        {(
          [
            ["comprobantes", "Comprobantes"],
            ["cobranzas", "Cobranzas"],
            ["ctacte", "Cuentas corrientes"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            className={`tab${tab === k ? " activa" : ""}`}
            onClick={() => setTab(k)}
          >
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
              placeholder="Cliente o número…"
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
              <option value="emitido">Emitidos</option>
              <option value="anulado">Anulados</option>
            </select>
            <div style={{ flex: 1 }} />
            <button className="btn btn-primary" onClick={() => setFormAbierto(true)}>
              + Nueva venta
            </button>
          </div>

          <div className="tabla-card">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Comprobante</th>
                  <th>Fecha</th>
                  <th>Cliente</th>
                  <th className="num">Total</th>
                  <th className="num">Saldo</th>
                  <th>Estado</th>
                  <th style={{ width: 230 }}></th>
                </tr>
              </thead>
              <tbody>
                {filas.map((c) => (
                  <tr key={c.id} className={c.estado === "anulado" ? "fila-anulada" : ""}>
                    <td className="mono">
                      <b>{c.tipo_codigo}</b> {c.numero_formateado ?? "(borrador)"}
                    </td>
                    <td className="mono">{c.fecha}</td>
                    <td>{c.receptor_nombre}</td>
                    <td className="num mono">{fmt.format(Number(c.total))}</td>
                    <td className="num mono">
                      {Number(c.saldo) !== 0 ? fmt.format(Number(c.saldo)) : "—"}
                    </td>
                    <td>
                      <ChipEstado estado={c.estado} cae={c.cae} arcaResultado={c.arca_resultado} />
                    </td>
                    <td className="acciones">
                      <button className="mini-btn" onClick={() => setDetalleId(c.id)}>
                        ver
                      </button>
                      {c.estado === "borrador" && (
                        <>
                          <button className="mini-btn" disabled={ocupado} onClick={() => emitir(c)}>
                            emitir
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
                      {c.estado === "emitido" && (
                        <button className="mini-btn" disabled={ocupado} onClick={() => imprimir(c)}>
                          imprimir
                        </button>
                      )}
                      {c.estado === "emitido" && c.clase === "factura" && (
                        <button
                          className="mini-btn"
                          disabled={ocupado}
                          onClick={() => void notaCredito(c)}
                        >
                          NC
                        </button>
                      )}
                      {c.estado === "emitido" && c.clase === "presupuesto" && (
                        <button
                          className="mini-btn"
                          disabled={ocupado}
                          onClick={() => facturarPresupuesto(c)}
                        >
                          facturar
                        </button>
                      )}
                      {c.estado === "emitido" &&
                        (c.clase === "presupuesto" || c.clase === "remito") && (
                          <button
                            className="mini-btn"
                            disabled={ocupado}
                            onClick={() => void anular(c)}
                          >
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
                  : "Sin comprobantes: creá la primera venta"}
              </div>
            )}
          </div>

          <Paginado pagina={pagina} porPagina={POR_PAGINA} total={total} onPagina={setPagina} />
        </>
      )}

      {tab === "cobranzas" && <CobranzasTab puntosVenta={puntosVenta} />}
      {tab === "ctacte" && <CtaCteTab />}

      {detalleId && <ComprobanteDetalle id={detalleId} onCerrar={() => setDetalleId(null)} />}

      {formAbierto && (
        <ComprobanteForm
          puntosVenta={puntosVenta}
          onCerrar={(refrescar, emitido) => {
            setFormAbierto(false);
            if (emitido) {
              setMensaje(
                `${emitido.tipo_descripcion} ${emitido.numero_formateado} emitida` +
                  (emitido.cae ? ` — CAE ${emitido.cae}` : ""),
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
