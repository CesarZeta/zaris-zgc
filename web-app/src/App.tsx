import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./app/AppShell";
import LoginPage from "./app/LoginPage";
import ArticulosPage from "./modules/articulos/ArticulosPage";
import ClientesPage from "./modules/clientes/ClientesPage";
import ConfiguracionPage from "./modules/configuracion/ConfiguracionPage";
import StockPage from "./modules/stock/StockPage";

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/clientes" replace />} />
          <Route path="/clientes" element={<ClientesPage />} />
          <Route path="/articulos" element={<ArticulosPage />} />
          <Route path="/stock" element={<StockPage />} />
          <Route path="/configuracion" element={<ConfiguracionPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
