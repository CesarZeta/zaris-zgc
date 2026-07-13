// Chips de estado de logística (colores de estado, nunca naranja = brand).

const ENTREGA: Record<string, [string, string]> = {
  pendiente: ["chip chip-borrador", "Pendiente"],
  asignada: ["chip chip-prueba", "En hoja"],
  en_reparto: ["chip chip-prueba", "En reparto"],
  entregada: ["chip chip-ok", "Entregada"],
  rechazada: ["chip chip-anulado", "Rechazada"],
  reprogramada: ["chip", "Reprogramada"],
};

const HOJA: Record<string, [string, string]> = {
  abierta: ["chip chip-borrador", "Abierta"],
  en_reparto: ["chip chip-prueba", "En reparto"],
  cerrada: ["chip chip-ok", "Cerrada"],
};

export function ChipEntrega({ estado, anulada }: { estado: string; anulada?: boolean }) {
  if (anulada) return <span className="chip chip-anulado">Anulada</span>;
  const [clase, label] = ENTREGA[estado] ?? ["chip", estado];
  return <span className={clase}>{label}</span>;
}

export function ChipHoja({ estado, anulada }: { estado: string; anulada?: boolean }) {
  if (anulada) return <span className="chip chip-anulado">Anulada</span>;
  const [clase, label] = HOJA[estado] ?? ["chip", estado];
  return <span className={clase}>{label}</span>;
}
