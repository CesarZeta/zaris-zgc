"""Suite en vivo de la Fase 8 (Cheques y Bancos) contra el server de DEV.

Ejercita el ciclo completo: cuentas bancarias, movimientos, conciliación por
import, cheque de tercero (alta/depositar/acreditar), endoso vía OP, rechazo con
reversión de cta.cte., cheque propio vía OP, y cash-flow. Todo recurso nombrado
lleva sufijo único de la corrida (no ensucia conteos si crashea).

Uso:
    python tools/test_fase8_dev.py --base http://127.0.0.1:8099 \
        --email demo@zaris.com.ar --clave "F8testing1!"
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import date, timedelta

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]
# sufijo numérico (6 dígitos) para documentos; y un DNI/CUIT válidos por corrida
NUM6 = f"{int(SUF, 16) % 1_000_000:06d}"


def _cuit_valido(base10: str) -> str:
    # dv == 10 NO existe como CUIT (mapearlo a 9 da un DV inválido y el alta
    # revienta con 422 una de cada ~11 corridas): variar la base y reintentar
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    while True:
        s = sum(int(base10[i]) * mult[i] for i in range(10))
        dv = 11 - (s % 11)
        if dv == 11:
            dv = 0
        if dv != 10:
            return base10 + str(dv)
        base10 = base10[:9] + str((int(base10[9]) + 1) % 10)


def _req(method, base, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=40)
        payload = r.read()
        ctype = r.headers.get("Content-Type", "")
        if "json" not in ctype:
            return r.status, payload  # CSV u otro binario: no parsear
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
    perms = r.get("permisos")
    print(f"login OK (permisos.bancos={perms.get('bancos') if perms else 'sin mapa=admin'})")

    hoy = date.today()

    # ===== 1. Cuenta bancaria =====
    st, cuenta = _req("POST", base, "/bancos/cuentas", tok, {
        "banco": f"Banco Test {SUF}", "tipo": "CC", "numero": "123-4",
        "moneda": "ARS", "saldo_inicial": "10000.00",
    })
    check("crear cuenta bancaria", st == 201, f"{st} {cuenta}")
    cuenta_id = cuenta["id"] if st == 201 else None

    st, det = _req("GET", base, f"/bancos/cuentas/{cuenta_id}", tok)
    check("detalle cuenta trae saldo_actual", st == 200 and det.get("saldo_actual") == "10000.00",
          f"{st} {det.get('saldo_actual')}")

    # movimiento manual (crédito +5000) -> saldo 15000
    st, mov = _req("POST", base, f"/bancos/cuentas/{cuenta_id}/movimientos", tok, {
        "tipo": "credito", "importe": "5000.00", "descripcion": "Transferencia recibida",
    })
    check("crear movimiento manual credito", st == 201, f"{st} {mov}")
    st, det = _req("GET", base, f"/bancos/cuentas/{cuenta_id}", tok)
    check("saldo tras credito = 15000", det.get("saldo_actual") == "15000.00", det.get("saldo_actual"))

    # movimiento comision -200 -> 14800
    st, _ = _req("POST", base, f"/bancos/cuentas/{cuenta_id}/movimientos", tok, {
        "tipo": "comision", "importe": "200.00",
    })
    st, det = _req("GET", base, f"/bancos/cuentas/{cuenta_id}", tok)
    check("saldo tras comision = 14800", det.get("saldo_actual") == "14800.00", det.get("saldo_actual"))

    # ===== 2. Cheque de tercero: alta manual en cartera =====
    st, cheque = _req("POST", base, "/cheques", tok, {
        "numero": f"1001{SUF[:4]}", "banco": "Banco Galicia",
        "fecha_pago": (hoy + timedelta(days=30)).isoformat(),
        "importe": "3000.00", "titular": "Cliente Test",
    })
    check("alta cheque tercero en cartera", st == 201 and cheque["estado"] == "en_cartera",
          f"{st} {cheque}")
    ch1 = cheque["id"] if st == 201 else None

    # DV inválido en firmante -> 422
    st, r422 = _req("POST", base, "/cheques", tok, {
        "numero": "9999", "banco": "X", "fecha_pago": hoy.isoformat(),
        "importe": "1.00", "cuit_firmante": "20111111110",
    })
    check("cheque con CUIT firmante inválido -> 422", st == 422, f"{st} {r422}")

    # depositar -> depositado (crea banco_movimiento no conciliado)
    st, r = _req("POST", base, f"/cheques/{ch1}/depositar", tok, {"cuenta_id": cuenta_id})
    check("depositar cheque -> depositado", st == 200 and r["estado"] == "depositado", f"{st} {r}")

    # el saldo NO cambió aún (depósito no conciliado, pero el signo suma igual en
    # nuestro modelo de saldo: depósito es +). Verificamos que el movimiento existe.
    st, movs = _req("GET", base, f"/bancos/cuentas/{cuenta_id}/movimientos?conciliado=false", tok)
    check("depósito genera movimiento no conciliado",
          any(m["tipo"] == "deposito" and m["importe"] == "3000.00" for m in movs), movs)

    # acreditar -> acreditado (concilia el depósito)
    st, r = _req("POST", base, f"/cheques/{ch1}/acreditar", tok, {})
    check("acreditar cheque -> acreditado", st == 200 and r["estado"] == "acreditado", f"{st} {r}")
    st, movs = _req("GET", base, f"/bancos/cuentas/{cuenta_id}/movimientos?conciliado=true", tok)
    check("depósito quedó conciliado tras acreditar",
          any(m["tipo"] == "deposito" and m["conciliado"] for m in movs), movs)

    # saldo tras depósito acreditado: 14800 + 3000 = 17800
    st, det = _req("GET", base, f"/bancos/cuentas/{cuenta_id}", tok)
    check("saldo tras acreditar = 17800", det.get("saldo_actual") == "17800.00", det.get("saldo_actual"))

    # acreditar de nuevo -> 409
    st, r = _req("POST", base, f"/cheques/{ch1}/acreditar", tok, {})
    check("re-acreditar -> 409", st == 409, f"{st} {r}")

    # ===== 3. Cheque de tercero: rechazo con reversión de cta.cte. =====
    # Creamos un cliente + factura a crédito, cobramos con cheque, y lo rechazamos.
    st, cli = _req("POST", base, "/clientes", tok, {
        "entidad": {
            "razon_social": f"Cliente F8 {SUF}", "tipo_persona": "F",
            "tipo_documento": "DNI", "nro_documento": NUM6,
            "condicion_iva": "CF",
        },
    })
    check("crear cliente para rechazo", st in (200, 201), f"{st} {cli}")
    cli_id = cli["id"] if st in (200, 201) else None

    # traer punto de venta
    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    pv_id = pvs[0]["id"] if isinstance(pvs, list) and pvs else None

    # cobranza SOLO con cheque, a cuenta (sin imputar) -> reduce saldo del cliente
    st, rec = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli_id,
        "medios": [{
            "medio": "cheque", "importe": "2500.00",
            "cheque": {
                "numero": f"2002{SUF[:4]}", "banco": "Banco Nación",
                "fecha_pago": (hoy + timedelta(days=15)).isoformat(),
            },
        }],
    })
    check("cobranza con cheque materializa cartera", st == 201, f"{st} {rec}")
    recibo_id = rec["id"] if st == 201 else None
    a_cuenta_antes = rec.get("a_cuenta") if st == 201 else None

    # el cheque de la cobranza está en cartera, ligado al recibo
    st, lista = _req("GET", base, f"/cheques?estado=en_cartera&cliente_id={cli_id}", tok)
    ch2 = next((c["id"] for c in lista if c["numero"] == f"2002{SUF[:4]}"), None)
    check("cheque de cobranza en cartera", ch2 is not None, lista)

    # rechazar -> reabre el 'a cuenta' del recibo (reduce recibo.total)
    st, r = _req("POST", base, f"/cheques/{ch2}/rechazar", tok, {"detalle": "Sin fondos"})
    check("rechazar cheque -> rechazado", st == 200 and r["estado"] == "rechazado", f"{st} {r}")
    check("rechazo reabrió el recibo (reversión cta.cte.)",
          r.get("reabierto") and r["reabierto"]["importe_revertido"] == "2500.00", r.get("reabierto"))

    # ===== 4. Endoso vía OP =====
    # cheque de tercero nuevo en cartera -> endosar a proveedor por OP
    st, ch3d = _req("POST", base, "/cheques", tok, {
        "numero": f"3003{SUF[:4]}", "banco": "Banco Provincia",
        "fecha_pago": (hoy + timedelta(days=20)).isoformat(), "importe": "1800.00",
    })
    ch3 = ch3d["id"]
    st, prov = _req("POST", base, "/proveedores", tok, {
        "entidad": {
            "razon_social": f"Proveedor F8 {SUF}", "tipo_persona": "J",
            "tipo_documento": "CUIT", "nro_documento": _cuit_valido("30" + NUM6 + "12"),
            "condicion_iva": "RI",
        },
    })
    check("crear proveedor", st in (200, 201), f"{st} {prov}")
    prov_id = prov["id"] if st in (200, 201) else None

    st, op = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov_id,
        "medios": [{"medio": "cheque", "importe": "1800.00", "endosar_cheque_id": ch3}],
    })
    check("OP endosa cheque de cartera", st == 201, f"{st} {op}")
    st, r = _req("GET", base, f"/cheques/{ch3}", tok)
    check("cheque endosado -> estado endosado + proveedor",
          r["estado"] == "endosado" and r["proveedor_id"] == prov_id, r)

    # importe distinto -> 422
    st, ch4d = _req("POST", base, "/cheques", tok, {
        "numero": f"4004{SUF[:4]}", "banco": "B", "fecha_pago": hoy.isoformat(), "importe": "500.00",
    })
    st, r = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov_id,
        "medios": [{"medio": "cheque", "importe": "999.00", "endosar_cheque_id": ch4d["id"]}],
    })
    check("endoso con importe != cheque -> 422", st == 422, f"{st} {r}")

    # ===== 5. Cheque propio vía OP =====
    st, op2 = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
        "proveedor_id": prov_id,
        "medios": [{
            "medio": "cheque", "importe": "4200.00",
            "cheque_propio": {
                "cuenta_id": cuenta_id, "numero": f"P500{SUF[:3]}",
                "fecha_pago": (hoy + timedelta(days=45)).isoformat(),
            },
        }],
    })
    check("OP emite cheque propio", st == 201, f"{st} {op2}")
    st, propios = _req("GET", base, "/cheques?clase=propio&estado=emitido", tok)
    ch_prop = next((c for c in propios if c["numero"] == f"P500{SUF[:3]}"), None)
    check("cheque propio emitido con banco de la cuenta",
          ch_prop is not None and ch_prop["banco"] == f"Banco Test {SUF}", ch_prop)
    ch_prop_id = ch_prop["id"] if ch_prop else None

    # debitar el propio -> movimiento débito conciliado, saldo -4200
    st, det_antes = _req("GET", base, f"/bancos/cuentas/{cuenta_id}", tok)
    st, r = _req("POST", base, f"/cheques/{ch_prop_id}/debitar", tok, {})
    check("debitar cheque propio -> debitado", st == 200 and r["estado"] == "debitado", f"{st} {r}")
    st, det_desp = _req("GET", base, f"/bancos/cuentas/{cuenta_id}", tok)
    delta = float(det_antes["saldo_actual"]) - float(det_desp["saldo_actual"])
    check("débito de cheque propio restó 4200 del saldo", abs(delta - 4200.0) < 0.01, f"delta={delta}")

    # ===== 6. Conciliación por import de extracto =====
    # creamos un movimiento manual pendiente que el extracto va a matchear
    st, movp = _req("POST", base, f"/bancos/cuentas/{cuenta_id}/movimientos", tok, {
        "tipo": "credito", "importe": "999.99", "fecha": hoy.isoformat(),
        "descripcion": "Depósito a conciliar",
    })
    # preview con un CSV: una fila matchea (999.99 misma fecha), otra es nueva (-150 débito)
    csv = f"{hoy.isoformat()};Deposito;999,99\n{hoy.isoformat()};Comision banco;-150,00\n"
    # multipart no soportado por urllib fácil -> probamos el import directo (el
    # preview se prueba en el E2E navegador). Import manual con 2 items:
    st, imp = _req("POST", base, f"/bancos/cuentas/{cuenta_id}/extracto/import", tok, {
        "nombre_archivo": "extracto.csv",
        "items": [
            {"fecha": hoy.isoformat(), "importe": "999.99", "tipo": "credito",
             "match_movimiento_id": movp["id"], "accion": "conciliar"},
            {"fecha": hoy.isoformat(), "detalle": "Comision banco", "importe": "-150.00",
             "tipo": "debito", "accion": "crear"},
        ],
    })
    check("import extracto: 1 conciliado + 1 creado",
          st == 201 and imp["conciliados"] == 1 and imp["creados"] == 1, f"{st} {imp}")

    # ===== 7. Cash-flow proyectado =====
    st, cf = _req("GET", base, "/tesoreria/cashflow?granularidad=mes", tok)
    check("cashflow responde con serie", st == 200 and "serie" in cf and "saldo_inicial" in cf,
          f"{st} {str(cf)[:200]}")
    # debe incluir el cheque propio a debitar como salida futura (si aún emitido)
    # y algún cobro/cheque de tercero como entrada
    check("cashflow tiene saldo_inicial numérico",
          st == 200 and cf["saldo_inicial"].replace("-", "").replace(".", "").isdigit(),
          cf.get("saldo_inicial") if st == 200 else None)

    # ===== 8. Resumen de cartera + export =====
    st, resumen = _req("GET", base, "/cheques/resumen", tok)
    check("resumen cartera responde", st == 200 and isinstance(resumen, list), f"{st} {resumen}")

    st, _ = _req("GET", base, "/cheques/export.csv", tok)
    check("export cheques CSV 200", st == 200, st)

    print(f"\n=== Fase 8 DEV: {ok} ok, {fail} fail (suf {SUF}) ===")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
