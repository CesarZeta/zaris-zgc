// Config de etiquetas de balanza (F12-b): pesables etiquetados con EAN-13
// prefijo 20-29 — prefijo + PLU + valor embebido (peso o importe) + DV.
// El parsing es server-side (GET /pos/buscar); acá solo se configura.

import { useEffect, useMemo, useState } from "react";
import { ApiError, apiGet, apiPut } from "../../lib/api";
import { tienePermiso } from "../../lib/auth";
import type { PosBalanzaConfig } from "../../lib/types";

const PREFIJOS = ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29"];

export default function BalanzaSection() {
  const puedeEditar = tienePermiso("configuracion", "editar");
  const [cargado, setCargado] = useState(false);
  const [existe, setExiste] = useState(false);
  const [form, setForm] = useState<PosBalanzaConfig>({
    habilitado: true,
    prefijo: "20",
    valor_tipo: "peso",
    codigo_digitos: 5,
  });
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const r = await apiGet<PosBalanzaConfig | null>("/pos/balanza-config");
        if (r.data) {
          setForm(r.data);
          setExiste(true);
        }
      } finally {
        setCargado(true);
      }
    })();
  }, []);

  const esquema = useMemo(() => {
    const plu = "C".repeat(form.codigo_digitos);
    const valor = "V".repeat(10 - form.codigo_digitos);
    return `${form.prefijo} ${plu} ${valor} D`;
  }, [form.prefijo, form.codigo_digitos]);

  async function guardar() {
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const r = await apiPut<PosBalanzaConfig>("/pos/balanza-config", form);
      setForm(r);
      setExiste(true);
      setMensaje("Configuración de balanza guardada.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  if (!cargado) return null;

  return (
    <div className="config-card">
      <div className="seccion">Etiquetas de balanza (pesables)</div>
      <p className="config-ayuda">
        Para súper y carnicería: la balanza imprime etiquetas EAN-13 con un prefijo
        reservado (20–29), el código de balanza (PLU) del artículo y el peso en gramos o el
        importe en centavos. Al escanearlas, el POS arma la línea solo. Esquema actual:{" "}
        <code className="mono">{esquema}</code>
        {!existe && " — todavía no configurado (el escaneo de etiquetas está apagado)."}
      </p>
      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}
      <div className="fila">
        <label className="check">
          <input
            type="checkbox"
            disabled={!puedeEditar}
            checked={form.habilitado}
            onChange={(e) => setForm((f) => ({ ...f, habilitado: e.target.checked }))}
          />
          Habilitado
        </label>
        <div className="field">
          <label>Prefijo</label>
          <select
            className="input"
            disabled={!puedeEditar}
            value={form.prefijo}
            onChange={(e) => setForm((f) => ({ ...f, prefijo: e.target.value }))}
          >
            {PREFIJOS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Valor embebido</label>
          <select
            className="input"
            disabled={!puedeEditar}
            value={form.valor_tipo}
            onChange={(e) =>
              setForm((f) => ({ ...f, valor_tipo: e.target.value as "peso" | "importe" }))
            }
          >
            <option value="peso">Peso (gramos)</option>
            <option value="importe">Importe (centavos)</option>
          </select>
        </div>
        <div className="field">
          <label>Dígitos del PLU</label>
          <select
            className="input"
            disabled={!puedeEditar}
            value={form.codigo_digitos}
            onChange={(e) => setForm((f) => ({ ...f, codigo_digitos: Number(e.target.value) }))}
          >
            {[3, 4, 5, 6, 7].map((d) => (
              <option key={d} value={d}>
                {d} (valor: {10 - d} dígitos)
              </option>
            ))}
          </select>
        </div>
      </div>
      {puedeEditar && (
        <button className="btn btn-primary" disabled={guardando} onClick={() => void guardar()}>
          {guardando ? "Guardando…" : "Guardar balanza"}
        </button>
      )}
    </div>
  );
}
