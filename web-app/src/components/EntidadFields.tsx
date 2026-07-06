// Campos de la entidad BUE compartidos por ClienteForm y ProveedorForm
// (una persona existe UNA vez en `entidades`; los roles solo agregan lo suyo).
// Incluye la validación de documento con dígito verificador, espejo de
// backend/app/core/cuit.py — el backend sigue siendo la última palabra.

import { useState } from "react";

import AddressSearch from "./AddressSearch";
import { consultarPadron } from "../lib/padron";
import { CONDICIONES_IVA, PROVINCIAS, type Entidad } from "../lib/types";

export interface EntidadDraft {
  tipo_persona: string;
  razon_social: string;
  nombre_fantasia: string;
  tipo_documento: string;
  nro_documento: string;
  condicion_iva: string;
  email: string;
  telefono_1: string;
  domicilio: string;
  localidad: string;
  provincia_id: string;
  codigo_postal: string;
  latitud: string;
  longitud: string;
}

export function entidadDraft(
  e: Entidad | null | undefined,
  defaults: { tipo_persona?: string; tipo_documento?: string; condicion_iva?: string } = {},
): EntidadDraft {
  return {
    tipo_persona: e?.tipo_persona ?? defaults.tipo_persona ?? "F",
    razon_social: e?.razon_social ?? "",
    nombre_fantasia: e?.nombre_fantasia ?? "",
    tipo_documento: e?.tipo_documento ?? defaults.tipo_documento ?? "DNI",
    nro_documento: e?.nro_documento ?? "",
    condicion_iva: e?.condicion_iva ?? defaults.condicion_iva ?? "CF",
    email: e?.email ?? "",
    telefono_1: e?.telefono_1 ?? "",
    domicilio: e?.domicilio ?? "",
    localidad: e?.localidad ?? "",
    provincia_id: e?.provincia_id != null ? String(e.provincia_id) : "",
    codigo_postal: e?.codigo_postal ?? "",
    latitud: e?.latitud != null ? String(e.latitud) : "",
    longitud: e?.longitud != null ? String(e.longitud) : "",
  };
}

/** Body `entidad` para la API (trims y nulls). */
export function entidadPayload(d: EntidadDraft) {
  return {
    tipo_persona: d.tipo_persona,
    razon_social: d.razon_social.trim(),
    nombre_fantasia: d.nombre_fantasia.trim() || null,
    tipo_documento: d.tipo_documento,
    nro_documento: d.nro_documento.trim() || null,
    condicion_iva: d.condicion_iva,
    email: d.email.trim() || null,
    telefono_1: d.telefono_1.trim() || null,
    domicilio: d.domicilio.trim() || null,
    localidad: d.localidad.trim() || null,
    provincia_id: d.provincia_id === "" ? null : Number(d.provincia_id),
    codigo_postal: d.codigo_postal.trim() || null,
    latitud: d.latitud === "" ? null : Number(d.latitud),
    longitud: d.longitud === "" ? null : Number(d.longitud),
  };
}

/** DV módulo 11 con pesos 5,4,3,2,7,6,5,4,3,2 (espejo de validar_cuit). */
export function cuitValido(cuit: string): boolean {
  const c = cuit.replace(/\D/g, "");
  if (c.length !== 11) return false;
  const pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  const resto = pesos.reduce((a, p, i) => a + p * Number(c[i]), 0) % 11;
  let dv = 11 - resto;
  if (dv === 11) dv = 0;
  else if (dv === 10) return false;
  return dv === Number(c[10]);
}

/** null = válido; string = mensaje de error (mismos criterios que el backend). */
export function validarEntidad(d: EntidadDraft): string | null {
  if (d.tipo_documento === "SD") return null;
  const n = d.nro_documento.replace(/\D/g, "");
  if (d.tipo_documento === "CUIT" || d.tipo_documento === "CUIL") {
    if (!cuitValido(n))
      return `${d.tipo_documento} inválido (dígito verificador no coincide)`;
  }
  if (d.tipo_documento === "DNI" && (n.length < 6 || n.length > 8))
    return "DNI inválido (se esperan 6 a 8 dígitos)";
  return null;
}

