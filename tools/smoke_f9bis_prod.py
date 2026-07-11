"""Smoke de F9-bis (bienes de uso + balance + apertura + apareo) contra PROD.

Read-mostly + dos ciclos cortos y limpios en el tenant DEMO:
- activo fijo de smoke (categoría del seed) → regenerar rango corto → amortización
  derivada → anular → regenerar → desaparece (estado final = estado inicial);
- par de cuentas bancarias de smoke → transferencias espejo → aparear → asiento
  banco_transfer → anular movimientos (desaparea) → inactivar cuentas.

Uso:
    python tools/smoke_f9bis_prod.py --email demo@zaris.com.ar --clave "..."
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
        r = U.urlopen(req, timeout=90)
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
    ap.add_argument("--base", default="https://zaris-zgc-api.vercel.app")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"
    hoy = date.today()

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print("login FAIL", st, r)
        sys.exit(1)
    tok = r["access_token"]
    print(f"login OK — sufijo {SUF}")

    # 1. Re-seed lazy en prod: el plan del tenant demo suma las cuentas F9-bis
    st, plan = _req("GET", base, "/contabilidad/plan", tok)
    cuenta = {c["codigo"]: c for c in plan} if isinstance(plan, list) else {}
    check("plan responde y trae 1.4.01/1.4.02/5.1.07/5.1.08",
          st == 200 and all(c in cuenta for c in ("1.4.01", "1.4.02", "5.1.07", "5.1.08")),
          f"{st}")
    st, cats = _req("GET", base, "/contabilidad/activos/categorias", tok)
    check("categorías base sembradas", st == 200 and len(cats) >= 6,
          f"{st} n={len(cats) if isinstance(cats, list) else cats}")

    # 2. Ciclo de activo: alta → regenerar → amortiza → anular → regenerar → limpio
    inicio = (hoy.replace(day=1) - timedelta(days=40)).replace(day=1)  # ~2 meses atrás
    st, act = _req("POST", base, "/contabilidad/activos", tok, {
        "nombre": f"Smoke F9bis {SUF}", "categoria_id": cats[0]["id"],
        "fecha_alta": inicio.isoformat(), "valor_origen": "120.00",
        "valor_residual": "0", "vida_util_meses": 12})
    check("alta de activo -> 201", st == 201, f"{st} {act}")
    st, gen = _req("POST", base, "/contabilidad/regenerar", tok,
                   {"desde": inicio.isoformat(), "hasta": hoy.isoformat()})
    check("regenerar rango corto", st == 200, f"{st} {gen}")
    st, amorts = _req("GET", base,
                      f"/contabilidad/asientos?desde={inicio}&hasta={hoy}&origen=amortizacion&limit=50", tok)
    con_smoke = any(
        f"Smoke F9bis {SUF}"[:40] in (l["detalle"] or "")
        for a in (amorts or []) for l in a["lineas"]
    )
    check("amortización derivada en prod", st == 200 and con_smoke,
          f"{st} n={len(amorts) if isinstance(amorts, list) else amorts}")
    st, activos = _req("GET", base, f"/contabilidad/activos?corte={hoy}", tok)
    mio = next((a for a in activos if a["id"] == act["id"]), None)
    check("cuadro con amort. acumulada > 0", mio is not None and D(mio["amort_acumulada"]) > 0,
          mio and mio["amort_acumulada"])
    st, csv_b = _req("GET", base, f"/contabilidad/activos/cuadro.csv?corte={hoy}", tok)
    check("cuadro.csv responde", st == 200, f"{st}")
    st, _ = _req("POST", base, f"/contabilidad/activos/{act['id']}/anular", tok)
    check("anular activo smoke", st == 200, f"{st}")
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": inicio.isoformat(), "hasta": hoy.isoformat()})
    st, amorts2 = _req("GET", base,
                       f"/contabilidad/asientos?desde={inicio}&hasta={hoy}&origen=amortizacion&limit=50", tok)
    sin_smoke = not any(
        f"Smoke F9bis {SUF}"[:40] in (l["detalle"] or "")
        for a in (amorts2 or []) for l in a["lineas"]
    )
    check("estado restaurado (amortización del smoke fuera)", sin_smoke)

    # 3. Balance + exports
    st, bal = _req("GET", base, f"/contabilidad/balance?hasta={hoy}", tok)
    check("balance responde con ecuación OK", st == 200 and bal.get("ecuacion_ok") is True,
          f"{st} A={bal.get('activo_total') if isinstance(bal, dict) else bal}")
    st, csv_b = _req("GET", base, f"/contabilidad/balance.csv?hasta={hoy}", tok)
    check("balance.csv responde", st == 200, f"{st}")
    desde_zip = (hoy - timedelta(days=30)).isoformat()
    st, zip_b = _req("GET", base,
                     f"/contabilidad/export-contador.zip?desde={desde_zip}&hasta={hoy}", tok)
    check("export-contador.zip (magic PK)",
          st == 200 and isinstance(zip_b, bytes) and zip_b[:2] == b"PK", f"{st}")

    # 4. Apertura: solo la sugerencia (no se postea — no ensuciar el demo)
    st, sug = _req("GET", base, "/contabilidad/apertura/sugerencia", tok)
    tot_d = sum((D(l["debe"]) for l in sug.get("lineas", [])), Decimal("0")) if isinstance(sug, dict) else Decimal("0")
    tot_h = sum((D(l["haber"]) for l in sug.get("lineas", [])), Decimal("0")) if isinstance(sug, dict) else Decimal("0")
    check("apertura/sugerencia balancea", st == 200 and tot_d == tot_h, f"{st} {tot_d} vs {tot_h}")

    # 5. Ciclo de apareo: cuentas smoke → espejo → aparear → asiento → limpiar
    IMP = f"{300 + int(SUF[:4], 16) % 300}.{int(SUF[4:6], 16) % 100:02d}"
    st, cta_a = _req("POST", base, "/bancos/cuentas", tok,
                     {"banco": f"Smoke A {SUF}", "saldo_inicial": "0"})
    st, cta_b = _req("POST", base, "/bancos/cuentas", tok,
                     {"banco": f"Smoke B {SUF}", "saldo_inicial": "0"})
    st, mov_out = _req("POST", base, f"/bancos/cuentas/{cta_a['id']}/movimientos", tok,
                       {"tipo": "transferencia_out", "importe": IMP,
                        "descripcion": f"smoke {SUF}", "fecha": hoy.isoformat()})
    st, mov_in = _req("POST", base, f"/bancos/cuentas/{cta_b['id']}/movimientos", tok,
                      {"tipo": "transferencia_in", "importe": IMP,
                       "descripcion": f"smoke {SUF}", "fecha": hoy.isoformat()})
    st, cands = _req("GET", base, f"/bancos/movimientos/{mov_out['id']}/candidatos-apareo", tok)
    check("candidatos-apareo encuentra el espejo",
          st == 200 and any(c["id"] == mov_in["id"] for c in cands), f"{st}")
    st, ap_r = _req("POST", base, f"/bancos/movimientos/{mov_out['id']}/aparear", tok,
                    {"contrapartida_id": mov_in["id"]})
    check("aparear -> 200", st == 200 and ap_r.get("contrapartida_id") == mov_in["id"], f"{st}")
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": hoy.isoformat(), "hasta": hoy.isoformat()})
    st, transfers = _req("GET", base,
                         f"/contabilidad/asientos?desde={hoy}&hasta={hoy}&origen=banco_transfer&limit=20", tok)
    check("asiento banco_transfer derivado en prod",
          st == 200 and any(f"smoke {SUF}"[:40] in (a["descripcion"] or "") for a in transfers),
          f"{st} n={len(transfers) if isinstance(transfers, list) else transfers}")
    # limpieza: anular movimientos (el primero desaparea al otro) + regenerar + inactivar cuentas
    st, _ = _req("DELETE", base, f"/bancos/movimientos/{mov_out['id']}", tok)
    check("anular salida apareada -> 204", st == 204, f"{st}")
    st, _ = _req("DELETE", base, f"/bancos/movimientos/{mov_in['id']}", tok)
    st, _ = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": hoy.isoformat(), "hasta": hoy.isoformat()})
    st, _ = _req("POST", base, f"/bancos/cuentas/{cta_a['id']}/inactivar", tok)
    st, _ = _req("POST", base, f"/bancos/cuentas/{cta_b['id']}/inactivar", tok)
    check("cuentas smoke inactivadas", st == 200, f"{st}")

    print(f"\n===== SMOKE F9-BIS PROD: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
