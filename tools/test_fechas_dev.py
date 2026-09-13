r"""Suite GUARDA de la zona horaria de negocio (fix fechas UTC, 2026-09-13).

El bug: la nube (Vercel + Supabase) corre en UTC y `date.today()` fechaba
MAÑANA todo hecho de negocio posterior a las 21:00 hora argentina. El dev
(Postgres y Python en hora local) nunca lo mostró — por eso esta suite no
puede «reproducir» el bug contra el server: lo que hace es impedir que
vuelva a entrar y verificar que las piezas que lo cierran están vivas.
Cubre:
A. Guarda estática sobre el REPO: ningún `date.today()`, `datetime.utcnow()`,
   `datetime.now()` a secas ni `datetime.combine(..., timezone.utc)` en
   backend/app fuera de core/fechas.py (y el comentario de config.py); ningún
   `toISOString().slice(0, 10|7)` en web-app/src fuera de lib/fechas.ts; todo
   `server_default=func.current_date()` de los modelos viene acompañado de
   `default=hoy`.
B. Unidad de core/fechas.py (in-process): a_fecha_local en los bordes
   (23:30 UTC del 31/7 → 31/7; 01:00 UTC del 1/8 → 31/7; 03:00 UTC → 1/8;
   naive = UTC) y hoy() coherente con el instante UTC actual.
C. La base que usa el backend tiene la zona de la migración 028
   (`current_setting('TimeZone')` = TZ_APP) y `current_date` = hoy().
D. En vivo: un presupuesto y un movimiento bancario creados SIN fecha salen
   fechados con hoy() calculado del lado del cliente con la zona AR.
Uso (desde backend/, como toda suite in-process):
    cd backend
    $env:ENV_FILE=".env.local"; .venv\Scripts\python.exe ..\tools\test_fechas_dev.py \
        --base http://127.0.0.1:8021 --email demo@zaris.com.ar --clave "..."
"""
import argparse
import asyncio
import json
import re
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]


