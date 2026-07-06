// Tesorería (Fase 8): cash-flow proyectado. Serie temporal de entradas/salidas y
// saldo acumulado, con detalle expandible por punto. Barra visual simple (sin
// dependencia de gráficos: proporción del saldo respecto al máximo).

import { Fragment, useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { fmt, hoy, type Cashflow } from "./tipos";

function enDias(n: number) {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

export default function TesoreriaTab() {
  const [gran, setGran] = useState<"dia" | "semana" | "mes">("semana");
  const [hasta, setHasta] = useState(enDias(90));
  const [cf, setCf] = useState<Cashflow | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [abierto, setAbierto] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { data } = await apiGet<Cashflow>(
        `/tesoreria/cashflow?granularidad=${gran}&desde=${hoy()}&hasta=${hasta}`,
      );
      setCf(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al calcular la tesorería");
    } finally {
      setCargando(false);
    }
  }, [gran, hasta]);

  useEffect(() => { void cargar(); }, [cargar]);

  const saldos = cf ? cf.serie.map((p) => Number(p.saldo_proyectado)) : [];
  const maxAbs = Math.max(1, ...saldos.map((s) => Math.abs(s)));

  return (
    <>
      {error && <div className="login-error">{error}</div>}

      <div className="toolbar">
        <label className="hint-mono">Proyectar hasta</label>
        <input type="date" className="input" value={hasta} onChange={(e) => setHasta(e.target.value)} style={{ width: 170 }} />
        <select className="select" value={gran} onChange={(e) => setGran(e.target.value as typeof gran)}>
          <option value="dia">Por día</option>
          <option value="semana">Por semana</option>
          <option value="mes">Por mes</option>
        </select>
      </div>

      {cf && (
        <div className="import-resultado" style={{ marginBottom: 12 }}>
          Saldo inicial de tesorería (caja efectivo + bancos):{" "}
          <b className="mono">${fmt.format(Number(cf.saldo_inicial))}</b>
        </div>
      )}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Período</th>
              <th className="num">Entradas</th>
              <th className="num">Salidas</th>
              <th className="num">Saldo proyectado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {cf?.serie.map((p) => {
              const saldo = Number(p.saldo_proyectado);
              const neg = saldo < 0;
              return (
                <Fragment key={p.fecha}>
                  <tr style={{ cursor: "pointer" }} onClick={() => setAbierto(abierto === p.fecha ? null : p.fecha)}>
                    <td className="mono">{p.fecha}</td>
                    <td className="num mono" style={{ color: "var(--exito, #1f8a65)" }}>
                      +${fmt.format(Number(p.entradas))}
                    </td>
                    <td className="num mono" style={{ color: "var(--error, #cf2d56)" }}>
                      −${fmt.format(Number(p.salidas))}
                    </td>
                    <td className="num mono" style={{ fontWeight: 700, color: neg ? "var(--error, #cf2d56)" : undefined }}>
                      ${fmt.format(saldo)}
                    </td>
                    <td>
                      <div style={{
                        height: 8, borderRadius: 4, background: "var(--surface-300, #e5e3dd)",
                        width: 120, position: "relative", overflow: "hidden",
                      }}>
                        <div style={{
                          position: "absolute", top: 0, bottom: 0,
                          left: neg ? undefined : 0, right: neg ? 0 : undefined,
                          width: `${(Math.abs(saldo) / maxAbs) * 100}%`,
                          background: neg ? "var(--error, #cf2d56)" : "var(--exito, #1f8a65)",
                        }} />
                      </div>
                    </td>
                  </tr>
                  {abierto === p.fecha && p.detalle.length > 0 && (
                    <tr>
                      <td colSpan={5} style={{ background: "var(--surface-200, #f5f4f0)" }}>
                        <div style={{ padding: "6px 12px" }}>
                          {p.detalle.map((d, i) => (
                            <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85em" }}>
                              <span>{d.concepto} · {d.referencia}</span>
                              <span className="mono">${fmt.format(Number(d.importe))}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
        {!cargando && cf?.serie.length === 0 && (
          <div className="vacio">Sin vencimientos ni cheques proyectados en el rango.</div>
        )}
      </div>
    </>
  );
}
