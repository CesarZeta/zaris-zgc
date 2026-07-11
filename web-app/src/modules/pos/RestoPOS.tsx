// POS Resto (F12-d) — grilla de mesas, comandas, cocina, delivery y mozos.
// La comanda vive en el POS (mandato: nada llega a la gestión salvo la venta
// final). Cerrar mesa = cobro con la pantalla del POS actual → factura fiscal
// vía emitir_core en el backend.

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from "../../lib/api";
import type {
  Cliente,
  ImpresionPayload,
  PosCalculo,
  PosCocina,
  PosComanda,
  PosMesa,
  PosReporteMozo,
  PosResultadoBusqueda,
  PosSesion,
  Comprobante,
} from "../../lib/types";
import AddressSearch from "../../components/AddressSearch";
import { useDialogos } from "../../components/dialogos";
import { CierreModal, CobroModal, SalirCajaBoton } from "./POSPage";
import { imprimirTicket } from "./ticket";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const $ = (v: string | number | null | undefined) => fmt.format(Number(v ?? 0));
const hora = (iso: string | null) =>
  iso ? new Date(iso).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" }) : "";

const TIPO_NOMBRE: Record<string, string> = {
  mesa: "Mesa",
  delivery: "Delivery",
  takeaway: "Para llevar",
};
const ENVIO_NOMBRE: Record<string, string> = {
  en_preparacion: "En preparación",
  despachado: "Despachado",
  entregado: "Entregado",
};