def check(nombre, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok  {nombre}")
    else:
        fail += 1
        print(f" FAIL {nombre}  {extra}")


def _req(method, base, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = U.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = U.urlopen(req, timeout=40)
        payload = r.read()
        return r.status, (json.loads(payload) if payload else None)
    except E.HTTPError as ex:
        payload = ex.read()
        try:
            return ex.code, json.loads(payload)
        except Exception:
            return ex.code, payload.decode(errors="replace")


def _grep(carpeta: Path, patron: str, exts: tuple[str, ...]) -> list[str]:
    rx = re.compile(patron)
    hits = []
    for p in carpeta.rglob("*"):
        if p.suffix not in exts or "__pycache__" in p.parts or "node_modules" in p.parts:
            continue
        try:
            for n, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if rx.search(linea):
                    hits.append(f"{p.relative_to(RAIZ)}:{n}: {linea.strip()[:90]}")
        except UnicodeDecodeError:
            continue
    return hits


def seccion_a_guarda_estatica():
    print("\n== A. Guarda estática sobre el repo ==")
    app_dir = RAIZ / "backend" / "app"
    permitidos_py = {"backend/app/core/fechas.py", "backend/app/core/config.py"}

    def _filtrar(hits):
        return [h for h in hits if h.split(":")[0].replace("\\", "/") not in permitidos_py]

    hits = _filtrar(_grep(app_dir, r"date\.today\(\)", (".py",)))
    check("backend sin date.today()", not hits, "\n      " + "\n      ".join(hits))

    hits = _filtrar(_grep(app_dir, r"datetime\.utcnow\(\)", (".py",)))
    check("backend sin datetime.utcnow()", not hits, "\n      " + "\n      ".join(hits))

    # datetime.now() SIN argumento = reloj naive del server (UTC en la nube).
    hits = _filtrar(_grep(app_dir, r"datetime\.now\(\s*\)", (".py",)))
    check("backend sin datetime.now() naive", not hits, "\n      " + "\n      ".join(hits))

    # Un rango de DÍAS armado con combine(..., timezone.utc) corta a las 21:00
    # AR (mordió en auditoria.py y en el sello del kardex backdateado).
    hits = _filtrar(_grep(app_dir, r"combine\([^)]*timezone\.utc", (".py",)))
    check("backend sin datetime.combine(..., timezone.utc)", not hits,
          "\n      " + "\n      ".join(hits))

    web = RAIZ / "web-app" / "src"
    # slice(0, 10) = «hoy», slice(0, 7) = «período actual» (libro IVA / CITI):
    # las dos variantes son la fecha UTC.
    hits = [
        h for h in _grep(web, r"toISOString\(\)\.slice\(0,\s*(7|10)\)", (".ts", ".tsx"))
        if not h.replace("\\", "/").startswith("web-app/src/lib/fechas.ts")
    ]
    check("front sin toISOString().slice(0, 7|10)", not hits, "\n      " + "\n      ".join(hits))

    # Todo server_default=current_date() lleva default=hoy (el ORM manda la fecha).
    faltan = []
    for p in (app_dir / "models").glob("*.py"):
        for n, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "func.current_date()" in linea and "default=hoy" not in linea:
                faltan.append(f"{p.name}:{n}")
    check("modelos: current_date() siempre con default=hoy", not faltan, str(faltan))


def seccion_b_unidad():
    print("\n== B. core/fechas.py (unidad) ==")
    from app.core.config import settings  # noqa: E402
    from app.core.fechas import ZONA, a_fecha_local, ahora, hoy  # noqa: E402

    check("TZ_APP es Argentina por default", settings.TZ_APP == "America/Argentina/Buenos_Aires",
          settings.TZ_APP)
    check("la zona resuelve (tzdata presente)", str(ZONA) == settings.TZ_APP, str(ZONA))

    utc = timezone.utc
    casos = [
        (datetime(2026, 7, 31, 23, 30, tzinfo=utc), date(2026, 7, 31), "23:30 UTC del 31/7 sigue siendo 31/7"),
        (datetime(2026, 8, 1, 1, 0, tzinfo=utc), date(2026, 7, 31), "01:00 UTC del 1/8 es 31/7 en AR"),
        (datetime(2026, 8, 1, 2, 59, tzinfo=utc), date(2026, 7, 31), "02:59 UTC del 1/8 es 31/7 en AR"),
        (datetime(2026, 8, 1, 3, 0, tzinfo=utc), date(2026, 8, 1), "03:00 UTC del 1/8 ya es 1/8 en AR"),
        (datetime(2026, 8, 1, 1, 0), date(2026, 7, 31), "naive se asume UTC"),
    ]
    for ts, esperado, nombre in casos:
        got = a_fecha_local(ts)
        check(f"a_fecha_local: {nombre}", got == esperado, f"{got} != {esperado}")
    check("a_fecha_local(None) es None", a_fecha_local(None) is None)

    ahora_utc = datetime.now(utc)
    check("hoy() coincide con la fecha AR del instante UTC actual",
          hoy() == a_fecha_local(ahora_utc), f"{hoy()} vs {a_fecha_local(ahora_utc)}")
    check("ahora() es aware en la zona de negocio",
          ahora().tzinfo is not None and ahora().utcoffset() == timedelta(hours=-3),
          str(ahora()))


def seccion_c_db():
    print("\n== C. Zona de la base (migración 028) ==")
    from sqlalchemy import text

    from app.core.config import settings  # noqa: E402
    from app.core.db import SessionLocal  # noqa: E402
    from app.core.fechas import hoy  # noqa: E402

    async def _q():
        async with SessionLocal() as db:
            tz = await db.scalar(text("select current_setting('TimeZone')"))
            cd = await db.scalar(text("select current_date"))
            return tz, cd

    tz, cd = asyncio.run(_q())
    check("current_setting('TimeZone') = TZ_APP (028 aplicada)", tz == settings.TZ_APP, str(tz))
    check("current_date de la DB = hoy() del backend", cd == hoy(), f"{cd} vs {hoy()}")


def seccion_d_vivo(base: str, email: str, clave: str):
    print("\n== D. Documentos sin fecha salen con hoy() ==")
    from app.core.fechas import hoy  # noqa: E402

    st, r = _req("POST", base, "/auth/login", body={"email": email, "password": clave})
    check("login", st == 200, f"{st} {r}")
    if st != 200:
        return
    tok = r["access_token"]
    hoy_ar = hoy().isoformat()

    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    pv_id = pvs[0]["id"]
    st, arts = _req("GET", base, "/articulos?limit=1", tok)
    art_id = arts[0]["id"] if isinstance(arts, list) and arts else None
    check("setup: artículo disponible", art_id is not None, str(arts)[:120])
    if not art_id:
        return

    st, pre = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "presupuesto", "punto_venta_id": pv_id, "contado": True,
        "precios_con_iva": True,
        "items": [{"articulo_id": art_id, "cantidad": "1", "precio_unitario": "10.00",
                   "tasa_iva": "21"}],
        "observaciones": f"test_fechas {SUF}",
    })
    check("presupuesto sin fecha -> 201", st == 201, f"{st} {pre}")
    if st == 201:
        check("presupuesto.fecha = hoy() (zona AR)", pre.get("fecha") == hoy_ar,
              f"{pre.get('fecha')} vs {hoy_ar}")

    st, cta = _req("POST", base, "/bancos/cuentas", tok, {
        "banco": f"Banco fechas {SUF}", "tipo": "CC", "numero": f"tz-{SUF}",
        "moneda": "ARS", "saldo_inicial": "0.00",
    })
    check("setup cuenta bancaria", st == 201, f"{st} {cta}")
    if st == 201:
        st, mov = _req("POST", base, f"/bancos/cuentas/{cta['id']}/movimientos", tok, {
            "tipo": "credito", "importe": "1.00",
            "descripcion": f"test_fechas {SUF}",
        })
        check("movimiento bancario sin fecha -> 201", st == 201, f"{st} {mov}")
        if st == 201:
            check("movimiento.fecha = hoy() (zona AR)", mov.get("fecha") == hoy_ar,
                  f"{mov.get('fecha')} vs {hoy_ar}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    base = args.base.rstrip("/") + "/api/v1"

    seccion_a_guarda_estatica()
    seccion_b_unidad()
    seccion_c_db()
    seccion_d_vivo(base, args.email, args.clave)

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
