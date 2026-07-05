// Módulo Proveedores (Fase 4): rol sobre la BUE, espejo de ClientesPage.
// Incluye drill-down a los artículos que provee (costos y bonificaciones).

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { ArticuloDeProveedor, Proveedor } from "../../lib/types";
import ProveedorForm from "./ProveedorForm";

const POR_PAGINA = 50;
const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

function formatoDocumento(p: Proveedor): string {
  const e = p.entidad;
  if (!e.nro_documento) return "—";
  if (e.tipo_documento === "CUIT" || e.tipo_documento === "CUIL") {
    const n = e.nro_documento;
    return `${n.slice(0, 2)}-${n.slice(2, 10)}-${n.slice(10)}`;
  }
  return `${e.tipo_documento} ${e.nro_documento}`;
}

function ArticulosModal({ proveedor, onCerrar }: { proveedor: Proveedor; onCerrar: () => void }) {
  const [filas, setFilas] = useState<ArticuloDeProveedor[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    void apiGet<ArticuloDeProveedor[]>(`/proveedores/${proveedor.id}/articulos`)
      .then(({ data }) => setFilas(data))
      .finally(() => setCargando(false));
  }, [proveedor]);

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>Artículos de {proveedor.entidad.razon_social}</h2>
        {cargando ? (
          <p className="page-sub">Cargando…</p>
        ) : filas.length === 0 ? (
          <div className="vacio">Sin artículos asociados: se cargan al registrar compras</div>
        ) : (
          <div className="tabla-card">
            <table className="tabla tabla-mini">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Artículo</th>
                  <th>Cód. proveedor</th>
                  <th className="num">Lista (neto)</th>
                  <th className="num">Bonifs %</th>
                  <th className="num">Costo neto</th>
                  <th>Última compra</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => (
                  <tr key={f.id}>
                    <td className="mono">{f.articulo_codigo}</td>
                    <td>{f.articulo_descripcion}</td>
                    <td className="mono">{f.codigo_proveedor ?? "—"}</td>
                    <td className="num mono">{fmt.format(Number(f.costo))}</td>
                    <td className="num mono">
                      {[f.bonif_1, f.bonif_2, f.bonif_3]
                        .filter((b) => Number(b) > 0)
                        .map((b) => Number(b))
                        .join(" + ") || "—"}
                    </td>
                    <td className="num mono">{fmt.format(Number(f.costo_neto))}</td>
                    <td className="mono">{f.ultima_compra ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={onCerrar}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ProveedoresPage() {
  const [q, setQ] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(0);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [editando, setEditando] = useState<Proveedor | null>(null);
  const [verArticulos, setVerArticulos] = useState<Proveedor | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setBusqueda(q);
      setPagina(0);
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        q: busqueda,
        limit: String(POR_PAGINA),
        offset: String(pagina * POR_PAGINA),
      });
      const { data, headers } = await apiGet<Proveedor[]>(`/proveedores?${params}`);
      setProveedores(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar proveedores");
    } finally {
      setCargando(false);
    }
  }, [busqueda, pagina]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  function cerrarForm(refrescar: boolean) {
    setFormAbierto(false);
    setEditando(null);
    if (refrescar) void cargar();
  }

  const desde = pagina * POR_PAGINA + 1;
  const hasta = Math.min((pagina + 1) * POR_PAGINA, total);

  return (
    <>
      <h1 className="page-title">Proveedores</h1>
      <p className="page-sub">{cargando ? "Cargando…" : `${total} proveedores`}</p>

      <div className="toolbar">
        <input
          className="input"
          placeholder="Buscar por nombre, CUIT o teléfono…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button
          className="btn btn-primary"
          onClick={() => {
            setEditando(null);
            setFormAbierto(true);
          }}
        >
          + Nuevo proveedor
        </button>
      </div>

      {error && <div className="login-error">{error}</div>}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Código</th>
              <th>Razón social</th>
              <th>Documento</th>
              <th>IVA</th>
              <th>Rubro</th>
              <th style={{ width: 110 }}></th>
            </tr>
          </thead>
          <tbody>
            {proveedores.map((p) => (
              <tr
                key={p.id}
                onClick={() => {
                  setEditando(p);
                  setFormAbierto(true);
                }}
              >
                <td className="mono">{p.codigo ?? "—"}</td>
                <td>
                  {p.entidad.razon_social}
                  {p.entidad.nombre_fantasia && (
                    <span className="fantasia">{p.entidad.nombre_fantasia}</span>
                  )}
                </td>
                <td className="mono">{formatoDocumento(p)}</td>
                <td>
                  <span className={`chip${p.entidad.condicion_iva === "RI" ? " chip-ri" : ""}`}>
                    {p.entidad.condicion_iva}
                  </span>
                </td>
                <td>{p.rubro ?? "—"}</td>
                <td className="acciones">
                  <button
                    className="mini-btn"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      setVerArticulos(p);
                    }}
                  >
                    artículos
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && proveedores.length === 0 && (
          <div className="vacio">
            {busqueda ? `Sin resultados para «${busqueda}»` : "Todavía no hay proveedores cargados"}
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

      {formAbierto && <ProveedorForm proveedor={editando} onCerrar={cerrarForm} />}
      {verArticulos && (
        <ArticulosModal proveedor={verArticulos} onCerrar={() => setVerArticulos(null)} />
      )}
    </>
  );
}
