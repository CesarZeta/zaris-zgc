import { useState } from "react";
import { ApiError, apiPost, apiPut } from "../../lib/api";
import type { Articulo, Familia, Marca, Unidad } from "../../lib/types";

interface Props {
  articulo: Articulo | null; // null = alta
  familias: Familia[];
  marcas: Marca[];
  unidades: Unidad[];
  onCerrar: (refrescar: boolean) => void;
}

const LISTAS = [1, 2, 3, 4] as const;

function n(valor: string): number {
  const v = Number(valor.replace(",", "."));
  return Number.isFinite(v) ? v : 0;
}

function fijar2(v: number): string {
  return (Math.round(v * 100) / 100).toFixed(2);
}

export default function ArticuloForm({ articulo: a, familias, marcas, unidades, onCerrar }: Props) {
  const [form, setForm] = useState({
    codigo: a?.codigo ?? "",
    codigo_barras: a?.codigo_barras ?? "",
    descripcion: a?.descripcion ?? "",
    familia_id: a?.familia_id ?? "",
    subfamilia_id: a?.subfamilia_id ?? "",
    marca_id: a?.marca_id ?? "",
    unidad_id: a?.unidad_id ?? "",
    controla_stock: a?.controla_stock ?? true,
    costo: a ? String(Number(a.costo)) : "0",
    costo_con_iva: a?.costo_con_iva ?? false,
    tasa_iva: a ? String(Number(a.tasa_iva)) : "21",
    en_dolares: a?.en_dolares ?? false,
    pesable: a?.pesable ?? false,
    venta_por_depto: a?.venta_por_depto ?? false,
    es_envase_retornable: a?.es_envase_retornable ?? false,
    observaciones: a?.observaciones ?? "",
    activo: a?.activo ?? true,
    utilidad_1: a ? String(Number(a.utilidad_1)) : "0",
    utilidad_2: a ? String(Number(a.utilidad_2)) : "0",
    utilidad_3: a ? String(Number(a.utilidad_3)) : "0",
    utilidad_4: a ? String(Number(a.utilidad_4)) : "0",
    precio_1: a ? String(Number(a.precio_1)) : "0",
    precio_2: a ? String(Number(a.precio_2)) : "0",
    precio_3: a ? String(Number(a.precio_3)) : "0",
    precio_4: a ? String(Number(a.precio_4)) : "0",
  });
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  function set<K extends keyof typeof form>(campo: K, valor: (typeof form)[K]) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  const familia = familias.find((f) => f.id === form.familia_id);

  function costoNeto(f: typeof form): number {
    const costo = n(f.costo);
    const tasa = n(f.tasa_iva);
    return f.costo_con_iva && tasa ? costo / (1 + tasa / 100) : costo;
  }

  // legacy: editar cualquiera de las dos patas recalcula la otra
  function cambiarUtilidad(lista: (typeof LISTAS)[number], valor: string) {
    setForm((f) => {
      const nuevo = { ...f, [`utilidad_${lista}`]: valor };
      const neto = costoNeto(nuevo);
      if (neto > 0) nuevo[`precio_${lista}`] = fijar2(neto * (1 + n(valor) / 100));
      return nuevo;
    });
  }

  function cambiarPrecio(lista: (typeof LISTAS)[number], valor: string) {
    setForm((f) => {
      const nuevo = { ...f, [`precio_${lista}`]: valor };
      const neto = costoNeto(nuevo);
      if (neto > 0) nuevo[`utilidad_${lista}`] = fijar2((n(valor) / neto - 1) * 100);
      return nuevo;
    });
  }

  function cambiarCosto(campo: "costo" | "tasa_iva" | "costo_con_iva", valor: string | boolean) {
    setForm((f) => {
      const nuevo = { ...f, [campo]: valor } as typeof form;
      const neto = costoNeto(nuevo);
      if (neto > 0) {
        for (const lista of LISTAS) {
          nuevo[`precio_${lista}`] = fijar2(neto * (1 + n(nuevo[`utilidad_${lista}`]) / 100));
        }
      }
      return nuevo;
    });
  }

  async function crearCatalogo(tipo: "familia" | "subfamilia" | "marca" | "unidad") {
    const nombre = window.prompt(`Nombre de la nueva ${tipo}:`);
    if (!nombre?.trim()) return;
    try {
      if (tipo === "familia") {
        const f = await apiPost<Familia>("/catalogos-articulos/familias", { nombre });
        familias.push({ ...f, subfamilias: f.subfamilias ?? [] });
        set("familia_id", f.id);
      } else if (tipo === "subfamilia") {
        if (!familia) return;
        const s = await apiPost<Familia["subfamilias"][number]>("/catalogos-articulos/subfamilias", {
          familia_id: familia.id,
          nombre,
        });
        familia.subfamilias.push(s);
        set("subfamilia_id", s.id);
      } else if (tipo === "marca") {
        const m = await apiPost<Marca>("/catalogos-articulos/marcas", { nombre });
        marcas.push(m);
        set("marca_id", m.id);
      } else {
        const u = await apiPost<Unidad>("/catalogos-articulos/unidades", {
          codigo: nombre.slice(0, 6),
          nombre,
        });
        unidades.push(u);
        set("unidad_id", u.id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `No se pudo crear la ${tipo}`);
    }
  }

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    setError(null);
    setGuardando(true);

    const body = {
      codigo: form.codigo.trim(),
      codigo_barras: form.codigo_barras.trim() || null,
      descripcion: form.descripcion.trim(),
      familia_id: form.familia_id || null,
      subfamilia_id: form.subfamilia_id || null,
      marca_id: form.marca_id || null,
      unidad_id: form.unidad_id || null,
      controla_stock: form.controla_stock,
      costo: n(form.costo),
      costo_con_iva: form.costo_con_iva,
      tasa_iva: n(form.tasa_iva),
      en_dolares: form.en_dolares,
      pesable: form.pesable,
      venta_por_depto: form.venta_por_depto,
      es_envase_retornable: form.es_envase_retornable,
      observaciones: form.observaciones.trim() || null,
      activo: form.activo,
      utilidad_1: n(form.utilidad_1),
      utilidad_2: n(form.utilidad_2),
      utilidad_3: n(form.utilidad_3),
      utilidad_4: n(form.utilidad_4),
      precio_1: n(form.precio_1),
      precio_2: n(form.precio_2),
      precio_3: n(form.precio_3),
      precio_4: n(form.precio_4),
    };

    try {
      if (a) {
        await apiPut(`/articulos/${a.id}`, body);
      } else {
        await apiPost("/articulos", body);
      }
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <form className="drawer" onClick={(ev) => ev.stopPropagation()} onSubmit={guardar}>
        <h2>{a ? `Editar artículo ${a.codigo}` : "Nuevo artículo"}</h2>

        {error && <div className="login-error">{error}</div>}

        <div className="seccion">Identificación</div>
        <div className="fila">
          <div className="field">
            <label>Código interno *</label>
            <input
              className="input mono"
              required
              maxLength={20}
              value={form.codigo}
              onChange={(ev) => set("codigo", ev.target.value)}
              autoFocus={!a}
            />
          </div>
          <div className="field">
            <label>Código de barras</label>
            <input
              className="input mono"
              maxLength={20}
              value={form.codigo_barras}
              onChange={(ev) => set("codigo_barras", ev.target.value)}
            />
          </div>
        </div>
        <div className="field">
          <label>Descripción *</label>
          <input
            className="input"
            required
            maxLength={80}
            value={form.descripcion}
            onChange={(ev) => set("descripcion", ev.target.value)}
          />
        </div>
        <div className="fila">
          <div className="field">
            <label>
              Familia{" "}
              <button type="button" className="mini-btn" onClick={() => crearCatalogo("familia")}>
                + nueva
              </button>
            </label>
            <select
              className="select"
              value={form.familia_id}
              onChange={(ev) => {
                set("familia_id", ev.target.value);
                set("subfamilia_id", "");
              }}
            >
              <option value="">—</option>
              {familias.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.nombre}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>
              Subfamilia{" "}
              {familia && (
                <button type="button" className="mini-btn" onClick={() => crearCatalogo("subfamilia")}>
                  + nueva
                </button>
              )}
            </label>
            <select
              className="select"
              value={form.subfamilia_id}
              onChange={(ev) => set("subfamilia_id", ev.target.value)}
              disabled={!familia}
            >
              <option value="">—</option>
              {familia?.subfamilias.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="fila">
          <div className="field">
            <label>
              Marca{" "}
              <button type="button" className="mini-btn" onClick={() => crearCatalogo("marca")}>
                + nueva
              </button>
            </label>
            <select
              className="select"
              value={form.marca_id}
              onChange={(ev) => set("marca_id", ev.target.value)}
            >
              <option value="">—</option>
              {marcas.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nombre}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>
              Unidad{" "}
              <button type="button" className="mini-btn" onClick={() => crearCatalogo("unidad")}>
                + nueva
              </button>
            </label>
            <select
              className="select"
              value={form.unidad_id}
              onChange={(ev) => set("unidad_id", ev.target.value)}
            >
              <option value="">—</option>
              {unidades.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.codigo} — {u.nombre}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="seccion">Costo y precios</div>
        <div className="fila-3">
          <div className="field">
            <label>Costo {form.en_dolares ? "USD" : "$"}</label>
            <input
              className="input mono"
              type="number"
              step="0.0001"
              min="0"
              value={form.costo}
              onChange={(ev) => cambiarCosto("costo", ev.target.value)}
            />
          </div>
          <div className="field">
            <label>Tasa IVA %</label>
            <select
              className="select"
              value={form.tasa_iva}
              onChange={(ev) => cambiarCosto("tasa_iva", ev.target.value)}
            >
              {["0", "10.5", "21", "27"].map((t) => (
                <option key={t} value={t}>
                  {t}%
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>&nbsp;</label>
            <label className="check">
              <input
                type="checkbox"
                checked={form.costo_con_iva}
                onChange={(ev) => cambiarCosto("costo_con_iva", ev.target.checked)}
              />
              Costo con IVA
            </label>
          </div>
        </div>
        <div className="precios-grid">
          <div className="precios-head">Lista</div>
          <div className="precios-head num">Utilidad %</div>
          <div className="precios-head num">Precio {form.en_dolares ? "USD" : "$"}</div>
          {LISTAS.map((lista) => (
            <div key={lista} className="precios-fila">
              <div className="precios-lista">Lista {lista}</div>
              <input
                className="input mono num"
                type="number"
                step="0.01"
                value={form[`utilidad_${lista}`]}
                onChange={(ev) => cambiarUtilidad(lista, ev.target.value)}
              />
              <input
                className="input mono num"
                type="number"
                step="0.01"
                min="0"
                value={form[`precio_${lista}`]}
                onChange={(ev) => cambiarPrecio(lista, ev.target.value)}
              />
            </div>
          ))}
        </div>
        <label className="check">
          <input
            type="checkbox"
            checked={form.en_dolares}
            onChange={(ev) => set("en_dolares", ev.target.checked)}
          />
          Precios en dólares (se convierten con la cotización vigente)
        </label>

        <div className="seccion">Stock y POS</div>
        <div className="fila">
          <label className="check">
            <input
              type="checkbox"
              checked={form.controla_stock}
              onChange={(ev) => set("controla_stock", ev.target.checked)}
            />
            Controla stock
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={form.pesable}
              onChange={(ev) => set("pesable", ev.target.checked)}
            />
            Pesable (balanza)
          </label>
        </div>
        <div className="fila">
          <label className="check">
            <input
              type="checkbox"
              checked={form.venta_por_depto}
              onChange={(ev) => set("venta_por_depto", ev.target.checked)}
            />
            Venta por departamento
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={form.es_envase_retornable}
              onChange={(ev) => set("es_envase_retornable", ev.target.checked)}
            />
            Envase retornable
          </label>
        </div>

        <div className="field" style={{ marginTop: "var(--space-6)" }}>
          <label>Observaciones</label>
          <textarea
            className="textarea"
            rows={3}
            value={form.observaciones}
            onChange={(ev) => set("observaciones", ev.target.value)}
          />
        </div>
        {a && (
          <label className="check">
            <input
              type="checkbox"
              checked={form.activo}
              onChange={(ev) => set("activo", ev.target.checked)}
            />
            Artículo activo
          </label>
        )}

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            {guardando ? "Guardando…" : a ? "Guardar cambios" : "Crear artículo"}
          </button>
        </div>
      </form>
    </div>
  );
}
