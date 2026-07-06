// Reemplazo con identidad visual de window.confirm / window.prompt.
//
// Uso:
//   const { confirmar, pedirTexto, dialogos } = useDialogos();
//   ...
//   if (!(await confirmar("¿Anular el recibo?"))) return;
//   const nombre = await pedirTexto("Nombre del depósito:", "01");  // null = canceló
//   ...
//   return (<> ... {dialogos} </>);   // SIEMPRE renderizar {dialogos}
//
// Enter acepta, Escape (o click en el backdrop) cancela.

import { useCallback, useEffect, useState, type ReactNode } from "react";

type Dialogo =
  | { tipo: "confirmar"; mensaje: string; resolver: (ok: boolean) => void }
  | { tipo: "prompt"; mensaje: string; resolver: (valor: string | null) => void };

export function useDialogos(): {
  confirmar: (mensaje: string) => Promise<boolean>;
  pedirTexto: (mensaje: string, defecto?: string) => Promise<string | null>;
  dialogos: ReactNode;
} {
  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const [texto, setTexto] = useState("");

  const confirmar = useCallback(
    (mensaje: string) =>
      new Promise<boolean>((resolver) => setDialogo({ tipo: "confirmar", mensaje, resolver })),
    [],
  );

  const pedirTexto = useCallback(
    (mensaje: string, defecto = "") =>
      new Promise<string | null>((resolver) => {
        setTexto(defecto);
        setDialogo({ tipo: "prompt", mensaje, resolver });
      }),
    [],
  );

  const aceptar = useCallback(() => {
    if (!dialogo) return;
    if (dialogo.tipo === "confirmar") dialogo.resolver(true);
    else dialogo.resolver(texto);
    setDialogo(null);
  }, [dialogo, texto]);

  const cancelar = useCallback(() => {
    if (!dialogo) return;
    if (dialogo.tipo === "confirmar") dialogo.resolver(false);
    else dialogo.resolver(null);
    setDialogo(null);
  }, [dialogo]);

  useEffect(() => {
    if (!dialogo) return;
    function onTecla(ev: KeyboardEvent) {
      if (ev.key === "Escape") cancelar();
      if (ev.key === "Enter" && dialogo?.tipo === "confirmar") aceptar();
    }
    document.addEventListener("keydown", onTecla);
    return () => document.removeEventListener("keydown", onTecla);
  }, [dialogo, aceptar, cancelar]);

  const dialogos = dialogo && (
    // stopPropagation: puede renderizarse junto a otro backdrop (un form
    // abierto) y el click no debe llegarle
    <div
      className="drawer-backdrop"
      onClick={(ev) => {
        ev.stopPropagation();
        cancelar();
      }}
    >
      <div className="modal modal-dialogo" onClick={(ev) => ev.stopPropagation()}>
        <p className="dialogo-mensaje">{dialogo.mensaje}</p>
        {dialogo.tipo === "prompt" && (
          <input
            className="input"
            autoFocus
            value={texto}
            onChange={(ev) => setTexto(ev.target.value)}
            onKeyDown={(ev) => {
              if (ev.key === "Enter") aceptar();
            }}
          />
        )}
        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={cancelar}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            autoFocus={dialogo.tipo === "confirmar"}
            onClick={aceptar}
          >
            Aceptar
          </button>
        </div>
      </div>
    </div>
  );

  return { confirmar, pedirTexto, dialogos };
}
