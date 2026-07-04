import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiGet, apiPost, apiUpload } from "../../lib/api";
import type { Articulo, Cotizacion, Familia, Marca, Unidad } from "../../lib/types";
import ArticuloForm from "./ArticuloForm";
import CambioPreciosModal from "./CambioPreciosModal";

const POR_PAGINA = 50;

const fmtPrecio = new Intl.NumberFormat("es-AR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const fmtCant = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 3 });

export function precioARS(a: Articulo, campo: "precio_1" | "precio_2" | "precio_3" | "precio_4") {
  return Number(a[campo]);
}

interface ImportResultado {
  total_filas: number;
  creados: number;
  actualizados: number;
  errores: { fila: number; error: string }[];
}

export default function ArticulosPage() {
  const [q, setQ] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [familiaId, setFamiliaId] = useState("");
  const [pagina, setPagina] = useState(0);
  const [articulos, setArticulos] = useState<Articulo[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [familias, setFamilias] = useState<Familia[]>([]);
  const [marcas, setMarcas] = useState<Marca[]>([]);
  const [unidades, setUnidades] = useState<Unidad[]>([]);
  const [cotizacion, setCotizacion] = useState<Cotizacion | null>(null);

  const [formAbierto, setFormAbierto] = useState(false);
  const [editando, setEditando] = useState<Articulo | null>(null);
  const [cambioAbierto, setCambioAbierto] = useState(false);
  const [importando, setImportando] = useState(false);
  const [importResultado, setImportResultado] = useState<ImportResultado | null>(null);
  const inputArchivo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setBusqueda(q);
      setPagina(0);
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const cargarCatalogos = useCallback(async () => {
    try {
      const [f, m, u, c] = await Promise.all([
        apiGet<Familia[]>("/catalogos-articulos/familias"),
        apiGet<Marca[]>("/catalogos-articulos/marcas"),
        apiGet<Unidad[]>("/catalogos-articulos/unidades"),
        apiGet<Cotizacion | null>("/catalogos-articulos/cotizacion"),
      ]);
      setFamilias(f.data);
      setMarcas(m.data);
      setUnidades(u.data);
      setCotizacion(c.data);
    } catch {
      /* los selects quedan vacíos; el listado principal reporta el error */
    }
  }, []);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        q: busqueda,
        limit: String(POR_PAGINA),
        offset: String(pagina * POR_PAGINA),
      });
      if (familiaId) params.set("familia_id", familiaId);
      const { data, headers } = await apiGet<Articulo[]>(`/articulos?${params}`);
      setArticulos(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar artículos");
    } finally {
      setCargando(false);
    }
  }, [busqueda, pagina, familiaId]);

  useEffect(() => {
    void cargar();
  }, [cargar]);
  useEffect(() => {
    void cargarCatalogos();
  }, [cargarCatalogos]);

  function cerrarForm(refrescar: boolean) {
    setFormAbierto(false);
    setEditando(null);
    if (refrescar) {
      void cargar();
      void cargarCatalogos();
    }
  }

  async function actualizarCotizacion() {
    const valor = window.prompt(
      "Cotización del dólar (ARS por USD):",
      cotizacion ? String(Number(cotizacion.valor)) : "",
    );
    if (!valor) return;
    try {
      const nueva = await apiPost<Cotizacion>("/catalogos-articulos/cotizacion", {
        valor: valor.replace(",", "."),
      });
      setCotizacion(nueva);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la cotización");
    }
  }

  async function importarExcel(ev: React.ChangeEvent<HTMLInputElement>) {
    const archivo = ev.target.files?.[0];
    ev.target.value = "";
    if (!archivo) return;
    setImportando(true);
    setImportResultado(null);
    setError(null);
    try {
      const res = await apiUpload<ImportResultado>("/articulos/importar-excel", "archivo", archivo);
      setImportResultado(res);
      void cargar();
      void cargarCatalogos();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo importar el archivo");
    } finally {
      setImportando(false);
    }
  }

  const desde = pagina * POR_PAGINA + 1;
  const hasta = Math.min((pagina + 1) * POR_PAGINA, total);

  return (
    <>
      <h1 className="page-title">Artículos</h1>
      <p className="page-sub">
        {cargando ? "Cargando…" : `${total} artículos`}
        <button className="cotizacion" onClick={actualizarCotizacion} title="Actualizar cotización">
          USD {cotizacion ? `$${fmtPrecio.format(Number(cotizacion.valor))}` : "sin cotización"} ✎
        </button>
      </p>

      <div className="toolbar">
        <input
          className="input"
          placeholder="Buscar por descripción, código o código de barras…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="select toolbar-select"
          value={familiaId}
          onChange={(e) => {
            setFamiliaId(e.target.value);
            setPagina(0);
          }}
        >
          <option value="">Todas las familias</option>
          {familias.map((f) => (
            <option key={f.id} value={f.id}>
              {f.nombre}
            </option>
          ))}
        </select>
        <button className="btn btn-ghost" onClick={() => setCambioAbierto(true)}>
          Cambio de precios
        </button>
        <button
          className="btn btn-ghost"
          disabled={importando}
          onClick={() => inputArchivo.current?.click()}
        >
          {importando ? "Importando…" : "Importar Excel"}
        </button>
        <input
          ref={inputArchivo}
          type="file"
          accept=".xlsx"
          style={{ display: "none" }}
          onChange={importarExcel}
        />
        <button
          className="btn btn-primary"
          onClick={() => {
            setEditando(null);
            setFormAbierto(true);
          }}
        >
          + Nuevo artículo
        </button>
      </div>

      {error && <div className="login-error">{error}</div>}
      {importResultado && (
        <div className="import-resultado">
          Importación: {importResultado.creados} creados, {importResultado.actualizados} actualizados
          {importResultado.errores.length > 0 && (
            <>
              , {importResultado.errores.length} con error
              <ul>
                {importResultado.errores.slice(0, 5).map((e) => (
                  <li key={e.fila}>
                    Fila {e.fila}: {e.error}
                  </li>
                ))}
              </ul>
            </>
          )}
          <button className="btn-cerrar" onClick={() => setImportResultado(null)}>
            ×
          </button>
        </div>
      )}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Código</th>
              <th>Descripción</th>
              <th>Familia</th>
              <th className="num">Precio 1</th>
              <th className="num">Precio 2</th>
              <th className="num">IVA %</th>
              <th className="num">Stock</th>
            </tr>
          </thead>
          <tbody>
            {articulos.map((a) => {
              const familia = familias.find((f) => f.id === a.familia_id);
              return (
                <tr
                  key={a.id}
                  onClick={() => {
                    setEditando(a);
                    setFormAbierto(true);
                  }}
                >
                  <td className="mono">
                    {a.codigo}
                    {a.codigo_barras && <span className="fantasia mono">{a.codigo_barras}</span>}
                  </td>
                  <td>
                    {a.descripcion}
                    {a.en_dolares && <span className="chip chip-usd">USD</span>}
                  </td>
                  <td>{familia?.nombre ?? "—"}</td>
                  <td className="num mono">${fmtPrecio.format(precioARS(a, "precio_1"))}</td>
                  <td className="num mono">${fmtPrecio.format(precioARS(a, "precio_2"))}</td>
                  <td className="num mono">{Number(a.tasa_iva)}</td>
                  <td className="num mono">
                    {a.controla_stock ? fmtCant.format(Number(a.stock_total ?? 0)) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!cargando && articulos.length === 0 && (
          <div className="vacio">
            {busqueda ? `Sin resultados para «${busqueda}»` : "Todavía no hay artículos cargados"}
          </div>
        )}
      </div>

      {total > POR_PAGINA && (
        <div className="paginado">
          <button className="btn btn-ghost" disabled={pagina === 0} onClick={() => setPagina(pagina - 1)}>
            ← Anterior
          </button>
          <span>
            {desde}–{hasta} de {total}
          </span>
          <button
            className="btn btn-ghost"
            disabled={hasta >= total}
            onClick={() => setPagina(pagina + 1)}
          >
            Siguiente →
          </button>
        </div>
      )}

      {formAbierto && (
        <ArticuloForm
          articulo={editando}
          familias={familias}
          marcas={marcas}
          unidades={unidades}
          onCerrar={cerrarForm}
        />
      )}
      {cambioAbierto && (
        <CambioPreciosModal
          familias={familias}
          marcas={marcas}
          onCerrar={(refrescar) => {
            setCambioAbierto(false);
            if (refrescar) void cargar();
          }}
        />
      )}
    </>
  );
}
