import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { clearSesion, getSesion, tienePermiso } from "../lib/auth";
import ZarisLogo from "./ZarisLogo";

const MODULOS_PROXIMOS = ["Bancos y Cheques"];

/** Ítems del menú con su módulo de permisos (Fase 6.5): sin `ver` sobre el
 *  módulo, el ítem no aparece (además del 403 del backend). */
const NAV: { to: string; label: string; modulo: string | null }[] = [
  { to: "/inicio", label: "Inicio", modulo: null },
  { to: "/clientes", label: "Clientes", modulo: "clientes" },
  { to: "/ventas", label: "Ventas", modulo: "ventas" },
  { to: "/proveedores", label: "Proveedores", modulo: "proveedores" },
  { to: "/compras", label: "Compras", modulo: "compras" },
  { to: "/articulos", label: "Artículos", modulo: "articulos" },
  { to: "/stock", label: "Stock", modulo: "stock" },
  { to: "/caja", label: "Caja", modulo: "caja" },
  { to: "/pos", label: "Punto de Venta", modulo: "pos" },
  { to: "/libros", label: "Libros IVA", modulo: "libros_iva" },
  { to: "/configuracion", label: "Configuración", modulo: "configuracion" },
];

export default function AppShell() {
  const navigate = useNavigate();
  const sesion = getSesion();
  if (!sesion) return <Navigate to="/login" replace />;

  function salir() {
    clearSesion();
    navigate("/login");
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <ZarisLogo size={24} />
          <span className="sidebar-logo-txt">ZARIS</span>
        </div>
        {NAV.filter((m) => !m.modulo || tienePermiso(m.modulo)).map((m) => (
          <NavLink
            key={m.to}
            to={m.to}
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
          >
            {m.label}
          </NavLink>
        ))}
        {MODULOS_PROXIMOS.map((m) => (
          <span key={m} className="nav-item soon">
            {m}
          </span>
        ))}
        <div className="sidebar-footer">
          <div>{sesion.user.email}</div>
          <button className="logout" onClick={salir}>
            Cerrar sesión
          </button>
        </div>
      </aside>
      <div className="main">
        <div className="topbar">
          <span className="empresa">ZARIS Gestión Comercial</span>
          <span className="usuario">
            Hola, <b>{sesion.user.nombre}</b>
          </span>
        </div>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
