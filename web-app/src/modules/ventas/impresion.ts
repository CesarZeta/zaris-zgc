// Impresión de comprobantes: HTML autocontenido en ventana nueva → print.
// El backend entrega TODO (emisor, receptor, ítems, CAE, QR, leyendas) en
// /ventas/comprobantes/{id}/impresion — acá solo se maqueta (RG 1415 + QR
// RG 4892 + transparencia fiscal Ley 27.743). Sin dependencias externas.

import type { ImpresionPayload } from "../../lib/types";

const fmt = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2 });
const n = (v: string | null | undefined) => fmt.format(Number(v ?? 0));

function esc(s: string | null | undefined): string {
  return (s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function imprimirComprobante(p: ImpresionPayload): void {
  const c = p.comprobante;
  const discrimina = p.discrimina_iva;

  const filas = (c.items ?? [])
    .map(
      (i) => `<tr>
        <td class="mono">${esc(i.codigo) || "—"}</td>
        <td>${esc(i.descripcion)}</td>
        <td class="num mono">${fmt.format(Number(i.cantidad))}</td>
        <td class="num mono">${n(i.precio_unitario)}</td>
        <td class="num mono">${Number(i.bonif_pct) > 0 ? `${i.bonif_pct}%` : "—"}</td>
        ${discrimina ? `<td class="num mono">${i.tasa_iva}%</td>` : ""}
        <td class="num mono">${n(discrimina ? i.importe_neto : i.importe_total)}</td>
      </tr>`,
    )
    .join("");

  const alicuotas = discrimina
    ? (c.alicuotas ?? [])
        .map(
          (a) =>
            `<div class="tot-linea"><span>IVA ${a.tasa}% (base ${n(a.base)})</span><span class="mono">${n(a.importe)}</span></div>`,
        )
        .join("")
    : "";

  const transparencia = p.transparencia_fiscal
    ? `<div class="transparencia">
        <b>${esc(p.transparencia_fiscal.titulo)}</b><br/>
        IVA Contenido: $ ${n(p.transparencia_fiscal.iva_contenido)} ·
        Otros Impuestos Nacionales Indirectos: $ ${n(p.transparencia_fiscal.otros_impuestos_nacionales_indirectos)}
      </div>`
    : "";

  const cae = c.cae
    ? `<div class="cae"><b>CAE:</b> <span class="mono">${esc(c.cae)}</span> ·
       <b>Vto. CAE:</b> <span class="mono">${esc(c.cae_vencimiento)}</span></div>`
    : "";

  const leyendas = p.leyendas
    .map((l) => `<div class="leyenda">${esc(l)}</div>`)
    .join("");

  const vencimientos =
    (c.vencimientos ?? []).length > 0
      ? `<div class="vtos"><b>Vencimientos:</b> ${(c.vencimientos ?? [])
          .map((v) => `cuota ${v.nro_cuota}: ${esc(v.fecha_vto)} $ ${n(v.importe)}`)
          .join(" · ")}</div>`
      : "";

  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>${esc(c.tipo_descripcion)} ${esc(c.numero_formateado)}</title>
<style>
  * { box-sizing: border-box; margin: 0; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #111;
         max-width: 210mm; margin: 0 auto; padding: 10mm; }
  .mono { font-family: 'Courier New', monospace; }
  .num { text-align: right; }
  .cabecera { display: flex; border: 1.5px solid #111; position: relative; }
  .caja-letra { position: absolute; left: 50%; top: 0; transform: translateX(-50%);
    border: 1.5px solid #111; border-top: none; width: 15mm; height: 15mm;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: #fff; font-weight: bold; }
  .caja-letra .letra { font-size: 24px; line-height: 1; }
  .caja-letra .cod { font-size: 8px; }
  .col { flex: 1; padding: 6mm 5mm 4mm; }
  .col + .col { border-left: 1px solid transparent; }
  .col.der { text-align: right; }
  .emisor-nombre { font-size: 17px; font-weight: bold; }
  .doc-titulo { font-size: 16px; font-weight: bold; }
  .receptor { border: 1px solid #111; border-top: none; padding: 3mm 5mm; }
  table { width: 100%; border-collapse: collapse; margin-top: 4mm; }
  th { border-bottom: 1.2px solid #111; text-align: left; padding: 2mm 1.5mm; font-size: 11px; }
  th.num { text-align: right; }
  td { padding: 1.6mm 1.5mm; border-bottom: 0.5px solid #bbb; vertical-align: top; }
  .totales { margin-top: 4mm; margin-left: auto; width: 70mm; }
  .tot-linea { display: flex; justify-content: space-between; padding: 1mm 0; }
  .tot-final { border-top: 1.2px solid #111; font-weight: bold; font-size: 15px; }
  .transparencia { margin-top: 4mm; border: 1px solid #111; padding: 2.5mm; font-size: 10.5px; }
  .leyenda { margin-top: 3mm; text-align: center; font-weight: bold; font-size: 13px;
             border: 1.5px dashed #111; padding: 2mm; }
  .pie { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 6mm; }
  .cae { font-size: 12px; }
  .vtos, .obs { margin-top: 3mm; font-size: 10.5px; }
  .qr svg { width: 30mm; height: 30mm; }
  @media print { body { padding: 4mm; } }
</style></head><body>
  <div class="cabecera">
    <div class="caja-letra"><span class="letra">${esc(c.letra)}</span>
      ${p.codigo_arca ? `<span class="cod">COD. ${String(p.codigo_arca).padStart(2, "0")}</span>` : ""}
    </div>
    <div class="col">
      <div class="emisor-nombre">${esc(p.emisor.razon_social)}</div>
      ${p.emisor.nombre_fantasia ? `<div>${esc(p.emisor.nombre_fantasia)}</div>` : ""}
      <div>${esc(p.emisor.domicilio)}</div>
      <div>${esc(p.emisor.condicion_iva)}</div>
    </div>
    <div class="col der">
      <div class="doc-titulo">${esc(c.tipo_descripcion).toUpperCase()}</div>
      <div class="mono"><b>N° ${esc(c.numero_formateado)}</b></div>
      <div>Fecha: <span class="mono">${esc(c.fecha)}</span></div>
      ${p.emisor.cuit ? `<div>CUIT: <span class="mono">${esc(p.emisor.cuit)}</span></div>` : ""}
      ${p.emisor.iibb ? `<div>IIBB: <span class="mono">${esc(p.emisor.iibb)}</span></div>` : ""}
      ${p.emisor.inicio_actividades ? `<div>Inicio de actividades: <span class="mono">${esc(p.emisor.inicio_actividades)}</span></div>` : ""}
    </div>
  </div>
  <div class="receptor">
    <b>${esc(c.receptor_nombre)}</b> — ${esc(p.receptor_condicion_iva_desc)}
    ${c.receptor_doc_nro ? ` · Doc: <span class="mono">${esc(c.receptor_doc_nro)}</span>` : ""}
    ${c.condicion_venta_desc ? ` · ${esc(c.condicion_venta_desc)}` : c.contado ? " · Contado" : ""}
  </div>
  <table>
    <thead><tr>
      <th>Código</th><th>Descripción</th><th class="num">Cant.</th>
      <th class="num">P. unit.</th><th class="num">Bonif.</th>
      ${discrimina ? '<th class="num">IVA</th>' : ""}
      <th class="num">Importe</th>
    </tr></thead>
    <tbody>${filas}</tbody>
  </table>
  <div class="totales">
    ${discrimina ? `<div class="tot-linea"><span>Neto gravado</span><span class="mono">${n(c.neto_gravado)}</span></div>${alicuotas}` : ""}
    <div class="tot-linea tot-final"><span>TOTAL $</span><span class="mono">${n(c.total)}</span></div>
  </div>
  ${transparencia}
  ${vencimientos}
  ${c.observaciones ? `<div class="obs">${esc(c.observaciones)}</div>` : ""}
  ${leyendas}
  <div class="pie">
    <div>${cae}</div>
    ${p.qr_svg ? `<div class="qr">${p.qr_svg}</div>` : ""}
  </div>
<script>window.onload = () => { window.print(); };</script>
</body></html>`;

  const w = window.open("", "_blank", "width=880,height=1100");
  if (!w) return;
  w.document.write(html);
  w.document.close();
}
