// Módulo Contabilidad (Fase 9): libro diario derivado + plan de cuentas +
// mapeos + sumas y saldos/mayor. RBAC `contabilidad`. La contabilidad se
// DERIVA de los documentos operativos (docs/DISENO-CONTABILIDAD.md).

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import ActivosTab from "./ActivosTab";
import BalanceTab from "./BalanceTab";
import DiarioTab from "./DiarioTab";
import MapeosTab from "./MapeosTab";
import PlanTab from "./PlanTab";
import ReportesTab from "./ReportesTab";
import type { Cuenta } from "./tipos";

export default function ContabilidadPage() {
  const [tab, setTab] = useState<"diario" | "reportes" | "balance" | "activos" | "plan" | "mapeos">("diario");
  const [cuentas, setCuentas] = useState<Cuenta[]>([]);

  const cargarCuentas = useCallback(async () => {
    try {
      // el primer GET siembra el plan base + mapeos default del tenant
      const { data } = await apiGet<Cuenta[]>("/contabilidad/plan?incluir_inactivas=true");
      setCuentas(data);
    } catch {
      // el error visible lo dan los tabs
    }
  }, []);

  useEffect(() => {
    void cargarCuentas();
  }, [cargarCuentas]);

  return (
    <>
      <h1 className="page-title">Contabilidad</h1>
      <div className="tabs">
        {(
          [
            ["diario", "Libro diario"],
            ["reportes", "Sumas y saldos"],
            ["balance", "Balance"],
            ["activos", "Bienes de uso"],
            ["plan", "Plan de cuentas"],
            ["mapeos", "Mapeos"],
          ] as const
        ).map(([k, label]) => (
          <button key={k} className={`tab${tab === k ? " activa" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "diario" && <DiarioTab cuentas={cuentas} />}
      {tab === "reportes" && <ReportesTab />}
      {tab === "balance" && <BalanceTab />}
      {tab === "activos" && <ActivosTab />}
      {tab === "plan" && <PlanTab cuentas={cuentas} onRefrescar={() => void cargarCuentas()} />}
      {tab === "mapeos" && <MapeosTab cuentas={cuentas} />}
    </>
  );
}
