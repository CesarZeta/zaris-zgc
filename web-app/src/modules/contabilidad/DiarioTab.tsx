// Libro diario: asientos (derivados + manuales) con detalle expandible,
// regeneración por período, asiento manual, cierre/reapertura de períodos
// y export CSV. Los asientos derivados se regeneran, nunca se editan.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDescargar, apiGet, apiPost } from "../../lib/api";
import { AlertError, AlertOk } from "../../components/Alertas";
import Paginado from "../../components/Paginado";
import { useDialogos } from "../../components/dialogos";
import type { AperturaLinea, Asiento, Cuenta, Periodo } from "./tipos";
import { ORIGEN_LABEL, fmt, hoy, primeroDelMes } from "./tipos";

const POR_PAGINA = 50;

function AsientoManualModal({
  cuentas,
  onCerrar,
}: {
  cuentas: Cuenta[];
  onCerrar: (refrescar: boolean) => void;
}) {
  const imputables = cuentas.filter((c) => c.imputable && c.activa);
  const [fecha, setFecha] = useState(hoy());
  const [descripcion, setDescripcion] = useState("");
  const [lineas, setLineas] = useState(
    [0, 1].map(() => ({ cuenta_id: "", debe: "", haber: "" })),
  );
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const totalDebe = lineas.reduce((a, l) => a + Number(l.debe || 0), 0);
  const totalHaber = lineas.reduce((a, l) => a + Number(l.haber || 0), 0);

  async function guardar() {
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/contabilidad/asientos", {
        fecha,
        descripcion: descripcion.trim(),
        lineas: lineas
          .filter((l) => l.cuenta_id && (Number(l.debe) > 0 || Number(l.haber) > 0))
          .map((l) => ({
            cuenta_id: l.cuenta_id,
            debe: l.debe || "0",
            haber: l.haber || "0",
          })),
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el asiento");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Asiento manual</h2>
        <AlertError>{error}</AlertError>
        <div className="fila">
          <div className="field">
            <label>Fecha</label>
            <input type="date" className="input" value={fecha} onChange={(ev) => setFecha(ev.target.value)} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Descripción *</label>
            <input className="input" value={descripcion} onChange={(ev) => setDescripcion(ev.target.value)} />
          </div>
        </div>
        {lineas.map((l, i) => (
          <div className="fila" key={i}>
            <div className="field" style={{ flex: 2 }}>
              <select
                className="select"
                value={l.cuenta_id}
                onChange={(ev) =>
                  setLineas(lineas.map((x, j) => (j === i ? { ...x, cuenta_id: ev.target.value } : x)))
                }
              >
                <option value="">— cuenta —</option>
                {imputables.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.codigo} — {c.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <input
                className="input mono" type="number" step="0.01" min="0" placeholder="debe"
                value={l.debe}
                onChange={(ev) =>
                  setLineas(lineas.map((x, j) => (j === i ? { ...x, debe: ev.target.value, haber: "" } : x)))
                }
              />
            </div>
            <div className="field">
              <input
                className="input mono" type="number" step="0.01" min="0" placeholder="haber"
                value={l.haber}
                onChange={(ev) =>
                  setLineas(lineas.map((x, j) => (j === i ? { ...x, haber: ev.target.value, debe: "" } : x)))
                }
              />
            </div>
            {lineas.length > 2 && (
              <button type="button" className="mini-btn" onClick={() => setLineas(lineas.filter((_, j) => j !== i))}>
                quitar
              </button>
            )}
          </div>
        ))}
        <div className="toolbar">
          <button type="button" className="mini-btn"
            onClick={() => setLineas([...lineas, { cuenta_id: "", debe: "", haber: "" }])}>
            + línea
          </button>
          <span className="mono" style={{ marginLeft: "auto" }}>
            Debe $ {fmt.format(totalDebe)} · Haber $ {fmt.format(totalHaber)}
          </span>
        </div>
        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>Cancelar</button>
          <button
            className="btn btn-primary"
            disabled={guardando || !descripcion.trim() || totalDebe === 0 || totalDebe !== totalHaber}
            onClick={() => void guardar()}
          >
            {guardando ? "Guardando…" : "Crear asiento"}
          </button>
        </div>
      </div>
    </div>
  );
}

// Asiento de apertura asistido (F9-bis §6.5): trae la sugerencia calculada
// desde los datos vivos (bancos, cta. cte., cheques, stock) y deja editarla
// antes de confirmar. Solo puede haber UNA apertura viva por tenant.
function AperturaModal({
  cuentas,
  onCerrar,
}: {
  cuentas: Cuenta[];
  onCerrar: (refrescar: boolean) => void;
}) {
  const imputables = cuentas.filter((c) => c.imputable && c.activa);
  const [fecha, setFecha] = useState(hoy());
  const [lineas, setLineas] = useState<{ cuenta_id: string; debe: string; haber: string; detalle: string }[]>([]);
  const [advertencia, setAdvertencia] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await apiGet<{ lineas: AperturaLinea[]; advertencia: string }>(
          "/contabilidad/apertura/sugerencia",
        );
        setLineas(
          data.lineas
            .filter((l) => l.cuenta_id)
            .map((l) => ({
              cuenta_id: l.cuenta_id as string,
              debe: Number(l.debe) > 0 ? l.debe : "",
              haber: Number(l.haber) > 0 ? l.haber : "",
              detalle: l.detalle ?? "",
            })),
        );
        setAdvertencia(data.advertencia);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo calcular la sugerencia");
      }
    })();
  }, []);

  const totalDebe = lineas.reduce((a, l) => a + Number(l.debe || 0), 0);
  const totalHaber = lineas.reduce((a, l) => a + Number(l.haber || 0), 0);

  async function guardar() {
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/contabilidad/apertura", {
        fecha,
        descripcion: "Asiento de apertura",
        lineas: lineas
          .filter((l) => l.cuenta_id && (Number(l.debe) > 0 || Number(l.haber) > 0))
          .map((l) => ({
            cuenta_id: l.cuenta_id,
            debe: l.debe || "0",
            haber: l.haber || "0",
            detalle: l.detalle.trim() || null,
          })),
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la apertura");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Asiento de apertura</h2>
        <AlertError>{error}</AlertError>
        {advertencia && <p className="hint-mono">{advertencia}</p>}
        <div className="fila">
          <div className="field">
            <label>Fecha</label>
            <input type="date" className="input" value={fecha} onChange={(ev) => setFecha(ev.target.value)} />
          </div>
        </div>
        {lineas.map((l, i) => (
          <div className="fila" key={i}>
            <div className="field" style={{ flex: 2 }}>
              <select className="select" value={l.cuenta_id}
                onChange={(ev) => setLineas(lineas.map((x, j) => (j === i ? { ...x, cuenta_id: ev.target.value } : x)))}>
                <option value="">— cuenta —</option>
                {imputables.map((c) => (
                  <option key={c.id} value={c.id}>{c.codigo} — {c.nombre}</option>
                ))}
              </select>
            </div>
            <div className="field" style={{ flex: 1 }}>
              <input className="input" placeholder="detalle" value={l.detalle}
                onChange={(ev) => setLineas(lineas.map((x, j) => (j === i ? { ...x, detalle: ev.target.value } : x)))} />
            </div>
            <div className="field">
              <input className="input mono" type="number" step="0.01" min="0" placeholder="debe" value={l.debe}
                onChange={(ev) => setLineas(lineas.map((x, j) => (j === i ? { ...x, debe: ev.target.value, haber: "" } : x)))} />
            </div>
            <div className="field">
              <input className="input mono" type="number" step="0.01" min="0" placeholder="haber" value={l.haber}
                onChange={(ev) => setLineas(lineas.map((x, j) => (j === i ? { ...x, haber: ev.target.value, debe: "" } : x)))} />
            </div>
            <button type="button" className="mini-btn" onClick={() => setLineas(lineas.filter((_, j) => j !== i))}>
              quitar
            </button>
          </div>
        ))}
        <div className="toolbar">
          <button type="button" className="mini-btn"
            onClick={() => setLineas([...lineas, { cuenta_id: "", debe: "", haber: "", detalle: "" }])}>
            + línea
          </button>
          <span className="mono" style={{ marginLeft: "auto" }}>
            Debe $ {fmt.format(totalDebe)} · Haber $ {fmt.format(totalHaber)}
          </span>
        </div>
        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>Cancelar</button>
          <button className="btn btn-primary"
            disabled={guardando || totalDebe === 0 || Math.abs(totalDebe - totalHaber) > 0.005}
            onClick={() => void guardar()}>
            {guardando ? "Guardando…" : "Crear apertura"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function DiarioTab({ cuentas }: { cuentas: Cuenta[] }) {
  const [desde, setDesde] = useState(primeroDelMes());
  const [hasta, setHasta] = useState(hoy());
  const [filas, setFilas] = useState<Asiento[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [abierto, setAbierto] = useState<string | null>(null);
  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [modalManual, setModalManual] = useState(false);
  const [modalApertura, setModalApertura] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const { data, headers } = await apiGet<Asiento[]>(
        `/contabilidad/asientos?desde=${desde}&hasta=${hasta}&limit=${POR_PAGINA}&offset=${pagina * POR_PAGINA}`,
      );
      setFilas(data);
      setTotal(Number(headers.get("X-Total-Count") || 0));
      const { data: ps } = await apiGet<Periodo[]>("/contabilidad/periodos");
      setPeriodos(ps);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el diario");
    }
  }, [desde, hasta, pagina]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function regenerar() {
    if (
      !(await confirmar(
        `¿Regenerar los asientos derivados del ${desde} al ${hasta}? Los manuales no se tocan.`,
      ))
    )
      return;
    setOcupado(true);
    setAviso(null);
    setError(null);
    try {
      const r = await apiPost<{ asientos: number; warnings: string[] }>(
        "/contabilidad/regenerar",
        { desde, hasta },
      );
      setAviso(
        `${r.asientos} asientos generados` +
          (r.warnings.length ? ` · ${r.warnings.length} advertencias: ${r.warnings.slice(0, 3).join(" | ")}` : ""),
      );
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo regenerar");
    } finally {
      setOcupado(false);
    }
  }

  async function cerrarPeriodo() {
    const periodo = desde.slice(0, 7) + "-01";
    if (!(await confirmar(`¿Cerrar el período ${desde.slice(0, 7)}? No se podrá regenerar ni cargar asientos en ese mes.`))) return;
    try {
      await apiPost("/contabilidad/periodos/cerrar", { periodo });
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar el período");
    }
  }

  async function reabrirPeriodo(p: Periodo) {
    if (!(await confirmar(`¿Reabrir el período ${p.periodo.slice(0, 7)}?`))) return;
    try {
      await apiPost(`/contabilidad/periodos/${p.id}/reabrir`, {});
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo reabrir");
    }
  }

  return (
    <>
      <AlertError>{error}</AlertError>
      <AlertOk>{aviso}</AlertOk>
      <div className="toolbar">
        <input type="date" className="input" style={{ width: 160 }} value={desde}
          onChange={(ev) => { setDesde(ev.target.value); setPagina(0); }} />
        <span>→</span>
        <input type="date" className="input" style={{ width: 160 }} value={hasta}
          onChange={(ev) => { setHasta(ev.target.value); setPagina(0); }} />
        <button className="btn btn-primary" disabled={ocupado} onClick={() => void regenerar()}>
          {ocupado ? "Generando…" : "Regenerar asientos"}
        </button>
        <button className="btn" onClick={() => setModalManual(true)}>+ Asiento manual</button>
        <button className="btn" onClick={() => setModalApertura(true)}>Apertura asistida</button>
        <button className="btn" onClick={() => void apiDescargar(
          `/contabilidad/diario.csv?desde=${desde}&hasta=${hasta}`, "libro-diario.csv")}>
          Exportar CSV
        </button>
        <button className="btn" onClick={() => void cerrarPeriodo()}>Cerrar período</button>
      </div>

      {periodos.length > 0 && (
        <div className="toolbar" style={{ gap: 6 }}>
          <span className="texto-suave">Períodos cerrados:</span>
          {periodos.map((p) => (
            <button key={p.id} className="mini-btn" title="Reabrir"
              onClick={() => void reabrirPeriodo(p)}>
              {p.periodo.slice(0, 7)} ✕
            </button>
          ))}
        </div>
      )}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Nro</th>
              <th>Fecha</th>
              <th>Descripción</th>
              <th>Origen</th>
              <th className="num">Importe</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((a) => (
              <>
                <tr key={a.id} style={{ cursor: "pointer", opacity: a.anulado ? 0.5 : 1 }}
                  onClick={() => setAbierto(abierto === a.id ? null : a.id)}>
                  <td className="mono">{a.numero ?? "—"}</td>
                  <td>{a.fecha}</td>
                  <td>{a.descripcion}{a.anulado ? " (anulado)" : ""}</td>
                  <td>{ORIGEN_LABEL[a.origen_tipo] ?? a.origen_tipo}</td>
                  <td className="num mono">$ {fmt.format(Number(a.total))}</td>
                </tr>
                {abierto === a.id && (
                  <tr key={`${a.id}-det`}>
                    <td colSpan={5} style={{ padding: 0 }}>
                      <table className="tabla tabla-mini" style={{ margin: 0 }}>
                        <tbody>
                          {a.lineas.map((l, i) => (
                            <tr key={i}>
                              <td className="mono" style={{ width: 90 }}>{l.cuenta_codigo}</td>
                              <td>{l.cuenta_nombre}{l.detalle ? ` — ${l.detalle}` : ""}</td>
                              <td className="num mono" style={{ width: 130 }}>
                                {Number(l.debe) > 0 ? `$ ${fmt.format(Number(l.debe))}` : ""}
                              </td>
                              <td className="num mono" style={{ width: 130 }}>
                                {Number(l.haber) > 0 ? `$ ${fmt.format(Number(l.haber))}` : ""}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {filas.length === 0 && (
              <tr>
                <td colSpan={5} className="texto-suave">
                  Sin asientos en el rango — usá “Regenerar asientos” para derivarlos de las operaciones.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Paginado total={total} porPagina={POR_PAGINA} pagina={pagina} onPagina={setPagina} />

      {modalManual && (
        <AsientoManualModal
          cuentas={cuentas}
          onCerrar={(refrescar) => {
            setModalManual(false);
            if (refrescar) void cargar();
          }}
        />
      )}
      {modalApertura && (
        <AperturaModal
          cuentas={cuentas}
          onCerrar={(refrescar) => {
            setModalApertura(false);
            if (refrescar) void cargar();
          }}
        />
      )}
      {dialogos}
    </>
  );
}
