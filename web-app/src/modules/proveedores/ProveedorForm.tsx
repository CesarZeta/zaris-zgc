// Alta/edición de proveedor: entidad BUE + rol (código, rubro, condición de
// pago). Espejo de ClienteForm — misma entidad puede ser cliente Y proveedor.

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost, apiPut } from "../../lib/api";
import {
  CONDICIONES_IVA,
  PROVINCIAS,
  type CondicionVentaCatalogo,
  type Proveedor,
} from "../../lib/types";

interface Props {
  proveedor: Proveedor | null; // null = alta
  onCerrar: (refrescar: boolean) => void;
}

export default function ProveedorForm({ proveedor, onCerrar }: Props) {
  const e = proveedor?.entidad;
  const [form, setForm] = useState({
    // entidad
    tipo_persona: e?.tipo_persona ?? "J",
    razon_social: e?.razon_social ?? "",
    nombre_fantasia: e?.nombre_fantasia ?? "",
    tipo_documento: e?.tipo_documento ?? "CUIT",
    nro_documento: e?.nro_documento ?? "",
    condicion_iva: e?.condicion_iva ?? "RI",
    email: e?.email ?? "",
    telefono_1: e?.telefono_1 ?? "",
    domicilio: e?.domicilio ?? "",
    localidad: e?.localidad ?? "",
    provincia_id: e?.provincia_id != null ? String(e.provincia_id) : "",
    codigo_postal: e?.codigo_postal ?? "",
    // rol proveedor
    codigo: proveedor?.codigo ?? "",
    condicion_compra_id: proveedor?.condicion_compra_id ?? "",
    rubro: proveedor?.rubro ?? "",
  });
  const [condiciones, setCondiciones] = useState<CondicionVentaCatalogo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    void apiGet<CondicionVentaCatalogo[]>("/ventas/condiciones-venta").then(({ data }) =>
      setCondiciones(data),
    );
  }, []);

  function set<K extends keyof typeof form>(campo: K, valor: (typeof form)[K]) {
    setForm((f) => ({ ...f, [campo]: valor }));
  }

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    setError(null);
    setGuardando(true);

    const entidad = {
      tipo_persona: form.tipo_persona,
      razon_social: form.razon_social.trim(),
      nombre_fantasia: form.nombre_fantasia.trim() || null,
      tipo_documento: form.tipo_documento,
      nro_documento: form.nro_documento.trim() || null,
      condicion_iva: form.condicion_iva,
      email: form.email.trim() || null,
      telefono_1: form.telefono_1.trim() || null,
      domicilio: form.domicilio.trim() || null,
      localidad: form.localidad.trim() || null,
      provincia_id: form.provincia_id === "" ? null : Number(form.provincia_id),
      codigo_postal: form.codigo_postal.trim() || null,
    };
    const rol = {
      codigo: form.codigo.trim() || null,
      condicion_compra_id: form.condicion_compra_id || null,
      rubro: form.rubro.trim() || null,
    };

    try {
      if (proveedor) {
        await apiPut(`/proveedores/${proveedor.id}`, { ...rol, entidad });
      } else {
        await apiPost("/proveedores", { ...rol, entidad });
      }
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <form className="drawer" onClick={(ev) => ev.stopPropagation()} onSubmit={guardar}>
        <h2>{proveedor ? `Editar proveedor ${proveedor.codigo ?? ""}` : "Nuevo proveedor"}</h2>

        {error && <div className="login-error">{error}</div>}

        <div className="seccion">Datos de la entidad</div>
        <div className="field">
          <label>Razón social *</label>
          <input
            className="input"
            required
            value={form.razon_social}
            onChange={(ev) => set("razon_social", ev.target.value)}
            autoFocus
          />
        </div>
        <div className="fila">
          <div className="field">
            <label>Nombre de fantasía</label>
            <input
              className="input"
              value={form.nombre_fantasia}
              onChange={(ev) => set("nombre_fantasia", ev.target.value)}
            />
          </div>
          <div className="field">
            <label>Tipo de persona</label>
            <select
              className="select"
              value={form.tipo_persona}
              onChange={(ev) => set("tipo_persona", ev.target.value)}
            >
              <option value="J">Jurídica</option>
              <option value="F">Física</option>
            </select>
          </div>
        </div>
        <div className="fila-3">
          <div className="field">
            <label>Tipo doc.</label>
            <select
              className="select"
              value={form.tipo_documento}
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
            <input
              className="input mono"
              value={form.nro_documento}
              onChange={(ev) => set("nro_documento", ev.target.value)}
              disabled={form.tipo_documento === "SD"}
              placeholder={form.tipo_documento === "CUIT" ? "30-12345678-0" : ""}
            />
          </div>
          <div className="field">
            <label>Condición IVA</label>
            <select
              className="select"
              value={form.condicion_iva}
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
            <input className="input" value={form.email} onChange={(ev) => set("email", ev.target.value)} />
          </div>
          <div className="field">
            <label>Teléfono</label>
            <input
              className="input"
              value={form.telefono_1}
              onChange={(ev) => set("telefono_1", ev.target.value)}
            />
          </div>
        </div>
        <div className="field">
          <label>Domicilio</label>
          <input
            className="input"
            value={form.domicilio}
            onChange={(ev) => set("domicilio", ev.target.value)}
          />
        </div>
        <div className="fila-3">
          <div className="field">
            <label>Localidad</label>
            <input
              className="input"
              value={form.localidad}
              onChange={(ev) => set("localidad", ev.target.value)}
            />
          </div>
          <div className="field">
            <label>Provincia</label>
            <select
              className="select"
              value={form.provincia_id}
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
              value={form.codigo_postal}
              onChange={(ev) => set("codigo_postal", ev.target.value)}
            />
          </div>
        </div>

        <div className="seccion">Datos comerciales</div>
        <div className="fila-3">
          <div className="field">
            <label>Código interno</label>
            <input
              className="input mono"
              value={form.codigo}
              onChange={(ev) => set("codigo", ev.target.value)}
              maxLength={10}
            />
          </div>
          <div className="field">
            <label>Condición de pago habitual</label>
            <select
              className="select"
              value={form.condicion_compra_id}
              onChange={(ev) => set("condicion_compra_id", ev.target.value)}
            >
              <option value="">—</option>
              {condiciones.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.descripcion}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Rubro</label>
            <input
              className="input"
              value={form.rubro}
              onChange={(ev) => set("rubro", ev.target.value)}
              maxLength={40}
              placeholder="Alimentos, ferretería…"
            />
          </div>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            {guardando ? "Guardando…" : proveedor ? "Guardar cambios" : "Crear proveedor"}
          </button>
        </div>
      </form>
    </div>
  );
}
