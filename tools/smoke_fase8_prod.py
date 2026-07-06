"""Smoke E2E de la Fase 8 (Cheques y Bancos) contra PROD (Vercel) — post-deploy.

Verifica que los endpoints nuevos existan y respondan coherente en prod, y ejerce
un mini-ciclo de cheque (alta → depositar → acreditar) + una cuenta bancaria +
cash-flow. Todo recurso nombrado lleva sufijo único de la corrida. NO deja basura
crítica (los cheques quedan acreditados/anulados; la cuenta se inactiva al final).

Uso:
    python tools/smoke_fase8_prod.py --email <admin> --clave <clave>
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import date, timedelta

BASE = "https://zaris-zgc-api.vercel.app/api/v1"
SUF = uuid.uuid4().hex[:6]
ok = 0
fail = 0


def _req(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=45)
        payload = r.read()
        ctype = r.headers.get("Content-Type", "")
        if "json" not in ctype:
            return r.status, payload, dict(r.headers)
        return r.status, (json.loads(payload) if payload else None), dict(r.headers)
    except E.HTTPError as ex:
        payload = ex.read()
        try:
            return ex.code, json.loads(payload), dict(ex.headers)
        except Exception:
            return ex.code, payload.decode(errors="replace"), dict(ex.headers)


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
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()

    st, r, _ = _req("POST", "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print("login FAIL", st, r)
        sys.exit(1)
    tok = r["access_token"]
    perms = r.get("permisos")
    check("login + permiso bancos", perms is None or "bancos" in perms,
          f"permisos={perms}")

    hoy = date.today()

    # cuenta bancaria
    st, cuenta, _ = _req("POST", "/bancos/cuentas", tok, {
        "banco": f"Smoke Banco {SUF}", "moneda": "ARS", "saldo_inicial": "1000.00",
    })
    check("crear cuenta bancaria", st == 201, f"{st} {cuenta}")
    cuenta_id = cuenta["id"] if st == 201 else None

    st, det, _ = _req("GET", f"/bancos/cuentas/{cuenta_id}", tok)
    check("saldo_actual calculado", st == 200 and det.get("saldo_actual") == "1000.00", det)

    # cheque de tercero: alta → depositar → acreditar
    st, ch, _ = _req("POST", "/cheques", tok, {
        "numero": f"S{SUF}", "banco": "Banco Smoke",
        "fecha_pago": (hoy + timedelta(days=30)).isoformat(), "importe": "500.00",
    })
    check("alta cheque tercero", st == 201 and ch["estado"] == "en_cartera", f"{st} {ch}")
    ch_id = ch["id"] if st == 201 else None

    st, r, _ = _req("POST", f"/cheques/{ch_id}/depositar", tok, {"cuenta_id": cuenta_id})
    check("depositar", st == 200 and r["estado"] == "depositado", f"{st} {r}")
    st, r, _ = _req("POST", f"/cheques/{ch_id}/acreditar", tok, {})
    check("acreditar", st == 200 and r["estado"] == "acreditado", f"{st} {r}")

    st, det, _ = _req("GET", f"/bancos/cuentas/{cuenta_id}", tok)
    check("saldo tras acreditar = 1500", det.get("saldo_actual") == "1500.00", det.get("saldo_actual"))

    # DV inválido en padrón-like: cheque firmante inválido
    st, r, _ = _req("POST", "/cheques", tok, {
        "numero": "X", "banco": "Y", "fecha_pago": hoy.isoformat(),
        "importe": "1.00", "cuit_firmante": "20111111110",
    })
    check("CUIT firmante inválido -> 422", st == 422, f"{st} {r}")

    # resumen y export
    st, res, _ = _req("GET", "/cheques/resumen", tok)
    check("resumen cartera", st == 200 and isinstance(res, list), st)
    st, _, hdrs = _req("GET", "/cheques/export.csv", tok)
    check("export cheques CSV 200", st == 200, st)

    # cash-flow
    st, cf, _ = _req("GET", "/tesoreria/cashflow?granularidad=mes", tok)
    check("cashflow responde", st == 200 and "serie" in cf and "saldo_inicial" in cf, st)

    # X-Total-Count expuesto (CORS real, sin proxy)
    st, _, hdrs = _req("GET", "/cheques?limit=1", tok)
    check("X-Total-Count presente en listado", "X-Total-Count" in hdrs or "x-total-count" in hdrs, list(hdrs))

    # cleanup: inactivar la cuenta smoke (no hay DELETE por diseño)
    _req("POST", f"/bancos/cuentas/{cuenta_id}/inactivar", tok, {})

    print(f"\n=== Fase 8 PROD smoke: {ok} ok, {fail} fail (suf {SUF}) ===")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
