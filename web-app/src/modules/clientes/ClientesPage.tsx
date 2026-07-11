import { useCallback, useEffect, useState } from "react";
import { apiDescargar, apiGet } from "../../lib/api";
import { CONDICIONES_IVA, type Cliente } from "../../lib/types";
import ClienteForm from "./ClienteForm";

const POR_PAGINA = 50;

function formatoDocumento(c: Cliente): string {
  const e = c.entidad;
  if (!e.nro_documento) return "—";
  if (e.tipo_documento === "CUIT" || e.tipo_documento === "CUIL") {
    const n = e.nro_documento;
    return `${n.slice(0, 2)}-${n.slice(2, 10)}-${n.slice(10)}`;
  }
  return `${e.tipo_documento} ${e.nro_documento}`;
}

export default function ClientesPage() {
  const [q, setQ] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(0);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [editando, setEditando] = useState<Cliente | null>(null);

  // debounce de la búsqueda
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
      const { data, headers } = await apiGet<Cliente[]>(`/clientes?${params}`);
      setClientes(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar clientes");
    } finally {
      setCargando(false);
    }
  }, [busqueda, pagina]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  function abrirNuevo() {
    setEditando(null);
    setFormAbierto(true);
  }
  function abrirEdicion(c: Cliente) {
    setEditando(c);
    setFormAbierto(true);
  }
  function cerrarForm(refrescar: boolean) {
    setFormAbierto(false);
    setEditando(null);
    if (refrescar) void cargar();
  }

  const desde = pagina * POR_PAGINA + 1;
  const hasta = Math.min((pagina + 1) * POR_PAGINA, total);

  return (
    <>
      <h1 className="page-title">Clientes</h1>
      <p className="page-sub">{cargando ? "Cargando…" : `${total} clientes`}</p>

      <div className="toolbar">
        <input
          className="input"
          placeholder="Buscar por nombre, CUIT, DNI o teléfono…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div style={{ flex: 1 }} />
        <button
          className="btn btn-ghost"
          onClick={() =>
            void apiDescargar(
              `/clientes/export.csv?${new URLSearchParams({ q: busqueda })}`,
              "clientes.csv",
            ).catch((err) =>
              setError(err instanceof Error ? err.message : "Error al exportar"),
            )
          }
        >
          Exportar CSV
        </button>
        <button className="btn btn-primary" onClick={abrirNuevo}>
          + Nuevo cliente
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
              <th>Lista</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {clientes.map((c) => (
              <tr key={c.id} onClick={() => abrirEdicion(c)}>
                <td className="mono">{c.codigo ?? "—"}</td>
                <td>
                  {c.entidad.razon_social}
                  {c.entidad.nombre_fantasia && (
                    <span className="fantasia">{c.entidad.nombre_fantasia}</span>
                  )}
                </td>
                <td className="mono">{formatoDocumento(c)}</td>
                <td>
                  <span className={`chip${c.entidad.condicion_iva === "RI" ? " chip-ri" : ""}`}>
                    {c.entidad.condicion_iva}
                  </span>
                </td>
                <td>{c.lista_precios}</td>
                <td>
                  {c.bloqueado ? (
                    <span className="estado-bloq">Bloqueado</span>
                  ) : (
                    <span className="estado-ok">Activo</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!cargando && clientes.length === 0 && (
          <div className="vacio">
            {busqueda ? `Sin resultados para «${busqueda}»` : "Todavía no hay clientes cargados"}
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

      {formAbierto && <ClienteForm cliente={editando} onCerrar={cerrarForm} />}
    </>
  );
}

export { CONDICIONES_IVA };
