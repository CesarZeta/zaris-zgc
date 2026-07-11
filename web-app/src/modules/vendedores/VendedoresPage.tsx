// Módulo Vendedores (F11): rol sobre la BUE (espejo del VIAJANTE del legacy,
// % único + modalidad venta/cobranza) + liquidaciones de comisión como
// documento. RBAC `vendedores`. Diseño en docs/DISENO-VENDEDORES-COMISIONES.md.

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { Vendedor } from "../../lib/types";
import LiquidacionesTab from "./LiquidacionesTab";
import VendedorForm from "./VendedorForm";

export default function VendedoresPage() {
  const [tab, setTab] = useState<"vendedores" | "liquidaciones">("vendedores");
  const [vendedores, setVendedores] = useState<Vendedor[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [editando, setEditando] = useState<Vendedor | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { data } = await apiGet<Vendedor[]>("/vendedores?limit=200&incluir_inactivos=true");
      setVendedores(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar vendedores");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  function cerrarForm(refrescar: boolean) {
    setFormAbierto(false);
    setEditando(null);
    if (refrescar) void cargar();
  }

  const activos = vendedores.filter((v) => v.activo);

  return (
    <>
      <h1 className="page-title">Vendedores</h1>
      <div className="tabs">
        {(
          [
            ["vendedores", "Vendedores"],
            ["liquidaciones", "Comisiones"],
          ] as const
        ).map(([k, label]) => (
          <button key={k} className={`tab${tab === k ? " activa" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {error && <div className="login-error">{error}</div>}

      {tab === "vendedores" && (
        <>
          <div className="toolbar">
            <span className="page-sub" style={{ margin: 0 }}>
              {cargando ? "Cargando…" : `${activos.length} vendedores activos`}
            </span>
            <button className="btn btn-primary" style={{ marginLeft: "auto" }}
              onClick={() => { setEditando(null); setFormAbierto(true); }}>
              + Nuevo vendedor
            </button>
          </div>
          <div className="tabla-card">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Nombre</th>
                  <th>Teléfono</th>
                  <th className="num">Comisión %</th>
                  <th>Liquida por</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {vendedores.map((v) => (
                  <tr key={v.id} style={{ cursor: "pointer", opacity: v.activo ? 1 : 0.5 }}
                    onClick={() => { setEditando(v); setFormAbierto(true); }}>
                    <td className="mono">{v.codigo ?? "—"}</td>
                    <td>{v.entidad.razon_social}</td>
                    <td className="mono">{v.entidad.telefono_1 ?? "—"}</td>
                    <td className="num mono">{v.comision_pct}</td>
                    <td>{v.modalidad === "venta" ? "Venta" : "Cobranza"}</td>
                    <td>
                      <span className={`chip ${v.activo ? "chip-ok" : "chip-anulado"}`}>
                        {v.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                  </tr>
                ))}
                {!cargando && vendedores.length === 0 && (
                  <tr>
                    <td colSpan={6} className="texto-suave">
                      Sin vendedores cargados. El vendedor se asigna al cliente (habitual) y se
                      sella en cada venta y cobranza para liquidar comisiones.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "liquidaciones" && <LiquidacionesTab vendedores={activos} />}

      {formAbierto && <VendedorForm vendedor={editando} onCerrar={cerrarForm} />}
    </>
  );
}
