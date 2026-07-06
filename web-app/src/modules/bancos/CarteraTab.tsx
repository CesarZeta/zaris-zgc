// Cartera de cheques (Fase 8): listado con filtros + chips de estado, acciones
// del ciclo de vida (depositar/acreditar/endosar/rechazar/anular/debitar) y alta
// manual de cheque de tercero. Resumen por estado arriba.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDescargar, apiGet, apiPost } from "../../lib/api";
import { useDialogos } from "../../components/dialogos";
import {
  CHIP_CHEQUE,
  ESTADO_LABEL,
  fmt,
  hoy,
  type Cheque,
  type CuentaBancaria,
} from "./tipos";

interface Resumen {
  clase: string;
  estado: string;
  cantidad: number;
  importe: string;
}
interface Proveedor {
  id: string;
  entidad: { razon_social: string };
}

const ESTADOS = [
  "en_cartera",
  "depositado",
  "acreditado",
  "endosado",
  "rechazado",
  "anulado",
  "emitido",
  "debitado",
];

export default function CarteraTab() {
  const [cheques, setCheques] = useState<Cheque[]>([]);
  const [resumen, setResumen] = useState<Resumen[]>([]);
  const [cuentas, setCuentas] = useState<CuentaBancaria[]>([]);
  const [clase, setClase] = useState("");
  const [estado, setEstado] = useState("");
  const [q, setQ] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [alta, setAlta] = useState(false);
  const [accion, setAccion] = useState<{ cheque: Cheque; tipo: "depositar" | "endosar" } | null>(null);
  const { confirmar, pedirTexto, dialogos } = useDialogos();

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (clase) params.set("clase", clase);
      if (estado) params.set("estado", estado);
      if (q.trim()) params.set("q", q.trim());
      const [ch, res] = await Promise.all([
        apiGet<Cheque[]>(`/cheques?${params.toString()}`),
        apiGet<Resumen[]>("/cheques/resumen"),
      ]);
      setCheques(ch.data);
      setResumen(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar la cartera");
    } finally {
      setCargando(false);
    }
  }, [clase, estado, q]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function accionSimple(cheque: Cheque, verbo: string, endpoint: string, pregunta: string) {
    if (!(await confirmar(pregunta))) return;
    setOcupado(true);
    setError(null);
    try {
      const r = await apiPost<{ reabierto?: { importe_revertido: string } | null }>(
        `/cheques/${cheque.id}/${endpoint}`,
        {},
      );
      let msg = `Cheque ${cheque.numero}: ${verbo}.`;
      if (r?.reabierto) msg += ` Se reabrió la cuenta corriente por $${fmt.format(Number(r.reabierto.importe_revertido))}.`;
      setMensaje(msg);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `No se pudo ${verbo}`);
    } finally {
      setOcupado(false);
    }
  }

  async function rechazar(cheque: Cheque) {
    const detalle = await pedirTexto(`Rechazar cheque ${cheque.numero} — motivo (opcional):`, "Sin fondos");
    if (detalle === null) return;
    setOcupado(true);
    try {
      const r = await apiPost<{ reabierto?: { importe_revertido: string } | null }>(
        `/cheques/${cheque.id}/rechazar`,
        { detalle: detalle || null },
      );
      let msg = `Cheque ${cheque.numero} rechazado.`;
      if (r?.reabierto)
        msg += ` Se reabrió la cuenta corriente por $${fmt.format(Number(r.reabierto.importe_revertido))}.`;
      setMensaje(msg);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo rechazar");
    } finally {
      setOcupado(false);
    }
  }

  function acciones(c: Cheque) {
    const btns: { label: string; fn: () => void }[] = [];
    if (c.estado === "en_cartera") {
      btns.push({ label: "Depositar", fn: () => abrirAccion(c, "depositar") });
      btns.push({ label: "Endosar", fn: () => abrirAccion(c, "endosar") });
      btns.push({ label: "Rechazar", fn: () => void rechazar(c) });
      btns.push({ label: "Anular", fn: () => void accionSimple(c, "anulado", "anular", `¿Anular cheque ${c.numero}?`) });
    }
    if (c.estado === "depositado") {
      btns.push({ label: "Acreditar", fn: () => void accionSimple(c, "acreditado", "acreditar", `¿Acreditar cheque ${c.numero}?`) });
      btns.push({ label: "Rechazar", fn: () => void rechazar(c) });
    }
    if (c.estado === "emitido") {
      btns.push({ label: "Debitar", fn: () => void accionSimple(c, "debitado", "debitar", `¿Debitar cheque propio ${c.numero}?`) });
    }
    return btns;
  }

  async function abrirAccion(cheque: Cheque, tipo: "depositar" | "endosar") {
    // cargar cuentas al abrir depositar (solo activas de la moneda del cheque)
    if (tipo === "depositar" && cuentas.length === 0) {
      try {
        const { data } = await apiGet<CuentaBancaria[]>("/bancos/cuentas");
        setCuentas(data);
      } catch {
        /* si falla, el modal muestra vacío */
      }
    }
    setAccion({ cheque, tipo });
  }

  return (
    <>
      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      {resumen.length > 0 && (
        <div className="kpis-grid" style={{ marginBottom: 12 }}>
          {resumen.map((r) => (
            <div className="kpi-card" key={`${r.clase}-${r.estado}`}>
              <div className="kpi-label">
                {r.clase === "propio" ? "Propio" : "Tercero"} · {ESTADO_LABEL[r.estado] ?? r.estado}
              </div>
              <div className="kpi-valor real mono">${fmt.format(Number(r.importe))}</div>
              <div className="kpi-hint">{r.cantidad} cheque{r.cantidad === 1 ? "" : "s"}</div>
            </div>
          ))}
        </div>
      )}

      <div className="toolbar">
        <input
          className="input"
          placeholder="Buscar por número, banco o titular…"
          value={q}
          onChange={(ev) => setQ(ev.target.value)}
          style={{ minWidth: 240 }}
        />
        <select className="select" value={clase} onChange={(ev) => setClase(ev.target.value)}>
          <option value="">Todas las clases</option>
          <option value="tercero">Terceros</option>
          <option value="propio">Propios</option>
        </select>
        <select className="select" value={estado} onChange={(ev) => setEstado(ev.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map((e) => (
            <option key={e} value={e}>
              {ESTADO_LABEL[e]}
            </option>
          ))}
        </select>
        <div style={{ flex: 1 }} />
        <button
          className="btn btn-ghost"
          onClick={() =>
            void apiDescargar(
              `/cheques/export.csv?${new URLSearchParams({ clase, estado, q: q.trim() }).toString()}`,
              "cheques.csv",
            )
          }
        >
          Exportar CSV
        </button>
        <button className="btn btn-primary" onClick={() => setAlta(true)}>
          + Nuevo cheque
        </button>
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Clase</th>
              <th>Número</th>
              <th>Banco</th>
              <th>Titular</th>
              <th>Pago</th>
              <th className="num">Importe</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {cheques.map((c) => (
              <tr key={c.id}>
                <td className="chico">{c.clase === "propio" ? "Propio" : "Tercero"}</td>
                <td className="mono">{c.numero}</td>
                <td>{c.banco}</td>
                <td>{c.titular ?? "—"}</td>
                <td className="mono">{c.fecha_pago}</td>
                <td className="num mono">${fmt.format(Number(c.importe))}</td>
                <td>
                  <span className={CHIP_CHEQUE[c.estado] ?? "chip"}>
                    {ESTADO_LABEL[c.estado] ?? c.estado}
                  </span>
                </td>
                <td>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {acciones(c).map((b) => (
                      <button key={b.label} className="btn btn-ghost btn-chico" disabled={ocupado} onClick={b.fn}>
                        {b.label}
                      </button>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && cheques.length === 0 && <div className="vacio">Sin cheques</div>}
      </div>

      {alta && <AltaCheque onCerrar={() => setAlta(false)} onCreado={() => { setAlta(false); void cargar(); }} />}
      {accion && (
        <AccionModal
          accion={accion}
          cuentas={cuentas}
          onCerrar={() => setAccion(null)}
          onHecho={(msg) => { setAccion(null); setMensaje(msg); void cargar(); }}
        />
      )}
      {dialogos}
    </>
  );
}

// ===== Alta manual de cheque de tercero =====
function AltaCheque({ onCerrar, onCreado }: { onCerrar: () => void; onCreado: () => void }) {
  const [f, setF] = useState({
    numero: "", banco: "", titular: "", fecha_pago: hoy(), importe: "", es_echeq: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function guardar() {
    setOcupado(true);
    setError(null);
    try {
      await apiPost("/cheques", {
        numero: f.numero.trim(),
        banco: f.banco.trim(),
        titular: f.titular.trim() || null,
        fecha_pago: f.fecha_pago,
        importe: f.importe,
        es_echeq: f.es_echeq,
      });
      onCreado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el cheque");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h2>Nuevo cheque de tercero</h2>
        {error && <div className="login-error">{error}</div>}
        <div className="field">
          <label>Número</label>
          <input className="input mono" value={f.numero} onChange={(e) => setF({ ...f, numero: e.target.value })} />
        </div>
        <div className="field">
          <label>Banco</label>
          <input className="input" value={f.banco} onChange={(e) => setF({ ...f, banco: e.target.value })} />
        </div>
        <div className="field">
          <label>Titular / firmante</label>
          <input className="input" value={f.titular} onChange={(e) => setF({ ...f, titular: e.target.value })} />
        </div>
        <div className="field">
          <label>Fecha de pago</label>
          <input type="date" className="input" value={f.fecha_pago} onChange={(e) => setF({ ...f, fecha_pago: e.target.value })} />
        </div>
        <div className="field">
          <label>Importe</label>
          <input type="number" step="0.01" className="input mono" value={f.importe} onChange={(e) => setF({ ...f, importe: e.target.value })} />
        </div>
        <label className="check">
          <input type="checkbox" checked={f.es_echeq} onChange={(e) => setF({ ...f, es_echeq: e.target.checked })} />
          e-cheq
        </label>
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={onCerrar}>Cancelar</button>
          <button className="btn btn-primary" disabled={ocupado || !f.numero || !f.banco || !f.importe} onClick={() => void guardar()}>
            Crear
          </button>
        </div>
      </div>
    </div>
  );
}

// ===== Modal de depositar (elige cuenta) / endosar (elige proveedor) =====
function AccionModal({
  accion, cuentas, onCerrar, onHecho,
}: {
  accion: { cheque: Cheque; tipo: "depositar" | "endosar" };
  cuentas: CuentaBancaria[];
  onCerrar: () => void;
  onHecho: (msg: string) => void;
}) {
  const [cuentaId, setCuentaId] = useState("");
  const [provId, setProvId] = useState("");
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    if (accion.tipo === "endosar") {
      apiGet<Proveedor[]>("/proveedores?limit=200").then(({ data }) => setProveedores(data)).catch(() => {});
    }
  }, [accion.tipo]);

  async function confirmar() {
    setOcupado(true);
    setError(null);
    try {
      if (accion.tipo === "depositar") {
        await apiPost(`/cheques/${accion.cheque.id}/depositar`, { cuenta_id: cuentaId });
        onHecho(`Cheque ${accion.cheque.numero} depositado.`);
      } else {
        await apiPost(`/cheques/${accion.cheque.id}/endosar`, { proveedor_id: provId });
        onHecho(`Cheque ${accion.cheque.numero} endosado.`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar la acción");
    } finally {
      setOcupado(false);
    }
  }

  const cuentasCompat = cuentas.filter((c) => c.activa && c.moneda === accion.cheque.moneda);

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h2>
          {accion.tipo === "depositar" ? "Depositar" : "Endosar"} cheque {accion.cheque.numero}
        </h2>
        {error && <div className="login-error">{error}</div>}
        {accion.tipo === "depositar" ? (
          <div className="field">
            <label>Cuenta de depósito ({accion.cheque.moneda})</label>
            <select className="select" value={cuentaId} onChange={(e) => setCuentaId(e.target.value)}>
              <option value="">Elegí una cuenta…</option>
              {cuentasCompat.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.banco} {c.numero ? `· ${c.numero}` : ""}
                </option>
              ))}
            </select>
            {cuentasCompat.length === 0 && (
              <span className="hint-mono">No hay cuentas activas en {accion.cheque.moneda}. Creá una en la pestaña Cuentas.</span>
            )}
          </div>
        ) : (
          <div className="field">
            <label>Proveedor a endosar</label>
            <select className="select" value={provId} onChange={(e) => setProvId(e.target.value)}>
              <option value="">Elegí un proveedor…</option>
              {proveedores.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.entidad.razon_social}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={onCerrar}>Cancelar</button>
          <button
            className="btn btn-primary"
            disabled={ocupado || (accion.tipo === "depositar" ? !cuentaId : !provId)}
            onClick={() => void confirmar()}
          >
            {accion.tipo === "depositar" ? "Depositar" : "Endosar"}
          </button>
        </div>
      </div>
    </div>
  );
}
