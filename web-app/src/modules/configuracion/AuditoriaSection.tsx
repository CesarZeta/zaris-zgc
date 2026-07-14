// Configuración → Auditoría de acciones (F17, DISENO-AUDITORIA.md §6).
// Registro INMUTABLE de escrituras de configuración y eventos de seguridad:
// quién cambió precios masivamente, quién editó la matriz de permisos, quién
// tocó la config ARCA, logins fallidos. Solo lectura — no hay nada que editar.

import { Fragment, useCallback, useEffect, useState } from "react";

import Paginado from "../../components/Paginado";
import { ApiError, apiDescargar, apiGet } from "../../lib/api";

interface AuditEvento {
  id: string;
  usuario_email: string | null;
  accion: string;
  modulo: string;
  ref_id: string | null;
  ref_texto: string | null;
  detalle: Record<string, unknown> | null;
  ip: string | null;
  created_at: string;
}

interface AccionCatalogo {
  codigo: string;
  modulo: string;
  etiqueta: string;
}

const POR_PAGINA = 50;

// colores por acción — estados con colores propios, nunca naranja (brand);
// neutral por defecto, rojo para fallos de seguridad, amarillo para reversiones
const CHIP_ACCION: Record<string, string> = {
  login_fallido: "chip-anulado",
  pos_anulacion_supervisor: "chip-prueba",
  periodo_reabierto: "chip-prueba",
  rol_borrado: "chip-prueba",
  nodo_revocado: "chip-prueba",
};

function fechaHora(iso: string): string {
  const d = new Date(iso);
  return `${d.toLocaleDateString("es-AR")} ${d.toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })}`;
}

function detalleLegible(detalle: Record<string, unknown>): string {
  return JSON.stringify(detalle, null, 2);
}

export default function AuditoriaSection() {
  const [eventos, setEventos] = useState<AuditEvento[]>([]);
  const [catalogo, setCatalogo] = useState<AccionCatalogo[]>([]);
  const [etiquetas, setEtiquetas] = useState<Record<string, string>>({});
  const [accion, setAccion] = useState("");
  const [q, setQ] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(0);
  const [total, setTotal] = useState(0);
  const [abierto, setAbierto] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filtros = useCallback(() => {
    const p = new URLSearchParams();
    if (accion) p.set("accion", accion);
    if (q.trim()) p.set("q", q.trim());
    if (desde) p.set("desde", desde);
    if (hasta) p.set("hasta", hasta);
    return p;
  }, [accion, q, desde, hasta]);

  const cargar = useCallback(async () => {
    try {
      const p = filtros();
      p.set("limit", String(POR_PAGINA));
      p.set("offset", String(pagina * POR_PAGINA));
      const r = await apiGet<AuditEvento[]>(`/auditoria/eventos?${p.toString()}`);
      setEventos(r.data);
      setTotal(Number(r.headers.get("X-Total-Count") ?? r.data.length));
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cargar la auditoría");
    }
  }, [filtros, pagina]);

  useEffect(() => {
    void apiGet<{ acciones: AccionCatalogo[] }>("/auditoria/catalogo").then((r) => {
      setCatalogo(r.data.acciones);
      setEtiquetas(Object.fromEntries(r.data.acciones.map((a) => [a.codigo, a.etiqueta])));
    });
  }, []);

  // debounce del texto libre (patrón de los listados: 350 ms)
  useEffect(() => {
    const t = setTimeout(() => void cargar(), q ? 350 : 0);
    return () => clearTimeout(t);
  }, [cargar, q]);

  function exportar() {
    void apiDescargar(`/auditoria/export.csv?${filtros().toString()}`, "auditoria.csv");
  }

  return (
    <div className="config-card">
      <div className="seccion">Auditoría de acciones</div>
      <p className="config-ayuda">
        Registro inmutable de las acciones sensibles del tenant: ingresos y logins fallidos,
        cambios de usuarios/roles/permisos, configuración ARCA, cambios masivos de precios,
        anulaciones POS autorizadas y cierres de período. Los documentos (ventas, compras,
        recibos) no aparecen acá: su propia historia inmutable ya los audita.
      </p>
      {error && <div className="login-error">{error}</div>}

      <div className="toolbar" style={{ flexWrap: "wrap", gap: 8 }}>
        <select
          className="input"
          value={accion}
          onChange={(e) => {
            setAccion(e.target.value);
            setPagina(0);
          }}
        >
          <option value="">Todas las acciones</option>
          {catalogo.map((a) => (
            <option key={a.codigo} value={a.codigo}>
              {a.etiqueta}
            </option>
          ))}
        </select>
        <input
          className="input"
          placeholder="Buscar por usuario o referencia…"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPagina(0);
          }}
          style={{ minWidth: 220 }}
        />
        <input
          className="input"
          type="date"
          value={desde}
          onChange={(e) => {
            setDesde(e.target.value);
            setPagina(0);
          }}
        />
        <input
          className="input"
          type="date"
          value={hasta}
          onChange={(e) => {
            setHasta(e.target.value);
            setPagina(0);
          }}
        />
        <button className="btn btn-ghost" onClick={exportar}>
          Exportar CSV
        </button>
      </div>

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Usuario</th>
              <th>Acción</th>
              <th>Referencia</th>
              <th>IP</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {eventos.map((e) => (
              <Fragment key={e.id}>
                <tr>
                  <td className="mono">{fechaHora(e.created_at)}</td>
                  <td>{e.usuario_email ?? "—"}</td>
                  <td>
                    <span className={`chip ${CHIP_ACCION[e.accion] ?? "chip-borrador"}`}>
                      {etiquetas[e.accion] ?? e.accion}
                    </span>
                  </td>
                  <td>{e.ref_texto ?? "—"}</td>
                  <td className="mono">{e.ip ?? "—"}</td>
                  <td>
                    {e.detalle && (
                      <button
                        className="mini-btn"
                        onClick={() => setAbierto(abierto === e.id ? null : e.id)}
                      >
                        {abierto === e.id ? "Ocultar" : "Detalle"}
                      </button>
                    )}
                  </td>
                </tr>
                {abierto === e.id && e.detalle && (
                  <tr>
                    <td colSpan={6}>
                      <pre
                        className="mono"
                        style={{ margin: 0, fontSize: "var(--size-caption)", whiteSpace: "pre-wrap" }}
                      >
                        {detalleLegible(e.detalle)}
                      </pre>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {eventos.length === 0 && (
              <tr>
                <td colSpan={6}>Sin eventos con esos filtros.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <Paginado pagina={pagina} porPagina={POR_PAGINA} total={total} onPagina={setPagina} />
    </div>
  );
}
