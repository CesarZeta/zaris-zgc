export interface Usuario {
  id: string;
  tenant_id: string;
  email: string;
  nombre: string;
  nivel_acceso: number;
  rol_id: string | null;
  sucursal_id: string | null;
}

/** Nivel máximo por módulo: "ver" | "editar" | "anular" (acumulativos). */
export type PermisosMap = Record<string, string>;

export interface Sesion {
  access_token: string;
  user: Usuario;
  /** Permisos por módulo (Fase 6.5). Ausente en sesiones viejas = acceso total
   *  en la UI (el backend igual controla cada endpoint). */
  permisos?: PermisosMap;
  /** ISO timestamp del inicio de sesión (lo sella el cliente al loguear). */
  login_at?: string;
}

// ===== Usuarios, roles y permisos (Fase 6.5) =====

export interface Rol {
  id: string;
  codigo: string;
  nombre: string;
  es_sistema: boolean;
  activo: boolean;
  permisos: PermisosMap;
  usuarios: number;
}

export interface UsuarioAdmin {
  id: string;
  email: string;
  nombre: string;
  nivel_acceso: number;
  rol_id: string | null;
  sucursal_id: string | null;
  activo: boolean;
}

export interface CatalogoPermisos {
  modulos: { codigo: string; nombre: string }[];
  acciones: string[];
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
  latitud: number | null;
  longitud: number | null;
  observaciones: string | null;
  activo: boolean;
}

export interface Cliente {
  id: string;
  codigo: string | null;
  lista_precios: number;
  condicion_venta_id: string | null;
  zona_id: string | null;
  vendedor_id: string | null;
  descuento: string;
  limite_credito: string | null;
  bloqueado: boolean;
  observaciones: string | null;
  activo: boolean;
  entidad: Entidad;
}

// ===== Vendedores y comisiones (F11) =====

export interface Vendedor {
  id: string;
  codigo: string | null;
  comision_pct: string;
  modalidad: "venta" | "cobranza";
  observaciones: string | null;
  activo: boolean;
  entidad: Entidad;
}

export interface ComisionPendiente {
  comprobante_id: string | null;
  recibo_id: string | null;
  fecha: string;
  descripcion: string;
  base: string;
  importe: string;
}

