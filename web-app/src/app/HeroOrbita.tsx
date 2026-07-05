import ZarisLogo from "./ZarisLogo";

/**
 * Gráfica abstracta animada del inicio: la marca ZARIS al centro, rodeada de
 * órbitas concéntricas con satélites que giran, evocando un sistema que orquesta
 * módulos alrededor del núcleo (el cliente, §1-bis del CLAUDE.md).
 *
 * SVG + CSS puro (sin librerías). La animación se apaga sola con
 * `prefers-reduced-motion` (ver app.css) para accesibilidad.
 */
export default function HeroOrbita() {
  return (
    <div className="hero-orbita" aria-hidden="true">
      <svg viewBox="0 0 320 320" className="orbitas">
        <defs>
          <radialGradient id="glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--zaris-orange)" stopOpacity="0.18" />
            <stop offset="70%" stopColor="var(--zaris-orange)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* halo suave detrás del núcleo */}
        <circle cx="160" cy="160" r="150" fill="url(#glow)" />

        {/* tres órbitas concéntricas, cada una con su satélite */}
        <g className="orbita orbita-1">
          <circle cx="160" cy="160" r="70" className="anillo" />
          <circle cx="160" cy="90" r="6" className="satelite sat-orange" />
        </g>
        <g className="orbita orbita-2">
          <circle cx="160" cy="160" r="108" className="anillo" />
          <circle cx="160" cy="52" r="5" className="satelite sat-gold" />
        </g>
        <g className="orbita orbita-3">
          <circle cx="160" cy="160" r="144" className="anillo anillo-punteado" />
          <circle cx="160" cy="16" r="4" className="satelite sat-dark" />
          <circle cx="304" cy="160" r="3" className="satelite sat-gold" />
        </g>
      </svg>

      {/* marca al centro, con leve respiración */}
      <div className="hero-marca">
        <ZarisLogo size={72} />
      </div>
    </div>
  );
}
