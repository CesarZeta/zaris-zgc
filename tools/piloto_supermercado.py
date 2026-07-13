r"""
PILOTO FICTICIO «Supermercado ZARIS» — un mes completo de operación (junio 2026)
tocando TODOS los módulos, con registros reales generados por la API pública.

Plan aprobado por César 2026-07-13 (junto con F12-bis, que este piloto estrena):
  - Tenant nuevo plan suite, rubro supermercado, con 2 cajas POS (PV 0002/0003)
    y PV 0001 para la facturación de gestión.
  - Compras PRIMERO (2 facturas A de mercadería) → stock → ventas.
  - 50 tickets POS de 3-10 artículos con cantidades/medios aleatorios,
    repartidos en ~10 jornadas de junio entre las 2 cajas, con apertura/cierre
    de sesión y arqueo (una jornada con diferencia). Incluye: pesable por
    etiqueta de balanza, venta por departamento, envase retornable, descuentos
    F7 (línea y venta), ticket a cliente identificado (factura A) y 2
    anulaciones con supervisor (NC espejo).
  - Gestión: facturas A/B en cta. cte. con vendedor sellado, presupuesto,
    remitos, NC, cobranzas (totales/parciales/a cuenta), cheques de terceros
    (uno acreditado, uno RECHAZADO que reabre deuda, uno endosado), OP por
    transferencia y con cheque propio diferido, retenciones sufrida/practicada,
    caja con movimientos manuales y cierres con arqueo, transferencia entre
    cuentas propias APAREADA, extracto bancario conciliado, bien de uso con
    amortización derivada, asiento de apertura asistido, logística (entregas →
    hoja de ruta → rendición con un rechazo), comisiones liquidadas, y
    contabilidad REGENERADA con el período junio CERRADO.
  - Sueldos: EXCLUIDO (F15 no existe — decisión de César).

Backdating: ventas/compras/recibos/OP/caja/bancos/retenciones aceptan `fecha`
por API (modo ARCA simulado). El POS NO (a propósito: no se toca el producto
para simular) → los tickets se emiten por los endpoints POS reales y un
RETOQUE SQL FINAL, acotado al tenant del piloto, corre las fechas de sesiones,
comprobantes POS, kardex y logística a sus días de junio. La contabilidad se
regenera DESPUÉS del retoque (los asientos derivan de las fechas finales).

Los cheques diferidos se gestionan con fechas de pago de julio: el depósito /
acreditación / rechazo ocurren HOY (realista: un cheque recibido en junio al
día 30/45 se gestiona en julio) — sin retoque.

NO idempotente: correrlo dos veces duplica operaciones. Pensado para correr
UNA vez sobre el tenant recién creado (el propio script lo crea via
setup_tenant.py). Determinístico (seed fija).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\piloto_supermercado.py `
        --base http://localhost:8021 --clave "PilotoSuper2026!"
"""

import argparse
import asyncio
import random
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

SEED = 20260601
EMAIL = "piloto@zgc.dev"
RAZON = "Supermercado ZARIS (piloto)"

# ---- calendario del piloto (junio 2026; el 7/14/21/28 son domingos) ----
J = lambda d: date(2026, 6, d)  # noqa: E731
DIAS_POS = [2, 4, 6, 9, 11, 13, 17, 20, 24, 27]  # 10 jornadas de caja


def log(msg: str) -> None:
    print(msg, flush=True)


class Api:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.h = {"Authorization": f"Bearer {token}"}
        self.cli = httpx.Client(timeout=60.0)

    def get(self, path: str, **params):
        r = self.cli.get(f"{self.base}/api/v1{path}", headers=self.h, params=params)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, body: dict | None = None):
        r = self.cli.post(f"{self.base}/api/v1{path}", headers=self.h, json=body or {})
        if r.status_code >= 400:
            raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()

    def put(self, path: str, body: dict):
        r = self.cli.put(f"{self.base}/api/v1{path}", headers=self.h, json=body)
        r.raise_for_status()
        return r.json()


def cuit_valido(prefijo: str, base8: int) -> str:
    """CUIT sintético con DV real; si el DV da 10, varía la base (regla §6-bis)."""
    while True:
        cuerpo = f"{prefijo}{base8:08d}"
        pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        resto = sum(int(d) * p for d, p in zip(cuerpo, pesos)) % 11
        dv = 11 - resto if resto not in (0, 1) else (0 if resto == 0 else 9 if prefijo in ("23", "24") else None)
        if resto == 0:
            dv = 0
        elif resto == 1:
            base8 += 1
            continue
        else:
            dv = 11 - resto
        if dv == 10:
            base8 += 1
            continue
        return cuerpo + str(dv)


def ean13_balanza(prefijo: str, plu: int, gramos: int, plu_dig: int = 5) -> str:
    """Etiqueta de balanza esquema Kretz: P(2) + PLU + VALOR + DV = 13."""
    valor_dig = 12 - len(prefijo) - plu_dig
    cuerpo = f"{prefijo}{plu:0{plu_dig}d}{gramos:0{valor_dig}d}"
    suma = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(cuerpo))
    return cuerpo + str((10 - suma % 10) % 10)


