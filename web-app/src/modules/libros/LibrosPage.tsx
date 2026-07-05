// Módulo Libros (Fase 5): libros de IVA ventas y compras por período (con las
// NC en negativo), registro básico de retenciones y exportes para el contador
// (CSV es-AR y CITI RG 3685).

import { useState } from "react";
import ExportarTab from "./ExportarTab";
import LibroIvaTab from "./LibroIvaTab";
import RetencionesTab from "./RetencionesTab";

export default function LibrosPage() {
  const [tab, setTab] = useState<"ventas" | "compras" | "retenciones" | "exportar">("ventas");

  return (
    <>
      <h1 className="page-title">Libros de IVA</h1>
      <div className="tabs">
        {(
          [
            ["ventas", "IVA Ventas"],
            ["compras", "IVA Compras"],
            ["retenciones", "Retenciones"],
            ["exportar", "Exportar"],
          ] as const
        ).map(([k, label]) => (
          <button key={k} className={`tab${tab === k ? " activa" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "ventas" && <LibroIvaTab libro="ventas" />}
      {tab === "compras" && <LibroIvaTab libro="compras" />}
      {tab === "retenciones" && <RetencionesTab />}
      {tab === "exportar" && <ExportarTab />}
    </>
  );
}
