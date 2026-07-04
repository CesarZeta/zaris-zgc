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
  cantidad: string;
  stock_minimo: string;
  ubicacion: string | null;
  articulo_codigo: string;
  articulo_descripcion: string;
  deposito_codigo: string;
  deposito_nombre: string;
}

export interface Movimiento {
  id: string;
  articulo_id: string;
  deposito_id: string;
  fecha: string;
  tipo: string;
  cantidad: string;
  saldo_resultante: string;
  comprobante: string | null;
  observaciones: string | null;
  grupo_id: string | null;
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