# ============================ CATÁLOGO DEL SÚPER ============================
# (familia, codigo, descripcion, costo neto, precio_1 final, tasa_iva, extras)
CATALOGO = [
    ("Almacén", "ARZ001", "Arroz largo fino 1kg", 950, 1890, 21, {}),
    ("Almacén", "FID002", "Fideos spaghetti 500g", 620, 1250, 21, {}),
    ("Almacén", "ACE003", "Aceite girasol 1.5L", 2400, 4690, 21, {}),
    ("Almacén", "AZU004", "Azúcar 1kg", 780, 1490, 21, {}),
    ("Almacén", "YER005", "Yerba mate 1kg", 3900, 7590, 21, {}),
    ("Almacén", "HAR006", "Harina 000 1kg", 450, 890, 21, {}),
    ("Almacén", "PUR007", "Puré de tomate 520g", 590, 1150, 21, {}),
    ("Almacén", "ATU008", "Atún al natural 170g", 1650, 3190, 21, {}),
    ("Almacén", "GLL009", "Galletitas surtidas 400g", 1100, 2290, 21, {}),
    ("Almacén", "MER010", "Mermelada durazno 454g", 1250, 2450, 21, {}),
    ("Bebidas", "GAS101", "Gaseosa cola 2.25L", 1800, 3490, 21, {}),
    ("Bebidas", "AGU102", "Agua mineral 2L", 700, 1390, 21, {}),
    ("Bebidas", "CER103", "Cerveza rubia 1L retornable", 1500, 2890, 21, {"envase": True}),
    ("Bebidas", "VIN104", "Vino tinto 750ml", 2300, 4590, 21, {}),
    ("Bebidas", "JUG105", "Jugo exprimido 1L", 1400, 2790, 21, {}),
    ("Lácteos", "LEC201", "Leche entera 1L", 950, 1790, 21, {}),
    ("Lácteos", "YOG202", "Yogur bebible 900g", 1350, 2590, 21, {}),
    ("Lácteos", "QUE203", "Queso cremoso x kg", 6500, 12490, 21, {"pesable": 203}),
    ("Lácteos", "MAN204", "Manteca 200g", 1450, 2790, 21, {}),
    ("Lácteos", "CRE205", "Crema de leche 360g", 1600, 3090, 21, {}),
    ("Carnicería", "CAR301", "Carne picada especial x kg", 5200, 8990, 10.5, {"pesable": 301}),
    ("Carnicería", "ASA302", "Asado de tira x kg", 7800, 13490, 10.5, {"pesable": 302}),
    ("Carnicería", "POL303", "Pollo entero x kg", 2400, 4290, 10.5, {"pesable": 303}),
    ("Carnicería", "MIL304", "Milanesa de nalga x kg", 8200, 14290, 10.5, {"pesable": 304}),
    ("Verdulería", "PAP401", "Papa x kg", 550, 1190, 10.5, {"pesable": 401}),
    ("Verdulería", "TOM402", "Tomate redondo x kg", 1300, 2590, 10.5, {"pesable": 402}),
    ("Verdulería", "BAN403", "Banana x kg", 1100, 2290, 10.5, {"pesable": 403}),
    ("Verdulería", "CEB404", "Cebolla x kg", 480, 990, 10.5, {"pesable": 404}),
    ("Panadería", "PAN501", "Pan francés x kg", 1200, 2490, 21, {"pesable": 501}),
    ("Panadería", "FAC502", "Facturas x docena", 2800, 5490, 21, {}),
    ("Limpieza", "LAV601", "Detergente 750ml", 1300, 2590, 21, {}),
    ("Limpieza", "JAB602", "Jabón en polvo 800g", 2200, 4390, 21, {}),
    ("Limpieza", "LAV603", "Lavandina 1L", 600, 1190, 21, {}),
    ("Limpieza", "PAP604", "Papel higiénico x4", 1900, 3790, 21, {}),
    ("Limpieza", "ESP605", "Esponja multiuso", 450, 890, 21, {}),
    ("Perfumería", "SHA701", "Shampoo 400ml", 2600, 5190, 21, {}),
    ("Perfumería", "JAB702", "Jabón de tocador x3", 1400, 2790, 21, {}),
    ("Perfumería", "DEN703", "Dentífrico 90g", 1500, 2990, 21, {}),
    ("Perfumería", "DES704", "Desodorante aerosol", 2300, 4590, 21, {}),
    ("Kiosco", "CHO801", "Chocolate con leche 100g", 1200, 2390, 21, {}),
    ("Kiosco", "CAR802", "Caramelos surtidos 150g", 600, 1190, 21, {}),
    ("Kiosco", "PAP803", "Papas fritas 145g", 1500, 2990, 21, {}),
    ("Kiosco", "ALF804", "Alfajor triple", 700, 1390, 21, {}),
    ("Kiosco", "MAN805", "Maní salado 200g", 900, 1790, 21, {}),
]

CLIENTES = [
    # (razon_social, tipo_doc, doc, cond_iva, domicilio, localidad) — RI = factura A
    ("Comedor Escolar N° 44", "CUIT", ("30", 61224488), "RI", "San Martín 1240", "Rosario"),
    ("Rotisería Don Pepe", "CUIT", ("30", 55887733), "RI", "Mitre 356", "Rosario"),
    ("Kiosco La Parada", "CUIT", ("27", 28455661), "MT", "Av. Pellegrini 2801", "Rosario"),
    ("Club Atlético Barrio Norte", "CUIT", ("30", 70996611), "EX", "Bv. Rondeau 980", "Rosario"),
    ("María Fernanda Ledesma", "DNI", 28455662, "CF", "Catamarca 1520, 2° B", "Rosario"),
    ("Hotel Puerto Viejo", "CUIT", ("30", 68112244), "RI", "Av. Belgrano 750", "Rosario"),
    ("Geriátrico Los Aromos", "CUIT", ("30", 66334455), "RI", "Zeballos 3110", "Rosario"),
    ("Jorge Daniel Peralta", "DNI", 22334455, "CF", "Ovidio Lagos 4470", "Rosario"),
    ("Panadería La Espiga (reventa)", "CUIT", ("20", 31224477), "MT", "Génova 5230", "Rosario"),
    ("Bar El Cruce", "CUIT", ("30", 59887711), "RI", "Córdoba 1180", "Rosario"),
]

