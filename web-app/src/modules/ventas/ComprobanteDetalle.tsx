// Detalle de un comprobante emitido (o borrador): renglones, alícuotas,
// vencimientos y datos fiscales. El listado viaja liviano, así que acá se
// pide el comprobante completo por id.

import { useEffect, useState } from "react";
import { ApiError, apiDescargar, apiGet, apiPost } from "../../lib/api";
import type { Comprobante, ImpresionPayload } from "../../lib/types";
import { AlertError, AlertOk } from "../../components/Alertas";
import ChipEstado from "../../components/ChipEstado";
import { imprimirComprobante } from "./impresion";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

export default function ComprobanteDetalle({
  id,
  onCerrar,
}: {
  id: string;
  onCerrar: () => void;
}) {
  const [comp, setComp] = useState<Comprobante | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [enviarAbierto, setEnviarAbierto] = useState(false);
  const [emailEnvio, setEmailEnvio] = useState("");

  useEffect(() => {
    void apiGet<Comprobante>(`/ventas/comprobantes/${id}`)
      .then(({ data }) => setComp(data))
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "No se pudo cargar el comprobante"),
      );
  }, [id]);

  async function imprimir() {
    setOcupado(true);
    try {
      const { data } = await apiGet<ImpresionPayload>(`/ventas/comprobantes/${id}/impresion`);
      imprimirComprobante(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo imprimir");
    } finally {
      setOcupado(false);
    }
  }

  async function descargarPdf() {
    if (!comp) return;
    setOcupado(true);
    setError(null);
    try {
      const nombre = `${comp.tipo_descripcion} ${comp.numero_formateado ?? ""}`
        .trim()
        .replace(/[^A-Za-z0-9]+/g, "-");
      await apiDescargar(`/ventas/comprobantes/${id}/pdf`, `${nombre}.pdf`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo descargar el PDF");
    } finally {
      setOcupado(false);
    }
  }

  async function enviarEmail() {
    setOcupado(true);
    setError(null);
    setOk(null);
    try {
      const res = await apiPost<{ destinatario: string; estado: string }>(
        `/ventas/comprobantes/${id}/enviar`,
        emailEnvio.trim() ? { email: emailEnvio.trim() } : {},
      );
      setOk(
        res.estado === "simulado"
          ? `Envío registrado en modo simulado (no salió un email real) — destino ${res.destinatario}`
          : `Enviado a ${res.destinatario}`,
      );
      setEnviarAbierto(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar el email");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        {comp ? (
          <>
            <h2>
              {comp.tipo_descripcion} {comp.numero_formateado ?? "(borrador)"}{" "}
              <ChipEstado estado={comp.estado} cae={comp.cae} arcaResultado={comp.arca_resultado} />
            </h2>
            <div className="fila" style={{ flexWrap: "wrap", gap: "var(--space-6)" }}>
              <div className="field">
                <label>Fecha</label>
                <span className="mono">{comp.fecha}</span>
              </div>
              <div className="field" style={{ flex: 2 }}>
                <label>Receptor</label>
                <span>
                  {comp.receptor_nombre}
                  {comp.receptor_doc_nro && (
                    <span className="mono"> — {comp.receptor_doc_nro}</span>
                  )}{" "}
                  ({comp.receptor_condicion_iva})
                </span>
              </div>
              <div className="field">
                <label>Condición</label>
                <span>{comp.contado ? "Contado" : (comp.condicion_venta_desc ?? "Cta. cte.")}</span>
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
                    <th className="num">P. unitario</th>
                    <th className="num">Bonif %</th>
                    <th className="num">IVA %</th>
                    <th className="num">Importe</th>
                  </tr>
                </thead>
                <tbody>
                  {(comp.items ?? []).map((i) => (
                    <tr key={i.id}>
                      <td className="mono">{i.codigo ?? "—"}</td>
                      <td>{i.descripcion}</td>
                      <td className="num mono">{Number(i.cantidad)}</td>
                      <td className="num mono">{fmt.format(Number(i.precio_unitario))}</td>
                      <td className="num mono">
                        {Number(i.bonif_pct) > 0 ? Number(i.bonif_pct) : "—"}
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
                Neto: <b className="mono">$ {fmt.format(Number(comp.neto_gravado))}</b> · IVA:{" "}
                <b className="mono">$ {fmt.format(Number(comp.iva))}</b> · Total:{" "}
                <b className="mono">$ {fmt.format(Number(comp.total))}</b>
                {Number(comp.saldo) !== 0 && (
                  <>
                    {" "}
                    · Saldo: <b className="mono">$ {fmt.format(Number(comp.saldo))}</b>
                  </>
                )}
              </div>
            </div>

            {(comp.vencimientos ?? []).length > 0 && (
              <>
                <div className="seccion">Vencimientos</div>
                {(comp.vencimientos ?? []).map((v) => (
                  <div key={v.nro_cuota} className="mono" style={{ fontSize: "var(--size-btn)" }}>
                    Cuota {v.nro_cuota}: {v.fecha_vto} — $ {fmt.format(Number(v.importe))}
                  </div>
                ))}
              </>
            )}

            {comp.cae && (
              <p className="mono" style={{ marginTop: "var(--space-6)", fontSize: "var(--size-btn)" }}>
                CAE {comp.cae} — vto. {comp.cae_vencimiento}
              </p>
            )}
            {comp.observaciones && <p style={{ marginTop: "var(--space-4)" }}>{comp.observaciones}</p>}
          </>
        ) : (
          !error && <p>Cargando…</p>
        )}
        <AlertError>{error}</AlertError>
        <AlertOk>{ok}</AlertOk>

        {enviarAbierto && (
          <div className="fila" style={{ gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
            <div className="field" style={{ flex: 1 }}>
              <label htmlFor="email-envio">Enviar a (vacío = email del cliente)</label>
              <input
                id="email-envio"
                className="input"
                type="email"
                value={emailEnvio}
                onChange={(e) => setEmailEnvio(e.target.value)}
                placeholder="cliente@dominio.com"
                autoFocus
              />
            </div>
            <button
              type="button"
              className="btn btn-primary"
              disabled={ocupado}
              onClick={() => void enviarEmail()}
            >
              Enviar
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setEnviarAbierto(false)}
            >
              Cancelar
            </button>
          </div>
        )}

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={onCerrar}>
            Cerrar
          </button>
          {comp?.estado === "emitido" && (
            <>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={ocupado}
                onClick={() => void descargarPdf()}
              >
                PDF
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={ocupado}
                onClick={() => setEnviarAbierto((v) => !v)}
              >
                Enviar por email
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={ocupado}
                onClick={() => void imprimir()}
              >
                Imprimir
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
