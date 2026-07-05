// Cuentas corrientes de proveedores: cuánto le debemos a cada uno, con
// drill-down al detalle de movimientos (espejo de CtaCteTab de Ventas).

import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { MovimientoCtaCte, SaldoProveedor } from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

function DetalleModal({ fila, onCerrar }: { fila: SaldoProveedor; onCerrar: () => void }) {
  const [movs, setMovs] = useState<MovimientoCtaCte[]>([]);
  const [saldo, setSaldo] = useState("0");
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await apiGet<{ movimientos: MovimientoCtaCte[]; saldo: string }>(
          `/compras/pagos/cuenta-corriente/${fila.proveedor_id}`,
        );
        setMovs(data.movimientos);
        setSaldo(data.saldo);
      } finally {
        setCargando(false);
      }
    })();
  }, [fila]);

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Cuenta corriente — {fila.nombre}</h2>
        {cargando ? (
          <p className="page-sub">Cargando…</p>
        ) : movs.length === 0 ? (
          <div className="vacio">Sin movimientos en cuenta corriente</div>
        ) : (
          <div className="tabla-card">
            <table className="tabla tabla-mini">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Comprobante</th>
                  <th className="num">Debe</th>
                  <th className="num">Haber</th>
                  <th className="num">Pendiente</th>
                  <th className="num">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {movs.map((m, i) => (
                  <tr key={i}>
                    <td className="mono">{m.fecha}</td>
                    <td>
                      {m.tipo} <span className="mono">{m.numero}</span>
                    </td>
                    <td className="num mono">{Number(m.debe) > 0 ? fmt.format(Number(m.debe)) : "—"}</td>
                    <td className="num mono">
                      {Number(m.haber) > 0 ? fmt.format(Number(m.haber)) : "—"}
                    </td>
                    <td className="num mono">
                      {Number(m.pendiente) > 0 ? fmt.format(Number(m.pendiente)) : "—"}
                    </td>
                    <td className={`num mono ${Number(m.saldo_acumulado) > 0 ? "neg" : "pos"}`}>
                      {fmt.format(Number(m.saldo_acumulado))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="page-sub">
          Le debemos: <b className="mono">$ {fmt.format(Number(saldo))}</b>
        </p>
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={onCerrar}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CtaCteProvTab() {
  const [saldos, setSaldos] = useState<SaldoProveedor[]>([]);
  const [soloConDeuda, setSoloConDeuda] = useState(true);
  const [cargando, setCargando] = useState(true);
  const [detalle, setDetalle] = useState<SaldoProveedor | null>(null);

  useEffect(() => {
    setCargando(true);
    void apiGet<SaldoProveedor[]>(`/compras/pagos/saldos?solo_con_deuda=${soloConDeuda}`)
      .then(({ data }) => setSaldos(data))
      .finally(() => setCargando(false));
  }, [soloConDeuda]);

  const totalDeuda = saldos.reduce((a, s) => a + Number(s.saldo), 0);

  return (
    <>
      <div className="toolbar">
        <span className="page-sub" style={{ margin: 0 }}>
          {cargando
            ? "Cargando…"
            : `${saldos.length} proveedores · les debemos $ ${fmt.format(totalDeuda)}`}
        </span>
        <label className="check">
          <input
            type="checkbox"
            checked={soloConDeuda}
            onChange={(ev) => setSoloConDeuda(ev.target.checked)}
          />
          Solo con deuda
        </label>
      </div>
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Código</th>
              <th>Proveedor</th>
              <th className="num">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {saldos.map((s) => (
              <tr key={s.proveedor_id} onClick={() => setDetalle(s)}>
                <td className="mono">{s.codigo ?? "—"}</td>
                <td>{s.nombre}</td>
                <td className={`num mono ${Number(s.saldo) > 0 ? "neg" : "pos"}`}>
                  {fmt.format(Number(s.saldo))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && saldos.length === 0 && (
          <div className="vacio">
            {soloConDeuda ? "No le debemos nada a nadie 🎉" : "Sin cuentas corrientes con movimientos"}
          </div>
        )}
      </div>
      {detalle && <DetalleModal fila={detalle} onCerrar={() => setDetalle(null)} />}
    </>
  );
}
