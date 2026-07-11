// Hook compartido (014 — Contabilizabilidad): cuentas bancarias activas del
// tenant para señalar contra qué cuenta fue una transferencia/tarjeta/MP.
// Si el rol no tiene permiso `bancos` (403) devuelve lista vacía en silencio:
// los selects de cuenta simplemente no se muestran (cuenta_bancaria_id es
// opcional en toda la API).

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import type { CuentaBancaria } from "../modules/bancos/tipos";

export function useCuentasBancarias(): CuentaBancaria[] {
  const [cuentas, setCuentas] = useState<CuentaBancaria[]>([]);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const { data } = await apiGet<CuentaBancaria[]>("/bancos/cuentas");
        if (vivo) setCuentas(data);
      } catch {
        // sin permiso bancos (403) u otro error: sin selector de cuenta
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  return cuentas;
}

export function etiquetaCuenta(c: CuentaBancaria): string {
  const num = c.numero ? ` ${c.numero}` : c.alias ? ` (${c.alias})` : "";
  return `${c.banco}${num} · ${c.moneda}`;
}
