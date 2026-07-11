r"""Suite en vivo de F12-b (POS súper: pesables por etiqueta de balanza, envases
retornables y venta por departamento) contra DEV.

Cubre: config de balanza por tenant (upsert + validaciones), codigo_balanza en
artículos (normalización, unicidad, 422 no numérico), parsing server-side de
etiquetas EAN-13 en GET /pos/buscar (peso y importe, DV inválido, PLU
inexistente, config deshabilitada), PLU tipeado directo, envase asociado en la
búsqueda, departamentos (listado + venta con importe tipeado + guardas 422) y
una venta POS completa con pesable + depto + envase que descarga stock.

El tenant de prueba se elimina al final (DELETE por cascada vía SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_f12b_dev.py \
        --base http://127.0.0.1:8021
"""

import argparse
import asyncio
import json
import subprocess
import sys
import urllib.error as E
import urllib.request as U
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

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


def dv_ean13(doce: str) -> int:
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(doce))
    return (10 - suma % 10) % 10


def etiqueta(prefijo: str, plu: int, valor: int, codigo_digitos: int = 5) -> str:
    doce = f"{prefijo}{plu:0{codigo_digitos}d}{valor:0{10 - codigo_digitos}d}"
    return doce + str(dv_ean13(doce))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    razon = f"Super F12b {SUF}"
    email = f"super.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 1. tenant efímero (suite, rubro supermercado) =====
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", "suite", "--rubro", "supermercado"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    check("setup_tenant.py rubro supermercado corre OK", r.returncode == 0, r.stdout + r.stderr)

    st, login = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    check("login -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    st, cajas = _req("GET", base, "/pos/cajas", tok)
    check("GET /pos/cajas trae la caja default", st == 200 and len(cajas) >= 1, f"{st} {cajas}")
    caja_id = cajas[0]["id"]

    # ===== 2. config de balanza =====
    st, cfg = _req("GET", base, "/pos/balanza-config", tok)
    check("GET /pos/balanza-config sin configurar -> null", st == 200 and cfg is None, f"{st} {cfg}")
    st, cfg = _req("PUT", base, "/pos/balanza-config", tok,
                   {"habilitado": True, "prefijo": "20", "valor_tipo": "peso", "codigo_digitos": 5})
    check("PUT /pos/balanza-config -> 200", st == 200 and cfg["prefijo"] == "20", f"{st} {cfg}")
    st, cfg = _req("GET", base, "/pos/balanza-config", tok)
    check("GET devuelve la config guardada", st == 200 and cfg and cfg["valor_tipo"] == "peso",
          f"{st} {cfg}")
    st, _ = _req("PUT", base, "/pos/balanza-config", tok,
                 {"habilitado": True, "prefijo": "30", "valor_tipo": "peso", "codigo_digitos": 5})
    check("prefijo fuera de 20-29 -> 422", st == 422, f"{st}")
    st, _ = _req("PUT", base, "/pos/balanza-config", tok,
                 {"habilitado": True, "prefijo": "20", "valor_tipo": "peso", "codigo_digitos": 8})
    check("codigo_digitos > 7 -> 422", st == 422, f"{st}")

    # ===== 3. artículos: codigo_balanza + envase + depto =====
    st, carne = _req("POST", base, "/articulos", tok, {
        "codigo": f"CARNE{SUF}", "descripcion": f"Carne picada {SUF}",
        "tasa_iva": 21, "precio_1": 4500, "pesable": True, "codigo_balanza": "123",
    })
    check("alta pesable con codigo_balanza -> 201", st == 201, f"{st} {carne}")
    check("codigo_balanza guardado normalizado", carne.get("codigo_balanza") == "123", f"{carne}")

    st, _ = _req("POST", base, "/articulos", tok, {
        "codigo": f"DUP{SUF}", "descripcion": "Duplicado PLU",
        "tasa_iva": 21, "precio_1": 100, "pesable": True, "codigo_balanza": "0123",
    })
    check("PLU duplicado (0123 ≡ 123) -> 409", st == 409, f"{st}")
    st, _ = _req("POST", base, "/articulos", tok, {
        "codigo": f"MAL{SUF}", "descripcion": "PLU no numérico",
        "tasa_iva": 21, "precio_1": 100, "codigo_balanza": "12a",
    })
    check("PLU no numérico -> 422", st == 422, f"{st}")

    st, envase = _req("POST", base, "/articulos", tok, {
        "codigo": f"ENV{SUF}", "descripcion": f"Envase retornable {SUF}",
        "tasa_iva": 21, "precio_1": 500, "es_envase_retornable": True,
        "controla_stock": True,
    })
    check("alta envase retornable -> 201", st == 201, f"{st} {envase}")
    st, coca = _req("POST", base, "/articulos", tok, {
        "codigo": f"COCA{SUF}", "descripcion": f"Gaseosa retornable {SUF}",
        "tasa_iva": 21, "precio_1": 2000, "envase_articulo_id": envase["id"],
    })
    check("alta artículo con envase asociado -> 201", st == 201, f"{st} {coca}")

    st, envases_lista = _req("GET", base, "/articulos?es_envase=true", tok)
    check("GET /articulos?es_envase=true filtra envases",
          st == 200 and any(a["id"] == envase["id"] for a in envases_lista)
          and all(a["es_envase_retornable"] for a in envases_lista), f"{st}")

    st, depto = _req("POST", base, "/articulos", tok, {
        "codigo": f"VARIOS{SUF}", "descripcion": f"Departamento varios {SUF}",
        "tasa_iva": 21, "venta_por_depto": True, "controla_stock": False,
    })
    check("alta artículo-departamento -> 201", st == 201, f"{st} {depto}")

    st, deptos = _req("GET", base, "/pos/departamentos", tok)
    check("GET /pos/departamentos lo lista",
          st == 200 and any(d["articulo_id"] == depto["id"] for d in deptos), f"{st} {deptos}")

    # ===== 4. parsing de etiquetas en /pos/buscar =====
    q = etiqueta("20", 123, 1500)  # 1.500 kg
    st, res = _req("GET", base, f"/pos/buscar?q={q}&caja_id={caja_id}", tok)
    check("etiqueta peso -> 1 resultado exacto", st == 200 and len(res) == 1 and res[0]["exacto"],
          f"{st} {res}")
    if st == 200 and res:
        check("etiqueta peso: artículo por PLU", res[0]["articulo_id"] == carne["id"], f"{res[0]}")
        check("etiqueta peso: cantidad 1.500 kg", res[0]["cantidad"] == "1.500", f"{res[0]}")
        check("etiqueta peso: precio de lista de la caja", float(res[0]["precio"]) == 4500.0,
              f"{res[0]}")

    q_mal = q[:12] + str((int(q[12]) + 1) % 10)  # DV inválido
    st, res = _req("GET", base, f"/pos/buscar?q={q_mal}&caja_id={caja_id}", tok)
    check("etiqueta con DV inválido no parsea (búsqueda normal vacía)",
          st == 200 and (not res or res[0].get("cantidad") is None), f"{st} {res}")

    q999 = etiqueta("20", 99911, 1000)
    st, res = _req("GET", base, f"/pos/buscar?q={q999}&caja_id={caja_id}", tok)
    check("etiqueta con PLU inexistente no matchea", st == 200 and not res, f"{st} {res}")

    st, res = _req("GET", base, f"/pos/buscar?q=123&caja_id={caja_id}", tok)
    check("PLU tipeado directo -> match exacto",
          st == 200 and len(res) == 1 and res[0]["articulo_id"] == carne["id"] and res[0]["exacto"],
          f"{st} {res}")

    # modo importe: $45.00 embebidos a $4500/kg = 0.010 kg
    st, _ = _req("PUT", base, "/pos/balanza-config", tok,
                 {"habilitado": True, "prefijo": "20", "valor_tipo": "importe", "codigo_digitos": 5})
    check("PUT balanza modo importe -> 200", st == 200, f"{st}")
    q_imp = etiqueta("20", 123, 4500)  # 4500 centavos = $45.00
    st, res = _req("GET", base, f"/pos/buscar?q={q_imp}&caja_id={caja_id}", tok)
    check("etiqueta importe: cantidad = importe/precio",
          st == 200 and len(res) == 1 and res[0]["cantidad"] == "0.010", f"{st} {res}")

    st, _ = _req("PUT", base, "/pos/balanza-config", tok,
                 {"habilitado": False, "prefijo": "20", "valor_tipo": "peso", "codigo_digitos": 5})
    st, res = _req("GET", base, f"/pos/buscar?q={q}&caja_id={caja_id}", tok)
    check("config deshabilitada: la etiqueta no parsea", st == 200 and not res, f"{st} {res}")
    _req("PUT", base, "/pos/balanza-config", tok,
         {"habilitado": True, "prefijo": "20", "valor_tipo": "peso", "codigo_digitos": 5})

    # ===== 5. envase asociado en la búsqueda =====
    st, res = _req("GET", base, f"/pos/buscar?q=COCA{SUF}&caja_id={caja_id}", tok)
    check("buscar por código exacto trae envase asociado",
          st == 200 and len(res) == 1 and res[0]["envase"]
          and res[0]["envase"]["articulo_id"] == envase["id"]
          and float(res[0]["envase"]["precio"]) == 500.0, f"{st} {res}")
    st, res = _req("GET", base, f"/pos/buscar?q=CARNE{SUF}&caja_id={caja_id}", tok)
    check("artículo sin envase -> envase null",
          st == 200 and len(res) == 1 and res[0]["envase"] is None, f"{st} {res}")

    # ===== 6. venta por departamento: cálculo y guardas =====
    st, calc = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id,
        "items": [{"articulo_id": depto["id"], "cantidad": "1", "precio_unitario": "1210"}],
    })
    check("calcular depto con importe tipeado -> 200 total 1210",
          st == 200 and float(calc["total"]) == 1210.0, f"{st} {calc}")
    st, _ = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id,
        "items": [{"articulo_id": depto["id"], "cantidad": "1"}],
    })
    check("depto sin importe -> 422", st == 422, f"{st}")
    st, _ = _req("POST", base, "/pos/ventas/calcular", tok, {
        "caja_id": caja_id,
        "items": [{"articulo_id": carne["id"], "cantidad": "1", "precio_unitario": "99"}],
    })
    check("importe tipeado en artículo común -> 422", st == 422, f"{st}")

    # ===== 7. venta POS completa: pesable + depto + envase =====
    st, sesion = _req("POST", base, "/pos/sesiones", tok,
                      {"caja_id": caja_id, "fondo_inicial": "1000"})
    check("abrir sesión POS -> 201", st == 201, f"{st} {sesion}")
    items = [
        {"articulo_id": carne["id"], "cantidad": "1.500"},
        {"articulo_id": coca["id"], "cantidad": "2"},
        {"articulo_id": envase["id"], "cantidad": "2"},
        {"articulo_id": depto["id"], "cantidad": "1", "precio_unitario": "1210"},
    ]
    st, calc = _req("POST", base, "/pos/ventas/calcular", tok,
                    {"caja_id": caja_id, "items": items})
    check("calcular venta mixta -> 200", st == 200, f"{st} {calc}")
    total = calc["total"]
    st, venta = _req("POST", base, "/pos/ventas", tok, {
        "sesion_id": sesion["id"], "items": items,
        "medios": [{"medio": "efectivo", "importe": total}],
    })
    check("venta POS mixta emitida -> 201", st == 201, f"{st} {venta}")
    check("venta con número fiscal", bool(venta.get("numero_formateado")), f"{venta}")

    st, stock = _req("GET", base, f"/stock/articulo/{carne['id']}", tok)
    check("la venta descargó 1.500 kg del pesable",
          st == 200 and any(float(f["cantidad"]) == -1.5 for f in stock), f"{st} {stock}")
    st, stock_env = _req("GET", base, f"/stock/articulo/{envase['id']}", tok)
    check("la venta descargó 2 envases",
          st == 200 and any(float(f["cantidad"]) == -2 for f in stock_env), f"{st} {stock_env}")

    st, resumen = _req("GET", base, f"/pos/sesiones/{sesion['id']}/resumen", tok)
    check("resumen de sesión suma la venta",
          st == 200 and resumen["cantidad_tickets"] == 1
          and float(resumen["total_ventas"]) == float(total), f"{st} {resumen}")
    _req("POST", base, f"/pos/sesiones/{sesion['id']}/cerrar", tok, {"efectivo_contado": None})

    # ===== 8. cleanup =====
    async def _cleanup():
        from sqlalchemy import text as _text

        from app.core.db import SessionLocal

        async with SessionLocal() as db:
            await db.execute(
                _text("delete from tenants where razon_social = :r"), {"r": razon}
            )
            await db.commit()

    try:
        asyncio.run(_cleanup())
        print(f"  --  cleanup: tenant '{razon}' eliminado")
    except Exception as ex:  # noqa: BLE001
        print(f"  !!  cleanup falló (borrar a mano): {ex}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
