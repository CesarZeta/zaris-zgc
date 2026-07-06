import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type { Articulo, Deposito, Movimiento, StockFila, Variante } from "../../lib/types";
import { useDialogos } from "../../components/dialogos";

const POR_PAGINA = 50;
const fmtCant = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 3 });
const fmtFecha = new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" });

const TIPOS_MOV: Record<string, string> = {
  inicial: "Saldo inicial",
  ajuste: "Ajuste",
  transferencia: "Transferencia",
  compra: "Compra",
  venta: "Venta",
};

// ---------- buscador de artículo (autocomplete liviano) ----------

function BuscadorArticulo({
  onElegir,
  elegido,
}: {
  onElegir: (a: Articulo | null) => void;
  elegido: Articulo | null;
}) {
  const [q, setQ] = useState("");
  const [opciones, setOpciones] = useState<Articulo[]>([]);

  useEffect(() => {
    if (elegido || q.trim().length < 2) {
      setOpciones([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await apiGet<Articulo[]>(
          `/articulos?q=${encodeURIComponent(q)}&limit=8`,
        );
        setOpciones(data);
      } catch {
        setOpciones([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q, elegido]);

  if (elegido) {
    return (
      <div className="buscador-elegido">
        <span className="mono">{elegido.codigo}</span> {elegido.descripcion}
        <button type="button" className="mini-btn" onClick={() => onElegir(null)}>
          cambiar
        </button>
      </div>
    );
  }
  return (
    <div className="buscador">
      <input
        className="input"
        placeholder="Buscar artículo por descripción o código…"
        value={q}
        onChange={(ev) => setQ(ev.target.value)}
        autoFocus
      />
      {opciones.length > 0 && (
        <div className="buscador-opciones">
          {opciones.map((a) => (
            <button key={a.id} type="button" onClick={() => onElegir(a)}>
              <span className="mono">{a.codigo}</span> {a.descripcion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// selector de variante: aparece solo si el artículo tiene variantes activas
function SelectorVariante({
  articulo,
  varianteId,
  onCambiar,
  inicial,
}: {
  articulo: Articulo | null;
  varianteId: string;
  onCambiar: (id: string, requerida: boolean) => void;
  inicial?: string | null;
}) {
  const [variantes, setVariantes] = useState<Variante[]>([]);

  useEffect(() => {
    if (!articulo) {
      setVariantes([]);
      onCambiar("", false);
      return;
    }
    void apiGet<Variante[]>(`/articulos/${articulo.id}/variantes`).then(({ data }) => {
      const activas = data.filter((v) => v.activo);
      setVariantes(activas);
      const preseleccion = inicial && activas.some((v) => v.id === inicial) ? inicial : "";
      onCambiar(preseleccion, activas.length > 0);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [articulo?.id]);

  if (!articulo || variantes.length === 0) return null;
  return (
    <div className="field">
      <label>Variante *</label>
      <select
        className="select"
        value={varianteId}
        onChange={(ev) => onCambiar(ev.target.value, true)}
      >
        <option value="">— elegir —</option>
        {variantes.map((v) => (
          <option key={v.id} value={v.id}>
            {v.etiqueta}
          </option>
        ))}
      </select>
    </div>
  );
}

// ---------- modal de ajuste ----------

function AjusteModal({
  depositos,
  inicial,
  onCerrar,
}: {
  depositos: Deposito[];
  inicial: StockFila | null;
  onCerrar: (refrescar: boolean) => void;
}) {
  const [articulo, setArticulo] = useState<Articulo | null>(null);
  const [depositoId, setDepositoId] = useState(inicial?.deposito_id ?? depositos[0]?.id ?? "");
  const [varianteId, setVarianteId] = useState("");
  const [varianteRequerida, setVarianteRequerida] = useState(false);
  const [modo, setModo] = useState<"recuento" | "delta">("recuento");
  const [cantidad, setCantidad] = useState("");
  const [obs, setObs] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  // si vino desde una fila del listado, precargar el artículo
  useEffect(() => {
    if (!inicial) return;
    void apiGet<Articulo>(`/articulos/${inicial.articulo_id}`).then(({ data }) => setArticulo(data));
  }, [inicial]);

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    if (!articulo || !depositoId || cantidad === "") return;
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/stock/ajuste", {
        articulo_id: articulo.id,
        deposito_id: depositoId,
        variante_id: varianteId || null,
        [modo === "recuento" ? "cantidad_final" : "delta"]: Number(cantidad.replace(",", ".")),
        observaciones: obs.trim() || null,
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el ajuste");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <form className="modal" onClick={(ev) => ev.stopPropagation()} onSubmit={guardar}>
        <h2>Ajuste de stock</h2>
        {error && <div className="login-error">{error}</div>}
        <div className="field">
          <label>Artículo *</label>
          <BuscadorArticulo elegido={articulo} onElegir={setArticulo} />
        </div>
        <SelectorVariante
          articulo={articulo}
          varianteId={varianteId}
          inicial={inicial?.variante_id}
          onCambiar={(id, req) => {
            setVarianteId(id);
            setVarianteRequerida(req);
          }}
        />
        <div className="fila">
          <div className="field">
            <label>Depósito *</label>
            <select
              className="select"
              value={depositoId}
              onChange={(ev) => setDepositoId(ev.target.value)}
            >
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.codigo} — {d.nombre}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Modo</label>
            <select
              className="select"
              value={modo}
              onChange={(ev) => setModo(ev.target.value as "recuento" | "delta")}
            >
              <option value="recuento">Recuento (fijar saldo)</option>
              <option value="delta">Sumar / restar</option>
            </select>
          </div>
        </div>
        <div className="field">
          <label>{modo === "recuento" ? "Saldo contado *" : "Cantidad (± para restar) *"}</label>
          <input
            className="input mono"
            type="number"
            step="0.001"
            required
            value={cantidad}
            onChange={(ev) => setCantidad(ev.target.value)}
          />
        </div>
        <div className="field">
          <label>Observaciones</label>
          <input
            className="input"
            maxLength={120}
            value={obs}
            onChange={(ev) => setObs(ev.target.value)}
            placeholder="ej: recuento físico, rotura, vencimiento…"
          />
        </div>
        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            disabled={!articulo || cantidad === "" || guardando || (varianteRequerida && !varianteId)}
            type="submit"
          >
            {guardando ? "Guardando…" : "Registrar ajuste"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------- modal de transferencia ----------

function TransferenciaModal({
  depositos,
  onCerrar,
}: {
  depositos: Deposito[];
  onCerrar: (refrescar: boolean) => void;
}) {
  const [articulo, setArticulo] = useState<Articulo | null>(null);
  const [origenId, setOrigenId] = useState(depositos[0]?.id ?? "");
  const [destinoId, setDestinoId] = useState(depositos[1]?.id ?? "");
  const [varianteId, setVarianteId] = useState("");
  const [varianteRequerida, setVarianteRequerida] = useState(false);
  const [cantidad, setCantidad] = useState("");
  const [obs, setObs] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function guardar(ev: React.FormEvent) {
    ev.preventDefault();
    if (!articulo) return;
    setError(null);
    setGuardando(true);
    try {
      await apiPost("/stock/transferencia", {
        articulo_id: articulo.id,
        origen_id: origenId,
        destino_id: destinoId,
        variante_id: varianteId || null,
        cantidad: Number(cantidad.replace(",", ".")),
        observaciones: obs.trim() || null,
      });
      onCerrar(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo transferir");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <form className="modal" onClick={(ev) => ev.stopPropagation()} onSubmit={guardar}>
        <h2>Transferencia entre depósitos</h2>
        {error && <div className="login-error">{error}</div>}
        <div className="field">
          <label>Artículo *</label>
          <BuscadorArticulo elegido={articulo} onElegir={setArticulo} />
        </div>
        <SelectorVariante
          articulo={articulo}
          varianteId={varianteId}
          onCambiar={(id, req) => {
            setVarianteId(id);
            setVarianteRequerida(req);
          }}
        />
        <div className="fila">
          <div className="field">
            <label>Desde *</label>
            <select className="select" value={origenId} onChange={(ev) => setOrigenId(ev.target.value)}>
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.codigo} — {d.nombre}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Hacia *</label>
            <select
              className="select"
              value={destinoId}
              onChange={(ev) => setDestinoId(ev.target.value)}
            >
              {depositos.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.codigo} — {d.nombre}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="fila">
          <div className="field">
            <label>Cantidad *</label>
            <input
              className="input mono"
              type="number"
              step="0.001"
              min="0.001"
              required
              value={cantidad}
              onChange={(ev) => setCantidad(ev.target.value)}
            />
          </div>
          <div className="field">
            <label>Observaciones</label>
            <input
              className="input"
              maxLength={120}
              value={obs}
              onChange={(ev) => setObs(ev.target.value)}
            />
          </div>
        </div>
        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            disabled={
              !articulo ||
              cantidad === "" ||
              origenId === destinoId ||
              guardando ||
              (varianteRequerida && !varianteId)
            }
            type="submit"
          >
            {guardando ? "Transfiriendo…" : "Transferir"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------- kardex ----------

function KardexModal({
  fila,
  depositos,
  onCerrar,
}: {
  fila: StockFila;
  depositos: Deposito[];
  onCerrar: () => void;
}) {
  const [movs, setMovs] = useState<Movimiento[]>([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await apiGet<Movimiento[]>(
          `/stock/kardex/${fila.articulo_id}?limit=100`,
        );
        setMovs(data);
      } finally {
        setCargando(false);
      }
    })();
  }, [fila]);

  const depPorId = new Map(depositos.map((d) => [d.id, d.codigo]));

  return (
    <div className="drawer-backdrop" onClick={onCerrar}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>
          Kardex — <span className="mono">{fila.articulo_codigo}</span> {fila.articulo_descripcion}
        </h2>
        {cargando ? (
          <p className="page-sub">Cargando…</p>
        ) : movs.length === 0 ? (
          <div className="vacio">Sin movimientos registrados</div>
        ) : (
          <div className="tabla-card">
            <table className="tabla tabla-mini">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th>Variante</th>
                  <th>Dep.</th>
                  <th className="num">Cantidad</th>
                  <th className="num">Saldo</th>
                  <th>Observaciones</th>
                </tr>
              </thead>
              <tbody>
                {movs.map((m) => (
                  <tr key={m.id}>
                    <td className="mono">{fmtFecha.format(new Date(m.fecha))}</td>
                    <td>{TIPOS_MOV[m.tipo] ?? m.tipo}</td>
                    <td>{m.variante_etiqueta ?? "—"}</td>
                    <td className="mono">{depPorId.get(m.deposito_id) ?? "?"}</td>
                    <td className={`num mono ${Number(m.cantidad) < 0 ? "neg" : "pos"}`}>
                      {Number(m.cantidad) > 0 ? "+" : ""}
                      {fmtCant.format(Number(m.cantidad))}
                    </td>
                    <td className="num mono">{fmtCant.format(Number(m.saldo_resultante))}</td>
                    <td>{m.observaciones ?? m.comprobante ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="drawer-acciones">
          <button className="btn btn-ghost" onClick={onCerrar}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- página ----------

export default function StockPage() {
  const [q, setQ] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [depositoId, setDepositoId] = useState("");
  const [bajoMinimo, setBajoMinimo] = useState(false);
  const [pagina, setPagina] = useState(0);
  const [filas, setFilas] = useState<StockFila[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [depositos, setDepositos] = useState<Deposito[]>([]);
  const { pedirTexto, dialogos } = useDialogos();

  const [ajusteAbierto, setAjusteAbierto] = useState(false);
  const [ajusteInicial, setAjusteInicial] = useState<StockFila | null>(null);
  const [transferAbierto, setTransferAbierto] = useState(false);
  const [kardexFila, setKardexFila] = useState<StockFila | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setBusqueda(q);
      setPagina(0);
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    void apiGet<Deposito[]>("/catalogos-articulos/depositos").then(({ data }) =>
      setDepositos(data.filter((d) => d.activo)),
    );
  }, []);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        q: busqueda,
        limit: String(POR_PAGINA),
        offset: String(pagina * POR_PAGINA),
      });
      if (depositoId) params.set("deposito_id", depositoId);
      if (bajoMinimo) params.set("solo_bajo_minimo", "true");
      const { data, headers } = await apiGet<StockFila[]>(`/stock?${params}`);
      setFilas(data);
      setTotal(Number(headers.get("X-Total-Count") ?? data.length));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar stock");
    } finally {
      setCargando(false);
    }
  }, [busqueda, pagina, depositoId, bajoMinimo]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  async function crearDeposito() {
    const nombre = await pedirTexto("Nombre del nuevo depósito:");
    if (!nombre?.trim()) return;
    const codigo = await pedirTexto(
      "Código corto (ej: 01, DEP2):",
      String(depositos.length + 1).padStart(2, "0"),
    );
    if (!codigo?.trim()) return;
    try {
      const d = await apiPost<Deposito>("/catalogos-articulos/depositos", { codigo, nombre });
      setDepositos((ds) => [...ds, d]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el depósito");
    }
  }

  const desde = pagina * POR_PAGINA + 1;
  const hasta = Math.min((pagina + 1) * POR_PAGINA, total);

  return (
    <>
      <h1 className="page-title">Stock</h1>
      <p className="page-sub">
        {cargando ? "Cargando…" : `${total} posiciones con datos`}
        <button className="cotizacion" onClick={() => void crearDeposito()}>
          + depósito
        </button>
      </p>

      <div className="toolbar">
        <input
          className="input"
          placeholder="Buscar artículo…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="select toolbar-select"
          value={depositoId}
          onChange={(e) => {
            setDepositoId(e.target.value);
            setPagina(0);
          }}
        >
          <option value="">Todos los depósitos</option>
          {depositos.map((d) => (
            <option key={d.id} value={d.id}>
              {d.codigo} — {d.nombre}
            </option>
          ))}
        </select>
        <label className="check">
          <input
            type="checkbox"
            checked={bajoMinimo}
            onChange={(e) => {
              setBajoMinimo(e.target.checked);
              setPagina(0);
            }}
          />
          Bajo mínimo
        </label>
        <button className="btn btn-ghost" onClick={() => setTransferAbierto(true)}>
          Transferencia
        </button>
        <button
          className="btn btn-primary"
          onClick={() => {
            setAjusteInicial(null);
            setAjusteAbierto(true);
          }}
        >
          + Ajuste
        </button>
      </div>

      {error && <div className="login-error">{error}</div>}

      <div className="tabla-card">
        <table className="tabla">
          <thead>
            <tr>
              <th>Código</th>
              <th>Artículo</th>
              <th>Depósito</th>
              <th className="num">Saldo</th>
              <th className="num">Mínimo</th>
              <th>Ubicación</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => {
              const bajo = Number(f.stock_minimo) > 0 && Number(f.cantidad) < Number(f.stock_minimo);
              return (
                <tr
                  key={`${f.articulo_id}-${f.deposito_id}-${f.variante_id ?? ""}`}
                  onClick={() => setKardexFila(f)}
                >
                  <td className="mono">{f.articulo_codigo}</td>
                  <td>
                    {f.articulo_descripcion}
                    {f.variante_etiqueta && <span className="chip chip-variante">{f.variante_etiqueta}</span>}
                  </td>
                  <td>
                    {f.deposito_codigo} — {f.deposito_nombre}
                  </td>
                  <td className={`num mono${bajo ? " neg" : ""}`}>
                    {fmtCant.format(Number(f.cantidad))}
                    {bajo && " ⚠"}
                  </td>
                  <td className="num mono">
                    {Number(f.stock_minimo) > 0 ? fmtCant.format(Number(f.stock_minimo)) : "—"}
                  </td>
                  <td>{f.ubicacion ?? "—"}</td>
                  <td>
                    <button
                      className="mini-btn"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        setAjusteInicial(f);
                        setAjusteAbierto(true);
                      }}
                    >
                      ajustar
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!cargando && filas.length === 0 && (
          <div className="vacio">
            {busqueda || bajoMinimo
              ? "Sin resultados con esos filtros"
              : "Sin posiciones de stock: registrá un ajuste para cargar saldos iniciales"}
          </div>
        )}
      </div>

      {total > POR_PAGINA && (
        <div className="paginado">
          <button className="btn btn-ghost" disabled={pagina === 0} onClick={() => setPagina(pagina - 1)}>
            ← Anterior
          </button>
          <span>
            {desde}–{hasta} de {total}
          </span>
          <button
            className="btn btn-ghost"
            disabled={hasta >= total}
            onClick={() => setPagina(pagina + 1)}
          >
            Siguiente →
          </button>
        </div>
      )}

      {ajusteAbierto && (
        <AjusteModal
          depositos={depositos}
          inicial={ajusteInicial}
          onCerrar={(r) => {
            setAjusteAbierto(false);
            setAjusteInicial(null);
            if (r) void cargar();
          }}
        />
      )}
      {transferAbierto && (
        <TransferenciaModal
          depositos={depositos}
          onCerrar={(r) => {
            setTransferAbierto(false);
            if (r) void cargar();
          }}
        />
      )}
      {kardexFila && (
        <KardexModal fila={kardexFila} depositos={depositos} onCerrar={() => setKardexFila(null)} />
      )}
      {dialogos}
    </>
  );
}
