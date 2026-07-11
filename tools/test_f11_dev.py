"""Suite en vivo de F11 (Vendedores y comisiones) contra DEV.

Cubre: ABM del rol vendedor sobre la BUE (unicidad, cross-rol), vendedor
habitual del cliente y default en comprobantes/recibos (con override
explícito y validación de tenant), NC espejo que hereda el vendedor,
comisiones pendientes por modalidad venta (las NC restan) y cobranza
(neto de rechazado_total), liquidación como documento (sellado de % y
modalidad, exclusión de ya liquidados, 422 sin pendientes), anulación que
libera los documentos, export CSV y la derivación contable de la
liquidación (asiento comision / reversión comision_anulacion).

Uso:
    python tools/test_f11_dev.py --base http://127.0.0.1:8021 \
        --email demo@zaris.com.ar --clave "..."
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import date, timedelta
from decimal import Decimal

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]
NUM6 = f"{int(SUF, 16) % 1_000_000:06d}"


def _req(method, base, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=120)
        payload = r.read()
        if "json" not in r.headers.get("Content-Type", ""):
            return r.status, payload
        return r.status, (json.loads(payload) if payload else None)
    except E.HTTPError as ex:
        payload = ex.read()
        try:
            return ex.code, json.loads(payload)
        except Exception:
            return ex.code, payload.decode(errors="replace")


def check(nombre, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok  {nombre}")
    else:
        fail += 1
        print(f" FAIL {nombre}  {extra}")


def D(x) -> Decimal:
    return Decimal(str(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print("login FAIL", st, r)
        sys.exit(1)
    tok = r["access_token"]
    print(f"login OK — sufijo {SUF}")
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    # ===== 1. ABM del rol vendedor (BUE) =====
    st, v1 = _req("POST", base, "/vendedores", tok, {
        "entidad": {"razon_social": f"Vende Ventas {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": NUM6, "condicion_iva": "CF"},
        "comision_pct": "5", "modalidad": "venta"})
    check("alta vendedor (modalidad venta) -> 201", st == 201, f"{st} {v1}")
    st, v2 = _req("POST", base, "/vendedores", tok, {
        "entidad": {"razon_social": f"Vende Cobranza {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": str(int(NUM6) + 1).zfill(6),
                    "condicion_iva": "CF"},
        "comision_pct": "2", "modalidad": "cobranza"})
    check("alta vendedor (modalidad cobranza) -> 201", st == 201, f"{st} {v2}")
    st, r2 = _req("POST", base, "/vendedores", tok, {"entidad_id": v1["entidad"]["id"],
                                                     "comision_pct": "1"})
    check("entidad ya vendedor -> 409", st == 409, f"{st}")
    st, lista = _req("GET", base, f"/vendedores?q={NUM6}", tok)
    check("listado con búsqueda", st == 200 and len(lista) >= 1, f"{st}")
    st, v1b = _req("PUT", base, f"/vendedores/{v1['id']}", tok, {"comision_pct": "10"})
    check("editar % -> 200", st == 200 and D(v1b["comision_pct"]) == 10, f"{st}")

    # ===== 2. Cliente con vendedor habitual + default en documentos =====
    st, cli = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente F11 {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": str(int(NUM6) + 2).zfill(6),
                    "condicion_iva": "CF"},
        "vendedor_id": v1["id"]})
    check("cliente con vendedor habitual -> 201", st == 201 and cli["vendedor_id"] == v1["id"], f"{st}")
    st, r2 = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Mal {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": str(int(NUM6) + 3).zfill(6),
                    "condicion_iva": "CF"},
        "vendedor_id": str(uuid.uuid4())})
    check("vendedor inexistente en cliente -> 422", st == 422, f"{st}")

    st, art = _req("POST", base, "/articulos", tok, {
        "codigo": f"F11{SUF}", "descripcion": f"Artículo F11 {SUF}",
        "costo": "100.00", "tasa_iva": "21", "precio_1": "242.00"})
    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    pv_id = pvs[0]["id"]

    # venta SIN vendedor explícito → hereda el habitual del cliente
    st, vb = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli["id"], "contado": True,
        "precios_con_iva": True,
        "items": [{"articulo_id": art["id"], "cantidad": "2", "precio_unitario": "121.00", "tasa_iva": "21"}]})
    check("borrador hereda vendedor del cliente", st == 201 and vb["vendedor_id"] == v1["id"], f"{st} {vb.get('vendedor_id')}")
    st, f1 = _req("POST", base, f"/ventas/comprobantes/{vb['id']}/emitir", tok,
                  {"medios": [{"medio": "efectivo", "importe": vb["total"]}]})
    check("factura emitida con vendedor", st == 200 and f1["vendedor_id"] == v1["id"], f"{st}")

    # venta con vendedor EXPLÍCITO distinto
    st, vb2 = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli["id"], "contado": True,
        "precios_con_iva": True, "vendedor_id": v2["id"],
        "items": [{"articulo_id": art["id"], "cantidad": "1", "precio_unitario": "121.00", "tasa_iva": "21"}]})
    check("override explícito de vendedor", st == 201 and vb2["vendedor_id"] == v2["id"], f"{st}")
    st, f2 = _req("POST", base, f"/ventas/comprobantes/{vb2['id']}/emitir", tok,
                  {"medios": [{"medio": "efectivo", "importe": vb2["total"]}]})
    st, r2 = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli["id"], "contado": True,
        "vendedor_id": str(uuid.uuid4()),
        "items": [{"articulo_id": art["id"], "cantidad": "1", "precio_unitario": "10", "tasa_iva": "21"}]})
    check("vendedor inexistente en venta -> 422", st == 422, f"{st}")

    # ===== 3. Pendientes modalidad VENTA (neto × signo; la NC resta) =====
    st, pend = _req("GET", base,
                    f"/vendedores/{v1['id']}/comisiones/pendientes?desde={ayer}&hasta={hoy}", tok)
    check("pendientes venta: solo la factura del vendedor 1",
          st == 200 and len(pend) == 1 and pend[0]["comprobante_id"] == f1["id"], f"{st} n={len(pend)}")
    neto_f1 = D(f1["neto_gravado"])
    check("base = neto gravado", D(pend[0]["base"]) == neto_f1, f"{pend[0]['base']} vs {neto_f1}")
    check("importe = base × 10%", D(pend[0]["importe"]) == (neto_f1 * 10 / 100).quantize(Decimal("0.01")),
          pend[0]["importe"])

    # NC espejo hereda el vendedor y aparece restando (nace borrador → emitir)
    st, nc = _req("POST", base, f"/ventas/comprobantes/{f1['id']}/nota-credito", tok)
    check("NC espejo hereda vendedor", st in (200, 201) and nc["vendedor_id"] == v1["id"],
          f"{st} {nc.get('vendedor_id') if isinstance(nc, dict) else nc}")
    st, nc = _req("POST", base, f"/ventas/comprobantes/{nc['id']}/emitir", tok, {})
    check("NC espejo emitida", st == 200, f"{st} {nc if st != 200 else ''}")
    st, pend2 = _req("GET", base,
                     f"/vendedores/{v1['id']}/comisiones/pendientes?desde={ayer}&hasta={hoy}", tok)
    total_pend = sum((D(p["importe"]) for p in pend2), Decimal("0"))
    check("con la NC el neto pendiente queda en 0",
          st == 200 and len(pend2) == 2 and total_pend == 0, f"n={len(pend2)} total={total_pend}")

    # ===== 4. Liquidación modalidad venta (suma 0 tras la NC → liquida igual con 2 ítems) =====
    st, lq0 = _req("POST", base, f"/vendedores/{v1['id']}/liquidaciones", tok,
                   {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("liquidar venta (factura + NC) -> 201",
          st == 201 and len(lq0["items"]) == 2 and D(lq0["total"]) == 0, f"{st}")
    st, pend3 = _req("GET", base,
                     f"/vendedores/{v1['id']}/comisiones/pendientes?desde={ayer}&hasta={hoy}", tok)
    check("liquidados: ya no quedan pendientes", st == 200 and len(pend3) == 0, f"n={len(pend3)}")
    st, r2 = _req("POST", base, f"/vendedores/{v1['id']}/liquidaciones", tok,
                  {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("liquidar sin pendientes -> 422", st == 422, f"{st}")

    # ===== 5. Modalidad COBRANZA: recibo hereda vendedor del cliente... =====
    # cliente con habitual v2 (cobranza)
    st, cli2 = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente Cob {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": str(int(NUM6) + 4).zfill(6),
                    "condicion_iva": "CF"},
        "vendedor_id": v2["id"]})
    st, conds = _req("GET", base, "/ventas/condiciones-venta", tok)
    st, fb = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli2["id"], "contado": False,
        "condicion_venta_id": conds[0]["id"], "precios_con_iva": True,
        "items": [{"articulo_id": art["id"], "cantidad": "1", "precio_unitario": "242.00", "tasa_iva": "21"}]})
    st, fcc = _req("POST", base, f"/ventas/comprobantes/{fb['id']}/emitir", tok, {})
    st, rec = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli2["id"],
        "medios": [{"medio": "efectivo", "importe": fcc["total"]}],
        "imputaciones": [{"comprobante_id": fcc["id"], "importe": fcc["total"]}]})
    check("recibo hereda vendedor del cliente", st == 201 and rec["vendedor_id"] == v2["id"],
          f"{st} {rec.get('vendedor_id') if isinstance(rec, dict) else rec}")

    st, pend_c = _req("GET", base,
                      f"/vendedores/{v2['id']}/comisiones/pendientes?desde={ayer}&hasta={hoy}", tok)
    en_pend = [p for p in pend_c if p["recibo_id"] == rec["id"]]
    check("pendientes cobranza incluyen el recibo",
          st == 200 and len(en_pend) == 1 and D(en_pend[0]["base"]) == D(rec["total"]),
          f"{st} n={len(pend_c)}")
    esperado_c = (D(rec["total"]) * 2 / 100).quantize(Decimal("0.01"))
    check("comisión cobranza = total × 2%", D(en_pend[0]["importe"]) == esperado_c,
          en_pend[0]["importe"])

    # la factura contado del vendedor 2 (modalidad cobranza) NO comisiona por venta
    tiene_f2 = any(p.get("comprobante_id") == f2["id"] for p in pend_c)
    check("modalidad cobranza no lista facturas", not tiene_f2)

    # ===== 6. Liquidar cobranza + anular libera =====
    st, lq = _req("POST", base, f"/vendedores/{v2['id']}/liquidaciones", tok,
                  {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("liquidación cobranza -> 201 con % sellado",
          st == 201 and D(lq["comision_pct"]) == 2 and lq["modalidad"] == "cobranza", f"{st}")
    st, det = _req("GET", base, f"/vendedores/liquidaciones/{lq['id']}", tok)
    check("detalle con ítems", st == 200 and len(det["items"]) >= 1, f"{st}")
    st, csv_b = _req("GET", base, f"/vendedores/liquidaciones/{lq['id']}/export.csv", tok)
    check("export.csv responde", st == 200 and isinstance(csv_b, bytes) and len(csv_b) > 50, f"{st}")

    # cambiar el % del vendedor NO cambia la liquidación sellada
    st, _ = _req("PUT", base, f"/vendedores/{v2['id']}", tok, {"comision_pct": "7"})
    st, det2 = _req("GET", base, f"/vendedores/liquidaciones/{lq['id']}", tok)
    check("el % queda sellado en el documento", D(det2["comision_pct"]) == 2, det2["comision_pct"])

    # ===== 7. Derivación contable de la liquidación =====
    st, gen = _req("POST", base, "/contabilidad/regenerar", tok,
                   {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("regenerar con liquidaciones", st == 200, f"{st} {gen}")
    st, asientos = _req("GET", base,
                        f"/contabilidad/asientos?desde={ayer}&hasta={hoy}&origen=comision&limit=50", tok)
    a_lq = next((a for a in asientos if f"LC-{lq['numero']:08d}" in (a["descripcion"] or "")), None)
    check("asiento de comisión derivado", a_lq is not None, f"n={len(asientos)}")
    if a_lq:
        debe_gasto = sum(D(l["debe"]) for l in a_lq["lineas"] if l["cuenta_codigo"] == "5.1.09")
        haber_pasivo = sum(D(l["haber"]) for l in a_lq["lineas"] if l["cuenta_codigo"] == "2.1.03")
        check("debe 5.1.09 / haber 2.1.03 por el total",
              debe_gasto == D(lq["total"]) and haber_pasivo == D(lq["total"]),
              f"{debe_gasto} {haber_pasivo} vs {lq['total']}")

    # anular → los documentos vuelven a pendientes + reversión contable
    st, anulada = _req("POST", base, f"/vendedores/liquidaciones/{lq['id']}/anular", tok)
    check("anular liquidación -> 200 marcada", st == 200 and anulada["anulada"] is True, f"{st}")
    st, pend4 = _req("GET", base,
                     f"/vendedores/{v2['id']}/comisiones/pendientes?desde={ayer}&hasta={hoy}", tok)
    check("anulada: el recibo vuelve a pendiente",
          any(p.get("recibo_id") == rec["id"] for p in pend4), f"n={len(pend4)}")
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    st, reversiones = _req("GET", base,
                           f"/contabilidad/asientos?desde={ayer}&hasta={hoy}&origen=comision_anulacion&limit=50", tok)
    check("reversión contable de la anulada",
          st == 200 and any(f"LC-{lq['numero']:08d}" in (a["descripcion"] or "") for a in reversiones),
          f"n={len(reversiones)}")

    # ===== 8. Sumas y saldos sigue balanceando =====
    st, sys_ = _req("GET", base, f"/contabilidad/sumas-y-saldos?desde={ayer}&hasta={hoy}", tok)
    check("sumas y saldos balancea con comisiones", st == 200 and sys_["balanceado"] is True, f"{st}")

    print(f"\n===== F11 DEV: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
