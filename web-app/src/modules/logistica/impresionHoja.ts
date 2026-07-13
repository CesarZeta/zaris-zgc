// Impresión de hoja de ruta: HTML autocontenido en ventana nueva → print
// (mismo mecanismo que la impresión de comprobantes). Dirección, cliente,
// teléfono, bultos/observaciones y columna para firma (diseño §2.1).

import type { HojaRuta } from "../../lib/types";

function esc(s: string | null | undefined): string {
  return (s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function imprimirHojaRuta(h: HojaRuta, empresa: string): void {
  const filas = (h.entregas ?? [])
    .map(
      (e, i) => `<tr>
        <td class="num mono">${i + 1}</td>
        <td class="mono">${esc(e.comprobante_desc)}</td>
        <td>${esc(e.destinatario)}</td>
        <td>${esc(e.domicilio)}${e.localidad ? `, ${esc(e.localidad)}` : ""}</td>
        <td class="mono">${esc(e.telefono) || "—"}</td>
        <td>${esc(e.bultos) || "—"}</td>
        <td>${esc(e.observaciones) || ""}</td>
        <td class="firma"></td>
      </tr>`,
    )
    .join("");

  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Hoja de ruta ${esc(h.numero_formateado)}</title>
<style>
  * { box-sizing: border-box; margin: 0; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #111;
         max-width: 280mm; margin: 0 auto; padding: 8mm; }
  .mono { font-family: 'Courier New', monospace; }
  .num { text-align: right; }
  h1 { font-size: 18px; margin-bottom: 2px; }
  .sub { color: #444; margin-bottom: 10px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th, td { border: 1px solid #999; padding: 5px 6px; text-align: left; vertical-align: top; }
  th { background: #eee; font-size: 11px; }
  .firma { width: 34mm; height: 12mm; }
  .pie { margin-top: 14px; display: flex; justify-content: space-between; color: #444; }
  @media print { body { padding: 0; } }
</style></head><body>
<h1>Hoja de ruta ${esc(h.numero_formateado)}</h1>
<div class="sub">
  <b>${esc(empresa)}</b> · Fecha: <span class="mono">${esc(h.fecha)}</span> ·
  Transportista: <b>${esc(h.transportista_nombre)}</b>
  ${h.observaciones ? ` · ${esc(h.observaciones)}` : ""}
</div>
<table>
  <thead><tr>
    <th>#</th><th>Comprobante</th><th>Cliente</th><th>Domicilio</th>
    <th>Teléfono</th><th>Bultos</th><th>Observaciones</th><th>Recibí conforme (firma)</th>
  </tr></thead>
  <tbody>${filas}</tbody>
</table>
<div class="pie">
  <span>Salida: ____:____ &nbsp;&nbsp; Regreso: ____:____</span>
  <span>Firma del transportista: ______________________</span>
</div>
<script>window.print()</script>
</body></html>`;

  const w = window.open("", "_blank", "width=1000,height=700");
  if (!w) return;
  w.document.write(html);
  w.document.close();
}
