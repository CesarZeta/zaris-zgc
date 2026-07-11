// POS Mostrador (Fase 6) — pantalla de venta rápida teclado-first.
// Fuera del AppShell (pantalla completa de caja). Flujo: abrir sesión con
// fondo → escanear/buscar (multiplicador "3*") → F10 cobrar (el total EXACTO
// lo calcula el servidor) → ticket térmico. Anulación con supervisor y
// cierre con arqueo. El servidor manda: precios, letra y totales.

import { useCallback, useEffect, useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import { getSesion } from "../../lib/auth";
import type {
  Cliente,
  ImpresionPayload,
  PosCaja,
  PosCalculo,
  PosDepartamento,
  PosResultadoBusqueda,
  PosResumen,
  PosSesion,
  PosTicketResumen,
  Comprobante,
} from "../../lib/types";
import { MEDIOS_PAGO } from "../../lib/types";
import { imprimirTicket } from "./ticket";
import RestoPOS from "./RestoPOS";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const $ = (v: string | number | null | undefined) => fmt.format(Number(v ?? 0));

interface Linea {
  articulo_id: string;
  variante_id: string | null;
  codigo: string;
  descripcion: string;
  cantidad: number;
  precio: number; // final estimado; el exacto lo da /calcular
  pesable: boolean;
  es_depto?: boolean; // venta por departamento: el precio ES el importe tipeado
}

interface ClienteSel {
  id: string;
  nombre: string;
  condicion_iva: string;
}

export default function POSPage() {
  const auth = getSesion();
  const [cargando, setCargando] = useState(true);
  const [sesion, setSesion] = useState<PosSesion | null>(null);

  useEffect(() => {
    if (!auth) return;
    void (async () => {
      try {
        const r = await apiGet<PosSesion | null>("/pos/sesiones/actual");
        setSesion(r.data);
      } finally {
        setCargando(false);
      }
    })();
  }, []);

  if (!auth) return <Navigate to="/login" replace />;
  if (cargando) return <div className="pos-pantalla pos-centro">Cargando…</div>;
  if (!sesion) return <AperturaView onAbierta={setSesion} />;
  // F12-d: la caja decide la pantalla — mostrador (F6) o resto (mesas/comandas)
  return sesion.caja_perfil === "resto" ? (
    <RestoPOS sesion={sesion} onCerrada={() => setSesion(null)} />
  ) : (
    <VentaView sesion={sesion} onCerrada={() => setSesion(null)} />
  );
}

// ===== Apertura de caja =====

function AperturaView({ onAbierta }: { onAbierta: (s: PosSesion) => void }) {
  const [cajas, setCajas] = useState<PosCaja[]>([]);
  const [cajaId, setCajaId] = useState<string | null>(null);
  const [fondo, setFondo] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [cargado, setCargado] = useState(false);

  useEffect(() => {
    void (async () => {
      const r = await apiGet<PosCaja[]>("/pos/cajas");
      setCajas(r.data);
      const libre = r.data.find((c) => !c.sesion_abierta);
      if (libre) setCajaId(libre.id);
      setCargado(true);
    })();
  }, []);

  async function abrir() {
    if (!cajaId) return;
    setError(null);
    try {
      const s = await apiPost<PosSesion>("/pos/sesiones", {
        caja_id: cajaId,
        fondo_inicial: fondo || "0",
      });
      onAbierta(s);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo abrir la caja");
    }
  }

  return (
    <div className="pos-pantalla pos-centro">
      <div className="pos-apertura">
        <div className="pos-logo">
          Z<span>GC</span> · Punto de Venta
        </div>
        {error && <div className="login-error">{error}</div>}
        {cargado && cajas.length === 0 ? (
          <p className="pos-ayuda">
            No hay cajas configuradas. Creá una en{" "}
            <Link to="/configuracion">Configuración → Cajas POS</Link>.
          </p>
        ) : (
          <>
            <div className="seccion">Elegí tu caja</div>
            <div className="pos-cajas-grid">
              {cajas.map((c) => (
                <button
                  key={c.id}
                  className={`pos-caja-card${cajaId === c.id ? " activa" : ""}`}
                  disabled={c.sesion_abierta}
                  onClick={() => setCajaId(c.id)}
                >
                  <b>{c.nombre}</b>
                  <span className="chico">
                    PV {String(c.punto_venta_numero).padStart(4, "0")} · Lista {c.lista_precios} ·{" "}
                    {c.ancho_ticket}mm
                  </span>
                  {c.sesion_abierta && <span className="chip chip-borrador">en uso</span>}
                </button>
              ))}
            </div>
            <label className="pos-fondo">
              Fondo inicial (efectivo en el cajón)
              <input
                className="input num"
                type="number"
                min="0"
                step="0.01"
                value={fondo}
                onChange={(e) => setFondo(e.target.value)}
              />
            </label>
            <button className="btn btn-primary btn-block" disabled={!cajaId} onClick={() => void abrir()}>
              Abrir caja
            </button>
          </>
        )}
        <Link className="pos-salir" to="/">
          ← Volver a la gestión
        </Link>
      </div>
    </div>
  );
}

// ===== Venta =====

function VentaView({ sesion, onCerrada }: { sesion: PosSesion; onCerrada: () => void }) {
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [selec, setSelec] = useState<number>(-1);
  const [entrada, setEntrada] = useState("");
  const [multi, setMulti] = useState<number | null>(null);
  const [cliente, setCliente] = useState<ClienteSel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const [resultados, setResultados] = useState<PosResultadoBusqueda[] | null>(null);
  const [pickVariante, setPickVariante] = useState<PosResultadoBusqueda | null>(null);
  const [buscaCliente, setBuscaCliente] = useState(false);
  const [cobro, setCobro] = useState<PosCalculo | null>(null);
  const [verTickets, setVerTickets] = useState(false);
  const [verCierre, setVerCierre] = useState(false);
  const [verDepto, setVerDepto] = useState(false);
  const [deptos, setDeptos] = useState<PosDepartamento[]>([]);

  useEffect(() => {
    void (async () => {
      try {
        const r = await apiGet<PosDepartamento[]>("/pos/departamentos");
        setDeptos(r.data);
      } catch {
        /* sin departamentos configurados */
      }
    })();
  }, []);

  const inputRef = useRef<HTMLInputElement>(null);
  const modalAbierto = !!(resultados || pickVariante || buscaCliente || cobro || verTickets || verCierre || verDepto);

  const enfocar = useCallback(() => {
    setTimeout(() => inputRef.current?.focus(), 30);
  }, []);

  useEffect(() => {
    if (!modalAbierto) enfocar();
  }, [modalAbierto, enfocar]);

  function avisar(msg: string) {
    setError(msg);
    setTimeout(() => setError(null), 4000);
  }

  function agregarLinea(r: PosResultadoBusqueda, cantidad: number, varianteId?: string, precioVar?: string) {
    const varId = varianteId ?? r.variante_id;
    const precio = Number(precioVar ?? r.precio);
    setLineas((prev) => {
      const i = prev.findIndex(
        (l) => l.articulo_id === r.articulo_id && l.variante_id === (varId ?? null) && !l.es_depto,
      );
      if (i >= 0) {
        const copia = [...prev];
        copia[i] = { ...copia[i], cantidad: copia[i].cantidad + cantidad };
        setSelec(i);
        return copia;
      }
      setSelec(prev.length);
      return [
        ...prev,
        {
          articulo_id: r.articulo_id,
          variante_id: varId ?? null,
          codigo: r.codigo,
          descripcion: r.descripcion,
          cantidad,
          precio,
          pesable: r.pesable,
        },
      ];
    });
    // Envase retornable (F12-b): se agrega/acumula junto con el producto.
    if (r.envase) {
      const env = r.envase;
      setLineas((prev) => {
        const i = prev.findIndex((l) => l.articulo_id === env.articulo_id && !l.es_depto);
        if (i >= 0) {
          const copia = [...prev];
          copia[i] = { ...copia[i], cantidad: copia[i].cantidad + cantidad };
          return copia;
        }
        return [
          ...prev,
          {
            articulo_id: env.articulo_id,
            variante_id: null,
            codigo: env.codigo,
            descripcion: `${env.descripcion} (envase)`,
            cantidad,
            precio: Number(env.precio),
            pesable: false,
          },
        ];
      });
    }
  }

  function agregarDepto(d: PosDepartamento, importe: number) {
    // Cada venta por departamento es una línea propia (importe tipeado, no se acumula).
    setLineas((prev) => {
      setSelec(prev.length);
      return [
        ...prev,
        {
          articulo_id: d.articulo_id,
          variante_id: null,
          codigo: d.codigo,
          descripcion: d.descripcion,
          cantidad: 1,
          precio: importe,
          pesable: false,
          es_depto: true,
        },
      ];
    });
  }

  async function procesarEntrada() {
    const texto = entrada.trim();
    if (!texto) return;
    // multiplicador: "3*" solo, o "3*codigo"
    const m = texto.match(/^(\d+(?:[.,]\d+)?)\s*\*\s*(.*)$/);
    let cantidad = multi ?? 1;
    let codigo = texto;
    if (m) {
      cantidad = Number(m[1].replace(",", "."));
      codigo = m[2].trim();
      if (!codigo) {
        setMulti(cantidad);
        setEntrada("");
        return;
      }
    }
    setEntrada("");
    setMulti(null);
    try {
      const r = await apiGet<PosResultadoBusqueda[]>(
        `/pos/buscar?q=${encodeURIComponent(codigo)}&caja_id=${sesion.caja_id}`,
      );
      const lista = r.data;
      if (lista.length === 0) {
        avisar(`Sin resultados para “${codigo}”`);
        return;
      }
      const unico = lista[0];
      if (lista.length === 1 && unico.exacto) {
        if (unico.variante_id || !unico.tiene_variantes) {
          // etiqueta de balanza: la cantidad viene resuelta del servidor (kg o importe/precio)
          agregarLinea(unico, unico.cantidad ? Number(unico.cantidad) : cantidad);
        } else {
          setPickVariante(unico); // exacto pero hay que elegir talle/color
        }
        return;
      }
      setResultados(lista);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "Error buscando");
    }
  }

  function elegirResultado(r: PosResultadoBusqueda) {
    setResultados(null);
    if (r.tiene_variantes && !r.variante_id) {
      setPickVariante(r);
    } else {
      agregarLinea(r, multi ?? 1);
      setMulti(null);
    }
  }

  function quitarLinea(i: number) {
    setLineas((prev) => prev.filter((_, x) => x !== i));
    setSelec((s) => (s >= i ? s - 1 : s));
  }

  function cambiarCantidad(i: number, v: string) {
    const cant = Number(v.replace(",", "."));
    if (Number.isNaN(cant) || cant < 0) return;
    setLineas((prev) => prev.map((l, x) => (x === i ? { ...l, cantidad: cant } : l)));
  }

  const totalEstimado = lineas.reduce((acc, l) => acc + l.cantidad * l.precio, 0);

  async function abrirCobro() {
    if (lineas.length === 0 || ocupado) return;
    if (lineas.some((l) => l.cantidad <= 0)) {
      avisar("Hay líneas con cantidad 0");
      return;
    }
    setOcupado(true);
    try {
      const calculo = await apiPost<PosCalculo>("/pos/ventas/calcular", {
        caja_id: sesion.caja_id,
        cliente_id: cliente?.id ?? null,
        items: lineas.map((l) => ({
          articulo_id: l.articulo_id,
          variante_id: l.variante_id,
          cantidad: String(l.cantidad),
          precio_unitario: l.es_depto ? String(l.precio) : null,
        })),
      });
      setCobro(calculo);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo calcular la venta");
    } finally {
      setOcupado(false);
    }
  }

  async function confirmarVenta(medios: { medio: string; importe: string; referencia?: string }[], recibido?: string, vuelto?: string) {
    setOcupado(true);
    try {
      const vta = await apiPost<Comprobante>("/pos/ventas", {
        sesion_id: sesion.id,
        cliente_id: cliente?.id ?? null,
        items: lineas.map((l) => ({
          articulo_id: l.articulo_id,
          variante_id: l.variante_id,
          cantidad: String(l.cantidad),
          precio_unitario: l.es_depto ? String(l.precio) : null,
        })),
        medios,
      });
      setCobro(null);
      setLineas([]);
      setCliente(null);
      setSelec(-1);
      setFlash(`✔ ${vta.tipo_descripcion} ${vta.letra} ${vta.numero_formateado} — $ ${$(vta.total)}`);
      setTimeout(() => setFlash(null), 6000);
      try {
        const imp = await apiGet<ImpresionPayload>(`/ventas/comprobantes/${vta.id}/impresion`);
        imprimirTicket(imp.data, sesion.ancho_ticket, { medios, recibido, vuelto }, sesion.cajero_nombre);
      } catch {
        avisar("Venta emitida pero no se pudo generar el ticket (reimprimí desde F6)");
      }
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo emitir la venta");
      setCobro(null); // los precios pueden haber cambiado: recalcular
    } finally {
      setOcupado(false);
    }
  }

  // Teclas globales
  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      if (ev.key === "F10") {
        ev.preventDefault();
        if (!modalAbierto) void abrirCobro();
      } else if (ev.key === "F6") {
        ev.preventDefault();
        if (!modalAbierto) setVerTickets(true);
      } else if (ev.key === "F8") {
        ev.preventDefault();
        if (!modalAbierto) setVerCierre(true);
      } else if (ev.key === "F3") {
        ev.preventDefault();
        if (!modalAbierto) setBuscaCliente(true);
      } else if (ev.key === "F9") {
        ev.preventDefault();
        if (!modalAbierto && deptos.length > 0) setVerDepto(true);
      } else if (ev.key === "Escape") {
        setResultados(null);
        setPickVariante(null);
        setBuscaCliente(false);
        setCobro(null);
        setVerTickets(false);
        setVerCierre(false);
        setVerDepto(false);
        setMulti(null);
        enfocar();
      } else if (ev.key === "Delete" && !modalAbierto && selec >= 0 && document.activeElement === inputRef.current) {
        ev.preventDefault();
        quitarLinea(selec);
      } else if (ev.key === "ArrowUp" && !modalAbierto && document.activeElement === inputRef.current) {
        ev.preventDefault();
        setSelec((s) => Math.max(0, s - 1));
      } else if (ev.key === "ArrowDown" && !modalAbierto && document.activeElement === inputRef.current) {
        ev.preventDefault();
        setSelec((s) => Math.min(lineas.length - 1, s + 1));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modalAbierto, lineas.length, selec, deptos.length]);

  return (
    <div className="pos-pantalla">
      <header className="pos-topbar">
        <div className="pos-logo">
          Z<span>GC</span> POS
        </div>
        <div className="pos-caja-info">
          <b>{sesion.caja_nombre}</b> · {sesion.cajero_nombre}
        </div>
        <div className="pos-topbar-botones">
          {deptos.length > 0 && (
            <button className="btn btn-ghost" onClick={() => setVerDepto(true)}>
              Depto (F9)
            </button>
          )}
          <button className="btn btn-ghost" onClick={() => setVerTickets(true)}>
            Tickets (F6)
          </button>
          <button className="btn btn-ghost" onClick={() => setVerCierre(true)}>
            Cierre (F8)
          </button>
          <Link className="btn btn-ghost" to="/">
            Salir
          </Link>
        </div>
      </header>

      <div className="pos-cuerpo">
        <div className="pos-izquierda">
          <div className="pos-scan">
            {multi !== null && <span className="pos-multi">{fmt.format(multi)} ×</span>}
            <input
              ref={inputRef}
              className="input pos-input"
              autoFocus
              placeholder="Escaneá el código o escribí para buscar… (3* = multiplicador)"
              value={entrada}
              onChange={(e) => setEntrada(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void procesarEntrada();
                }
              }}
            />
          </div>
          {error && <div className="pos-error">{error}</div>}
          {flash && <div className="pos-flash">{flash}</div>}

          <div className="tabla-card pos-lineas">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Descripción</th>
                  <th className="num">Cant.</th>
                  <th className="num">Precio</th>
                  <th className="num">Importe</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {lineas.length === 0 && (
                  <tr>
                    <td colSpan={6} className="pos-vacio">
                      Escaneá un producto para empezar
                    </td>
                  </tr>
                )}
                {lineas.map((l, i) => (
                  <tr key={`${l.articulo_id}-${l.variante_id ?? ""}`} className={i === selec ? "pos-selec" : ""} onClick={() => setSelec(i)}>
                    <td className="mono">{l.codigo}</td>
                    <td>{l.descripcion}</td>
                    <td className="num">
                      <input
                        className="input pos-cant"
                        type="number"
                        min="0"
                        step={l.pesable ? "0.001" : "1"}
                        value={l.cantidad}
                        onChange={(e) => cambiarCantidad(i, e.target.value)}
                      />
                    </td>
                    <td className="num mono">{$(l.precio)}</td>
                    <td className="num mono">{$(l.cantidad * l.precio)}</td>
                    <td>
                      <button className="btn-quitar" title="Quitar (Supr)" onClick={() => quitarLinea(i)}>
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="pos-derecha">
          <div className="pos-total-card">
            <span className="pos-total-label">TOTAL</span>
            <span className="pos-total">$ {$(totalEstimado)}</span>
            <span className="chico pos-total-nota">
              {lineas.reduce((a, l) => a + l.cantidad, 0)} ítems · el total fiscal exacto se
              confirma al cobrar
            </span>
          </div>
          <button className="pos-cliente" onClick={() => setBuscaCliente(true)}>
            {cliente ? (
              <>
                <b>{cliente.nombre}</b>
                <span className="chico">({cliente.condicion_iva}) — F3 para cambiar</span>
              </>
            ) : (
              <>
                Consumidor Final <span className="chico">(F3: identificar cliente)</span>
              </>
            )}
          </button>
          {cliente && (
            <button className="btn btn-ghost btn-block" onClick={() => setCliente(null)}>
              Volver a Consumidor Final
            </button>
          )}
          <button
            className="btn btn-primary btn-block pos-cobrar"
            disabled={lineas.length === 0 || ocupado}
            onClick={() => void abrirCobro()}
          >
            COBRAR (F10)
          </button>
        </aside>
      </div>

      {resultados && (
        <BusquedaModal resultados={resultados} onElegir={elegirResultado} onCerrar={() => setResultados(null)} />
      )}
      {pickVariante && (
        <VarianteModal
          resultado={pickVariante}
          onElegir={(varianteId, precio, etiqueta) => {
            agregarLinea(
              { ...pickVariante, descripcion: `${pickVariante.descripcion} · ${etiqueta}` },
              multi ?? 1,
              varianteId,
              precio,
            );
            setMulti(null);
            setPickVariante(null);
          }}
          onCerrar={() => setPickVariante(null)}
        />
      )}
      {buscaCliente && (
        <ClienteModal
          onElegir={(c) => {
            setCliente(c);
            setBuscaCliente(false);
          }}
          onCerrar={() => setBuscaCliente(false)}
        />
      )}
      {cobro && (
        <CobroModal
          calculo={cobro}
          ocupado={ocupado}
          onConfirmar={confirmarVenta}
          onCerrar={() => setCobro(null)}
        />
      )}
      {verTickets && <TicketsModal sesion={sesion} onCerrar={() => setVerTickets(false)} />}
      {verCierre && (
        <CierreModal sesion={sesion} onCerrada={onCerrada} onCerrar={() => setVerCierre(false)} />
      )}
      {verDepto && (
        <DeptoModal
          deptos={deptos}
          onElegir={(d, importe) => {
            agregarDepto(d, importe);
            setVerDepto(false);
          }}
          onCerrar={() => setVerDepto(false)}
        />
      )}
    </div>
  );
}

function DeptoModal({
  deptos,
  onElegir,
  onCerrar,
}: {
  deptos: PosDepartamento[];
  onElegir: (d: PosDepartamento, importe: number) => void;
  onCerrar: () => void;
}) {
  const [sel, setSel] = useState<PosDepartamento | null>(deptos.length === 1 ? deptos[0] : null);
  const [importe, setImporte] = useState("");
  const monto = Number(importe.replace(",", "."));
  const valido = sel !== null && !Number.isNaN(monto) && monto > 0;

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Venta por departamento</h2>
        <div className="pos-resultados">
          {deptos.map((d) => (
            <button
              key={d.articulo_id}
              className={`pos-resultado${sel?.articulo_id === d.articulo_id ? " activo" : ""}`}
              onClick={() => setSel(d)}
            >
              <span className="mono chico">{d.codigo}</span>
              <span className="pos-res-desc">{d.descripcion}</span>
              <span className="chico">IVA {d.tasa_iva}%</span>
            </button>
          ))}
        </div>
        <label className="pos-campo">
          Importe (final, IVA incluido)
          <input
            className="input num"
            type="number"
            min="0"
            step="0.01"
            autoFocus
            value={importe}
            onChange={(e) => setImporte(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && valido) {
                e.preventDefault();
                onElegir(sel, monto);
              }
            }}
          />
        </label>
        <div className="pos-cobro-botones">
          <button className="btn btn-ghost" onClick={onCerrar}>
            Cancelar (Esc)
          </button>
          <button className="btn btn-primary" disabled={!valido} onClick={() => sel && onElegir(sel, monto)}>
            Agregar (Enter)
          </button>
        </div>
      </div>
    </div>
  );
}

