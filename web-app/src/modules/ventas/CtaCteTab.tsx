// Cuentas corrientes: saldos por cliente (morosidad-lite) con drill-down
// al detalle de movimientos (debe/haber/saldo acumulado).

import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { MovimientoCtaCte, SaldoCliente } from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

function DetalleModal({ fila, onCerrar }: { fila: SaldoCliente; onCerrar: () => void }) {
  const [movs, setMovs] = useState<MovimientoCtaCte[]>([]);
  const [saldo, setSaldo] = useState("0");
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await apiGet<{ movimientos: MovimientoCtaCte[]; saldo: string }>(
          `/cobranzas/cuenta-corriente/${fila.cliente_id}`,
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
          Saldo actual: <b className="mono">$ {fmt.format(Number(saldo))}</b>
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

export default function CtaCteTab() {
  const [saldos, setSaldos] = useState<SaldoCliente[]>([]);
  const [soloDeudores, setSoloDeudores] = useState(true);
  const [cargando, setCargando] = useState(true);
  const [detalle, setDetalle] = useState<SaldoCliente | null>(null);

  useEffect(() => {
    setCargando(true);
    void apiGet<SaldoCliente[]>(`/cobranzas/saldos?solo_deudores=${soloDeudores}`)
      .then(({ data }) => setSaldos(data))
      .finally(() => setCargando(false));
  }, [soloDeudores]);

  const totalDeuda = saldos.reduce((a, s) => a + Number(s.saldo), 0);

  return (
    <>
      <div className="toolbar">
        <span className="page-sub" style={{ margin: 0 }}>
          {cargando
            ? "Cargando…"
            : `${saldos.length} clientes · deuda total $ ${fmt.format(totalDeuda)}`}
        </span>
        <label className="check">
          <input
            type="checkbox"
            checked={soloDeudores}
            onChange={(ev) => setSoloDeudores(ev.target.checked)}
          />
          Solo deudores
        </label>
      </div>
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Código</th>
              <th>Cliente</th>
              <th className="num">Saldo</th>
              <th className="num">Vencido</th>
              <th className="num">Límite de crédito</th>
            </tr>
          </thead>
          <tbody>
            {saldos.map((s) => (
              <tr key={s.cliente_id} onClick={() => setDetalle(s)}>
                <td className="mono">{s.codigo ?? "—"}</td>
                <td>{s.nombre}</td>
                <td className={`num mono ${Number(s.saldo) > 0 ? "neg" : "pos"}`}>
                  {fmt.format(Number(s.saldo))}
                </td>
                <td className="num mono">
                  {Number(s.vencido) > 0 ? (
                    <span className="neg">{fmt.format(Number(s.vencido))} ⚠</span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="num mono">
                  {s.limite_credito ? fmt.format(Number(s.limite_credito)) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && saldos.length === 0 && (
          <div className="vacio">
            {soloDeudores ? "Nadie debe nada 🎉" : "Sin cuentas corrientes con movimientos"}
          </div>
        )}
      </div>
      {detalle && <DetalleModal fila={detalle} onCerrar={() => setDetalle(null)} />}
    </>
  );
}
