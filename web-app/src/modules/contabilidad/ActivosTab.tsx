// Bienes de uso (F9-bis): cuadro con amortización acumulada y valor contable
// al corte, alta/edición/baja/anulación y categorías con vida útil sugerida.
// El alta NO postea asiento: el motor deriva las amortizaciones mensuales y la
// baja al regenerar (docs/DISENO-CONTABILIDAD.md §6.1).

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDescargar, apiGet, apiPost, apiPut } from "../../lib/api";
import { AlertError, AlertOk } from "../../components/Alertas";
import { useDialogos } from "../../components/dialogos";
import type { ActivoCategoria, ActivoFijo } from "./tipos";
import { fmt, hoy } from "./tipos";

interface FormActivo {
  id: string | null;
  nombre: string;
  categoria_id: string;
  fecha_alta: string;
  valor_origen: string;
  valor_residual: string;
  vida_util_meses: string;
  observaciones: string;
}

function ActivoModal({
  activo,
  categorias,
  onCerrar,
}: {
  activo: FormActivo;
  categorias: ActivoCategoria[];
  onCerrar: (refrescar: boolean) => void;
}) {
  const [f, setF] = useState(activo);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const esNuevo = !f.id;

  function elegirCategoria(id: string) {
    const cat = categorias.find((c) => c.id === id);
    setF({
      ...f,
      categoria_id: id,
      // sugerir la vida útil de la categoría solo si el campo no fue tocado
      vida_util_meses: esNuevo && cat ? String(cat.vida_util_meses) : f.vida_util_meses,
    });
  }

  async function guardar() {
    setError(null);
    setGuardando(true);
    const body = {
      nombre: f.nombre.trim(),
      categoria_id: f.categoria_id,
      fecha_alta: f.fecha_alta,
      valor_origen: f.valor_origen,
      valor_residual: f.valor_residual || "0",
      vida_util_meses: Number(f.vida_util_meses),
      observaciones: f.observaciones.trim() || null,
    };
    try {
      if (esNuevo) await apiPost("/contabilidad/activos", body);
      else await apiPut(`/contabilidad/activos/${f.id}`, body);
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el bien");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h2>{esNuevo ? "Nuevo bien de uso" : "Editar bien de uso"}</h2>
        <AlertError>{error}</AlertError>
        <div className="field"><label>Nombre *</label>
          <input className="input" value={f.nombre} onChange={(ev) => setF({ ...f, nombre: ev.target.value })} /></div>
        <div className="grid-2">
          <div className="field"><label>Categoría *</label>
            <select className="select" value={f.categoria_id} onChange={(ev) => elegirCategoria(ev.target.value)}>
              <option value="">— categoría —</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>{c.nombre} ({c.vida_util_meses} m)</option>
              ))}
            </select></div>
          <div className="field"><label>Fecha de alta</label>
            <input type="date" className="input" value={f.fecha_alta}
              onChange={(ev) => setF({ ...f, fecha_alta: ev.target.value })} /></div>
        </div>
        <div className="grid-2">
          <div className="field"><label>Valor de origen *</label>
            <input type="number" step="0.01" min="0" className="input mono" value={f.valor_origen}
              onChange={(ev) => setF({ ...f, valor_origen: ev.target.value })} /></div>
          <div className="field"><label>Valor residual</label>
            <input type="number" step="0.01" min="0" className="input mono" value={f.valor_residual}
              onChange={(ev) => setF({ ...f, valor_residual: ev.target.value })} /></div>
        </div>
        <div className="field"><label>Vida útil (meses) *</label>
          <input type="number" min="1" className="input mono" value={f.vida_util_meses}
            onChange={(ev) => setF({ ...f, vida_util_meses: ev.target.value })} />
          <span className="hint-mono">Amortización lineal mensual desde el mes de alta; el mes de la baja no amortiza.</span>
        </div>
        <div className="field"><label>Observaciones</label>
          <input className="input" value={f.observaciones} onChange={(ev) => setF({ ...f, observaciones: ev.target.value })} /></div>
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={() => onCerrar(false)}>Cancelar</button>
          <button className="btn btn-primary"
            disabled={guardando || !f.nombre.trim() || !f.categoria_id || Number(f.valor_origen) <= 0 || Number(f.vida_util_meses) <= 0}
            onClick={() => void guardar()}>
            {guardando ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ActivosTab() {
  const [filas, setFilas] = useState<ActivoFijo[]>([]);
  const [categorias, setCategorias] = useState<ActivoCategoria[]>([]);
  const [corte, setCorte] = useState(hoy());
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [form, setForm] = useState<FormActivo | null>(null);
  const { confirmar, pedirTexto, dialogos } = useDialogos();

  const cargar = useCallback(async () => {
    setError(null);
    try {
      const [a, c] = await Promise.all([
        apiGet<ActivoFijo[]>(`/contabilidad/activos?corte=${corte}`),
        apiGet<ActivoCategoria[]>("/contabilidad/activos/categorias"),
      ]);
      setFilas(a.data);
      setCategorias(c.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar bienes de uso");
    }
  }, [corte]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function darDeBaja(a: ActivoFijo) {
    if (!(await confirmar(`¿Dar de baja "${a.nombre}" con fecha de hoy? El mes en curso no amortiza; el asiento de baja aparece al regenerar.`))) return;
    try {
      await apiPost(`/contabilidad/activos/${a.id}/baja`, { fecha_baja: hoy() });
      setAviso(`"${a.nombre}" dado de baja — regenerá el período para derivar el asiento.`);
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo dar de baja");
    }
  }

  async function anular(a: ActivoFijo) {
    if (!(await confirmar(`¿Anular "${a.nombre}" (error de carga)? Sus amortizaciones desaparecen al regenerar.`))) return;
    try {
      await apiPost(`/contabilidad/activos/${a.id}/anular`, {});
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo anular");
    }
  }

  async function nuevaCategoria() {
    const nombre = await pedirTexto("Nombre de la categoría nueva:");
    if (!nombre?.trim()) return;
    const vida = await pedirTexto("Vida útil sugerida en meses:", "60");
    if (!vida) return;
    try {
      await apiPost("/contabilidad/activos/categorias", {
        nombre: nombre.trim(),
        vida_util_meses: Number(vida) || 60,
      });
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la categoría");
    }
  }

  const totalOrigen = filas.reduce((s, a) => s + (a.fecha_baja ? 0 : Number(a.valor_origen)), 0);
  const totalContable = filas.reduce((s, a) => s + (a.fecha_baja ? 0 : Number(a.valor_contable)), 0);

  return (
    <>
      <AlertError>{error}</AlertError>
      <AlertOk>{aviso}</AlertOk>
      <div className="toolbar">
        <label className="texto-suave">Corte:</label>
        <input type="date" className="input" style={{ width: 160 }} value={corte}
          onChange={(ev) => setCorte(ev.target.value)} />
        <button className="btn btn-primary" onClick={() => setForm({
          id: null, nombre: "", categoria_id: "", fecha_alta: hoy(),
          valor_origen: "", valor_residual: "0", vida_util_meses: "60", observaciones: "",
        })}>+ Bien de uso</button>
        <button className="btn" onClick={() => void nuevaCategoria()}>+ Categoría</button>
        <button className="btn" onClick={() => void apiDescargar(
          `/contabilidad/activos/cuadro.csv?corte=${corte}`, "bienes-de-uso.csv")}>
          Exportar CSV
        </button>
        <span className="mono" style={{ marginLeft: "auto" }}>
          Origen $ {fmt.format(totalOrigen)} · Contable $ {fmt.format(totalContable)}
        </span>
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Bien</th>
              <th>Categoría</th>
              <th>Alta</th>
              <th className="num">Vida (m)</th>
              <th className="num">Valor origen</th>
              <th className="num">Amort. acum.</th>
              <th className="num">Valor contable</th>
              <th>Estado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filas.map((a) => (
              <tr key={a.id} style={{ opacity: a.fecha_baja ? 0.6 : 1 }}>
                <td>{a.nombre}</td>
                <td>{a.categoria_nombre}</td>
                <td className="mono">{a.fecha_alta}</td>
                <td className="num mono">{a.vida_util_meses}</td>
                <td className="num mono">$ {fmt.format(Number(a.valor_origen))}</td>
                <td className="num mono">$ {fmt.format(Number(a.amort_acumulada))}</td>
                <td className="num mono">$ {fmt.format(Number(a.valor_contable))}</td>
                <td>
                  {a.fecha_baja ? (
                    <span className="chip chip-anulado" title={a.baja_motivo ?? ""}>Baja {a.fecha_baja}</span>
                  ) : (
                    <span className="chip chip-ok">En uso</span>
                  )}
                </td>
                <td style={{ whiteSpace: "nowrap" }}>
                  {!a.fecha_baja && (
                    <>
                      <button className="mini-btn" onClick={() => setForm({
                        id: a.id, nombre: a.nombre, categoria_id: a.categoria_id,
                        fecha_alta: a.fecha_alta, valor_origen: a.valor_origen,
                        valor_residual: a.valor_residual, vida_util_meses: String(a.vida_util_meses),
                        observaciones: a.observaciones ?? "",
                      })}>editar</button>{" "}
                      <button className="mini-btn" onClick={() => void darDeBaja(a)}>baja</button>{" "}
                    </>
                  )}
                  <button className="mini-btn" onClick={() => void anular(a)}>anular</button>
                </td>
              </tr>
            ))}
            {filas.length === 0 && (
              <tr>
                <td colSpan={9} className="texto-suave">
                  Sin bienes de uso cargados. El alta no postea asientos: las amortizaciones
                  se derivan al regenerar el período desde el Diario.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {form && (
        <ActivoModal
          activo={form}
          categorias={categorias}
          onCerrar={(refrescar) => {
            setForm(null);
            if (refrescar) void cargar();
          }}
        />
      )}
      {dialogos}
    </>
  );
}
