// Cobranzas: recibos (documento interno X) con medios de pago e imputación
// contra facturas pendientes del cliente. El resto queda "a cuenta".

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Cliente, Comprobante, PuntoVenta, Recibo } from "../../lib/types";
import { AlertError } from "../../components/Alertas";
import Buscador from "../../components/Buscador";
import ChipEstado from "../../components/ChipEstado";
import Paginado from "../../components/Paginado";
import { useDialogos } from "../../components/dialogos";

const POR_PAGINA = 50;
const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

const MEDIOS = [
  ["efectivo", "Efectivo"],
  ["transferencia", "Transferencia"],
  ["cheque", "Cheque"],
  ["tarjeta", "Tarjeta"],
  ["mercadopago", "Mercado Pago"],
  ["otro", "Otro"],
] as const;

const buscarClientes = async (q: string) =>
  (await apiGet<Cliente[]>(`/clientes?q=${encodeURIComponent(q)}&limit=8`)).data;

function ReciboModal({
  puntosVenta,
  onCerrar,
}: {
  puntosVenta: PuntoVenta[];
  onCerrar: (refrescar: boolean) => void;
}) {
  const [pvId, setPvId] = useState(puntosVenta[0]?.id ?? "");
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [pendientes, setPendientes] = useState<Comprobante[]>([]);
  const [medios, setMedios] = useState<{ medio: string; importe: string; referencia: string }[]>([
    { medio: "efectivo", importe: "", referencia: "" },
  ]);
  const [imputar, setImputar] = useState<Record<string, string>>({});
  const [obs, setObs] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  useEffect(() => {
    if (!cliente) {
      setPendientes([]);
      setImputar({});
      return;
    }
    void apiGet<Comprobante[]>(
      `/ventas/comprobantes?cliente_id=${cliente.id}&estado=emitido&con_saldo=true&limit=100`,
    ).then(({ data }) =>
      setPendientes(data.filter((c) => ["factura", "nota_debito"].includes(c.clase))),
    );
  }, [cliente]);

  const totalMedios = medios.reduce((a, m) => a + Number(m.importe || 0), 0);
  const totalImputado = Object.values(imputar).reduce((a, v) => a + Number(v || 0), 0);

  const hayDatos = cliente !== null || medios.some((m) => m.importe) || obs.trim() !== "";

  async function intentarCerrar() {
    if (hayDatos && !(await confirmar("Hay datos sin guardar. ¿Descartar la cobranza?"))) return;
    onCerrar(false);
  }

  async function guardar() {
    if (!cliente) return;
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/cobranzas/recibos", {
        punto_venta_id: pvId,
        cliente_id: cliente.id,
        medios: medios
          .filter((m) => Number(m.importe) > 0)
          .map((m) => ({
            medio: m.medio,
            importe: m.importe,
            referencia: m.referencia.trim() || null,
          })),
        imputaciones: Object.entries(imputar)
          .filter(([, v]) => Number(v) > 0)
          .map(([comprobante_id, importe]) => ({ comprobante_id, importe })),
        observaciones: obs.trim() || null,
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar la cobranza");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => void intentarCerrar()}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Nueva cobranza (recibo)</h2>
        <AlertError>{error}</AlertError>

        <div className="fila">
          <div className="field" style={{ flex: 2 }}>
            <label>Cliente *</label>
            <Buscador<Cliente>
              placeholder="Buscar cliente…"
              buscar={buscarClientes}
              etiqueta={(c) => c.entidad.razon_social}
              clave={(c) => c.id}
              elegido={cliente}
              onElegir={setCliente}
              autoFocus
            />
          </div>
          <div className="field">
            <label>Punto de venta</label>
            <select className="select" value={pvId} onChange={(ev) => setPvId(ev.target.value)}>
              {puntosVenta.map((pv) => (
                <option key={pv.id} value={pv.id}>
                  {String(pv.numero).padStart(4, "0")}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="seccion">Medios de pago</div>
        {medios.map((m, i) => (
          <div className="fila" key={i}>
            <div className="field">
              <select
                className="select"
                value={m.medio}
                onChange={(ev) =>
                  setMedios(medios.map((x, j) => (j === i ? { ...x, medio: ev.target.value } : x)))
                }
              >
                {MEDIOS.map(([v, n]) => (
                  <option key={v} value={v}>
                    {n}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <input
                className="input mono"
                type="number"
                step="0.01"
                min="0"
                placeholder="importe"
                value={m.importe}
                onChange={(ev) =>
                  setMedios(medios.map((x, j) => (j === i ? { ...x, importe: ev.target.value } : x)))
                }
              />
            </div>
            <div className="field">
              <input
                className="input"
                placeholder="referencia (cheque/lote/op.)"
                value={m.referencia}
                onChange={(ev) =>
                  setMedios(
                    medios.map((x, j) => (j === i ? { ...x, referencia: ev.target.value } : x)),
                  )
                }
              />
            </div>
            {medios.length > 1 && (
              <button
                type="button"
                className="mini-btn"
                onClick={() => setMedios(medios.filter((_, j) => j !== i))}
              >
                quitar
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          className="mini-btn"
          onClick={() => setMedios([...medios, { medio: "transferencia", importe: "", referencia: "" }])}
        >
          + medio
        </button>

        {cliente && pendientes.length > 0 && (
          <>
            <div className="seccion">Imputar a facturas pendientes</div>
            <div className="tabla-card">
              <table className="tabla tabla-mini">
                <thead>
                  <tr>
                    <th>Comprobante</th>
                    <th>Fecha</th>
                    <th className="num">Saldo</th>
                    <th className="num">Imputar $</th>
                  </tr>
                </thead>
                <tbody>
                  {pendientes.map((c) => (
                    <tr key={c.id}>
                      <td className="mono">
                        {c.tipo_codigo} {c.numero_formateado}
                      </td>
                      <td className="mono">{c.fecha}</td>
                      <td className="num mono">{fmt.format(Number(c.saldo))}</td>
                      <td className="num">
                        <input
                          className="input input-mini num mono"
                          type="number"
                          step="0.01"
                          min="0"
                          max={c.saldo}
                          value={imputar[c.id] ?? ""}
                          onChange={(ev) => setImputar({ ...imputar, [c.id]: ev.target.value })}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <div className="fila" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div className="field" style={{ flex: 1 }}>
            <label>Observaciones</label>
            <input className="input" value={obs} onChange={(ev) => setObs(ev.target.value)} />
          </div>
          <div className="total-preview">
            Cobrado: <b className="mono">$ {fmt.format(totalMedios)}</b> · Imputado:{" "}
            <b className="mono">$ {fmt.format(totalImputado)}</b> · A cuenta:{" "}
            <b className="mono">$ {fmt.format(totalMedios - totalImputado)}</b>
          </div>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!cliente || totalMedios <= 0 || totalImputado > totalMedios || guardando}
            onClick={() => void guardar()}
          >
            {guardando ? "Guardando…" : "Registrar cobranza"}
          </button>
        </div>
      </div>
      {dialogos}
    </div>
  );
}

export default function CobranzasTab({ puntosVenta }: { puntosVenta: PuntoVenta[] }) {
  const [recibos, setRecibos] = useState<Recibo[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  // debounce del buscador
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(qInput.trim());
      setPagina(0);
    }, 350);
    return () => clearTimeout(t);
  }, [qInput]);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const params = new URLSearchParams({
        limit: String(POR_PAGINA),
        offset: String(pagina * POR_PAGINA),
      });
      if (q) params.set("q", q);
      if (desde) params.set("desde", desde);
      if (hasta) params.set("hasta", hasta);
      const { data, headers } = await apiGet<Recibo[]>(`/cobranzas/recibos?${params}`);
      setRecibos(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar recibos");
    } finally {
      setCargando(false);
    }
  }, [q, desde, hasta, pagina]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function anular(r: Recibo) {
    if (
      !(await confirmar(`¿Anular el recibo ${r.numero_formateado}? Se revierten sus imputaciones.`))
    )
      return;
    try {
      await apiPost(`/cobranzas/recibos/${r.id}/anular`, {});
      void cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo anular");
    }
  }

  return (
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
        <span className="page-sub" style={{ margin: 0, alignSelf: "center" }}>
          {cargando ? "Cargando…" : `${total} recibos`}
        </span>
        <div style={{ flex: 1 }} />
        <button className="btn btn-primary" onClick={() => setModalAbierto(true)}>
          + Nueva cobranza
        </button>
      </div>
      <AlertError>{error}</AlertError>
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Recibo</th>
              <th>Fecha</th>
              <th>Cliente</th>
              <th className="num">Total</th>
              <th className="num">Imputado</th>
              <th className="num">A cuenta</th>
              <th>Medios</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {recibos.map((r) => (
              <tr key={r.id} className={r.estado === "anulado" ? "fila-anulada" : ""}>
                <td className="mono">{r.numero_formateado}</td>
                <td className="mono">{r.fecha}</td>
                <td>{r.receptor_nombre}</td>
                <td className="num mono">{fmt.format(Number(r.total))}</td>
                <td className="num mono">{fmt.format(Number(r.aplicado))}</td>
                <td className="num mono">{fmt.format(Number(r.a_cuenta))}</td>
                <td>{r.medios.map((m) => m.medio).join(", ")}</td>
                <td>
                  {r.estado === "anulado" ? (
                    <ChipEstado estado={r.estado} />
                  ) : (
                    <button className="mini-btn" onClick={() => void anular(r)}>
                      anular
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && recibos.length === 0 && (
          <div className="vacio">
            {q || desde || hasta ? "Sin resultados para esa búsqueda" : "Sin cobranzas registradas"}
          </div>
        )}
      </div>
      <Paginado pagina={pagina} porPagina={POR_PAGINA} total={total} onPagina={setPagina} />
      {modalAbierto && (
        <ReciboModal
          puntosVenta={puntosVenta}
          onCerrar={(refrescar) => {
            setModalAbierto(false);
            if (refrescar) void cargar();
          }}
        />
      )}
      {dialogos}
    </>
  );
}
