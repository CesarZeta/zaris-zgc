// Cuentas bancarias (Fase 8): ABM (sin DELETE, se inactivan) + movimientos por
// cuenta + conciliación por import de extracto CSV (preview → confirmar).

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiGet, apiPost, apiPut, apiUpload } from "../../lib/api";
import { useDialogos } from "../../components/dialogos";
import { fmt, hoy, TIPO_MOV_LABEL, type BancoMovimiento, type CuentaBancaria } from "./tipos";

interface CuentaDet extends CuentaBancaria {
  saldo_actual: string;
}
interface PreviewFila {
  fecha: string;
  detalle: string;
  importe: string;
  tipo: string;
  match_movimiento_id: string | null;
  accion: string;
}

const TIPOS_MANUALES = [
  ["credito", "Crédito / ingreso"],
  ["transferencia_in", "Transferencia recibida"],
  ["transferencia_out", "Transferencia enviada"],
  ["extraccion", "Extracción"],
  ["comision", "Comisión"],
  ["ajuste_positivo", "Ajuste (+)"],
  ["ajuste_negativo", "Ajuste (−)"],
];

export default function CuentasTab() {
  const [cuentas, setCuentas] = useState<CuentaBancaria[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [det, setDet] = useState<CuentaDet | null>(null);
  const [movs, setMovs] = useState<BancoMovimiento[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [form, setForm] = useState<CuentaBancaria | null>(null);
  const [movForm, setMovForm] = useState(false);
  const [apareando, setApareando] = useState<BancoMovimiento | null>(null);
  const { confirmar, dialogos } = useDialogos();

  const cargarCuentas = useCallback(async () => {
    try {
      const { data } = await apiGet<CuentaBancaria[]>("/bancos/cuentas?incluir_inactivas=true");
      setCuentas(data);
      if (!sel && data.length) setSel(data[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar cuentas");
    }
  }, [sel]);

  const cargarDetalle = useCallback(async () => {
    if (!sel) return;
    try {
      const [d, m] = await Promise.all([
        apiGet<CuentaDet>(`/bancos/cuentas/${sel}`),
        apiGet<BancoMovimiento[]>(`/bancos/cuentas/${sel}/movimientos?limit=200`),
      ]);
      setDet(d.data);
      setMovs(m.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el detalle");
    }
  }, [sel]);

  useEffect(() => { void cargarCuentas(); }, [cargarCuentas]);
  useEffect(() => { void cargarDetalle(); }, [cargarDetalle]);

  async function inactivar(c: CuentaBancaria) {
    if (!(await confirmar(`¿${c.activa ? "Inactivar" : "Reactivar"} la cuenta ${c.banco}?`))) return;
    try {
      await apiPost(`/bancos/cuentas/${c.id}/inactivar`, {});
      await cargarCuentas();
      await cargarDetalle();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el estado");
    }
  }

  async function conciliar(m: BancoMovimiento) {
    try {
      await apiPost(`/bancos/movimientos/${m.id}/conciliar`, {});
      await cargarDetalle();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo conciliar");
    }
  }

  async function desaparear(m: BancoMovimiento) {
    if (!(await confirmar("¿Desaparear la transferencia? Volverá a derivar por la cuenta puente."))) return;
    try {
      await apiPost(`/bancos/movimientos/${m.id}/desaparear`, {});
      await cargarDetalle();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desaparear");
    }
  }

  return (
    <>
      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      <div className="toolbar">
        <select className="select" value={sel ?? ""} onChange={(e) => setSel(e.target.value)}>
          {cuentas.map((c) => (
            <option key={c.id} value={c.id}>
              {c.banco} {c.numero ? `· ${c.numero}` : ""} {c.activa ? "" : "(inactiva)"}
            </option>
          ))}
        </select>
        <div style={{ flex: 1 }} />
        <button className="btn btn-ghost" onClick={() => setForm({
          id: "", banco: "", sucursal_bancaria: null, tipo: "CC", numero: null, cbu: null,
          alias: null, moneda: "ARS", saldo_inicial: "0", activa: true, observaciones: null,
        })}>+ Nueva cuenta</button>
      </div>

      {det && (
        <div className="tabla-card" style={{ padding: 16, marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <div>
              <b>{det.banco}</b> · {det.tipo} {det.numero ?? ""} · {det.moneda}
              {!det.activa && <span className="chip chip-anulado" style={{ marginLeft: 8 }}>inactiva</span>}
            </div>
            <div className="kpi-valor real mono">${fmt.format(Number(det.saldo_actual))}</div>
          </div>
          <div className="drawer-acciones" style={{ justifyContent: "flex-start", marginTop: 8 }}>
            <button className="btn btn-ghost btn-chico" onClick={() => setForm(det)}>Editar</button>
            <button className="btn btn-ghost btn-chico" onClick={() => void inactivar(det)}>
              {det.activa ? "Inactivar" : "Reactivar"}
            </button>
            <button className="btn btn-ghost btn-chico" onClick={() => setMovForm(true)}>+ Movimiento</button>
            <ImportExtracto cuentaId={det.id} onImportado={(msg) => { setMensaje(msg); void cargarDetalle(); }} />
          </div>
        </div>
      )}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Tipo</th>
              <th>Descripción</th>
              <th className="num">Importe</th>
              <th>Conciliado</th>
            </tr>
          </thead>
          <tbody>
            {movs.map((m) => (
              <tr key={m.id}>
                <td className="mono">{m.fecha}</td>
                <td>
                  {TIPO_MOV_LABEL[m.tipo] ?? m.tipo}
                  {(m.tipo === "transferencia_in" || m.tipo === "transferencia_out") && (
                    m.contrapartida_id ? (
                      <>
                        {" "}<span className="chip chip-ok" title="Apareada con la cuenta propia contraparte">apareada</span>{" "}
                        <button className="mini-btn" onClick={() => void desaparear(m)}>✕</button>
                      </>
                    ) : (
                      <>
                        {" "}<button className="mini-btn" title="Aparear con la transferencia espejo de otra cuenta propia"
                          onClick={() => setApareando(m)}>aparear</button>
                      </>
                    )
                  )}
                </td>
                <td>{m.descripcion ?? "—"}{m.cheque_id && " · (cheque)"}</td>
                <td className="num mono">{m.signo < 0 ? "−" : ""}${fmt.format(Number(m.importe))}</td>
                <td>
                  <button
                    className={`chip ${m.conciliado ? "chip-ok" : "chip-borrador"}`}
                    style={{ cursor: "pointer", border: "none" }}
                    onClick={() => void conciliar(m)}
                    title="Alternar conciliado"
                  >
                    {m.conciliado ? "Conciliado ✓" : "Pendiente"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {movs.length === 0 && <div className="vacio">Sin movimientos</div>}
      </div>

      {form && (
        <CuentaForm
          cuenta={form}
          onCerrar={() => setForm(null)}
          onGuardado={() => { setForm(null); void cargarCuentas(); void cargarDetalle(); }}
        />
      )}
      {movForm && det && (
        <MovForm
          cuentaId={det.id}
          onCerrar={() => setMovForm(false)}
          onGuardado={() => { setMovForm(false); void cargarDetalle(); }}
        />
      )}
      {apareando && (
        <AparearModal
          mov={apareando}
          onCerrar={(refrescar) => {
            setApareando(null);
            if (refrescar) void cargarDetalle();
          }}
        />
      )}
      {dialogos}
    </>
  );
}

function CuentaForm({ cuenta, onCerrar, onGuardado }: { cuenta: CuentaBancaria; onCerrar: () => void; onGuardado: () => void }) {
  const [f, setF] = useState(cuenta);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const esNueva = !cuenta.id;

  async function guardar() {
    setOcupado(true);
    setError(null);
    const body = {
      banco: f.banco.trim(), sucursal_bancaria: f.sucursal_bancaria || null, tipo: f.tipo,
      numero: f.numero || null, cbu: f.cbu || null, alias: f.alias || null,
      moneda: f.moneda, saldo_inicial: f.saldo_inicial, observaciones: f.observaciones || null,
    };
    try {
      if (esNueva) await apiPost("/bancos/cuentas", body);
      else await apiPut(`/bancos/cuentas/${cuenta.id}`, body);
      onGuardado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setOcupado(false);
    }
  }

  const set = (k: keyof CuentaBancaria, v: string) => setF({ ...f, [k]: v });

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h2>{esNueva ? "Nueva cuenta bancaria" : "Editar cuenta"}</h2>
        {error && <div className="login-error">{error}</div>}
        <div className="field"><label>Banco</label>
          <input className="input" value={f.banco} onChange={(e) => set("banco", e.target.value)} /></div>
        <div className="grid-2">
          <div className="field"><label>Tipo</label>
            <select className="select" value={f.tipo} onChange={(e) => set("tipo", e.target.value)}>
              <option value="CC">Cuenta corriente</option>
              <option value="CA">Caja de ahorro</option>
            </select></div>
          <div className="field"><label>Moneda</label>
            <select className="select" value={f.moneda} onChange={(e) => set("moneda", e.target.value)}>
              <option value="ARS">ARS</option><option value="USD">USD</option>
            </select></div>
        </div>
        <div className="field"><label>Número</label>
          <input className="input mono" value={f.numero ?? ""} onChange={(e) => set("numero", e.target.value)} /></div>
        <div className="field"><label>CBU</label>
          <input className="input mono" value={f.cbu ?? ""} onChange={(e) => set("cbu", e.target.value)} /></div>
        <div className="field"><label>Alias</label>
          <input className="input" value={f.alias ?? ""} onChange={(e) => set("alias", e.target.value)} /></div>
        <div className="field"><label>Saldo inicial</label>
          <input type="number" step="0.01" className="input mono" value={f.saldo_inicial}
            onChange={(e) => set("saldo_inicial", e.target.value)} disabled={!esNueva} />
          {!esNueva && <span className="hint-mono">El saldo inicial no se edita (afectaría el histórico).</span>}
        </div>
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={onCerrar}>Cancelar</button>
          <button className="btn btn-primary" disabled={ocupado || !f.banco} onClick={() => void guardar()}>Guardar</button>
        </div>
      </div>
    </div>
  );
}

function MovForm({ cuentaId, onCerrar, onGuardado }: { cuentaId: string; onCerrar: () => void; onGuardado: () => void }) {
  const [f, setF] = useState({ tipo: "credito", importe: "", descripcion: "", fecha: hoy() });
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function guardar() {
    setOcupado(true);
    setError(null);
    try {
      await apiPost(`/bancos/cuentas/${cuentaId}/movimientos`, {
        tipo: f.tipo, importe: f.importe, descripcion: f.descripcion.trim() || null, fecha: f.fecha,
      });
      onGuardado();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h2>Nuevo movimiento</h2>
        {error && <div className="login-error">{error}</div>}
        <div className="field"><label>Tipo</label>
          <select className="select" value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value })}>
            {TIPOS_MANUALES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select></div>
        <div className="field"><label>Importe</label>
          <input type="number" step="0.01" className="input mono" value={f.importe}
            onChange={(e) => setF({ ...f, importe: e.target.value })} /></div>
        <div className="field"><label>Fecha</label>
          <input type="date" className="input" value={f.fecha} onChange={(e) => setF({ ...f, fecha: e.target.value })} /></div>
        <div className="field"><label>Descripción</label>
          <input className="input" value={f.descripcion} onChange={(e) => setF({ ...f, descripcion: e.target.value })} /></div>
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={onCerrar}>Cancelar</button>
          <button className="btn btn-primary" disabled={ocupado || !f.importe} onClick={() => void guardar()}>Guardar</button>
        </div>
      </div>
    </div>
  );
}

// Apareo de transferencias entre cuentas propias (F9-bis): elegir la
// transferencia espejo (tipo opuesto, mismo importe, otra cuenta) para que la
// contabilidad derive UN asiento banco a banco en vez de dos contra la puente.
function AparearModal({
  mov,
  onCerrar,
}: {
  mov: BancoMovimiento;
  onCerrar: (refrescar: boolean) => void;
}) {
  interface Candidato {
    id: string;
    cuenta: string;
    fecha: string;
    tipo: string;
    importe: string;
    descripcion: string | null;
  }
  const [candidatos, setCandidatos] = useState<Candidato[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await apiGet<Candidato[]>(
          `/bancos/movimientos/${mov.id}/candidatos-apareo`,
        );
        setCandidatos(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudieron buscar candidatos");
        setCandidatos([]);
      }
    })();
  }, [mov.id]);

  async function aparear(c: Candidato) {
    setOcupado(true);
    setError(null);
    try {
      await apiPost(`/bancos/movimientos/${mov.id}/aparear`, { contrapartida_id: c.id });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo aparear");
      setOcupado(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Aparear transferencia</h2>
        {error && <div className="login-error">{error}</div>}
        <p className="hint-mono">
          {TIPO_MOV_LABEL[mov.tipo]} del {mov.fecha} por ${fmt.format(Number(mov.importe))} —
          elegí su espejo en otra cuenta propia (mismo importe, sentido opuesto).
        </p>
        <div className="tabla-card" style={{ maxHeight: 320, overflow: "auto" }}>
          <table className="tabla">
            <thead>
              <tr><th>Cuenta</th><th>Fecha</th><th>Tipo</th><th className="num">Importe</th><th /></tr>
            </thead>
            <tbody>
              {(candidatos ?? []).map((c) => (
                <tr key={c.id}>
                  <td>{c.cuenta}</td>
                  <td className="mono">{c.fecha}</td>
                  <td>{TIPO_MOV_LABEL[c.tipo] ?? c.tipo}{c.descripcion ? ` · ${c.descripcion}` : ""}</td>
                  <td className="num mono">${fmt.format(Number(c.importe))}</td>
                  <td>
                    <button className="mini-btn" disabled={ocupado} onClick={() => void aparear(c)}>
                      aparear
                    </button>
                  </td>
                </tr>
              ))}
              {candidatos !== null && candidatos.length === 0 && (
                <tr>
                  <td colSpan={5} className="texto-suave">
                    Sin candidatos: no hay transferencias del sentido opuesto por el mismo
                    importe en otra cuenta. Cargá el movimiento espejo primero.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={() => onCerrar(false)}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}

// Import de extracto: sube CSV → preview → confirma
function ImportExtracto({ cuentaId, onImportado }: { cuentaId: string; onImportado: (msg: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<PreviewFila[] | null>(null);
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function onArchivo(ev: React.ChangeEvent<HTMLInputElement>) {
    const file = ev.target.files?.[0];
    if (!file) return;
    setNombre(file.name);
    setError(null);
    try {
      const r = await apiUpload<{ propuestas: PreviewFila[] }>(
        `/bancos/cuentas/${cuentaId}/extracto/preview`, "archivo", file,
      );
      setPreview(r.propuestas);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo leer el extracto");
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function confirmar() {
    if (!preview) return;
    setOcupado(true);
    try {
      const r = await apiPost<{ conciliados: number; creados: number }>(
        `/bancos/cuentas/${cuentaId}/extracto/import`,
        { nombre_archivo: nombre, items: preview },
      );
      onImportado(`Extracto importado: ${r.conciliados} conciliado(s), ${r.creados} creado(s).`);
      setPreview(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo importar");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      <input ref={inputRef} type="file" accept=".csv,text/csv" style={{ display: "none" }} onChange={onArchivo} />
      <button className="btn btn-ghost btn-chico" onClick={() => inputRef.current?.click()}>Importar extracto</button>
      {preview && (
        <div className="drawer-backdrop" onClick={() => setPreview(null)}>
          <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
            <h2>Conciliar extracto ({nombre})</h2>
            {error && <div className="login-error">{error}</div>}
            <p className="hint-mono">
              {preview.filter((p) => p.match_movimiento_id).length} concilian con movimientos existentes ·{" "}
              {preview.filter((p) => p.accion === "crear").length} se crearán nuevos.
            </p>
            <div className="tabla-card" style={{ maxHeight: 320, overflow: "auto" }}>
              <table className="tabla">
                <thead><tr><th>Fecha</th><th>Detalle</th><th className="num">Importe</th><th>Acción</th></tr></thead>
                <tbody>
                  {preview.map((p, i) => (
                    <tr key={i}>
                      <td className="mono">{p.fecha}</td>
                      <td>{p.detalle}</td>
                      <td className="num mono">${fmt.format(Number(p.importe))}</td>
                      <td>
                        <span className={`chip ${p.match_movimiento_id ? "chip-ok" : "chip-ri"}`}>
                          {p.match_movimiento_id ? "Conciliar" : "Crear"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="drawer-acciones">
              <button className="btn btn-ghost" onClick={() => setPreview(null)}>Cancelar</button>
              <button className="btn btn-primary" disabled={ocupado || preview.length === 0} onClick={() => void confirmar()}>
                Confirmar import
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
