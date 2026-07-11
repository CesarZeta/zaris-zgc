"""Suite en vivo de la mini-fase CONTABILIZABILIDAD (migración 014) contra DEV.

Cubre: anulaciones no destructivas (recibo/OP con imputaciones marcadas y saldos
restaurados), rechazo de cheque sin reescribir recibo.total (rechazado_total),
soft-delete de caja/retenciones/cierres/bancos (re-cierre de fecha reabierta),
medios en ventas/compras CONTADO de gestión (con impacto en planilla por deltas),
cuenta bancaria en medios (validación de tenant), y costo sellado en el kardex
(+ fecha del documento en compras backdateadas).

Todo recurso nombrado lleva el sufijo único de la corrida. Las aserciones sobre
agregados del día son por DELTA (regla CLAUDE.md §6).

Uso:
    python tools/test_contab_dev.py --base http://127.0.0.1:8099 \
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


def _cuit_valido(base10: str) -> str:
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    s = sum(int(base10[i]) * mult[i] for i in range(10))
    dv = 11 - (s % 11)
    dv = 0 if dv == 11 else (9 if dv == 10 else dv)
    return base10 + str(dv)


def _req(method, base, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=40)
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


def medio_total(lista, medio) -> Decimal:
    return sum((D(m["total"]) for m in lista if m["medio"] == medio), Decimal("0"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8099")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print("login FAIL", st, r)
        sys.exit(1)
    tok = r["access_token"]
    print(f"login OK — sufijo de corrida {SUF}")
    hoy = date.today()

    # ===== 0. Setup: cliente, proveedor, artículo, cuenta bancaria =====
    st, cli = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente C14 {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": NUM6, "condicion_iva": "CF"},
    })
    check("setup cliente", st in (200, 201), f"{st} {cli}")
    cli_id = cli["id"]

    st, prov = _req("POST", base, "/proveedores", tok, {
        "entidad": {"razon_social": f"Proveedor C14 {SUF}", "tipo_persona": "J",
                    "tipo_documento": "CUIT", "nro_documento": _cuit_valido("30" + NUM6 + "77"),
                    "condicion_iva": "RI"},
    })
    check("setup proveedor", st in (200, 201), f"{st} {prov}")
    prov_id = prov["id"]

    st, art = _req("POST", base, "/articulos", tok, {
        "codigo": f"C14{SUF}", "descripcion": f"Artículo contab {SUF}",
        "costo": "100.00", "costo_con_iva": False, "tasa_iva": "21",
        "precio_1": "242.00",
    })
    check("setup artículo", st in (200, 201), f"{st} {art}")
    art_id = art["id"]

    st, cta = _req("POST", base, "/bancos/cuentas", tok, {
        "banco": f"Banco C14 {SUF}", "tipo": "CC", "numero": f"14-{SUF}",
        "moneda": "ARS", "saldo_inicial": "1000.00",
        "saldo_inicial_fecha": (hoy - timedelta(days=30)).isoformat(),
    })
    check("setup cuenta bancaria (con saldo_inicial_fecha)",
          st == 201 and cta.get("saldo_inicial_fecha") == (hoy - timedelta(days=30)).isoformat(),
          f"{st} {cta}")
    cta_id = cta["id"]

    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    pv_id = pvs[0]["id"]
    st, conds = _req("GET", base, "/ventas/condiciones-venta", tok)
    cond_id = conds[0]["id"] if conds else None

    # planilla ANTES (deltas)
    st, pl0 = _req("GET", base, "/caja/planilla", tok)
    check("planilla base", st == 200, f"{st}")

    # ===== 1. Venta CONTADO de gestión con medios (transferencia + cuenta) =====
    st, borr = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli_id,
        "contado": True, "precios_con_iva": True,
        "items": [{"articulo_id": art_id, "cantidad": "2", "precio_unitario": "242.00",
                   "tasa_iva": "21"}],
    })
    check("borrador venta contado", st == 201, f"{st} {borr}")
    total_venta = borr["total"]

    # medios que no suman el total -> 422
    st, r = _req("POST", base, f"/ventas/comprobantes/{borr['id']}/emitir", tok,
                 {"medios": [{"medio": "efectivo", "importe": "1.00"}]})
    check("emitir con medios que no suman -> 422", st == 422, f"{st} {r}")

    # cuenta bancaria inexistente -> 422
    st, r = _req("POST", base, f"/ventas/comprobantes/{borr['id']}/emitir", tok,
                 {"medios": [{"medio": "transferencia", "importe": total_venta,
                              "cuenta_bancaria_id": str(uuid.uuid4())}]})
    check("emitir con cuenta bancaria inexistente -> 422", st == 422, f"{st} {r}")

    st, fac = _req("POST", base, f"/ventas/comprobantes/{borr['id']}/emitir", tok,
                   {"medios": [{"medio": "transferencia", "importe": total_venta,
                                "cuenta_bancaria_id": cta_id}]})
    check("emitir venta contado con medios", st == 200 and fac["estado"] == "emitido",
          f"{st} {fac}")

    st, pl1 = _req("GET", base, "/caja/planilla", tok)
    delta_transf = medio_total(pl1["ventas_por_medio"], "transferencia") - \
        medio_total(pl0["ventas_por_medio"], "transferencia")
    check("planilla: delta ventas transferencia = total venta",
          delta_transf == D(total_venta), f"delta={delta_transf} esperado={total_venta}")

    # kardex: la venta selló costo (100 neto) y descargó 2
    st, kx = _req("GET", base, f"/stock/kardex/{art_id}", tok)
    mv = kx[0] if st == 200 and kx else {}
    check("kardex venta: costo_unitario sellado = 100.0000",
          mv.get("tipo") == "venta" and mv.get("costo_unitario") == "100.0000", f"{mv}")

    # venta contado SIN medios (compat histórico)
    st, borr2 = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "contado": True,
        "precios_con_iva": True,
        "items": [{"articulo_id": art_id, "cantidad": "1", "precio_unitario": "242.00",
                   "tasa_iva": "21"}],
    })
    st, fac2 = _req("POST", base, f"/ventas/comprobantes/{borr2['id']}/emitir", tok, {})
    check("emitir venta contado sin medios (compat)", st == 200, f"{st} {fac2}")

    # ===== 2. Recibo con cheque -> rechazo SIN reescribir total =====
    st, rec = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli_id,
        "medios": [{"medio": "cheque", "importe": "2500.00",
                    "cheque": {"numero": f"14{SUF[:4]}", "banco": "Banco Nación",
                               "fecha_pago": (hoy + timedelta(days=10)).isoformat()}}],
    })
    check("recibo con cheque materializa cartera", st == 201, f"{st} {rec}")
    check("recibo expone rechazado_total=0 y a_cuenta=2500",
          rec.get("rechazado_total") == "0" and rec.get("a_cuenta") == "2500.00",
          f"{rec.get('rechazado_total')} / {rec.get('a_cuenta')}")
    rec_id = rec["id"]

    st, lista = _req("GET", base, f"/cheques?estado=en_cartera&cliente_id={cli_id}", tok)
    ch = next((c["id"] for c in lista if c["numero"] == f"14{SUF[:4]}"), None)
    st, r = _req("POST", base, f"/cheques/{ch}/rechazar", tok, {"detalle": "Sin fondos"})
    check("rechazar cheque reporta reabierto", st == 200 and r.get("reabierto")
          and r["reabierto"]["importe_revertido"] == "2500.00", f"{st} {r}")

    st, recs = _req("GET", base, f"/cobranzas/recibos?cliente_id={cli_id}", tok)
    rec_post = next((x for x in recs if x["id"] == rec_id), {})
    check("rechazo NO reescribió recibo.total (documento inmutable)",
          rec_post.get("total") == "2500.00", rec_post.get("total"))
    check("rechazado_total=2500 y a_cuenta=0",
          rec_post.get("rechazado_total") == "2500.00" and rec_post.get("a_cuenta") == "0.00",
          f"{rec_post.get('rechazado_total')} / {rec_post.get('a_cuenta')}")

    # ===== 3. Anular recibo: imputaciones marcadas + saldo de deuda restaurado =====
    st, fcc = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli_id,
        "contado": False, "condicion_venta_id": cond_id, "precios_con_iva": True,
        "items": [{"articulo_id": art_id, "cantidad": "1", "precio_unitario": "242.00",
                   "tasa_iva": "21"}],
    })
    st, fcc = _req("POST", base, f"/ventas/comprobantes/{fcc['id']}/emitir", tok, {})
    check("factura cta cte emitida con saldo", st == 200 and fcc["saldo"] == fcc["total"],
          f"{st} {fcc.get('saldo')}")

    st, rec2 = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli_id,
        "medios": [{"medio": "efectivo", "importe": fcc["total"]}],
        "imputaciones": [{"comprobante_id": fcc["id"], "importe": fcc["total"]}],
    })
    check("recibo imputado a la factura", st == 201 and rec2["aplicado"] == fcc["total"],
          f"{st} {rec2}")

    st, r = _req("POST", base, f"/cobranzas/recibos/{rec2['id']}/anular", tok)
    check("anular recibo", st == 200 and r["estado"] == "anulado", f"{st} {r}")
    st, det = _req("GET", base, f"/ventas/comprobantes/{fcc['id']}", tok)
    check("anular recibo restauró el saldo de la factura",
          det.get("saldo") == det.get("total"), f"{det.get('saldo')} vs {det.get('total')}")

    # ===== 4. Compra CONTADO con medios (efectivo) -> planilla global =====
    st, plc0 = _req("GET", base, "/caja/planilla", tok)
    st, cborr = _req("POST", base, "/compras/comprobantes", tok, {
        "clase": "factura", "letra": "A", "punto_venta": 14,
        "numero": int(NUM6), "proveedor_id": prov_id, "contado": True,
        "items": [{"articulo_id": art_id, "cantidad": "3", "costo_unitario": "90.00",
                   "tasa_iva": "21"}],
    })
    check("borrador compra contado", st == 201, f"{st} {cborr}")

    st, r = _req("POST", base, f"/compras/comprobantes/{cborr['id']}/registrar", tok,
                 {"medios": [{"medio": "efectivo", "importe": "1.00"}]})
    check("registrar compra con medios que no suman -> 422", st == 422, f"{st} {r}")

    st, creg = _req("POST", base, f"/compras/comprobantes/{cborr['id']}/registrar", tok,
                    {"medios": [{"medio": "efectivo", "importe": cborr["total"]}]})
    check("registrar compra contado con medios", st == 200 and creg["estado"] == "registrado",
          f"{st} {creg}")
    check("detalle compra trae medios", len(creg.get("medios", [])) == 1
          and creg["medios"][0]["medio"] == "efectivo", creg.get("medios"))

    st, plc1 = _req("GET", base, "/caja/planilla", tok)
    delta_pago_ef = medio_total(plc1["pagos"], "efectivo") - medio_total(plc0["pagos"], "efectivo")
    check("planilla: compra contado efectivo entró en pagos",
          delta_pago_ef == D(creg["total"]), f"delta={delta_pago_ef} esperado={creg['total']}")
    delta_salidas = D(plc1["salidas_efectivo"]) - D(plc0["salidas_efectivo"])
    check("planilla: salidas_efectivo suman la compra contado",
          delta_salidas == D(creg["total"]), f"delta={delta_salidas}")

    # kardex compra: costo REAL neto (90) sellado
    st, kx = _req("GET", base, f"/stock/kardex/{art_id}", tok)
    mv = next((m for m in kx if m["tipo"] == "compra"), {})
    check("kardex compra: costo real sellado = 90.0000",
          mv.get("costo_unitario") == "90.0000", f"{mv}")

    # ===== 5. Compra backdateada: kardex con fecha del papel =====
    ayer5 = (hoy - timedelta(days=5)).isoformat()
    st, cb = _req("POST", base, "/compras/comprobantes", tok, {
        "clase": "factura", "letra": "A", "punto_venta": 14,
        "numero": int(NUM6) + 1, "proveedor_id": prov_id, "contado": True,
        "fecha": ayer5,
        "items": [{"articulo_id": art_id, "cantidad": "1", "costo_unitario": "80.00",
                   "tasa_iva": "21"}],
    })
    st, cbr = _req("POST", base, f"/compras/comprobantes/{cb['id']}/registrar", tok, {})
    check("compra backdateada registrada (sin medios, compat)", st == 200, f"{st} {cbr}")
    st, kx = _req("GET", base, f"/stock/kardex/{art_id}", tok)
    mv = next((m for m in kx if m.get("costo_unitario") == "80.0000"), {})
    check("kardex backdate: fecha del movimiento = fecha del papel",
          (mv.get("fecha") or "").startswith(ayer5), f"{mv.get('fecha')}")

    # ===== 6. OP imputada -> anular: saldo restaurado =====
    st, ccc = _req("POST", base, "/compras/comprobantes", tok, {
        "clase": "factura", "letra": "A", "punto_venta": 14,
        "numero": int(NUM6) + 2, "proveedor_id": prov_id, "contado": False,
        "condicion_compra_id": cond_id,
        "items": [{"articulo_id": art_id, "cantidad": "2", "costo_unitario": "90.00",
                   "tasa_iva": "21"}],
    })
    st, ccc = _req("POST", base, f"/compras/comprobantes/{ccc['id']}/registrar", tok, {})
    check("compra cta cte registrada con saldo", st == 200 and ccc["saldo"] == ccc["total"],
          f"{st}")

    st, op = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov_id,
        "medios": [{"medio": "transferencia", "importe": ccc["total"],
                    "cuenta_bancaria_id": cta_id}],
        "imputaciones": [{"compra_id": ccc["id"], "importe": ccc["total"]}],
    })
    check("OP con transferencia + cuenta bancaria", st == 201, f"{st} {op}")
    check("OP devuelve cuenta_bancaria_id en medios",
          op["medios"][0].get("cuenta_bancaria_id") == cta_id, op.get("medios"))

    st, r = _req("POST", base, f"/compras/pagos/ordenes-pago/{op['id']}/anular", tok)
    check("anular OP", st == 200 and r["estado"] == "anulada", f"{st} {r}")
    st, det = _req("GET", base, f"/compras/comprobantes/{ccc['id']}", tok)
    check("anular OP restauró el saldo de la compra",
          det.get("saldo") == det.get("total"), f"{det.get('saldo')} vs {det.get('total')}")
    # tras anular la OP, la compra puede anularse (las imputaciones anuladas no bloquean)
    st, r = _req("POST", base, f"/compras/comprobantes/{ccc['id']}/anular", tok)
    check("compra anulable tras anular la OP (imputaciones marcadas no bloquean)",
          st == 200 and r["estado"] == "anulado", f"{st} {r}")

    # ===== 7. Caja: soft-delete de movimiento + cierre reabrible y re-cerrable =====
    st, cc = _req("POST", base, "/caja/conceptos", tok,
                  {"nombre": f"Gasto C14 {SUF}", "tipo": "salida"})
    conc_id = cc["id"] if st == 201 else None
    check("concepto de caja", st == 201, f"{st} {cc}")

    st, plm0 = _req("GET", base, "/caja/planilla", tok)
    st, mv1 = _req("POST", base, "/caja/movimientos", tok, {
        "concepto_id": conc_id, "medio": "efectivo", "importe": "111.00",
        "descripcion": f"mov C14 {SUF}",
    })
    check("movimiento manual de caja", st == 201, f"{st} {mv1}")
    st, _ = _req("DELETE", base, f"/caja/movimientos/{mv1['id']}", tok)
    check("eliminar movimiento (soft)", st == 204, f"{st}")
    st, plm1 = _req("GET", base, "/caja/planilla", tok)
    check("planilla: el movimiento anulado no cuenta",
          D(plm1["salidas_efectivo"]) - D(plm0["salidas_efectivo"]) == 0,
          f"{plm0['salidas_efectivo']} -> {plm1['salidas_efectivo']}")
    st, movs = _req("GET", base, "/caja/movimientos?desde=%s&hasta=%s" % (hoy, hoy), tok)
    check("listado no muestra el movimiento anulado",
          all(m["id"] != mv1["id"] for m in movs), "aparece")

    # transferencia con cuenta bancaria en caja
    st, mv2 = _req("POST", base, "/caja/movimientos", tok, {
        "concepto_id": conc_id, "medio": "transferencia", "importe": "50.00",
        "cuenta_bancaria_id": cta_id,
    })
    check("movimiento de caja con cuenta bancaria", st == 201
          and mv2.get("cuenta_bancaria_id") == cta_id, f"{st} {mv2}")

    # cierre en fecha vieja única -> reabrir -> re-cerrar (unique parcial 014)
    fvieja = (date(2020, 1, 1) + timedelta(days=int(SUF, 16) % 300)).isoformat()
    st, ci1 = _req("POST", base, "/caja/cierres", tok,
                   {"fecha": fvieja, "efectivo_contado": "0"})
    check("cierre de fecha vieja", st == 201, f"{st} {ci1}")
    st, _ = _req("DELETE", base, f"/caja/cierres/{ci1['id']}", tok)
    check("reabrir (marca, no borra)", st == 204, f"{st}")
    st, ci2 = _req("POST", base, "/caja/cierres", tok,
                   {"fecha": fvieja, "efectivo_contado": "0"})
    check("la fecha reabierta puede volver a cerrarse", st == 201, f"{st} {ci2}")
    st, cierres = _req("GET", base, "/caja/cierres?desde=%s&hasta=%s" % (fvieja, fvieja), tok)
    check("listado de cierres muestra solo el vivo",
          len([c for c in cierres if c["fecha"] == fvieja]) == 1, cierres)
    _req("DELETE", base, f"/caja/cierres/{ci2['id']}", tok)  # cleanup

    # ===== 8. Retenciones: soft-delete =====
    st, res0 = _req("GET", base, "/libros/retenciones/resumen", tok)
    st, ret = _req("POST", base, "/libros/retenciones", tok, {
        "tipo": "sufrida", "regimen": "IVA", "importe": "123.45", "cliente_id": cli_id,
    })
    check("alta retención", st == 201, f"{st} {ret}")
    st, _ = _req("DELETE", base, f"/libros/retenciones/{ret['id']}", tok)
    check("eliminar retención (soft)", st == 204, f"{st}")
    st, res1 = _req("GET", base, "/libros/retenciones/resumen", tok)

    def _tot(res):
        return sum((D(x["total"]) for x in res if x["tipo"] == "sufrida"
                    and x["regimen"] == "IVA"), Decimal("0"))
    check("resumen de retenciones no cuenta la anulada", _tot(res1) == _tot(res0),
          f"{_tot(res0)} -> {_tot(res1)}")

    # ===== 9. Bancos: soft-delete de movimiento manual =====
    st, det0 = _req("GET", base, f"/bancos/cuentas/{cta_id}", tok)
    st, bm = _req("POST", base, f"/bancos/cuentas/{cta_id}/movimientos", tok,
                  {"tipo": "credito", "importe": "700.00"})
    check("movimiento bancario manual", st == 201, f"{st} {bm}")
    st, _ = _req("DELETE", base, f"/bancos/movimientos/{bm['id']}", tok)
    check("eliminar movimiento bancario (soft)", st == 204, f"{st}")
    st, det1 = _req("GET", base, f"/bancos/cuentas/{cta_id}", tok)
    check("saldo bancario no cuenta el movimiento anulado",
          det1["saldo_actual"] == det0["saldo_actual"],
          f"{det0['saldo_actual']} -> {det1['saldo_actual']}")

    # ===== 10. Ajuste de stock: costo sellado =====
    st, deps = _req("GET", base, "/catalogos-articulos/depositos", tok)
    dep_id = deps[0]["id"]
    st, aj = _req("POST", base, "/stock/ajuste", tok, {
        "articulo_id": art_id, "deposito_id": dep_id, "delta": "5",
    })
    # las compras de la suite actualizaron articulos.costo a 90 (la última con
    # actualiza_costos fue la de 90; la anulación NO revierte costos, criterio F4)
    check("ajuste de stock sella el costo vigente (90 neto)", st == 201
          and aj.get("costo_unitario") == "90.0000", f"{st} {aj}")

    print(f"\n===== {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
