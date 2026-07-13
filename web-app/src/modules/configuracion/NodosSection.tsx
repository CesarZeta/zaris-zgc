// Configuración → Nodos de sucursal (F13-LAN N1, DISENO-NODO-LAN.md §3).
// Un nodo es la PC servidor local de una sucursal: sirve el POS por LAN y
// replica los maestros de la nube. El token de aparejamiento se muestra UNA
// sola vez (patrón reset de clave); mientras el nodo esté activo, su PV y los
// de las cajas POS de la sucursal facturan SOLO en el nodo.

import { useEffect, useState } from "react";

import { useDialogos } from "../../components/dialogos";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import { tienePermiso } from "../../lib/auth";
import type { NodoSucursal, PuntoVenta, Sucursal } from "../../lib/types";

interface NodoCreado extends NodoSucursal {
  token: string;
}

function fechaCorta(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return `${d.toLocaleDateString("es-AR")} ${d.toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })}`;
}

export default function NodosSection() {
  const [nodos, setNodos] = useState<NodoSucursal[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [pvs, setPvs] = useState<PuntoVenta[]>([]);
  const [form, setForm] = useState<{ sucursal_id: string; nombre: string; pv_id: string } | null>(
    null,
  );
  const [tokenNuevo, setTokenNuevo] = useState<NodoCreado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const { confirmar, dialogos } = useDialogos();
  const puedeEditar = tienePermiso("configuracion", "editar");

  async function cargar() {
    const [n, s, p] = await Promise.all([
      apiGet<NodoSucursal[]>("/nodos"),
      apiGet<Sucursal[]>("/sucursales"),
      apiGet<PuntoVenta[]>("/ventas/puntos-venta"),
    ]);
    setNodos(n.data);
    setSucursales(s.data);
    setPvs(p.data);
  }

  useEffect(() => {
    void cargar();
  }, []);

  async function crear() {
    if (!form || ocupado) return;
    setOcupado(true);
    setError(null);
    try {
      const creado = await apiPost<NodoCreado>("/nodos", {
        sucursal_id: form.sucursal_id,
        nombre: form.nombre.trim(),
        punto_venta_id: form.pv_id || null,
      });
      setTokenNuevo(creado);
      setForm(null);
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo crear el nodo");
    } finally {
      setOcupado(false);
    }
  }

  async function revocar(n: NodoSucursal) {
    if (
      !(await confirmar(
        `¿Revocar el nodo «${n.nombre}»? Deja de sincronizar y sus puntos de venta ` +
          "vuelven a facturar en la nube. Los datos locales del nodo no se tocan.",
      ))
    )
      return;
    try {
      await apiPost(`/nodos/${n.id}/revocar`, {});
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo revocar el nodo");
    }
  }

  async function regenerarToken(n: NodoSucursal) {
    if (
      !(await confirmar(
        `¿Regenerar el token de «${n.nombre}»? El token anterior deja de servir ` +
          "(hay que volver a configurar el nodo con el nuevo).",
      ))
    )
      return;
    try {
      const r = await apiPost<NodoCreado>(`/nodos/${n.id}/regenerar-token`, {});
      setTokenNuevo(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo regenerar el token");
    }
  }

  return (
    <div className="config-card">
      <div className="seccion">Nodos de sucursal (LAN)</div>
      <p className="config-ayuda">
        La PC servidor local de una sucursal: las cajas de la LAN le pegan al nodo y el POS sigue
        vendiendo aunque se corte internet. Mientras un nodo está activo, su punto de venta y los
        de las cajas POS de esa sucursal facturan <strong>solo en el nodo</strong>.
      </p>
      {error && <div className="login-error">{error}</div>}

      {tokenNuevo && (
        <div className="import-resultado">
          <p style={{ margin: 0 }}>
            Token de aparejamiento de <strong>{tokenNuevo.nombre}</strong> — copialo ahora,{" "}
            <strong>no se vuelve a mostrar</strong>. Va en la instalación del nodo
            (instalar_nodo.ps1) junto con el ID.
          </p>
          <p className="mono" style={{ wordBreak: "break-all", margin: "8px 0" }}>
            NODO_ID={tokenNuevo.id}
            <br />
            NODO_TOKEN={tokenNuevo.token}
          </p>
          <button
            className="mini-btn"
            onClick={() =>
              void navigator.clipboard.writeText(
                `NODO_ID=${tokenNuevo.id}\nNODO_TOKEN=${tokenNuevo.token}`,
              )
            }
          >
            Copiar
          </button>{" "}
          <button className="mini-btn" onClick={() => setTokenNuevo(null)}>
            Listo, lo guardé
          </button>
        </div>
      )}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Nodo</th>
              <th>Sucursal</th>
              <th>PV propio</th>
              <th>Última conexión</th>
              <th>Última réplica</th>
              <th>Atraso</th>
              <th>Versión</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {nodos.map((n) => (
              <tr key={n.id}>
                <td>
                  <b>{n.nombre}</b>
                </td>
                <td>{n.sucursal_nombre ?? "—"}</td>
                <td className="mono">
                  {n.punto_venta_numero != null
                    ? String(n.punto_venta_numero).padStart(4, "0")
                    : "—"}
                </td>
                <td className="mono">{fechaCorta(n.last_seen_at)}</td>
                <td className="mono">{fechaCorta(n.last_sync_at)}</td>
                <td>
                  {n.subida_pendientes === 0 && n.cae_pendientes === 0 ? (
                    "al día"
                  ) : (
                    <span className="chip chip-anulado">
                      {n.subida_pendientes > 0 && `${n.subida_pendientes} por subir`}
                      {n.subida_pendientes > 0 && n.cae_pendientes > 0 && " · "}
                      {n.cae_pendientes > 0 && `${n.cae_pendientes} sin CAE`}
                    </span>
                  )}
                </td>
                <td className="mono">{n.version_app ?? "—"}</td>
                <td>
                  {n.estado === "activo" ? (
                    "activo"
                  ) : (
                    <span className="chip chip-anulado">revocado</span>
                  )}
                </td>
                <td>
                  {puedeEditar && n.estado === "activo" && (
                    <>
                      <button className="btn btn-ghost" onClick={() => void regenerarToken(n)}>
                        Regenerar token
                      </button>{" "}
                      <button className="btn btn-ghost" onClick={() => void revocar(n)}>
                        Revocar
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {nodos.length === 0 && (
              <tr>
                <td colSpan={9}>Sin nodos: todas las sucursales operan online contra la nube.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {form ? (
        <div className="pos-form-caja">
          <select
            className="input"
            value={form.sucursal_id}
            onChange={(e) => setForm({ ...form, sucursal_id: e.target.value })}
          >
            <option value="">Sucursal…</option>
            {sucursales.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nombre}
              </option>
            ))}
          </select>
          <input
            className="input"
            placeholder="Nombre (Servidor local Centro)"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
          />
          <select
            className="input"
            value={form.pv_id}
            onChange={(e) => setForm({ ...form, pv_id: e.target.value })}
          >
            <option value="">PV propio del nodo (facturación de gestión)…</option>
            {pvs
              .filter((p) => p.activo)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {String(p.numero).padStart(4, "0")} — {p.descripcion || "sin descripción"}
                </option>
              ))}
          </select>
          <p className="config-ayuda" style={{ margin: 0 }}>
            El PV propio debe ser distinto del de las cajas POS (cada canal factura con su punto
            de venta y su numeración). Podés dejarlo vacío si el nodo solo opera cajas.
          </p>
          <div>
            <button
              className="btn btn-primary"
              disabled={!form.sucursal_id || !form.nombre.trim() || ocupado}
              onClick={() => void crear()}
            >
              Crear nodo
            </button>{" "}
            <button className="btn btn-ghost" onClick={() => setForm(null)}>
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        puedeEditar && (
          <button
            className="btn btn-primary"
            onClick={() => setForm({ sucursal_id: "", nombre: "", pv_id: "" })}
          >
            + Agregar nodo
          </button>
        )
      )}
      {dialogos}
    </div>
  );
}