export interface ComisionLiquidacion {
  id: string;
  numero: number;
  numero_formateado: string;
  vendedor_id: string;
  vendedor_nombre: string;
  modalidad: string;
  desde: string;
  hasta: string;
  comision_pct: string;
  base_total: string;
  total: string;
  fecha: string;
  observaciones: string | null;
  anulada: boolean;
  items?: ComisionPendiente[];
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
  codigo_balanza: string | null;
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
  /** Plan comercial (F12-a): "suite" | "pos". Read-only — lo administra ZARIS. */
  plan: string;
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
  /** Solo en el detalle (GET por id): el listado viaja liviano, sin hijos. */
  items?: ComprobanteItem[];
  alicuotas?: ComprobanteAlicuota[];
  vencimientos?: ComprobanteVencimiento[];
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

// ===== Compras y Proveedores (Fase 4) =====

export interface Proveedor {
  id: string;
  codigo: string | null;
  condicion_compra_id: string | null;
  rubro: string | null;
  observaciones: string | null;
  activo: boolean;
  entidad: Entidad;
}

export interface CompraItem {
  id: string;
  orden: number;
  articulo_id: string | null;
  variante_id: string | null;
  codigo: string | null;
  descripcion: string;
  cantidad: string;
  costo_unitario: string;
  bonif_1: string;
  bonif_2: string;
  tasa_iva: string;
  importe_neto: string;
  importe_iva: string;
  importe_total: string;
}

export interface Compra {
  id: string;
  clase: string;
  tipo_codigo: string;
  tipo_descripcion: string;
  letra: string;
  punto_venta: number;
  numero: number;
  numero_formateado: string;
  fecha: string;
  periodo_iva: string | null;
  proveedor_id: string;
  proveedor_nombre: string;
  proveedor_cuit: string | null;
  proveedor_condicion_iva: string;
  contado: boolean;
  condicion_desc: string | null;
  actualiza_stock: boolean;
  actualiza_costos: boolean;
  neto_gravado: string;
  no_gravado: string;
  exento: string;
  iva: string;
  percepcion_iva: string;
  percepcion_iibb: string;
  impuestos_internos: string;
  otros_tributos: string;
  redondeo: string;
  total: string;
  saldo: string;
  estado: string;
  compra_asociada_id: string | null;
  observaciones: string | null;
  /** Solo en el detalle (GET por id): el listado viaja liviano, sin hijos. */
  items?: CompraItem[];
  vencimientos?: ComprobanteVencimiento[];
}

export interface OrdenPago {
  id: string;
  numero: number;
  numero_formateado: string;
  fecha: string;
  proveedor_id: string;
  proveedor_nombre: string;
  total: string;
  aplicado: string;
  a_cuenta: string;
  estado: string;
  observaciones: string | null;
  medios: ReciboMedio[];
}

export interface SaldoProveedor {
  proveedor_id: string;
  codigo: string | null;
  nombre: string;
  saldo: string;
}

export interface VencimientoPagar {
  compra_id: string;
  proveedor_id: string;
  proveedor_nombre: string;
  tipo_codigo: string;
  numero: string;
  nro_cuota: number;
  fecha_vto: string;
  importe_cuota: string;
  saldo_compra: string;
  vencida: boolean;
}

export interface ComparativoFila {
  articulo_proveedor_id: string;
  proveedor_id: string;
  proveedor_codigo: string | null;
  proveedor_nombre: string;
  codigo_proveedor: string | null;
  costo_lista: string;
  bonif_1: string;
  bonif_2: string;
  bonif_3: string;
  costo_neto: string;
  ultima_compra: string | null;
  habitual: boolean;
}

export interface Comparativo {
  articulo: {
    id: string;
    codigo: string;
    descripcion: string;
    costo_actual: string;
    costo_con_iva: boolean;
  };
  proveedores: ComparativoFila[];
}

export interface ArticuloDeProveedor {
  id: string;
  articulo_id: string;
  articulo_codigo: string;
  articulo_descripcion: string;
  codigo_proveedor: string | null;
  costo: string;
  bonif_1: string;
  bonif_2: string;
  bonif_3: string;
  costo_neto: string;
  ultima_compra: string | null;
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

// ===== Caja e IVA (Fase 5) =====

export interface ConceptoCaja {
  id: string;
  nombre: string;
  tipo: "entrada" | "salida";
  activo: boolean;
}

export interface CajaMovimiento {
  id: string;
  fecha: string;
  sucursal_id: string | null;
  concepto_id: string;
  concepto_nombre: string;
  tipo: "entrada" | "salida";
  medio: string;
  importe: string;
  descripcion: string | null;
}

export interface TotalMedio {
  medio: string;
  total: string;
  cantidad: number;
}

export interface CajaCierre {
  id: string;
  sucursal_id: string | null;
  fecha: string;
  saldo_inicial: string;
  entradas: string;
  salidas: string;
  saldo_final: string;
  efectivo_contado: string | null;
  diferencia: string | null;
  observaciones: string | null;
}

export interface Planilla {
  fecha: string;
  sucursal_id: string | null;
  saldo_inicial: string;
  ventas_contado_cantidad: number;
  ventas_contado_total: string;
  ventas_por_medio: TotalMedio[];
  cobranzas: TotalMedio[];
  pagos: TotalMedio[];
  movimientos: CajaMovimiento[];
  entradas_efectivo: string;
  salidas_efectivo: string;
  saldo_final: string;
  cierre: CajaCierre | null;
}

export interface AlicuotaLibro {
  tasa: string;
  base: string;
  importe: string;
}

export interface FilaLibro {
  id: string;
  fecha: string;
  tipo_codigo: string;
  tipo_descripcion: string;
  letra: string;
  punto_venta: number;
  numero: number;
  contraparte: string;
  doc_nro: string | null;
  condicion_iva: string;
  neto_gravado: string;
  no_gravado: string;
  exento: string;
  iva: string;
  percepciones: string;
  otros: string;
  total: string;
  alicuotas: AlicuotaLibro[];
}

export interface LibroIva {
  periodo: string;
  filas: FilaLibro[];
  totales: Omit<FilaLibro, "id" | "fecha" | "tipo_codigo" | "tipo_descripcion" | "letra" | "punto_venta" | "numero" | "contraparte" | "doc_nro" | "condicion_iva" | "alicuotas"> & {
    por_alicuota: AlicuotaLibro[];
  };
}

export interface Retencion {
  id: string;
  tipo: "sufrida" | "practicada";
  regimen: string;
  fecha: string;
  importe: string;
  nro_certificado: string | null;
  cliente_id: string | null;
  proveedor_id: string | null;
  contraparte: string | null;
  descripcion: string | null;
}

export interface ResumenRetencion {
  tipo: string;
  regimen: string;
  cantidad: number;
  total: string;
}

export const MEDIOS_PAGO: Record<string, string> = {
  efectivo: "Efectivo",
  transferencia: "Transferencia",
  cheque: "Cheque",
  tarjeta: "Tarjeta",
  mercadopago: "Mercado Pago",
  otro: "Otro",
};

// ===== POS Mostrador (Fase 6) =====

export interface Sucursal {
  id: string;
  nombre: string;
  domicilio: string | null;
  localidad: string | null;
  provincia_id: number | null;
  codigo_postal: string | null;
  latitud: number | null;
  longitud: number | null;
  telefono: string | null;
  activa: boolean;
}

export interface PosCaja {
  id: string;
  nombre: string;
  sucursal_id: string | null;
  punto_venta_id: string;
  punto_venta_numero: number;
  deposito_id: string | null;
  lista_precios: number;
  ancho_ticket: number;
  /** F12-d: estandar (mostrador) | resto (mesas/comandas) */
  perfil: "estandar" | "resto";
  activa: boolean;
  sesion_abierta: boolean;
}

export interface PosSesion {
  id: string;
  caja_id: string;
  caja_nombre: string;
  caja_perfil: "estandar" | "resto";
  ancho_ticket: number;
  cajero_id: string;
  cajero_nombre: string;
  estado: "abierta" | "cerrada";
  fondo_inicial: string;
  abierta_at: string;
  cerrada_at: string | null;
  cantidad_tickets: number | null;
  total_ventas: string | null;
  cobrado_efectivo: string | null;
  cobrado_tarjeta: string | null;
  cobrado_mercadopago: string | null;
  cobrado_otros: string | null;
  efectivo_teorico: string | null;
  efectivo_contado: string | null;
  diferencia: string | null;
  observaciones: string | null;
}

export interface PosResumen {
  sesion_id: string;
  fondo_inicial: string;
  cantidad_tickets: number;
  anulaciones: number;
  total_ventas: string;
  medios: TotalMedio[];
  efectivo_teorico: string;
}

export interface PosVarianteBusqueda {
  variante_id: string;
  descripcion: string;
  codigo_barras: string | null;
  precio: string;
}

export interface PosEnvaseBusqueda {
  articulo_id: string;
  codigo: string;
  descripcion: string;
  precio: string;
}

export interface PosResultadoBusqueda {
  articulo_id: string;
  variante_id: string | null;
  codigo: string;
  descripcion: string;
  precio: string;
  tasa_iva: string;
  pesable: boolean;
  exacto: boolean;
  tiene_variantes: boolean;
  variantes: PosVarianteBusqueda[];
  /** F12-b: cantidad resuelta desde la etiqueta de balanza (kg, o importe/precio). */
  cantidad: string | null;
  envase: PosEnvaseBusqueda | null;
}

// ===== POS Resto (F12-d) =====

export interface PosSalon {
  id: string;
  nombre: string;
  orden: number;
  activo: boolean;
}

export interface PosMesa {
  id: string;
  salon_id: string;
  salon_nombre: string;
  numero: number;
  nombre: string | null;
  activa: boolean;
  ocupada: boolean;
  comanda_id: string | null;
  comanda_total: string | null;
  mozo_nombre: string | null;
  abierta_at: string | null;
}

export interface PosComandaItem {
  id: string;
  articulo_id: string;
  variante_id: string | null;
  descripcion: string;
  cantidad: string;
  precio_unitario: string;
  importe: string;
  observaciones: string | null;
  estado_cocina: "pendiente" | "enviado";
}

export interface PosComanda {
  id: string;
  caja_id: string;
  mesa_id: string | null;
  mesa_numero: number | null;
  salon_nombre: string | null;
  tipo: "mesa" | "delivery" | "takeaway";
  estado: "abierta" | "cerrada" | "anulada";
  mozo_id: string;
  mozo_nombre: string;
  cubiertos: number | null;
  cliente_nombre: string | null;
  telefono: string | null;
  domicilio: string | null;
  localidad: string | null;
  latitud: string | null;
  longitud: string | null;
  envio_estado: "en_preparacion" | "despachado" | "entregado" | null;
  propina_pct: string;
  observaciones: string | null;
  comprobante_id: string | null;
  abierta_at: string;
  cerrada_at: string | null;
  total: string;
  items: PosComandaItem[];
}

export interface PosCocina {
  comanda_id: string;
  mesa: string | null;
  tipo: string;
  mozo_nombre: string;
  hora: string;
  items: { cantidad: string; descripcion: string; observaciones: string | null }[];
}

export interface PosReporteMozo {
  mozo_id: string;
  mozo_nombre: string;
  comandas: number;
  total_vendido: string;
  propina_estimada: string;
}

// ===== Despiece / transformación de stock (F12-c) =====

export interface DespiecePlantillaCorte {
  articulo_id: string;
  articulo_codigo: string;
  articulo_descripcion: string;
  rendimiento_pct: string;
  coef_valor: string;
}

export interface DespiecePlantilla {
  id: string;
  nombre: string;
  articulo_origen_id: string;
  origen_codigo: string;
  origen_descripcion: string;
  activa: boolean;
  cortes: DespiecePlantillaCorte[];
}

export interface TransformacionResultado {
  grupo_id: string;
  merma: string;
  costo_total: string;
  costos_corte: { articulo_id: string; costo_unitario: string }[];
}

export interface PosBalanzaConfig {
  habilitado: boolean;
  prefijo: string;
  valor_tipo: "peso" | "importe";
  codigo_digitos: number;
}

export interface PosDepartamento {
  articulo_id: string;
  codigo: string;
  descripcion: string;
  tasa_iva: string;
}

export interface PosItemCalculado {
  descripcion: string;
  cantidad: string;
  precio_unitario: string;
  importe_total: string;
}

export interface PosCalculo {
  letra: string;
  receptor_nombre: string;
  neto_gravado: string;
  iva: string;
  total: string;
  items: PosItemCalculado[];
}

export interface PosTicketResumen {
  id: string;
  tipo_codigo: string;
  clase: string;
  letra: string;
  numero_formateado: string | null;
  emitido_at: string | null;
  receptor_nombre: string;
  total: string;
  anulada: boolean;
}
