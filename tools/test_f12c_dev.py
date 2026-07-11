r"""Suite en vivo de F12-c (despiece / transformación de stock) contra DEV.

Cubre: plantillas de despiece (CRUD, validaciones de coherencia, 409 nombre),
transformación con costeo proporcional al VALOR (fórmula del diseño §2.2
verificada al centavo), merma explícita, costo_total default (costo vigente ×
cantidad), actualización del costo por corte en su convención, kardex atado
por grupo_id con costo sellado, saldos resultantes, guardas 422 (merma
negativa, origen entre cortes, corte sin controla_stock) y NEUTRALIDAD
contable (la transformación no deriva asientos; el ajuste inicial sí).

El tenant de prueba se elimina al final (DELETE por cascada vía SQL directo).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_f12c_dev.py \
        --base http://127.0.0.1:8021
"""

import argparse
import asyncio
import datetime as dt
import json
import subprocess
import sys
import urllib.error as E
import urllib.request as U
import uuid
from decimal import Decimal
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    razon = f"Carniceria F12c {SUF}"
    email = f"carne.{SUF}@zgc.dev"
    clave = f"clave-{SUF}"

    # ===== 1. tenant efímero (rubro carniceria) =====
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", razon, "--email", email, "--clave", clave,
         "--plan", "suite", "--rubro", "carniceria"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    check("setup_tenant.py rubro carniceria corre OK", r.returncode == 0, r.stdout + r.stderr)

    st, login = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    check("login -> 200", st == 200, f"{st} {login}")
    if st != 200:
        sys.exit(1)
    tok = login["access_token"]

    st, depositos = _req("GET", base, "/catalogos-articulos/depositos", tok)
    check("depósito default del setup", st == 200 and len(depositos) >= 1, f"{st}")
    dep_id = depositos[0]["id"]

    # ===== 2. artículos: media res + cortes =====
    def alta(codigo, descripcion, **extra):
        st, a = _req("POST", base, "/articulos", tok, {
            "codigo": codigo, "descripcion": descripcion, "tasa_iva": 21, **extra,
        })
        check(f"alta {descripcion} -> 201", st == 201, f"{st} {a}")
        return a

    media = alta(f"MEDIA{SUF}", f"Media res {SUF}", costo=5000, precio_1=0)
    lomo = alta(f"LOMO{SUF}", f"Lomo {SUF}", precio_1=15000)
    asado = alta(f"ASADO{SUF}", f"Asado {SUF}", precio_1=9000)
    hueso = alta(f"HUESO{SUF}", f"Hueso {SUF}", precio_1=1000)
    servicio = alta(f"SERV{SUF}", f"Servicio sin stock {SUF}", controla_stock=False)

    # stock inicial de media res: 150 kg
    st, _ = _req("POST", base, "/stock/ajuste", tok, {
        "articulo_id": media["id"], "deposito_id": dep_id, "delta": "150",
        "observaciones": "carga inicial",
    })
    check("ajuste inicial media res +150 -> 201", st == 201, f"{st}")

    # ===== 3. plantillas =====
    st, plantilla = _req("POST", base, "/stock/despiece-plantillas", tok, {
        "nombre": f"Media res estándar {SUF}",
        "articulo_origen_id": media["id"],
        "cortes": [
            {"articulo_id": lomo["id"], "rendimiento_pct": "4", "coef_valor": "3"},
            {"articulo_id": asado["id"], "rendimiento_pct": "60", "coef_valor": "1.5"},
            {"articulo_id": hueso["id"], "rendimiento_pct": "33", "coef_valor": "0.2"},
        ],
    })
    check("crear plantilla -> 201", st == 201, f"{st} {plantilla}")
    check("plantilla con origen resuelto",
          st == 201 and plantilla["origen_codigo"] == f"MEDIA{SUF}"
          and len(plantilla["cortes"]) == 3, f"{plantilla}")

    st, _ = _req("POST", base, "/stock/despiece-plantillas", tok, {
        "nombre": f"Media res estándar {SUF}",
        "articulo_origen_id": media["id"],
        "cortes": [{"articulo_id": lomo["id"], "rendimiento_pct": "4", "coef_valor": "3"}],
    })
    check("plantilla duplicada -> 409", st == 409, f"{st}")

    st, _ = _req("POST", base, "/stock/despiece-plantillas", tok, {
        "nombre": f"Origen en cortes {SUF}",
        "articulo_origen_id": media["id"],
        "cortes": [{"articulo_id": media["id"], "rendimiento_pct": "50", "coef_valor": "1"}],
    })
    check("plantilla con origen entre los cortes -> 422", st == 422, f"{st}")

    st, _ = _req("POST", base, "/stock/despiece-plantillas", tok, {
        "nombre": f"Rinde imposible {SUF}",
        "articulo_origen_id": media["id"],
        "cortes": [
            {"articulo_id": lomo["id"], "rendimiento_pct": "70", "coef_valor": "1"},
            {"articulo_id": asado["id"], "rendimiento_pct": "60", "coef_valor": "1"},
        ],
    })
    check("rendimientos > 100% -> 422", st == 422, f"{st}")

    st, plantilla2 = _req("PUT", base, f"/stock/despiece-plantillas/{plantilla['id']}", tok, {
        "nombre": f"Media res v2 {SUF}",
        "articulo_origen_id": media["id"],
        "cortes": [
            {"articulo_id": lomo["id"], "rendimiento_pct": "5", "coef_valor": "3"},
            {"articulo_id": asado["id"], "rendimiento_pct": "58", "coef_valor": "1.5"},
        ],
    })
    check("editar plantilla (reemplaza cortes) -> 200",
          st == 200 and len(plantilla2["cortes"]) == 2 and plantilla2["nombre"].startswith("Media res v2"),
          f"{st} {plantilla2}")

    st, lista = _req("GET", base, "/stock/despiece-plantillas", tok)
    check("listar plantillas", st == 200 and len(lista) == 1, f"{st} {lista}")

    # ===== 4. transformación con costeo por valor (ejemplo del diseño) =====
    # 100 kg a $500.000; lomo 4 kg coef 3 · asado 60 kg coef 1.5 · hueso 33 kg coef 0.2
    # denominador = 12 + 90 + 6.6 = 108.6
    st, tr = _req("POST", base, "/stock/transformacion", tok, {
        "deposito_id": dep_id,
        "articulo_origen_id": media["id"],
        "cantidad_origen": "100",
        "costo_total": "500000",
        "cortes": [
            {"articulo_id": lomo["id"], "cantidad": "4", "coef_valor": "3"},
            {"articulo_id": asado["id"], "cantidad": "60", "coef_valor": "1.5"},
            {"articulo_id": hueso["id"], "cantidad": "33", "coef_valor": "0.2"},
        ],
        "observaciones": "ingreso de media res del frigorífico",
    })
    check("transformación -> 201", st == 201, f"{st} {tr}")
    if st != 201:
        sys.exit(1)
    check("merma 3 kg", Decimal(tr["merma"]) == 3, f"{tr['merma']}")
    costos = {c["articulo_id"]: Decimal(c["costo_unitario"]) for c in tr["costos_corte"]}
    check("costo lomo = 500000×3/108.6", costos[lomo["id"]] == Decimal("13812.1547"),
          f"{costos[lomo['id']]}")
    check("costo asado = 500000×1.5/108.6", costos[asado["id"]] == Decimal("6906.0773"),
          f"{costos[asado['id']]}")
    check("costo hueso = 500000×0.2/108.6", costos[hueso["id"]] == Decimal("920.8103"),
          f"{costos[hueso['id']]}")
    valor_entradas = 4 * costos[lomo["id"]] + 60 * costos[asado["id"]] + 33 * costos[hueso["id"]]
    check("Σ(kg × costo) ≈ costo_total (neutro en valor)",
          abs(valor_entradas - Decimal("500000")) < Decimal("0.05"), f"{valor_entradas}")
    check("salida -100 con saldo 50", Decimal(tr["salida"]["cantidad"]) == -100
          and Decimal(tr["salida"]["saldo_resultante"]) == 50, f"{tr['salida']}")
    check("salida sella costo unitario origen (5000)",
          Decimal(tr["salida"]["costo_unitario"]) == 5000, f"{tr['salida']}")
    check("salida registra la merma en observaciones",
          "Merma 3" in (tr["salida"]["observaciones"] or ""), f"{tr['salida']}")
    check("3 entradas con el mismo grupo_id",
          len(tr["entradas"]) == 3
          and all(e["grupo_id"] == tr["grupo_id"] for e in tr["entradas"])
          and tr["salida"]["grupo_id"] == tr["grupo_id"], f"{tr}")
    check("entradas tipo transformacion",
          all(e["tipo"] == "transformacion" for e in tr["entradas"]), f"{tr}")

    st, lomo_full = _req("GET", base, f"/articulos/{lomo['id']}", tok)
    check("costo del corte actualizado (lomo)",
          st == 200 and Decimal(lomo_full["costo"]) == Decimal("13812.1547"),
          f"{st} {lomo_full.get('costo')}")

    st, kardex = _req("GET", base, f"/stock/kardex/{lomo['id']}", tok)
    check("kardex del lomo: entrada por transformación con costo sellado",
          st == 200 and any(
              m["tipo"] == "transformacion" and Decimal(m["cantidad"]) == 4
              and Decimal(m["costo_unitario"]) == Decimal("13812.1547")
              for m in kardex
          ), f"{st} {kardex}")

    # ===== 5. costo_total default (costo vigente del origen × cantidad) =====
    st, tr2 = _req("POST", base, "/stock/transformacion", tok, {
        "deposito_id": dep_id,
        "articulo_origen_id": media["id"],
        "cantidad_origen": "10",
        "cortes": [{"articulo_id": asado["id"], "cantidad": "9", "coef_valor": "1"}],
    })
    check("transformación sin costo_total -> 201 (usa costo vigente)",
          st == 201 and Decimal(tr2["costo_total"]) == Decimal("50000"), f"{st} {tr2}")
    check("coef 1: prorrateo por peso (50000/9)",
          Decimal(tr2["costos_corte"][0]["costo_unitario"]) == Decimal("5555.5556"),
          f"{tr2['costos_corte']}")

    # ===== 6. guardas =====
    st, _ = _req("POST", base, "/stock/transformacion", tok, {
        "deposito_id": dep_id, "articulo_origen_id": media["id"], "cantidad_origen": "5",
        "cortes": [{"articulo_id": asado["id"], "cantidad": "6", "coef_valor": "1"}],
    })
    check("cortes > origen (merma negativa) -> 422", st == 422, f"{st}")
    st, _ = _req("POST", base, "/stock/transformacion", tok, {
        "deposito_id": dep_id, "articulo_origen_id": media["id"], "cantidad_origen": "5",
        "cortes": [{"articulo_id": media["id"], "cantidad": "5", "coef_valor": "1"}],
    })
    check("origen entre los cortes -> 422", st == 422, f"{st}")
    st, _ = _req("POST", base, "/stock/transformacion", tok, {
        "deposito_id": dep_id, "articulo_origen_id": media["id"], "cantidad_origen": "5",
        "cortes": [{"articulo_id": servicio["id"], "cantidad": "5", "coef_valor": "1"}],
    })
    check("corte sin controla_stock -> 422", st == 422, f"{st}")
    st, _ = _req("POST", base, "/stock/transformacion", tok, {
        "deposito_id": dep_id, "articulo_origen_id": servicio["id"], "cantidad_origen": "5",
        "cortes": [{"articulo_id": asado["id"], "cantidad": "5", "coef_valor": "1"}],
    })
    check("origen sin controla_stock -> 422", st == 422, f"{st}")

    # ===== 7. neutralidad contable: la transformación NO deriva asientos =====
    hoy = dt.date.today().isoformat()
    st, resumen = _req("POST", base, "/contabilidad/regenerar", tok,
                       {"desde": hoy, "hasta": hoy})
    check("regenerar contabilidad del día -> 200", st == 200, f"{st} {resumen}")
    st, asientos = _req("GET", base, f"/contabilidad/asientos?origen=stock_ajuste&desde={hoy}&hasta={hoy}", tok)
    check("solo el ajuste inicial derivó asiento (transformación neutra)",
          st == 200 and len(asientos) == 1, f"{st} n={len(asientos) if st == 200 else '?'}")

    # saldo final de media res: 150 − 100 − 10 = 40
    st, stock_media = _req("GET", base, f"/stock/articulo/{media['id']}", tok)
    check("saldo final media res = 40",
          st == 200 and any(Decimal(f["cantidad"]) == 40 for f in stock_media),
          f"{st} {stock_media}")

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
