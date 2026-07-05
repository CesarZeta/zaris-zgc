import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSesion } from "../lib/auth";
import HeroOrbita from "./HeroOrbita";

/** Tarjetas de indicadores. Los valores reales se conectan en la Fase 7
 *  (módulo Dashboard con endpoints de agregación); por ahora, skeleton. */
const KPIS = [
  { label: "Ventas del mes", hint: "facturación acumulada" },
  { label: "Cobros pendientes", hint: "cuentas por cobrar" },
  { label: "Stock valorizado", hint: "existencias a costo" },
  { label: "Saldo de caja", hint: "efectivo del día" },
];

/** Accesos directos a los módulos del sistema. */
const MODULOS = [
  { to: "/clientes", nombre: "Clientes", desc: "Cartera, cuentas corrientes y cobranzas" },
  { to: "/ventas", nombre: "Ventas", desc: "Presupuestos, facturación y notas de crédito" },
  { to: "/proveedores", nombre: "Proveedores", desc: "Proveedores y comparativo de precios" },
  { to: "/compras", nombre: "Compras", desc: "Facturas de compra y órdenes de pago" },
  { to: "/articulos", nombre: "Artículos", desc: "Catálogo, listas de precios y variantes" },
  { to: "/stock", nombre: "Stock", desc: "Existencias, kardex y ajustes" },
  { to: "/caja", nombre: "Caja", desc: "Planilla diaria, movimientos y arqueo" },
  { to: "/pos", nombre: "Punto de Venta", desc: "Mostrador con lector y ticket térmico" },
  { to: "/libros", nombre: "Libros IVA", desc: "Ventas, compras, retenciones y CITI" },
  { to: "/configuracion", nombre: "Configuración", desc: "Empresa, rubro, usuarios y ajustes" },
];

/** Nivel de acceso legible (semántica ZGE: 1=admin, 2=supervisor). Los permisos
 *  por módulo llegan con la Fase 6.5 (RBAC); hasta entonces el acceso es total. */
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

  // reloj en vivo: se actualiza cada segundo → la sesión "respira"
  const [ahora, setAhora] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setAhora(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

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
              <div>
                <dt>Módulos habilitados</dt>
                <dd>
                  {MODULOS.length} de {MODULOS.length}
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
        {MODULOS.map((m) => (
          <Link to={m.to} className="modulo-card" key={m.to}>
            <div className="modulo-nombre">{m.nombre}</div>
            <div className="modulo-desc">{m.desc}</div>
            <span className="modulo-flecha">→</span>
          </Link>
        ))}
      </section>
    </div>
  );
}
