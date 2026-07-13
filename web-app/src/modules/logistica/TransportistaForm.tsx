// Alta/edición de transportista: entidad BUE + rol (vehículo/dominio).
// Sirve el fletero externo (CUIT) y el reparto propio (empleado/vehículo).

import { useState } from "react";
import { ApiError, apiPost, apiPut } from "../../lib/api";
import type { Transportista } from "../../lib/types";
import EntidadFields, {
  entidadDraft,
  entidadPayload,
  validarEntidad,
} from "../../components/EntidadFields";
import { AlertError } from "../../components/Alertas";
import { useDialogos } from "../../components/dialogos";

interface Props {
  transportista: Transportista | null; // null = alta
  onCerrar: (refrescar: boolean) => void;
}

export default function TransportistaForm({ transportista, onCerrar }: Props) {
  const [entidad, setEntidad] = useState(
    entidadDraft(transportista?.entidad, {
      tipo_persona: "F",
      tipo_documento: "DNI",
      condicion_iva: "CF",
    }),
  );
  const [rol, setRol] = useState({
    codigo: transportista?.codigo ?? "",
    vehiculo: transportista?.vehiculo ?? "",
    dominio: transportista?.dominio ?? "",
    observaciones: transportista?.observaciones ?? "",
    activo: transportista?.activo ?? true,
  });
  const [modificado, setModificado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  function set<K extends keyof typeof rol>(campo: K, valor: (typeof rol)[K]) {
    setRol((f) => ({ ...f, [campo]: valor }));
    setModificado(true);
  }

  async function intentarCerrar() {
    if (modificado && !(await confirmar("Hay cambios sin guardar. ¿Descartar?"))) return;
    onCerrar(false);
  }

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    setError(null);
    const errorDoc = validarEntidad(entidad);
    if (errorDoc) {
      setError(errorDoc);
      return;
    }
    setGuardando(true);
    const body = {
      codigo: rol.codigo.trim() || null,
      vehiculo: rol.vehiculo.trim() || null,
      dominio: rol.dominio.trim() || null,
      observaciones: rol.observaciones.trim() || null,
      ...(transportista ? { activo: rol.activo } : {}),
      entidad: entidadPayload(entidad),
    };
    try {
      if (transportista) {
        await apiPut(`/logistica/transportistas/${transportista.id}`, body);
      } else {
        await apiPost("/logistica/transportistas", body);
      }
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => void intentarCerrar()}>
      <form className="drawer" onClick={(ev) => ev.stopPropagation()} onSubmit={guardar}>
        <h2>{transportista ? "Editar transportista" : "Nuevo transportista"}</h2>
        <AlertError>{error}</AlertError>

        <div className="seccion">Datos de la entidad</div>
        <EntidadFields
          valor={entidad}
          onCambiar={(d) => {
            setEntidad(d);
            setModificado(true);
          }}
          labelRazonSocial="Nombre / razón social *"
        />

        <div className="seccion">Reparto</div>
        <div className="fila-3">
          <div className="field">
            <label>Código interno</label>
            <input className="input mono" value={rol.codigo} maxLength={10}
              onChange={(ev) => set("codigo", ev.target.value)} />
          </div>
          <div className="field">
            <label>Vehículo</label>
            <input className="input" value={rol.vehiculo} maxLength={60}
              placeholder="Fiat Fiorino, moto, a pie…"
              onChange={(ev) => set("vehiculo", ev.target.value)} />
          </div>
          <div className="field">
            <label>Dominio (patente)</label>
            <input className="input mono" value={rol.dominio} maxLength={15}
              onChange={(ev) => set("dominio", ev.target.value.toUpperCase())} />
          </div>
        </div>
        <div className="fila">
          <div className="field" style={{ flex: 1 }}>
            <label>Observaciones</label>
            <input className="input" value={rol.observaciones} maxLength={200}
              onChange={(ev) => set("observaciones", ev.target.value)} />
          </div>
        </div>
        {transportista && (
          <div className="fila">
            <label className="check">
              <input type="checkbox" checked={rol.activo}
                onChange={(ev) => set("activo", ev.target.checked)} />
              Activo
            </label>
          </div>
        )}

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            {guardando ? "Guardando…" : transportista ? "Guardar cambios" : "Crear transportista"}
          </button>
        </div>
        {dialogos}
      </form>
    </div>
  );
}
