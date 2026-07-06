// Autocomplete de domicilios contra el proxy Nominatim (Fase 7).
// Debounce 500 ms, mínimo 3 caracteres, 5 sugerencias (política Nominatim).
// Criterio BUC heredado de ZGE: domicilio/localidad/provincia se completan
// SOLO desde OSM; el llamador los deja readOnly.

import { useEffect, useRef, useState } from "react";

import { geoBuscar, parseAddress, type DireccionNormalizada, type GeoResult } from "../lib/geo";

export default function AddressSearch({
  onElegir,
  placeholder = "Buscar dirección…",
  disabled,
}: {
  onElegir: (d: DireccionNormalizada, raw: GeoResult) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [q, setQ] = useState("");
  const [opciones, setOpciones] = useState<GeoResult[]>([]);
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const saltar = useRef(false);
  const caja = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (saltar.current) {
      saltar.current = false;
      return;
    }
    if (q.trim().length < 3) {
      setOpciones([]);
      setAbierto(false);
      return;
    }
    const t = setTimeout(async () => {
      setCargando(true);
      setError(null);
      try {
        const data = await geoBuscar(q.trim(), 5, true);
        setOpciones(data);
        setAbierto(true);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error de búsqueda");
        setOpciones([]);
        setAbierto(true);
      } finally {
        setCargando(false);
      }
    }, 500);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    function fuera(ev: MouseEvent) {
      if (caja.current && !caja.current.contains(ev.target as Node)) setAbierto(false);
    }
    document.addEventListener("mousedown", fuera);
    return () => document.removeEventListener("mousedown", fuera);
  }, []);

  function elegir(r: GeoResult) {
    saltar.current = true;
    setQ(r.display_name);
    setAbierto(false);
    setOpciones([]);
    onElegir(parseAddress(r), r);
  }

  return (
    <div className="buscador" ref={caja}>
      <input
        className="input"
        placeholder={placeholder}
        value={q}
        disabled={disabled}
        onChange={(ev) => setQ(ev.target.value)}
        onFocus={() => opciones.length > 0 && setAbierto(true)}
      />
      {cargando && <span className="hint-mono">buscando…</span>}
      {abierto && (
        <div className="buscador-opciones">
          {error && <div className="buscador-vacio neg">{error}</div>}
          {!error && opciones.length === 0 && (
            <div className="buscador-vacio">Sin resultados — refiná la búsqueda</div>
          )}
          {opciones.map((r, i) => (
            <button key={`${r.lat}-${r.lon}-${i}`} type="button" onClick={() => elegir(r)}>
              {r.display_name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
