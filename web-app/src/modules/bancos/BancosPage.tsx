// Módulo Bancos y Cheques (Fase 8): cartera de cheques con ciclo de vida,
// cuentas bancarias con movimientos y conciliación por import, y tesorería
// (cash-flow proyectado). RBAC `bancos`.

import { useState } from "react";
import CarteraTab from "./CarteraTab";
import CuentasTab from "./CuentasTab";
import TesoreriaTab from "./TesoreriaTab";

export default function BancosPage() {
  const [tab, setTab] = useState<"cartera" | "cuentas" | "tesoreria">("cartera");

  return (
    <>
      <h1 className="page-title">Bancos y Cheques</h1>
      <div className="tabs">
        {(
          [
            ["cartera", "Cartera de cheques"],
            ["cuentas", "Cuentas bancarias"],
            ["tesoreria", "Tesorería"],
          ] as const
        ).map(([k, label]) => (
          <button key={k} className={`tab${tab === k ? " activa" : ""}`} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>

      {tab === "cartera" && <CarteraTab />}
      {tab === "cuentas" && <CuentasTab />}
      {tab === "tesoreria" && <TesoreriaTab />}
    </>
  );
}
