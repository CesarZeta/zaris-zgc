// Configuración → Cajas POS (Fase 6): cada caja física ata un punto de venta
// (numeración/CAE), un depósito (descarga de stock), una lista de precios y
// el ancho del ticket térmico.

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPatch, apiPost } from "../../lib/api";
import type { Deposito, PosCaja, PuntoVenta, Sucursal } from "../../lib/types";

interface Form {
  id: string | null;
  nombre: string;
  sucursal_id: string;
  punto_venta_id: string;
  deposito_id: string;
  lista_precios: number;
  ancho_ticket: number;
}

const VACIO: Form = {
  id: null,
  nombre: "",
  sucursal_id: "",
  punto_venta_id: "",
  deposito_id: "",
  lista_precios: 1,
  ancho_ticket: 80,
};

export default function CajasSection() {
  const [cajas, setCajas] = useState<PosCaja[]>([]);
  const [pvs, setPvs] = useState<PuntoVenta[]>([]);
  const [depositos, setDepositos] = useState<Deposito[]>([]);
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [form, setForm] = useState<Form | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function cargar() {
    const [c, p, d, s] = await Promise.all([
      apiGet<PosCaja[]>("/pos/cajas?incluir_inactivas=true"),
      apiGet<PuntoVenta[]>("/ventas/puntos-venta"),
      apiGet<Deposito[]>("/catalogos-articulos/depositos"),
      apiGet<Sucursal[]>("/sucursales"),
    ]);
    setCajas(c.data);
    setPvs(p.data.filter((x) => x.activo));
    setDepositos(d.data.filter((x) => x.activo));
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
      sucursal_id: form.sucursal_id || null,
      punto_venta_id: form.punto_venta_id,
      deposito_id: form.deposito_id || null,
      lista_precios: form.lista_precios,
      ancho_ticket: form.ancho_ticket,
    };
    try {
      if (form.id) await apiPatch<PosCaja>(`/pos/cajas/${form.id}`, body);
      else await apiPost<PosCaja>("/pos/cajas", body);
      setForm(null);
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar la caja");
    } finally {
      setOcupado(false);
    }
  }

  async function toggleActiva(caja: PosCaja) {
    await apiPatch<PosCaja>(`/pos/cajas/${caja.id}`, { activa: !caja.activa });
    await cargar();
  }

  return (
    <div className="config-card">
      <div className="seccion">Cajas POS</div>
      <p className="config-ayuda">
        Cada caja del mostrador factura por su punto de venta, descarga stock de su depósito y
        usa su lista de precios. El ancho define el ticket térmico (58 u 80 mm).
      </p>
      {error && <div className="login-error">{error}</div>}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Caja</th>
              <th>Sucursal</th>
              <th>Punto de venta</th>
              <th>Depósito</th>
              <th className="num">Lista</th>
              <th className="num">Ticket</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {cajas.map((c) => (
              <tr key={c.id}>
                <td>
                  <b>{c.nombre}</b>
                  {c.sesion_abierta && <span className="chip chip-ok"> en uso</span>}
                </td>
                <td>{sucursales.find((s) => s.id === c.sucursal_id)?.nombre ?? "—"}</td>
                <td className="mono">{String(c.punto_venta_numero).padStart(4, "0")}</td>
                <td>{depositos.find((d) => d.id === c.deposito_id)?.nombre ?? "—"}</td>
                <td className="num">{c.lista_precios}</td>
                <td className="num">{c.ancho_ticket}mm</td>
                <td>{c.activa ? "activa" : <span className="chip chip-anulado">inactiva</span>}</td>
                <td>
                  <button
                    className="btn btn-ghost"
                    onClick={() =>
                      setForm({
                        id: c.id,
                        nombre: c.nombre,
                        sucursal_id: c.sucursal_id ?? "",
                        punto_venta_id: c.punto_venta_id,
                        deposito_id: c.deposito_id ?? "",
                        lista_precios: c.lista_precios,
                        ancho_ticket: c.ancho_ticket,
                      })
                    }
                  >
                    Editar
                  </button>{" "}
                  <button className="btn btn-ghost" onClick={() => void toggleActiva(c)}>
                    {c.activa ? "Inactivar" : "Activar"}
                  </button>
                </td>
              </tr>
            ))}
            {cajas.length === 0 && (
              <tr>
                <td colSpan={8}>Sin cajas todavía.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {form ? (
        <div className="pos-form-caja">
          <input
            className="input"
            placeholder="Nombre (Caja 1)"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
          />
          <select
            className="input"
            value={form.sucursal_id}
            onChange={(e) => setForm({ ...form, sucursal_id: e.target.value })}
          >
            <option value="">Sucursal (opcional)</option>
            {sucursales.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nombre}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={form.punto_venta_id}
            onChange={(e) => setForm({ ...form, punto_venta_id: e.target.value })}
          >
            <option value="">Punto de venta…</option>
            {pvs.map((p) => (
              <option key={p.id} value={p.id}>
                {String(p.numero).padStart(4, "0")} {p.descripcion}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={form.deposito_id}
            onChange={(e) => setForm({ ...form, deposito_id: e.target.value })}
          >
            <option value="">Depósito (default)</option>
            {depositos.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nombre}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={form.lista_precios}
            onChange={(e) => setForm({ ...form, lista_precios: Number(e.target.value) })}
          >
            {[1, 2, 3, 4].map((l) => (
              <option key={l} value={l}>
                Lista {l}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={form.ancho_ticket}
            onChange={(e) => setForm({ ...form, ancho_ticket: Number(e.target.value) })}
          >
            <option value={80}>Ticket 80mm</option>
            <option value={58}>Ticket 58mm</option>
          </select>
          <div>
            <button
              className="btn btn-primary"
              disabled={!form.nombre.trim() || !form.punto_venta_id || ocupado}
              onClick={() => void guardar()}
            >
              {form.id ? "Guardar" : "Crear caja"}
            </button>{" "}
            <button className="btn btn-ghost" onClick={() => setForm(null)}>
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <button className="btn btn-primary" onClick={() => setForm(VACIO)}>
          + Nueva caja
        </button>
      )}
    </div>
  );
}
