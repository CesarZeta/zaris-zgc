// Alta/edición de cliente: entidad BUE (campos compartidos con proveedores)
// + rol comercial (lista, condición de venta habitual, zona, crédito).

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost, apiPut } from "../../lib/api";
import type { Cliente, CondicionVentaCatalogo } from "../../lib/types";
import EntidadFields, {
  entidadDraft,
  entidadPayload,
  validarEntidad,
} from "../../components/EntidadFields";
import { AlertError } from "../../components/Alertas";
import { useDialogos } from "../../components/dialogos";

interface Zona {
  id: string;
  nombre: string;
}

interface Props {
  cliente: Cliente | null; // null = alta
  onCerrar: (refrescar: boolean) => void;
}

export default function ClienteForm({ cliente, onCerrar }: Props) {
  const [entidad, setEntidad] = useState(
    entidadDraft(cliente?.entidad, { tipo_persona: "F", tipo_documento: "DNI", condicion_iva: "CF" }),
  );
  const [rol, setRol] = useState({
    codigo: cliente?.codigo ?? "",
    lista_precios: cliente?.lista_precios ?? 1,
    condicion_venta_id: cliente?.condicion_venta_id ?? "",
    zona_id: cliente?.zona_id ?? "",
    descuento: cliente?.descuento ?? "0",
    limite_credito: cliente?.limite_credito ?? "",
    bloqueado: cliente?.bloqueado ?? false,
  });
  const [condiciones, setCondiciones] = useState<CondicionVentaCatalogo[]>([]);
  const [zonas, setZonas] = useState<Zona[]>([]);
  const [modificado, setModificado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, pedirTexto, dialogos } = useDialogos();

  useEffect(() => {
    void apiGet<CondicionVentaCatalogo[]>("/ventas/condiciones-venta").then(({ data }) =>
      setCondiciones(data.filter((c) => c.activa)),
    );
    void apiGet<Zona[]>("/clientes/zonas").then(({ data }) => setZonas(data));
  }, []);

  function set<K extends keyof typeof rol>(campo: K, valor: (typeof rol)[K]) {
    setRol((f) => ({ ...f, [campo]: valor }));
    setModificado(true);
  }

  async function nuevaZona() {
    const nombre = await pedirTexto("Nombre de la nueva zona:");
    if (!nombre?.trim()) return;
    try {
      const zona = await apiPost<Zona>("/clientes/zonas", { nombre: nombre.trim() });
      setZonas((zs) => (zs.some((z) => z.id === zona.id) ? zs : [...zs, zona]));
      set("zona_id", zona.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la zona");
    }
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
      lista_precios: Number(rol.lista_precios),
      condicion_venta_id: rol.condicion_venta_id || null,
      zona_id: rol.zona_id || null,
      descuento: rol.descuento === "" ? 0 : Number(rol.descuento),
      limite_credito: rol.limite_credito === "" ? null : Number(rol.limite_credito),
      bloqueado: rol.bloqueado,
      entidad: entidadPayload(entidad),
    };

    try {
      if (cliente) {
        await apiPut(`/clientes/${cliente.id}`, body);
      } else {
        await apiPost("/clientes", body);
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
        <h2>{cliente ? `Editar cliente ${cliente.codigo ?? ""}` : "Nuevo cliente"}</h2>

        <AlertError>{error}</AlertError>

        <div className="seccion">Datos de la entidad</div>
        <EntidadFields
          valor={entidad}
          onCambiar={(d) => {
            setEntidad(d);
            setModificado(true);
          }}
          labelRazonSocial="Razón social / Nombre completo *"
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
            <label>Lista de precios</label>
            <select
              className="select"
              value={String(rol.lista_precios)}
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
              value={rol.descuento}
              onChange={(ev) => set("descuento", ev.target.value)}
            />
          </div>
        </div>
        <div className="fila">
          <div className="field">
            <label>Condición de venta habitual</label>
            <select
              className="select"
              value={rol.condicion_venta_id}
              onChange={(ev) => set("condicion_venta_id", ev.target.value)}
            >
              <option value="">— (contado)</option>
              {condiciones.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.descripcion}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>
              Zona{" "}
              <button type="button" className="mini-btn" onClick={() => void nuevaZona()}>
                + nueva
              </button>
            </label>
            <select
              className="select"
              value={rol.zona_id}
              onChange={(ev) => set("zona_id", ev.target.value)}
            >
              <option value="">—</option>
              {zonas.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.nombre}
                </option>
              ))}
            </select>
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
              value={rol.limite_credito}
              onChange={(ev) => set("limite_credito", ev.target.value)}
              placeholder="Sin límite"
            />
          </div>
          <div className="field">
            <label>&nbsp;</label>
            <label className="check">
              <input
                type="checkbox"
                checked={rol.bloqueado}
                onChange={(ev) => set("bloqueado", ev.target.checked)}
              />
              Cliente bloqueado
            </label>
          </div>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando}>
            {guardando ? "Guardando…" : cliente ? "Guardar cambios" : "Crear cliente"}
          </button>
        </div>
        {dialogos}
      </form>
    </div>
  );
}
