// Tipos del módulo Bancos y Cheques (Fase 8). Co-locados al módulo.

export interface Cheque {
  id: string;
  clase: "tercero" | "propio";
  numero: string;
  banco: string;
  titular: string | null;
  fecha_emision: string | null;
  fecha_pago: string;
  importe: string;
  moneda: string;
  es_echeq: boolean;
  estado: string;
  cliente_id: string | null;
  proveedor_id: string | null;
  cuenta_id: string | null;
  observaciones: string | null;
}

export interface ChequeEvento {
  fecha: string;
  estado_desde: string | null;
  estado_hasta: string;
  detalle: string | null;
}

export interface CuentaBancaria {
  id: string;
  banco: string;
  sucursal_bancaria: string | null;
  tipo: string;
  numero: string | null;
  cbu: string | null;
  alias: string | null;
  moneda: string;
  saldo_inicial: string;
  activa: boolean;
  observaciones: string | null;
  saldo_actual?: string;
}

export interface BancoMovimiento {
  id: string;
  cuenta_id: string;
  fecha: string;
  tipo: string;
  importe: string;
  signo: number;
  descripcion: string | null;
  referencia: string | null;
  cheque_id: string | null;
  conciliado: boolean;
  fecha_conciliacion: string | null;
  origen: string;
}

export interface CashflowPunto {
  fecha: string;
  entradas: string;
  salidas: string;
  saldo_proyectado: string;
  detalle: { concepto: string; referencia: string; importe: string }[];
}

export interface Cashflow {
  desde: string;
  hasta: string;
  granularidad: string;
  saldo_inicial: string;
  serie: CashflowPunto[];
}

/** Estado de cheque → clase de chip (color; nunca naranja = brand). */
export const CHIP_CHEQUE: Record<string, string> = {
  en_cartera: "chip chip-ri",
  depositado: "chip chip-prueba",
  acreditado: "chip chip-ok",
  endosado: "chip chip-variante",
  rechazado: "chip chip-anulado",
  anulado: "chip chip-anulado",
  emitido: "chip chip-ri",
  debitado: "chip chip-ok",
};

export const ESTADO_LABEL: Record<string, string> = {
  en_cartera: "En cartera",
  depositado: "Depositado",
  acreditado: "Acreditado",
  endosado: "Endosado",
  rechazado: "Rechazado",
  anulado: "Anulado",
  emitido: "Emitido",
  debitado: "Debitado",
};

export const TIPO_MOV_LABEL: Record<string, string> = {
  deposito: "Depósito",
  extraccion: "Extracción",
  transferencia_in: "Transferencia recibida",
  transferencia_out: "Transferencia enviada",
  debito: "Débito",
  credito: "Crédito",
  comision: "Comisión",
  ajuste_positivo: "Ajuste (+)",
  ajuste_negativo: "Ajuste (−)",
};

export const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
export const hoy = () => new Date().toISOString().slice(0, 10);
