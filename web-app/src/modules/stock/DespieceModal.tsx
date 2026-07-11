// Despiece / transformación de stock (F12-c) — "Ingreso de media res".
// Elegís plantilla (o armás los cortes a mano), peso y costo total; la grilla
// propone kilos por % de rendimiento (editables), muestra la merma en vivo y
// al confirmar genera la transformación (salida origen + entradas por corte,
// costeo proporcional al VALOR con coeficiente por corte).

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Articulo, Deposito, DespiecePlantilla, TransformacionResultado } from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtKg = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 3 });

function n(v: string): number {
  const x = Number(v.replace(",", "."));
  return Number.isFinite(x) ? x : 0;
}

interface CorteFila {
  articulo_id: string;
  codigo: string;
  descripcion: string;
  cantidad: string;
  coef_valor: string;
}

function BuscadorArt({
  onElegir,
  placeholder,
}: {
  onElegir: (a: Articulo) => void;
  placeholder: string;
}) {
  const [q, setQ] = useState("");
  const [opciones, setOpciones] = useState<Articulo[]>([]);

  useEffect(() => {
    if (q.trim().length < 2) {
      setOpciones([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await apiGet<Articulo[]>(`/articulos?q=${encodeURIComponent(q)}&limit=8`);
        setOpciones(data);
      } catch {
        setOpciones([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="buscador">
      <input
        className="input"
        placeholder={placeholder}
        value={q}
        onChange={(ev) => setQ(ev.target.value)}
      />
      {opciones.length > 0 && (
        <div className="buscador-opciones">
          {opciones.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => {
                onElegir(a);
                setQ("");
                setOpciones([]);
              }}
            >
              <span className="mono">{a.codigo}</span> {a.descripcion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DespieceModal({
  depositos,
  onCerrar,
}: {
  depositos: Deposito[];
  onCerrar: (refrescar: boolean) => void;
}) {
  const [plantillas, setPlantillas] = useState<DespiecePlantilla[]>([]);
  const [plantillaId, setPlantillaId] = useState("");
  const [origen, setOrigen] = useState<Articulo | null>(null);
  const [depositoId, setDepositoId] = useState(depositos[0]?.id ?? "");
  const [peso, setPeso] = useState("");
  const [costoTotal, setCostoTotal] = useState("");
  const [cortes, setCortes] = useState<CorteFila[]>([]);
  const [obs, setObs] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [resultado, setResultado] = useState<TransformacionResultado | null>(null);
  const [guardandoPlantilla, setGuardandoPlantilla] = useState(false);

  useEffect(() => {
    void apiGet<DespiecePlantilla[]>("/stock/despiece-plantillas").then(({ data }) =>
      setPlantillas(data),
    );
  }, []);

  function aplicarPlantilla(id: string) {
    setPlantillaId(id);
    const p = plantillas.find((x) => x.id === id);
    if (!p) return;
    setOrigen({
      id: p.articulo_origen_id,
      codigo: p.origen_codigo,
      descripcion: p.origen_descripcion,
    } as Articulo);
    const kg = n(peso);
    setCortes(
      p.cortes.map((c) => ({
        articulo_id: c.articulo_id,
        codigo: c.articulo_codigo,
        descripcion: c.articulo_descripcion,
        cantidad: kg > 0 ? ((kg * Number(c.rendimiento_pct)) / 100).toFixed(3) : "",
        coef_valor: String(Number(c.coef_valor)),
      })),
    );
  }

  function cambiarPeso(v: string) {
    setPeso(v);
    // si hay plantilla elegida, re-proponer kilos por % (siguen editables)
    const p = plantillas.find((x) => x.id === plantillaId);
    if (p && n(v) > 0) {
      setCortes((prev) =>
        prev.map((fila) => {
          const cp = p.cortes.find((c) => c.articulo_id === fila.articulo_id);
          return cp
            ? { ...fila, cantidad: ((n(v) * Number(cp.rendimiento_pct)) / 100).toFixed(3) }
            : fila;
        }),
      );
    }
  }

  const sumaCortes = cortes.reduce((a, c) => a + n(c.cantidad), 0);
  const merma = n(peso) - sumaCortes;
  const mermaPct = n(peso) > 0 ? (merma / n(peso)) * 100 : 0;
  const denominador = cortes.reduce((a, c) => a + n(c.coef_valor) * n(c.cantidad), 0);

  function costoKg(c: CorteFila): number | null {
    const total = n(costoTotal);
    if (total <= 0 || denominador <= 0) return null;
    return (total * n(c.coef_valor)) / denominador;
  }

  const valido =
    origen !== null &&
    depositoId !== "" &&
    n(peso) > 0 &&
    cortes.length > 0 &&
    cortes.every((c) => n(c.cantidad) > 0 && n(c.coef_valor) > 0) &&
    merma >= -0.0005;

  async function confirmar() {
    if (!valido || !origen || ocupado) return;
    setOcupado(true);
    setError(null);
    try {
      const r = await apiPost<TransformacionResultado>("/stock/transformacion", {
        deposito_id: depositoId,
        articulo_origen_id: origen.id,
        cantidad_origen: String(n(peso)),
        costo_total: costoTotal !== "" ? String(n(costoTotal)) : null,
        cortes: cortes.map((c) => ({
          articulo_id: c.articulo_id,
          cantidad: String(n(c.cantidad)),
          coef_valor: String(n(c.coef_valor)),
        })),
        observaciones: obs.trim() || null,
      });
      setResultado(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo registrar la transformación");
    } finally {
      setOcupado(false);
    }
  }

  async function guardarPlantilla() {
    if (!origen || cortes.length === 0 || n(peso) <= 0) return;
    setGuardandoPlantilla(true);
    setError(null);
    try {
      await apiPost("/stock/despiece-plantillas", {
        nombre: `Despiece ${origen.descripcion}`.slice(0, 60),
        articulo_origen_id: origen.id,
        cortes: cortes.map((c) => ({
          articulo_id: c.articulo_id,
          rendimiento_pct: ((n(c.cantidad) / n(peso)) * 100).toFixed(3),
          coef_valor: String(n(c.coef_valor)),
        })),
      });
      const { data } = await apiGet<DespiecePlantilla[]>("/stock/despiece-plantillas");
      setPlantillas(data);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar la plantilla");
    } finally {
      setGuardandoPlantilla(false);
    }
  }

  if (resultado) {
    return (
      <div className="drawer-backdrop">
        <div className="modal">
          <h2>Transformación registrada</h2>
          <div className="pos-arqueo">
            <div className="linea-arqueo">
              <span>Costo total distribuido</span>
              <b className="mono">$ {fmt.format(Number(resultado.costo_total))}</b>
            </div>
            <div className="linea-arqueo">
              <span>Merma</span>
              <b className="mono">{fmtKg.format(Number(resultado.merma))} kg</b>
            </div>
            {resultado.costos_corte.map((c) => {
              const fila = cortes.find((x) => x.articulo_id === c.articulo_id);
              return (
                <div key={c.articulo_id} className="linea-arqueo chico">
                  <span>· {fila?.descripcion ?? c.articulo_id}</span>
                  <span className="mono">$ {fmt.format(Number(c.costo_unitario))} /kg</span>
                </div>
              );
            })}
          </div>
          <button className="btn btn-primary btn-block" onClick={() => onCerrar(true)}>
            Listo
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <div className="modal modal-ancho" onClick={(e) => e.stopPropagation()}>
        <h2>Despiece / transformación de stock</h2>
        <p className="chico config-ayuda">
          Consume el artículo origen (media res, bolsa a fraccionar) y da de alta los cortes en
          el mismo depósito. El costo se reparte por <b>valor</b> (coeficiente por corte), no por
          peso — con coeficiente 1 en todos, se prorratea por peso.
        </p>
        {error && <div className="login-error">{error}</div>}

        <div className="fila">
          {plantillas.length > 0 && (
            <div className="field">
              <label>Plantilla</label>
              <select
                className="select"
                value={plantillaId}
                onChange={(e) => aplicarPlantilla(e.target.value)}
              >
                <option value="">— sin plantilla —</option>
                {plantillas.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="field">
            <label>Depósito</label>
            <select className="select" value={depositoId} onChange={(e) => setDepositoId(e.target.value)}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.codigo} — {d.nombre}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="field">
          <label>Artículo origen *</label>
          {origen ? (
            <div className="buscador-elegido">
              <span className="mono">{origen.codigo}</span> {origen.descripcion}
              <button type="button" className="mini-btn" onClick={() => setOrigen(null)}>
                cambiar
              </button>
            </div>
          ) : (
            <BuscadorArt onElegir={setOrigen} placeholder="Buscar el artículo origen (ej. MEDIA RES)…" />
          )}
        </div>

        <div className="fila">
          <div className="field">
            <label>Cantidad origen (kg) *</label>
            <input
              className="input num"
              type="number"
              min="0"
              step="0.001"
              value={peso}
              onChange={(e) => cambiarPeso(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Costo total ($, opcional)</label>
            <input
              className="input num"
              type="number"
              min="0"
              step="0.01"
              placeholder="vacío = costo vigente del origen"
              value={costoTotal}
              onChange={(e) => setCostoTotal(e.target.value)}
            />
          </div>
        </div>

        <div className="seccion">Cortes obtenidos</div>
        <div className="tabla-card">
          <table className="tabla">
            <thead>
              <tr>
                <th>Corte</th>
                <th className="num">Kg</th>
                <th className="num">Coef. valor</th>
                <th className="num">Costo/kg</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cortes.map((c, i) => {
                const ck = costoKg(c);
                return (
                  <tr key={c.articulo_id}>
                    <td>
                      <span className="mono chico">{c.codigo}</span> {c.descripcion}
                    </td>
                    <td className="num">
                      <input
                        className="input pos-cant"
                        type="number"
                        min="0"
                        step="0.001"
                        value={c.cantidad}
                        onChange={(e) =>
                          setCortes((prev) =>
                            prev.map((x, j) => (j === i ? { ...x, cantidad: e.target.value } : x)),
                          )
                        }
                      />
                    </td>
                    <td className="num">
                      <input
                        className="input pos-cant"
                        type="number"
                        min="0"
                        step="0.1"
                        value={c.coef_valor}
                        onChange={(e) =>
                          setCortes((prev) =>
                            prev.map((x, j) => (j === i ? { ...x, coef_valor: e.target.value } : x)),
                          )
                        }
                      />
                    </td>
                    <td className="num mono">{ck !== null ? `$ ${fmt.format(ck)}` : "—"}</td>
                    <td>
                      <button
                        className="btn-quitar"
                        onClick={() => setCortes((prev) => prev.filter((_, j) => j !== i))}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })}
              <tr>
                <td colSpan={5}>
                  <BuscadorArt
                    placeholder="+ agregar corte (buscar artículo)…"
                    onElegir={(a) => {
                      if (a.id === origen?.id || cortes.some((c) => c.articulo_id === a.id)) return;
                      setCortes((prev) => [
                        ...prev,
                        {
                          articulo_id: a.id,
                          codigo: a.codigo,
                          descripcion: a.descripcion,
                          cantidad: "",
                          coef_valor: "1",
                        },
                      ]);
                    }}
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="pos-arqueo" style={{ marginTop: "var(--space-4)" }}>
          <div className="linea-arqueo">
            <span>Σ cortes</span>
            <span className="mono">{fmtKg.format(sumaCortes)} kg</span>
          </div>
          <div className={`linea-arqueo${merma < 0 ? " neg" : ""}`}>
            <span>Merma</span>
            <b className="mono">
              {n(peso) > 0 ? `${fmtKg.format(merma)} kg (${fmt.format(mermaPct)}%)` : "—"}
            </b>
          </div>
        </div>
        {merma < -0.0005 && (
          <div className="login-error">Los cortes suman más que la cantidad de origen.</div>
        )}

        <div className="field" style={{ marginTop: "var(--space-4)" }}>
          <label>Observaciones</label>
          <input className="input" maxLength={100} value={obs} onChange={(e) => setObs(e.target.value)} />
        </div>

        <div className="pos-cobro-botones">
          <button
            className="btn btn-ghost"
            disabled={!origen || cortes.length === 0 || n(peso) <= 0 || guardandoPlantilla}
            onClick={() => void guardarPlantilla()}
            title="Guarda origen + cortes con los % actuales como plantilla"
          >
            {guardandoPlantilla ? "Guardando…" : "Guardar como plantilla"}
          </button>
          <button className="btn btn-ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </button>
          <button className="btn btn-primary" disabled={!valido || ocupado} onClick={() => void confirmar()}>
            {ocupado ? "Registrando…" : "Registrar transformación"}
          </button>
        </div>
      </div>
    </div>
  );
}
