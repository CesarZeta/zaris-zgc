// Carga de comprobante de compra (factura/NC/ND/remito del proveedor).
// A diferencia de Ventas, acá el documento YA existe en papel: la letra y la
// numeración (punto de venta + número) se copian del comprobante físico.
// Letra A: costos netos + IVA discriminado. B/C: importes finales.

import { useEffect, useMemo, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import type {
  Articulo,
  Compra,
  CondicionVentaCatalogo,
  Proveedor,
  Variante,
} from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const TASAS = ["0", "2.5", "5", "10.5", "21", "27"];

interface ItemDraft {
  articulo: Articulo | null;
  variante_id: string;
  variantes: Variante[];
  descripcion: string;
  cantidad: string;
  costo: string;
  bonif1: string;
  bonif2: string;
  tasa_iva: string;
}

function itemVacio(): ItemDraft {
  return {
    articulo: null,
    variante_id: "",
    variantes: [],
    descripcion: "",
    cantidad: "1",
    costo: "",
    bonif1: "",
    bonif2: "",
    tasa_iva: "21",
  };
}

export function BuscadorProveedor({
  elegido,
  onElegir,
}: {
  elegido: Proveedor | null;
  onElegir: (p: Proveedor | null) => void;
}) {
  const [q, setQ] = useState("");
  const [opciones, setOpciones] = useState<Proveedor[]>([]);

  useEffect(() => {
    if (elegido || q.trim().length < 2) {
      setOpciones([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await apiGet<Proveedor[]>(`/proveedores?q=${encodeURIComponent(q)}&limit=8`);
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
        placeholder="Buscar proveedor…"
        value={q}
        onChange={(ev) => setQ(ev.target.value)}
        autoFocus
      />
      {opciones.length > 0 && (
        <div className="buscador-opciones">
          {opciones.map((p) => (
            <button key={p.id} type="button" onClick={() => onElegir(p)}>
              {p.entidad.razon_social}{" "}
              <span className="mono">{p.entidad.nro_documento ?? ""}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function FilaItem({
  item,
  letra,
  onCambiar,
  onQuitar,
}: {
  item: ItemDraft;
  letra: string;
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
      costo: a.costo !== "0.0000" ? a.costo : "",
      tasa_iva: a.tasa_iva,
    });
    setQ("");
  }

  const neto =
    Number(item.cantidad || 0) *
    Number(item.costo || 0) *
    (1 - Number(item.bonif1 || 0) / 100) *
    (1 - Number(item.bonif2 || 0) / 100);

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
              placeholder="Buscar artículo (o texto libre en descripción)…"
              value={q}
              onChange={(ev) => {
                setQ(ev.target.value);
                onCambiar({ ...item, descripcion: ev.target.value });
              }}
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
          title={letra === "A" ? "Costo neto (sin IVA)" : "Costo final (IVA incluido)"}
          value={item.costo}
          onChange={(ev) => onCambiar({ ...item, costo: ev.target.value })}
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
          value={item.bonif1}
          onChange={(ev) => onCambiar({ ...item, bonif1: ev.target.value })}
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
          value={item.bonif2}
          onChange={(ev) => onCambiar({ ...item, bonif2: ev.target.value })}
        />
      </td>
      <td>
        <select
          className="select input-mini"
          value={item.tasa_iva}
          onChange={(ev) => onCambiar({ ...item, tasa_iva: ev.target.value })}
        >
          {TASAS.map((t) => (
            <option key={t} value={t}>
              {t}%
            </option>
          ))}
        </select>
      </td>
      <td className="num mono">{fmt.format(neto)}</td>
      <td>
        <button type="button" className="mini-btn" onClick={onQuitar}>
          quitar
        </button>
      </td>
    </tr>
  );
}

export default function CompraForm({
  onCerrar,
}: {
  onCerrar: (refrescar: boolean, registrada?: Compra) => void;
}) {
  const [clase, setClase] = useState<"factura" | "nota_credito" | "nota_debito" | "remito">(
    "factura",
  );
  const [letra, setLetra] = useState("A");
  const [pv, setPv] = useState("");
  const [numero, setNumero] = useState("");
  const [fecha, setFecha] = useState("");
  const [proveedor, setProveedor] = useState<Proveedor | null>(null);
  // arranca en contado (coincide con lo que muestra el select); si el
  // proveedor tiene condición habitual, el useEffect pasa a cta. cte.
  const [contado, setContado] = useState(true);
  const [condiciones, setCondiciones] = useState<CondicionVentaCatalogo[]>([]);
  const [condicionId, setCondicionId] = useState("");
  const [asociadaId, setAsociadaId] = useState("");
  const [facturasProv, setFacturasProv] = useState<Compra[]>([]);
  const [extras, setExtras] = useState({
    percepcion_iva: "",
    percepcion_iibb: "",
    impuestos_internos: "",
    otros_tributos: "",
    no_gravado: "",
    exento: "",
    redondeo: "",
  });
  const [verExtras, setVerExtras] = useState(false);
  const [obs, setObs] = useState("");
  const [items, setItems] = useState<ItemDraft[]>([itemVacio()]);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const esRemito = clase === "remito";
  const esNCND = clase === "nota_credito" || clase === "nota_debito";

  useEffect(() => {
    void apiGet<CondicionVentaCatalogo[]>("/ventas/condiciones-venta").then(({ data }) =>
      setCondiciones(data),
    );
  }, []);

  // condición habitual del proveedor
  useEffect(() => {
    if (proveedor?.condicion_compra_id && condiciones.some((c) => c.id === proveedor.condicion_compra_id)) {
      setCondicionId(proveedor.condicion_compra_id);
      setContado(false);
    }
  }, [proveedor, condiciones]);

  // facturas registradas del proveedor (para asociar NC/ND)
  useEffect(() => {
    if (!proveedor || !esNCND) {
      setFacturasProv([]);
      setAsociadaId("");
      return;
    }
    void apiGet<Compra[]>(
      `/compras/comprobantes?proveedor_id=${proveedor.id}&clase=factura&estado=registrado&limit=100`,
    ).then(({ data }) => setFacturasProv(data));
  }, [proveedor, esNCND]);

  const totalPreview = useMemo(() => {
    const extrasTotal =
      Number(extras.percepcion_iva || 0) +
      Number(extras.percepcion_iibb || 0) +
      Number(extras.impuestos_internos || 0) +
      Number(extras.otros_tributos || 0) +
      Number(extras.no_gravado || 0) +
      Number(extras.exento || 0) +
      Number(extras.redondeo || 0);
    const itemsTotal = items.reduce((acc, it) => {
      const neto =
        Number(it.cantidad || 0) *
        Number(it.costo || 0) *
        (1 - Number(it.bonif1 || 0) / 100) *
        (1 - Number(it.bonif2 || 0) / 100);
      return acc + (letra === "A" && !esRemito ? neto * (1 + Number(it.tasa_iva || 0) / 100) : neto);
    }, 0);
    return itemsTotal + extrasTotal;
  }, [items, extras, letra, esRemito]);

  async function guardar(registrar: boolean) {
    setError(null);
    if (!proveedor) {
      setError("Elegí el proveedor");
      return;
    }
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
        letra: esRemito ? "A" : letra, // el backend fuerza X en remitos
        punto_venta: Number(pv || 0),
        numero: Number(numero || 0),
        proveedor_id: proveedor.id,
        fecha: fecha || null,
        contado: esRemito ? true : contado,
        condicion_compra_id: !contado && condicionId ? condicionId : null,
        compra_asociada_id: esNCND && asociadaId ? asociadaId : null,
        percepcion_iva: extras.percepcion_iva || "0",
        percepcion_iibb: extras.percepcion_iibb || "0",
        impuestos_internos: extras.impuestos_internos || "0",
        otros_tributos: extras.otros_tributos || "0",
        no_gravado: extras.no_gravado || "0",
        exento: extras.exento || "0",
        redondeo: extras.redondeo || "0",
        observaciones: obs.trim() || null,
        items: listos.map((it) => ({
          articulo_id: it.articulo?.id ?? null,
          variante_id: it.variante_id || null,
          descripcion: it.descripcion.trim() || null,
          cantidad: it.cantidad,
          costo_unitario: it.costo || "0",
          bonif_1: it.bonif1 || "0",
          bonif_2: it.bonif2 || "0",
          tasa_iva: it.tasa_iva,
        })),
      };
      const borrador = await apiPost<Compra>("/compras/comprobantes", body);
      if (registrar) {
        const registrada = await apiPost<Compra>(
          `/compras/comprobantes/${borrador.id}/registrar`,
          {},
        );
        onCerrar(true, registrada);
      } else {
        onCerrar(true);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la compra");
      setGuardando(false);
    }
  }

  const titulos: Record<typeof clase, string> = {
    factura: "Nueva compra (factura del proveedor)",
    nota_credito: "Nota de crédito del proveedor",
    nota_debito: "Nota de débito del proveedor",
    remito: "Remito del proveedor",
  };

  return (
    <div className="drawer-backdrop" onClick={() => onCerrar(false)}>
      <div className="modal modal-ancho" onClick={(ev) => ev.stopPropagation()}>
        <h2>{titulos[clase]}</h2>
        {error && <div className="login-error">{error}</div>}

        <div className="fila">
          <div className="field">
            <label>Documento</label>
            <select
              className="select"
              value={clase}
              onChange={(ev) => setClase(ev.target.value as typeof clase)}
            >
              <option value="factura">Factura de compra</option>
              <option value="nota_credito">Nota de crédito</option>
              <option value="nota_debito">Nota de débito</option>
              <option value="remito">Remito (solo stock)</option>
            </select>
          </div>
          {!esRemito && (
            <div className="field" style={{ maxWidth: 90 }}>
              <label>Letra</label>
              <select className="select" value={letra} onChange={(ev) => setLetra(ev.target.value)}>
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
              </select>
            </div>
          )}
          <div className="field" style={{ maxWidth: 110 }}>
            <label>Punto de venta</label>
            <input
              className="input mono"
              type="number"
              min="0"
              max="99999"
              placeholder="0001"
              value={pv}
              onChange={(ev) => setPv(ev.target.value)}
            />
          </div>
          <div className="field" style={{ maxWidth: 140 }}>
            <label>Número</label>
            <input
              className="input mono"
              type="number"
              min="0"
              placeholder="del papel"
              value={numero}
              onChange={(ev) => setNumero(ev.target.value)}
            />
          </div>
          <div className="field" style={{ maxWidth: 160 }}>
            <label>Fecha</label>
            <input
              className="input mono"
              type="date"
              value={fecha}
              onChange={(ev) => setFecha(ev.target.value)}
            />
          </div>
        </div>

        <div className="field">
          <label>Proveedor *</label>
          <BuscadorProveedor elegido={proveedor} onElegir={setProveedor} />
        </div>

        {!esRemito && (
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
                <option value="contado">Contado (pagada en el acto)</option>
                {condiciones.map((c) => (
                  <option key={c.id} value={c.id}>
                    Cta. cte. — {c.descripcion}
                  </option>
                ))}
              </select>
            </div>
            {esNCND && (
              <div className="field">
                <label>Factura asociada (opcional)</label>
                <select
                  className="select"
                  value={asociadaId}
                  onChange={(ev) => setAsociadaId(ev.target.value)}
                  disabled={!proveedor}
                >
                  <option value="">—</option>
                  {facturasProv.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.tipo_codigo} {f.numero_formateado} — $ {fmt.format(Number(f.total))}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}

        <div className="tabla-card">
          <table className="tabla tabla-mini">
            <thead>
              <tr>
                <th style={{ width: "30%" }}>Artículo</th>
                <th>Variante</th>
                <th className="num">Cant.</th>
                <th className="num">{letra === "A" && !esRemito ? "Costo neto" : "Costo final"}</th>
                <th className="num">Bonif 1%</th>
                <th className="num">Bonif 2%</th>
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
                  letra={esRemito ? "X" : letra}
                  onCambiar={(nuevo) => setItems(items.map((x, j) => (j === i ? nuevo : x)))}
                  onQuitar={() => setItems(items.filter((_, j) => j !== i))}
                />
              ))}
            </tbody>
          </table>
          <div style={{ padding: "8px", display: "flex", gap: 8 }}>
            <button type="button" className="mini-btn" onClick={() => setItems([...items, itemVacio()])}>
              + ítem
            </button>
            {!esRemito && (
              <button type="button" className="mini-btn" onClick={() => setVerExtras(!verExtras)}>
                {verExtras ? "− ocultar" : "+ percepciones y otros"}
              </button>
            )}
          </div>
        </div>

        {verExtras && !esRemito && (
          <div className="fila" style={{ flexWrap: "wrap" }}>
            {(
              [
                ["percepcion_iva", "Percep. IVA"],
                ["percepcion_iibb", "Percep. IIBB"],
                ["impuestos_internos", "Imp. internos"],
                ["otros_tributos", "Otros tributos"],
                ["no_gravado", "No gravado"],
                ["exento", "Exento"],
                ["redondeo", "Redondeo ±"],
              ] as const
            ).map(([k, etiqueta]) => (
              <div className="field" key={k} style={{ maxWidth: 130 }}>
                <label>{etiqueta}</label>
                <input
                  className="input input-mini num mono"
                  type="number"
                  step="0.01"
                  placeholder="0"
                  value={extras[k]}
                  onChange={(ev) => setExtras({ ...extras, [k]: ev.target.value })}
                />
              </div>
            ))}
          </div>
        )}

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
          <button type="button" className="btn btn-ghost" onClick={() => onCerrar(false)}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={guardando}
            onClick={() => void guardar(false)}
          >
            Guardar borrador
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={guardando}
            onClick={() => void guardar(true)}
          >
            {guardando ? "Procesando…" : "Guardar y registrar"}
          </button>
        </div>
      </div>
    </div>
  );
}
