import { useState } from "react";
import { ApiError, apiPost, apiPut } from "../../lib/api";
import { CONDICIONES_IVA, PROVINCIAS, type Cliente } from "../../lib/types";

interface Props {
  cliente: Cliente | null; // null = alta
  onCerrar: (refrescar: boolean) => void;
}

export default function ClienteForm({ cliente, onCerrar }: Props) {
  const e = cliente?.entidad;
  const [form, setForm] = useState({
    // entidad
    tipo_persona: e?.tipo_persona ?? "F",
    razon_social: e?.razon_social ?? "",
    nombre_fantasia: e?.nombre_fantasia ?? "",
    tipo_documento: e?.tipo_documento ?? "DNI",
    nro_documento: e?.nro_documento ?? "",
    condicion_iva: e?.condicion_iva ?? "CF",
    email: e?.email ?? "",
    telefono_1: e?.telefono_1 ?? "",
    domicilio: e?.domicilio ?? "",
    localidad: e?.localidad ?? "",
    provincia_id: e?.provincia_id != null ? String(e.provincia_id) : "",
    codigo_postal: e?.codigo_postal ?? "",
    // rol cliente
    codigo: cliente?.codigo ?? "",
    lista_precios: cliente?.lista_precios ?? 1,
    descuento: cliente?.descuento ?? "0",
    limite_credito: cliente?.limite_credito ?? "",
    bloqueado: cliente?.bloqueado ?? false,
  });
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

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
      lista_precios: Number(form.lista_precios),
      descuento: form.descuento === "" ? 0 : Number(form.descuento),
      limite_credito: form.limite_credito === "" ? null : Number(form.limite_credito),
      bloqueado: form.bloqueado,
    };

    try {
      if (cliente) {
        await apiPut(`/clientes/${cliente.id}`, { ...rol, entidad });
      } else {
        await apiPost("/clientes", { ...rol, entidad });
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
        <h2>{cliente ? `Editar cliente ${cliente.codigo ?? ""}` : "Nuevo cliente"}</h2>

        {error && <div className="login-error">{error}</div>}

        <div className="seccion">Datos de la entidad</div>
        <div className="field">
          <label>Razón social / Nombre completo *</label>
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
            <label>Lista de precios</label>
            <select
              className="select"
              value={String(form.lista_precios)}
              onChange={(ev) => set("lista_precios", Number(ev.target.value))}
            >
              {[1, 2, 3, 4].map((n) => (
                <option key={n} value={String(n)}>
                  Lista {n}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Descuento %</label>
            <input
              className="input mono"
              type="number"
              step="0.01"
              min="0"
              max="99.99"
              value={form.descuento}
              onChange={(ev) => set("descuento", ev.target.value)}
            />
          </div>
        </div>
        <div className="fila">
          <div className="field">
            <label>Límite de crédito $</label>
            <input
              className="input mono"
              type="number"
              step="0.01"
              min="0"
              value={form.limite_credito}
              onChange={(ev) => set("limite_credito", ev.target.value)}
              placeholder="Sin límite"
            />
          </div>
          <div className="field">
            <label>&nbsp;</label>
            <label className="check">
              <input
                type="checkbox"
                checked={form.bloqueado}
                onChange={(ev) => set("bloqueado", ev.target.checked)}
              />
              Cliente bloqueado
            </label>
          </div>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            {guardando ? "Guardando…" : cliente ? "Guardar cambios" : "Crear cliente"}
          </button>
        </div>
      </form>
    </div>
  );
}
