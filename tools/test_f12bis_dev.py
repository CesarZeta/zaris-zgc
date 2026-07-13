"""Suite en vivo de F12-bis (Logística de entregas) contra DEV.

Cubre: ABM del rol transportista sobre la BUE (unicidad, cross-rol), creación
de entregas desde facturas/remitos EMITIDOS (snapshot de domicilio con
fallback entidad → 422 sin domicilio; 409 entrega activa duplicada; 422 para
clases no entregables y borradores), entregables, rendición directa y con
motivo obligatorio en rechazos, reprogramación (la rechazada queda terminal y
nace una nueva), anulación (libera el comprobante), hojas de ruta (armado con
orden de recorrido, transportista propagado, edición solo abierta, despacho,
cierre exigiendo rendición completa, anulación solo abierta que libera) y la
regla de encuadre: el estado de entrega NO toca el circuito fiscal.

Uso:
    python tools/test_f12bis_dev.py --base http://127.0.0.1:8021 \
        --email admin@zgc.dev --clave 123456
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
NUM6 = f"{int(SUF, 16) % 1_000_000:06d}"


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
    check("login expone permiso logistica", (r.get("permisos") or {}).get("logistica") is not None
          or r.get("permisos") is None, r.get("permisos", {}).get("logistica"))
    print(f"sufijo {SUF}")

    # ===== 1. ABM transportistas (rol BUE) =====
    st, t1 = _req("POST", base, "/logistica/transportistas", tok, {
        "entidad": {"razon_social": f"Fletes Sur {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": NUM6, "condicion_iva": "CF",
                    "telefono_1": "341-5550001"},
        "vehiculo": "Fiat Fiorino", "dominio": "AB123CD"})
    check("alta transportista -> 201", st == 201, f"{st} {t1}")
    st, r2 = _req("POST", base, "/logistica/transportistas", tok, {"entidad_id": t1["entidad"]["id"]})
    check("entidad ya transportista -> 409", st == 409, f"{st}")
    st, lista = _req("GET", base, f"/logistica/transportistas?q={NUM6}", tok)
    check("listado con búsqueda", st == 200 and len(lista) == 1, f"{st} n={len(lista)}")
    st, t1b = _req("PUT", base, f"/logistica/transportistas/{t1['id']}", tok, {"vehiculo": "Camión Iveco"})
    check("editar transportista -> 200", st == 200 and t1b["vehiculo"] == "Camión Iveco", f"{st}")

    # cross-rol BUE: el cliente también puede ser transportista (misma entidad)
    st, cli = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente Entregas {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": str(int(NUM6) + 1).zfill(6),
                    "condicion_iva": "CF", "domicilio": f"Av. Siempreviva {SUF} 742",
                    "localidad": "Rosario", "telefono_1": "341-5550002"}})
    check("cliente con domicilio -> 201", st == 201, f"{st} {cli if st != 201 else ''}")
    st, t2 = _req("POST", base, "/logistica/transportistas", tok, {"entidad_id": cli["entidad"]["id"]})
    check("cross-rol BUE: cliente también transportista -> 201", st == 201, f"{st}")

    # ===== 2. Fixtures de venta =====
    st, art = _req("POST", base, "/articulos", tok, {
        "codigo": f"F12B{SUF}", "descripcion": f"Artículo F12bis {SUF}",
        "costo": "100.00", "tasa_iva": "21", "precio_1": "242.00"})
    check("artículo fixture -> 201", st == 201, f"{st} {art if st != 201 else ''}")
    st, pvs = _req("GET", base, "/ventas/puntos-venta", tok)
    pv_id = pvs[0]["id"]

    def emitir(clase, cliente_id, contado=True):
        st, b = _req("POST", base, "/ventas/comprobantes", tok, {
            "clase": clase, "punto_venta_id": pv_id, "cliente_id": cliente_id,
            "contado": contado, "precios_con_iva": True,
            "items": [{"articulo_id": art["id"], "cantidad": "1",
                       "precio_unitario": "121.00", "tasa_iva": "21"}]})
        if st != 201:
            return st, b
        medios = {"medios": [{"medio": "efectivo", "importe": b["total"]}]} if (
            clase == "factura" and contado) else {}
        return _req("POST", base, f"/ventas/comprobantes/{b['id']}/emitir", tok, medios)

    st, f1 = emitir("factura", cli["id"])
    check("factura emitida", st == 200, f"{st} {f1 if st != 200 else ''}")
    st, rem1 = emitir("remito", cli["id"])
    check("remito emitido", st == 200, f"{st} {rem1 if st != 200 else ''}")
    st, pre1 = emitir("presupuesto", cli["id"])
    check("presupuesto emitido (fixture negativo)", st == 200, f"{st}")

    # ===== 3. Crear entregas: snapshot y validaciones =====
    st, e1 = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": f1["id"]})
    check("entrega de factura -> 201", st == 201, f"{st} {e1 if st != 201 else ''}")
    check("snapshot: domicilio heredado de la entidad",
          e1["domicilio"] == f"Av. Siempreviva {SUF} 742" and e1["localidad"] == "Rosario",
          f"{e1['domicilio']} / {e1['localidad']}")
    check("snapshot: teléfono de la entidad", e1["telefono"] == "341-5550002", e1["telefono"])
    check("destinatario = receptor del comprobante",
          e1["destinatario"] == f"Cliente Entregas {SUF}", e1["destinatario"])

    st, r2 = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": f1["id"]})
    check("segunda entrega del mismo comprobante -> 409", st == 409, f"{st}")
    st, r2 = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": pre1["id"]})
    check("presupuesto no se reparte -> 422", st == 422, f"{st}")
    st, r2 = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": str(uuid.uuid4())})
    check("comprobante inexistente -> 404", st == 404, f"{st}")

    # borrador -> 422
    st, borr = _req("POST", base, "/ventas/comprobantes", tok, {
        "clase": "factura", "punto_venta_id": pv_id, "cliente_id": cli["id"], "contado": True,
        "precios_con_iva": True,
        "items": [{"articulo_id": art["id"], "cantidad": "1", "precio_unitario": "121.00",
                   "tasa_iva": "21"}]})
    st, r2 = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": borr["id"]})
    check("borrador no se reparte -> 422", st == 422, f"{st}")

    # cliente SIN domicilio -> 422 al crear la entrega
    st, cli2 = _req("POST", base, "/clientes", tok, {
        "entidad": {"razon_social": f"Cliente Sin Dom {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": str(int(NUM6) + 2).zfill(6),
                    "condicion_iva": "CF"}})
    st, f2 = emitir("factura", cli2["id"])
    st, r2 = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": f2["id"]})
    check("destino sin domicilio -> 422", st == 422, f"{st}")
    st, e2 = _req("POST", base, "/logistica/entregas", tok, {
        "comprobante_id": f2["id"], "domicilio": f"Depósito Norte {SUF}",
        "localidad": "Funes", "bultos": "2 cajas"})
    check("entrega con domicilio explícito -> 201",
          st == 201 and e2["domicilio"] == f"Depósito Norte {SUF}", f"{st}")

    # snapshot inmutable: cambiar el domicilio de la entidad NO toca la entrega
    st, _ = _req("PUT", base, f"/clientes/{cli['id']}", tok, {
        "entidad": {"razon_social": f"Cliente Entregas {SUF}", "tipo_persona": "F",
                    "tipo_documento": "DNI", "nro_documento": str(int(NUM6) + 1).zfill(6),
                    "condicion_iva": "CF", "domicilio": "Otra Calle 999",
                    "localidad": "Rosario", "telefono_1": "341-5550002"}})
    st, e1b = _req("GET", base, f"/logistica/entregas/{e1['id']}", tok)
    check("snapshot inmutable tras mudanza de la entidad",
          st == 200 and e1b["domicilio"] == f"Av. Siempreviva {SUF} 742", e1b["domicilio"])

    # ===== 4. Entregables =====
    st, ents = _req("GET", base, f"/logistica/entregables?q=Entregas%20{SUF}", tok)
    ids = {x["comprobante_id"] for x in ents} if st == 200 else set()
    check("entregables: el remito sin entrega aparece", st == 200 and rem1["id"] in ids, f"{st}")
    check("entregables: la factura con entrega activa NO aparece", f1["id"] not in ids)

    # ===== 5. Rendición directa (sin hoja) y validaciones =====
    st, r2 = _req("POST", base, f"/logistica/entregas/{e2['id']}/rendir", tok,
                  {"resultado": "rechazada"})
    check("rechazo sin motivo -> 422", st == 422, f"{st}")
    st, e2r = _req("POST", base, f"/logistica/entregas/{e2['id']}/rendir", tok,
                   {"resultado": "entregada", "recibido_por": "Juan Depósito"})
    check("rendición directa entregada -> 200",
          st == 200 and e2r["estado"] == "entregada" and e2r["recibido_por"] == "Juan Depósito",
          f"{st}")
    st, r2 = _req("POST", base, f"/logistica/entregas/{e2['id']}/rendir", tok,
                  {"resultado": "entregada"})
    check("re-rendir una entregada -> 422", st == 422, f"{st}")
    st, r2 = _req("POST", base, f"/logistica/entregas/{e2['id']}/anular", tok)
    check("anular una entregada -> 422", st == 422, f"{st}")

    # anulación libera el comprobante para una entrega nueva
    st, e_rem = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": rem1["id"]})
    check("entrega de remito -> 201", st == 201, f"{st}")
    st, e_rem_a = _req("POST", base, f"/logistica/entregas/{e_rem['id']}/anular", tok)
    check("anular pendiente -> 200 marcada", st == 200 and e_rem_a["anulada"] is True, f"{st}")
    st, e_rem2 = _req("POST", base, "/logistica/entregas", tok, {"comprobante_id": rem1["id"]})
    check("anulada libera: nueva entrega del remito -> 201", st == 201, f"{st}")

    # ===== 6. Hoja de ruta: armado, orden, despacho, rendición, cierre =====
    st, h1 = _req("POST", base, "/logistica/hojas", tok, {
        "transportista_id": t1["id"], "entrega_ids": [e_rem2["id"], e1["id"]]})
    check("crear hoja con 2 entregas -> 201",
          st == 201 and h1["cantidad_entregas"] == 2, f"{st} {h1 if st != 201 else ''}")
    ordenes = {e["id"]: e["orden"] for e in h1["entregas"]}
    check("orden = orden de selección",
          ordenes.get(e_rem2["id"]) == 1 and ordenes.get(e1["id"]) == 2, ordenes)
    check("entregas asignadas con transportista de la hoja",
          all(e["estado"] == "asignada" and e["transportista_id"] == t1["id"]
              for e in h1["entregas"]))

    # una entrega asignada no entra en otra hoja
    st, r2 = _req("POST", base, "/logistica/hojas", tok, {
        "transportista_id": t2["id"], "entrega_ids": [e1["id"]]})
    check("entrega ya asignada en otra hoja -> 422", st == 422, f"{st}")

    # editar: quitar una entrega (queda pendiente) y reordenar
    st, h1b = _req("PUT", base, f"/logistica/hojas/{h1['id']}", tok,
                   {"entrega_ids": [e1["id"]]})
    check("PUT hoja: queda 1 entrega", st == 200 and h1b["cantidad_entregas"] == 1, f"{st}")
    st, e_rem2b = _req("GET", base, f"/logistica/entregas/{e_rem2['id']}", tok)
    check("la quitada vuelve a pendiente sin hoja",
          e_rem2b["estado"] == "pendiente" and e_rem2b["hoja_ruta_id"] is None,
          e_rem2b["estado"])
    st, h1c = _req("PUT", base, f"/logistica/hojas/{h1['id']}", tok,
                   {"entrega_ids": [e1["id"], e_rem2["id"]]})
    check("PUT hoja: vuelve con 2 en otro orden", st == 200 and h1c["cantidad_entregas"] == 2, f"{st}")

    # despachar
    st, h1d = _req("POST", base, f"/logistica/hojas/{h1['id']}/despachar", tok)
    check("despachar -> en_reparto", st == 200 and h1d["estado"] == "en_reparto", f"{st}")
    check("entregas en reparto", all(e["estado"] == "en_reparto" for e in h1d["entregas"]))
    st, r2 = _req("PUT", base, f"/logistica/hojas/{h1['id']}", tok, {"entrega_ids": []})
    check("editar hoja despachada -> 422", st == 422, f"{st}")
    st, r2 = _req("POST", base, f"/logistica/hojas/{h1['id']}/anular", tok)
    check("anular hoja despachada -> 422", st == 422, f"{st}")

    # cerrar exige rendición completa
    st, r2 = _req("POST", base, f"/logistica/hojas/{h1['id']}/cerrar", tok)
    check("cerrar con entregas sin rendir -> 422", st == 422, f"{st}")
    st, _ = _req("POST", base, f"/logistica/entregas/{e1['id']}/rendir", tok,
                 {"resultado": "entregada", "recibido_por": "Cliente"})
    st, e_rej = _req("POST", base, f"/logistica/entregas/{e_rem2['id']}/rendir", tok,
                     {"resultado": "rechazada", "motivo_rechazo": "Cerrado, sin timbre"})
    check("rendir rechazada con motivo -> 200",
          st == 200 and e_rej["estado"] == "rechazada", f"{st}")
    st, h1e = _req("POST", base, f"/logistica/hojas/{h1['id']}/cerrar", tok)
    check("cerrar rendida -> 200 cerrada", st == 200 and h1e["estado"] == "cerrada", f"{st}")

    # ===== 7. Reprogramar la rechazada =====
    st, e_nueva = _req("POST", base, f"/logistica/entregas/{e_rem2['id']}/reprogramar", tok)
    check("reprogramar rechazada -> 201 nueva pendiente",
          st == 201 and e_nueva["estado"] == "pendiente"
          and e_nueva["comprobante_id"] == rem1["id"], f"{st}")
    st, e_vieja = _req("GET", base, f"/logistica/entregas/{e_rem2['id']}", tok)
    check("la rechazada queda terminal (reprogramada)",
          e_vieja["estado"] == "reprogramada", e_vieja["estado"])
    st, r2 = _req("POST", base, f"/logistica/entregas/{e_rem2['id']}/reprogramar", tok)
    check("re-reprogramar -> 422", st == 422, f"{st}")

    # ===== 8. Hoja anulada libera =====
    st, h2 = _req("POST", base, "/logistica/hojas", tok, {
        "transportista_id": t2["id"], "entrega_ids": [e_nueva["id"]]})
    check("segunda hoja numerada en secuencia", st == 201 and h2["numero"] == h1["numero"] + 1,
          f"{st} {h2.get('numero')}")
    st, h2a = _req("POST", base, f"/logistica/hojas/{h2['id']}/anular", tok)
    check("anular hoja abierta -> 200 marcada", st == 200 and h2a["anulada"] is True, f"{st}")
    st, e_nueva_b = _req("GET", base, f"/logistica/entregas/{e_nueva['id']}", tok)
    check("anulada la hoja, la entrega vuelve a pendiente",
          e_nueva_b["estado"] == "pendiente" and e_nueva_b["hoja_ruta_id"] is None,
          e_nueva_b["estado"])

    # ===== 9. Encuadre: logística no toca el circuito fiscal =====
    st, f1_final = _req("GET", base, f"/ventas/comprobantes/{f1['id']}", tok)
    check("la factura entregada sigue emitida con su total",
          st == 200 and f1_final["estado"] == "emitido"
          and D(f1_final["total"]) == D(f1["total"]), f"{st}")
    st, listado = _req("GET", base, "/logistica/entregas?estado=entregada&limit=200", tok)
    check("filtro por estado en el listado",
          st == 200 and any(x["id"] == e1["id"] for x in listado), f"{st}")

    print(f"\n===== F12-bis DEV: {ok} ok · {fail} FAIL =====")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
