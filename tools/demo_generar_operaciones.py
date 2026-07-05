r"""
Generador de ~3 meses de operaciones DEMO para ZGC (paso 3).

Usa la API HTTP (camino seguro: numeración, stock, IVA y cta.cte. los maneja el
servidor; imposible violar invariantes). Requiere el tenant demo ya seteado
(demo_setup_tenant.py) y sus maestros migrados (migrar_*.py). Modo ARCA simulado.

Estrategia (informe de investigación):
  1. Login como usuario demo.
  2. Muestrea un subconjunto de artículos (los que tengan precio de venta),
     clientes y proveedores.
  3. COMPRAS DE APERTURA backdated al inicio de la ventana: abastecen stock para
     que las ventas posteriores no queden negativas. Realista: primero comprás.
  4. VENTAS repartidas en la ventana, en orden cronológico ascendente
     (numeración crece con la fecha). Cada venta: crear borrador con `fecha`
     pasada -> emitir. Mezcla contado / cuenta corriente y B (consumidor final) /
     A (cliente con CUIT).

Determinístico: usa random.seed fijo para que una re-corrida sea reproducible.
No borra nada; si lo corrés dos veces, DUPLICA operaciones (pensado para correr
una vez sobre un tenant recién seteado).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\demo_generar_operaciones.py \
        --base http://localhost:8021 --clave "DemosAFu4MB1!" \
        --meses 3 --ventas 180 --compras 40
"""

import argparse
import random
from datetime import date, timedelta

import httpx

EMAIL_DEMO = "demo@zaris.com.ar"
SEED = 20260705


def log(msg: str) -> None:
    print(msg, flush=True)


class Api:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.h = {"Authorization": f"Bearer {token}"}
        self.cli = httpx.Client(timeout=30.0)

    def get(self, path: str, **params):
        r = self.cli.get(f"{self.base}/api/v1{path}", headers=self.h, params=params)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, body: dict):
        r = self.cli.post(f"{self.base}/api/v1{path}", headers=self.h, json=body)
        r.raise_for_status()
        return r.json()


