import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPut } from "../../lib/api";
import type { Empresa, Rubro } from "../../lib/types";

const DETALLE: Record<string, string> = {
  general: "Sin presets especiales: todas las opciones visibles.",
  supermercado: "Muestra pesables, envases retornables y venta por departamento.",
  indumentaria_calzado: "Variantes destacadas; siembra Talle (XS–XXL) y Color.",
  electronica: "Variantes destacadas y precios en USD; siembra Color y Capacidad.",
  ferreteria_repuestos: "Precios en USD destacados; siembra el atributo Medida.",
  distribuidora: "Orientado a mayorista; siembra Gusto y Presentación.",
};

export default function ConfiguracionPage() {
  const [empresa, setEmpresa] = useState<Empresa | null>(null);
  const [rubros, setRubros] = useState<Rubro[]>([]);
  const [guardando, setGuardando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const [e, r] = await Promise.all([
        apiGet<Empresa>("/empresa"),
        apiGet<Rubro[]>("/empresa/rubros"),
      ]);
      setEmpresa(e.data);
      setRubros(r.data);
    })();
  }, []);

  async function cambiarRubro(rubro: string) {
    if (!empresa || rubro === empresa.rubro) return;
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const actualizada = await apiPut<Empresa>("/empresa/rubro", { rubro });
      setEmpresa(actualizada);
      setMensaje(
        "Rubro actualizado. Se sembraron los atributos sugeridos (si no existían) — revisá Artículos.",
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el rubro");
    } finally {
      setGuardando(false);
    }
  }

  if (!empresa) return <p className="page-sub">Cargando…</p>;

  return (
    <>
      <h1 className="page-title">Configuración</h1>
      <p className="page-sub">{empresa.razon_social}</p>

      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      <div className="config-card">
        <div className="seccion">Rubro del comercio</div>
        <p className="config-ayuda">
          La gestión es una sola para todos los rubros; el rubro adapta el formulario de
          artículos, los atributos sugeridos para variantes y, más adelante, el punto de venta
          que usan las cajas.
        </p>
        <div className="rubros-grid">
          {rubros.map((r) => (
            <button
              key={r.codigo}
              className={`rubro-card${empresa.rubro === r.codigo ? " activo" : ""}`}
              disabled={guardando}
              onClick={() => void cambiarRubro(r.codigo)}
            >
              <span className="rubro-nombre">{r.nombre}</span>
              <span className="rubro-detalle">{DETALLE[r.codigo]}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
