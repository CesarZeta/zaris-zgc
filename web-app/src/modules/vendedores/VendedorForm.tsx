// Alta/edición de vendedor: entidad BUE + rol (código, % de comisión y
// modalidad venta/cobranza — el esquema del VIAJANTE del legacy).

import { useState } from "react";
import { ApiError, apiPost, apiPut } from "../../lib/api";
import type { Vendedor } from "../../lib/types";
import EntidadFields, {
  entidadDraft,
  entidadPayload,
  validarEntidad,
} from "../../components/EntidadFields";
import { AlertError } from "../../components/Alertas";
import { useDialogos } from "../../components/dialogos";

interface Props {
  vendedor: Vendedor | null; // null = alta
  onCerrar: (refrescar: boolean) => void;
}

export default function VendedorForm({ vendedor, onCerrar }: Props) {
  const [entidad, setEntidad] = useState(
    entidadDraft(vendedor?.entidad, {
      tipo_persona: "F",
      tipo_documento: "DNI",
      condicion_iva: "CF",
    }),
  );
  const [rol, setRol] = useState({
    codigo: vendedor?.codigo ?? "",
    comision_pct: vendedor?.comision_pct ?? "0",
    modalidad: vendedor?.modalidad ?? "venta",
    activo: vendedor?.activo ?? true,
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
      comision_pct: rol.comision_pct === "" ? "0" : rol.comision_pct,
      modalidad: rol.modalidad,
      ...(vendedor ? { activo: rol.activo } : {}),
      entidad: entidadPayload(entidad),
    };
    try {
      if (vendedor) {
        await apiPut(`/vendedores/${vendedor.id}`, body);
      } else {
        await apiPost("/vendedores", body);
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
        <h2>{vendedor ? "Editar vendedor" : "Nuevo vendedor"}</h2>
        <AlertError>{error}</AlertError>

        <div className="seccion">Datos de la entidad</div>
        <EntidadFields
          valor={entidad}
          onCambiar={(d) => {
            setEntidad(d);
            setModificado(true);
          }}
          labelRazonSocial="Nombre completo *"
        />

        <div className="seccion">Comisión</div>
        <div className="fila-3">
          <div className="field">
            <label>Código interno</label>
            <input className="input mono" value={rol.codigo} maxLength={10}
              onChange={(ev) => set("codigo", ev.target.value)} />
          </div>
          <div className="field">
            <label>Comisión %</label>
            <input className="input mono" type="number" step="0.01" min="0" max="100"
              value={rol.comision_pct}
              onChange={(ev) => set("comision_pct", ev.target.value)} />
          </div>
          <div className="field">
            <label>Liquida por</label>
            <select className="select" value={rol.modalidad}
              onChange={(ev) => set("modalidad", ev.target.value as "venta" | "cobranza")}>
              <option value="venta">Venta (lo facturado)</option>
              <option value="cobranza">Cobranza (lo cobrado)</option>
            </select>
          </div>
        </div>
        {vendedor && (
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
            {guardando ? "Guardando…" : vendedor ? "Guardar cambios" : "Crear vendedor"}
          </button>
        </div>
        {dialogos}
      </form>
    </div>
  );
}
