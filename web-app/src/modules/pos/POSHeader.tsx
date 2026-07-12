// Marco de terminal del POS (rediseño UX 2026-07-12, mandato de César):
// la pantalla vive dentro de un bezel oscuro tipo dispositivo físico, con la
// marca ZARIS + punto de venta arriba a la izquierda, y a la derecha cajero,
// estado de conexión, fecha y reloj vivo. Compartido por mostrador, resto,
// apertura y login de caja.

import { useEffect, useState, type ReactNode } from "react";
import ZarisLogo from "../../app/ZarisLogo";
import type { PosSesion } from "../../lib/types";

/** Bezel de dispositivo: envuelve la pantalla completa del POS. */
export function PosDevice({ children, centro = false }: { children: ReactNode; centro?: boolean }) {
  return (
    <div className="pos-device">
      <div className={`pos-pantalla${centro ? " pos-centro" : ""}`}>{children}</div>
      <div className="pos-bisel-pie" aria-hidden>
        <span className="pos-led" />
        <span>ZARIS · Punto de venta</span>
      </div>
    </div>
  );
}

/** Reloj vivo de la terminal (fecha + HH:MM:SS, es-AR). */
function Reloj() {
  const [ahora, setAhora] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setAhora(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="pos-reloj">
      <span className="pos-reloj-hora">
        {ahora.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}
      </span>
      <span className="pos-reloj-fecha">
        {ahora.toLocaleDateString("es-AR", { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}
      </span>
    </div>
  );
}

/** Estado de conexión del navegador (con el nodo LAN va a significar "sin nube"). */
function EstadoConexion() {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return (
    <span className={`pos-online${online ? "" : " off"}`} title={online ? "Conectado al servidor" : "Sin conexión a internet"}>
      <span className="pos-online-dot" />
      {online ? "En línea" : "Sin conexión"}
    </span>
  );
}

/**
 * Header de la terminal. `sesion` completa el centro (PV, caja, sucursal,
 * cajero); sin sesión queda la marca + reloj (apertura). `children` son los
 * botones del extremo derecho (tabs del resto, Salir).
 */
export default function POSHeader({
  sesion,
  subtitulo = "Punto de Venta",
  children,
}: {
  sesion?: PosSesion | null;
  subtitulo?: string;
  children?: ReactNode;
}) {
  return (
    <header className="pos-topbar">
      <div className="pos-marca">
        <span className="pos-marca-logo">
          <ZarisLogo size={30} />
        </span>
        <div className="pos-marca-texto">
          <span className="pos-marca-nombre">ZARIS</span>
          <span className="pos-marca-sub">{subtitulo}</span>
        </div>
      </div>

      {sesion && (
        <>
          <span className="pos-topbar-sep" aria-hidden />
          <div className="pos-caja-info">
            {sesion.punto_venta_numero != null && (
              <span className="pos-chip-pv">PV {String(sesion.punto_venta_numero).padStart(4, "0")}</span>
            )}
            <div className="pos-caja-texto">
              <b>{sesion.caja_nombre}</b>
              <span className="chico">
                {[sesion.sucursal_nombre, sesion.empresa_nombre].filter(Boolean).join(" · ") || " "}
              </span>
            </div>
          </div>
        </>
      )}

      <div className="pos-topbar-estado">
        {sesion && (
          <div className="pos-cajero">
            <span className="pos-cajero-nombre">{sesion.cajero_nombre}</span>
            <span className="chico">
              caja abierta{" "}
              {new Date(sesion.abierta_at).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hour12: false })}
            </span>
          </div>
        )}
        <EstadoConexion />
        <Reloj />
      </div>

      {children && <div className="pos-topbar-botones">{children}</div>}
    </header>
  );
}
