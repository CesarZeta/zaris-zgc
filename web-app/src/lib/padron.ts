// Consulta de padrón ARCA por CUIT (Fase 7) — autocompletar entidad BUE.

import { apiGet } from "./api";

export interface PadronResult {
  cuit: string;
  razon_social: string | null;
  tipo_persona: string;
  condicion_iva: string;
  domicilio: string | null;
  localidad: string | null;
  provincia_id: number | null;
  codigo_postal: string | null;
  fuente: "padron" | "simulado";
}

export async function consultarPadron(cuit: string): Promise<PadronResult> {
  const { data } = await apiGet<PadronResult>(`/padron/${cuit.replace(/\D/g, "")}`);
  return data;
}
