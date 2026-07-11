// Alta de comprobante de venta (factura / presupuesto / remito).
// La letra (A/B/C) y los totales los decide SIEMPRE el backend; acá solo se
// muestra una vista previa. El borrador se puede guardar y emitir después,
// o emitir directo ("Guardar y emitir").

import { useEffect, useMemo, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type {
  Articulo,
  Cliente,
  Comprobante,
  CondicionVentaCatalogo,
  PuntoVenta,
  Variante,
} from "../../lib/types";
import { useDialogos } from "../../components/dialogos";
import { etiquetaCuenta, useCuentasBancarias } from "../../components/useCuentasBancarias";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });

interface ItemDraft {
  articulo: Articulo | null;
  variante_id: string;
  variantes: Variante[];
  descripcion: string;
  cantidad: string;
  precio: string;
  bonif: string;
  tasa_iva: string;
}

function itemVacio(): ItemDraft {
  return {
    articulo: null,
    variante_id: "",
    variantes: [],
    descripcion: "",
    cantidad: "1",
    precio: "",
    bonif: "",
    tasa_iva: "21",
  };
}

function BuscadorCliente({
  elegido,
  onElegir,
}: {
  elegido: Cliente | null;
  onElegir: (c: Cliente | null) => void;
}) {
  const [q, setQ] = useState("");
  const [opciones, setOpciones] = useState<Cliente[]>([]);

  useEffect(() => {
    if (elegido || q.trim().length < 2) {
      setOpciones([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await apiGet<Cliente[]>(`/clientes?q=${encodeURIComponent(q)}&limit=8`);
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
        {elegido.entidad.razon_social}
        <span className="chip">{elegido.entidad.condicion_iva}</span>
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
        placeholder="Buscar cliente (o dejar vacío = Consumidor Final)…"
        value={q}
        onChange={(ev) => setQ(ev.target.value)}
      />
      {opciones.length > 0 && (
        <div className="buscador-opciones">
          {opciones.map((c) => (
            <button key={c.id} type="button" onClick={() => onElegir(c)}>
              {c.entidad.razon_social}{" "}
              <span className="mono">{c.entidad.nro_documento ?? ""}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function FilaItem({
  item,
  listaPrecios,
  preciosConIva,
  onCambiar,
  onQuitar,
}: {
  item: ItemDraft;
  listaPrecios: number;
  preciosConIva: boolean;
  onCambiar: (it: ItemDraft) => void;
  onQuitar: () => void;
}) {
  const [q, setQ] = useState("");
  const [opciones, setOpciones] = useState<Articulo[]>([]);

  useEffect(() => {
    if (item.articulo || q.trim().length < 2) {
      setOpciones([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await apiGet<Articulo[]>(`/articulos?q=${encodeURIComponent(q)}&limit=8`);
        setOpciones(data);
      } catch {
        setOpciones([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q, item.articulo]);

  async function elegir(a: Articulo) {
    const precioLista = a[`precio_${listaPrecios}` as "precio_1"] ?? a.precio_1;
    let variantes: Variante[] = [];
    try {
      const { data } = await apiGet<Variante[]>(`/articulos/${a.id}/variantes`);
      variantes = data.filter((v) => v.activo);
    } catch {
      variantes = [];
    }
    onCambiar({
      ...item,
      articulo: a,
      variantes,
      variante_id: "",
      descripcion: a.descripcion,
      precio: precioLista,
      tasa_iva: a.tasa_iva,
    });
    setQ("");
  }

  const neto =
    Number(item.cantidad || 0) *
    Number(item.precio || 0) *
    (1 - Number(item.bonif || 0) / 100);

  return (
    <tr>
      <td className="col-articulo">
        {item.articulo ? (
          <>
            <span className="mono">{item.articulo.codigo}</span> {item.descripcion}
            <button
              type="button"
              className="mini-btn"
              onClick={() => onCambiar({ ...itemVacio(), cantidad: item.cantidad })}
            >
              ×
            </button>
          </>
        ) : (
          <div className="buscador">
            <input
              className="input input-mini"
              placeholder="Buscar artículo…"
              value={q}
              onChange={(ev) => setQ(ev.target.value)}
            />
            {opciones.length > 0 && (
              <div className="buscador-opciones">
                {opciones.map((a) => (
                  <button key={a.id} type="button" onClick={() => void elegir(a)}>
                    <span className="mono">{a.codigo}</span> {a.descripcion}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </td>
      <td>
        {item.variantes.length > 0 && (
          <select
            className="select input-mini"
            value={item.variante_id}
            onChange={(ev) => onCambiar({ ...item, variante_id: ev.target.value })}
          >
            <option value="">— variante —</option>
            {item.variantes.map((v) => (
              <option key={v.id} value={v.id}>
                {v.etiqueta}
              </option>
            ))}
          </select>
        )}
      </td>
      <td>
        <input
          className="input input-mini num mono"
          type="number"
          step="0.001"
          min="0.001"
          value={item.cantidad}
          onChange={(ev) => onCambiar({ ...item, cantidad: ev.target.value })}
        />
      </td>
      <td>
        <input
          className="input input-mini num mono"
          type="number"
          step="0.0001"
          min="0"
          title={preciosConIva ? "Precio final (IVA incluido)" : "Precio neto (sin IVA)"}
          value={item.precio}
          onChange={(ev) => onCambiar({ ...item, precio: ev.target.value })}
        />
      </td>
      <td>
        <input
          className="input input-mini num mono"
          type="number"
          step="0.01"
          min="0"
          max="100"
          placeholder="0"
          value={item.bonif}
          onChange={(ev) => onCambiar({ ...item, bonif: ev.target.value })}
        />
      </td>
      <td className="num mono">{item.tasa_iva}%</td>
      <td className="num mono">{fmt.format(neto)}</td>
      <td>
        <button type="button" className="mini-btn" onClick={onQuitar}>
          quitar
        </button>
      </td>
    </tr>
  );
}

export default function ComprobanteForm({
  puntosVenta,
  onCerrar,
}: {
  puntosVenta: PuntoVenta[];
  onCerrar: (refrescar: boolean, emitido?: Comprobante) => void;
}) {
  const [clase, setClase] = useState<"factura" | "presupuesto" | "remito">("factura");
  const [pvId, setPvId] = useState(puntosVenta[0]?.id ?? "");
  const [cliente, setCliente] = useState<Cliente | null>(null);
  const [contado, setContado] = useState(true);
  const [condiciones, setCondiciones] = useState<CondicionVentaCatalogo[]>([]);
  const [condicionId, setCondicionId] = useState("");
  const [preciosConIva, setPreciosConIva] = useState(true);
  const [descuento, setDescuento] = useState("");
  const [obs, setObs] = useState("");
  const [items, setItems] = useState<ItemDraft[]>([itemVacio()]);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();
  // medio de cobro del contado (014): la contrapartida financiera del documento
  const [medioCobro, setMedioCobro] = useState("efectivo");
  const [cuentaBancariaId, setCuentaBancariaId] = useState("");
  const cuentas = useCuentasBancarias();

  // un click en el backdrop no tira una factura a medio cargar (LOTE TÉCNICO)
  const hayDatos =
    cliente !== null ||
    obs.trim() !== "" ||
    items.some((it) => it.articulo || it.descripcion.trim() || it.precio);

  async function intentarCerrar() {
    if (hayDatos && !(await confirmar("Hay datos sin guardar. ¿Descartar el comprobante?")))
      return;
    onCerrar(false);
  }

  useEffect(() => {
    void apiGet<CondicionVentaCatalogo[]>("/ventas/condiciones-venta").then(({ data }) =>
      setCondiciones(data),
    );
  }, []);

  // al elegir cliente, adoptar su lista y su condición habitual
  const listaPrecios = cliente?.lista_precios ?? 1;
  useEffect(() => {
    if (cliente?.condicion_venta_id && condiciones.some((c) => c.id === cliente.condicion_venta_id)) {
      setCondicionId(cliente.condicion_venta_id);
      setContado(false);
    }
  }, [cliente, condiciones]);

  const totalPreview = useMemo(() => {
    const dto = 1 - Number(descuento || 0) / 100;
    return items.reduce((acc, it) => {
      const neto =
        Number(it.cantidad || 0) * Number(it.precio || 0) * (1 - Number(it.bonif || 0) / 100);
      const conIva = preciosConIva ? neto : neto * (1 + Number(it.tasa_iva || 0) / 100);
      return acc + conIva * dto;
    }, 0);
  }, [items, descuento, preciosConIva]);

  async function guardar(emitir: boolean) {
    setError(null);
    const listos = items.filter((it) => it.articulo || it.descripcion.trim());
    if (listos.length === 0) {
      setError("Agregá al menos un ítem");
      return;
    }
    const faltaVariante = listos.find((it) => it.variantes.length > 0 && !it.variante_id);
    if (faltaVariante) {
      setError(`"${faltaVariante.descripcion}" tiene variantes: elegí cuál`);
      return;
    }
    setGuardando(true);
    try {
      const body = {
        clase,
        punto_venta_id: pvId,
        cliente_id: cliente?.id ?? null,
        contado: clase === "factura" ? contado : true,
        condicion_venta_id: !contado && condicionId ? condicionId : null,
        lista_precios: listaPrecios,
        precios_con_iva: preciosConIva,
        descuento_pct: descuento || "0",
        observaciones: obs.trim() || null,
        items: listos.map((it) => ({
          articulo_id: it.articulo?.id ?? null,
          variante_id: it.variante_id || null,
          descripcion: it.descripcion.trim() || null,
          cantidad: it.cantidad,
          precio_unitario: it.precio || "0",
          bonif_pct: it.bonif || "0",
          tasa_iva: it.tasa_iva,
        })),
      };
      const borrador = await apiPost<Comprobante>("/ventas/comprobantes", body);
      if (emitir) {
        // contado: se registra el medio de cobro con el total REAL que calculó
        // el server en el borrador (014 — contrapartida financiera)
        const esContadoFiscal = clase === "factura" && contado;
        const emitido = await apiPost<Comprobante>(
          `/ventas/comprobantes/${borrador.id}/emitir`,
          esContadoFiscal
            ? {
                medios: [
                  {
                    medio: medioCobro,
                    importe: borrador.total,
                    cuenta_bancaria_id:
                      medioCobro === "transferencia" && cuentaBancariaId
                        ? cuentaBancariaId
                        : null,
                  },
                ],
              }
            : {},
        );
        onCerrar(true, emitido);
      } else {
        onCerrar(true);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el comprobante");
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => void intentarCerrar()}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>
          {clase === "factura" ? "Nueva venta" : clase === "presupuesto" ? "Nuevo presupuesto" : "Nuevo remito"}
        </h2>
        {error && <div className="login-error">{error}</div>}

        <div className="fila">
          <div className="field">
            <label>Documento</label>
            <select
              className="select"
              value={clase}
              onChange={(ev) => setClase(ev.target.value as typeof clase)}
            >
              <option value="factura">Factura (la letra la decide el sistema)</option>
              <option value="presupuesto">Presupuesto (X)</option>
              <option value="remito">Remito interno (X)</option>
            </select>
          </div>
          <div className="field">
            <label>Punto de venta</label>
            <select className="select" value={pvId} onChange={(ev) => setPvId(ev.target.value)}>
              {puntosVenta.map((pv) => (
                <option key={pv.id} value={pv.id}>
                  {String(pv.numero).padStart(4, "0")} — {pv.descripcion || "sin nombre"}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="field">
          <label>Cliente</label>
          <BuscadorCliente elegido={cliente} onElegir={setCliente} />
        </div>

        {clase === "factura" && (
          <div className="fila">
            <div className="field">
              <label>Condición</label>
              <select
                className="select"
                value={contado ? "contado" : condicionId}
                onChange={(ev) => {
                  if (ev.target.value === "contado") setContado(true);
                  else {
                    setContado(false);
                    setCondicionId(ev.target.value);
                  }
                }}
              >
                <option value="contado">Contado</option>
                {condiciones.map((c) => (
                  <option key={c.id} value={c.id} disabled={!cliente}>
                    Cta. cte. — {c.descripcion}
                  </option>
                ))}
              </select>
            </div>
            {contado && (
              <div className="field">
                <label>Cobro</label>
                <select
                  className="select"
                  value={medioCobro}
                  onChange={(ev) => setMedioCobro(ev.target.value)}
                >
                  <option value="efectivo">Efectivo</option>
                  <option value="transferencia">Transferencia</option>
                  <option value="tarjeta">Tarjeta</option>
                  <option value="mercadopago">MercadoPago</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
            )}
            {contado && medioCobro === "transferencia" && cuentas.length > 0 && (
              <div className="field">
                <label>Cuenta bancaria</label>
                <select
                  className="select"
                  value={cuentaBancariaId}
                  onChange={(ev) => setCuentaBancariaId(ev.target.value)}
                >
                  <option value="">— sin especificar —</option>
                  {cuentas.map((c) => (
                    <option key={c.id} value={c.id}>
                      {etiquetaCuenta(c)}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div className="field">
              <label>Descuento global %</label>
              <input
                className="input mono"
                type="number"
                min="0"
                max="99"
                step="0.01"
                placeholder="0"
                value={descuento}
                onChange={(ev) => setDescuento(ev.target.value)}
              />
            </div>
            <div className="field">
              <label>Precios cargados</label>
              <select
                className="select"
                value={preciosConIva ? "final" : "neto"}
                onChange={(ev) => setPreciosConIva(ev.target.value === "final")}
              >
                <option value="final">IVA incluido (final)</option>
                <option value="neto">Netos (sin IVA)</option>
              </select>
            </div>
          </div>
        )}

        <div className="tabla-card">
          <table className="tabla tabla-mini">
            <thead>
              <tr>
                <th style={{ width: "34%" }}>Artículo</th>
                <th>Variante</th>
                <th className="num">Cant.</th>
                <th className="num">Precio</th>
                <th className="num">Bonif %</th>
                <th className="num">IVA</th>
                <th className="num">Importe</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <FilaItem
                  key={i}
                  item={it}
                  listaPrecios={listaPrecios}
                  preciosConIva={preciosConIva}
                  onCambiar={(nuevo) => setItems(items.map((x, j) => (j === i ? nuevo : x)))}
                  onQuitar={() => setItems(items.filter((_, j) => j !== i))}
                />
              ))}
            </tbody>
          </table>
          <div style={{ padding: "8px" }}>
            <button type="button" className="mini-btn" onClick={() => setItems([...items, itemVacio()])}>
              + ítem
            </button>
          </div>
        </div>

        <div className="fila" style={{ alignItems: "center", justifyContent: "space-between" }}>
          <div className="field" style={{ flex: 1 }}>
            <label>Observaciones</label>
            <input className="input" value={obs} onChange={(ev) => setObs(ev.target.value)} />
          </div>
          <div className="total-preview">
            Total estimado: <b className="mono">$ {fmt.format(totalPreview)}</b>
          </div>
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={guardando || !pvId}
            onClick={() => void guardar(false)}
          >
            Guardar borrador
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={guardando || !pvId}
            onClick={() => void guardar(true)}
          >
            {guardando ? "Procesando…" : clase === "factura" ? "Guardar y emitir" : "Guardar y numerar"}
          </button>
        </div>
      </div>
      {dialogos}
    </div>
  );
}
