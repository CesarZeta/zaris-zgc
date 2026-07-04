import { useState } from "react";
import { ApiError, apiPost } from "../../lib/api";
import type { Familia, Marca } from "../../lib/types";

interface Props {
  familias: Familia[];
  marcas: Marca[];
  onCerrar: (refrescar: boolean) => void;
}

interface Resultado {
  afectados: number;
  dry_run: boolean;
  muestra: {
    codigo: string;
    descripcion: string;
    precio_1_antes: string;
    precio_1_despues: string;
  }[];
}

const TIPOS = [
  { valor: "porcentaje_precios", nombre: "% sobre los precios (mantiene el costo)" },
  { valor: "porcentaje_costo", nombre: "% sobre el costo (mantiene los márgenes)" },
  { valor: "fijar_margen", nombre: "Fijar margen de utilidad %" },
];

export default function CambioPreciosModal({ familias, marcas, onCerrar }: Props) {
  const [tipo, setTipo] = useState("porcentaje_precios");
  const [porcentaje, setPorcentaje] = useState("");
  const [listas, setListas] = useState<number[]>([1, 2, 3, 4]);
  const [familiaId, setFamiliaId] = useState("");
  const [marcaId, setMarcaId] = useState("");
  const [q, setQ] = useState("");
  const [previa, setPrevia] = useState<Resultado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trabajando, setTrabajando] = useState(false);
  const [aplicado, setAplicado] = useState<Resultado | null>(null);

  function toggleLista(n: number) {
    setListas((ls) => (ls.includes(n) ? ls.filter((x) => x !== n) : [...ls, n].sort()));
    setPrevia(null);
  }

  async function ejecutar(dryRun: boolean) {
    setError(null);
    setTrabajando(true);
    try {
      const res = await apiPost<Resultado>("/articulos/cambio-precios", {
        tipo,
        porcentaje: Number(porcentaje.replace(",", ".")),
        listas,
        familia_id: familiaId || null,
        marca_id: marcaId || null,
        q,
        dry_run: dryRun,
      });
      if (dryRun) setPrevia(res);
      else setAplicado(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo ejecutar el cambio");
    } finally {
      setTrabajando(false);
    }
  }

  const listo = porcentaje !== "" && listas.length > 0;

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(aplicado != null)}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h2>Cambio masivo de precios</h2>

        {error && <div className="login-error">{error}</div>}

        {aplicado ? (
          <>
            <p className="cambio-ok">
              ✔ Se actualizaron <b>{aplicado.afectados}</b> artículos.
            </p>
            <div className="drawer-acciones">
              <button className="btn btn-primary" onClick={() => onCerrar(true)}>
                Cerrar
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="field">
              <label>Operación</label>
              <select
                className="select"
                value={tipo}
                onChange={(ev) => {
                  setTipo(ev.target.value);
                  setPrevia(null);
                }}
              >
                {TIPOS.map((t) => (
                  <option key={t.valor} value={t.valor}>
                    {t.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div className="fila">
              <div className="field">
                <label>{tipo === "fijar_margen" ? "Margen %" : "Porcentaje (± %)"}</label>
                <input
                  className="input mono"
                  type="number"
                  step="0.01"
                  value={porcentaje}
                  onChange={(ev) => {
                    setPorcentaje(ev.target.value);
                    setPrevia(null);
                  }}
                  placeholder={tipo === "fijar_margen" ? "40" : "10 sube · -5 baja"}
                  autoFocus
                />
              </div>
              <div className="field">
                <label>Listas</label>
                <div className="listas-checks">
                  {[1, 2, 3, 4].map((n) => (
                    <label key={n} className="check">
                      <input
                        type="checkbox"
                        checked={listas.includes(n)}
                        onChange={() => toggleLista(n)}
                      />
                      {n}
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="seccion">Alcance (opcional)</div>
            <div className="fila">
              <div className="field">
                <label>Familia</label>
                <select
                  className="select"
                  value={familiaId}
                  onChange={(ev) => {
                    setFamiliaId(ev.target.value);
                    setPrevia(null);
                  }}
                >
                  <option value="">Todas</option>
                  {familias.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Marca</label>
                <select
                  className="select"
                  value={marcaId}
                  onChange={(ev) => {
                    setMarcaId(ev.target.value);
                    setPrevia(null);
                  }}
                >
                  <option value="">Todas</option>
                  {marcas.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.nombre}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field">
              <label>Filtro de texto</label>
              <input
                className="input"
                value={q}
                onChange={(ev) => {
                  setQ(ev.target.value);
                  setPrevia(null);
                }}
                placeholder="descripción o código (opcional)"
              />
            </div>

            {previa && (
              <div className="previa">
                <b>{previa.afectados}</b> artículos serían afectados.
                {previa.muestra.length > 0 && (
                  <table className="tabla tabla-mini">
                    <thead>
                      <tr>
                        <th>Código</th>
                        <th>Descripción</th>
                        <th className="num">P1 antes</th>
                        <th className="num">P1 después</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previa.muestra.map((m) => (
                        <tr key={m.codigo}>
                          <td className="mono">{m.codigo}</td>
                          <td>{m.descripcion}</td>
                          <td className="num mono">${Number(m.precio_1_antes).toFixed(2)}</td>
                          <td className="num mono">${Number(m.precio_1_despues).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            <div className="drawer-acciones">
              <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={!listo || trabajando}
                onClick={() => void ejecutar(true)}
              >
                Vista previa
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!listo || trabajando || previa == null}
                title={previa == null ? "Primero hacé una vista previa" : ""}
                onClick={() => void ejecutar(false)}
              >
                {trabajando ? "Aplicando…" : "Aplicar"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
