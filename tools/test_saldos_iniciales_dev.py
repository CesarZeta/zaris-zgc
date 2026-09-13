"""Suite en vivo de SALDO INICIAL DE CUENTA CORRIENTE (migración 029,
docs/DISENO-CONTABILIDAD.md §7) contra DEV.

Cubre el documento interno `saldo_inicial` en los dos circuitos:
- Ventas: SAL (deudor, +1) / SAF (a favor, −1) por `POST /ventas/saldos-iniciales`
  — nace emitido, sin ítems, total = saldo = importe, letra X, UN vencimiento
  a la fecha (SAL) / ninguno (SAF); entra a cta. cte. (detalle, saldos,
  vencido), se imputa con recibo, se lista por clase, y NO entra a PDF/email
  (409), libro IVA ni contabilidad derivada; la sugerencia de apertura lo suma.
- Compras: SALP (le debemos, +1) / SAFP (nos deben, −1) por
  `POST /compras/saldos-iniciales` — nace registrado con punto_venta 0,
  entra a cta. cte. del proveedor, saldos y vencimientos a pagar, se imputa
  con OP, no entra al libro IVA compras ni a la derivación contable.
- Anulación por los endpoints existentes: 409 con imputaciones vivas; anular
  el recibo/OP libera; el saldo de cta. cte. vuelve a 0 al anular todo.
- RBAC: un usuario con el rol sembrado «consulta» recibe 403 (nunca 401).

Todo recurso nombrado lleva el sufijo único de la corrida. Los agregados
COMPARTIDOS del tenant (sugerencia de apertura, cantidad de asientos
derivados) se asertan por DELTA; la presencia/ausencia de un documento en un
agregado se busca con su filtro específico o recorriendo TODAS las páginas,
nunca mirando una sola (regla CLAUDE.md §6). El cliente y el proveedor son
nuevos por corrida, así que sus saldos de cta. cte. sí se asertan absolutos.

El saldo deudor se fecha AYER (no hoy) a propósito: así el vencimiento queda
estrictamente en el pasado y «vencido» no depende de si el lector compara
con `<` o `<=` contra hoy.

SAF como CRÉDITO FUENTE (B-bis): se imputa a una factura cta. cte. por
`/cobranzas/imputaciones` (credito_id) y al anularse REVIERTE la imputación
(la factura recupera el saldo) — no existe desimputación y la factura destino
es fiscal, así que la anulación es la única salida (revisión 029). La factura
se deja en cero con la NC espejo (TOTAL) emitida.

Uso:
    python tools/test_saldos_iniciales_dev.py --base http://127.0.0.1:8021 \
        --email demo@zaris.com.ar --clave "..."
"""

import argparse
import json
import sys
import urllib.error as E
import urllib.request as U
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ok = 0
fail = 0
SUF = uuid.uuid4().hex[:6]
NUM6 = f"{int(SUF, 16) % 1_000_000:06d}"
# misma zona de negocio que el backend (core/fechas.py): la suite no depende
# del reloj UTC del server ni del de la máquina que la corre
ZONA_AR = ZoneInfo("America/Argentina/Buenos_Aires")


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


def _todos(base, path, tok, limit=200):
    """Recorre TODAS las páginas de un listado (para asertar AUSENCIA sin
    depender de que el registro caiga en la primera página)."""
    sep = "&" if "?" in path else "?"
    filas, offset = [], 0
    while True:
        st, pagina = _req("GET", base, f"{path}{sep}limit={limit}&offset={offset}", tok)
        if st != 200 or not isinstance(pagina, list):
            return st, filas
        filas.extend(pagina)
        if len(pagina) < limit:
            return 200, filas
        offset += limit


def _mov(cc, numero, tipo=None):
    """Movimiento de una cta. cte. por número formateado y, si se pasa, por la
    descripción del tipo. OJO: cada tipo numera aparte (como FA vs NCA), así que
    SAL y SAF de un mismo PV pueden ser los dos 0001-00000001 — el número solo
    no identifica (mordió en la primera corrida)."""
    return next(
        (
            m
            for m in (cc or {}).get("movimientos", [])
            if m.get("numero") == numero and (tipo is None or m.get("tipo") == tipo)
        ),
        {},
    )


def _linea_apertura(base, tok, detalle):
    """Debe − haber de una línea de la sugerencia de apertura (0 si no está)."""
    st, sug = _req("GET", base, "/contabilidad/apertura/sugerencia", tok)
    if st != 200:
        return None
    for ln in sug.get("lineas", []):
        if ln.get("detalle") == detalle:
            return D(ln["debe"]) - D(ln["haber"])
    return Decimal("0")


def _regenerar(base, tok, desde, hasta):
    """Cantidad de asientos derivados del rango (None si la contabilidad no
    pudo regenerar: período cerrado u otro error — se informa)."""
    st, r = _req("POST", base, "/contabilidad/regenerar", tok,
                 {"desde": desde, "hasta": hasta})
    if st != 200:
        print(f"      (regenerar {desde}..{hasta} -> {st} {r})")
        return None
    return int(r.get("asientos", 0))


