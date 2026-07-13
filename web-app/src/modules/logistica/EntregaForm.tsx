// Crear entrega desde un comprobante entregable (factura/remito emitido sin
// entrega activa). El domicilio por defecto lo resuelve el SERVER (snapshot:
// predeterminado de entrega → fiscal de la entidad → receptor del papel);
// acá solo se puede pisar con texto libre.

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Entregable, Transportista } from "../../lib/types";
import { AlertError } from "../../components/Alertas";
import { useDialogos } from "../../components/dialogos";

interface Props {
  transportistas: Transportista[];
  onCerrar: (refrescar: boolean) => void;
}

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

export default function EntregaForm({ transportistas, onCerrar }: Props) {
  const [entregables, setEntregables] = useState<Entregable[]>([]);
  const [q, setQ] = useState("");
  const [cargando, setCargando] = useState(true);
  const [elegido, setElegido] = useState<Entregable | null>(null);
  const [form, setForm] = useState({
    domicilio: "",
    localidad: "",
    telefono: "",
    fecha_programada: "",
    transportista_id: "",
    bultos: "",
    observaciones: "",
  });
  const [modificado, setModificado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  useEffect(() => {
    const t = setTimeout(async () => {
      setCargando(true);
      try {
        const { data } = await apiGet<Entregable[]>(
          `/logistica/entregables?q=${encodeURIComponent(q)}&limit=50`,
        );
        setEntregables(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al buscar comprobantes");
      } finally {
        setCargando(false);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  function set<K extends keyof typeof form>(campo: K, valor: string) {
    setForm((f) => ({ ...f, [campo]: valor }));
    setModificado(true);
  }

  async function intentarCerrar() {
    if (modificado && !(await confirmar("Hay cambios sin guardar. ¿Descartar?"))) return;
    onCerrar(false);
  }

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    if (!elegido) {
      setError("Elegí el comprobante a entregar");
      return;
    }
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/logistica/entregas", {
        comprobante_id: elegido.comprobante_id,
        domicilio: form.domicilio.trim() || null,
        localidad: form.localidad.trim() || null,
        telefono: form.telefono.trim() || null,
        fecha_programada: form.fecha_programada || null,
        transportista_id: form.transportista_id || null,
        bultos: form.bultos.trim() || null,
        observaciones: form.observaciones.trim() || null,
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la entrega");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => void intentarCerrar()}>
      <form className="drawer" onClick={(ev) => ev.stopPropagation()} onSubmit={guardar}>
        <h2>Nueva entrega</h2>
        <AlertError>{error}</AlertError>

        <div className="seccion">Comprobante a entregar</div>
        {elegido ? (
          <div className="fila" style={{ alignItems: "center", gap: 8 }}>
            <span className="mono">{elegido.descripcion}</span>
            <span>{elegido.receptor_nombre}</span>
            <span className="mono">$ {fmt.format(Number(elegido.total))}</span>
            <button type="button" className="btn btn-ghost" style={{ marginLeft: "auto" }}
              onClick={() => { setElegido(null); setModificado(true); }}>
              Cambiar
            </button>
          </div>
        ) : (
          <>
            <input className="input" placeholder="Buscar por cliente o número…" value={q}
              autoFocus onChange={(ev) => setQ(ev.target.value)} />
            <div className="tabla-card" style={{ maxHeight: 220, overflowY: "auto", marginTop: 8 }}>
              <table className="tabla">
                <tbody>
                  {entregables.map((e) => (
                    <tr key={e.comprobante_id} style={{ cursor: "pointer" }}
                      onClick={() => { setElegido(e); setModificado(true); }}>
                      <td className="mono">{e.fecha}</td>
                      <td className="mono">{e.descripcion}</td>
                      <td>{e.receptor_nombre}</td>
                      <td className="num mono">$ {fmt.format(Number(e.total))}</td>
                    </tr>
                  ))}
                  {!cargando && entregables.length === 0 && (
                    <tr>
                      <td className="texto-suave">
                        Sin facturas ni remitos emitidos pendientes de entrega.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        <div className="seccion">Destino y reparto</div>
        <div className="fila">
          <div className="field" style={{ flex: 2 }}>
            <label>Domicilio (vacío = el del cliente)</label>
            <input className="input" value={form.domicilio} maxLength={180}
              placeholder="Se usa el domicilio de entrega del cliente"
              onChange={(ev) => set("domicilio", ev.target.value)} />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Localidad</label>
            <input className="input" value={form.localidad} maxLength={60}
              onChange={(ev) => set("localidad", ev.target.value)} />
          </div>
        </div>
        <div className="fila-3">
          <div className="field">
            <label>Teléfono</label>
            <input className="input mono" value={form.telefono} maxLength={30}
              onChange={(ev) => set("telefono", ev.target.value)} />
          </div>
          <div className="field">
            <label>Fecha programada</label>
            <input className="input mono" type="date" value={form.fecha_programada}
              onChange={(ev) => set("fecha_programada", ev.target.value)} />
          </div>
          <div className="field">
            <label>Transportista</label>
            <select className="select" value={form.transportista_id}
              onChange={(ev) => set("transportista_id", ev.target.value)}>
              <option value="">(se asigna con la hoja de ruta)</option>
              {transportistas.map((t) => (
                <option key={t.id} value={t.id}>{t.entidad.razon_social}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="fila">
          <div className="field" style={{ flex: 1 }}>
            <label>Bultos</label>
            <input className="input" value={form.bultos} maxLength={60}
              placeholder="3 cajas, 1 pallet…"
              onChange={(ev) => set("bultos", ev.target.value)} />
          </div>
          <div className="field" style={{ flex: 2 }}>
            <label>Observaciones</label>
            <input className="input" value={form.observaciones} maxLength={200}
              onChange={(ev) => set("observaciones", ev.target.value)} />
          </div>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button type="submit" className="btn btn-primary" disabled={guardando || !elegido}>
            {guardando ? "Creando…" : "Crear entrega"}
          </button>
        </div>
        {dialogos}
      </form>
    </div>
  );
}
