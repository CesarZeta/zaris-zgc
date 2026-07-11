// Sumas y saldos por cuenta (con verificación de balance) + mayor de una
// cuenta al hacer click en la fila.

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { AlertError } from "../../components/Alertas";
import type { MayorMovimiento, SumasYSaldos } from "./tipos";
import { fmt, hoy, primeroDelMes } from "./tipos";

export default function ReportesTab() {
  const [desde, setDesde] = useState(primeroDelMes());
  const [hasta, setHasta] = useState(hoy());
  const [datos, setDatos] = useState<SumasYSaldos | null>(null);
  const [mayor, setMayor] = useState<{
    cuenta: { id: string; codigo: string; nombre: string };
    movimientos: MayorMovimiento[];
    saldo: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    setMayor(null);
    try {
      const { data } = await apiGet<SumasYSaldos>(
        `/contabilidad/sumas-y-saldos?desde=${desde}&hasta=${hasta}`,
      );
      setDatos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar sumas y saldos");
    }
  }, [desde, hasta]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function verMayor(cuenta_id: string) {
    try {
      const { data } = await apiGet<typeof mayor>(
        `/contabilidad/mayor/${cuenta_id}?desde=${desde}&hasta=${hasta}`,
      );
      setMayor(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el mayor");
    }
  }

  return (
    <>
      <AlertError>{error}</AlertError>
      <div className="toolbar">
        <input type="date" className="input" style={{ width: 160 }} value={desde}
          onChange={(ev) => setDesde(ev.target.value)} />
        <span>→</span>
        <input type="date" className="input" style={{ width: 160 }} value={hasta}
          onChange={(ev) => setHasta(ev.target.value)} />
        {datos && (
          <span className="mono" style={{ marginLeft: "auto" }}>
            Debe $ {fmt.format(Number(datos.total_debe))} · Haber ${" "}
            {fmt.format(Number(datos.total_haber))} ·{" "}
            {datos.balanceado ? "✓ balanceado" : "✗ NO BALANCEA"}
          </span>
        )}
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th style={{ width: 100 }}>Código</th>
              <th>Cuenta</th>
              <th className="num">Debe</th>
              <th className="num">Haber</th>
              <th className="num">Saldo deudor</th>
              <th className="num">Saldo acreedor</th>
            </tr>
          </thead>
          <tbody>
            {(datos?.filas ?? []).map((f) => (
              <tr key={f.cuenta_id} style={{ cursor: "pointer" }}
                onClick={() => void verMayor(f.cuenta_id)}>
                <td className="mono">{f.codigo}</td>
                <td>{f.nombre}</td>
                <td className="num mono">$ {fmt.format(Number(f.debe))}</td>
                <td className="num mono">$ {fmt.format(Number(f.haber))}</td>
                <td className="num mono">{Number(f.saldo_deudor) > 0 ? `$ ${fmt.format(Number(f.saldo_deudor))}` : ""}</td>
                <td className="num mono">{Number(f.saldo_acreedor) > 0 ? `$ ${fmt.format(Number(f.saldo_acreedor))}` : ""}</td>
              </tr>
            ))}
            {(datos?.filas ?? []).length === 0 && (
              <tr>
                <td colSpan={6} className="texto-suave">
                  Sin movimientos en el rango — regenerá los asientos desde el Diario.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {mayor && (
        <>
          <h2 style={{ marginTop: 16 }}>
            Mayor — {mayor.cuenta.codigo} {mayor.cuenta.nombre}
          </h2>
          <div className="tabla-card">
            <table className="tabla tabla-mini">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Nro</th>
                  <th>Descripción</th>
                  <th className="num">Debe</th>
                  <th className="num">Haber</th>
                  <th className="num">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {mayor.movimientos.map((m, i) => (
                  <tr key={i}>
                    <td>{m.fecha}</td>
                    <td className="mono">{m.numero ?? "—"}</td>
                    <td>{m.descripcion}{m.detalle ? ` — ${m.detalle}` : ""}</td>
                    <td className="num mono">{Number(m.debe) > 0 ? `$ ${fmt.format(Number(m.debe))}` : ""}</td>
                    <td className="num mono">{Number(m.haber) > 0 ? `$ ${fmt.format(Number(m.haber))}` : ""}</td>
                    <td className="num mono">$ {fmt.format(Number(m.saldo))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