def _asientos_con(base, tok, fecha, origen, prefijo):
    """Asientos derivados de `origen` en `fecha` cuya descripción arranca con
    `prefijo` — recorriendo todas las páginas."""
    st, filas = _todos(base, f"/contabilidad/asientos?desde={fecha}&hasta={fecha}&origen={origen}", tok)
    return st, [a for a in filas if (a.get("descripcion") or "").startswith(prefijo)]


def _en_libro(base, tok, ruta, periodos, doc_id):
    """True si el documento figura en alguno de los períodos del libro."""
    for per in periodos:
        st, libro = _req("GET", base, f"/libros/{ruta}?periodo={per}", tok)
        if st != 200:
            return None
        if any(f.get("id") == doc_id for f in libro.get("filas", [])):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8021")
    ap.add_argument("--email", required=True)
    ap.add_argument("--clave", required=True)
    args = ap.parse_args()
    raiz = args.base.rstrip("/")
    base = raiz + "/api/v1"

    st, r = _req("POST", base, "/auth/login", body={"email": args.email, "password": args.clave})
    if st != 200:
        print("login FAIL", st, r)
        sys.exit(1)
    tok = r["access_token"]
    print(f"login OK — sufijo de corrida {SUF}")

    hoy = datetime.now(ZONA_AR).date()
    ayer = (hoy - timedelta(days=1)).isoformat()
    manana = (hoy + timedelta(days=1)).isoformat()
    hoy_s = hoy.isoformat()
    periodos = sorted({ayer[:7], hoy_s[:7]})

    # ===== 0. Probe: el backend que responde tiene las rutas nuevas =====
    # (el openapi es público; un backend viejo hace fallar TODO lo que sigue)
    st, oa = _req("GET", raiz, "/openapi.json")
    paths = (oa or {}).get("paths", {}) if isinstance(oa, dict) else {}
    check("openapi expone /ventas/saldos-iniciales y /compras/saldos-iniciales",
          "/api/v1/ventas/saldos-iniciales" in paths
          and "/api/v1/compras/saldos-iniciales" in paths,
          f"{st} — ¿backend viejo sin reiniciar?")

    # ===== A. Setup: cliente, cliente bloqueado, proveedor, PV, condición =====
    print("--- A. setup")
    st, cli = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente SI {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": NUM6, "condicion_iva": "CF"},
    })
    check("setup cliente", st in (200, 201), f"{st} {cli}")
    cli_id = cli["id"]
    cli_nombre = cli["entidad"]["razon_social"]

    st, clib = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente SI bloqueado {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": f"{(int(NUM6) + 1) % 1_000_000:06d}",
                    "condicion_iva": "CF"},
        "bloqueado": True,
    })
    check("setup cliente bloqueado", st in (200, 201) and clib.get("bloqueado") is True,
          f"{st} {clib}")
    clib_id = clib.get("id")

    st, prov = _req("POST", base, "/proveedores", tok, {
        "entidad": {"razon_social": f"Proveedor SI {SUF}", "tipo_persona": "J",
                    "tipo_documento": "CUIT", "nro_documento": _cuit_valido("30" + NUM6 + "29"),
                    "condicion_iva": "RI"},
    })
    check("setup proveedor", st in (200, 201), f"{st} {prov}")
    prov_id = prov["id"]

    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    check("setup punto de venta disponible", st == 200 and len(pvs) > 0, f"{st} {pvs}")
    pv_id = pvs[0]["id"]
    st, conds = _req("GET", base, "/ventas/condiciones-venta", tok)
    check("setup condición de venta disponible", st == 200 and len(conds) > 0, f"{st}")

    # ===== B. Ventas: SAL / SAF =====
    print("--- B. ventas")

    # agregados compartidos ANTES (deltas): sugerencia de apertura y asientos
    sug0 = _linea_apertura(base, tok, "Saldos de clientes")
    check("apertura/sugerencia base", sug0 is not None, "GET sugerencia falló")
    n0 = _regenerar(base, tok, ayer, hoy_s)

    st, sal = _req("POST", base, "/ventas/saldos-iniciales", tok, {
        "cliente_id": cli_id, "importe": "1000.00", "sentido": "deudor",
        "fecha": ayer, "observaciones": f"SAL suite {SUF}",
    })
    check("POST saldo inicial deudor -> 201", st == 201, f"{st} {sal}")
    if st != 201:
        print("sin SAL no se puede seguir")
        print(f"\n===== {ok} ok / {fail} fail =====")
        sys.exit(1)
    sal_id = sal["id"]
    sal_num = sal.get("numero_formateado")
    check("SAL: tipo_codigo SAL / clase saldo_inicial / letra X",
          sal.get("tipo_codigo") == "SAL" and sal.get("clase") == "saldo_inicial"
          and sal.get("letra") == "X",
          f"{sal.get('tipo_codigo')} {sal.get('clase')} {sal.get('letra')}")
    check("SAL: estado emitido (no hay borrador)", sal.get("estado") == "emitido", sal.get("estado"))
    check("SAL: total = saldo = 1000.00 y neto/iva 0",
          D(sal.get("total", 0)) == D("1000") and D(sal.get("saldo", 0)) == D("1000")
          and D(sal.get("neto_gravado", 0)) == 0 and D(sal.get("iva", 0)) == 0,
          f"total={sal.get('total')} saldo={sal.get('saldo')} neto={sal.get('neto_gravado')} iva={sal.get('iva')}")
    check("SAL: numerado (numero y numero_formateado no nulos)",
          sal.get("numero") is not None and sal_num, f"{sal.get('numero')} {sal_num}")
    check("SAL: fecha = la pedida (ayer)", sal.get("fecha") == ayer, sal.get("fecha"))
    check("SAL: sin ítems ni alícuotas", sal.get("items") == [] and sal.get("alicuotas") == [],
          f"{len(sal.get('items') or [])} items / {len(sal.get('alicuotas') or [])} alíc.")
    vtos = sal.get("vencimientos") or []
    check("SAL: UN vencimiento a la fecha del documento por el total",
          len(vtos) == 1 and vtos[0].get("fecha_vto") == ayer and D(vtos[0].get("importe", 0)) == D("1000"),
          str(vtos))
    check("SAL: snapshot del receptor (BUE)", sal.get("cliente_id") == cli_id
          and sal.get("receptor_nombre") == cli_nombre and sal.get("receptor_condicion_iva") == "CF",
          f"{sal.get('receptor_nombre')} {sal.get('receptor_condicion_iva')}")
    check("SAL: sin CAE ni resultado ARCA", not sal.get("cae") and not sal.get("arca_resultado"),
          f"cae={sal.get('cae')} arca={sal.get('arca_resultado')}")

    # validaciones
    st, r = _req("POST", base, "/ventas/saldos-iniciales", tok,
                 {"cliente_id": cli_id, "importe": "0", "sentido": "deudor"})
    check("importe 0 -> 422", st == 422, f"{st} {r}")
    st, r = _req("POST", base, "/ventas/saldos-iniciales", tok,
                 {"cliente_id": cli_id, "importe": "-5", "sentido": "deudor"})
    check("importe negativo -> 422", st == 422, f"{st} {r}")
    st, r = _req("POST", base, "/ventas/saldos-iniciales", tok,
                 {"cliente_id": cli_id, "importe": "10", "sentido": "debemos"})
    check("sentido inválido (el de compras) -> 422", st == 422, f"{st} {r}")
    st, r = _req("POST", base, "/ventas/saldos-iniciales", tok,
                 {"cliente_id": cli_id, "importe": "10", "sentido": "deudor", "fecha": manana})
    check("fecha futura -> 422", st == 422, f"{st} {r}")
    st, r = _req("POST", base, "/ventas/saldos-iniciales", tok,
                 {"cliente_id": str(uuid.uuid4()), "importe": "10", "sentido": "deudor"})
    check("cliente inexistente -> 404", st == 404, f"{st} {r}")
    if clib_id:
        st, r = _req("POST", base, "/ventas/saldos-iniciales", tok,
                     {"cliente_id": clib_id, "importe": "10", "sentido": "deudor"})
        check("cliente bloqueado -> 409", st == 409, f"{st} {r}")
    # body válido para ComprobanteIn: así el request llega a la guarda de estado
    # (con un body incompleto el 422 de validación taparía el 409)
    st, r = _req("PUT", base, f"/ventas/comprobantes/{sal_id}", tok, {
        "clase": "presupuesto", "punto_venta_id": pv_id, "contado": True,
        "items": [{"descripcion": "no debería poder", "cantidad": "1", "precio_unitario": "1"}],
    })
    check("PUT sobre un saldo inicial emitido -> 409 (inmutable)", st == 409, f"{st} {r}")

    # cta. cte. del cliente (nuevo por corrida: absolutos válidos)
    st, cc = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok)
    m = _mov(cc, sal_num, "Saldo inicial deudor")
    check("cta. cte.: el SAL aparece con debe 1000 y pendiente 1000",
          st == 200 and D(m.get("debe", 0)) == D("1000") and D(m.get("haber", 1)) == 0
          and D(m.get("pendiente", 0)) == D("1000"), f"{st} {m}")
    check("cta. cte.: tipo «Saldo inicial deudor»", m.get("tipo") == "Saldo inicial deudor", m.get("tipo"))
    check("cta. cte.: saldo del cliente = 1000", st == 200 and D(cc.get("saldo", 0)) == D("1000"),
          str((cc or {}).get("saldo")))

    st, saldos = _req("GET", base, "/cobranzas/saldos", tok)
    fila = next((x for x in (saldos or []) if x.get("cliente_id") == cli_id), {})
    check("saldos por cliente: figura con saldo 1000", st == 200 and D(fila.get("saldo", 0)) == D("1000"),
          f"{st} {fila}")
    check("saldos por cliente: vencido 1000 (vencimiento en el pasado)",
          D(fila.get("vencido", 0)) == D("1000"), str(fila.get("vencido")))

    # documento NO fiscal: PDF / email 409, libro IVA no lo lista
    st, r = _req("GET", base, f"/ventas/comprobantes/{sal_id}/pdf", tok)
    check("PDF de un saldo inicial -> 409 (no imprimible)", st == 409, f"{st} {str(r)[:120]}")
    st, r = _req("POST", base, f"/ventas/comprobantes/{sal_id}/enviar", tok,
                 {"email": f"si-{SUF}@zgc.dev"})
    check("email de un saldo inicial -> 409", st == 409, f"{st} {r}")
    en_libro = _en_libro(base, tok, "iva-ventas", periodos, sal_id)
    check("libro IVA ventas: el SAL NO figura", en_libro is False, f"{en_libro} (None = GET falló)")

    # contabilidad derivada: ningún asiento del SAL; apertura lo suma
    n1 = _regenerar(base, tok, ayer, hoy_s)
    if n0 is None or n1 is None:
        print("      SKIP delta de asientos derivados (regenerar no disponible: ¿período cerrado?)")
    else:
        check("regenerar: la cantidad de asientos derivados no cambió con el SAL", n1 == n0,
              f"{n0} -> {n1}")
    st, hits = _asientos_con(base, tok, ayer, "venta", f"SAL {sal_num}")
    check("asientos origen=venta del día: ninguno del SAL (todas las páginas)",
          st == 200 and hits == [], f"{st} {hits}")
    sug1 = _linea_apertura(base, tok, "Saldos de clientes")
    check("apertura/sugerencia: «Saldos de clientes» subió exactamente 1000",
          sug0 is not None and sug1 is not None and sug1 - sug0 == D("1000"),
          f"{sug0} -> {sug1}")

    # recibo efectivo 400 imputado al SAL
    st, rec = _req("POST", base, "/cobranzas/recibos", tok, {
        "punto_venta_id": pv_id, "cliente_id": cli_id,
        "medios": [{"medio": "efectivo", "importe": "400.00"}],
        "imputaciones": [{"comprobante_id": sal_id, "importe": "400.00"}],
        "observaciones": f"recibo SI {SUF}",
    })
    check("recibo 400 imputado al SAL -> 201 aplicado 400",
          st == 201 and D(rec.get("aplicado", 0)) == D("400"), f"{st} {rec}")
    rec_id = rec.get("id")
    st, det = _req("GET", base, f"/ventas/comprobantes/{sal_id}", tok)
    check("SAL: saldo 600 tras el recibo", st == 200 and D(det.get("saldo", 0)) == D("600"),
          f"{st} {det.get('saldo')}")
    st, cc = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok)
    check("cta. cte.: saldo 600", st == 200 and D(cc.get("saldo", 0)) == D("600"), str(cc.get("saldo")))

    # SAF a favor 200
    st, saf = _req("POST", base, "/ventas/saldos-iniciales", tok, {
        "cliente_id": cli_id, "importe": "200.00", "sentido": "a_favor",
        "observaciones": f"SAF suite {SUF}",
    })
    check("POST saldo inicial a favor -> 201 SAF emitido",
          st == 201 and saf.get("tipo_codigo") == "SAF" and saf.get("clase") == "saldo_inicial"
          and saf.get("estado") == "emitido" and saf.get("letra") == "X", f"{st} {saf}")
    saf_id = saf.get("id")
    saf_num = saf.get("numero_formateado")
    check("SAF: total = saldo = 200, sin vencimientos, fecha hoy por default",
          D(saf.get("total", 0)) == D("200") and D(saf.get("saldo", 0)) == D("200")
          and (saf.get("vencimientos") or []) == [] and saf.get("fecha") == hoy_s,
          f"{saf.get('total')} {saf.get('saldo')} {saf.get('vencimientos')} {saf.get('fecha')}")
    check("SAF: numerado", saf.get("numero") is not None and saf_num, f"{saf.get('numero')} {saf_num}")
    st, cc = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok)
    m = _mov(cc, saf_num, "Saldo inicial a favor")
    check("cta. cte.: el SAF aparece como haber 200",
          st == 200 and D(m.get("haber", 0)) == D("200") and D(m.get("debe", 1)) == 0
          and m.get("tipo") == "Saldo inicial a favor", f"{st} {m}")
    check("cta. cte.: saldo 400 (600 − 200 a favor)", D(cc.get("saldo", 0)) == D("400"),
          str(cc.get("saldo")))
    st, saldos = _req("GET", base, "/cobranzas/saldos", tok)
    fila = next((x for x in (saldos or []) if x.get("cliente_id") == cli_id), {})
    check("saldos por cliente: 400", st == 200 and D(fila.get("saldo", 0)) == D("400"), f"{fila}")

    # listado por clase (filtro específico: clase + cliente)
    st, lista = _req("GET", base, f"/ventas/comprobantes?clase=saldo_inicial&cliente_id={cli_id}&limit=50", tok)
    ids_lista = {x["id"] for x in (lista or [])} if st == 200 else set()
    check("listado ?clase=saldo_inicial&cliente_id lista el SAL y el SAF",
          st == 200 and ids_lista == {sal_id, saf_id},
          f"{st} {[(x.get('tipo_codigo'), x.get('estado')) for x in (lista or [])]}")
    st, lista = _req("GET", base, f"/ventas/comprobantes?clase=factura&cliente_id={cli_id}&limit=50", tok)
    check("listado ?clase=factura del cliente no los mezcla", st == 200 and lista == [], f"{st} {lista}")
    en_libro = _en_libro(base, tok, "iva-ventas", periodos, saf_id)
    check("libro IVA ventas: el SAF NO figura", en_libro is False, f"{en_libro}")

    # anulación: 409 con imputación viva; anular recibo libera; anular SAL/SAF
    st, r = _req("POST", base, f"/ventas/comprobantes/{sal_id}/anular", tok)
    check("anular SAL con imputación viva -> 409", st == 409, f"{st} {r}")
    st, r = _req("POST", base, f"/cobranzas/recibos/{rec_id}/anular", tok)
    check("anular el recibo -> 200", st == 200 and r.get("estado") == "anulado", f"{st} {r}")
    st, det = _req("GET", base, f"/ventas/comprobantes/{sal_id}", tok)
    check("SAL: saldo restaurado a 1000", st == 200 and D(det.get("saldo", 0)) == D("1000"),
          str(det.get("saldo")))
    st, r = _req("POST", base, f"/ventas/comprobantes/{sal_id}/anular", tok)
    check("anular SAL sin imputaciones vivas -> 200 estado anulado",
          st == 200 and r.get("estado") == "anulado", f"{st} {r}")
    st, cc = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok)
    check("cta. cte.: saldo −200 (solo queda el SAF a favor)",
          st == 200 and D(cc.get("saldo", 0)) == D("-200"), str(cc.get("saldo")))
    check("cta. cte.: el SAL anulado ya no figura en los movimientos", _mov(cc, sal_num, "Saldo inicial deudor") == {},
          str(_mov(cc, sal_num, "Saldo inicial deudor")))
    st, saldos = _req("GET", base, "/cobranzas/saldos?solo_deudores=false", tok)
    fila = next((x for x in (saldos or []) if x.get("cliente_id") == cli_id), {})
    check("saldos (todos): el cliente figura con −200", st == 200 and D(fila.get("saldo", 0)) == D("-200"),
          f"{fila}")
    st, r = _req("POST", base, f"/ventas/comprobantes/{sal_id}/anular", tok)
    check("re-anular el SAL -> 409", st == 409, f"{st} {r}")
    st, r = _req("POST", base, f"/ventas/comprobantes/{saf_id}/anular", tok)
    check("anular SAF -> 200 estado anulado", st == 200 and r.get("estado") == "anulado", f"{st} {r}")
    st, cc = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok)
    check("cta. cte.: saldo 0 con todo anulado", st == 200 and D(cc.get("saldo", 1)) == 0,
          str(cc.get("saldo")))
    st, saldos = _req("GET", base, "/cobranzas/saldos?solo_deudores=false", tok)
    check("saldos: el cliente ya no figura", st == 200
          and not any(x.get("cliente_id") == cli_id for x in (saldos or [])), "")
    st, lista = _req("GET", base,
                     f"/ventas/comprobantes?clase=saldo_inicial&cliente_id={cli_id}&estado=anulado&limit=50", tok)
    check("listado: los dos saldos iniciales quedaron anulados",
          st == 200 and {x["id"] for x in (lista or [])} == {sal_id, saf_id}, f"{st}")
    sug2 = _linea_apertura(base, tok, "Saldos de clientes")
    check("apertura/sugerencia: volvió al valor base (delta 0)",
          sug0 is not None and sug2 is not None and sug2 == sug0, f"{sug0} -> {sug2}")

    # ===== B-bis. SAF como CRÉDITO FUENTE: imputar a una factura y anular =====
    # (revisión 029: sin endpoint de desimputación, la anulación del SAF tiene
    # que revertir sola sus imputaciones — como la NC de compra — o queda
    # inanulable para siempre)
    print("--- B-bis. SAF como crédito fuente")
    cond_id = conds[0]["id"]
    st, fb = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli_id,
        "contado": False, "condicion_venta_id": cond_id, "precios_con_iva": True,
        "items": [{"descripcion": f"Ítem SI {SUF}", "cantidad": "1",
                   "precio_unitario": "500.00", "tasa_iva": "21"}],
    })
    check("factura cta. cte. borrador -> 201", st == 201, f"{st} {fb}")
    st, fcc = _req("POST", base, f"/ventas/comprobantes/{fb['id']}/emitir", tok, {})
    check("factura cta. cte. emitida con saldo = total",
          st == 200 and D(fcc.get("saldo", 0)) == D(fcc.get("total", -1)) == D("500"),
          f"{st} {fcc.get('saldo')} {fcc.get('total')}")
    fcc_id = fcc["id"]
    st, saf2 = _req("POST", base, "/ventas/saldos-iniciales", tok, {
        "cliente_id": cli_id, "importe": "150.00", "sentido": "a_favor",
        "observaciones": f"SAF crédito {SUF}",
    })
    check("SAF 150 -> 201", st == 201, f"{st} {saf2}")
    saf2_id = saf2["id"]
    st, imp = _req("POST", base, "/cobranzas/imputaciones", tok,
                   {"credito_id": saf2_id, "comprobante_id": fcc_id, "importe": "150.00"})
    check("imputar el SAF a la factura -> 201 (mismo camino que una NC)", st == 201, f"{st} {imp}")
    st, fcc2 = _req("GET", base, f"/ventas/comprobantes/{fcc_id}", tok)
    check("factura: saldo 350 tras imputar el SAF", st == 200 and D(fcc2.get("saldo", 0)) == D("350"),
          f"{st} {fcc2.get('saldo')}")
    st, saf2b = _req("GET", base, f"/ventas/comprobantes/{saf2_id}", tok)
    check("SAF: saldo 0 (consumido como crédito)", st == 200 and D(saf2b.get("saldo", 1)) == 0,
          f"{st} {saf2b.get('saldo')}")
    st, cc = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok)
    check("cta. cte.: saldo 350", st == 200 and D(cc.get("saldo", 0)) == D("350"), str(cc.get("saldo")))
    st, r = _req("POST", base, f"/ventas/comprobantes/{saf2_id}/anular", tok, {})
    check("anular el SAF usado como crédito -> 200 (revierte la imputación)",
          st == 200 and r.get("estado") == "anulado", f"{st} {r}")
    st, fcc3 = _req("GET", base, f"/ventas/comprobantes/{fcc_id}", tok)
    check("factura: saldo restaurado a 500", st == 200 and D(fcc3.get("saldo", 0)) == D("500"),
          f"{st} {fcc3.get('saldo')}")
    st, cc = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok)
    check("cta. cte.: saldo 500 (imputación revertida, SAF fuera)",
          st == 200 and D(cc.get("saldo", 0)) == D("500")
          and _mov(cc, saf2.get("numero_formateado"), "Saldo inicial a favor") == {},
          str(cc.get("saldo")))
    # dejar al cliente en cero: NC espejo (TOTAL, nace borrador -> emitir)
    st, nc = _req("POST", base, f"/ventas/comprobantes/{fcc_id}/nota-credito", tok, {})
    check("NC espejo borrador -> 200/201", st in (200, 201), f"{st} {nc}")
    if st in (200, 201):
        st, ncE = _req("POST", base, f"/ventas/comprobantes/{nc['id']}/emitir", tok, {})
        check("NC espejo emitida -> factura saldo 0", st == 200, f"{st} {ncE}")
        st, fcc4 = _req("GET", base, f"/ventas/comprobantes/{fcc_id}", tok)
        check("factura: saldo 0 tras la NC espejo", st == 200 and D(fcc4.get("saldo", 1)) == 0,
              f"{st} {fcc4.get('saldo')}")

    # ===== C. Compras: SALP / SAFP =====
    print("--- C. compras")
    sp0 = _linea_apertura(base, tok, "Saldos de proveedores")
    m0 = _regenerar(base, tok, ayer, hoy_s)
    st, salp = _req("POST", base, "/compras/saldos-iniciales", tok, {
        "proveedor_id": prov_id, "importe": "500.00", "sentido": "debemos",
        "fecha": ayer, "observaciones": f"SALP suite {SUF}",
    })
    check("POST saldo inicial a pagar -> 201", st == 201, f"{st} {salp}")
    if st != 201:
        print("sin SALP se saltea el resto de compras")
        salp = {}
    salp_id = salp.get("id")
    salp_num = salp.get("numero_formateado")
    if salp_id:
        check("SALP: tipo SALP / clase saldo_inicial / letra X / registrado",
              salp.get("tipo_codigo") == "SALP" and salp.get("clase") == "saldo_inicial"
              and salp.get("letra") == "X" and salp.get("estado") == "registrado",
              f"{salp.get('tipo_codigo')} {salp.get('clase')} {salp.get('letra')} {salp.get('estado')}")
        check("SALP: total = saldo = 500, neto/iva 0, sin ítems",
              D(salp.get("total", 0)) == D("500") and D(salp.get("saldo", 0)) == D("500")
              and D(salp.get("neto_gravado", 0)) == 0 and D(salp.get("iva", 0)) == 0
              and salp.get("items") == [],
              f"{salp.get('total')} {salp.get('saldo')} {salp.get('neto_gravado')} {salp.get('iva')}")
        check("SALP: punto_venta 0 y numero de numeracion_compras",
              salp.get("punto_venta") == 0 and salp.get("numero") is not None and salp_num,
              f"pv={salp.get('punto_venta')} nro={salp.get('numero')} {salp_num}")
        vtos = salp.get("vencimientos") or []
        check("SALP: UN vencimiento a la fecha del documento",
              len(vtos) == 1 and vtos[0].get("fecha_vto") == ayer and D(vtos[0].get("importe", 0)) == D("500"),
              str(vtos))
        check("SALP: snapshot del proveedor (BUE)",
              salp.get("proveedor_id") == prov_id and salp.get("proveedor_nombre") == f"Proveedor SI {SUF}"
              and salp.get("proveedor_condicion_iva") == "RI", f"{salp.get('proveedor_nombre')}")

        # validaciones
        st, r = _req("POST", base, "/compras/saldos-iniciales", tok,
                     {"proveedor_id": prov_id, "importe": "0", "sentido": "debemos"})
        check("compras: importe 0 -> 422", st == 422, f"{st} {r}")
        st, r = _req("POST", base, "/compras/saldos-iniciales", tok,
                     {"proveedor_id": prov_id, "importe": "10", "sentido": "deudor"})
        check("compras: sentido inválido (el de ventas) -> 422", st == 422, f"{st} {r}")
        st, r = _req("POST", base, "/compras/saldos-iniciales", tok,
                     {"proveedor_id": prov_id, "importe": "10", "sentido": "debemos", "fecha": manana})
        check("compras: fecha futura -> 422", st == 422, f"{st} {r}")
        st, r = _req("POST", base, "/compras/saldos-iniciales", tok,
                     {"proveedor_id": str(uuid.uuid4()), "importe": "10", "sentido": "debemos"})
        check("compras: proveedor inexistente -> 404", st == 404, f"{st} {r}")

        # cta. cte. del proveedor
        st, cc = _req("GET", base, f"/compras/pagos/cuenta-corriente/{prov_id}", tok)
        m = _mov(cc, salp_num, "Saldo inicial a pagar")
        check("cta. cte. proveedor: el SALP aparece con debe 500",
              st == 200 and D(m.get("debe", 0)) == D("500") and D(m.get("pendiente", 0)) == D("500")
              and m.get("tipo") == "Saldo inicial a pagar", f"{st} {m}")
        check("cta. cte. proveedor: saldo 500", st == 200 and D(cc.get("saldo", 0)) == D("500"),
              str(cc.get("saldo")))
        st, saldos = _req("GET", base, "/compras/pagos/saldos", tok)
        fila = next((x for x in (saldos or []) if x.get("proveedor_id") == prov_id), {})
        check("saldos por proveedor: figura con 500", st == 200 and D(fila.get("saldo", 0)) == D("500"),
              f"{st} {fila}")
        st, vtos_p = _req("GET", base, "/compras/pagos/vencimientos?dias=0", tok)
        fila = next((x for x in (vtos_p or []) if x.get("compra_id") == salp_id), {})
        check("cuentas a pagar: el SALP figura vencido (fecha_vto ayer)",
              st == 200 and fila.get("vencida") is True and D(fila.get("saldo_compra", 0)) == D("500"),
              f"{st} {fila}")

        # no fiscal: libro IVA compras ni derivación contable
        en_libro = _en_libro(base, tok, "iva-compras", periodos, salp_id)
        check("libro IVA compras: el SALP NO figura", en_libro is False, f"{en_libro}")
        m1 = _regenerar(base, tok, ayer, hoy_s)
        if m0 is None or m1 is None:
            print("      SKIP delta de asientos derivados (regenerar no disponible)")
        else:
            check("regenerar: la cantidad de asientos derivados no cambió con el SALP", m1 == m0,
                  f"{m0} -> {m1}")
        st, hits = _asientos_con(base, tok, ayer, "compra", f"SALP {salp_num}")
        check("asientos origen=compra del día: ninguno del SALP (todas las páginas)",
              st == 200 and hits == [], f"{st} {hits}")
        # la línea va al HABER (pasivo): debe − haber baja exactamente 500
        sp1 = _linea_apertura(base, tok, "Saldos de proveedores")
        check("apertura/sugerencia: «Saldos de proveedores» sumó exactamente 500 al haber",
              sp0 is not None and sp1 is not None and sp1 - sp0 == D("-500"), f"{sp0} -> {sp1}")

        # OP 200 imputada
        st, op = _req("POST", base, "/compras/pagos/ordenes-pago", tok, {
            "proveedor_id": prov_id,
            "medios": [{"medio": "efectivo", "importe": "200.00"}],
            "imputaciones": [{"compra_id": salp_id, "importe": "200.00"}],
            "observaciones": f"OP SI {SUF}",
        })
        check("OP 200 imputada al SALP -> 201 aplicado 200",
              st == 201 and D(op.get("aplicado", 0)) == D("200"), f"{st} {op}")
        op_id = op.get("id")
        st, det = _req("GET", base, f"/compras/comprobantes/{salp_id}", tok)
        check("SALP: saldo 300 tras la OP", st == 200 and D(det.get("saldo", 0)) == D("300"),
              str(det.get("saldo")))

        # SAFP nos deben 100
        st, safp = _req("POST", base, "/compras/saldos-iniciales", tok, {
            "proveedor_id": prov_id, "importe": "100.00", "sentido": "nos_deben",
            "observaciones": f"SAFP suite {SUF}",
        })
        check("POST saldo inicial a favor (nos deben) -> 201 SAFP registrado",
              st == 201 and safp.get("tipo_codigo") == "SAFP" and safp.get("estado") == "registrado"
              and safp.get("punto_venta") == 0 and (safp.get("vencimientos") or []) == [],
              f"{st} {safp}")
        safp_id = safp.get("id")
        safp_num = safp.get("numero_formateado")
        st, cc = _req("GET", base, f"/compras/pagos/cuenta-corriente/{prov_id}", tok)
        m = _mov(cc, safp_num, "Saldo inicial a favor")
        check("cta. cte. proveedor: el SAFP aparece como haber 100",
              st == 200 and D(m.get("haber", 0)) == D("100") and D(m.get("debe", 1)) == 0, f"{st} {m}")
        check("cta. cte. proveedor: saldo 200 (300 − 100)", D(cc.get("saldo", 0)) == D("200"),
              str(cc.get("saldo")))
        st, lista = _req("GET", base,
                         f"/compras/comprobantes?clase=saldo_inicial&proveedor_id={prov_id}&limit=50", tok)
        check("listado compras ?clase=saldo_inicial&proveedor_id lista SALP y SAFP",
              st == 200 and {x["id"] for x in (lista or [])} == {salp_id, safp_id}, f"{st}")

        # anulación
        st, r = _req("POST", base, f"/compras/comprobantes/{salp_id}/anular", tok)
        check("anular SALP con OP imputada -> 409", st == 409, f"{st} {r}")
        st, r = _req("POST", base, f"/compras/pagos/ordenes-pago/{op_id}/anular", tok)
        check("anular la OP -> 200", st == 200 and r.get("estado") == "anulada", f"{st} {r}")
        st, det = _req("GET", base, f"/compras/comprobantes/{salp_id}", tok)
        check("SALP: saldo restaurado a 500", st == 200 and D(det.get("saldo", 0)) == D("500"),
              str(det.get("saldo")))
        st, r = _req("POST", base, f"/compras/comprobantes/{salp_id}/anular", tok)
        check("anular SALP -> 200 estado anulado", st == 200 and r.get("estado") == "anulado", f"{st} {r}")
        st, cc = _req("GET", base, f"/compras/pagos/cuenta-corriente/{prov_id}", tok)
        check("cta. cte. proveedor: saldo −100 (solo el SAFP)",
              st == 200 and D(cc.get("saldo", 0)) == D("-100"), str(cc.get("saldo")))
        st, r = _req("POST", base, f"/compras/comprobantes/{safp_id}/anular", tok)
        check("anular SAFP -> 200", st == 200 and r.get("estado") == "anulado", f"{st} {r}")
        st, cc = _req("GET", base, f"/compras/pagos/cuenta-corriente/{prov_id}", tok)
        check("cta. cte. proveedor: saldo 0 con todo anulado", st == 200 and D(cc.get("saldo", 1)) == 0,
              str(cc.get("saldo")))
        st, saldos = _req("GET", base, "/compras/pagos/saldos?solo_con_deuda=false", tok)
        check("saldos por proveedor: ya no figura", st == 200
              and not any(x.get("proveedor_id") == prov_id for x in (saldos or [])), "")
        sp2 = _linea_apertura(base, tok, "Saldos de proveedores")
        check("apertura/sugerencia: «Saldos de proveedores» volvió al valor base (delta 0)",
              sp0 is not None and sp2 is not None and sp2 == sp0, f"{sp0} -> {sp2}")

    # ===== D. RBAC: rol «consulta» -> 403, nunca 401 =====
    print("--- D. RBAC")
    st, roles = _req("GET", base, "/roles", tok)
    consulta = next((x for x in (roles or []) if x.get("codigo") == "consulta"), None)
    check("rol sembrado «consulta» disponible", st == 200 and consulta is not None, f"{st}")
    tok_c = None
    user_id = None
    if consulta:
        clave_c = f"Consulta{SUF}"
        st, u = _req("POST", base, "/usuarios", tok, {
            "email": f"si-consulta-{SUF}@zgc.dev", "nombre": f"Consulta SI {SUF}",
            "password": clave_c, "rol_id": consulta["id"],
        })
        check("alta usuario de consulta -> 201", st == 201, f"{st} {u}")
        user_id = (u or {}).get("id")
        st, r = _req("POST", base, "/auth/login",
                     body={"email": f"si-consulta-{SUF}@zgc.dev", "password": clave_c})
        check("login del usuario de consulta", st == 200, f"{st} {r}")
        tok_c = (r or {}).get("access_token") if st == 200 else None
    if tok_c:
        st, r = _req("POST", base, "/ventas/saldos-iniciales", tok_c,
                     {"cliente_id": cli_id, "importe": "10", "sentido": "deudor"})
        check("consulta: POST /ventas/saldos-iniciales -> 403 (nunca 401)", st == 403, f"{st} {r}")
        st, r = _req("POST", base, "/compras/saldos-iniciales", tok_c,
                     {"proveedor_id": prov_id, "importe": "10", "sentido": "debemos"})
        check("consulta: POST /compras/saldos-iniciales -> 403 (nunca 401)", st == 403, f"{st} {r}")
        st, r = _req("GET", base, f"/ventas/comprobantes/{sal_id}", tok_c)
        check("consulta: GET del saldo inicial -> 200 (ver)", st == 200 and r.get("id") == sal_id, f"{st}")
        st, r = _req("GET", base, f"/cobranzas/cuenta-corriente/{cli_id}", tok_c)
        check("consulta: GET cta. cte. -> 200", st == 200, f"{st}")
    # sin token: 401 (autenticación), para contrastar con el 403 de arriba
    st, r = _req("POST", base, "/ventas/saldos-iniciales", None,
                 {"cliente_id": cli_id, "importe": "10", "sentido": "deudor"})
    check("sin JWT: 401", st == 401, f"{st} {r}")

    # ===== E. Cleanup mínimo =====
    print("--- E. cleanup")
    # los documentos quedaron anulados en B/C; el cliente/proveedor con sufijo
    # no molestan (saldo 0, sin deuda) — se desactivan para no ensuciar listados
    st, _ = _req("PUT", base, f"/clientes/{cli_id}", tok, {"activo": False})
    check("cleanup: cliente desactivado", st == 200, f"{st}")
    if clib_id:
        _req("PUT", base, f"/clientes/{clib_id}", tok, {"activo": False})
    st, _ = _req("PUT", base, f"/proveedores/{prov_id}", tok, {"activo": False})
    check("cleanup: proveedor desactivado", st == 200, f"{st}")
    if user_id:
        st, _ = _req("PUT", base, f"/usuarios/{user_id}", tok, {"activo": False})
        check("cleanup: usuario de consulta desactivado", st == 200, f"{st}")

    print(f"\n===== {ok} ok / {fail} fail =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