// ===== Modales =====

function BusquedaModal({
  resultados,
  onElegir,
  onCerrar,
}: {
  resultados: PosResultadoBusqueda[];
  onElegir: (r: PosResultadoBusqueda) => void;
  onCerrar: () => void;
}) {
  const [idx, setIdx] = useState(0);
  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div
        className="modal pos-modal"
        onClick={(e) => e.stopPropagation()}
        tabIndex={-1}
        ref={(el) => el?.focus()}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") setIdx((i) => Math.min(resultados.length - 1, i + 1));
          else if (e.key === "ArrowUp") setIdx((i) => Math.max(0, i - 1));
          else if (e.key === "Enter") onElegir(resultados[idx]);
        }}
      >
        <h2>Resultados</h2>
        <div className="pos-resultados">
          {resultados.map((r, i) => (
            <button
              key={`${r.articulo_id}-${r.variante_id ?? ""}`}
              className={`pos-resultado${i === idx ? " activo" : ""}`}
              onClick={() => onElegir(r)}
            >
              <span className="mono chico">{r.codigo}</span>
              <span className="pos-res-desc">
                {r.descripcion}
                {r.tiene_variantes && !r.variante_id ? " …" : ""}
              </span>
              <span className="mono">$ {$(r.precio)}</span>
            </button>
          ))}
        </div>
        <p className="chico pos-ayuda">↑↓ para moverte, Enter para agregar, Esc para cerrar</p>
      </div>
    </div>
  );
}