export default function EntidadFields({
  valor,
  onCambiar,
  labelRazonSocial = "Razón social *",
}: {
  valor: EntidadDraft;
  onCambiar: (d: EntidadDraft) => void;
  labelRazonSocial?: string;
}) {
  const d = valor;
  // domicilio "a mano" si ya trae texto sin coordenadas (carga previa a OSM); si
  // no, arranca en modo OSM (criterio BUC: solo desde el buscador).
  const [manual, setManual] = useState(d.domicilio !== "" && d.latitud === "");
  const [padronCargando, setPadronCargando] = useState(false);
  const [padronMsg, setPadronMsg] = useState<string | null>(null);

  function set<K extends keyof EntidadDraft>(campo: K, v: EntidadDraft[K]) {
    onCambiar({ ...d, [campo]: v });
  }
  const errorDoc = d.nro_documento.trim() !== "" ? validarEntidad(d) : null;
  const puedePadron =
    (d.tipo_documento === "CUIT" || d.tipo_documento === "CUIL") && cuitValido(d.nro_documento);

  async function traerPadron() {
    setPadronCargando(true);
    setPadronMsg(null);
    try {
      const p = await consultarPadron(d.nro_documento);
      onCambiar({
        ...d,
        razon_social: p.razon_social || d.razon_social,
        tipo_persona: p.tipo_persona || d.tipo_persona,
        condicion_iva: p.condicion_iva || d.condicion_iva,
        domicilio: p.domicilio ?? d.domicilio,
        localidad: p.localidad ?? d.localidad,
        provincia_id: p.provincia_id != null ? String(p.provincia_id) : d.provincia_id,
        codigo_postal: p.codigo_postal ?? d.codigo_postal,
      });
      setPadronMsg(
        p.fuente === "simulado"
          ? "Datos simulados (ARCA en modo prueba)"
          : "Datos traídos del padrón ARCA",
      );
    } catch (e) {
      setPadronMsg(e instanceof Error ? e.message : "No se pudo consultar el padrón");
    } finally {
      setPadronCargando(false);
    }
  }

  function elegirDireccion(nd: {
    domicilio: string;
    localidad: string;
    provincia_id: number | null;
    codigo_postal: string;
    latitud: number | null;
    longitud: number | null;
  }) {
    onCambiar({
      ...d,
      domicilio: nd.domicilio,
      localidad: nd.localidad,
      provincia_id: nd.provincia_id != null ? String(nd.provincia_id) : "",
      // OSM Argentina es flojo en CP: no piso el que ya haya si OSM no lo trae
      codigo_postal: nd.codigo_postal || d.codigo_postal,
      latitud: nd.latitud != null ? String(nd.latitud) : "",
      longitud: nd.longitud != null ? String(nd.longitud) : "",
    });
  }

  function quitarPin() {
    onCambiar({ ...d, latitud: "", longitud: "" });
  }

  const desdeOsm = d.latitud !== "";

  return (
    <>
      <div className="field">
        <label>{labelRazonSocial}</label>
        <input
          className="input"
          required
          value={d.razon_social}
          onChange={(ev) => set("razon_social", ev.target.value)}
          autoFocus
        />
      </div>
      <div className="fila">
        <div className="field">
          <label>Nombre de fantasía</label>
          <input
            className="input"
            value={d.nombre_fantasia}
            onChange={(ev) => set("nombre_fantasia", ev.target.value)}
          />
        </div>
        <div className="field">
          <label>Tipo de persona</label>
          <select
            className="select"
            value={d.tipo_persona}
            onChange={(ev) => set("tipo_persona", ev.target.value)}
          >
            <option value="F">Física</option>
            <option value="J">Jurídica</option>
          </select>
        </div>
      </div>
      <div className="fila-3">
        <div className="field">
          <label>Tipo doc.</label>
          <select
            className="select"
            value={d.tipo_documento}
            onChange={(ev) => set("tipo_documento", ev.target.value)}
          >
            <option value="CUIT">CUIT</option>
            <option value="CUIL">CUIL</option>
            <option value="DNI">DNI</option>
            <option value="SD">Sin doc.</option>
          </select>
        </div>
        <div className="field">
          <label>Número</label>
          <div className="input-con-boton">
            <input
              className="input mono"
              value={d.nro_documento}
              onChange={(ev) => set("nro_documento", ev.target.value)}
              disabled={d.tipo_documento === "SD"}
              placeholder={d.tipo_documento === "CUIT" ? "30-12345678-0" : ""}
            />
            {(d.tipo_documento === "CUIT" || d.tipo_documento === "CUIL") && (
              <button
                type="button"
                className="mini-btn"
                onClick={traerPadron}
                disabled={!puedePadron || padronCargando}
                title="Traer razón social, condición IVA y domicilio del padrón ARCA"
              >
                {padronCargando ? "…" : "ARCA"}
              </button>
            )}
          </div>
          {errorDoc && <span className="neg">{errorDoc}</span>}
          {padronMsg && <span className="hint-mono">{padronMsg}</span>}
        </div>
        <div className="field">
          <label>Condición IVA</label>
          <select
            className="select"
            value={d.condicion_iva}
            onChange={(ev) => set("condicion_iva", ev.target.value)}
          >
            {Object.entries(CONDICIONES_IVA).map(([codigo, nombre]) => (
              <option key={codigo} value={codigo}>
                {nombre}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="fila">
        <div className="field">
          <label>Email</label>
          <input className="input" value={d.email} onChange={(ev) => set("email", ev.target.value)} />
        </div>
        <div className="field">
          <label>Teléfono</label>
          <input
            className="input"
            value={d.telefono_1}
            onChange={(ev) => set("telefono_1", ev.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <div className="label-fila">
          <label>Domicilio</label>
          <button type="button" className="mini-btn-plano" onClick={() => setManual((m) => !m)}>
            {manual ? "buscar con mapa (OSM)" : "cargar a mano"}
          </button>
        </div>
        {manual ? (
          <input
            className="input"
            value={d.domicilio}
            onChange={(ev) => set("domicilio", ev.target.value)}
            placeholder="Calle y altura"
          />
        ) : (
          <>
            <AddressSearch onElegir={elegirDireccion} />
            {d.domicilio && (
              <div className="dir-normalizada">
                <span>{d.domicilio}</span>
                {desdeOsm && (
                  <span className="hint-mono">
                    {Number(d.latitud).toFixed(5)}, {Number(d.longitud).toFixed(5)}
                    <button type="button" className="mini-btn-plano" onClick={quitarPin}>
                      quitar
                    </button>
                  </span>
                )}
              </div>
            )}
          </>
        )}
      </div>
      <div className="fila-3">
        <div className="field">
          <label>Localidad</label>
          <input
            className="input"
            value={d.localidad}
            readOnly={!manual}
            onChange={(ev) => set("localidad", ev.target.value)}
          />
        </div>
        <div className="field">
          <label>Provincia</label>
          <select
            className="select"
            value={d.provincia_id}
            disabled={!manual}
            onChange={(ev) => set("provincia_id", ev.target.value)}
          >
            <option value="">—</option>
            {PROVINCIAS.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Cód. postal</label>
          <input
            className="input"
            value={d.codigo_postal}
            onChange={(ev) => set("codigo_postal", ev.target.value)}
          />
        </div>
      </div>
    </>
  );
}