function esc(s: string | null | undefined): string {
  return (s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Comanda a cocina: impresión angosta por el diálogo del navegador (patrón ticket)
function imprimirComanda(c: PosCocina) {
  const items = c.items
    .map(
      (i) =>
        `<div class="item"><b>${fmt.format(Number(i.cantidad))} × ${esc(i.descripcion)}</b>${
          i.observaciones ? `<div class="obs">» ${esc(i.observaciones)}</div>` : ""
        }</div>`,
    )
    .join("");
  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Comanda</title>
<style>
  body { font-family: monospace; width: 72mm; margin: 0; padding: 4mm; font-size: 12px; }
  h1 { font-size: 16px; text-align: center; margin: 0 0 4px; }
  .enc { text-align: center; border-bottom: 1px dashed #000; padding-bottom: 4px; margin-bottom: 6px; }
  .item { margin-bottom: 4px; font-size: 13px; }
  .obs { font-size: 11px; padding-left: 8px; }
</style></head><body>
  <h1>COCINA</h1>
  <div class="enc">${esc(c.mesa ?? TIPO_NOMBRE[c.tipo] ?? c.tipo)}<br/>
  ${new Date(c.hora).toLocaleTimeString("es-AR")} · ${esc(c.mozo_nombre)}</div>
  ${items}
</body></html>`;
  const w = window.open("", "_blank", "width=380,height=520");
  if (!w) return;
  w.document.write(html);
  w.document.close();
  w.focus();
  setTimeout(() => {
    w.print();
    w.close();
  }, 150);
}

export default function RestoPOS({
  sesion,
  onCerrada,
}: {
  sesion: PosSesion;
  onCerrada: () => void;
}) {
  const [tab, setTab] = useState<"mesas" | "pedidos" | "mozos">("mesas");
  const [mesas, setMesas] = useState<PosMesa[]>([]);
  const [pedidos, setPedidos] = useState<PosComanda[]>([]);
  const [comanda, setComanda] = useState<PosComanda | null>(null);
  const [nuevoPedido, setNuevoPedido] = useState(false);
  const [verCierre, setVerCierre] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      const [m, p] = await Promise.all([
        apiGet<PosMesa[]>("/pos/resto/mesas"),
        apiGet<PosComanda[]>("/pos/resto/comandas?estado=abierta"),
      ]);
      setMesas(m.data);
      setPedidos(p.data.filter((c) => c.tipo !== "mesa"));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cargar el salón");
    }
  }, []);

  useEffect(() => {
    void cargar();
    const t = setInterval(() => void cargar(), 30000);
    return () => clearInterval(t);
  }, [cargar]);

  async function abrirMesa(mesa: PosMesa) {
    setError(null);
    if (mesa.comanda_id) {
      const { data } = await apiGet<PosComanda>(`/pos/resto/comandas/${mesa.comanda_id}`);
      setComanda(data);
      return;
    }
    try {
      const c = await apiPost<PosComanda>("/pos/resto/comandas", {
        caja_id: sesion.caja_id,
        tipo: "mesa",
        mesa_id: mesa.id,
      });
      setComanda(c);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo abrir la mesa");
      void cargar();
    }
  }

  const salones = [...new Set(mesas.map((m) => m.salon_nombre))];

  return (
    <div className="pos-pantalla">
      <header className="pos-topbar">
        <div className="pos-logo">
          Z<span>GC</span> RESTO
        </div>
        <div className="pos-caja-info">
          <b>{sesion.caja_nombre}</b> · {sesion.cajero_nombre}
        </div>
        <div className="pos-topbar-botones">
          <button
            className={`btn btn-ghost${tab === "mesas" ? " activo" : ""}`}
            onClick={() => setTab("mesas")}
          >
            Mesas
          </button>
          <button
            className={`btn btn-ghost${tab === "pedidos" ? " activo" : ""}`}
            onClick={() => setTab("pedidos")}
          >
            Pedidos ({pedidos.length})
          </button>
          <button
            className={`btn btn-ghost${tab === "mozos" ? " activo" : ""}`}
            onClick={() => setTab("mozos")}
          >
            Mozos
          </button>
          <button className="btn btn-ghost" onClick={() => setVerCierre(true)}>
            Cierre (F8)
          </button>
          <SalirCajaBoton className="btn btn-ghost" label="Salir" />
        </div>
      </header>

      <div className="pos-cuerpo" style={{ display: "block", overflow: "auto", padding: "var(--space-5)" }}>
        {error && <div className="pos-error">{error}</div>}

        {tab === "mesas" && (
          <>
            {mesas.length === 0 && (
              <p className="pos-ayuda">
                No hay mesas configuradas. Crealas en{" "}
                <Link to="/configuracion">Configuración → Salones y mesas</Link>.
              </p>
            )}
            {salones.map((salon) => (
              <div key={salon}>
                <div className="seccion">{salon}</div>
                <div className="pos-cajas-grid" style={{ marginBottom: "var(--space-5)" }}>
                  {mesas
                    .filter((m) => m.salon_nombre === salon)
                    .map((m) => (
                      <button
                        key={m.id}
                        className={`pos-caja-card${m.ocupada ? " activa" : ""}`}
                        onClick={() => void abrirMesa(m)}
                      >
                        <b>
                          Mesa {m.numero}
                          {m.nombre ? ` · ${m.nombre}` : ""}
                        </b>
                        {m.ocupada ? (
                          <>
                            <span className="chico">
                              {m.mozo_nombre} · desde {hora(m.abierta_at)}
                            </span>
                            <span className="mono">$ {$(m.comanda_total)}</span>
                          </>
                        ) : (
                          <span className="chico">libre</span>
                        )}
                      </button>
                    ))}
                </div>
              </div>
            ))}
          </>
        )}

        {tab === "pedidos" && (
          <>
            <div className="toolbar">
              <button className="btn btn-primary" onClick={() => setNuevoPedido(true)}>
                + Nuevo pedido (delivery / para llevar)
              </button>
            </div>
            <div className="pos-cajas-grid">
              {pedidos.map((p) => (
                <button key={p.id} className="pos-caja-card activa" onClick={() => setComanda(p)}>
                  <b>
                    {TIPO_NOMBRE[p.tipo]} · {p.cliente_nombre ?? "sin nombre"}
                  </b>
                  <span className="chico">
                    {hora(p.abierta_at)}
                    {p.envio_estado ? ` · ${ENVIO_NOMBRE[p.envio_estado]}` : ""}
                  </span>
                  <span className="mono">$ {$(p.total)}</span>
                </button>
              ))}
              {pedidos.length === 0 && <p className="pos-ayuda">Sin pedidos abiertos</p>}
            </div>
          </>
        )}

        {tab === "mozos" && <MozosTab />}
      </div>

      {comanda && (
        <ComandaPanel
          sesion={sesion}
          comandaInicial={comanda}
          onCerrar={(refrescar) => {
            setComanda(null);
            if (refrescar) void cargar();
          }}
        />
      )}
      {nuevoPedido && (
        <NuevoPedidoModal
          sesion={sesion}
          onCreada={(c) => {
            setNuevoPedido(false);
            setComanda(c);
            void cargar();
          }}
          onCerrar={() => setNuevoPedido(false)}
        />
      )}
      {verCierre && (
        <CierreModal sesion={sesion} onCerrada={onCerrada} onCerrar={() => setVerCierre(false)} />
      )}
    </div>
  );
}

// ===== Comanda (cuenta abierta) =====

function ComandaPanel({
  sesion,
  comandaInicial,
  onCerrar,
}: {
  sesion: PosSesion;
  comandaInicial: PosComanda;
  onCerrar: (refrescar: boolean) => void;
}) {
  const [comanda, setComanda] = useState<PosComanda>(comandaInicial);
  const [q, setQ] = useState("");
  const [resultados, setResultados] = useState<PosResultadoBusqueda[]>([]);
  const [obsItem, setObsItem] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [cobro, setCobro] = useState<PosCalculo | null>(null);
  const [cliente, setCliente] = useState<{ id: string; nombre: string } | null>(null);
  const [buscaCliente, setBuscaCliente] = useState(false);
  const [mover, setMover] = useState(false);
  const [unir, setUnir] = useState(false);
  const [propina, setPropina] = useState(String(Number(comandaInicial.propina_pct) || ""));
  const { confirmar, dialogos } = useDialogos();

  const abierta = comanda.estado === "abierta";

  useEffect(() => {
    if (q.trim().length < 2) {
      setResultados([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const r = await apiGet<PosResultadoBusqueda[]>(
          `/pos/buscar?q=${encodeURIComponent(q.trim())}&caja_id=${comanda.caja_id}`,
        );
        setResultados(r.data);
      } catch {
        setResultados([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q, comanda.caja_id]);

  function avisar(msg: string) {
    setError(msg);
    setTimeout(() => setError(null), 4000);
  }

  async function agregar(r: PosResultadoBusqueda, varianteId?: string) {
    setQ("");
    setResultados([]);
    try {
      const c = await apiPost<PosComanda>(`/pos/resto/comandas/${comanda.id}/items`, [
        {
          articulo_id: r.articulo_id,
          variante_id: varianteId ?? r.variante_id,
          cantidad: r.cantidad ?? "1",
          observaciones: obsItem.trim() || null,
        },
      ]);
      setComanda(c);
      setObsItem("");
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo agregar");
    }
  }

  async function cambiarCantidad(itemId: string, cantidad: string) {
    const cant = Number(cantidad.replace(",", "."));
    if (Number.isNaN(cant) || cant <= 0) return;
    try {
      const c = await apiPatch<PosComanda>(
        `/pos/resto/comandas/${comanda.id}/items/${itemId}`,
        { cantidad: String(cant) },
      );
      setComanda(c);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo modificar");
    }
  }

  async function quitar(itemId: string) {
    try {
      await apiDelete(`/pos/resto/comandas/${comanda.id}/items/${itemId}`);
      const { data } = await apiGet<PosComanda>(`/pos/resto/comandas/${comanda.id}`);
      setComanda(data);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo quitar");
    }
  }

  async function enviarCocina() {
    setOcupado(true);
    try {
      const cocina = await apiPost<PosCocina>(`/pos/resto/comandas/${comanda.id}/enviar-cocina`, {});
      imprimirComanda(cocina);
      const { data } = await apiGet<PosComanda>(`/pos/resto/comandas/${comanda.id}`);
      setComanda(data);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo enviar a cocina");
    } finally {
      setOcupado(false);
    }
  }

  async function anular() {
    if (!(await confirmar("¿Anular la comanda? La mesa queda libre y no se factura nada."))) return;
    try {
      await apiPost(`/pos/resto/comandas/${comanda.id}/anular`, {});
      onCerrar(true);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo anular");
    }
  }

  async function abrirCobro() {
    if (comanda.items.length === 0 || ocupado) return;
    setOcupado(true);
    try {
      const calculo = await apiPost<PosCalculo>("/pos/ventas/calcular", {
        caja_id: sesion.caja_id,
        cliente_id: cliente?.id ?? null,
        items: comanda.items.map((i) => ({
          articulo_id: i.articulo_id,
          variante_id: i.variante_id,
          cantidad: i.cantidad,
        })),
      });
      setCobro(calculo);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo calcular el cobro");
    } finally {
      setOcupado(false);
    }
  }

  async function confirmarCobro(
    medios: { medio: string; importe: string; referencia?: string }[],
    recibido?: string,
    vuelto?: string,
  ) {
    setOcupado(true);
    try {
      const vta = await apiPost<Comprobante>(`/pos/resto/comandas/${comanda.id}/cobrar`, {
        sesion_id: sesion.id,
        cliente_id: cliente?.id ?? null,
        medios,
        propina_pct: propina !== "" ? propina : null,
      });
      setCobro(null);
      try {
        const imp = await apiGet<ImpresionPayload>(`/ventas/comprobantes/${vta.id}/impresion`);
        imprimirTicket(imp.data, sesion.ancho_ticket, { medios, recibido, vuelto }, sesion.cajero_nombre);
      } catch {
        /* la venta quedó emitida igual */
      }
      onCerrar(true);
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "No se pudo cobrar");
      setCobro(null);
    } finally {
      setOcupado(false);
    }
  }

  const pendientes = comanda.items.filter((i) => i.estado_cocina === "pendiente").length;
  const titulo =
    comanda.tipo === "mesa"
      ? `${comanda.salon_nombre ?? ""} · Mesa ${comanda.mesa_numero ?? ""}`
      : `${TIPO_NOMBRE[comanda.tipo]} · ${comanda.cliente_nombre ?? "sin nombre"}`;

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(true)}>
      <div className="modal modal-ancho pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>
          {titulo} <span className="chico">— {comanda.mozo_nombre}</span>
        </h2>
        {comanda.tipo === "delivery" && (
          <p className="chico">
            {comanda.domicilio ?? "sin domicilio"}
            {comanda.localidad ? `, ${comanda.localidad}` : ""} · {comanda.telefono ?? "sin tel."}
            {comanda.envio_estado && abierta && (
              <>
                {" · "}
                <select
                  className="input"
                  style={{ width: "auto", display: "inline-block" }}
                  value={comanda.envio_estado}
                  onChange={(e) =>
                    void apiPatch<PosComanda>(`/pos/resto/comandas/${comanda.id}`, {
                      envio_estado: e.target.value,
                    }).then(setComanda)
                  }
                >
                  {Object.entries(ENVIO_NOMBRE).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </>
            )}
          </p>
        )}
        {error && <div className="login-error">{error}</div>}

        {abierta && (
          <div className="pos-scan" style={{ position: "relative" }}>
            <input
              className="input"
              placeholder="Buscar plato / artículo…"
              value={q}
              autoFocus
              onChange={(e) => setQ(e.target.value)}
            />
            <input
              className="input"
              placeholder="Obs. («sin sal», «jugoso»)"
              value={obsItem}
              onChange={(e) => setObsItem(e.target.value)}
            />
            {resultados.length > 0 && (
              <div className="buscador-opciones" style={{ top: "100%" }}>
                {resultados.map((r) => (
                  <button
                    key={`${r.articulo_id}-${r.variante_id ?? ""}`}
                    type="button"
                    onClick={() => void agregar(r)}
                  >
                    <span className="mono">{r.codigo}</span> {r.descripcion} — $ {$(r.precio)}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="tabla-card" style={{ marginTop: "var(--space-4)" }}>
          <table className="tabla">
            <thead>
              <tr>
                <th className="num">Cant.</th>
                <th>Detalle</th>
                <th className="num">Importe</th>
                <th>Cocina</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {comanda.items.map((i) => (
                <tr key={i.id}>
                  <td className="num" style={{ width: 90 }}>
                    {abierta ? (
                      <input
                        className="input pos-cant"
                        type="number"
                        min="0.001"
                        step="1"
                        value={Number(i.cantidad)}
                        onChange={(e) => void cambiarCantidad(i.id, e.target.value)}
                      />
                    ) : (
                      <span className="mono">{Number(i.cantidad)}</span>
                    )}
                  </td>
                  <td>
                    {i.descripcion}
                    {i.observaciones && <span className="chico"> » {i.observaciones}</span>}
                  </td>
                  <td className="num mono">$ {$(i.importe)}</td>
                  <td>
                    <span className={`chip ${i.estado_cocina === "enviado" ? "chip-emitido" : "chip-borrador"}`}>
                      {i.estado_cocina}
                    </span>
                  </td>
                  <td>
                    {abierta && (
                      <button className="btn-quitar" onClick={() => void quitar(i.id)}>
                        ✕
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {comanda.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="pos-vacio">
                    Buscá un plato para empezar la comanda
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="pos-arqueo" style={{ marginTop: "var(--space-4)" }}>
          <div className="linea-arqueo total">
            <span>Total de la cuenta</span>
            <b className="mono">$ {$(comanda.total)}</b>
          </div>
          {propina !== "" && Number(propina) > 0 && (
            <div className="linea-arqueo chico">
              <span>Propina sugerida ({propina}% — no integra la factura)</span>
              <span className="mono">$ {$((Number(comanda.total) * Number(propina)) / 100)}</span>
            </div>
          )}
        </div>

        {abierta && (
          <>
            <div className="fila" style={{ marginTop: "var(--space-4)", alignItems: "end" }}>
              <button className="pos-cliente" style={{ flex: 1 }} onClick={() => setBuscaCliente(true)}>
                {cliente ? <b>{cliente.nombre}</b> : "Consumidor Final (identificar cliente)"}
              </button>
              <div className="field" style={{ maxWidth: 130 }}>
                <label>Propina %</label>
                <input
                  className="input num"
                  type="number"
                  min="0"
                  max="100"
                  value={propina}
                  onChange={(e) => setPropina(e.target.value)}
                />
              </div>
            </div>
            <div className="pos-cobro-botones" style={{ flexWrap: "wrap" }}>
              <button className="btn btn-ghost" disabled={pendientes === 0 || ocupado} onClick={() => void enviarCocina()}>
                Enviar a cocina ({pendientes})
              </button>
              {comanda.tipo === "mesa" && (
                <>
                  <button className="btn btn-ghost" onClick={() => setMover(true)}>
                    Mover mesa
                  </button>
                  <button className="btn btn-ghost" onClick={() => setUnir(true)}>
                    Unir mesa
                  </button>
                </>
              )}
              <button className="btn btn-ghost" onClick={() => void anular()}>
                Anular
              </button>
              <button
                className="btn btn-primary"
                disabled={comanda.items.length === 0 || ocupado}
                onClick={() => void abrirCobro()}
              >
                COBRAR
              </button>
            </div>
          </>
        )}

        {cobro && (
          <CobroModal
            calculo={cobro}
            ocupado={ocupado}
            onConfirmar={confirmarCobro}
            onCerrar={() => setCobro(null)}
          />
        )}
        {buscaCliente && (
          <ClientePickerModal
            onElegir={(c) => {
              setCliente(c);
              setBuscaCliente(false);
            }}
            onCerrar={() => setBuscaCliente(false)}
          />
        )}
        {mover && (
          <MesaPickerModal
            titulo="Mover a la mesa…"
            soloLibres
            onElegir={async (mesa) => {
              try {
                const c = await apiPost<PosComanda>(`/pos/resto/comandas/${comanda.id}/mover`, {
                  mesa_id: mesa.id,
                });
                setComanda(c);
                setMover(false);
              } catch (e) {
                avisar(e instanceof ApiError ? e.message : "No se pudo mover");
                setMover(false);
              }
            }}
            onCerrar={() => setMover(false)}
          />
        )}
        {unir && (
          <MesaPickerModal
            titulo="Traer la cuenta de la mesa…"
            soloOcupadas
            excluirComanda={comanda.id}
            onElegir={async (mesa) => {
              if (!mesa.comanda_id) return;
              try {
                const c = await apiPost<PosComanda>(`/pos/resto/comandas/${comanda.id}/unir`, {
                  desde_comanda_id: mesa.comanda_id,
                });
                setComanda(c);
                setUnir(false);
              } catch (e) {
                avisar(e instanceof ApiError ? e.message : "No se pudo unir");
                setUnir(false);
              }
            }}
            onCerrar={() => setUnir(false)}
          />
        )}
        {dialogos}
      </div>
    </div>
  );
}

// ===== Modales auxiliares =====

function ClientePickerModal({
  onElegir,
  onCerrar,
}: {
  onElegir: (c: { id: string; nombre: string }) => void;
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
              onClick={() => onElegir({ id: c.id, nombre: c.entidad.razon_social })}
            >
              <span className="pos-res-desc">{c.entidad.razon_social}</span>
              <span className="mono chico">{c.entidad.nro_documento ?? ""}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MesaPickerModal({
  titulo,
  soloLibres,
  soloOcupadas,
  excluirComanda,
  onElegir,
  onCerrar,
}: {
  titulo: string;
  soloLibres?: boolean;
  soloOcupadas?: boolean;
  excluirComanda?: string;
  onElegir: (m: PosMesa) => void;
  onCerrar: () => void;
}) {
  const [mesas, setMesas] = useState<PosMesa[]>([]);

  useEffect(() => {
    void apiGet<PosMesa[]>("/pos/resto/mesas").then(({ data }) => {
      let lista = data;
      if (soloLibres) lista = lista.filter((m) => !m.ocupada);
      if (soloOcupadas) lista = lista.filter((m) => m.ocupada && m.comanda_id !== excluirComanda);
      setMesas(lista);
    });
  }, [soloLibres, soloOcupadas, excluirComanda]);

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>{titulo}</h2>
        <div className="pos-resultados">
          {mesas.map((m) => (
            <button key={m.id} className="pos-resultado" onClick={() => onElegir(m)}>
              <span className="pos-res-desc">
                {m.salon_nombre} · Mesa {m.numero}
              </span>
              {m.ocupada && <span className="mono">$ {$(m.comanda_total)}</span>}
            </button>
          ))}
          {mesas.length === 0 && <p className="chico pos-ayuda">No hay mesas disponibles</p>}
        </div>
      </div>
    </div>
  );
}

function NuevoPedidoModal({
  sesion,
  onCreada,
  onCerrar,
}: {
  sesion: PosSesion;
  onCreada: (c: PosComanda) => void;
  onCerrar: () => void;
}) {
  const [tipo, setTipo] = useState<"delivery" | "takeaway">("delivery");
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [domicilio, setDomicilio] = useState("");
  const [localidad, setLocalidad] = useState("");
  const [coords, setCoords] = useState<{ lat: number | null; lon: number | null }>({
    lat: null,
    lon: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function crear() {
    setOcupado(true);
    setError(null);
    try {
      const c = await apiPost<PosComanda>("/pos/resto/comandas", {
        caja_id: sesion.caja_id,
        tipo,
        cliente_nombre: nombre.trim() || null,
        telefono: telefono.trim() || null,
        domicilio: tipo === "delivery" ? domicilio.trim() || null : null,
        localidad: tipo === "delivery" ? localidad.trim() || null : null,
        latitud: tipo === "delivery" ? coords.lat : null,
        longitud: tipo === "delivery" ? coords.lon : null,
      });
      onCreada(c);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo crear el pedido");
      setOcupado(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal pos-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Nuevo pedido</h2>
        {error && <div className="login-error">{error}</div>}
        <div className="fila">
          <label className="check">
            <input type="radio" checked={tipo === "delivery"} onChange={() => setTipo("delivery")} />
            Delivery
          </label>
          <label className="check">
            <input type="radio" checked={tipo === "takeaway"} onChange={() => setTipo("takeaway")} />
            Para llevar
          </label>
        </div>
        <label className="pos-campo">
          Cliente
          <input className="input" autoFocus value={nombre} onChange={(e) => setNombre(e.target.value)} />
        </label>
        <label className="pos-campo">
          Teléfono
          <input className="input" value={telefono} onChange={(e) => setTelefono(e.target.value)} />
        </label>
        {tipo === "delivery" && (
          <>
            <div className="field">
              <label>Domicilio de entrega (buscador OSM)</label>
              <AddressSearch
                onElegir={(d) => {
                  setDomicilio(d.domicilio);
                  setLocalidad(d.localidad);
                  setCoords({ lat: d.latitud, lon: d.longitud });
                }}
              />
            </div>
            <label className="pos-campo">
              Domicilio
              <input className="input" value={domicilio} onChange={(e) => setDomicilio(e.target.value)} />
            </label>
            <label className="pos-campo">
              Localidad
              <input className="input" value={localidad} onChange={(e) => setLocalidad(e.target.value)} />
            </label>
          </>
        )}
        <div className="pos-cobro-botones">
          <button className="btn btn-ghost" onClick={onCerrar}>
            Cancelar
          </button>
          <button className="btn btn-primary" disabled={ocupado} onClick={() => void crear()}>
            Abrir pedido
          </button>
        </div>
      </div>
    </div>
  );
}

function MozosTab() {
  const hoy = new Date().toISOString().slice(0, 10);
  const [desde, setDesde] = useState(hoy);
  const [hasta, setHasta] = useState(hoy);
  const [filas, setFilas] = useState<PosReporteMozo[]>([]);

  useEffect(() => {
    void apiGet<PosReporteMozo[]>(`/pos/resto/reporte-mozos?desde=${desde}&hasta=${hasta}`).then(
      ({ data }) => setFilas(data),
    );
  }, [desde, hasta]);

  return (
    <>
      <div className="toolbar">
        <input className="input" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        <input className="input" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
      </div>
      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Mozo</th>
              <th className="num">Comandas</th>
              <th className="num">Total vendido</th>
              <th className="num">Propina estimada</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.mozo_id}>
                <td>{f.mozo_nombre}</td>
                <td className="num mono">{f.comandas}</td>
                <td className="num mono">$ {$(f.total_vendido)}</td>
                <td className="num mono">$ {$(f.propina_estimada)}</td>
              </tr>
            ))}
            {filas.length === 0 && (
              <tr>
                <td colSpan={4} className="pos-vacio">
                  Sin ventas cerradas en el rango
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
