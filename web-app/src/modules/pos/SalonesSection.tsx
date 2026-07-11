// Configuración → Salones y mesas (F12-d, POS resto): sectores del local y
// alta de mesas numeradas por lote. El layout es config sensible del POS
// (configuracion.editar), como las cajas.

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPatch, apiPost } from "../../lib/api";
import { tienePermiso } from "../../lib/auth";
import { useDialogos } from "../../components/dialogos";
import type { PosMesa, PosSalon } from "../../lib/types";

export default function SalonesSection() {
  const puedeEditar = tienePermiso("configuracion", "editar");
  const [salones, setSalones] = useState<PosSalon[]>([]);
  const [mesas, setMesas] = useState<PosMesa[]>([]);
  const [error, setError] = useState<string | null>(null);
  const { pedirTexto, dialogos } = useDialogos();

  async function cargar() {
    const [s, m] = await Promise.all([
      apiGet<PosSalon[]>("/pos/resto/salones?incluir_inactivos=true"),
      apiGet<PosMesa[]>("/pos/resto/mesas?incluir_inactivas=true"),
    ]);
    setSalones(s.data);
    setMesas(m.data);
  }

  useEffect(() => {
    void cargar();
  }, []);

  async function crearSalon() {
    const nombre = await pedirTexto("Nombre del salón (Salón, Vereda, Barra…):");
    if (!nombre?.trim()) return;
    try {
      await apiPost<PosSalon>("/pos/resto/salones", { nombre });
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo crear el salón");
    }
  }

  async function agregarMesas(salon: PosSalon) {
    const cant = await pedirTexto(`¿Cuántas mesas agregar a ${salon.nombre}?`, "4");
    const n = Number(cant);
    if (!cant || Number.isNaN(n) || n < 1) return;
    try {
      await apiPost<PosMesa[]>("/pos/resto/mesas", { salon_id: salon.id, cantidad: n });
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudieron crear las mesas");
    }
  }

  async function toggleMesa(m: PosMesa) {
    try {
      await apiPatch<PosMesa>(`/pos/resto/mesas/${m.id}`, { activa: !m.activa });
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo modificar la mesa");
    }
  }

  async function toggleSalon(s: PosSalon) {
    try {
      await apiPatch<PosSalon>(`/pos/resto/salones/${s.id}`, { activo: !s.activo });
      await cargar();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo modificar el salón");
    }
  }

  return (
    <div className="config-card">
      <div className="seccion">Salones y mesas (POS resto)</div>
      <p className="config-ayuda">
        Para cajas con perfil <b>resto</b>: sectores del local y sus mesas. La mesa es una
        cuenta abierta en el POS; nada de esto llega a la gestión — solo la venta final.
      </p>
      {error && <div className="login-error">{error}</div>}

      {salones.map((s) => {
        const delSalon = mesas.filter((m) => m.salon_id === s.id);
        return (
          <div key={s.id} style={{ marginBottom: "var(--space-4)" }}>
            <div className="fila" style={{ alignItems: "center" }}>
              <b>{s.nombre}</b>
              {!s.activo && <span className="chip chip-anulado">inactivo</span>}
              {puedeEditar && (
                <>
                  <button className="mini-btn" onClick={() => void agregarMesas(s)}>
                    + mesas
                  </button>
                  <button className="mini-btn" onClick={() => void toggleSalon(s)}>
                    {s.activo ? "inactivar" : "activar"}
                  </button>
                </>
              )}
            </div>
            <div className="fila" style={{ flexWrap: "wrap", gap: 6 }}>
              {delSalon.map((m) => (
                <button
                  key={m.id}
                  className={`chip${m.activa ? "" : " chip-anulado"}`}
                  title={puedeEditar ? "Click para activar/inactivar" : undefined}
                  disabled={!puedeEditar}
                  onClick={() => void toggleMesa(m)}
                >
                  Mesa {m.numero}
                </button>
              ))}
              {delSalon.length === 0 && <span className="chico">sin mesas</span>}
            </div>
          </div>
        );
      })}
      {salones.length === 0 && <p className="chico">Sin salones todavía.</p>}

      {puedeEditar && (
        <button className="btn btn-primary" onClick={() => void crearSalon()}>
          + Nuevo salón
        </button>
      )}
      {dialogos}
    </div>
  );
}
