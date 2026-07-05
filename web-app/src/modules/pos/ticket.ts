// Ticket térmico 58/80mm para el POS (Fase 6). Mismo criterio que
// ventas/impresion.ts: el backend entrega TODO en /ventas/comprobantes/{id}/
// impresion y acá solo se maqueta angosto para la impresora térmica, vía el
// diálogo de impresión del navegador (QZ Tray evaluado y diferido — ver
// ROADMAP F6). Sin dependencias externas.

import type { ImpresionPayload } from "../../lib/types";
import { MEDIOS_PAGO } from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const n = (v: string | number | null | undefined) => fmt.format(Number(v ?? 0));

function esc(s: string | null | undefined): string {
  return (s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export interface DatosCobro {
  medios: { medio: string; importe: string }[];
  recibido?: string; // efectivo entregado por el cliente (para el vuelto)
  vuelto?: string;
}

export function imprimirTicket(
  p: ImpresionPayload,
  ancho: number,
  cobro?: DatosCobro,
  cajero?: string,
): void {
  const c = p.comprobante;
  const discrimina = p.discrimina_iva;
  const util = ancho === 58 ? 48 : 72; // mm imprimibles típicos

  const filas = c.items
    .map((i) => {
      const cant = Number(i.cantidad);
      // Sin discriminación (B/C) el unitario que ve el cliente es el FINAL;
      // en A se muestra el neto (precio_unitario guardado).
      const unitario = discrimina
        ? Number(i.precio_unitario)
        : Number(i.importe_total) / (cant || 1);
      const detalle =
        cant === 1
          ? `<div class="linea"><span class="desc">${esc(i.descripcion)}</span><span class="imp">${n(i.importe_total)}</span></div>`
          : `<div class="desc">${esc(i.descripcion)}</div>
             <div class="linea"><span>${fmt.format(cant)} x ${n(unitario)}</span><span class="imp">${n(i.importe_total)}</span></div>`;
      return `<div class="item">${detalle}</div>`;
    })
    .join("");

  const totales = discrimina
    ? `<div class="linea"><span>Neto gravado</span><span>${n(c.neto_gravado)}</span></div>` +
      c.alicuotas
        .map((a) => `<div class="linea"><span>IVA ${a.tasa}%</span><span>${n(a.importe)}</span></div>`)
        .join("")
    : "";

  const medios = (cobro?.medios ?? [])
    .map(
      (m) =>
        `<div class="linea"><span>${esc(MEDIOS_PAGO[m.medio] ?? m.medio)}</span><span>${n(m.importe)}</span></div>`,
    )
    .join("");
  const vuelto =
    cobro?.vuelto && Number(cobro.vuelto) > 0
      ? `<div class="linea"><span>Recibido</span><span>${n(cobro.recibido)}</span></div>
         <div class="linea vuelto"><span>VUELTO</span><span>${n(cobro.vuelto)}</span></div>`
      : "";

  const transparencia = p.transparencia_fiscal
    ? `<div class="fisco">Rég. Transparencia Fiscal (Ley 27.743)<br/>
       IVA Contenido $ ${n(p.transparencia_fiscal.iva_contenido)} ·
       Otros Imp. Nac. Ind. $ ${n(p.transparencia_fiscal.otros_impuestos_nacionales_indirectos)}</div>`
    : "";

  const cae = c.cae
    ? `<div class="cae">CAE ${esc(c.cae)} · Vto ${esc(c.cae_vencimiento)}</div>`
    : "";
  const leyendas = p.leyendas.map((l) => `<div class="leyenda">${esc(l)}</div>`).join("");

  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>${esc(c.tipo_descripcion)} ${esc(c.numero_formateado)}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  @page { size: ${ancho}mm auto; margin: 0; }
  html { background: #fff; }
  body { font-family: 'Courier New', monospace; font-size: ${ancho === 58 ? "9.5px" : "11px"};
         color: #000; background: #fff; width: ${util}mm; margin: 0 auto; padding: 2mm 0 6mm; }
  .centro { text-align: center; }
  .emisor { font-weight: bold; font-size: ${ancho === 58 ? "11px" : "13px"}; }
  .chico { font-size: ${ancho === 58 ? "8.5px" : "9.5px"}; }
  .sep { border-top: 1px dashed #000; margin: 1.5mm 0; }
  .linea { display: flex; justify-content: space-between; gap: 2mm; }
  .item { margin-bottom: 1mm; }
  .desc { overflow-wrap: anywhere; }
  .imp { white-space: nowrap; }
  .total { font-weight: bold; font-size: ${ancho === 58 ? "13px" : "16px"}; }
  .vuelto { font-weight: bold; }
  .doc { font-weight: bold; font-size: ${ancho === 58 ? "10.5px" : "12px"}; }
  .fisco, .cae { font-size: ${ancho === 58 ? "8px" : "9px"}; margin-top: 1.5mm; }
  .leyenda { text-align: center; font-weight: bold; border: 1px dashed #000;
             padding: 1mm; margin-top: 1.5mm; font-size: ${ancho === 58 ? "8.5px" : "10px"}; }
  .qr { text-align: center; margin-top: 2mm; }
  .qr svg { width: ${ancho === 58 ? "22mm" : "28mm"}; height: ${ancho === 58 ? "22mm" : "28mm"}; }
</style></head><body>
  <div class="centro">
    <div class="emisor">${esc(p.emisor.nombre_fantasia || p.emisor.razon_social)}</div>
    ${p.emisor.nombre_fantasia ? `<div class="chico">${esc(p.emisor.razon_social)}</div>` : ""}
    <div class="chico">${esc(p.emisor.domicilio)}</div>
    <div class="chico">${p.emisor.cuit ? `CUIT ${esc(p.emisor.cuit)} · ` : ""}${esc(p.emisor.condicion_iva)}</div>
    ${p.emisor.iibb ? `<div class="chico">IIBB ${esc(p.emisor.iibb)}</div>` : ""}
  </div>
  <div class="sep"></div>
  <div class="centro doc">${esc(c.tipo_descripcion).toUpperCase()}
    ${p.codigo_arca ? `<span class="chico">(COD. ${String(p.codigo_arca).padStart(2, "0")})</span>` : ""}</div>
  <div class="centro">N° ${esc(c.numero_formateado)}</div>
  <div class="centro chico">${esc(c.fecha)}${cajero ? ` · Cajero: ${esc(cajero)}` : ""}</div>
  <div class="centro chico">${
    c.receptor_nombre === p.receptor_condicion_iva_desc
      ? esc(c.receptor_nombre)
      : `${esc(c.receptor_nombre)} — ${esc(p.receptor_condicion_iva_desc)}`
  }${c.receptor_doc_nro ? ` · ${esc(c.receptor_doc_nro)}` : ""}</div>
  <div class="sep"></div>
  ${filas}
  <div class="sep"></div>
  ${totales}
  <div class="linea total"><span>TOTAL $</span><span>${n(c.total)}</span></div>
  ${medios ? `<div class="sep"></div>${medios}${vuelto}` : ""}
  ${transparencia}
  ${cae}
  ${p.qr_svg ? `<div class="qr">${p.qr_svg}</div>` : ""}
  ${leyendas}
  <div class="centro chico" style="margin-top:2mm">¡Gracias por su compra!</div>
<script>window.onload = () => { window.print(); };</script>
</body></html>`;

  const w = window.open("", "_blank", "width=420,height=720");
  if (!w) return;
  w.document.write(html);
  w.document.close();
}
