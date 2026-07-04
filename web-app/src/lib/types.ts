export interface Usuario {
  id: string;
  tenant_id: string;
  email: string;
  nombre: string;
  nivel_acceso: number;
  sucursal_id: string | null;
}

export interface Sesion {
  access_token: string;
  user: Usuario;
}

export interface Entidad {
  id: string;
  tipo_persona: string;
  razon_social: string;
  nombre_fantasia: string | null;
  tipo_documento: string;
  nro_documento: string | null;
  condicion_iva: string;
  email: string | null;
  telefono_1: string | null;
  telefono_2: string | null;
  domicilio: string | null;
  localidad: string | null;
  provincia_id: number | null;
  codigo_postal: string | null;
  observaciones: string | null;
  activo: boolean;
}

export interface Cliente {
  id: string;
  codigo: string | null;
  lista_precios: number;
  condicion_venta_id: string | null;
  zona_id: string | null;
  descuento: string;
  limite_credito: string | null;
  bloqueado: boolean;
  observaciones: string | null;
  activo: boolean;
  entidad: Entidad;
}

// ===== Artículos y Stock (Fase 2) =====

export interface Subfamilia {
  id: string;
  familia_id: string;
  nombre: string;
  activa: boolean;
}

export interface Familia {
  id: string;
  nombre: string;
  activa: boolean;
  subfamilias: Subfamilia[];
}

export interface Marca {
  id: string;
  nombre: string;
  activa: boolean;
}

export interface Unidad {
  id: string;
  codigo: string;
  nombre: string;
}

export interface Deposito {
  id: string;
  codigo: string;
  nombre: string;
  sucursal_id: string | null;
  activo: boolean;
}

export interface Cotizacion {
  id: string;
  valor: string;
  vigente_desde: string;
}

export interface Articulo {
  id: string;
  codigo: string;
  codigo_barras: string | null;
  descripcion: string;
  familia_id: string | null;
  subfamilia_id: string | null;
  marca_id: string | null;
  unidad_id: string | null;
  controla_stock: boolean;
  costo: string;
  costo_con_iva: boolean;
  tasa_iva: string;
  utilidad_1: string;
  utilidad_2: string;
  utilidad_3: string;
  utilidad_4: string;
  precio_1: string;
  precio_2: string;
  precio_3: string;
  precio_4: string;
  en_dolares: boolean;
  impuesto_interno: string;
  pesable: boolean;
  venta_por_depto: boolean;
  es_envase_retornable: boolean;
  envase_articulo_id: string | null;
  precio_actualizado_at: string | null;
  observaciones: string | null;
  activo: boolean;
  stock_total: string | null;
}

export interface StockFila {
  articulo_id: string;
  deposito_id: string;
  variante_id: string | null;
  variante_etiqueta: string | null;
  cantidad: string;
  stock_minimo: string;
  ubicacion: string | null;
  articulo_codigo: string;
  articulo_descripcion: string;
  deposito_codigo: string;
  deposito_nombre: string;
}

// ===== Rubros y variantes (Fase 2.5) =====

export interface Empresa {
  id: string;
  razon_social: string;
  nombre_fantasia: string | null;
  rubro: string;
}

export interface Rubro {
  codigo: string;
  nombre: string;
  flags_pos_super: boolean;
  variantes_destacadas: boolean;
  en_dolares_destacado: boolean;
}

export interface AtributoValor {
  id: string;
  valor: string;
  orden: number;
}

export interface Atributo {
  id: string;
  nombre: string;
  orden: number;
  valores: AtributoValor[];
}

export interface Variante {
  id: string;
  articulo_id: string;
  valor_1_id: string;
  valor_2_id: string | null;
  valor_3_id: string | null;
  etiqueta: string;
  codigo_barras: string | null;
  sku_sufijo: string | null;
  dif_precio: string;
  activo: boolean;
  stock_total: string;
}

export interface Movimiento {
  id: string;
  articulo_id: string;
  deposito_id: string;
  variante_id: string | null;
  variante_etiqueta: string | null;
  fecha: string;
  tipo: string;
  cantidad: string;
  saldo_resultante: string;
  comprobante: string | null;
  observaciones: string | null;
  grupo_id: string | null;
}

// ===== Ventas y Facturación Electrónica (Fase 3) =====

export interface PuntoVenta {
  id: string;
  numero: number;
  descripcion: string;
  sucursal_id: string | null;
  electronico: boolean;
  activo: boolean;
}

export interface ArcaConfig {
  modo: string;
  cuit: string | null;
  razon_social: string | null;
  iibb: string | null;
  inicio_actividades: string | null;
  concepto: number;
  umbral_identificar_cf: string;
  tiene_certificado: boolean;
  tiene_clave: boolean;
  comprobantes_emitidos: number;
}

