// Chip de estado de documentos (comprobantes, compras, recibos, OP).
// Para comprobantes de venta pasar cae/arca_resultado y el chip distingue
// CAE real de CAE de prueba (modo simulado).

const CLASE_POR_ESTADO: Record<string, string> = {
  borrador: "chip chip-borrador",
  anulado: "chip chip-anulado",
  anulada: "chip chip-anulado",
  registrado: "chip chip-ok",
};

export default function ChipEstado({
  estado,
  cae,
  arcaResultado,
}: {
  estado: string;
  cae?: string | null;
  arcaResultado?: string | null;
}) {
  if (estado === "emitido" && arcaResultado === "S")
    return <span className="chip chip-prueba">CAE prueba</span>;
  if (estado === "emitido" && cae) return <span className="chip chip-ok">CAE ✓</span>;
  return <span className={CLASE_POR_ESTADO[estado] ?? "chip"}>{estado}</span>;
}