def login(base: str, clave: str) -> str:
    r = httpx.post(
        f"{base.rstrip('/')}/api/v1/auth/login",
        json={"email": EMAIL_DEMO, "password": clave},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def paginar(api: Api, path: str, **extra) -> list[dict]:
    """Trae todas las páginas de un listado (limit/offset)."""
    out, offset = [], 0
    while True:
        page = api.get(path, limit=100, offset=offset, **extra)
        if not page:
            break
        out.extend(page)
        if len(page) < 100:
            break
        offset += 100
    return out


def fecha_aleatoria(inicio: date, fin: date, rng: random.Random) -> date:
    dias = (fin - inicio).days
    return inicio + timedelta(days=rng.randint(0, max(dias, 0)))


def main() -> None:
    ap = argparse.ArgumentParser(description="Generar operaciones demo (ventas/compras)")
    ap.add_argument("--base", default="http://localhost:8021")
    ap.add_argument("--clave", required=True)
    ap.add_argument("--meses", type=int, default=3)
    ap.add_argument("--ventas", type=int, default=180)
    ap.add_argument("--compras", type=int, default=40)
    args = ap.parse_args()

    rng = random.Random(SEED)
    hoy = date.today()
    inicio = hoy - timedelta(days=args.meses * 30)
    # las compras de apertura caen en los primeros 7 días de la ventana
    fin_apertura = inicio + timedelta(days=7)

    token = login(args.base, args.clave)
    api = Api(args.base, token)
    log(f"Login OK. Ventana: {inicio} .. {hoy}")

    # --- prerequisitos (punto de venta, depósito) ---
    pvs = api.get("/ventas/puntos-venta")
    pv_id = pvs[0]["id"]
    depos = api.get("/catalogos-articulos/depositos")
    dep_id = next((d["id"] for d in depos if d.get("activo", True)), depos[0]["id"])

    # --- maestros ---
    def num(v) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    articulos = [a for a in paginar(api, "/articulos") if num(a.get("precio_1")) > 0]
    clientes = paginar(api, "/clientes")
    proveedores = paginar(api, "/proveedores")
    log(f"Maestros: {len(articulos)} art. c/precio, {len(clientes)} clientes, {len(proveedores)} prov.")
    if not articulos or not clientes or not proveedores:
        raise SystemExit("Faltan maestros: corré los migradores primero.")

    # subconjunto manejable de artículos "estrella" del demo
    catalogo = rng.sample(articulos, min(120, len(articulos)))

    # ============ 1) COMPRAS DE APERTURA (abastecen stock) ============
    log(f"\n=== Compras de apertura ({args.compras}) ===")
    ok_c = err_c = 0
    numero_prov: dict[str, int] = {}
    for i in range(args.compras):
        prov = rng.choice(proveedores)
        pid = prov["id"]
        numero_prov[pid] = numero_prov.get(pid, rng.randint(1000, 5000)) + 1
        items_art = rng.sample(catalogo, rng.randint(3, 8))
        items = []
        for a in items_art:
            costo = (num(a.get("costo")) or num(a["precio_1"]) * 0.6) or 100.0
            items.append(
                {
                    "articulo_id": a["id"],
                    "cantidad": rng.randint(20, 120),
                    "costo_unitario": round(costo, 2),
                    "tasa_iva": a.get("tasa_iva", 21),
                }
            )
        f = fecha_aleatoria(inicio, fin_apertura, rng)
        try:
            borrador = api.post(
                "/compras/comprobantes",
                {
                    "clase": "factura",
                    "letra": "A",
                    "punto_venta": 1,
                    "numero": numero_prov[pid],
                    "proveedor_id": pid,
                    "fecha": f.isoformat(),
                    "contado": rng.random() < 0.5,
                    "deposito_id": dep_id,
                    "actualiza_stock": True,
                    "actualiza_costos": True,
                    "items": items,
                },
            )
            api.post(f"/compras/comprobantes/{borrador['id']}/registrar", {})
            ok_c += 1
        except httpx.HTTPStatusError as e:
            err_c += 1
            if err_c <= 3:
                log(f"  compra err: {e.response.status_code} {e.response.text[:160]}")
    log(f"Compras: {ok_c} OK, {err_c} error")

    # ============ 2) VENTAS repartidas en la ventana ============
    log(f"\n=== Ventas ({args.ventas}) — orden cronológico ===")
    # fechas ascendentes: la numeración crece con la fecha (realista)
    fechas = sorted(fecha_aleatoria(fin_apertura, hoy, rng) for _ in range(args.ventas))
    clientes_con_cuit = [c for c in clientes if c.get("nro_documento")]
    ok_v = err_v = 0
    for idx, f in enumerate(fechas):
        # 55% consumidor final (B, sin cliente), 45% cliente con cuenta
        if rng.random() < 0.45 and clientes:
            cli = rng.choice(clientes)
            cliente_id = cli["id"]
        else:
            cliente_id = None
        items_art = rng.sample(catalogo, rng.randint(1, 5))
        items = []
        for a in items_art:
            items.append(
                {
                    "articulo_id": a["id"],
                    "cantidad": rng.randint(1, 6),
                    "precio_unitario": round(num(a["precio_1"]), 2),
                    "tasa_iva": a.get("tasa_iva", 21),
                }
            )
        contado = rng.random() < 0.7
        try:
            borrador = api.post(
                "/ventas/comprobantes",
                {
                    "clase": "factura",
                    "punto_venta_id": pv_id,
                    "cliente_id": cliente_id,
                    "fecha": f.isoformat(),
                    "contado": contado,
                    "deposito_id": dep_id,
                    "actualiza_stock": True,
                    "items": items,
                },
            )
            api.post(f"/ventas/comprobantes/{borrador['id']}/emitir", {})
            ok_v += 1
        except httpx.HTTPStatusError as e:
            err_v += 1
            if err_v <= 5:
                log(f"  venta err ({f}): {e.response.status_code} {e.response.text[:160]}")
        if (idx + 1) % 40 == 0:
            log(f"  ... {idx + 1}/{len(fechas)} ventas ({ok_v} OK)")
    log(f"Ventas: {ok_v} OK, {err_v} error")

    log("\n=== GENERACIÓN COMPLETA ===")
    log(f"Compras OK: {ok_c}  |  Ventas OK: {ok_v}")
    log("Recordá: el kardex (stock_movimientos.fecha) se corrige aparte con el UPDATE post-generación.")


if __name__ == "__main__":
    main()