export interface CondicionVentaCatalogo {
  id: string;
  descripcion: string;
  dias: number[];
  activa: boolean;
}

export interface ComprobanteItem {
  id: string;
  orden: number;
  articulo_id: string | null;
  variante_id: string | null;
  codigo: string | null;
  descripcion: string;
  cantidad: string;
  precio_unitario: string;
  bonif_pct: string;
  tasa_iva: string;
  importe_neto: string;
  importe_iva: string;
  importe_total: string;
}

export interface ComprobanteAlicuota {
  tasa: string;
  codigo_arca: number;
  base: string;
  importe: string;
}

export interface ComprobanteVencimiento {
  nro_cuota: number;
  fecha_vto: string;
  importe: string;
}

export interface Comprobante {
  id: string;
  clase: string;
  tipo_codigo: string;
  tipo_descripcion: string;
  letra: string;
  punto_venta: number;
  numero: number | null;
  numero_formateado: string | null;
  fecha: string;
  cliente_id: string | null;
  receptor_nombre: string;
  receptor_doc_tipo: number;
  receptor_doc_nro: string | null;
  receptor_condicion_iva: string;
  contado: boolean;
  condicion_venta_desc: string | null;
  moneda: string;
  descuento_pct: string;
  neto_gravado: string;
  iva: string;
  total: string;
  saldo: string;
  estado: string;
  cae: string | null;
  cae_vencimiento: string | null;
  arca_resultado: string | null;
  arca_observaciones: string | null;
  comprobante_asociado_id: string | null;
  origen_id: string | null;
  observaciones: string | null;
  items: ComprobanteItem[];
  alicuotas: ComprobanteAlicuota[];
  vencimientos: ComprobanteVencimiento[];
}

export interface ReciboMedio {
  medio: string;
  importe: string;
  referencia: string | null;
}

export interface Recibo {
  id: string;
  numero: number;
  numero_formateado: string;
  fecha: string;
  cliente_id: string;
  receptor_nombre: string;
  total: string;
  aplicado: string;
  a_cuenta: string;
  estado: string;
  observaciones: string | null;
  medios: ReciboMedio[];
}

export interface SaldoCliente {
  cliente_id: string;
  codigo: string | null;
  nombre: string;
  saldo: string;
  vencido: string;
  limite_credito: string | null;
}

export interface MovimientoCtaCte {
  fecha: string;
  tipo: string;
  numero: string;
  debe: string;
  haber: string;
  pendiente: string;
  saldo_acumulado: string;
}

export interface ImpresionPayload {
  comprobante: Comprobante;
  emisor: {
    razon_social: string;
    nombre_fantasia: string | null;
    cuit: string | null;
    condicion_iva: string;
    domicilio: string;
    iibb: string | null;
    inicio_actividades: string | null;
  };
  receptor_condicion_iva_desc: string;
  codigo_arca: number | null;
  discrimina_iva: boolean;
  leyendas: string[];
  transparencia_fiscal: {
    titulo: string;
    iva_contenido: string;
    otros_impuestos_nacionales_indirectos: string;
  } | null;
  qr_svg: string | null;
}

export const CONDICIONES_IVA: Record<string, string> = {
  RI: "Resp. Inscripto",
  MT: "Monotributo",
  EX: "Exento",
  CF: "Cons. Final",
};

export const PROVINCIAS: { id: number; nombre: string }[] = [
  { id: 0, nombre: "CABA" },
  { id: 1, nombre: "Buenos Aires" },
  { id: 2, nombre: "Catamarca" },
  { id: 3, nombre: "Córdoba" },
  { id: 4, nombre: "Corrientes" },
  { id: 5, nombre: "Entre Ríos" },
  { id: 6, nombre: "Jujuy" },
  { id: 7, nombre: "Mendoza" },
  { id: 8, nombre: "La Rioja" },
  { id: 9, nombre: "Salta" },
  { id: 10, nombre: "San Juan" },
  { id: 11, nombre: "San Luis" },
  { id: 12, nombre: "Santa Fe" },
  { id: 13, nombre: "Santiago del Estero" },
  { id: 14, nombre: "Tucumán" },
  { id: 16, nombre: "Chaco" },
  { id: 17, nombre: "Chubut" },
  { id: 18, nombre: "Formosa" },
  { id: 19, nombre: "Misiones" },
  { id: 20, nombre: "Neuquén" },
  { id: 21, nombre: "La Pampa" },
  { id: 22, nombre: "Río Negro" },
  { id: 23, nombre: "Santa Cruz" },
  { id: 24, nombre: "Tierra del Fuego" },
];
