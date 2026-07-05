// Pagos a proveedores: órdenes de pago (documento interno) con medios de
// pago e imputación contra facturas de compra pendientes; el resto queda a
// cuenta. Debajo, las cuentas a pagar (vencimientos próximos).

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Compra, OrdenPago, Proveedor, VencimientoPagar } from "../../lib/types";
import { BuscadorProveedor } from "./CompraForm";

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
  const [medios, setMedios] = useState<{ medio: string; importe: string; referencia: string }[]>([
    { medio: "transferencia", importe: "", referencia: "" },
  ]);
  const [imputar, setImputar] = useState<Record<string, string>>({});
  const [obs, setObs] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

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
          })),
        imputaciones: Object.entries(imputar)
          .filter(([, v]) => Number(v) > 0)
          .map(([compra_id, importe]) => ({ compra_id, importe })),
        observaciones: obs.trim() || null,
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el pago");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Nueva orden de pago</h2>
        {error && <div className="login-error">{error}</div>}

        <div className="field">
          <label>Proveedor *</label>
          <BuscadorProveedor elegido={proveedor} onElegir={setProveedor} />
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
          onClick={() => setMedios([...medios, { medio: "cheque", importe: "", referencia: "" }])}
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
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
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
    </div>
  );
}

export default function PagosTab() {
  const [ordenes, setOrdenes] = useState<OrdenPago[]>([]);
  const [vencimientos, setVencimientos] = useState<VencimientoPagar[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const [ops, vtos] = await Promise.all([
        apiGet<OrdenPago[]>("/compras/pagos/ordenes-pago?limit=100"),
        apiGet<VencimientoPagar[]>("/compras/pagos/vencimientos?dias=30"),
      ]);
      setOrdenes(ops.data);
      setVencimientos(vtos.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar pagos");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function anular(op: OrdenPago) {
    if (
      !window.confirm(`¿Anular la orden de pago ${op.numero_formateado}? Se revierten sus imputaciones.`)
    )
      return;
    try {
      await apiPost(`/compras/pagos/ordenes-pago/${op.id}/anular`, {});
      void cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo anular");
    }
  }

  return (
    <>
      <div className="toolbar">
        <span className="page-sub" style={{ margin: 0 }}>
          {cargando ? "Cargando…" : `${ordenes.length} órdenes de pago`}
        </span>
        <div style={{ flex: 1 }} />
        <button className="btn btn-primary" onClick={() => setModalAbierto(true)}>
          + Nueva orden de pago
        </button>
      </div>
      {error && <div className="login-error">{error}</div>}

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
                    <span className="chip chip-anulado">anulada</span>
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
        {!cargando && ordenes.length === 0 && <div className="vacio">Sin pagos registrados</div>}
      </div>

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
            if (refrescar) void cargar();
          }}
        />
      )}
    </>
  );
}
