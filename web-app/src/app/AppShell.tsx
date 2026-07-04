import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { clearSesion, getSesion } from "../lib/auth";

const MODULOS_PROXIMOS = ["Inicio", "Ventas", "Compras", "Caja y Bancos", "Punto de Venta"];

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
          Z<span>GC</span>
        </div>
        <NavLink to="/clientes" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Clientes
        </NavLink>
        <NavLink to="/articulos" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Artículos
        </NavLink>
        <NavLink to="/stock" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Stock
        </NavLink>
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
