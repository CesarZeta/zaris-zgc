// Comparativo de precios por proveedor (feature querida del legacy, ART_PROV):
// para un artículo, qué proveedor lo vende más barato (costo neto tras
// bonificaciones en cadena). Se alimenta solo al registrar compras, y también
// admite carga manual de listas.

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPut } from "../../lib/api";
import type { Articulo, Comparativo, Proveedor } from "../../lib/types";
import { BuscadorProveedor } from "./CompraForm";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

function BuscadorArticulo({ onElegir }: { onElegir: (a: Articulo) => void }) {
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
    <div className="buscador" style={{ maxWidth: 420 }}>
      <input
        className="input"
        placeholder="Buscar artículo para comparar…"
        value={q}
        onChange={(ev) => setQ(ev.target.value)}
        autoFocus
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

export default function ComparativoTab() {
  const [articulo, setArticulo] = useState<Articulo | null>(null);
  const [comparativo, setComparativo] = useState<Comparativo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agregando, setAgregando] = useState(false);
  const [nuevoProv, setNuevoProv] = useState<Proveedor | null>(null);
  const [nuevo, setNuevo] = useState({ codigo_proveedor: "", costo: "", b1: "", b2: "", b3: "" });

  const cargar = useCallback(async (articuloId: string) => {
    setError(null);
    try {
      const { data } = await apiGet<Comparativo>(`/compras/comparativo/${articuloId}`);
      setComparativo(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el comparativo");
    }
  }, []);

  useEffect(() => {
    if (articulo) void cargar(articulo.id);
    else setComparativo(null);
  }, [articulo, cargar]);

  async function guardarManual() {
    if (!articulo || !nuevoProv) return;
    setError(null);
    try {
      await apiPut("/compras/articulo-proveedor", {
        articulo_id: articulo.id,
        proveedor_id: nuevoProv.id,
        codigo_proveedor: nuevo.codigo_proveedor.trim() || null,
        costo: nuevo.costo || "0",
        bonif_1: nuevo.b1 || "0",
        bonif_2: nuevo.b2 || "0",
        bonif_3: nuevo.b3 || "0",
      });
      setAgregando(false);
      setNuevoProv(null);
      setNuevo({ codigo_proveedor: "", costo: "", b1: "", b2: "", b3: "" });
      void cargar(articulo.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    }
  }

  async function quitar(apId: string) {
    if (!articulo || !window.confirm("¿Quitar este proveedor del comparativo?")) return;
    try {
      await apiDelete(`/compras/articulo-proveedor/${apId}`);
      void cargar(articulo.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo quitar");
    }
  }

  return (
    <>
      <div className="toolbar">
        {articulo ? (
          <div className="buscador-elegido">
            <span className="mono">{articulo.codigo}</span> {articulo.descripcion}
            <button type="button" className="mini-btn" onClick={() => setArticulo(null)}>
              cambiar
            </button>
          </div>
        ) : (
          <BuscadorArticulo onElegir={setArticulo} />
        )}
        <div style={{ flex: 1 }} />
        {articulo && (
          <button className="btn btn-primary" onClick={() => setAgregando(true)}>
            + Agregar proveedor
          </button>
        )}
      </div>
      {error && <div className="login-error">{error}</div>}

      {!articulo && (
        <div className="vacio">
          Elegí un artículo para comparar los costos entre tus proveedores
        </div>
      )}

      {comparativo && (
        <>
          <p className="page-sub">
            Costo actual del artículo:{" "}
            <b className="mono">
              $ {fmt.format(Number(comparativo.articulo.costo_actual))}{" "}
              {comparativo.articulo.costo_con_iva ? "(IVA incl.)" : "(neto)"}
            </b>
          </p>
          <div className="tabla-card">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Proveedor</th>
                  <th>Cód. proveedor</th>
                  <th className="num">Lista (neto)</th>
                  <th className="num">Bonifs %</th>
                  <th className="num">Costo neto</th>
                  <th>Última compra</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {comparativo.proveedores.map((f, i) => (
                  <tr key={f.articulo_proveedor_id}>
                    <td>
                      {i === 0 && comparativo.proveedores.length > 1 && (
                        <span className="chip chip-ok">mejor</span>
                      )}{" "}
                      {f.proveedor_nombre}
                      {f.habitual && <span className="chip"> habitual</span>}
                    </td>
                    <td className="mono">{f.codigo_proveedor ?? "—"}</td>
                    <td className="num mono">{fmt.format(Number(f.costo_lista))}</td>
                    <td className="num mono">
                      {[f.bonif_1, f.bonif_2, f.bonif_3]
                        .filter((b) => Number(b) > 0)
                        .map((b) => Number(b))
                        .join(" + ") || "—"}
                    </td>
                    <td className="num mono">
                      <b>{fmt.format(Number(f.costo_neto))}</b>
                    </td>
                    <td className="mono">{f.ultima_compra ?? "—"}</td>
                    <td className="acciones">
                      <button className="mini-btn" onClick={() => void quitar(f.articulo_proveedor_id)}>
                        quitar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {comparativo.proveedores.length === 0 && (
              <div className="vacio">
                Ningún proveedor asociado todavía: registrá una compra o cargalo a mano
              </div>
            )}
          </div>
        </>
      )}

      {agregando && articulo && (
        <div className="drawer-backdrop" onClick={() => setAgregando(false)}>
          <div className="modal" onClick={(ev) => ev.stopPropagation()}>
            <h2>Proveedor para {articulo.descripcion}</h2>
            <div className="field">
              <label>Proveedor *</label>
              <BuscadorProveedor elegido={nuevoProv} onElegir={setNuevoProv} />
            </div>
            <div className="fila">
              <div className="field">
                <label>Código en el proveedor</label>
                <input
                  className="input mono"
                  value={nuevo.codigo_proveedor}
                  onChange={(ev) => setNuevo({ ...nuevo, codigo_proveedor: ev.target.value })}
                  maxLength={30}
                />
              </div>
              <div className="field">
                <label>Costo de lista (neto) *</label>
                <input
                  className="input mono"
                  type="number"
                  step="0.0001"
                  min="0"
                  value={nuevo.costo}
                  onChange={(ev) => setNuevo({ ...nuevo, costo: ev.target.value })}
                />
              </div>
            </div>
            <div className="fila-3">
              {(["b1", "b2", "b3"] as const).map((k, i) => (
                <div className="field" key={k}>
                  <label>Bonif. {i + 1} %</label>
                  <input
                    className="input mono"
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    placeholder="0"
                    value={nuevo[k]}
                    onChange={(ev) => setNuevo({ ...nuevo, [k]: ev.target.value })}
                  />
                </div>
              ))}
            </div>
            <div className="drawer-acciones">
              <button className="btn btn-ghost" onClick={() => setAgregando(false)}>
                Cancelar
              </button>
              <button
                className="btn btn-primary"
                disabled={!nuevoProv || !nuevo.costo}
                onClick={() => void guardarManual()}
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
