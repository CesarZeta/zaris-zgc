"""Suite en vivo de F9-bis (bienes de uso + balance + apertura + apareo) contra DEV.

Cubre: re-seed lazy del plan (cuentas 1.4.x/5.1.07-08 + categorías en tenants ya
sembrados), ABM de activos con cuadro valorizado, derivación de amortizaciones
mensuales y del asiento de baja, anulación de activo (sus asientos desaparecen al
regenerar), apareo de transferencias entre cuentas propias (validaciones + asiento
banco a banco sin cuenta puente + desapareo por anulación), balance general con
ecuación verificada, exports (cuadro CSV, balance CSV, paquete contador ZIP) y el
asiento de apertura asistido (sugerencia balanceada, unicidad, inmune a la
regeneración, anulable).

Uso:
    python tools/test_f9bis_dev.py --base http://127.0.0.1:8021 \
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

    # ===== 1. Re-seed lazy: cuentas y categorías nuevas en tenant ya sembrado =====
    st, plan = _req("GET", base, "/contabilidad/plan", tok)
    cuenta = {c["codigo"]: c for c in plan}
    for cod in ("1.4.01", "1.4.02", "5.1.07", "5.1.08"):
        check(f"plan re-sembrado incluye {cod}", cod in cuenta, list(cuenta)[:5])
    st, mapeos = _req("GET", base, "/contabilidad/mapeos", tok)
    origenes_m = {m["origen"] for m in mapeos}
    for o in ("bienes_uso", "amort_acumulada", "amort_ejercicio", "baja_bienes_uso"):
        check(f"mapeo default {o}", o in origenes_m, origenes_m)
    st, cats = _req("GET", base, "/contabilidad/activos/categorias", tok)
    check("categorías base sembradas", st == 200 and len(cats) >= 6,
          f"{st} n={len(cats) if isinstance(cats, list) else cats}")
    st, cat_nueva = _req("POST", base, "/contabilidad/activos/categorias", tok,
                         {"nombre": f"Herramientas {SUF}", "vida_util_meses": 24})
    check("categoría nueva -> 201", st == 201, f"{st} {cat_nueva}")
    st, r2 = _req("POST", base, "/contabilidad/activos/categorias", tok,
                  {"nombre": f"Herramientas {SUF}", "vida_util_meses": 24})
    check("categoría duplicada -> 409", st == 409, f"{st}")

    # ===== 2. Activo fijo: alta con inicio 3 meses atrás, vida 12, 1200/0 =====
    inicio = (hoy.replace(day=1) - timedelta(days=80)).replace(day=1)  # ~3 meses atrás
    st, act = _req("POST", base, "/contabilidad/activos", tok, {
        "nombre": f"Notebook {SUF}", "categoria_id": cat_nueva["id"],
        "fecha_alta": inicio.isoformat(), "valor_origen": "1200.00",
        "valor_residual": "0", "vida_util_meses": 12})
    check("alta de activo -> 201", st == 201, f"{st} {act}")
    st, r2 = _req("POST", base, "/contabilidad/activos", tok, {
        "nombre": f"Mal {SUF}", "categoria_id": cat_nueva["id"],
        "fecha_alta": inicio.isoformat(), "valor_origen": "100",
        "valor_residual": "150", "vida_util_meses": 12})
    check("residual >= origen -> 422", st == 422, f"{st}")

    # meses con fin de mes <= hoy desde `inicio`
    meses_devengados = 0
    m = inicio
    while True:
        siguiente = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
        fin_mes = siguiente - timedelta(days=1)
        if fin_mes > hoy:
            break
        meses_devengados += 1
        m = siguiente
    esperado = Decimal("100.00") * meses_devengados

    st, gen = _req("POST", base, "/contabilidad/regenerar", tok,
                   {"desde": inicio.isoformat(), "hasta": hoy.isoformat()})
    check("regenerar con activo", st == 200, f"{st} {gen}")
    st, amorts = _req("GET", base,
                      f"/contabilidad/asientos?desde={inicio}&hasta={hoy}&origen=amortizacion&limit=200", tok)
    check(f"asientos de amortización = {meses_devengados} meses",
          st == 200 and len(amorts) == meses_devengados, f"{st} n={len(amorts)}")
    check("amortizaciones balanceadas", all(balanceado(a) for a in amorts))
    suma_amort = sum(
        (D(l["debe"]) for a in amorts for l in a["lineas"]
         if l["cuenta_codigo"] == "5.1.07" and f"Notebook {SUF}"[:40] in (l["detalle"] or "")),
        Decimal("0"),
    )
    check(f"cuotas devengadas suman {esperado}", suma_amort == esperado, f"suma={suma_amort}")

    # cuadro al corte de hoy refleja lo mismo
    st, activos = _req("GET", base, f"/contabilidad/activos?corte={hoy}", tok)
    mio = next((a for a in activos if a["id"] == act["id"]), None)
    check("cuadro: amort. acumulada coincide", mio and D(mio["amort_acumulada"]) == esperado,
          mio and mio["amort_acumulada"])
    check("cuadro: valor contable = origen − amort",
          mio and D(mio["valor_contable"]) == Decimal("1200.00") - esperado,
          mio and mio["valor_contable"])
    st, csv_bytes = _req("GET", base, f"/contabilidad/activos/cuadro.csv?corte={hoy}", tok)
    check("cuadro.csv responde", st == 200 and isinstance(csv_bytes, bytes) and b"Notebook" in csv_bytes, f"{st}")

    # ===== 3. Baja: asiento de retiro balanceado =====
    st, baja = _req("POST", base, f"/contabilidad/activos/{act['id']}/baja", tok,
                    {"fecha_baja": hoy.isoformat(), "baja_motivo": "obsoleto"})
    check("baja -> 200", st == 200 and baja["fecha_baja"] == hoy.isoformat(), f"{st}")
    st, gen = _req("POST", base, "/contabilidad/regenerar", tok,
                   {"desde": inicio.isoformat(), "hasta": hoy.isoformat()})
    st, bajas = _req("GET", base,
                     f"/contabilidad/asientos?desde={inicio}&hasta={hoy}&origen=activo_baja&limit=50", tok)
    a_baja = next((a for a in bajas if f"Notebook {SUF}"[:40] in (a["descripcion"] or "")), None)
    check("asiento de baja presente y balanceado", a_baja is not None and balanceado(a_baja),
          f"n={len(bajas)}")
    if a_baja:
        haber_bu = sum(D(l["haber"]) for l in a_baja["lineas"] if l["cuenta_codigo"] == "1.4.01")
        debe_ac = sum(D(l["debe"]) for l in a_baja["lineas"] if l["cuenta_codigo"] == "1.4.02")
        debe_rb = sum(D(l["debe"]) for l in a_baja["lineas"] if l["cuenta_codigo"] == "5.1.08")
        check("baja: haber Bienes de uso = valor origen", haber_bu == Decimal("1200.00"), haber_bu)
        check("baja: debe amort. acumulada = devengado", debe_ac == esperado, debe_ac)
        check("baja: debe resultado = residual contable",
              debe_rb == Decimal("1200.00") - esperado, debe_rb)

    # ===== 4. Anular activo: sus asientos desaparecen al regenerar =====
    st, act2 = _req("POST", base, "/contabilidad/activos", tok, {
        "nombre": f"Errado {SUF}", "categoria_id": cat_nueva["id"],
        "fecha_alta": inicio.isoformat(), "valor_origen": "600.00",
        "valor_residual": "0", "vida_util_meses": 6})
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": inicio.isoformat(), "hasta": hoy.isoformat()})
    st, amorts2 = _req("GET", base,
                       f"/contabilidad/asientos?desde={inicio}&hasta={hoy}&origen=amortizacion&limit=200", tok)
    con_errado = any(
        f"Errado {SUF}"[:40] in (l["detalle"] or "") for a in amorts2 for l in a["lineas"]
    )
    check("el activo nuevo amortiza", con_errado)
    st, _ = _req("POST", base, f"/contabilidad/activos/{act2['id']}/anular", tok)
    check("anular activo -> 200", st == 200, f"{st}")
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": inicio.isoformat(), "hasta": hoy.isoformat()})
    st, amorts3 = _req("GET", base,
                       f"/contabilidad/asientos?desde={inicio}&hasta={hoy}&origen=amortizacion&limit=200", tok)
    sin_errado = not any(
        f"Errado {SUF}"[:40] in (l["detalle"] or "") for a in amorts3 for l in a["lineas"]
    )
    check("anulado: sus amortizaciones desaparecen al regenerar", sin_errado)

    # ===== 5. Apareo de transferencias entre cuentas propias =====
    # importe ÚNICO por corrida: los movimientos de corridas anteriores quedan
    # vivos y el buscador de candidatos matchea por importe en todo el tenant
    IMP = f"{500 + int(SUF[:4], 16) % 400}.{int(SUF[4:6], 16) % 100:02d}"
    st, cta_a = _req("POST", base, "/bancos/cuentas", tok,
                     {"banco": f"Banco A {SUF}", "saldo_inicial": "1000"})
    st, cta_b = _req("POST", base, "/bancos/cuentas", tok,
                     {"banco": f"Banco B {SUF}", "saldo_inicial": "0"})
    # mapear cada cuenta a su cuenta contable (para que el asiento discrimine)
    st, cu_a = _req("POST", base, "/contabilidad/plan", tok, {
        "codigo": f"1.1.90{SUF[:2]}", "nombre": f"Banco A {SUF}", "tipo": "activo",
        "imputable": True, "padre_id": cuenta["1.1"]["id"] if "1.1" in cuenta else None})
    st, cu_b = _req("POST", base, "/contabilidad/plan", tok, {
        "codigo": f"1.1.91{SUF[:2]}", "nombre": f"Banco B {SUF}", "tipo": "activo",
        "imputable": True, "padre_id": cuenta["1.1"]["id"] if "1.1" in cuenta else None})
    st, _ = _req("PUT", base, "/contabilidad/mapeos", tok,
                 {"origen": "cuenta_bancaria", "clave": cta_a["id"], "cuenta_id": cu_a["id"]})
    st, _ = _req("PUT", base, "/contabilidad/mapeos", tok,
                 {"origen": "cuenta_bancaria", "clave": cta_b["id"], "cuenta_id": cu_b["id"]})
    st, mov_out = _req("POST", base, f"/bancos/cuentas/{cta_a['id']}/movimientos", tok,
                       {"tipo": "transferencia_out", "importe": IMP,
                        "descripcion": f"a Banco B {SUF}", "fecha": hoy.isoformat()})
    st, mov_in = _req("POST", base, f"/bancos/cuentas/{cta_b['id']}/movimientos", tok,
                      {"tipo": "transferencia_in", "importe": IMP,
                       "descripcion": f"de Banco A {SUF}", "fecha": hoy.isoformat()})
    st, mov_in2 = _req("POST", base, f"/bancos/cuentas/{cta_b['id']}/movimientos", tok,
                       {"tipo": "transferencia_in", "importe": "123.00", "fecha": hoy.isoformat()})
    check("movimientos creados", mov_out.get("id") and mov_in.get("id"), f"{mov_out} {mov_in}")

    st, cands = _req("GET", base, f"/bancos/movimientos/{mov_out['id']}/candidatos-apareo", tok)
    check("candidatos: solo el espejo (mismo importe)",
          st == 200 and len(cands) == 1 and cands[0]["id"] == mov_in["id"],
          f"{st} n={len(cands) if isinstance(cands, list) else cands}")
    st, r2 = _req("POST", base, f"/bancos/movimientos/{mov_out['id']}/aparear", tok,
                  {"contrapartida_id": mov_in2["id"]})
    check("aparear importes distintos -> 422", st == 422, f"{st}")
    st, apareado = _req("POST", base, f"/bancos/movimientos/{mov_out['id']}/aparear", tok,
                        {"contrapartida_id": mov_in["id"]})
    check("aparear -> 200 con contrapartida", st == 200 and apareado["contrapartida_id"] == mov_in["id"], f"{st}")
    st, mov_in3 = _req("POST", base, f"/bancos/cuentas/{cta_b['id']}/movimientos", tok,
                       {"tipo": "transferencia_in", "importe": IMP, "fecha": hoy.isoformat()})
    st, r2 = _req("POST", base, f"/bancos/movimientos/{mov_in3['id']}/aparear", tok,
                  {"contrapartida_id": mov_out["id"]})
    check("re-aparear un apareado -> 409", st == 409, f"{st}")
    st, _ = _req("DELETE", base, f"/bancos/movimientos/{mov_in3['id']}", tok)

    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": hoy.isoformat(), "hasta": hoy.isoformat()})
    st, transfers = _req("GET", base,
                         f"/contabilidad/asientos?desde={hoy}&hasta={hoy}&origen=banco_transfer&limit=50", tok)
    a_tr = next((a for a in transfers if f"a Banco B {SUF}"[:40] in (a["descripcion"] or "")), None)
    check("asiento banco_transfer presente y balanceado", a_tr is not None and balanceado(a_tr),
          f"n={len(transfers)}")
    if a_tr:
        codigos = {l["cuenta_codigo"] for l in a_tr["lineas"]}
        check("transferencia apareada NO pasa por la puente 1.1.06", "1.1.06" not in codigos, codigos)
        debe_b = sum(D(l["debe"]) for l in a_tr["lineas"] if l["cuenta_codigo"] == cu_b["codigo"])
        haber_a = sum(D(l["haber"]) for l in a_tr["lineas"] if l["cuenta_codigo"] == cu_a["codigo"])
        check("debe Banco B / haber Banco A por el importe único",
              debe_b == D(IMP) and haber_a == D(IMP), f"{debe_b} {haber_a}")
    # la entrada apareada no genera asiento banco_mov propio
    st, bancomovs = _req("GET", base,
                         f"/contabilidad/asientos?desde={hoy}&hasta={hoy}&origen=banco_mov&limit=100", tok)
    in_suelto = any(
        f"de Banco A {SUF}"[:40] in (a["descripcion"] or "") for a in bancomovs
    )
    check("la entrada apareada no deriva asiento propio", not in_suelto)

    # anular la salida apareada desaparea a la entrada
    st, _ = _req("DELETE", base, f"/bancos/movimientos/{mov_out['id']}", tok)
    check("anular movimiento apareado -> 204", st == 204, f"{st}")
    st, movs_b = _req("GET", base, f"/bancos/cuentas/{cta_b['id']}/movimientos?limit=50", tok)
    m_in = next((m for m in movs_b if m["id"] == mov_in["id"]), None)
    check("la contraparte quedó desapareada", m_in is not None and m_in["contrapartida_id"] is None,
          m_in and m_in["contrapartida_id"])

    # ===== 6. Balance general =====
    st, bal = _req("GET", base, f"/contabilidad/balance?hasta={hoy}", tok)
    check("balance responde y la ecuación cierra", st == 200 and bal["ecuacion_ok"] is True,
          f"{st} A={bal.get('activo_total')} P={bal.get('pasivo_total')} PN={bal.get('pn_total')}")
    check("balance con secciones A/P/PN",
          [s["tipo"] for s in bal.get("secciones", [])] == ["activo", "pasivo", "pn"])
    st, csv_bytes = _req("GET", base, f"/contabilidad/balance.csv?hasta={hoy}", tok)
    check("balance.csv responde", st == 200 and isinstance(csv_bytes, bytes) and len(csv_bytes) > 100, f"{st}")

    # ===== 7. Paquete contador (ZIP con 4 CSV) =====
    desde_zip = (hoy - timedelta(days=120)).isoformat()
    st, zip_bytes = _req("GET", base,
                         f"/contabilidad/export-contador.zip?desde={desde_zip}&hasta={hoy}", tok)
    check("export-contador.zip responde (magic PK)",
          st == 200 and isinstance(zip_bytes, bytes) and zip_bytes[:2] == b"PK", f"{st}")
    if isinstance(zip_bytes, bytes) and zip_bytes[:2] == b"PK":
        import io
        import zipfile
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            nombres = set(zf.namelist())
        check("ZIP con los 4 CSV",
              nombres == {"plan-de-cuentas.csv", "libro-diario.csv", "sumas-y-saldos.csv", "mayor.csv"},
              nombres)

    # ===== 8. Asiento de apertura asistido =====
    st, sug = _req("GET", base, "/contabilidad/apertura/sugerencia", tok)
    check("sugerencia responde con líneas", st == 200 and len(sug["lineas"]) >= 1, f"{st}")
    tot_debe = sum((D(l["debe"]) for l in sug["lineas"]), Decimal("0"))
    tot_haber = sum((D(l["haber"]) for l in sug["lineas"]), Decimal("0"))
    check("sugerencia balancea (contrapartida capital)", tot_debe == tot_haber and tot_debe > 0,
          f"{tot_debe} vs {tot_haber}")
    lineas_ap = [
        {"cuenta_id": l["cuenta_id"], "debe": l["debe"], "haber": l["haber"], "detalle": l["detalle"]}
        for l in sug["lineas"] if l["cuenta_id"]
    ]
    st, apertura = _req("POST", base, "/contabilidad/apertura", tok,
                        {"fecha": hoy.isoformat(), "descripcion": f"Apertura {SUF}",
                         "lineas": lineas_ap})
    check("apertura -> 201 con origen apertura", st == 201 and apertura["origen_tipo"] == "apertura",
          f"{st} {apertura if st != 201 else ''}")
    st, r2 = _req("POST", base, "/contabilidad/apertura", tok,
                  {"fecha": hoy.isoformat(), "descripcion": "segunda", "lineas": lineas_ap})
    check("segunda apertura viva -> 409", st == 409, f"{st}")
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": hoy.isoformat(), "hasta": hoy.isoformat()})
    st, det = _req("GET", base, f"/contabilidad/asientos/{apertura['id']}", tok)
    check("la regeneración NO toca la apertura", st == 200 and not det["anulado"], f"{st}")
    st, anulada = _req("POST", base, f"/contabilidad/asientos/{apertura['id']}/anular", tok)
    check("apertura anulable (marcada)", st == 200 and anulada["anulado"] is True, f"{st}")

    print(f"\n===== F9-BIS DEV: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
