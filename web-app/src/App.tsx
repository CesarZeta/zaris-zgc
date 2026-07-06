import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./app/AppShell";
import InicioPage from "./app/InicioPage";
import LoginPage from "./app/LoginPage";
import ArticulosPage from "./modules/articulos/ArticulosPage";
import BancosPage from "./modules/bancos/BancosPage";
import CajaPage from "./modules/caja/CajaPage";
import ClientesPage from "./modules/clientes/ClientesPage";
import ComprasPage from "./modules/compras/ComprasPage";
import ConfiguracionPage from "./modules/configuracion/ConfiguracionPage";
import LibrosPage from "./modules/libros/LibrosPage";
import POSPage from "./modules/pos/POSPage";
import ProveedoresPage from "./modules/proveedores/ProveedoresPage";
import StockPage from "./modules/stock/StockPage";
import VentasPage from "./modules/ventas/VentasPage";

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {/* El POS va fuera del shell: pantalla completa de caja */}
        <Route path="/pos" element={<POSPage />} />
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/inicio" replace />} />
          <Route path="/inicio" element={<InicioPage />} />
          <Route path="/clientes" element={<ClientesPage />} />
          <Route path="/ventas" element={<VentasPage />} />
          <Route path="/proveedores" element={<ProveedoresPage />} />
          <Route path="/compras" element={<ComprasPage />} />
          <Route path="/articulos" element={<ArticulosPage />} />
          <Route path="/stock" element={<StockPage />} />
          <Route path="/caja" element={<CajaPage />} />
          <Route path="/bancos" element={<BancosPage />} />
          <Route path="/libros" element={<LibrosPage />} />
          <Route path="/configuracion" element={<ConfiguracionPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
