import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { clearSesion, getSesion } from "../lib/auth";

const MODULOS_PROXIMOS = ["Inicio", "Bancos y Cheques"];

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
        <NavLink to="/ventas" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Ventas
        </NavLink>
        <NavLink
          to="/proveedores"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          Proveedores
        </NavLink>
        <NavLink to="/compras" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Compras
        </NavLink>
        <NavLink to="/articulos" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Artículos
        </NavLink>
        <NavLink to="/stock" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Stock
        </NavLink>
        <NavLink to="/caja" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Caja
        </NavLink>
        <NavLink to="/pos" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Punto de Venta
        </NavLink>
        <NavLink to="/libros" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          Libros IVA
        </NavLink>
        <NavLink
          to="/configuracion"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          Configuración
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
