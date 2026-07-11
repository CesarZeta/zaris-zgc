// Balance general (F9-bis §6.3): estado de situación patrimonial al corte —
// Activo / Pasivo / PN con el árbol del plan y el resultado del ejercicio
// inyectado en el PN. Export CSV, paquete contador (ZIP) e impresión.

import { useCallback, useEffect, useState } from "react";
import { apiDescargar, apiGet } from "../../lib/api";
import { AlertError } from "../../components/Alertas";
import type { Balance } from "./tipos";
import { fmt, hoy, primeroDelMes } from "./tipos";

const SECCION_LABEL: Record<string, string> = {
  activo: "ACTIVO",
  pasivo: "PASIVO",
  pn: "PATRIMONIO NETO",
};

export default function BalanceTab() {
  const [hasta, setHasta] = useState(hoy());
  const [datos, setDatos] = useState<Balance | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const { data } = await apiGet<Balance>(`/contabilidad/balance?hasta=${hasta}`);
      setDatos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el balance");
    }
  }, [hasta]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  return (
    <>
      <AlertError>{error}</AlertError>
      <div className="toolbar no-imprimir">
        <label className="texto-suave">Al:</label>
        <input type="date" className="input" style={{ width: 160 }} value={hasta}
          onChange={(ev) => setHasta(ev.target.value)} />
        <button className="btn" onClick={() => void apiDescargar(
          `/contabilidad/balance.csv?hasta=${hasta}`, `balance-${hasta}.csv`)}>
          Exportar CSV
        </button>
        <button className="btn" onClick={() => void apiDescargar(
          `/contabilidad/export-contador.zip?desde=${primeroDelMes().slice(0, 4)}-01-01&hasta=${hasta}`,
          `contabilidad-${hasta}.zip`)}>
          Paquete contador (ZIP)
        </button>
        <button className="btn" onClick={() => window.print()}>Imprimir</button>
        {datos && (
          <span className="mono" style={{ marginLeft: "auto" }}>
            {datos.ecuacion_ok ? "✓ A = P + PN" : "✗ NO CIERRA LA ECUACIÓN"}
          </span>
        )}
      </div>

      {datos && (
        <div className="tabla-card" style={{ padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>Estado de situación patrimonial al {datos.hasta}</h2>
          {datos.secciones.map((sec) => (
            <div key={sec.tipo} style={{ marginBottom: 16 }}>
              <table className="tabla tabla-mini">
                <thead>
                  <tr>
                    <th style={{ width: 110 }}>{SECCION_LABEL[sec.tipo]}</th>
                    <th />
                    <th className="num" style={{ width: 160 }} />
                  </tr>
                </thead>
                <tbody>
                  {sec.cuentas.map((f) => (
                    <tr key={f.cuenta_id} style={{ fontWeight: f.imputable ? 400 : 600 }}>
                      <td className="mono">{f.codigo}</td>
                      <td style={{ paddingLeft: 8 + f.nivel * 18 }}>{f.nombre}</td>
                      <td className="num mono">$ {fmt.format(Number(f.saldo))}</td>
                    </tr>
                  ))}
                  {sec.tipo === "pn" && Number(datos.resultado_ejercicio) !== 0 && (
                    <tr>
                      <td className="mono" />
                      <td style={{ paddingLeft: 8 }}>Resultado del ejercicio</td>
                      <td className="num mono">$ {fmt.format(Number(datos.resultado_ejercicio))}</td>
                    </tr>
                  )}
                  <tr style={{ fontWeight: 700, borderTop: "2px solid var(--tinta, #26251e)" }}>
                    <td />
                    <td>Total {SECCION_LABEL[sec.tipo].toLowerCase()}</td>
                    <td className="num mono">
                      $ {fmt.format(Number(sec.tipo === "pn" ? datos.pn_total : sec.total))}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
          <div className="mono" style={{ textAlign: "right" }}>
            Activo $ {fmt.format(Number(datos.activo_total))} = Pasivo ${" "}
            {fmt.format(Number(datos.pasivo_total))} + PN $ {fmt.format(Number(datos.pn_total))}
          </div>
          {datos.secciones.every((s) => s.cuentas.length === 0) && (
            <p className="texto-suave">
              Sin saldos al corte — regenerá los asientos desde el Diario (y cargá el asiento
              de apertura si venís con historia previa).
            </p>
          )}
        </div>
      )}
    </>
  );
}
