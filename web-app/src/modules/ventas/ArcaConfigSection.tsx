// Configuración de Facturación Electrónica ARCA por empresa + puntos de venta.
// Modos: deshabilitado / simulado (pruebas SIN validez) / homologación / producción.
// Los certificados se pegan en PEM; el backend nunca los devuelve (solo "cargado ✓").

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost, apiPut } from "../../lib/api";
import type { ArcaConfig, PuntoVenta } from "../../lib/types";

const MODOS: [string, string, string][] = [
  ["deshabilitado", "Deshabilitado", "No se pueden emitir comprobantes fiscales."],
  ["simulado", "Simulado (pruebas)", "CAE ficticio marcado PRUEBA — sin validez fiscal, para probar el circuito."],
  ["homologacion", "Homologación", "Contra el ambiente de pruebas de ARCA (requiere certificado de homologación)."],
  ["produccion", "Producción", "Facturación REAL con CAE válido (requiere certificado productivo)."],
];

export default function ArcaConfigSection() {
  const [config, setConfig] = useState<ArcaConfig | null>(null);
  const [puntosVenta, setPuntosVenta] = useState<PuntoVenta[]>([]);
  const [cuit, setCuit] = useState("");
  const [iibb, setIibb] = useState("");
  const [inicio, setInicio] = useState("");
  const [umbral, setUmbral] = useState("");
  const [certPem, setCertPem] = useState("");
  const [keyPem, setKeyPem] = useState("");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    void (async () => {
      const [c, pv] = await Promise.all([
        apiGet<ArcaConfig>("/ventas/arca-config"),
        apiGet<PuntoVenta[]>("/ventas/puntos-venta"),
      ]);
      setConfig(c.data);
      setPuntosVenta(pv.data);
      setCuit(c.data.cuit ?? "");
      setIibb(c.data.iibb ?? "");
      setInicio(c.data.inicio_actividades ?? "");
      setUmbral(c.data.umbral_identificar_cf);
    })();
  }, []);

  async function guardar(modo: string) {
    if (!config) return;
    setGuardando(true);
    setError(null);
    setMensaje(null);
    try {
      const body: Record<string, unknown> = {
        modo,
        cuit: cuit.trim() || null,
        iibb: iibb.trim() || null,
        inicio_actividades: inicio || null,
        umbral_identificar_cf: umbral || "10000000",
      };
      if (certPem.trim()) body.cert_pem = certPem.trim();
      if (keyPem.trim()) body.key_pem = keyPem.trim();
      const actualizada = await apiPut<ArcaConfig>("/ventas/arca-config", body);
      setConfig(actualizada);
      setCertPem("");
      setKeyPem("");
      setMensaje(`Configuración guardada (modo ${modo}).`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar");
    } finally {
      setGuardando(false);
    }
  }

  async function agregarPuntoVenta() {
    const numero = window.prompt("Número de punto de venta (habilitado en ARCA como Web Services):");
    if (!numero) return;
    const descripcion = window.prompt("Descripción:", "Principal") ?? "";
    try {
      const pv = await apiPost<PuntoVenta>("/ventas/puntos-venta", {
        numero: Number(numero),
        descripcion,
        electronico: true,
      });
      setPuntosVenta((xs) => [...xs, pv].sort((a, b) => a.numero - b.numero));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el punto de venta");
    }
  }

  if (!config) return null;

  return (
    <div className="config-card">
      <div className="seccion">Facturación electrónica (ARCA)</div>
      <p className="config-ayuda">
        Todo comprobante fiscal sale con CAE vía WSFEv1, o no sale. El modo <b>simulado</b> permite
        probar el circuito completo con un CAE ficticio claramente marcado. Para homologación /
        producción hay que cargar CUIT y certificado (ver docs/FACTURACION-ARCA.md).
        {config.comprobantes_emitidos > 0 &&
          ` Ya se emitieron ${config.comprobantes_emitidos} comprobantes.`}
      </p>

      {error && <div className="login-error">{error}</div>}
      {mensaje && <div className="import-resultado">{mensaje}</div>}

      <div className="fila">
        <div className="field">
          <label>CUIT emisor</label>
          <input
            className="input mono"
            value={cuit}
            maxLength={11}
            onChange={(ev) => setCuit(ev.target.value.replace(/\D/g, ""))}
          />
        </div>
        <div className="field">
          <label>Ingresos Brutos</label>
          <input className="input mono" value={iibb} onChange={(ev) => setIibb(ev.target.value)} />
        </div>
        <div className="field">
          <label>Inicio de actividades</label>
          <input
            className="input"
            type="date"
            value={inicio}
            onChange={(ev) => setInicio(ev.target.value)}
          />
        </div>
        <div className="field">
          <label>Umbral identificar CF (RG 5700)</label>
          <input
            className="input mono"
            type="number"
            value={umbral}
            onChange={(ev) => setUmbral(ev.target.value)}
          />
        </div>
      </div>

      <div className="fila">
        <div className="field" style={{ flex: 1 }}>
          <label>
            Certificado (PEM) {config.tiene_certificado && <span className="chip chip-ok">cargado ✓</span>}
          </label>
          <textarea
            className="input"
            rows={3}
            placeholder="-----BEGIN CERTIFICATE-----  (pegar para reemplazar)"
            value={certPem}
            onChange={(ev) => setCertPem(ev.target.value)}
          />
        </div>
        <div className="field" style={{ flex: 1 }}>
          <label>
            Clave privada (PEM) {config.tiene_clave && <span className="chip chip-ok">cargada ✓</span>}
          </label>
          <textarea
            className="input"
            rows={3}
            placeholder="-----BEGIN PRIVATE KEY-----  (pegar para reemplazar)"
            value={keyPem}
            onChange={(ev) => setKeyPem(ev.target.value)}
          />
        </div>
      </div>

      <div className="rubros-grid">
        {MODOS.map(([codigo, nombre, detalle]) => (
          <button
            key={codigo}
            className={`rubro-card${config.modo === codigo ? " activo" : ""}`}
            disabled={guardando}
            onClick={() => void guardar(codigo)}
          >
            <span className="rubro-nombre">{nombre}</span>
            <span className="rubro-detalle">{detalle}</span>
          </button>
        ))}
      </div>

      <div className="seccion" style={{ marginTop: 16 }}>
        Puntos de venta
        <button className="mini-btn" style={{ marginLeft: 8 }} onClick={() => void agregarPuntoVenta()}>
          + agregar
        </button>
      </div>
      {puntosVenta.length === 0 ? (
        <p className="config-ayuda">Sin puntos de venta: creá al menos uno para vender.</p>
      ) : (
        <ul className="config-lista">
          {puntosVenta.map((pv) => (
            <li key={pv.id}>
              <span className="mono">{String(pv.numero).padStart(4, "0")}</span> —{" "}
              {pv.descripcion || "sin nombre"} {pv.electronico ? "· electrónico" : "· interno"}
              {!pv.activo && " · inactivo"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
