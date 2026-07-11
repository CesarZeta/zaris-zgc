"""Suite en vivo de la Fase 9 (Contabilidad derivada) contra DEV.

Cubre: seed lazy del plan + mapeos, derivación de venta/recibo/compra/OP/caja/
retención/ajuste con partida doble balanceada, reversión de anulados,
idempotencia de la regeneración, asiento manual (validaciones + anulación
marcada), cierre/reapertura de período, export CSV y la PRUEBA DE FUEGO del
diseño: regenerar la historia completa del tenant demo sin tocar ningún módulo
operativo, con sumas y saldos balanceados.

Uso:
    python tools/test_f9_dev.py --base http://127.0.0.1:8099 \
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


def balanceado(asiento) -> bool:
    debe = sum((D(l["debe"]) for l in asiento["lineas"]), Decimal("0"))
    haber = sum((D(l["haber"]) for l in asiento["lineas"]), Decimal("0"))
    return debe == haber and debe > 0


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
    print(f"login OK — sufijo {SUF}")
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    # ===== 1. Seed lazy del plan + mapeos =====
    st, plan = _req("GET", base, "/contabilidad/plan", tok)
    check("GET /plan siembra el plan base", st == 200 and len(plan) >= 35, f"{st} n={len(plan) if isinstance(plan, list) else plan}")
    st, plan2 = _req("GET", base, "/contabilidad/plan", tok)
    check("seed idempotente", len(plan2) == len(plan), f"{len(plan)} vs {len(plan2)}")
    cuenta = {c["codigo"]: c for c in plan}
    st, mapeos = _req("GET", base, "/contabilidad/mapeos", tok)
    check("mapeos default sembrados", st == 200 and len(mapeos) >= 35, f"{st} n={len(mapeos) if isinstance(mapeos, list) else mapeos}")
    st, origenes = _req("GET", base, "/contabilidad/origenes", tok)
    check("catálogo de orígenes", st == 200 and len(origenes) >= 15, f"{st}")

    # ===== 2. Operaciones frescas para derivar =====
    st, cli = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente F9 {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": NUM6, "condicion_iva": "CF"}})
    cli_id = cli["id"]
    st, prov = _req("POST", base, "/proveedores", tok, {
        "entidad": {"razon_social": f"Proveedor F9 {SUF}", "tipo_persona": "J",
                    "tipo_documento": "CUIT", "nro_documento": _cuit_valido("30" + NUM6 + "55"),
                    "condicion_iva": "RI"}})
    prov_id = prov["id"]
    st, art = _req("POST", base, "/articulos", tok, {
        "codigo": f"F9{SUF}", "descripcion": f"Artículo F9 {SUF}",
        "costo": "100.00", "tasa_iva": "21", "precio_1": "242.00"})
    art_id = art["id"]
    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    pv_id = pvs[0]["id"]
    st, conds = _req("GET", base, "/ventas/condiciones-venta", tok)
    cond_id = conds[0]["id"]

    # venta contado con medios efectivo
    st, vb = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli_id, "contado": True,
        "precios_con_iva": True,
        "items": [{"articulo_id": art_id, "cantidad": "2", "precio_unitario": "242.00", "tasa_iva": "21"}]})
    st, venta = _req("POST", base, f"/ventas/comprobantes/{vb['id']}/emitir", tok,
                     {"medios": [{"medio": "efectivo", "importe": vb["total"]}]})
    check("venta contado emitida", st == 200, f"{st} {venta}")

    # factura cta cte + recibo imputado (que después se anula)
    st, fb = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli_id, "contado": False,
        "condicion_venta_id": cond_id, "precios_con_iva": True,
        "items": [{"articulo_id": art_id, "cantidad": "1", "precio_unitario": "242.00", "tasa_iva": "21"}]})
    st, fcc = _req("POST", base, f"/ventas/comprobantes/{fb['id']}/emitir", tok, {})
    st, rec = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli_id,
        "medios": [{"medio": "efectivo", "importe": fcc["total"]}],
        "imputaciones": [{"comprobante_id": fcc["id"], "importe": fcc["total"]}]})
    check("recibo imputado", st == 201, f"{st} {rec}")

    # compra contado con medios + compra cta cte + OP
    st, cb = _req("POST", base, "/compras/comprobantes", tok, {
        "clase": "factura", "letra": "A", "punto_venta": 9, "numero": int(NUM6),
        "proveedor_id": prov_id, "contado": True,
        "items": [{"articulo_id": art_id, "cantidad": "3", "costo_unitario": "90.00", "tasa_iva": "21"}]})
    st, compra = _req("POST", base, f"/compras/comprobantes/{cb['id']}/registrar", tok,
                      {"medios": [{"medio": "efectivo", "importe": cb["total"]}]})
    check("compra contado registrada", st == 200, f"{st} {compra}")
    st, cb2 = _req("POST", base, "/compras/comprobantes", tok, {
        "clase": "factura", "letra": "A", "punto_venta": 9, "numero": int(NUM6) + 1,
        "proveedor_id": prov_id, "contado": False, "condicion_compra_id": cond_id,
        "items": [{"articulo_id": art_id, "cantidad": "1", "costo_unitario": "90.00", "tasa_iva": "21"}]})
    st, ccc = _req("POST", base, f"/compras/comprobantes/{cb2['id']}/registrar", tok, {})
    st, op = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov_id,
        "medios": [{"medio": "efectivo", "importe": ccc["total"]}],
        "imputaciones": [{"compra_id": ccc["id"], "importe": ccc["total"]}]})
    check("OP emitida", st == 201, f"{st} {op}")

    # caja manual + retención + ajuste de stock
    st, conc = _req("POST", base, "/caja/conceptos", tok, {"nombre": f"Gasto F9 {SUF}", "tipo": "salida"})
    st, mv = _req("POST", base, "/caja/movimientos", tok, {
        "concepto_id": conc["id"], "medio": "efectivo", "importe": "77.00"})
    check("movimiento de caja", st == 201, f"{st}")
    st, ret = _req("POST", base, "/libros/retenciones", tok, {
        "tipo": "sufrida", "regimen": "IVA", "importe": "55.00", "cliente_id": cli_id})
    check("retención sufrida", st == 201, f"{st}")
    st, deps = _req("GET", base, "/catalogos-articulos/depositos", tok)
    st, aj = _req("POST", base, "/stock/ajuste", tok, {
        "articulo_id": art_id, "deposito_id": deps[0]["id"], "delta": "10"})
    check("ajuste de stock", st == 201, f"{st}")

    # ===== 3. Regenerar y validar partida doble =====
    st, gen1 = _req("POST", base, "/contabilidad/regenerar", tok,
                    {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("regenerar", st == 200 and gen1["asientos"] > 0, f"{st} {gen1}")
    if gen1.get("warnings"):
        print(f"      warnings: {gen1['warnings'][:5]}")

    st, asientos = _req("GET", base, f"/contabilidad/asientos?desde={ayer}&hasta={hoy}&limit=200", tok)
    check("asientos listados", st == 200 and len(asientos) >= 8, f"{st} n={len(asientos)}")
    check("TODOS los asientos balancean", all(balanceado(a) for a in asientos),
          [a["descripcion"] for a in asientos if not balanceado(a)][:3])
    # El día es compartido entre corridas y suites: la ventana puede superar el
    # limit del listado (mordió con 351 asientos > limit=200 tras la batería de
    # regresión de F12-a). La presencia de cada origen se consulta con su filtro.
    for esperado in ("venta", "recibo", "compra", "orden_pago", "caja_mov", "retencion", "stock_ajuste"):
        st, del_origen = _req(
            "GET", base,
            f"/contabilidad/asientos?desde={ayer}&hasta={hoy}&limit=1&origen={esperado}", tok)
        check(f"derivó origen {esperado}", st == 200 and len(del_origen) >= 1, f"{st}")

    # la venta contado derivó CMV (línea a la cuenta 5.1.01)
    venta_asientos = [a for a in asientos if a["origen_tipo"] == "venta"]
    tiene_cmv = any(
        any(l["cuenta_codigo"] == "5.1.01" and D(l["debe"]) > 0 for l in a["lineas"])
        for a in venta_asientos
    )
    check("la venta deriva CMV contra Mercaderías (costo sellado 014)", tiene_cmv,
          [a["descripcion"] for a in venta_asientos])

    # idempotencia: re-regenerar el mismo rango produce el mismo total
    st, gen2 = _req("POST", base, "/contabilidad/regenerar", tok,
                    {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("regeneración idempotente", gen2["asientos"] == gen1["asientos"],
          f"{gen1['asientos']} vs {gen2['asientos']}")

    # ===== 4. Reversión de anulados =====
    st, _ = _req("POST", base, f"/cobranzas/recibos/{rec['id']}/anular", tok)
    st, gen3 = _req("POST", base, "/contabilidad/regenerar", tok,
                    {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("regenerar tras anular recibo suma la reversión",
          gen3["asientos"] == gen1["asientos"] + 1, f"{gen1['asientos']} -> {gen3['asientos']}")
    st, asientos = _req("GET", base, f"/contabilidad/asientos?desde={ayer}&hasta={hoy}&limit=200&origen=recibo_anulacion", tok)
    check("asiento de reversión presente y balanceado",
          len(asientos) >= 1 and all(balanceado(a) for a in asientos), f"n={len(asientos)}")

    # ===== 5. Sumas y saldos + mayor =====
    st, sys_ = _req("GET", base, f"/contabilidad/sumas-y-saldos?desde={ayer}&hasta={hoy}", tok)
    check("sumas y saldos balancea", st == 200 and sys_["balanceado"] is True,
          f"{st} {sys_.get('total_debe')} vs {sys_.get('total_haber')}")
    st, mayor = _req("GET", base, f"/contabilidad/mayor/{cuenta['4.1.01']['id']}?desde={ayer}&hasta={hoy}", tok)
    check("mayor de Ventas con movimientos y saldo acreedor",
          st == 200 and len(mayor["movimientos"]) >= 1 and D(mayor["saldo"]) < 0,
          f"{st} n={len(mayor.get('movimientos', []))} saldo={mayor.get('saldo')}")

    # ===== 6. Asiento manual =====
    st, r = _req("POST", base, "/contabilidad/asientos", tok, {
        "fecha": hoy.isoformat(), "descripcion": f"Manual desbalanceado {SUF}",
        "lineas": [{"cuenta_id": cuenta["1.1.01"]["id"], "debe": "10", "haber": "0"},
                   {"cuenta_id": cuenta["4.1.02"]["id"], "debe": "0", "haber": "9"}]})
    check("manual desbalanceado -> 422", st == 422, f"{st}")
    st, man = _req("POST", base, "/contabilidad/asientos", tok, {
        "fecha": hoy.isoformat(), "descripcion": f"Asiento manual {SUF}",
        "lineas": [{"cuenta_id": cuenta["1.1.01"]["id"], "debe": "10", "haber": "0"},
                   {"cuenta_id": cuenta["4.1.02"]["id"], "debe": "0", "haber": "10"}]})
    check("manual balanceado -> 201", st == 201 and man["origen_tipo"] == "manual", f"{st}")
    st, gen4 = _req("POST", base, "/contabilidad/regenerar", tok,
                    {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    st, det = _req("GET", base, f"/contabilidad/asientos/{man['id']}", tok)
    check("la regeneración NO toca los manuales", st == 200 and det["descripcion"] == f"Asiento manual {SUF}", f"{st}")
    st, anulado = _req("POST", base, f"/contabilidad/asientos/{man['id']}/anular", tok)
    check("anular manual = marcar", st == 200 and anulado["anulado"] is True, f"{st}")
    st, det = _req("GET", base, f"/contabilidad/asientos/{man['id']}", tok)
    check("el manual anulado sigue legible (historia)", st == 200 and det["anulado"], f"{st}")

    # ===== 7. Cierre de período =====
    st, per = _req("POST", base, "/contabilidad/periodos/cerrar", tok, {"periodo": hoy.isoformat()})
    check("cerrar período", st == 201, f"{st} {per}")
    st, r = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": ayer.isoformat(), "hasta": hoy.isoformat()})
    check("regenerar sobre período cerrado -> 409", st == 409, f"{st}")
    st, r = _req("POST", base, "/contabilidad/asientos", tok, {
        "fecha": hoy.isoformat(), "descripcion": "no debería entrar",
        "lineas": [{"cuenta_id": cuenta["1.1.01"]["id"], "debe": "1", "haber": "0"},
                   {"cuenta_id": cuenta["4.1.02"]["id"], "debe": "0", "haber": "1"}]})
    check("manual en período cerrado -> 409", st == 409, f"{st}")
    st, r = _req("POST", base, f"/contabilidad/periodos/{per['id']}/reabrir", tok, {})
    check("reabrir período", st == 200, f"{st}")

    # ===== 8. Export CSV =====
    st, csv_bytes = _req("GET", base, f"/contabilidad/diario.csv?desde={ayer}&hasta={hoy}", tok)
    check("diario.csv responde", st == 200 and isinstance(csv_bytes, bytes) and len(csv_bytes) > 100, f"{st}")

    # ===== 9. PRUEBA DE FUEGO: la historia completa del tenant demo =====
    desde_demo = (hoy - timedelta(days=120)).isoformat()
    st, fuego = _req("POST", base, "/contabilidad/regenerar", tok,
                     {"desde": desde_demo, "hasta": hoy.isoformat()})
    check("fuego: regenerar ~4 meses del tenant demo", st == 200 and fuego["asientos"] > 50,
          f"{st} {fuego if st != 200 else fuego['asientos']}")
    print(f"      fuego: {fuego.get('asientos')} asientos, {len(fuego.get('warnings', []))} warnings")
    if fuego.get("warnings"):
        print(f"      {fuego['warnings'][:5]}")
    st, sys2 = _req("GET", base, f"/contabilidad/sumas-y-saldos?desde={desde_demo}&hasta={hoy}", tok)
    check("fuego: sumas y saldos balancea sobre TODA la historia",
          st == 200 and sys2["balanceado"] is True,
          f"{st} debe={sys2.get('total_debe')} haber={sys2.get('total_haber')}")

    print(f"\n===== F9 DEV: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
