/**
 * Marca ZARIS (la "Z" de trazos heredada de la suite ZGE).
 * `currentColor` → hereda el color del contenedor, así sirve en sidebar oscuro,
 * login claro o el hero animado sin variantes de archivo.
 */
export default function ZarisLogo({
  size = 28,
  title = "ZARIS",
}: {
  size?: number;
  title?: string;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 500 500"
      width={size}
      height={size}
      role="img"
      aria-label={title}
      className="zaris-mark"
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth={34}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M 110 78 L 388 78" />
        <path d="M 388 78 L 110 430" />
        <path d="M 388 220 L 222 430" />
        <path d="M 388 362 L 334 430" />
      </g>
    </svg>
  );
}
