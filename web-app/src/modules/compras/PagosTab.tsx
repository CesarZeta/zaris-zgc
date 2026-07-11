// Pagos a proveedores: órdenes de pago (documento interno) con medios de
// pago e imputación contra facturas de compra pendientes; el resto queda a
// cuenta. Debajo, las cuentas a pagar (vencimientos próximos).

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Compra, OrdenPago, Proveedor, Sucursal, VencimientoPagar } from "../../lib/types";
import { AlertError } from "../../components/Alertas";
import ChipEstado from "../../components/ChipEstado";
import Paginado from "../../components/Paginado";
import { useDialogos } from "../../components/dialogos";
import { etiquetaCuenta, useCuentasBancarias } from "../../components/useCuentasBancarias";
import { BuscadorProveedor } from "./CompraForm";

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

function OrdenPagoModal({ onCerrar }: { onCerrar: (refrescar: boolean) => void }) {
  const [proveedor, setProveedor] = useState<Proveedor | null>(null);
  const [pendientes, setPendientes] = useState<Compra[]>([]);
  const [medios, setMedios] = useState<
    { medio: string; importe: string; referencia: string; cuenta_bancaria_id: string }[]
  >([{ medio: "transferencia", importe: "", referencia: "", cuenta_bancaria_id: "" }]);
  const [imputar, setImputar] = useState<Record<string, string>>({});
  const [obs, setObs] = useState("");
  const [sucursalId, setSucursalId] = useState("");
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();
  const cuentas = useCuentasBancarias();

  useEffect(() => {
    // sin sucursal la OP entra solo en la planilla global (022)
    void apiGet<Sucursal[]>("/sucursales")
      .then(({ data }) => setSucursales(data))
      .catch(() => setSucursales([]));
  }, []);

  useEffect(() => {
    if (!proveedor) {
      setPendientes([]);
      setImputar({});
      return;
    }
    void apiGet<Compra[]>(
      `/compras/comprobantes?proveedor_id=${proveedor.id}&estado=registrado&con_saldo=true&limit=100`,
    ).then(({ data }) =>
      setPendientes(data.filter((c) => ["factura", "nota_debito"].includes(c.clase))),
    );
  }, [proveedor]);

  const totalMedios = medios.reduce((a, m) => a + Number(m.importe || 0), 0);
  const totalImputado = Object.values(imputar).reduce((a, v) => a + Number(v || 0), 0);

  const hayDatos = proveedor !== null || medios.some((m) => m.importe) || obs.trim() !== "";

  async function intentarCerrar() {
    if (hayDatos && !(await confirmar("Hay datos sin guardar. ¿Descartar el pago?"))) return;
    onCerrar(false);
  }

  async function guardar() {
    if (!proveedor) return;
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/compras/pagos/ordenes-pago", {
        proveedor_id: proveedor.id,
        medios: medios
          .filter((m) => Number(m.importe) > 0)
          .map((m) => ({
            medio: m.medio,
            importe: m.importe,
            referencia: m.referencia.trim() || null,
            cuenta_bancaria_id:
              m.medio === "transferencia" && m.cuenta_bancaria_id
                ? m.cuenta_bancaria_id
                : null,
          })),
        imputaciones: Object.entries(imputar)
          .filter(([, v]) => Number(v) > 0)
          .map(([compra_id, importe]) => ({ compra_id, importe })),
        sucursal_id: sucursalId || null,
        observaciones: obs.trim() || null,
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el pago");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => void intentarCerrar()}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Nueva orden de pago</h2>
        <AlertError>{error}</AlertError>

        <div className="fila">
          <div className="field" style={{ flex: 2 }}>
            <label>Proveedor *</label>
            <BuscadorProveedor elegido={proveedor} onElegir={setProveedor} />
          </div>
          {sucursales.length > 0 && (
            <div className="field">
              <label>Sucursal</label>
              <select
                className="select"
                value={sucursalId}
                onChange={(ev) => setSucursalId(ev.target.value)}
              >
                <option value="">Global</option>
                {sucursales.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nombre}
                  </option>
                ))}
              </select>
            </div>
          )}
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
                placeholder="referencia (cheque/transferencia)"
                value={m.referencia}
                onChange={(ev) =>
                  setMedios(
                    medios.map((x, j) => (j === i ? { ...x, referencia: ev.target.value } : x)),
                  )
                }
              />
            </div>
            {m.medio === "transferencia" && cuentas.length > 0 && (
              <div className="field">
                <select
                  className="select"
                  value={m.cuenta_bancaria_id}
                  onChange={(ev) =>
                    setMedios(
                      medios.map((x, j) =>
                        j === i ? { ...x, cuenta_bancaria_id: ev.target.value } : x,
                      ),
                    )
                  }
                >
                  <option value="">— cuenta bancaria —</option>
                  {cuentas.map((c) => (
                    <option key={c.id} value={c.id}>
                      {etiquetaCuenta(c)}
                    </option>
                  ))}
                </select>
              </div>
            )}
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
          onClick={() =>
            setMedios([
              ...medios,
              { medio: "cheque", importe: "", referencia: "", cuenta_bancaria_id: "" },
            ])
          }
        >
          + medio
        </button>

        {proveedor && pendientes.length > 0 && (
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
            Pagado: <b className="mono">$ {fmt.format(totalMedios)}</b> · Imputado:{" "}
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
            disabled={!proveedor || totalMedios <= 0 || totalImputado > totalMedios || guardando}
            onClick={() => void guardar()}
          >
            {guardando ? "Guardando…" : "Registrar pago"}
          </button>
        </div>
      </div>
      {dialogos}
    </div>
  );
}

