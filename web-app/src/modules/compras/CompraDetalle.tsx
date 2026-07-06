// Detalle de un comprobante de compra: renglones, percepciones y
// vencimientos. El listado viaja liviano, así que acá se pide completo.

import { useEffect, useState } from "react";
import { ApiError, apiGet } from "../../lib/api";
import type { Compra } from "../../lib/types";
import { AlertError } from "../../components/Alertas";
import ChipEstado from "../../components/ChipEstado";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

export default function CompraDetalle({ id, onCerrar }: { id: string; onCerrar: () => void }) {
  const [compra, setCompra] = useState<Compra | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiGet<Compra>(`/compras/comprobantes/${id}`)
      .then(({ data }) => setCompra(data))
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el comprobante"),
      );
  }, [id]);

  const percepciones = compra
    ? Number(compra.percepcion_iva) +
      Number(compra.percepcion_iibb) +
      Number(compra.impuestos_internos) +
      Number(compra.otros_tributos)
    : 0;

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        {compra ? (
          <>
            <h2>
              {compra.tipo_descripcion} {compra.numero_formateado}{" "}
              <ChipEstado estado={compra.estado} />
            </h2>
            <div className="fila" style={{ flexWrap: "wrap", gap: "var(--space-6)" }}>
              <div className="field">
                <label>Fecha</label>
                <span className="mono">{compra.fecha}</span>
              </div>
              <div className="field" style={{ flex: 2 }}>
                <label>Proveedor</label>
                <span>
                  {compra.proveedor_nombre}
                  {compra.proveedor_cuit && <span className="mono"> — {compra.proveedor_cuit}</span>}{" "}
                  ({compra.proveedor_condicion_iva})
                </span>
              </div>
              <div className="field">
                <label>Período IVA</label>
                <span className="mono">{compra.periodo_iva ?? "—"}</span>
              </div>
            </div>

            <div className="seccion">Renglones</div>
            <div className="tabla-card">
              <table className="tabla tabla-mini">
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Descripción</th>
                    <th className="num">Cant.</th>
                    <th className="num">Costo unit.</th>
                    <th className="num">Bonifs %</th>
                    <th className="num">IVA %</th>
                    <th className="num">Importe</th>
                  </tr>
                </thead>
                <tbody>
                  {(compra.items ?? []).map((i) => (
                    <tr key={i.id}>
                      <td className="mono">{i.codigo ?? "—"}</td>
                      <td>{i.descripcion}</td>
                      <td className="num mono">{Number(i.cantidad)}</td>
                      <td className="num mono">{fmt.format(Number(i.costo_unitario))}</td>
                      <td className="num mono">
                        {Number(i.bonif_1) > 0 || Number(i.bonif_2) > 0
                          ? `${Number(i.bonif_1)}+${Number(i.bonif_2)}`
                          : "—"}
                      </td>
                      <td className="num mono">{Number(i.tasa_iva)}</td>
                      <td className="num mono">{fmt.format(Number(i.importe_total))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="fila" style={{ justifyContent: "flex-end", marginTop: "var(--space-6)" }}>
              <div className="total-preview">
                Neto: <b className="mono">$ {fmt.format(Number(compra.neto_gravado))}</b> · IVA:{" "}
                <b className="mono">$ {fmt.format(Number(compra.iva))}</b>
                {percepciones > 0 && (
                  <>
                    {" "}
                    · Percep./otros: <b className="mono">$ {fmt.format(percepciones)}</b>
                  </>
                )}{" "}
                · Total: <b className="mono">$ {fmt.format(Number(compra.total))}</b>
                {Number(compra.saldo) !== 0 && (
                  <>
                    {" "}
                    · Saldo: <b className="mono">$ {fmt.format(Number(compra.saldo))}</b>
                  </>
                )}
              </div>
            </div>

            {(compra.vencimientos ?? []).length > 0 && (
              <>
                <div className="seccion">Vencimientos</div>
                {(compra.vencimientos ?? []).map((v) => (
                  <div key={v.nro_cuota} className="mono" style={{ fontSize: "var(--size-btn)" }}>
                    Cuota {v.nro_cuota}: {v.fecha_vto} — $ {fmt.format(Number(v.importe))}
                  </div>
                ))}
              </>
            )}
            {compra.observaciones && (
              <p style={{ marginTop: "var(--space-4)" }}>{compra.observaciones}</p>
            )}
          </>
        ) : (
          !error && <p>Cargando…</p>
        )}
        <AlertError>{error}</AlertError>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={onCerrar}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
