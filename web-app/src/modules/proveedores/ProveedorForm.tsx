// Alta/edición de proveedor: entidad BUE (campos compartidos con clientes)
// + rol (código, rubro, condición de pago). Misma entidad puede ser cliente
// Y proveedor.

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost, apiPut } from "../../lib/api";
import type { CondicionVentaCatalogo, Proveedor } from "../../lib/types";
import EntidadFields, {
  entidadDraft,
  entidadPayload,
  validarEntidad,
} from "../../components/EntidadFields";
import { AlertError } from "../../components/Alertas";
import { useDialogos } from "../../components/dialogos";

interface Props {
  proveedor: Proveedor | null; // null = alta
  onCerrar: (refrescar: boolean) => void;
}

export default function ProveedorForm({ proveedor, onCerrar }: Props) {
  const [entidad, setEntidad] = useState(
    entidadDraft(proveedor?.entidad, {
      tipo_persona: "J",
      tipo_documento: "CUIT",
      condicion_iva: "RI",
    }),
  );
  const [rol, setRol] = useState({
    codigo: proveedor?.codigo ?? "",
    condicion_compra_id: proveedor?.condicion_compra_id ?? "",
    rubro: proveedor?.rubro ?? "",
  });
  const [condiciones, setCondiciones] = useState<CondicionVentaCatalogo[]>([]);
  const [modificado, setModificado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  useEffect(() => {
    void apiGet<CondicionVentaCatalogo[]>("/ventas/condiciones-venta").then(({ data }) =>
      setCondiciones(data),
    );
  }, []);

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
      condicion_compra_id: rol.condicion_compra_id || null,
      rubro: rol.rubro.trim() || null,
      entidad: entidadPayload(entidad),
    };

    try {
      if (proveedor) {
        await apiPut(`/proveedores/${proveedor.id}`, body);
      } else {
        await apiPost("/proveedores", body);
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
        <h2>{proveedor ? `Editar proveedor ${proveedor.codigo ?? ""}` : "Nuevo proveedor"}</h2>

        <AlertError>{error}</AlertError>

        <div className="seccion">Datos de la entidad</div>
        <EntidadFields
          valor={entidad}
          onCambiar={(d) => {
            setEntidad(d);
            setModificado(true);
          }}
        />

        <div className="seccion">Datos comerciales</div>
        <div className="fila-3">
          <div className="field">
            <label>Código interno</label>
            <input
              className="input mono"
              value={rol.codigo}
              onChange={(ev) => set("codigo", ev.target.value)}
              maxLength={10}
            />
          </div>
          <div className="field">
            <label>Condición de pago habitual</label>
            <select
              className="select"
              value={rol.condicion_compra_id}
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
              value={rol.rubro}
              onChange={(ev) => set("rubro", ev.target.value)}
              maxLength={40}
              placeholder="Alimentos, ferretería…"
            />
          </div>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            {guardando ? "Guardando…" : proveedor ? "Guardar cambios" : "Crear proveedor"}
          </button>
        </div>
        {dialogos}
      </form>
    </div>
  );
}