export default function PagosTab() {
  const [ordenes, setOrdenes] = useState<OrdenPago[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [vencimientos, setVencimientos] = useState<VencimientoPagar[]>([]);
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

  const cargarOrdenes = useCallback(async () => {
    setCargando(true);
    try {
      const params = new URLSearchParams({
        limit: String(POR_PAGINA),
        offset: String(pagina * POR_PAGINA),
      });
      if (q) params.set("q", q);
      if (desde) params.set("desde", desde);
      if (hasta) params.set("hasta", hasta);
      const { data, headers } = await apiGet<OrdenPago[]>(`/compras/pagos/ordenes-pago?${params}`);
      setOrdenes(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar pagos");
    } finally {
      setCargando(false);
    }
  }, [q, desde, hasta, pagina]);

  const cargarVencimientos = useCallback(async () => {
    try {
      const { data } = await apiGet<VencimientoPagar[]>("/compras/pagos/vencimientos?dias=30");
      setVencimientos(data);
    } catch {
      /* la grilla principal ya reporta errores */
    }
  }, []);

  useEffect(() => {
    void cargarOrdenes();
  }, [cargarOrdenes]);

  useEffect(() => {
    void cargarVencimientos();
  }, [cargarVencimientos]);

  async function anular(op: OrdenPago) {
    if (
      !(await confirmar(
        `¿Anular la orden de pago ${op.numero_formateado}? Se revierten sus imputaciones.`,
      ))
    )
      return;
    try {
      await apiPost(`/compras/pagos/ordenes-pago/${op.id}/anular`, {});
      void cargarOrdenes();
      void cargarVencimientos();
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
        <span className="page-sub" style={{ margin: 0, alignSelf: "center" }}>
          {cargando ? "Cargando…" : `${total} órdenes de pago`}
        </span>
        <div style={{ flex: 1 }} />
        <button className="btn btn-primary" onClick={() => setModalAbierto(true)}>
          + Nueva orden de pago
        </button>
      </div>
      <AlertError>{error}</AlertError>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>OP</th>
              <th>Fecha</th>
              <th>Proveedor</th>
              <th className="num">Total</th>
              <th className="num">Imputado</th>
              <th className="num">A cuenta</th>
              <th>Medios</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {ordenes.map((op) => (
              <tr key={op.id} className={op.estado === "anulada" ? "fila-anulada" : ""}>
                <td className="mono">{op.numero_formateado}</td>
                <td className="mono">{op.fecha}</td>
                <td>{op.proveedor_nombre}</td>
                <td className="num mono">{fmt.format(Number(op.total))}</td>
                <td className="num mono">{fmt.format(Number(op.aplicado))}</td>
                <td className="num mono">{fmt.format(Number(op.a_cuenta))}</td>
                <td>{op.medios.map((m) => m.medio).join(", ")}</td>
                <td>
                  {op.estado === "anulada" ? (
                    <ChipEstado estado={op.estado} />
                  ) : (
                    <button className="mini-btn" onClick={() => void anular(op)}>
                      anular
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && ordenes.length === 0 && (
          <div className="vacio">
            {q || desde || hasta ? "Sin resultados para esa búsqueda" : "Sin pagos registrados"}
          </div>
        )}
      </div>
      <Paginado pagina={pagina} porPagina={POR_PAGINA} total={total} onPagina={setPagina} />

      <div className="seccion" style={{ marginTop: 16 }}>
        Cuentas a pagar — vencimientos próximos (30 días)
      </div>
      <div className="tabla-card">
        <table className="tabla tabla-mini">
          <thead>
            <tr>
              <th>Vencimiento</th>
              <th>Proveedor</th>
              <th>Comprobante</th>
              <th className="num">Cuota</th>
              <th className="num">Importe cuota</th>
              <th className="num">Saldo compra</th>
            </tr>
          </thead>
          <tbody>
            {vencimientos.map((v, i) => (
              <tr key={i}>
                <td className="mono">
                  {v.fecha_vto} {v.vencida && <span className="neg">⚠ vencida</span>}
                </td>
                <td>{v.proveedor_nombre}</td>
                <td className="mono">
                  {v.tipo_codigo} {v.numero}
                </td>
                <td className="num mono">{v.nro_cuota}</td>
                <td className="num mono">{fmt.format(Number(v.importe_cuota))}</td>
                <td className="num mono">{fmt.format(Number(v.saldo_compra))}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && vencimientos.length === 0 && (
          <div className="vacio">Nada por pagar en los próximos 30 días 🎉</div>
        )}
      </div>

      {modalAbierto && (
        <OrdenPagoModal
          onCerrar={(refrescar) => {
            setModalAbierto(false);
            if (refrescar) {
              void cargarOrdenes();
              void cargarVencimientos();
            }
          }}
        />
      )}
      {dialogos}
    </>
  );
}
