// Mapeos regla → cuenta contable: el corazón configurable del motor de
// asientos (espejo moderno de los CUENTA del legacy). La clave NULL es el
// default de cada regla; toda regla tiene fallback.

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPut } from "../../lib/api";
import { AlertError, AlertOk } from "../../components/Alertas";
import type { Cuenta, Mapeo, OrigenCatalogo } from "./tipos";

export default function MapeosTab({ cuentas }: { cuentas: Cuenta[] }) {
  const [mapeos, setMapeos] = useState<Mapeo[]>([]);
  const [origenes, setOrigenes] = useState<OrigenCatalogo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const imputables = cuentas.filter((c) => c.imputable && c.activa);

  async function cargar() {
    try {
      const { data } = await apiGet<Mapeo[]>("/contabilidad/mapeos");
      setMapeos(data);
      const { data: origs } = await apiGet<OrigenCatalogo[]>("/contabilidad/origenes");
      setOrigenes(origs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar mapeos");
    }
  }

  useEffect(() => {
    void cargar();
  }, []);

  async function cambiar(m: Mapeo, cuenta_id: string) {
    setError(null);
    setAviso(null);
    try {
      await apiPut("/contabilidad/mapeos", { origen: m.origen, clave: m.clave, cuenta_id });
      setAviso("Mapeo actualizado — regenerá los asientos del período para aplicarlo");
      await cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el mapeo");
    }
  }

  const descripcionDe = (origen: string) =>
    origenes.find((o) => o.origen === origen)?.descripcion ?? origen;

  return (
    <>
      <AlertError>{error}</AlertError>
      <AlertOk>{aviso}</AlertOk>
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Regla</th>
              <th>Clave</th>
              <th style={{ width: 340 }}>Cuenta contable</th>
            </tr>
          </thead>
          <tbody>
            {mapeos.map((m) => (
              <tr key={m.id}>
                <td title={descripcionDe(m.origen)}>{m.origen}</td>
                <td className="mono">{m.clave ?? "(default)"}</td>
                <td>
                  <select
                    className="select"
                    value={m.cuenta_id}
                    onChange={(ev) => void cambiar(m, ev.target.value)}
                  >
                    {imputables.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.codigo} — {c.nombre}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="texto-suave" style={{ marginTop: 8 }}>
        Los cambios de mapeo rigen al regenerar: la contabilidad se deriva de los
        documentos, así que se puede re-derivar un período completo con el mapa nuevo.
      </p>
    </>
  );
}
