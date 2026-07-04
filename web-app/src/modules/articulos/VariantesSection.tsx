import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost, apiPut } from "../../lib/api";
import type { Atributo, Variante } from "../../lib/types";

const fmtCant = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 3 });

interface Props {
  articuloId: string;
}

export default function VariantesSection({ articuloId }: Props) {
  const [atributos, setAtributos] = useState<Atributo[]>([]);
  const [variantes, setVariantes] = useState<Variante[]>([]);
  const [seleccion, setSeleccion] = useState<Record<string, Set<string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [generando, setGenerando] = useState(false);

  const cargar = useCallback(async () => {
    const [a, v] = await Promise.all([
      apiGet<Atributo[]>("/catalogos-articulos/atributos"),
      apiGet<Variante[]>(`/articulos/${articuloId}/variantes`),
    ]);
    setAtributos(a.data);
    setVariantes(v.data);
  }, [articuloId]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  function toggle(atributoId: string, valorId: string) {
    setSeleccion((s) => {
      const set = new Set(s[atributoId] ?? []);
      if (set.has(valorId)) set.delete(valorId);
      else set.add(valorId);
      return { ...s, [atributoId]: set };
    });
  }

  const grupos = Object.values(seleccion).filter((s) => s.size > 0);
  const combinaciones = grupos.reduce((acc, g) => acc * g.size, grupos.length ? 1 : 0);

  async function generar() {
    setGenerando(true);
    setError(null);
    try {
      await apiPost(`/articulos/${articuloId}/variantes/generar`, {
        valores_por_atributo: grupos.map((g) => [...g]),
      });
      setSeleccion({});
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron generar las variantes");
    } finally {
      setGenerando(false);
    }
  }

  async function actualizar(v: Variante, cambios: Partial<Variante>) {
    try {
      const actualizada = await apiPut<Variante>(`/articulos/variantes/${v.id}`, cambios);
      setVariantes((vs) => vs.map((x) => (x.id === v.id ? actualizada : x)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la variante");
      await cargar(); // revertir el valor en pantalla
    }
  }

  async function crearValor(atributo: Atributo) {
    const valor = window.prompt(`Nuevo valor para ${atributo.nombre}:`);
    if (!valor?.trim()) return;
    try {
      await apiPost("/catalogos-articulos/atributos/valores", {
        atributo_id: atributo.id,
        valor,
      });
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el valor");
    }
  }

  async function crearAtributo() {
    const nombre = window.prompt("Nombre del nuevo atributo (ej: Talle, Color, Gusto):");
    if (!nombre?.trim()) return;
    try {
      await apiPost("/catalogos-articulos/atributos", { nombre });
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el atributo");
    }
  }

  return (
    <div className="variantes-seccion">
      {error && <div className="login-error">{error}</div>}

      {atributos.length === 0 ? (
        <p className="config-ayuda">
          No hay atributos definidos.{" "}
          <button type="button" className="mini-btn" onClick={crearAtributo}>
            + crear atributo
          </button>{" "}
          (o elegí un rubro en Configuración para sembrar los sugeridos)
        </p>
      ) : (
        <>
          {atributos.slice(0, 3).map((a) => (
            <div key={a.id} className="atributo-fila">
              <span className="atributo-nombre">
                {a.nombre}{" "}
                <button type="button" className="mini-btn" onClick={() => void crearValor(a)}>
                  +
                </button>
              </span>
              <div className="atributo-valores">
                {a.valores.map((val) => (
                  <label key={val.id} className={`valor-chip${seleccion[a.id]?.has(val.id) ? " sel" : ""}`}>
                    <input
                      type="checkbox"
                      checked={seleccion[a.id]?.has(val.id) ?? false}
                      onChange={() => toggle(a.id, val.id)}
                    />
                    {val.valor}
                  </label>
                ))}
              </div>
            </div>
          ))}
          <div className="variantes-acciones">
            <button type="button" className="mini-btn" onClick={crearAtributo}>
              + atributo
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={combinaciones === 0 || generando}
              onClick={() => void generar()}
            >
              {generando
                ? "Generando…"
                : `Generar ${combinaciones || ""} combinación${combinaciones === 1 ? "" : "es"}`}
            </button>
          </div>
        </>
      )}

      {variantes.length > 0 && (
        <table className="tabla tabla-mini tabla-variantes">
          <thead>
            <tr>
              <th>Variante</th>
              <th>Código de barras</th>
              <th className="num">Dif. precio $</th>
              <th className="num">Stock</th>
              <th>Activa</th>
            </tr>
          </thead>
          <tbody>
            {variantes.map((v) => (
              <tr key={v.id} className={v.activo ? "" : "variante-inactiva"}>
                <td>
                  <b>{v.etiqueta}</b>
                  {v.sku_sufijo && <span className="fantasia mono">{v.sku_sufijo}</span>}
                </td>
                <td>
                  <input
                    className="input mono input-mini"
                    defaultValue={v.codigo_barras ?? ""}
                    placeholder="EAN propio"
                    maxLength={20}
                    onBlur={(ev) => {
                      const nuevo = ev.target.value.trim() || null;
                      if (nuevo !== v.codigo_barras) void actualizar(v, { codigo_barras: nuevo });
                    }}
                  />
                </td>
                <td className="num">
                  <input
                    className="input mono input-mini num"
                    type="number"
                    step="0.01"
                    defaultValue={Number(v.dif_precio)}
                    onBlur={(ev) => {
                      if (Number(ev.target.value) !== Number(v.dif_precio))
                        void actualizar(v, { dif_precio: ev.target.value });
                    }}
                  />
                </td>
                <td className="num mono">{fmtCant.format(Number(v.stock_total))}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={v.activo}
                    onChange={(ev) => void actualizar(v, { activo: ev.target.checked })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
