"""Smoke de la mini-fase CONTABILIZABILIDAD (014) contra PROD.

Read-mostly + un ciclo de soft-delete en caja del tenant DEMO (crea y anula un
movimiento de $1; el concepto de prueba queda inactivado). Verifica que la 014
está viva (columnas nuevas serializadas) y que los filtros de anulados rigen.

Uso:
    python tools/smoke_contab_prod.py --email demo@zaris.com.ar --clave "..."
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
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
        r = U.urlopen(req, timeout=60)
        payload = r.read()
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
    ap.add_argument("--base", default="https://zaris-zgc-api.vercel.app")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    check("login", st == 200, f"{st} {r}")
    if st != 200:
        sys.exit(1)
    tok = r["access_token"]

    # 1. cuentas bancarias: el schema nuevo expone saldo_inicial_fecha
    st, cuentas = _req("GET", base, "/bancos/cuentas", tok)
    check("GET /bancos/cuentas 200", st == 200, f"{st}")
    if isinstance(cuentas, list) and cuentas:
        check("cuenta expone saldo_inicial_fecha (014 viva)",
              "saldo_inicial_fecha" in cuentas[0], list(cuentas[0].keys()))

    # 2. recibos: el schema nuevo expone rechazado_total
    st, recs = _req("GET", base, "/cobranzas/recibos?limit=1", tok)
    check("GET /cobranzas/recibos 200", st == 200, f"{st}")
    if isinstance(recs, list) and recs:
        check("recibo expone rechazado_total (014 viva)",
              "rechazado_total" in recs[0], list(recs[0].keys()))

    # 3. ciclo soft-delete de caja: crear movimiento $1, anularlo, planilla intacta
    st, pl0 = _req("GET", base, "/caja/planilla", tok)
    check("planilla 200", st == 200, f"{st}")
    st, conc = _req("POST", base, "/caja/conceptos", tok,
                    {"nombre": f"Smoke014 {SUF}", "tipo": "salida"})
    check("concepto smoke", st == 201, f"{st} {conc}")
    st, mv = _req("POST", base, "/caja/movimientos", tok, {
        "concepto_id": conc["id"], "medio": "efectivo", "importe": "1.00",
        "descripcion": f"smoke 014 {SUF}",
    })
    check("movimiento de caja (columnas 014 escriben)", st == 201, f"{st} {mv}")
    st, _ = _req("DELETE", base, f"/caja/movimientos/{mv['id']}", tok)
    check("soft-delete de movimiento", st == 204, f"{st}")
    st, pl1 = _req("GET", base, "/caja/planilla", tok)
    check("planilla no cuenta el anulado (delta 0)",
          Decimal(str(pl1["salidas_efectivo"])) == Decimal(str(pl0["salidas_efectivo"])),
          f"{pl0['salidas_efectivo']} -> {pl1['salidas_efectivo']}")
    st, movs = _req("GET", base, "/caja/movimientos", tok)
    check("listado no muestra el anulado", all(m["id"] != mv["id"] for m in movs), "aparece")
    _req("PATCH", base, f"/caja/conceptos/{conc['id']}", tok, {"activo": False})

    # 4. regresiones baratas de lectura
    st, _ = _req("GET", base, "/ventas/comprobantes?limit=1", tok)
    check("listado ventas 200", st == 200, f"{st}")
    st, _ = _req("GET", base, "/compras/comprobantes?limit=1", tok)
    check("listado compras 200", st == 200, f"{st}")
    st, _ = _req("GET", base, "/tesoreria/cashflow", tok)
    check("cashflow 200", st == 200, f"{st}")
    st, _ = _req("GET", base, "/dashboard/kpis", tok)
    check("KPIs 200", st == 200, f"{st}")

    print(f"\n===== SMOKE PROD 014: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
