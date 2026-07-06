// Cliente del proxy Nominatim (Fase 7) — el front NUNCA llama a OSM directo.
// Porteo de ZGE con parseAddress + mapeo de provincia OSM → código ARCA del catálogo.

import { apiGet } from "./api";

export interface NominatimAddress {
  road?: string;
  house_number?: string;
  pedestrian?: string;
  footway?: string;
  cycleway?: string;
  path?: string;
  city?: string;
  town?: string;
  village?: string;
  hamlet?: string;
  municipality?: string;
  suburb?: string;
  neighbourhood?: string;
  city_district?: string;
  state?: string;
  province?: string;
  region?: string;
  postcode?: string;
  country?: string;
  [k: string]: string | undefined;
}

export interface GeoResult {
  display_name: string;
  lat: number | null;
  lon: number | null;
  type: string | null;
  class?: string | null;
  address: NominatimAddress;
}

export async function geoBuscar(q: string, limit = 5, soloDirecciones = true): Promise<GeoResult[]> {
  const params = new URLSearchParams({
    q,
    limit: String(limit),
    solo_direcciones: String(soloDirecciones),
  });
  const { data } = await apiGet<GeoResult[]>(`/geo/buscar?${params.toString()}`);
  return data;
}

// Nombres de provincia como los devuelve OSM (state) → código ARCA del catálogo.
const PROV_OSM: Record<string, number> = {
  "ciudad autónoma de buenos aires": 0,
  "ciudad autonoma de buenos aires": 0,
  "buenos aires": 1,
  catamarca: 2,
  córdoba: 3,
  cordoba: 3,
  corrientes: 4,
  "entre ríos": 5,
  "entre rios": 5,
  jujuy: 6,
  mendoza: 7,
  "la rioja": 8,
  salta: 9,
  "san juan": 10,
  "san luis": 11,
  "santa fe": 12,
  "santiago del estero": 13,
  tucumán: 14,
  tucuman: 14,
  chaco: 16,
  chubut: 17,
  formosa: 18,
  misiones: 19,
  neuquén: 20,
  neuquen: 20,
  "la pampa": 21,
  "río negro": 22,
  "rio negro": 22,
  "santa cruz": 23,
  "tierra del fuego": 24,
};

export interface DireccionNormalizada {
  domicilio: string;
  localidad: string;
  provincia_id: number | null;
  codigo_postal: string;
  latitud: number | null;
  longitud: number | null;
}

// Buenos Aires provincia y CABA comparten prefijo: OSM distingue por state.
export function provinciaArca(state: string | undefined): number | null {
  if (!state) return null;
  const key = state.trim().toLowerCase();
  if (key in PROV_OSM) return PROV_OSM[key];
  // "Provincia de Buenos Aires" / "Provincia de Córdoba" etc.
  const sinPrefijo = key.replace(/^provincia de\s+/, "");
  return sinPrefijo in PROV_OSM ? PROV_OSM[sinPrefijo] : null;
}

export function parseAddress(r: GeoResult): DireccionNormalizada {
  const a = r.address ?? {};
  const calle = a.road || a.pedestrian || a.footway || a.cycleway || a.path || "";
  const domicilio = a.house_number && calle ? `${calle} ${a.house_number}` : calle;
  const localidad =
    a.city || a.town || a.village || a.hamlet || a.municipality || a.suburb || a.neighbourhood || a.city_district || "";
  return {
    domicilio,
    localidad,
    provincia_id: provinciaArca(a.state || a.province || a.region),
    codigo_postal: a.postcode ?? "",
    latitud: r.lat,
    longitud: r.lon,
  };
}
