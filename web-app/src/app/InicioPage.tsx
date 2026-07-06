import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { getSesion, tienePermiso } from "../lib/auth";
import HeroOrbita from "./HeroOrbita";

/** Tarjetas de indicadores. Los valores reales se conectan en la Fase 7
 *  (módulo Dashboard con endpoints de agregación); por ahora, skeleton. */
const KPIS = [
  { label: "Ventas del mes", hint: "facturación acumulada" },
  { label: "Cobros pendientes", hint: "cuentas por cobrar" },
  { label: "Stock valorizado", hint: "existencias a costo" },
  { label: "Saldo de caja", hint: "efectivo del día" },
];

/** Accesos directos a los módulos del sistema, con su código de permisos. */
const MODULOS = [
  { to: "/clientes", modulo: "clientes", nombre: "Clientes", desc: "Cartera, cuentas corrientes y cobranzas" },
  { to: "/ventas", modulo: "ventas", nombre: "Ventas", desc: "Presupuestos, facturación y notas de crédito" },
  { to: "/proveedores", modulo: "proveedores", nombre: "Proveedores", desc: "Proveedores y comparativo de precios" },
  { to: "/compras", modulo: "compras", nombre: "Compras", desc: "Facturas de compra y órdenes de pago" },
  { to: "/articulos", modulo: "articulos", nombre: "Artículos", desc: "Catálogo, listas de precios y variantes" },
  { to: "/stock", modulo: "stock", nombre: "Stock", desc: "Existencias, kardex y ajustes" },
  { to: "/caja", modulo: "caja", nombre: "Caja", desc: "Planilla diaria, movimientos y arqueo" },
  { to: "/pos", modulo: "pos", nombre: "Punto de Venta", desc: "Mostrador con lector y ticket térmico" },
  { to: "/libros", modulo: "libros_iva", nombre: "Libros IVA", desc: "Ventas, compras, retenciones y CITI" },
  { to: "/configuracion", modulo: "configuracion", nombre: "Configuración", desc: "Empresa, rubro, usuarios y ajustes" },
];

/** Nivel de acceso legible (semántica ZGE: 1=admin, 2=supervisor; gobierna la
 *  autorización de supervisor del POS — el acceso a módulos lo dan los roles). */
function nivelTexto(n: number): string {
  if (n <= 1) return "Administrador";
  if (n === 2) return "Supervisor";
  return "Operador";
}

/** Formatea una duración en ms como "2 h 14 min 07 s". */
function duracion(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const seg = s % 60;
  const pad = (x: number) => String(x).padStart(2, "0");
  if (h > 0) return `${h} h ${pad(m)} min ${pad(seg)} s`;
  if (m > 0) return `${m} min ${pad(seg)} s`;
  return `${seg} s`;
}

