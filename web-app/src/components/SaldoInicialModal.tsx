// Carga de SALDO INICIAL de cuenta corriente (cliente o proveedor).
// Es un documento sin ítems (ventas: SAL deudor / SAF a favor; compras: SALP
// le debemos / SAFP nos deben) que el backend numera y deja emitido/registrado
// al crearse — no hay borrador ni edición: se anula y se carga otro
// (docs/DISENO-CONTABILIDAD.md §7). Nube-only.

import { useState } from "react";
import { ApiError, apiGet, apiPost } from "../lib/api";
import { hoyISO } from "../lib/fechas";
import type { Cliente, Compra, Comprobante, Proveedor } from "../lib/types";
import { AlertError } from "./Alertas";
import Buscador from "./Buscador";
import { useDialogos } from "./dialogos";

export type CircuitoSaldoInicial = "ventas" | "compras";

// Cliente y Proveedor comparten `id` + `entidad` (BUE): un solo buscador sirve.
type Contraparte = Cliente | Proveedor;

const buscarClientes = async (q: string): Promise<Contraparte[]> =>
  (await apiGet<Cliente[]>(`/clientes?q=${encodeURIComponent(q)}&limit=8`)).data;
const buscarProveedores = async (q: string): Promise<Contraparte[]> =>
  (await apiGet<Proveedor[]>(`/proveedores?q=${encodeURIComponent(q)}&limit=8`)).data;

const TEXTOS = {
  ventas: {
    titulo: "Cargar saldo inicial de cliente",
    contraparte: "Cliente",
    placeholder: "Buscar cliente…",
    buscar: buscarClientes,
    url: "/ventas/saldos-iniciales",
    campoId: "cliente_id",
    sentidos: [
      ["deudor", "El cliente nos debe"],
      ["a_favor", "Tiene saldo a favor"],
    ],
    errorDefault: "No se pudo cargar el saldo inicial del cliente",
  },
  compras: {
    titulo: "Cargar saldo inicial de proveedor",
    contraparte: "Proveedor",
    placeholder: "Buscar proveedor…",
    buscar: buscarProveedores,
    url: "/compras/saldos-iniciales",
    campoId: "proveedor_id",
    sentidos: [
      ["debemos", "Le debemos al proveedor"],
      ["nos_deben", "El proveedor nos debe"],
    ],
    errorDefault: "No se pudo cargar el saldo inicial del proveedor",
  },
} as const;

export default function SaldoInicialModal({
  circuito,
  onCerrar,
  onCreado,
}: {
  circuito: CircuitoSaldoInicial;
  onCerrar: () => void;
  /** Se llama con el documento creado (ComprobanteOut / CompraOut) tras el 201. */
  onCreado: (doc: Comprobante | Compra) => void;
}) {
  const t = TEXTOS[circuito];
  const [contraparte, setContraparte] = useState<Contraparte | null>(null);
  const [sentido, setSentido] = useState<string>(t.sentidos[0][0]);
  const [importe, setImporte] = useState("");
  const [fecha, setFecha] = useState(hoyISO());
  const [obs, setObs] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const { confirmar, dialogos } = useDialogos();

  const importeNum = Number(importe);
  const importeValido = importe.trim() !== "" && Number.isFinite(importeNum) && importeNum > 0;
  const hayDatos = contraparte !== null || importe.trim() !== "" || obs.trim() !== "";

  async function intentarCerrar() {
    if (guardando) return;
    if (hayDatos && !(await confirmar("Hay datos sin guardar. ¿Descartar el saldo inicial?"))) {
      return;
    }
    onCerrar();
  }

  async function guardar() {
    if (!contraparte || !importeValido) return;
    setError(null);
    setGuardando(true);
    try {
      const doc = await apiPost<Comprobante | Compra>(t.url, {
        [t.campoId]: contraparte.id,
        importe: importe.trim(),
        sentido,
        fecha: fecha || null,
        observaciones: obs.trim() || null,
      });
      onCreado(doc);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.errorDefault);
      setGuardando(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={() => void intentarCerrar()}>
      <div className="modal" onClick={(ev) => ev.stopPropagation()}>
        <h2>{t.titulo}</h2>
        <p className="page-sub">
          Carga el saldo con el que arranca la cuenta corriente (migración desde otro sistema).
          No es un comprobante fiscal: no va a ARCA ni a los libros de IVA.
        </p>
        <AlertError>{error}</AlertError>

        <div className="field">
          <label>{t.contraparte} *</label>
          <Buscador<Contraparte>
            placeholder={t.placeholder}
            buscar={t.buscar}
            etiqueta={(c) => (
              <>
                {c.entidad.razon_social}{" "}
                <span className="mono">{c.entidad.nro_documento ?? ""}</span>
              </>
            )}
            clave={(c) => c.id}
            elegido={contraparte}
            onElegir={setContraparte}
            autoFocus
          />
        </div>

        <div className="fila">
          <div className="field" style={{ flex: 2 }}>
            <label>Sentido *</label>
            <select
              className="select"
              value={sentido}
              onChange={(ev) => setSentido(ev.target.value)}
            >
              {t.sentidos.map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Importe *</label>
            <input
              className="input mono"
              type="number"
              step="0.01"
              min="0.01"
              placeholder="0,00"
              value={importe}
              onChange={(ev) => setImporte(ev.target.value)}
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
          <label>Observaciones</label>
          <input
            className="input"
            placeholder="p. ej. saldo al cierre del sistema anterior"
            value={obs}
            onChange={(ev) => setObs(ev.target.value)}
          />
        </div>

        <div className="drawer-acciones">
          <button type="button" className="btn btn-ghost" onClick={() => void intentarCerrar()}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!contraparte || !importeValido || guardando}
            onClick={() => void guardar()}
          >
            {guardando ? "Guardando…" : "Cargar saldo inicial"}
          </button>
        </div>
      </div>
      {dialogos}
    </div>
  );
}
