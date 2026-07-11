// Tipos del módulo Contabilidad (Fase 9). Co-locados al módulo.

export interface Cuenta {
  id: string;
  codigo: string;
  nombre: string;
  tipo: "activo" | "pasivo" | "pn" | "r_positivo" | "r_negativo";
  imputable: boolean;
  padre_id: string | null;
  es_sistema: boolean;
  activa: boolean;
}

export interface Mapeo {
  id: string;
  origen: string;
  clave: string | null;
  cuenta_id: string;
}

export interface OrigenCatalogo {
  origen: string;
  descripcion: string;
}

export interface AsientoLinea {
  cuenta_id: string;
  cuenta_codigo: string;
  cuenta_nombre: string;
  debe: string;
  haber: string;
  detalle: string | null;
}

export interface Asiento {
  id: string;
  numero: number | null;
  fecha: string;
  descripcion: string | null;
  origen_tipo: string;
  anulado: boolean;
  total: string;
  lineas: AsientoLinea[];
}

export interface SumasFila {
  cuenta_id: string;
  codigo: string;
  nombre: string;
  tipo: string;
  debe: string;
  haber: string;
  saldo_deudor: string;
  saldo_acreedor: string;
}

export interface SumasYSaldos {
  filas: SumasFila[];
  total_debe: string;
  total_haber: string;
  balanceado: boolean;
}

export interface MayorMovimiento {
  fecha: string;
  numero: number | null;
  descripcion: string | null;
  detalle: string | null;
  debe: string;
  haber: string;
  saldo: string;
}

export interface Periodo {
  id: string;
  periodo: string;
  cerrado_at: string;
}

export interface ActivoCategoria {
  id: string;
  nombre: string;
  vida_util_meses: number;
  es_sistema: boolean;
  activa: boolean;
}

export interface ActivoFijo {
  id: string;
  nombre: string;
  categoria_id: string;
  categoria_nombre: string;
  fecha_alta: string;
  inicio_amortizacion: string;
  valor_origen: string;
  valor_residual: string;
  vida_util_meses: number;
  compra_id: string | null;
  fecha_baja: string | null;
  baja_motivo: string | null;
  observaciones: string | null;
  anulado: boolean;
  amort_acumulada: string;
  valor_contable: string;
}

export interface BalanceFila {
  cuenta_id: string;
  codigo: string;
  nombre: string;
  nivel: number;
  imputable: boolean;
  saldo: string;
}

export interface Balance {
  hasta: string;
  secciones: { tipo: "activo" | "pasivo" | "pn"; total: string; cuentas: BalanceFila[] }[];
  activo_total: string;
  pasivo_total: string;
  resultado_ejercicio: string;
  pn_total: string;
  ecuacion_ok: boolean;
}

export interface AperturaLinea {
  cuenta_id: string | null;
  cuenta_codigo: string;
  cuenta_nombre: string;
  debe: string;
  haber: string;
  detalle: string | null;
}

export const TIPO_LABEL: Record<string, string> = {
  activo: "Activo",
  pasivo: "Pasivo",
  pn: "Patrimonio neto",
  r_positivo: "Ingreso",
  r_negativo: "Egreso",
};

export const ORIGEN_LABEL: Record<string, string> = {
  manual: "Manual",
  venta: "Venta",
  recibo: "Cobranza",
  recibo_anulacion: "Cobranza anulada",
  compra: "Compra",
  compra_anulacion: "Compra anulada",
  orden_pago: "Orden de pago",
  op_anulacion: "OP anulada",
  caja_mov: "Caja",
  caja_anulacion: "Caja (anulado)",
  banco_mov: "Banco",
  banco_anulacion: "Banco (anulado)",
  cheque_evento: "Cheque",
  retencion: "Retención",
  retencion_anulacion: "Retención anulada",
  stock_ajuste: "Ajuste inventario",
  arqueo: "Arqueo",
  arqueo_anulacion: "Arqueo (reabierto)",
  amortizacion: "Amortización",
  activo_baja: "Baja bien de uso",
  banco_transfer: "Transferencia propia",
  apertura: "Apertura",
};

export const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
export const hoy = () => new Date().toISOString().slice(0, 10);
export const primeroDelMes = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};
