// Autocomplete genérico con debounce (250 ms, mínimo 2 caracteres).
// El llamador pasa `buscar` estable (useCallback o función de módulo) para
// no re-disparar el efecto en cada render.

import { useEffect, useState, type ReactNode } from "react";

export default function Buscador<T>({
  placeholder,
  buscar,
  etiqueta,
  clave,
  elegido,
  onElegir,
  autoFocus,
}: {
  placeholder: string;
  buscar: (q: string) => Promise<T[]>;
  etiqueta: (item: T) => ReactNode;
  clave: (item: T) => string;
  elegido: T | null;
  onElegir: (item: T | null) => void;
  autoFocus?: boolean;
}) {
  const [q, setQ] = useState("");
  const [opciones, setOpciones] = useState<T[]>([]);

  useEffect(() => {
    if (elegido || q.trim().length < 2) {
      setOpciones([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        setOpciones(await buscar(q));
      } catch {
        setOpciones([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q, elegido, buscar]);

  if (elegido) {
    return (
      <div className="buscador-elegido">
        {etiqueta(elegido)}
        <button
          type="button"
          className="mini-btn"
          onClick={() => {
            setQ("");
            onElegir(null);
          }}
        >
          cambiar
        </button>
      </div>
    );
  }
  return (
    <div className="buscador">
      <input
        className="input"
        placeholder={placeholder}
        value={q}
        onChange={(ev) => setQ(ev.target.value)}
        autoFocus={autoFocus}
      />
      {opciones.length > 0 && (
        <div className="buscador-opciones">
          {opciones.map((item) => (
            <button key={clave(item)} type="button" onClick={() => onElegir(item)}>
              {etiqueta(item)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
