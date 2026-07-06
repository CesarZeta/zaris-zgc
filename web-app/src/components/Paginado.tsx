// Paginador estándar de listados server-side (total = X-Total-Count).
// No renderiza nada si todo entra en una página.

export default function Paginado({
  pagina,
  porPagina,
  total,
  onPagina,
}: {
  pagina: number;
  porPagina: number;
  total: number;
  onPagina: (pagina: number) => void;
}) {
  if (total <= porPagina) return null;
  return (
    <div className="paginado">
      <button
        className="btn btn-ghost"
        disabled={pagina === 0}
        onClick={() => onPagina(pagina - 1)}
      >
        ← Anterior
      </button>
      <span>
        {pagina * porPagina + 1}–{Math.min((pagina + 1) * porPagina, total)} de {total}
      </span>
      <button
        className="btn btn-ghost"
        disabled={(pagina + 1) * porPagina >= total}
        onClick={() => onPagina(pagina + 1)}
      >
        Siguiente →
      </button>
    </div>
  );
}
