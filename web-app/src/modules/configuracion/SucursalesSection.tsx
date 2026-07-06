// Configuración → Sucursales (Fase 7): ABM de la tabla que existe desde la
// migración 001 y hasta ahora no tenía UI. Las cajas POS y los usuarios
// referencian sucursales; acá se administran.

import { useEffect, useState } from "react";

import AddressSearch from "../../components/AddressSearch";
import { ApiError, apiGet, apiPatch, apiPost } from "../../lib/api";
import { PROVINCIAS, type Sucursal } from "../../lib/types";

interface Form {
  id: string | null;
  nombre: string;
  domicilio: string;
  localidad: string;
  provincia_id: string;
  codigo_postal: string;
  latitud: string;
  longitud: string;
  telefono: string;
}

const VACIO: Form = {
  id: null,
  nombre: "",
  domicilio: "",
  localidad: "",
  provincia_id: "",
  codigo_postal: "",
  latitud: "",
  longitud: "",
  telefono: "",
};

export default function SucursalesSection() {
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [form, setForm] = useState<Form | null>(null);
  const [manual, setManual] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function cargar() {
    const s = await apiGet<Sucursal[]>("/sucursales?incluir_inactivas=true");
    setSucursales(s.data);
  }

  useEffect(() => {
    void cargar();
  }, []);

  async function guardar() {
    if (!form || ocupado) return;
    setOcupado(true);
    setError(null);
    const body = {
      nombre: form.nombre.trim(),
      domicilio: form.domicilio.trim() || null,
      localidad: form.localidad.trim() || null,
      provincia_id: form.provincia_id === "" ? null : Number(form.provincia_id),
      codigo_postal: form.codigo_postal.trim() || null,
      latitud: form.latitud === "" ? null : Number(form.latitud),
      longitud: form.longitud === "" ? null : Number(form.longitud),
      telefono: form.telefono.trim() || null,
    };
    try {
      if (form.id) await apiPatch<Sucursal>(`/sucursales/${form.id}`, body);
      else await apiPost<Sucursal>("/sucursales", body);
      setForm(null);
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar la sucursal");
    } finally {
      setOcupado(false);
    }
  }

  async function toggleActiva(s: Sucursal) {
    await apiPatch<Sucursal>(`/sucursales/${s.id}`, { activa: !s.activa });
    await cargar();
  }

  function abrir(s: Sucursal | null) {
    setManual(s != null && s.latitud == null && s.domicilio != null);
    setForm(
      s
        ? {
            id: s.id,
            nombre: s.nombre,
            domicilio: s.domicilio ?? "",
            localidad: s.localidad ?? "",
            provincia_id: s.provincia_id != null ? String(s.provincia_id) : "",
            codigo_postal: s.codigo_postal ?? "",
            latitud: s.latitud != null ? String(s.latitud) : "",
            longitud: s.longitud != null ? String(s.longitud) : "",
            telefono: s.telefono ?? "",
          }
        : VACIO,
    );
  }

  return (
    <div className="config-card">
      <div className="seccion">Sucursales</div>
      <p className="config-ayuda">
        Cada punto físico del negocio. Las cajas POS, los usuarios y los movimientos de caja se
        asocian a una sucursal. El domicilio se normaliza con OpenStreetMap.
      </p>
      {error && <div className="login-error">{error}</div>}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Sucursal</th>
              <th>Domicilio</th>
              <th>Localidad</th>
              <th>Teléfono</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sucursales.map((s) => (
              <tr key={s.id}>
                <td>
                  <b>{s.nombre}</b>
                </td>
                <td>{s.domicilio ?? "—"}</td>
                <td>{s.localidad ?? "—"}</td>
                <td className="mono">{s.telefono ?? "—"}</td>
                <td>{s.activa ? "activa" : <span className="chip chip-anulado">inactiva</span>}</td>
                <td>
                  <button className="btn btn-ghost" onClick={() => abrir(s)}>
                    Editar
                  </button>{" "}
                  <button className="btn btn-ghost" onClick={() => void toggleActiva(s)}>
                    {s.activa ? "Inactivar" : "Activar"}
                  </button>
                </td>
              </tr>
            ))}
            {sucursales.length === 0 && (
              <tr>
                <td colSpan={6}>Sin sucursales todavía.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {form ? (
        <div className="pos-form-caja">
          <input
            className="input"
            placeholder="Nombre (Casa central)"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
          />
          <div className="label-fila">
            <span className="config-ayuda" style={{ margin: 0 }}>
              Domicilio
            </span>
            <button type="button" className="mini-btn-plano" onClick={() => setManual((m) => !m)}>
              {manual ? "buscar con mapa (OSM)" : "cargar a mano"}
            </button>
          </div>
          {manual ? (
            <input
              className="input"
              placeholder="Calle y altura"
              value={form.domicilio}
              onChange={(e) => setForm({ ...form, domicilio: e.target.value })}
            />
          ) : (
            <>
              <AddressSearch
                onElegir={(nd) =>
                  setForm({
                    ...form,
                    domicilio: nd.domicilio,
                    localidad: nd.localidad,
                    provincia_id: nd.provincia_id != null ? String(nd.provincia_id) : "",
                    codigo_postal: nd.codigo_postal || form.codigo_postal,
                    latitud: nd.latitud != null ? String(nd.latitud) : "",
                    longitud: nd.longitud != null ? String(nd.longitud) : "",
                  })
                }
              />
              {form.domicilio && (
                <div className="dir-normalizada">
                  <span>{form.domicilio}</span>
                  {form.latitud && (
                    <span className="hint-mono">
                      {Number(form.latitud).toFixed(5)}, {Number(form.longitud).toFixed(5)}
                    </span>
                  )}
                </div>
              )}
            </>
          )}
          <input
            className="input"
            placeholder="Localidad"
            value={form.localidad}
            readOnly={!manual}
            onChange={(e) => setForm({ ...form, localidad: e.target.value })}
          />
          <select
            className="input"
            value={form.provincia_id}
            disabled={!manual}
            onChange={(e) => setForm({ ...form, provincia_id: e.target.value })}
          >
            <option value="">Provincia…</option>
            {PROVINCIAS.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.nombre}
              </option>
            ))}
          </select>
          <input
            className="input"
            placeholder="Cód. postal"
            value={form.codigo_postal}
            onChange={(e) => setForm({ ...form, codigo_postal: e.target.value })}
          />
          <input
            className="input"
            placeholder="Teléfono"
            value={form.telefono}
            onChange={(e) => setForm({ ...form, telefono: e.target.value })}
          />
          <div>
            <button
              className="btn btn-primary"
              disabled={!form.nombre.trim() || ocupado}
              onClick={() => void guardar()}
            >
              {form.id ? "Guardar" : "Crear sucursal"}
            </button>{" "}
            <button className="btn btn-ghost" onClick={() => setForm(null)}>
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-primary" onClick={() => abrir(null)}>
          + Nueva sucursal
        </button>
      )}
    </div>
  );
}