function VarianteModal({
  resultado,
  onElegir,
  onCerrar,
}: {
  resultado: PosResultadoBusqueda;
  onElegir: (varianteId: string, precio: string, etiqueta: string) => void;
  onCerrar: () => void;
}) {
  const [idx, setIdx] = useState(0);
  const vs = resultado.variantes;
  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div
        className="modal pos-modal"
        onClick={(e) => e.stopPropagation()}
        tabIndex={-1}
        ref={(el) => el?.focus()}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") setIdx((i) => Math.min(vs.length - 1, i + 1));
          else if (e.key === "ArrowUp") setIdx((i) => Math.max(0, i - 1));
          else if (e.key === "Enter" && vs[idx]) onElegir(vs[idx].variante_id, vs[idx].precio, vs[idx].descripcion);
        }}
      >
        <h2>{resultado.descripcion} — elegí la variante</h2>
        <div className="pos-resultados">
          {vs.map((v, i) => (
            <button
              key={v.variante_id}
              className={`pos-resultado${i === idx ? " activo" : ""}`}
              onClick={() => onElegir(v.variante_id, v.precio, v.descripcion)}
            >
              <span className="pos-res-desc">{v.descripcion}</span>
              <span className="mono chico">{v.codigo_barras ?? ""}</span>
              <span className="mono">$ {$(v.precio)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ClienteModal({
  onElegir,
  onCerrar,
}: {
  onElegir: (c: ClienteSel) => void;
  onCerrar: () => void;
}) {
  const [q, setQ] = useState("");
  const [clientes, setClientes] = useState<Cliente[]>([]);

  useEffect(() => {
    const t = setTimeout(() => {
      void (async () => {
        if (q.trim().length < 2) {
          setClientes([]);
          return;
        }
        const r = await apiGet<Cliente[]>(`/clientes?q=${encodeURIComponent(q.trim())}&limit=8`);
        setClientes(r.data);
      })();
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Identificar cliente</h2>
        <input
          className="input"
          autoFocus
          placeholder="Nombre, CUIT o código…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="pos-resultados" style={{ marginTop: 12 }}>
          {clientes.map((c) => (
            <button
              key={c.id}
              className="pos-resultado"
              onClick={() =>
                onElegir({
                  id: c.id,
                  nombre: c.entidad.razon_social,
                  condicion_iva: c.entidad.condicion_iva,
                })
              }
            >
              <span className="pos-res-desc">{c.entidad.razon_social}</span>
              <span className="mono chico">{c.entidad.nro_documento ?? ""}</span>
              <span className="chip">{c.entidad.condicion_iva}</span>
            </button>
          ))}
          {q.trim().length >= 2 && clientes.length === 0 && (
            <p className="chico pos-ayuda">Sin resultados</p>
          )}
        </div>
        <p className="chico pos-ayuda">
          La letra del comprobante (A/B) la decide el sistema según la condición de IVA.
        </p>
      </div>
    </div>
  );
}

interface MedioForm {
  medio: string;
  importe: string;
  referencia: string;
}

export function CobroModal({
  calculo,
  ocupado,
  onConfirmar,
  onCerrar,
}: {
  calculo: PosCalculo;
  ocupado: boolean;
  onConfirmar: (
    medios: { medio: string; importe: string; referencia?: string }[],
    recibido?: string,
    vuelto?: string,
  ) => void;
  onCerrar: () => void;
}) {
  const total = Number(calculo.total);
  const [medios, setMedios] = useState<MedioForm[]>([
    { medio: "efectivo", importe: calculo.total, referencia: "" },
  ]);
  const [recibido, setRecibido] = useState("");

  const suma = medios.reduce((a, m) => a + Number(m.importe || 0), 0);
  const cuadra = Math.abs(suma - total) < 0.005;
  const efectivo = medios.filter((m) => m.medio === "efectivo").reduce((a, m) => a + Number(m.importe || 0), 0);
  const vuelto = recibido ? Number(recibido) - efectivo : 0;

  function setMedio(i: number, campo: keyof MedioForm, valor: string) {
    setMedios((prev) => prev.map((m, x) => (x === i ? { ...m, [campo]: valor } : m)));
  }

  function confirmar() {
    if (!cuadra || ocupado || (recibido !== "" && vuelto < -0.004)) return;
    onConfirmar(
      medios
        .filter((m) => Number(m.importe) > 0)
        .map((m) => ({
          medio: m.medio,
          importe: m.importe,
          referencia: m.referencia.trim() || undefined,
        })),
      recibido || undefined,
      vuelto > 0 ? vuelto.toFixed(2) : undefined,
    );
  }

  return (
    <div className="drawer-backdrop">
      <div
        className="modal pos-modal pos-cobro"
        tabIndex={-1}
        ref={(el) => el?.focus()}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.target as HTMLElement).tagName !== "BUTTON") {
            e.preventDefault();
            confirmar();
          }
        }}
      >
        <h2>
          Cobrar — {calculo.receptor_nombre} (letra {calculo.letra})
        </h2>
        <div className="pos-cobro-total">$ {$(calculo.total)}</div>
        {medios.map((m, i) => (
          <div key={i} className="pos-medio-fila">
            <select className="input" value={m.medio} onChange={(e) => setMedio(i, "medio", e.target.value)}>
              {Object.entries(MEDIOS_PAGO).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <input
              className="input num"
              type="number"
              min="0"
              step="0.01"
              value={m.importe}
              onChange={(e) => setMedio(i, "importe", e.target.value)}
            />
            <input
              className="input"
              placeholder="Referencia (cupón, operación…)"
              value={m.referencia}
              onChange={(e) => setMedio(i, "referencia", e.target.value)}
            />
            {medios.length > 1 && (
              <button className="btn-quitar" onClick={() => setMedios((p) => p.filter((_, x) => x !== i))}>
                ✕
              </button>
            )}
          </div>
        ))}
        <div className="pos-cobro-acciones">
          <button
            className="btn btn-ghost"
            onClick={() => setMedios((p) => [...p, { medio: "tarjeta", importe: Math.max(0, total - suma).toFixed(2), referencia: "" }])}
          >
            + Agregar medio
          </button>
          {!cuadra && (
            <span className="pos-error-inline">
              Suman $ {$(suma)} — {suma < total ? "faltan" : "sobran"} $ {$(Math.abs(total - suma))}
            </span>
          )}
        </div>
        {efectivo > 0 && (
          <div className="pos-vuelto">
            <label>
              Recibido en efectivo
              <input
                className="input num"
                type="number"
                min="0"
                step="0.01"
                autoFocus
                value={recibido}
                onChange={(e) => setRecibido(e.target.value)}
              />
            </label>
            <div className={`pos-vuelto-valor${vuelto < 0 ? " neg" : ""}`}>
              {recibido ? (vuelto >= 0 ? `Vuelto: $ ${$(vuelto)}` : `Faltan $ ${$(-vuelto)}`) : ""}
            </div>
          </div>
        )}
        <div className="pos-cobro-botones">
          <button className="btn btn-ghost" onClick={onCerrar}>
            Cancelar (Esc)
          </button>
          <button
            className="btn btn-primary"
            disabled={!cuadra || ocupado || (recibido !== "" && vuelto < -0.004)}
            onClick={confirmar}
          >
            {ocupado ? "Emitiendo…" : "Confirmar y emitir (Enter)"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TicketsModal({ sesion, onCerrar }: { sesion: PosSesion; onCerrar: () => void }) {
  const [tickets, setTickets] = useState<PosTicketResumen[]>([]);
  const [anulando, setAnulando] = useState<PosTicketResumen | null>(null);

  const cargar = useCallback(async () => {
    const r = await apiGet<PosTicketResumen[]>(`/pos/sesiones/${sesion.id}/ventas`);
    setTickets(r.data);
  }, [sesion.id]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function reimprimir(id: string) {
    const imp = await apiGet<ImpresionPayload>(`/ventas/comprobantes/${id}/impresion`);
    imprimirTicket(imp.data, sesion.ancho_ticket, undefined, sesion.cajero_nombre);
  }

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal modal-ancho pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Tickets de la sesión</h2>
        <div className="tabla-card">
          <table className="tabla">
            <thead>
              <tr>
                <th>Hora</th>
                <th>Comprobante</th>
                <th>Receptor</th>
                <th className="num">Total</th>
                <th></th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr key={t.id}>
                  <td className="mono">{t.emitido_at ? new Date(t.emitido_at).toLocaleTimeString("es-AR") : ""}</td>
                  <td>
                    {t.tipo_codigo} <span className="mono">{t.numero_formateado}</span>
                  </td>
                  <td>{t.receptor_nombre}</td>
                  <td className={`num mono${t.clase === "nota_credito" ? " neg" : ""}`}>$ {$(t.total)}</td>
                  <td>{t.anulada && <span className="chip chip-anulado">anulado</span>}</td>
                  <td className="pos-acciones-ticket">
                    <button className="btn btn-ghost" onClick={() => void reimprimir(t.id)}>
                      Reimprimir
                    </button>
                    {t.clase === "factura" && !t.anulada && (
                      <button className="btn btn-ghost" onClick={() => setAnulando(t)}>
                        Anular
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {tickets.length === 0 && (
                <tr>
                  <td colSpan={6} className="pos-vacio">
                    Todavía no hay ventas en esta sesión
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {anulando && (
          <AnularModal
            ticket={anulando}
            sesion={sesion}
            onListo={() => {
              setAnulando(null);
              void cargar();
            }}
            onCerrar={() => setAnulando(null)}
          />
        )}
      </div>
    </div>
  );
}

function AnularModal({
  ticket,
  sesion,
  onListo,
  onCerrar,
}: {
  ticket: PosTicketResumen;
  sesion: PosSesion;
  onListo: () => void;
  onCerrar: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function anular() {
    if (ocupado) return;
    setOcupado(true);
    setError(null);
    try {
      const nc = await apiPost<Comprobante>(`/pos/ventas/${ticket.id}/anular`, {
        sesion_id: sesion.id,
        supervisor_email: email,
        supervisor_password: password,
        motivo: motivo.trim() || null,
      });
      try {
        const imp = await apiGet<ImpresionPayload>(`/ventas/comprobantes/${nc.id}/impresion`);
        imprimirTicket(imp.data, sesion.ancho_ticket, undefined, sesion.cajero_nombre);
      } catch {
        /* la NC quedó emitida igual */
      }
      onListo();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo anular");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>
          Anular {ticket.tipo_codigo} {ticket.numero_formateado}
        </h2>
        <p className="chico pos-ayuda">
          Requiere autorización de un supervisor. Se emite la nota de crédito espejo y se
          devuelve el stock — el patrón del legacy, con firma fiscal.
        </p>
        {error && <div className="login-error">{error}</div>}
        <label className="pos-campo">
          Email del supervisor
          <input className="input" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="pos-campo">
          Contraseña
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void anular()}
          />
        </label>
        <label className="pos-campo">
          Motivo (opcional)
          <input className="input" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        </label>
        <div className="pos-cobro-botones">
          <button className="btn btn-ghost" onClick={onCerrar}>
            Cancelar
          </button>
          <button className="btn btn-primary" disabled={!email || !password || ocupado} onClick={() => void anular()}>
            {ocupado ? "Anulando…" : "Autorizar anulación"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function CierreModal({
  sesion,
  onCerrada,
  onCerrar,
}: {
  sesion: PosSesion;
  onCerrada: () => void;
  onCerrar: () => void;
}) {
  const [resumen, setResumen] = useState<PosResumen | null>(null);
  const [contado, setContado] = useState("");
  const [obs, setObs] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [resultado, setResultado] = useState<PosSesion | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await apiGet<PosResumen>(`/pos/sesiones/${sesion.id}/resumen`);
      setResumen(r.data);
    })();
  }, [sesion.id]);

  async function cerrar() {
    if (ocupado) return;
    setOcupado(true);
    setError(null);
    try {
      const s = await apiPost<PosSesion>(`/pos/sesiones/${sesion.id}/cerrar`, {
        efectivo_contado: contado === "" ? null : contado,
        observaciones: obs.trim() || null,
      });
      setResultado(s);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cerrar la sesión");
    } finally {
      setOcupado(false);
    }
  }

  if (resultado) {
    const dif = Number(resultado.diferencia ?? 0);
    return (
      <div className="drawer-backdrop">
        <div className="modal pos-modal">
          <h2>Caja cerrada</h2>
          <div className="pos-arqueo">
            <div className="linea-arqueo">
              <span>Efectivo teórico</span>
              <b className="mono">$ {$(resultado.efectivo_teorico)}</b>
            </div>
            {resultado.efectivo_contado !== null && (
              <>
                <div className="linea-arqueo">
                  <span>Efectivo contado</span>
                  <b className="mono">$ {$(resultado.efectivo_contado)}</b>
                </div>
                <div className={`linea-arqueo${dif !== 0 ? (dif > 0 ? " pos" : " neg") : ""}`}>
                  <span>Diferencia</span>
                  <b className="mono">$ {$(resultado.diferencia)}</b>
                </div>
              </>
            )}
          </div>
          <button className="btn btn-primary btn-block" onClick={onCerrada}>
            Terminar turno
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Cierre de caja — arqueo</h2>
        {error && <div className="login-error">{error}</div>}
        {!resumen ? (
          <p>Cargando…</p>
        ) : (
          <>
            <div className="pos-arqueo">
              <div className="linea-arqueo">
                <span>Fondo inicial</span>
                <span className="mono">$ {$(resumen.fondo_inicial)}</span>
              </div>
              <div className="linea-arqueo">
                <span>
                  Ventas ({resumen.cantidad_tickets} tickets
                  {resumen.anulaciones > 0 ? `, ${resumen.anulaciones} anulados` : ""})
                </span>
                <span className="mono">$ {$(resumen.total_ventas)}</span>
              </div>
              {resumen.medios.map((m) => (
                <div key={m.medio} className="linea-arqueo chico">
                  <span>· {MEDIOS_PAGO[m.medio] ?? m.medio}</span>
                  <span className="mono">$ {$(m.total)}</span>
                </div>
              ))}
              <div className="linea-arqueo total">
                <span>Efectivo teórico en cajón</span>
                <b className="mono">$ {$(resumen.efectivo_teorico)}</b>
              </div>
            </div>
            <label className="pos-campo">
              Efectivo contado (arqueo físico)
              <input
                className="input num"
                type="number"
                min="0"
                step="0.01"
                autoFocus
                value={contado}
                onChange={(e) => setContado(e.target.value)}
              />
            </label>
            <label className="pos-campo">
              Observaciones
              <input className="input" value={obs} onChange={(e) => setObs(e.target.value)} />
            </label>
            <div className="pos-cobro-botones">
              <button className="btn btn-ghost" onClick={onCerrar}>
                Seguir vendiendo
              </button>
              <button className="btn btn-primary" disabled={ocupado} onClick={() => void cerrar()}>
                {ocupado ? "Cerrando…" : "Cerrar caja"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
