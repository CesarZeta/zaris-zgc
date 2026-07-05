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

export default function InicioPage() {
  const sesion = getSesion();
  const nombre = sesion?.user.nombre ?? "";
  const primerNombre = nombre.split(" ")[0] || nombre;

  return (
    <div className="inicio">
      <section className="inicio-hero">
        <HeroOrbita />
        <div className="inicio-bienvenida">
          <p className="inicio-hola">Bienvenido{primerNombre ? `, ${primerNombre}` : ""}</p>
          <h1 className="inicio-titulo">
            ZARIS <span>Gestión Comercial</span>
          </h1>
          <p className="inicio-lema">
            Tu ciclo comercial completo —ventas, compras, stock, caja e IVA— en un solo
            lugar, con facturación electrónica argentina nativa.
          </p>
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

      <h2 className="inicio-seccion">Módulos</h2>
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
