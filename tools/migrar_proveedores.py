r"""
Migrador de proveedores RevoSolution (PROVEEDO.DBF + ART_PROV.DBF) -> ZGC
(BUE + rol proveedor + costos por proveedor + proveedor habitual del artículo).

Herramienta interna de onboarding, espejo de migrar_clientes.py: la corre César
por cada ex cliente RevoSolution, idealmente DESPUÉS de migrar artículos al
mismo tenant (ART_PROV y el proveedor habitual matchean por código de artículo).
Idempotente: proveedores ya migrados (mismo código) se saltean.

Uso:
    cd backend
    $env:ENV_FILE=".env.local"
    .venv\Scripts\python.exe ..\tools\migrar_proveedores.py `
        --carpeta "..\Revosolution Software\BAck UP CLiente\eVARISTORE\SuperGestion" `
        --tenant-id <uuid> [--aplicar] [--encoding cp1252] [--limite 50]

Sin --aplicar hace un dry-run: transforma y reporta, no escribe nada.

Calibrado con censo de los 46 PROVEEDO / 21 ART_PROV reales (2026-07-05, ver
docs/legacy/recon-proveedores.md):
- Encoding por LDID (byte 29): TODOS los PROVEEDO reales son 0x03 (cp1252),
  a diferencia de CLIENTES.DBF (cp850). --encoding fuerza otro codec.
- REGPROV usa la codificación de REGCLI (1 RI / 3 CF / 4 EX / 6 MT; 2 y 5
  abolidas -> RI/CF). 0 o vacío = "sin cargar" (52/63 en eVARISTORE):
  RI si hay CUIT válido, CF si no.
- Coherencia BUE (espejo clientes): RI sin CUIT válido queda CF con aviso.
- BUE cross-rol: si el CUIT ya existe en el tenant (p. ej. migrado como
  cliente), el rol proveedor se cuelga de ESA entidad — no se duplica el
  maestro. Dos PROVEEDO con el mismo CUIT: el primero se lleva el documento,
  el segundo queda SD con nota (siguen siendo proveedores distintos).
- CCOND -> condiciones_venta vía CONVTA.DBF (catálogo compartido con ventas,
  mismo dedupe por descripción que migrar_clientes).
- ART_PROV: solo filas cuyo CODART matchea articulos.codigo del tenant y cuyo
  CPROV matchea un proveedor (eVARISTORE: 99,9%). Duplicados (proveedor,
  artículo): gana la fila con ULT_FECHA más nueva.
- ARTICULO.DBF (si está en la carpeta): CPROV -> articulos.proveedor_habitual_id,
  solo si el artículo no tiene ya uno.
- NO se migra (decisión 2026-07-05): saldos legacy FSALPROV/SALPROV_*/TSALDO
  (la cta. cte. arranca en cero; un saldo vivo se carga como comprobante de
  apertura), CAI/VTOCAI (régimen de imprenta viejo), PAGOPROV/RET_PROV
  (historia transaccional), FORMA_PAGO/ULT_LISTA de ART_PROV (texto libre sin
  destino en el modelo).
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("ENV_FILE", str(BACKEND / ".env.local"))

from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from migrar_articulos import buscar_archivo, encoding_de, leer_dbf, num, txt  # noqa: E402
from migrar_clientes import (  # noqa: E402
    MAPEO_PROVINCIAS,
    MAPEO_REGCLI,
    clave_provincia,
    email_valido,
    inferir_tipo_persona,
    leer_condiciones_venta,
)

from app.core.cuit import solo_digitos, validar_cuit  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Articulo,
    ArticuloProveedor,
    CondicionVenta,
    Entidad,
    EntidadContacto,
    Proveedor,
    Provincia,
    Tenant,
)


class Transformado:
    """Resultado de transformar un PROVEEDO legacy: entidad + rol + avisos."""

    def __init__(self, codigo, entidad, proveedor, contacto, avisos):
        self.codigo = codigo
        self.entidad = entidad
        self.proveedor = proveedor
        self.contacto = contacto
        self.avisos = avisos


def transformar_registro(rec: dict, provincias_por_nombre: dict[str, int]) -> Transformado | None:
    avisos: list[str] = []
    codigo = txt(rec.get("CPROV"))
    if codigo and len(codigo) > 10:
        avisos.append(f"CPROV '{codigo}' excede 10 caracteres -> truncado")
        codigo = codigo[:10]
    nombre = txt(rec.get("NOMPROV"))
    if not nombre:
        return None  # registro sin razón social: no migrable

    # --- documento (los proveedores del legacy solo traen CUIT) ---
    cuit = solo_digitos(txt(rec.get("CUITPROV")) or "")
    tipo_doc, nro_doc = "SD", None
    if cuit:
        if validar_cuit(cuit):
            tipo_doc, nro_doc = "CUIT", cuit
        else:
            avisos.append(f"CUIT inválido '{rec.get('CUITPROV')}' -> queda SD (se anota en observaciones)")

    # --- condición IVA: REGPROV con la codificación de REGCLI ---
    regprov = rec.get("REGPROV")
    try:
        regprov = int(regprov) if regprov is not None else None
    except (TypeError, ValueError):
        regprov = None
    if regprov in MAPEO_REGCLI:
        condicion_iva = MAPEO_REGCLI[regprov]
    else:
        # 0/None = sin cargar (mayoría en bases chicas): inferir por el CUIT
        condicion_iva = "RI" if tipo_doc == "CUIT" else "CF"
        if regprov not in (None, 0):
            avisos.append(f"REGPROV={regprov} sin mapeo -> {condicion_iva}")
    if condicion_iva == "RI" and tipo_doc != "CUIT":
        avisos.append("REGPROV=RI pero sin CUIT válido -> condicion_iva CF")
        condicion_iva = "CF"

    # --- provincia (PROVIN texto libre, mismo mapeo que clientes) ---
    provincia_id = None
    prov_txt = txt(rec.get("PROVIN"))
    if prov_txt:
        nombre_arca = MAPEO_PROVINCIAS.get(clave_provincia(prov_txt))
        if nombre_arca:
            provincia_id = provincias_por_nombre.get(nombre_arca)
        else:
            avisos.append(f"Provincia no mapeada: '{prov_txt}'")

    # --- email / notas de datos maestros -> observaciones de la ENTIDAD ---
    email = txt(rec.get("E_MAIL"))
    if email and not email_valido(email):
        avisos.append(f"Email inválido '{email}' -> a observaciones")
        email = None

    obs_entidad = []
    if cuit and tipo_doc != "CUIT":
        obs_entidad.append(f"[migración] CUIT legacy inválido: {rec.get('CUITPROV')}")
    email_crudo = txt(rec.get("E_MAIL"))
    if email_crudo and email is None:
        obs_entidad.append(f"[migración] email legacy: {email_crudo}")
    for campo, etiqueta in (("TELPROV_3", "teléfono 3"), ("TELPROV_4", "teléfono 4"), ("FAX", "fax"), ("HTTP", "web")):
        v = txt(rec.get(campo))
        if v:
            obs_entidad.append(f"[migración] {etiqueta} legacy: {v}")

    entidad = dict(
        tipo_persona=inferir_tipo_persona(nro_doc if tipo_doc == "CUIT" else None, nombre),
        razon_social=nombre[:120],
        tipo_documento=tipo_doc,
        nro_documento=nro_doc,
        condicion_iva=condicion_iva,
        email=email,
        telefono_1=txt(rec.get("TELPROV_1")),
        telefono_2=txt(rec.get("TELPROV_2")),
        domicilio=txt(rec.get("DOMPROV")),
        localidad=txt(rec.get("LOCPROV")),
        provincia_id=provincia_id,
        codigo_postal=txt(rec.get("CODPOS")),
        observaciones="\n".join(obs_entidad) or None,
    )

    # OBSERVAC (memo, notas del negocio con ese proveedor) -> observaciones del ROL
    rubro = txt(rec.get("RUBRO"))
    proveedor = dict(
        codigo=codigo or None,
        rubro=rubro[:40] if rubro else None,
        observaciones=txt(rec.get("OBSERVAC")) or None,
        _ccond=txt(rec.get("CCOND")),
    )

    contacto = txt(rec.get("CONTACTO"))
    return Transformado(codigo or None, entidad, proveedor, contacto, avisos)


def dedupe_art_prov(filas: list[dict]) -> list[dict]:
    """Una fila por (CPROV, CODART): gana la de ULT_FECHA más nueva."""
    por_clave: dict[tuple, dict] = {}
    for f in filas:
        clave = (txt(f.get("CPROV")), txt(f.get("CODART")))
        previa = por_clave.get(clave)
        if previa is None:
            por_clave[clave] = f
            continue
        fn, fp = f.get("ULT_FECHA"), previa.get("ULT_FECHA")
        if (fn is not None) and (fp is None or fn > fp):
            por_clave[clave] = f
    return list(por_clave.values())


async def migrar(args) -> dict:
    carpeta = Path(args.carpeta).resolve()
    dbf_prov = buscar_archivo(carpeta, "proveedo.dbf")
    if dbf_prov is None:
        sys.exit(f"No se encontró PROVEEDO.DBF en {carpeta}")

    encoding = encoding_de(dbf_prov, args.encoding, args.encoding_fallback)
    registros = leer_dbf(dbf_prov, args.encoding, args.encoding_fallback)
    if args.limite is not None:
        registros = registros[: args.limite]
    condiciones_legacy = leer_condiciones_venta(carpeta, encoding)

    dbf_artprov = buscar_archivo(carpeta, "art_prov.dbf")
    filas_artprov = leer_dbf(dbf_artprov, args.encoding, args.encoding_fallback) if dbf_artprov else []
    dbf_articulo = buscar_archivo(carpeta, "articulo.dbf")

    reporte = {
        "carpeta": str(carpeta),
        "encoding": encoding,
        "aplicado": bool(args.aplicar),
        "leidos": len(registros),
        "migrados": 0,
        "salteados_existentes": 0,
        "sin_nombre": 0,
        "entidades_reusadas_bue": 0,
        "documentos_duplicados_legacy": 0,
        "condiciones_venta_creadas": 0,
        "contactos_creados": 0,
        "art_prov_leidas": len(filas_artprov),
        "art_prov_migradas": 0,
        "art_prov_salteadas_existentes": 0,
        "art_prov_sin_articulo": 0,
        "art_prov_sin_proveedor": 0,
        "habituales_asignados": 0,
        "avisos": [],
    }

    async with SessionLocal() as db:
        # --- tenant ---
        if args.crear_tenant:
            tenant = Tenant(razon_social=args.crear_tenant, condicion_iva="RI")
            db.add(tenant)
            await db.flush()
        else:
            tenant = await db.get(Tenant, args.tenant_id)
            if tenant is None:
                sys.exit(f"Tenant {args.tenant_id} no existe")
        sufijo = "" if args.aplicar else " (dry-run: no persistido)"
        reporte["tenant_id"] = str(tenant.id) + (sufijo if args.crear_tenant else "")
        reporte["tenant"] = tenant.razon_social

        provincias_por_nombre = {
            p.nombre: p.codigo_arca for p in (await db.scalars(select(Provincia))).all()
        }

        # --- catálogo: condiciones (CONVTA compartida con ventas; dedupe por
        # descripción, mismo criterio que migrar_clientes) ---
        cond_por_codigo: dict[str, CondicionVenta] = {}
        cond_por_descripcion: dict[str, CondicionVenta] = {
            c.descripcion: c
            for c in (
                await db.scalars(select(CondicionVenta).where(CondicionVenta.tenant_id == tenant.id))
            ).all()
        }
        for c in condiciones_legacy:
            existente = cond_por_descripcion.get(c["descripcion"])
            if existente is None:
                existente = CondicionVenta(
                    tenant_id=tenant.id, descripcion=c["descripcion"], dias=c["dias"]
                )
                db.add(existente)
                await db.flush()
                cond_por_descripcion[c["descripcion"]] = existente
                reporte["condiciones_venta_creadas"] += 1
            cond_por_codigo[c["codigo"]] = existente

        # --- idempotencia y BUE cross-rol ---
        # 1) proveedores ya migrados, por código
        codigos_existentes = set(
            (await db.scalars(select(Proveedor.codigo).where(Proveedor.tenant_id == tenant.id))).all()
        )
        # 2) entidades del tenant por documento (cualquier rol): si el CUIT ya
        #    existe, el rol proveedor se cuelga de esa entidad (BUE §1-bis)
        entidad_por_doc: dict[tuple[str, str], object] = {}
        for e in (
            await db.scalars(
                select(Entidad).where(Entidad.tenant_id == tenant.id, Entidad.nro_documento.is_not(None))
            )
        ).all():
            entidad_por_doc[(e.tipo_documento, e.nro_documento)] = e
        # 3) entidades que YA tienen rol proveedor (para no duplicar el rol)
        entidades_con_rol = set(
            (await db.scalars(select(Proveedor.entidad_id).where(Proveedor.tenant_id == tenant.id))).all()
        )
        # 4) sin código: clave best-effort (espejo clientes)
        sin_codigo_existentes: set[tuple] = {
            (rs.lower(), nro, (dom or "").lower())
            for rs, nro, dom in (
                await db.execute(
                    select(Entidad.razon_social, Entidad.nro_documento, Entidad.domicilio)
                    .join(Proveedor, Proveedor.entidad_id == Entidad.id)
                    .where(Proveedor.tenant_id == tenant.id, Proveedor.codigo.is_(None))
                )
            ).all()
        }

        proveedor_por_cprov: dict[str, Proveedor] = {
            p.codigo: p
            for p in (
                await db.scalars(select(Proveedor).where(Proveedor.tenant_id == tenant.id))
            ).all()
            if p.codigo
        }

        registro_actual = "?"
        for rec in registros:
            t = transformar_registro(rec, provincias_por_nombre)
            if t is None:
                reporte["sin_nombre"] += 1
                continue
            registro_actual = f"{t.codigo or '?'} {t.entidad['razon_social']}"
            if t.codigo and t.codigo in codigos_existentes:
                reporte["salteados_existentes"] += 1
                continue
            if not t.codigo:
                rs = t.entidad["razon_social"].lower()
                dom = (t.entidad["domicilio"] or "").lower()
                if (rs, t.entidad["nro_documento"], dom) in sin_codigo_existentes or (
                    (rs, None, dom) in sin_codigo_existentes
                ):
                    reporte["salteados_existentes"] += 1
                    continue
                reporte["avisos"].append(
                    f"[? {t.entidad['razon_social']}] sin CPROV: idempotencia best-effort "
                    "por razón social+documento+domicilio"
                )

            # BUE: ¿el documento ya existe en el tenant?
            entidad = None
            if t.entidad["nro_documento"]:
                clave = (t.entidad["tipo_documento"], t.entidad["nro_documento"])
                existente = entidad_por_doc.get(clave)
                if existente is not None:
                    if existente.id in entidades_con_rol:
                        # esa entidad YA es proveedor (otro CPROV con el mismo
                        # CUIT: sucursales del legacy). Espejo clientes: este
                        # registro queda como entidad aparte SD con nota, así
                        # conserva su CPROV (y sus filas de ART_PROV).
                        reporte["documentos_duplicados_legacy"] += 1
                        nota = (
                            f"[migración] documento {clave[0]} {clave[1]} compartido con "
                            f"otro proveedor legacy ('{existente.razon_social}')"
                        )
                        t.entidad["observaciones"] = (
                            (t.entidad["observaciones"] + "\n" + nota) if t.entidad["observaciones"] else nota
                        )
                        t.entidad["tipo_documento"], t.entidad["nro_documento"] = "SD", None
                        if t.entidad["condicion_iva"] == "RI":
                            t.entidad["condicion_iva"] = "CF"
                    else:
                        entidad = existente
                        reporte["entidades_reusadas_bue"] += 1
                        reporte["avisos"].append(
                            f"[{registro_actual}] documento {clave[1]} ya existía en el tenant "
                            f"(entidad '{existente.razon_social}') -> rol proveedor sobre esa entidad"
                        )

            for aviso in t.avisos:
                reporte["avisos"].append(f"[{registro_actual}] {aviso}")

            if entidad is None:
                entidad = Entidad(tenant_id=tenant.id, **t.entidad)
                db.add(entidad)
                try:
                    await db.flush()
                except IntegrityError as exc:
                    await db.rollback()
                    reporte["error"] = (
                        f"Unicidad violada al insertar '{registro_actual}': {exc.orig}. "
                        "Corrida abortada de forma atómica: no se escribió nada."
                    )
                    return reporte
                if t.entidad["nro_documento"]:
                    entidad_por_doc[(t.entidad["tipo_documento"], t.entidad["nro_documento"])] = entidad

            cond = cond_por_codigo.get(t.proveedor["_ccond"]) if t.proveedor["_ccond"] else None
            datos_prov = {k: v for k, v in t.proveedor.items() if not k.startswith("_")}
            proveedor = Proveedor(
                tenant_id=tenant.id,
                entidad_id=entidad.id,
                condicion_compra_id=cond.id if cond else None,
                **datos_prov,
            )
            db.add(proveedor)
            try:
                await db.flush()
            except IntegrityError as exc:
                await db.rollback()
                reporte["error"] = (
                    f"Unicidad violada al insertar rol de '{registro_actual}': {exc.orig}. "
                    "Corrida abortada de forma atómica: no se escribió nada."
                )
                return reporte
            entidades_con_rol.add(entidad.id)

            if t.contacto:
                db.add(
                    EntidadContacto(tenant_id=tenant.id, entidad_id=entidad.id, nombre=t.contacto[:80])
                )
                reporte["contactos_creados"] += 1

            if t.codigo:
                codigos_existentes.add(t.codigo)
                proveedor_por_cprov[t.codigo] = proveedor
            else:
                sin_codigo_existentes.add(
                    (
                        t.entidad["razon_social"].lower(),
                        t.entidad["nro_documento"],
                        (t.entidad["domicilio"] or "").lower(),
                    )
                )
            reporte["migrados"] += 1

        # --- artículos del tenant por código (para ART_PROV y habituales) ---
        articulo_por_codigo: dict[str, object] = {}
        if filas_artprov or dbf_articulo is not None:
            articulo_por_codigo = {
                cod: aid
                for aid, cod in (
                    await db.execute(
                        select(Articulo.id, Articulo.codigo).where(Articulo.tenant_id == tenant.id)
                    )
                ).all()
            }

        # --- ART_PROV -> articulo_proveedores ---
        if filas_artprov:
            pares_existentes = {
                (a, p)
                for a, p in (
                    await db.execute(
                        select(ArticuloProveedor.articulo_id, ArticuloProveedor.proveedor_id).where(
                            ArticuloProveedor.tenant_id == tenant.id
                        )
                    )
                ).all()
            }
            cprov_huerfanos: set[str] = set()
            filas = dedupe_art_prov([f for f in filas_artprov if txt(f.get("CODART"))])
            for f in filas:
                cprov = txt(f.get("CPROV"))
                prov = proveedor_por_cprov.get(cprov)
                if prov is None:
                    reporte["art_prov_sin_proveedor"] += 1
                    if cprov and cprov not in cprov_huerfanos:
                        cprov_huerfanos.add(cprov)
                        reporte["avisos"].append(f"[ART_PROV] CPROV '{cprov}' sin proveedor migrado -> filas salteadas")
                    continue
                articulo_id = articulo_por_codigo.get(txt(f.get("CODART")))
                if articulo_id is None:
                    reporte["art_prov_sin_articulo"] += 1
                    continue
                if (articulo_id, prov.id) in pares_existentes:
                    reporte["art_prov_salteadas_existentes"] += 1
                    continue
                codsprov = txt(f.get("CODSPROV"))
                db.add(
                    ArticuloProveedor(
                        tenant_id=tenant.id,
                        articulo_id=articulo_id,
                        proveedor_id=prov.id,
                        codigo_proveedor=codsprov[:30] if codsprov else None,
                        costo=num(f.get("COSTO")),
                        bonif_1=num(f.get("BONIF1")),
                        bonif_2=num(f.get("BONIF2")),
                        bonif_3=num(f.get("BONIF3")),
                        ultima_compra=f.get("ULT_FECHA"),
                    )
                )
                pares_existentes.add((articulo_id, prov.id))
                reporte["art_prov_migradas"] += 1

        # --- ARTICULO.DBF: CPROV -> proveedor habitual (si no tiene) ---
        if dbf_articulo is not None:
            por_proveedor: dict = {}  # proveedor_id -> [articulo_id, ...]
            for rec in leer_dbf(dbf_articulo, args.encoding, args.encoding_fallback):
                cprov = txt(rec.get("CPROV"))
                codart = txt(rec.get("CODART"))
                prov = proveedor_por_cprov.get(cprov) if cprov else None
                articulo_id = articulo_por_codigo.get(codart) if codart else None
                if prov is None or articulo_id is None:
                    continue
                por_proveedor.setdefault(prov.id, []).append(articulo_id)
            for prov_id, articulo_ids in por_proveedor.items():
                resultado = await db.execute(
                    update(Articulo)
                    .where(
                        Articulo.id.in_(articulo_ids),
                        Articulo.tenant_id == tenant.id,
                        Articulo.proveedor_habitual_id.is_(None),
                    )
                    .values(proveedor_habitual_id=prov_id)
                )
                reporte["habituales_asignados"] += resultado.rowcount

        try:
            if args.aplicar:
                await db.commit()
            else:
                await db.rollback()
        except IntegrityError as exc:
            await db.rollback()
            reporte["error"] = (
                f"Unicidad violada al confirmar (último registro: '{registro_actual}'): {exc.orig}"
            )

    return reporte


def main():
    parser = argparse.ArgumentParser(
        description="Migra PROVEEDO.DBF (+ ART_PROV.DBF) de RevoSolution a la BUE de ZGC"
    )
    parser.add_argument("--carpeta", required=True, help="Carpeta del backup legacy con PROVEEDO.DBF")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--tenant-id", help="UUID del tenant destino existente")
    grupo.add_argument("--crear-tenant", help="Crear un tenant nuevo con esta razón social")
    parser.add_argument("--aplicar", action="store_true", help="Escribe en la DB (sin esto: dry-run)")
    parser.add_argument(
        "--encoding", default=None, help="Forzar codec (por defecto: LDID del header, byte 29)"
    )
    parser.add_argument("--encoding-fallback", default="cp1252", help="Codec si el LDID es desconocido")
    parser.add_argument("--limite", type=int, default=None, help="Procesar solo N registros (pruebas)")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    reporte = asyncio.run(migrar(args))

    salida = Path(__file__).parent / "reportes"
    salida.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = salida / f"migracion-proveedores-{stamp}.json"
    out.write_text(json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")

    if reporte.get("error"):
        modo = "FALLIDA (abortada de forma atómica)"
    elif reporte["aplicado"]:
        modo = "APLICADO"
    else:
        modo = "DRY-RUN (no se escribió nada)"
    print(f"\n===== MIGRACIÓN DE PROVEEDORES — {modo} =====")
    if reporte.get("error"):
        print(f"  ERROR: {reporte['error']}")
    for k in (
        "carpeta", "tenant", "tenant_id", "encoding", "leidos", "migrados",
        "salteados_existentes", "sin_nombre", "entidades_reusadas_bue",
        "documentos_duplicados_legacy", "condiciones_venta_creadas", "contactos_creados",
        "art_prov_leidas", "art_prov_migradas", "art_prov_salteadas_existentes",
        "art_prov_sin_articulo", "art_prov_sin_proveedor", "habituales_asignados",
    ):
        print(f"  {k}: {reporte.get(k)}")
    print(f"  avisos: {len(reporte['avisos'])}")
    for a in reporte["avisos"][:40]:
        print(f"    - {a}")
    if len(reporte["avisos"]) > 40:
        print(f"    ... y {len(reporte['avisos']) - 40} más (ver JSON)")
    print(f"\nReporte completo: {out}")


if __name__ == "__main__":
    main()