const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export default function InicioPage() {
  const sesion = getSesion();
  const nombre = sesion?.user.nombre ?? "";
  const primerNombre = nombre.split(" ")[0] || nombre;
  const nivel = sesion?.user.nivel_acceso ?? 1;
  const loginAt = sesion?.login_at ? new Date(sesion.login_at) : null;
  // permisos reales (Fase 6.5): módulos con al menos `ver`
  const habilitados = MODULOS.filter((m) => tienePermiso(m.modulo));

  // reloj en vivo: se actualiza cada segundo → la sesión "respira"
  const [ahora, setAhora] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setAhora(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  // popover con el detalle de módulos habilitados.
  // Se ancla al botón con position:fixed (coords del botón) para que NO lo
  // recorte el overflow:hidden del hero.
  const btnModulosRef = useRef<HTMLButtonElement>(null);
  const [verModulos, setVerModulos] = useState(false);
  const [popPos, setPopPos] = useState<{ top: number; left: number } | null>(null);

  function toggleModulos() {
    if (verModulos) {
      setVerModulos(false);
      return;
    }
    const r = btnModulosRef.current?.getBoundingClientRect();
    if (r) {
      const margen = 16;
      // ancho estimado (2 columnas). Si no entra a la derecha del botón, lo
      // alineamos por su borde derecho para que no se salga.
      const ancho = Math.min(360, window.innerWidth - 2 * margen);
      let left = r.left;
      if (left + ancho > window.innerWidth - margen) {
        left = Math.max(margen, r.right - ancho);
      }
      // alto estimado (título + 5 filas). Preferimos abrir hacia abajo; si no
      // entra, hacia arriba; si tampoco (ventana muy baja), lo pegamos al tope
      // con margen y el max-height del CSS activa scroll interno.
      const alto = 190;
      let top = r.bottom + 8;
      if (top + alto > window.innerHeight - margen) {
        const arriba = r.top - alto - 8;
        top = arriba >= margen ? arriba : margen;
      }
      // clamp final: nunca dejar que el borde inferior se salga (el max-height
      // del CSS activa scroll interno si aun así no entra).
      top = Math.min(top, Math.max(margen, window.innerHeight - alto - margen));
      setPopPos({ top, left });
    }
    setVerModulos(true);
  }

  useEffect(() => {
    if (!verModulos) return;
    const cerrar = (e: KeyboardEvent) => e.key === "Escape" && setVerModulos(false);
    // si cambia el tamaño o hace scroll, cerramos (la posición quedaría vieja)
    const reposicionar = () => setVerModulos(false);
    document.addEventListener("keydown", cerrar);
    window.addEventListener("resize", reposicionar);
    window.addEventListener("scroll", reposicionar, true);
    return () => {
      document.removeEventListener("keydown", cerrar);
      window.removeEventListener("resize", reposicionar);
      window.removeEventListener("scroll", reposicionar, true);
    };
  }, [verModulos]);

  const hh = (d: Date) =>
    `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const fechaLarga = `${DIAS[ahora.getDay()]} ${ahora.getDate()} de ${MESES[ahora.getMonth()]} de ${ahora.getFullYear()}`;
  const relojFull = `${hh(ahora)}:${String(ahora.getSeconds()).padStart(2, "0")}`;
  const enSesion = loginAt ? duracion(ahora.getTime() - loginAt.getTime()) : "—";

  return (
    <div className="inicio">
      <section className="inicio-hero">
        <div className="hero-izq">
          <HeroOrbita />
        </div>

        <div className="hero-der">
          {/* Bloque 1 — sesión activa + datos del usuario, todo junto */}
          <div className="hero-bloque">
            <div className="hero-vivo">
              <span className="pulso" aria-hidden="true" />
              Sesión activa · monitoreada
            </div>
            <p className="inicio-hola">Bienvenido</p>
            <h1 className="inicio-titulo">{nombre || "Usuario"}</h1>
            <dl className="hero-datos">
              <div>
                <dt>Nivel de acceso</dt>
                <dd>{nivelTexto(nivel)}</dd>
              </div>
              <div className="hero-modulos-dato">
                <dt>Módulos habilitados</dt>
                <dd>
                  {habilitados.length} de {MODULOS.length}
                  <button
                    type="button"
                    className="ver-detalle"
                    ref={btnModulosRef}
                    onClick={toggleModulos}
                    aria-expanded={verModulos}
                  >
                    Ver detalle
                  </button>
                </dd>
              </div>
            </dl>
          </div>

          {/* Bloque 2 — horario (hora en vivo) */}
          <div className="hero-bloque">
            <dt className="hero-etiqueta">Hora</dt>
            <span className="reloj-hora">{relojFull}</span>
          </div>

          {/* Bloque 3 — fecha y tiempo de sesión */}
          <div className="hero-bloque">
            <dl className="hero-datos">
              <div>
                <dt>Fecha</dt>
                <dd className="reloj-fecha">{fechaLarga}</dd>
              </div>
              <div>
                <dt>Inicio de sesión</dt>
                <dd>{loginAt ? hh(loginAt) : "—"} h</dd>
              </div>
              <div>
                <dt>Tiempo en sesión</dt>
                <dd className="mono">{enSesion}</dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      <section className="inicio-kpis">
        {KPIS.map((k) => (
          <div className="kpi-card" key={k.label}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-valor skeleton">—</div>
            <div className="kpi-hint">{k.hint}</div>
          </div>
        ))}
      </section>

      <h2 className="inicio-seccion">
        Módulos <span className="inicio-seccion-nota">· acceso de {primerNombre}</span>
      </h2>
      <section className="inicio-modulos">
        {habilitados.map((m) => (
          <Link to={m.to} className="modulo-card" key={m.to}>
            <div className="modulo-nombre">{m.nombre}</div>
            <div className="modulo-desc">{m.desc}</div>
            <span className="modulo-flecha">→</span>
          </Link>
        ))}
      </section>

      {/* Popover de módulos: fijo a la ventana (no lo recorta el overflow del hero) */}
      {verModulos && popPos && (
        <>
          <div
            className="modulos-pop-backdrop"
            onClick={() => setVerModulos(false)}
            aria-hidden="true"
          />
          <div
            className="modulos-pop"
            role="dialog"
            aria-label="Módulos habilitados"
            style={{ top: popPos.top, left: popPos.left }}
          >
            <div className="modulos-pop-titulo">
              Acceso a {habilitados.length} de {MODULOS.length} módulos
            </div>
            <ul className="modulos-pop-lista">
              {MODULOS.map((m) => {
                const con = tienePermiso(m.modulo);
                return (
                  <li key={m.to} className={con ? undefined : "deshabilitado"}>
                    <span className="tilde" aria-hidden="true">
                      {con ? "✓" : "–"}
                    </span>
                    {m.nombre}
                  </li>
                );
              })}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