PROVEEDORES = [
    ("Distribuidora Litoral SA", ("30", 71553311), "Av. Circunvalación 2500", "Rosario"),
    ("Frigorífico Paraná SRL", ("30", 65442200), "Ruta 11 km 32", "San Lorenzo"),
    ("Lácteos del Centro SA", ("30", 69887744), "Parque Industrial s/n", "Rafaela"),
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Generar el piloto Supermercado ZARIS")
    ap.add_argument("--base", default="http://localhost:8021")
    ap.add_argument("--clave", required=True, help="clave del usuario piloto@zgc.dev (se crea)")
    args = ap.parse_args()
    rng = random.Random(SEED)
    resumen: dict[str, object] = {}

    # ================= 0) tenant piloto via setup_tenant.py =================
    log("=== 0. setup del tenant piloto ===")
    r = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "setup_tenant.py"),
         "--razon", RAZON, "--email", EMAIL, "--clave", args.clave,
         "--plan", "suite", "--rubro", "supermercado"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent / "backend"),
    )
    if r.returncode != 0:
        raise SystemExit(f"setup_tenant falló:\n{r.stdout}\n{r.stderr}")
    log(r.stdout.strip().splitlines()[-1])

    lr = httpx.post(f"{args.base.rstrip('/')}/api/v1/auth/login",
                    json={"email": EMAIL, "password": args.clave}, timeout=30.0)
    lr.raise_for_status()
    api = Api(args.base, lr.json()["access_token"])
    tenant_id = lr.json()["user"]["tenant_id"]
    log(f"login OK — tenant {tenant_id}")

    # plan contable + categorías de activos: seed lazy
    api.get("/contabilidad/plan")
    plan = {c["codigo"]: c for c in api.get("/contabilidad/plan")}
    cat_activos = api.get("/contabilidad/activos/categorias")

    # ================= 1) maestros =================
    log("\n=== 1. maestros ===")
    pvs = api.get("/ventas/puntos-venta")
    pv1 = pvs[0]["id"]  # gestión (0001)
    pv2 = api.post("/ventas/puntos-venta", {"numero": 2, "descripcion": "Caja 1 (salón)"})["id"]
    pv3 = api.post("/ventas/puntos-venta", {"numero": 3, "descripcion": "Caja 2 (salón)"})["id"]
    dep = next(d["id"] for d in api.get("/catalogos-articulos/depositos") if d.get("activo", True))
    sucursal = api.get("/sucursales")[0]["id"]

    # setup_tenant ya crea una caja default: se reconfigura como Caja 1 (PV 0002)
    cajas_previas = {c["nombre"]: c for c in api.get("/pos/cajas")}
    if "Caja 1" in cajas_previas:
        r = api.cli.patch(f"{api.base}/api/v1/pos/cajas/{cajas_previas['Caja 1']['id']}",
                          headers=api.h, json={"punto_venta_id": pv2, "deposito_id": dep,
                                               "sucursal_id": sucursal})
        r.raise_for_status()
        caja1 = r.json()["id"]
    else:
        caja1 = api.post("/pos/cajas", {"nombre": "Caja 1", "punto_venta_id": pv2,
                                        "deposito_id": dep, "sucursal_id": sucursal})["id"]
    caja2 = api.post("/pos/cajas", {"nombre": "Caja 2", "punto_venta_id": pv3,
                                    "deposito_id": dep, "sucursal_id": sucursal})["id"]
    api.put("/pos/balanza-config", {"habilitado": True, "prefijo": "20",
                                    "valor_tipo": "peso", "codigo_digitos": 5})

    familias = {}
    for fam in dict.fromkeys(c[0] for c in CATALOGO):
        familias[fam] = api.post("/catalogos-articulos/familias", {"nombre": fam})["id"]

    # envase retornable (para la cerveza)
    envase_id = api.post("/articulos", {
        "codigo": "ENV100", "descripcion": "Envase botella 1L retornable",
        "tasa_iva": 21, "costo": 300, "precio_1": 800, "es_envase_retornable": True,
        "familia_id": familias["Bebidas"],
    })["id"]

    articulos: list[dict] = []
    depto_id = api.post("/articulos", {
        "codigo": "DEP900", "descripcion": "Bazar y varios (departamento)",
        "tasa_iva": 21, "venta_por_depto": True, "controla_stock": False,
        "familia_id": familias["Almacén"],
    })["id"]
    for fam, cod, desc, costo, precio, tasa, extra in CATALOGO:
        body = {"codigo": cod, "descripcion": desc, "costo": costo, "tasa_iva": tasa,
                "precio_1": precio, "familia_id": familias[fam]}
        if extra.get("pesable"):
            body["pesable"] = True
            body["codigo_balanza"] = str(extra["pesable"])
        if extra.get("envase"):
            body["envase_articulo_id"] = envase_id
        a = api.post("/articulos", body)
        a["_tasa"], a["_costo"], a["_precio"] = tasa, costo, precio
        a["_pesable"] = bool(extra.get("pesable"))
        articulos.append(a)
    log(f"artículos: {len(articulos)} + envase + departamento")

    proveedores = []
    for i, (razon, (pref, base8), dom, loc) in enumerate(PROVEEDORES):
        proveedores.append(api.post("/proveedores", {
            "entidad": {"razon_social": razon, "tipo_persona": "J", "tipo_documento": "CUIT",
                        "nro_documento": cuit_valido(pref, base8), "condicion_iva": "RI",
                        "domicilio": dom, "localidad": loc},
        }))

    conds = api.get("/ventas/condiciones-venta")
    cond_cta = next((c["id"] for c in conds if any(d > 0 for d in c.get("dias", [0]))), None)
    if cond_cta is None:
        cond_cta = api.post("/ventas/condiciones-venta",
                            {"descripcion": "Cuenta corriente 15 días", "dias": [15]})["id"]

    vend1 = api.post("/vendedores", {
        "entidad": {"razon_social": "Sergio Almada", "tipo_documento": "DNI",
                    "nro_documento": "25441822", "condicion_iva": "CF"},
        "codigo": "V1", "comision_pct": "2", "modalidad": "venta"})
    vend2 = api.post("/vendedores", {
        "entidad": {"razon_social": "Valeria Quiroz", "tipo_documento": "DNI",
                    "nro_documento": "31552933", "condicion_iva": "CF"},
        "codigo": "V2", "comision_pct": "1.5", "modalidad": "cobranza"})

    clientes = []
    for i, (razon, tdoc, doc, iva, dom, loc) in enumerate(CLIENTES):
        nro = cuit_valido(*doc) if tdoc == "CUIT" else str(doc)
        c = api.post("/clientes", {
            "entidad": {"razon_social": razon, "tipo_persona": "J" if iva in ("RI", "EX") else "F",
                        "tipo_documento": tdoc, "nro_documento": nro, "condicion_iva": iva,
                        "domicilio": dom, "localidad": loc,
                        "telefono_1": f"341-4{rng.randint(100000, 999999)}"},
            "condicion_venta_id": cond_cta,
            "vendedor_id": (vend1["id"] if i % 2 == 0 else vend2["id"]),
        })
        clientes.append(c)
    ri = [c for c in clientes if c["entidad"]["condicion_iva"] == "RI"]
    cf = [c for c in clientes if c["entidad"]["condicion_iva"] == "CF"]

    transportista = api.post("/logistica/transportistas", {
        "entidad": {"razon_social": "Ramón Ferreyra (reparto propio)", "tipo_documento": "DNI",
                    "nro_documento": "20887744", "condicion_iva": "CF",
                    "telefono_1": "341-5099887"},
        "codigo": "T1", "vehiculo": "Renault Kangoo", "dominio": "AF208KL"})

    cta_gal = api.post("/bancos/cuentas", {"banco": "Banco Galicia", "tipo": "CC",
                                           "numero": "4092-7 118-3", "saldo_inicial": "3500000.00"})
    cta_nac = api.post("/bancos/cuentas", {"banco": "Banco Nación", "tipo": "CA",
                                           "numero": "231-009448-6", "saldo_inicial": "800000.00"})

    conc_gasto = api.post("/caja/conceptos", {"nombre": "Gastos varios", "tipo": "salida"})["id"]
    conc_retiro = api.post("/caja/conceptos", {"nombre": "Retiro a banco", "tipo": "salida"})["id"]

    # ================= 2) apertura contable 1/6 =================
    log("\n=== 2. asiento de apertura (1/6) ===")
    sug = api.get("/contabilidad/apertura/sugerencia")
    api.post("/contabilidad/apertura", {
        "fecha": J(1).isoformat(),
        "descripcion": "Apertura del ejercicio — Supermercado ZARIS",
        "lineas": [l for l in sug["lineas"] if l.get("cuenta_id")],
    })

    # ================= 3) bien de uso (1/6) =================
    cat_inst = next((c for c in cat_activos if "Instalaciones" in c["nombre"]), cat_activos[0])
    api.post("/contabilidad/activos", {
        "nombre": "Heladera exhibidora vertical 6 puertas", "categoria_id": cat_inst["id"],
        "fecha_alta": J(1).isoformat(), "valor_origen": "4800000.00",
        "valor_residual": "0", "vida_util_meses": 120})

    # ================= 4) compras (3/6 y 4/6) =================
    log("\n=== 4. compras de mercadería ===")
    def compra(prov, fecha, arts, nro):
        items = [{"articulo_id": a["id"], "cantidad": rng.randint(60, 180),
                  "costo_unitario": a["_costo"], "tasa_iva": a["_tasa"]} for a in arts]
        b = api.post("/compras/comprobantes", {
            "clase": "factura", "letra": "A", "punto_venta": 1, "numero": nro,
            "proveedor_id": prov["id"], "fecha": fecha.isoformat(), "contado": False,
            "deposito_id": dep, "actualiza_stock": True, "actualiza_costos": True,
            "items": items})
        api.post(f"/compras/comprobantes/{b['id']}/registrar")
        return api.get(f"/compras/comprobantes/{b['id']}")

    secos = [a for a in articulos if not a["_pesable"]]
    frescos = [a for a in articulos if a["_pesable"]]
    c1 = compra(proveedores[0], J(3), secos, 8811)                 # Distribuidora: secos
    c2 = compra(proveedores[1], J(4), frescos + secos[:6], 2304)   # Frigorífico: frescos
    resumen["compras"] = (c1["total"], c2["total"])
    log(f"compra 1 (Distribuidora): $ {c1['total']} — compra 2 (Frigorífico): $ {c2['total']}")

    # ================= 5) ventas de gestión (cta. cte., junio) =================
    log("\n=== 5. ventas de gestión ===")
    ventas_g = []

    def venta_gestion(cliente, fecha, n_items, contado=False, clase="factura", emitir=True):
        arts = rng.sample(secos, n_items)
        items = [{"articulo_id": a["id"], "cantidad": rng.randint(4, 24),
                  "precio_unitario": a["_precio"], "tasa_iva": a["_tasa"]} for a in arts]
        b = api.post("/ventas/comprobantes", {
            "clase": clase, "punto_venta_id": pv1, "cliente_id": cliente["id"],
            "fecha": fecha.isoformat(), "contado": contado, "precios_con_iva": True,
            "condicion_venta_id": None if contado else cond_cta,
            "deposito_id": dep, "actualiza_stock": clase != "presupuesto",
            "items": items})
        if not emitir:
            return b
        medios = {"medios": [{"medio": "efectivo", "importe": b["total"]}]} if (
            clase == "factura" and contado) else {}
        return api.post(f"/ventas/comprobantes/{b['id']}/emitir", medios)

    # presupuesto (5/6) que después se factura (8/6) al mismo cliente
    pre = venta_gestion(ri[0], J(5), 4, clase="presupuesto")
    fechas_v = [(ri[0], J(8)), (ri[1], J(10)), (clientes[2], J(11)), (ri[2], J(12)),
                (clientes[3], J(15)), (ri[3], J(18)), (clientes[8], J(22)),
                (ri[4], J(28))]  # la del 28/6 queda IMPAGA (morosidad)
    for cli, f in fechas_v:
        ventas_g.append(venta_gestion(cli, f, rng.randint(3, 6)))

    # NC comercial (20/6): la venta al Club (15/6) se anula entera con NC espejo
    # (la NC nace hoy — su fecha se corre al 20/6 en el retoque SQL final)
    nc = api.post(f"/ventas/comprobantes/{ventas_g[4]['id']}/nota-credito")
    nc = api.post(f"/ventas/comprobantes/{nc['id']}/emitir")
    nc_touchup = {"id": nc["id"], "dia": 20}

    # remitos para logística (24/6 y 25/6)
    rem1 = venta_gestion(ri[0], J(24), 3, clase="remito")
    rem2 = venta_gestion(ri[2], J(25), 4, clase="remito")
    resumen["ventas_gestion"] = len(ventas_g)

    # ================= 6) cobranzas (junio) =================
    log("\n=== 6. cobranzas ===")
    def recibo(cliente, fecha, medios, imputaciones=None, obs=None):
        return api.post("/cobranzas/recibos", {
            "punto_venta_id": pv1, "cliente_id": cliente["id"], "fecha": fecha.isoformat(),
            "medios": medios, "imputaciones": imputaciones or [], "observaciones": obs})

    v = ventas_g
    # 12/6: cobro total en efectivo de la venta del 8/6
    r1 = recibo(ri[0], J(12), [{"medio": "efectivo", "importe": v[0]["total"]}],
                [{"comprobante_id": v[0]["id"], "importe": v[0]["total"]}])
    # 16/6: cheque de tercero 30 días (se deposita en julio y ACREDITA)
    ch_ok_imp = v[3]["total"]
    r2 = recibo(ri[2], J(16), [{"medio": "cheque", "importe": ch_ok_imp,
                                "cheque": {"numero": "00451208", "banco": "Banco Santander",
                                           "fecha_pago": "2026-07-06"}}],
                [{"comprobante_id": v[3]["id"], "importe": ch_ok_imp}])
    # 18/6: cobro PARCIAL por transferencia de la venta del 12/6
    mitad = f"{Decimal(v[2]['total']) / 2:.2f}"
    r3 = recibo(clientes[2], J(18), [{"medio": "transferencia", "importe": mitad,
                                      "cuenta_bancaria_id": cta_gal["id"]}],
                [{"comprobante_id": v[2]["id"], "importe": mitad}])
    # 20/6: cheque de tercero que va a REBOTAR (deuda del Bar El Cruce, venta 18/6)
    ch_rechazo_imp = v[5]["total"]
    r4 = recibo(ri[3], J(20), [{"medio": "cheque", "importe": ch_rechazo_imp,
                                "cheque": {"numero": "00098x2", "banco": "Banco Macro",
                                           "fecha_pago": "2026-07-02"}}],
                [{"comprobante_id": v[5]["id"], "importe": ch_rechazo_imp}])
    # 24/6: cobro con retención sufrida de IVA (Hotel — agente de retención)
    r5_imp = v[1]["total"]
    r5 = recibo(ri[1], J(24), [{"medio": "transferencia", "importe": r5_imp,
                                "cuenta_bancaria_id": cta_gal["id"]}],
                [{"comprobante_id": v[1]["id"], "importe": r5_imp}])
    api.post("/libros/retenciones", {"tipo": "sufrida", "regimen": "IVA",
                                     "fecha": J(24).isoformat(), "importe": "18500.00",
                                     "cliente_id": ri[1]["id"], "recibo_id": r5["id"],
                                     "nro_certificado": "R-2026-004411"})
    # 27/6: pago A CUENTA (sin imputar) del Geriátrico + un cheque chico para endosar
    r6 = recibo(ri[4], J(27), [{"medio": "cheque", "importe": "250000.00",
                                "cheque": {"numero": "00777role", "banco": "Banco Credicoop",
                                           "fecha_pago": "2026-07-10"}}], [],
                obs="Pago a cuenta junio")
    resumen["recibos"] = 6

    # ================= 7) pagos a proveedores (junio) =================
    log("\n=== 7. órdenes de pago ===")
    op1 = api.post("/compras/pagos/ordenes-pago", {
        "proveedor_id": proveedores[0]["id"], "fecha": J(10).isoformat(),
        "sucursal_id": sucursal,
        "medios": [{"medio": "transferencia", "importe": c1["total"],
                    "cuenta_bancaria_id": cta_gal["id"]}],
        "imputaciones": [{"compra_id": c1["id"], "importe": c1["total"]}]})
    op2 = api.post("/compras/pagos/ordenes-pago", {
        "proveedor_id": proveedores[1]["id"], "fecha": J(17).isoformat(),
        "sucursal_id": sucursal,
        "medios": [{"medio": "cheque", "importe": c2["total"],
                    "cheque_propio": {"cuenta_id": cta_gal["id"], "numero": "10000001",
                                      "fecha_pago": "2026-07-17"}}],
        "imputaciones": [{"compra_id": c2["id"], "importe": c2["total"]}]})
    api.post("/libros/retenciones", {"tipo": "practicada", "regimen": "Ganancias",
                                     "fecha": J(17).isoformat(), "importe": "42300.00",
                                     "proveedor_id": proveedores[1]["id"],
                                     "orden_pago_id": op2["id"],
                                     "nro_certificado": "RP-2026-000087"})

    # ================= 8) gestión de cheques (julio, realista) =================
    log("\n=== 8. cartera de cheques ===")
    cheques = api.get("/cheques", clase="tercero")
    ch_ok = next(c for c in cheques if c["numero"] == "00451208")
    ch_mal = next(c for c in cheques if c["numero"] == "00098x2")
    ch_endoso = next(c for c in cheques if c["numero"] == "00777role")
    api.post(f"/cheques/{ch_ok['id']}/depositar", {"cuenta_id": cta_nac["id"]})
    api.post(f"/cheques/{ch_ok['id']}/acreditar")
    api.post(f"/cheques/{ch_mal['id']}/depositar", {"cuenta_id": cta_nac["id"]})
    rej = api.post(f"/cheques/{ch_mal['id']}/rechazar", {"detalle": "Sin fondos suficientes"})
    # endoso del cheque a cuenta al 3er proveedor (compra chica de julio NO — a cuenta)
    api.post("/compras/pagos/ordenes-pago", {
        "proveedor_id": proveedores[2]["id"],
        "medios": [{"medio": "cheque", "importe": "250000.00",
                    "endosar_cheque_id": ch_endoso["id"]}]})
    resumen["cheque_rechazado"] = ch_rechazo_imp

    # ================= 9) caja (junio) =================
    log("\n=== 9. caja: movimientos manuales ===")
    api.post("/caja/movimientos", {"fecha": J(5).isoformat(), "concepto_id": conc_gasto,
                                   "medio": "efectivo", "importe": "38500.00",
                                   "descripcion": "Librería y artículos de limpieza propios"})
    api.post("/caja/movimientos", {"fecha": J(20).isoformat(), "concepto_id": conc_retiro,
                                   "medio": "efectivo", "importe": "900000.00",
                                   "descripcion": "Depósito de efectivo en Banco Galicia"})
    api.post(f"/bancos/cuentas/{cta_gal['id']}/movimientos", {
        "tipo": "credito", "importe": "900000.00", "fecha": J(20).isoformat(),
        "descripcion": "Depósito efectivo caja"})

    # ================= 10) transferencia apareada + extracto (junio) =================
    log("=== 10. bancos: transferencia apareada + extracto conciliado ===")
    mov_out = api.post(f"/bancos/cuentas/{cta_gal['id']}/movimientos", {
        "tipo": "transferencia_out", "importe": "500000.00", "fecha": J(25).isoformat(),
        "descripcion": "Transferencia a Banco Nación"})
    mov_in = api.post(f"/bancos/cuentas/{cta_nac['id']}/movimientos", {
        "tipo": "transferencia_in", "importe": "500000.00", "fecha": J(25).isoformat(),
        "descripcion": "Transferencia desde Banco Galicia"})
    api.post(f"/bancos/movimientos/{mov_out['id']}/aparear", {"contrapartida_id": mov_in["id"]})
    dep20 = api.get(f"/bancos/cuentas/{cta_gal['id']}/movimientos", limit=100)
    dep20_id = next(m["id"] for m in dep20 if m["importe"] == "900000.00")
    api.post(f"/bancos/cuentas/{cta_gal['id']}/extracto/import", {
        "nombre_archivo": "galicia-junio.csv",
        "items": [
            {"fecha": J(20).isoformat(), "importe": "900000.00", "tipo": "credito",
             "match_movimiento_id": dep20_id, "accion": "conciliar"},
            {"fecha": J(30).isoformat(), "detalle": "Comisión mantenimiento cuenta",
             "importe": "-45000.00", "tipo": "debito", "accion": "crear"},
        ]})

    # ================= 11) POS: 50 tickets en 10 jornadas × 2 cajas =================
    log("\n=== 11. POS: 50 tickets de junio ===")
    vendibles = [a for a in articulos if not a["_pesable"]]
    pesables = [a for a in articulos if a["_pesable"]]
    MEDIOS = ["efectivo"] * 6 + ["tarjeta"] * 2 + ["transferencia", "mercadopago"]
    plan_tickets: list[tuple[int, int]] = []  # (dia, caja_idx)
    for i in range(50):
        # i%10 = jornada, (i//10)%2 = caja → las DOS cajas abren cada día
        plan_tickets.append((DIAS_POS[i % len(DIAS_POS)], (i // 10) % 2))
    plan_tickets.sort()

    tickets: list[dict] = []          # {id, dia, nc_id?}
    sesiones: list[dict] = []         # {id, dia, caja_idx}
    especiales = {7: "pesable_etiqueta", 15: "cliente_A", 23: "depto",
                  31: "envase", 38: "desc_linea", 44: "desc_venta"}
    anular_idx = {12, 40}

    idx = 0
    for dia in DIAS_POS:
        del_dia = [t for t in plan_tickets if t[0] == dia]
        for caja_idx, caja_id in ((0, caja1), (1, caja2)):
            n_caja = len([t for t in del_dia if t[1] == caja_idx])
            if n_caja == 0:
                continue
            ses = api.post("/pos/sesiones", {"caja_id": caja_id, "fondo_inicial": "50000"})
            sesiones.append({"id": ses["id"], "dia": dia, "caja_idx": caja_idx})
            for _ in range(n_caja):
                tipo = especiales.get(idx)
                cliente_id = None
                items = []
                if tipo == "pesable_etiqueta":
                    a = pesables[0]
                    ean = ean13_balanza("20", int(a["codigo_balanza"]), 1485)
                    hit = api.get("/pos/buscar", q=ean, caja_id=caja_id)[0]
                    items.append({"articulo_id": hit["articulo_id"],
                                  "cantidad": hit.get("cantidad") or "1.485"})
                elif tipo == "depto":
                    items.append({"articulo_id": depto_id, "cantidad": 1,
                                  "precio_unitario": "15300.00"})
                elif tipo == "envase":
                    cerveza = next(a for a in articulos if a["codigo"] == "CER103")
                    items.append({"articulo_id": cerveza["id"], "cantidad": 2})
                    items.append({"articulo_id": envase_id, "cantidad": 2})
                if tipo == "cliente_A":
                    cliente_id = ri[1]["id"]
                # completar hasta 3-10 artículos
                faltan = max(rng.randint(3, 10) - len(items), 1)
                for a in rng.sample(vendibles, faltan):
                    it = {"articulo_id": a["id"], "cantidad": rng.randint(1, 4)}
                    if tipo == "desc_linea" and len(items) == 0:
                        it["descuento_pct"] = "15"
                    items.append(it)
                body = {"sesion_id": ses["id"], "cliente_id": cliente_id, "items": items}
                if tipo == "desc_venta":
                    body["descuento_pct"] = "10"
                calc = api.post("/pos/ventas/calcular", {
                    "caja_id": caja_id, "cliente_id": cliente_id,
                    "descuento_pct": body.get("descuento_pct", "0"), "items": items})
                medio = rng.choice(MEDIOS)
                body["medios"] = [{"medio": medio, "importe": calc["total"]}]
                venta = api.post("/pos/ventas", body)
                t = {"id": venta["id"], "dia": dia}
                if idx in anular_idx:
                    ncv = api.post(f"/pos/ventas/{venta['id']}/anular", {
                        "sesion_id": ses["id"], "supervisor_email": EMAIL,
                        "supervisor_password": args.clave})
                    t["nc_id"] = ncv["id"]
                tickets.append(t)
                idx += 1
            # cierre de sesión con arqueo (una jornada con diferencia de -1500)
            resumen_ses = api.get(f"/pos/sesiones/{ses['id']}/resumen")
            contado = Decimal(resumen_ses["efectivo_teorico"])
            if dia == 13 and caja_idx == 0:
                contado -= Decimal("1500")
            api.post(f"/pos/sesiones/{ses['id']}/cerrar",
                     {"efectivo_contado": f"{contado:.2f}"})
    log(f"tickets emitidos: {len(tickets)} (2 anulados con supervisor)")
    resumen["tickets"] = len(tickets)

    # ================= 12) logística (estrena F12-bis) =================
    log("\n=== 12. logística: entregas + hoja de ruta + rendición ===")
    e1 = api.post("/logistica/entregas", {"comprobante_id": rem1["id"], "bultos": "6 cajas"})
    e2 = api.post("/logistica/entregas", {"comprobante_id": rem2["id"], "bultos": "9 cajas"})
    e3 = api.post("/logistica/entregas", {"comprobante_id": v[6]["id"], "bultos": "3 cajas"})
    hoja = api.post("/logistica/hojas", {
        "transportista_id": transportista["id"], "fecha": J(26).isoformat(),
        "observaciones": "Reparto semanal zona centro",
        "entrega_ids": [e1["id"], e2["id"], e3["id"]]})
    api.post(f"/logistica/hojas/{hoja['id']}/despachar")
    api.post(f"/logistica/entregas/{e1['id']}/rendir",
             {"resultado": "entregada", "recibido_por": "Portería del comedor"})
    api.post(f"/logistica/entregas/{e2['id']}/rendir",
             {"resultado": "entregada", "recibido_por": "V. Núñez (recepción)"})
    api.post(f"/logistica/entregas/{e3['id']}/rendir",
             {"resultado": "rechazada", "motivo_rechazo": "Local cerrado — reprogramar"})
    api.post(f"/logistica/hojas/{hoja['id']}/cerrar")
    api.post(f"/logistica/entregas/{e3['id']}/reprogramar")
    resumen["hoja_ruta"] = hoja["numero_formateado"]

    # ================= 13) RETOQUE SQL de fechas (POS + logística) =================
    log("\n=== 13. retoque SQL de fechas (POS + logística, acotado al tenant) ===")

    async def retoque():
        from sqlalchemy import text
        from app.core.db import SessionLocal

        async with SessionLocal() as db:
            for t in tickets + [nc_touchup]:
                f = J(t["dia"])
                ts = datetime(f.year, f.month, f.day, 11, 30, tzinfo=timezone.utc)
                ids = [t["id"]] + ([t["nc_id"]] if t.get("nc_id") else [])
                for cid in ids:
                    await db.execute(text(
                        "update comprobantes set fecha=:f, emitido_at=:ts, created_at=:ts, "
                        "updated_at=:ts where id=:id and tenant_id=:tid"),
                        {"f": f, "ts": ts, "id": cid, "tid": tenant_id})
                    await db.execute(text(
                        "update stock_movimientos set fecha=:f, created_at=:ts "
                        "where grupo_id=:id and tenant_id=:tid"),
                        {"f": f, "ts": ts, "id": cid, "tid": tenant_id})
                    await db.execute(text(
                        "update venta_medios set created_at=:ts "
                        "where comprobante_id=:id and tenant_id=:tid"),
                        {"ts": ts, "id": cid, "tid": tenant_id})
            for s in sesiones:
                f = J(s["dia"])
                ab = datetime(f.year, f.month, f.day, 8, 30, tzinfo=timezone.utc)
                ci = datetime(f.year, f.month, f.day, 20, 30, tzinfo=timezone.utc)
                await db.execute(text(
                    "update pos_sesiones set abierta_at=:ab, cerrada_at=:ci, created_at=:ab, "
                    "updated_at=:ci where id=:id and tenant_id=:tid"),
                    {"ab": ab, "ci": ci, "id": s["id"], "tid": tenant_id})
            f26 = datetime(2026, 6, 26, 9, 0, tzinfo=timezone.utc)
            await db.execute(text(
                "update entregas set created_at=:ts, updated_at=:ts, "
                "rendida_at=coalesce(rendida_at,null) where tenant_id=:tid"),
                {"ts": f26, "tid": tenant_id})
            await db.execute(text(
                "update entregas set rendida_at=:ts where tenant_id=:tid "
                "and rendida_at is not null"),
                {"ts": datetime(2026, 6, 26, 18, 30, tzinfo=timezone.utc), "tid": tenant_id})
            await db.execute(text(
                "update hojas_ruta set created_at=:ts, updated_at=:ts where tenant_id=:tid"),
                {"ts": f26, "tid": tenant_id})
            await db.commit()

    asyncio.run(retoque())
    log("fechas de POS/logística corridas a junio")

    # ================= 14) cierres de caja (con las fechas ya finales) =================
    log("\n=== 14. cierres de caja con arqueo ===")
    for d in (5, 13, 30):
        pl = api.get("/caja/planilla", fecha=J(d).isoformat())
        contado = Decimal(pl["saldo_final"])
        if d == 13:
            contado -= Decimal("1500")  # espejo de la diferencia de la Caja 1
        api.post("/caja/cierres", {"fecha": J(d).isoformat(),
                                   "efectivo_contado": f"{contado:.2f}"})

    # ================= 15) comisiones de junio =================
    log("=== 15. liquidación de comisiones ===")
    for vend in (vend1, vend2):
        try:
            api.post(f"/vendedores/{vend['id']}/liquidaciones",
                     {"desde": J(1).isoformat(), "hasta": J(30).isoformat(),
                      "observaciones": "Comisiones junio 2026"})
        except RuntimeError as e:
            log(f"  liquidación {vend['codigo']}: {e}")

    # ================= 16) contabilidad: regenerar + cerrar junio =================
    log("=== 16. contabilidad: regenerar + cerrar período junio ===")
    hoy = date.today()
    gen = api.post("/contabilidad/regenerar",
                   {"desde": J(1).isoformat(), "hasta": hoy.isoformat()})
    sys_ = api.get("/contabilidad/sumas-y-saldos",
                   desde=J(1).isoformat(), hasta=hoy.isoformat())
    balance = api.get("/contabilidad/balance", hasta=J(30).isoformat())
    api.post("/contabilidad/periodos/cerrar", {"periodo": "2026-06-01"})
    resumen["asientos"] = gen.get("generados") or gen
    resumen["balanceado"] = sys_["balanceado"]

    # ================= resumen final =================
    kpis = api.get("/dashboard/kpis")
    log("\n" + "=" * 64)
    log("PILOTO GENERADO — resumen para la narrativa")
    log("=" * 64)
    log(f"tenant: {RAZON} ({tenant_id})")
    log(f"login:  {EMAIL}")
    log(f"compras: 2 (totales $ {resumen['compras'][0]} / $ {resumen['compras'][1]})")
    log(f"ventas gestión: {resumen['ventas_gestion']} + presupuesto + 2 remitos + 1 NC")
    log(f"tickets POS: {resumen['tickets']} (2 anulados) en {len(sesiones)} sesiones")
    log(f"recibos: {resumen['recibos']} · cheque rechazado por $ {resumen['cheque_rechazado']}")
    log(f"hoja de ruta: {resumen['hoja_ruta']} (2 entregadas, 1 rechazada→reprogramada)")
    log(f"contabilidad: {resumen['asientos']} asientos · balanceado={resumen['balanceado']}")
    log(f"balance 30/6: ecuación verificada={balance.get('ecuacion_ok', balance.get('verificada'))}")
    log(f"KPIs dashboard hoy: {kpis}")
    if not resumen["balanceado"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
