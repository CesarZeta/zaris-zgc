// Módulo Logística (F12-bis): entregas de facturas/remitos con transportistas
// (rol BUE), hojas de ruta imprimibles y rendición del reparto. El estado de
// entrega NO toca la facturación ni la cta. cte. — solo registra y ordena el
// reparto. RBAC `logistica`. Diseño en docs/DISENO-LOGISTICA-Y-DOMICILIOS.md §2.

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { Transportista } from "../../lib/types";
import EntregasTab from "./EntregasTab";
import HojasTab from "./HojasTab";
import RendicionTab from "./RendicionTab";
import TransportistaForm from "./TransportistaForm";

export default function LogisticaPage() {
  const [tab, setTab] = useState<"pendientes" | "hojas" | "rendicion" | "transportistas">(
    "pendientes",
  );
  const [transportistas, setTransportistas] = useState<Transportista[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formAbierto, setFormAbierto] = useState(false);
  const [editando, setEditando] = useState<Transportista | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const { data } = await apiGet<Transportista[]>(
        "/logistica/transportistas?limit=200&incluir_inactivos=true",
      );
      setTransportistas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar transportistas");
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

  const activos = transportistas.filter((t) => t.activo);

  return (
    <>
      <h1 className="page-title">Logística</h1>
      <div className="tabs">
        {(
          [
            ["pendientes", "Entregas"],
            ["hojas", "Hojas de ruta"],
            ["rendicion", "Rendición"],
            ["transportistas", "Transportistas"],
          ] as const
        ).map(([k, label]) => (
          <button key={k} className={`tab${tab === k ? " activa" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {error && <div className="login-error">{error}</div>}

      {tab === "pendientes" && <EntregasTab transportistas={activos} />}
      {tab === "hojas" && <HojasTab transportistas={activos} />}
      {tab === "rendicion" && <RendicionTab />}

      {tab === "transportistas" && (
        <>
          <div className="toolbar">
            <span className="page-sub" style={{ margin: 0 }}>
              {cargando ? "Cargando…" : `${activos.length} transportistas activos`}
            </span>
            <button className="btn btn-primary" style={{ marginLeft: "auto" }}
              onClick={() => { setEditando(null); setFormAbierto(true); }}>
              + Nuevo transportista
            </button>
          </div>
          <div className="tabla-card">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Nombre</th>
                  <th>Vehículo</th>
                  <th>Dominio</th>
                  <th>Teléfono</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {transportistas.map((t) => (
                  <tr key={t.id} style={{ cursor: "pointer", opacity: t.activo ? 1 : 0.5 }}
                    onClick={() => { setEditando(t); setFormAbierto(true); }}>
                    <td className="mono">{t.codigo ?? "—"}</td>
                    <td>{t.entidad.razon_social}</td>
                    <td>{t.vehiculo ?? "—"}</td>
                    <td className="mono">{t.dominio ?? "—"}</td>
                    <td className="mono">{t.entidad.telefono_1 ?? "—"}</td>
                    <td>
                      <span className={`chip ${t.activo ? "chip-ok" : "chip-anulado"}`}>
                        {t.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                  </tr>
                ))}
                {!cargando && transportistas.length === 0 && (
                  <tr>
                    <td colSpan={6} className="texto-suave">
                      Sin transportistas. Sirve tanto el fletero externo como el reparto
                      propio (empleado con vehículo de la empresa).
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {formAbierto && <TransportistaForm transportista={editando} onCerrar={cerrarForm} />}
    </>
  );
}
