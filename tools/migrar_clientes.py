r"""
Migrador de clientes RevoSolution (CLIENTES.DBF) -> ZGC (BUE + rol cliente).

Herramienta interna de onboarding (docs/DEFINICION-PRODUCTO.md §2): la corre
César por cada ex cliente RevoSolution. Lee la carpeta del backup legacy y
carga entidades + clientes + catálogos (zonas, condiciones de venta) en el
tenant indicado. Idempotente: los clientes ya migrados (mismo código) se saltean.

Uso:
    cd backend
    $env:ENV_FILE=".env.local"
    .venv\Scripts\python.exe ..\tools\migrar_clientes.py `
        --carpeta "..\Revosolution Software\BAck UP CLiente\Omni\Gestion Comercial" `
        --crear-tenant "Omni (migrado)" [--aplicar] [--encoding cp850] [--limite 50]

Sin --aplicar hace un dry-run: transforma y reporta, no escribe nada.

IMPORTANTE (ver docs/legacy/recon-clientes.md):
- Elegir UN solo archivo fuente por empresa (el snapshot más nuevo); el árbol
  legacy tiene espejos y snapshots repetidos del mismo comercio.
- Los registros con flag de borrado del DBF NO se migran.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("ENV_FILE", str(BACKEND / ".env.local"))

from dbfread import DBF  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.core.cuit import solo_digitos, validar_cuit  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Cliente,
    CondicionVenta,
    Entidad,
    EntidadContacto,
    Provincia,
    Tenant,
    Zona,
)

# ---------------------------------------------------------------------------
# Constantes calibradas con el reconocimiento de datos reales (ver
# docs/legacy/recon-clientes.md). Ajustables por línea de comandos.
# ---------------------------------------------------------------------------

# cp850 uniforme: los 18 CLIENTES.DBF reales tienen LDID 0x02 y sus bytes
# altos decodifican español válido solo con cp850 (recon 2026-07-03).
ENCODING_DEFAULT = "cp850"

# REGCLI (condición IVA del cliente en el legacy) -> condicion_iva ZGC.
# Evidencia triple (recon 2026-07-03): libro IVA del legacy (_ADMINC guarda
# código + texto: 1='R.Inscript', 3='C.Final', 4='Exento', 6='Monotribut'),
# cruce REGCLI×LETRA sobre ~326.000 comprobantes (1->100% A; 3/4/6->100% B),
# y perfil de CUIT. 2 y 5 son categorías AFIP abolidas sin ocurrencias:
# 2='Resp. No Inscripto' (recibía A) -> RI; 5='No Responsable' -> CF.
MAPEO_REGCLI = {
    1: "RI",
    2: "RI",
    3: "CF",
    4: "EX",
    5: "CF",
    6: "MT",
}
REGCLI_FALLBACK = "CF"  # vacío/None = cliente mostrador (100% ventas B)

# PROVCLI es texto libre C(15); mapeo de valores observados -> nombre ARCA.
MAPEO_PROVINCIAS = {
    "buenos aires": "Buenos Aires",
    "bs as": "Buenos Aires",
    "bs.as.": "Buenos Aires",
    "bsas": "Buenos Aires",
    "bs. as.": "Buenos Aires",
    "pcia bs as": "Buenos Aires",
    "gba": "Buenos Aires",
    "capital": "CABA",
    "cap fed": "CABA",
    "cap. fed.": "CABA",
    "capital fed": "CABA",
    "capital federal": "CABA",
    "caba": "CABA",
    "cordoba": "Córdoba",
    "santa fe": "Santa Fe",
    "sta fe": "Santa Fe",
    "sta. fe": "Santa Fe",
    "entre rios": "Entre Ríos",
    "corrientes": "Corrientes",
    "misiones": "Misiones",
    "chaco": "Chaco",
    "formosa": "Formosa",
    "jujuy": "Jujuy",
    "salta": "Salta",
    "tucuman": "Tucumán",
    "catamarca": "Catamarca",
    "la rioja": "La Rioja",
    "santiago": "Santiago del Estero",
    "sgo del estero": "Santiago del Estero",
    "santiago del e": "Santiago del Estero",
    "san juan": "San Juan",
    "san luis": "San Luis",
    "mendoza": "Mendoza",
    "neuquen": "Neuquén",
    "la pampa": "La Pampa",
    "rio negro": "Río Negro",
    "chubut": "Chubut",
    "santa cruz": "Santa Cruz",
    "tierra del fuego": "Tierra del Fuego",
    "t del fuego": "Tierra del Fuego",
    "buenos iares": "Buenos Aires",  # typo real observado en los datos
}

SOCIEDAD_RE = re.compile(
    r"\b(S\.?\s?R\.?\s?L|S\.?\s?A\.?|S\.?\s?H\.?|S\.?A\.?S|S\.?C\.?A|SOC|COOP|CIA|COMPAÑIA)\b\.?",
    re.IGNORECASE,
)


def normalizar_texto(valor) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    return s or None


def sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def clave_provincia(valor: str) -> str:
    return re.sub(r"\s+", " ", sin_acentos(valor).lower().strip())


def email_valido(valor: str | None) -> bool:
    if not valor:
        return False
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", valor.strip()))


def inferir_tipo_persona(cuit: str | None, razon_social: str) -> str:
    if cuit and cuit[:2] in ("30", "33", "34"):
        return "J"
    if cuit and cuit[:2] in ("20", "23", "24", "27"):
        return "F"
    return "J" if SOCIEDAD_RE.search(razon_social) else "F"


class Transformado:
    """Resultado de transformar un registro legacy: entidad + rol + avisos."""

    def __init__(self, codigo, entidad, cliente, contacto, avisos):
        self.codigo = codigo
        self.entidad = entidad
        self.cliente = cliente
        self.contacto = contacto
        self.avisos = avisos


def transformar_registro(rec: dict, provincias_por_nombre: dict[str, int]) -> Transformado | None:
    avisos: list[str] = []
    codigo = normalizar_texto(rec.get("CODCLI"))
    if codigo and len(codigo) > 10:
        avisos.append(f"CODCLI '{codigo}' excede 10 caracteres -> truncado")
        codigo = codigo[:10]
    nombre = normalizar_texto(rec.get("NOMCLI"))
    if not nombre:
        return None  # registro sin razón social: no migrable

    # --- documento ---
    cuit = solo_digitos(normalizar_texto(rec.get("CUITCLI")) or "")
    dni_raw = rec.get("DNI")
    if isinstance(dni_raw, (int, float)):
        dni = solo_digitos(str(int(dni_raw)))
    else:
        dni = solo_digitos(str(dni_raw)) if dni_raw else ""
    tipo_doc, nro_doc = "SD", None
    if cuit:
        if validar_cuit(cuit):
            tipo_doc, nro_doc = "CUIT", cuit
        else:
            avisos.append(f"CUIT inválido '{rec.get('CUITCLI')}' -> queda SD (se anota en observaciones)")
    if tipo_doc == "SD" and dni and 6 <= len(dni) <= 8:
        tipo_doc, nro_doc = "DNI", dni

    # --- condición IVA ---
    regcli = rec.get("REGCLI")
    try:
        regcli = int(regcli) if regcli is not None else None
    except (TypeError, ValueError):
        regcli = None
    condicion_iva = MAPEO_REGCLI.get(regcli, REGCLI_FALLBACK)
    if regcli is not None and regcli not in MAPEO_REGCLI:
        avisos.append(f"REGCLI={regcli} sin mapeo -> {REGCLI_FALLBACK}")
    # coherencia: RI requiere CUIT válido
    if condicion_iva == "RI" and tipo_doc != "CUIT":
        avisos.append("REGCLI=RI pero sin CUIT válido -> condicion_iva CF")
        condicion_iva = "CF"

    # --- provincia ---
    provincia_id = None
    prov_txt = normalizar_texto(rec.get("PROVCLI"))
    if prov_txt:
        nombre_arca = MAPEO_PROVINCIAS.get(clave_provincia(prov_txt))
        if nombre_arca:
            provincia_id = provincias_por_nombre.get(nombre_arca)
        else:
            avisos.append(f"Provincia no mapeada: '{prov_txt}'")

    # --- contacto / email / observaciones ---
    email = normalizar_texto(rec.get("E_MAIL"))
    if email and not email_valido(email):
        avisos.append(f"Email inválido '{email}' -> a observaciones")
        email = None

    obs_partes = []
    memo = normalizar_texto(rec.get("OBSERVAC"))
    if memo:
        obs_partes.append(memo)
    # != "CUIT" (no == "SD"): si el fallback DNI tomó el documento, la nota
    # del CUIT ilegible igual debe quedar (hallazgo verificación 2026-07-03)
    if cuit and tipo_doc != "CUIT":
        obs_partes.append(f"[migración] CUIT legacy inválido: {rec.get('CUITCLI')}")
    email_crudo = normalizar_texto(rec.get("E_MAIL"))
    if email_crudo and email is None and email_crudo.lower() != "false":
        obs_partes.append(f"[migración] email legacy: {email_crudo}")
    fax = normalizar_texto(rec.get("FAX"))
    if fax:
        obs_partes.append(f"[migración] fax legacy: {fax}")
    calific = normalizar_texto(rec.get("CALIFIC"))
    if calific:
        obs_partes.append(f"[migración] calificación legacy: {calific}")
    # vendedor y transporte: los roles llegan en fases posteriores del
    # roadmap; mientras tanto el dato queda trazable en observaciones
    cviaj = normalizar_texto(rec.get("CVIAJ"))
    if cviaj:
        obs_partes.append(f"[migración] vendedor legacy: {cviaj}")
    ctransp = normalizar_texto(rec.get("CTRANSP"))
    if ctransp:
        obs_partes.append(f"[migración] transporte legacy: {ctransp}")

    entidad = dict(
        tipo_persona=inferir_tipo_persona(nro_doc if tipo_doc == "CUIT" else None, nombre),
        razon_social=nombre[:120],
        tipo_documento=tipo_doc,
        nro_documento=nro_doc,
        condicion_iva=condicion_iva,
        email=email,
        telefono_1=normalizar_texto(rec.get("TELCLI_1")),
        telefono_2=normalizar_texto(rec.get("TELCLI_2")),
        domicilio=normalizar_texto(rec.get("DOMCLI")),
        localidad=normalizar_texto(rec.get("LOCCLI")),
        provincia_id=provincia_id,
        codigo_postal=normalizar_texto(rec.get("CODPOS")),
        observaciones="\n".join(obs_partes) or None,
    )

    lista = rec.get("LISTAPRE")
    try:
        lista = int(lista)
    except (TypeError, ValueError):
        lista = 1
    if not 1 <= lista <= 4:
        if lista != 0:
            avisos.append(f"LISTAPRE={lista} fuera de rango -> 1")
        lista = 1

    bloqueado_raw = rec.get("BLOQUEADO")
    try:
        bloqueado = bool(int(bloqueado_raw)) if bloqueado_raw is not None else False
    except (TypeError, ValueError):
        avisos.append(f"BLOQUEADO='{bloqueado_raw}' no numérico -> False")
        bloqueado = False

    cliente = dict(
        codigo=codigo,  # ya truncado a 10 al inicio (misma clave para idempotencia)
        lista_precios=lista,
        descuento=rec.get("DESCUENTO") or 0,
        # CRED_MAX=0 en el legacy = "sin límite definido" -> NULL (en Omni el
        # 100% es 0.0; ninguna base observada usa 0 como "sin crédito")
        limite_credito=rec.get("CRED_MAX") or None,
        bloqueado=bloqueado,
        _zona=normalizar_texto(rec.get("ZONA")),
        _ccond=normalizar_texto(rec.get("CCOND")),
    )

    contacto = normalizar_texto(rec.get("CONTACTO"))
    return Transformado(codigo, entidad, cliente, contacto, avisos)


def leer_dbf(path: Path, encoding: str) -> list[dict]:
    tabla = DBF(str(path), encoding=encoding, ignore_missing_memofile=True, char_decode_errors="replace")
    return [dict(r) for r in tabla]


def leer_condiciones_venta(carpeta: Path, encoding: str) -> list[dict]:
    """CONVTA.DBF: CCOND C(2), DESCOND C(26), DIAS_1..DIAS_12 N(3).

    Semántica de los días (recon 2026-07-03): blank (None) = slot sin usar;
    un 0 inicial o intermedio ANTES del último valor >0 es un vencimiento
    real a 0 días (ej. '0, 30, 60'); los 0/blank posteriores se descartan.
    Sin ningún valor >0 (Contado, Tarjeta) => [0].
    """
    path = next((p for p in carpeta.iterdir() if p.name.lower() == "convta.dbf"), None)
    if path is None:
        return []
    registros = leer_dbf(path, encoding)
    # CONVTA puede estar en cp1252 aunque CLIENTES sea cp850 ('Días' se lee
    # 'DÝas' con cp850). Si aparecen esos artefactos, releer en cp1252.
    if any("Ý" in (normalizar_texto(r.get("DESCOND")) or "") for r in registros):
        registros = leer_dbf(path, "cp1252")

    condiciones = []
    for rec in registros:
        codigo = normalizar_texto(rec.get("CCOND"))
        descripcion = normalizar_texto(rec.get("DESCOND")) or (f"Condición {codigo}" if codigo else None)
        if not codigo or not descripcion:
            continue
        valores = []
        for i in range(1, 13):
            v = rec.get(f"DIAS_{i}")
            try:
                valores.append(int(v) if v is not None else None)
            except (TypeError, ValueError):
                valores.append(None)
        ultimo_positivo = max((i for i, v in enumerate(valores) if v and v > 0), default=-1)
        dias = [v for v in valores[: ultimo_positivo + 1] if v is not None]
        condiciones.append({"codigo": codigo, "descripcion": descripcion[:60], "dias": dias or [0]})
    return condiciones


async def migrar(args) -> dict:
    carpeta = Path(args.carpeta).resolve()
    dbf_clientes = next((p for p in carpeta.iterdir() if p.name.lower() == "clientes.dbf"), None)
    if dbf_clientes is None:
        sys.exit(f"No se encontró CLIENTES.DBF en {carpeta}")

    registros = leer_dbf(dbf_clientes, args.encoding)
    if args.limite is not None:
        registros = registros[: args.limite]
    condiciones_legacy = leer_condiciones_venta(carpeta, args.encoding)

    reporte = {
        "carpeta": str(carpeta),
        "encoding": args.encoding,
        "aplicado": bool(args.aplicar),
        "leidos": len(registros),
        "migrados": 0,
        "salteados_existentes": 0,
        "sin_nombre": 0,
        "documentos_duplicados_legacy": 0,
        "condiciones_venta_creadas": 0,
        "zonas_creadas": 0,
        "contactos_creados": 0,
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

        # --- catálogos: condiciones de venta y zonas ---
        # Dedupe por descripción: en el legacy hay códigos distintos con la
        # misma DESCOND (Oricam: 12/13/14 = '1 Días') y la tabla nueva tiene
        # unique(tenant, descripcion) — todos apuntan a la misma condición.
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

        zonas_por_codigo: dict[str, Zona] = {
            z.nombre: z for z in (await db.scalars(select(Zona).where(Zona.tenant_id == tenant.id))).all()
        }

        # --- idempotencia (3 claves; ver verificación adversarial 2026-07-03) ---
        # 1) por código de cliente ya migrado
        codigos_existentes = set(
            (await db.scalars(select(Cliente.codigo).where(Cliente.tenant_id == tenant.id))).all()
        )
        # 2) por documento: precargar los ya persistidos del tenant. Sin esto,
        #    un CUIT duplicado del legacy que cruza tandas (re-run parcial u
        #    otro snapshot) revienta uq_entidades_doc y ataca el tenant
        #    (bug reproducido con --limite 100 + re-run).
        docs_vistos: dict[tuple[str, str], str] = {}  # (tipo, nro) -> codigo que lo tomó
        filas_docs = await db.execute(
            select(Entidad.tipo_documento, Entidad.nro_documento, Cliente.codigo)
            .join(Cliente, Cliente.entidad_id == Entidad.id)
            .where(Entidad.tenant_id == tenant.id, Entidad.nro_documento.is_not(None))
        )
        for tipo_doc_db, nro_doc_db, cod_db in filas_docs:
            docs_vistos[(tipo_doc_db, nro_doc_db)] = cod_db or "?"
        # 3) registros sin CODCLI: clave alternativa best-effort
        #    (razón social + documento + domicilio) para no reduplicarlos
        sin_codigo_existentes: set[tuple] = {
            (rs.lower(), nro, (dom or "").lower())
            for rs, nro, dom in (
                await db.execute(
                    select(Entidad.razon_social, Entidad.nro_documento, Entidad.domicilio)
                    .join(Cliente, Cliente.entidad_id == Entidad.id)
                    .where(Cliente.tenant_id == tenant.id, Cliente.codigo.is_(None))
                )
            ).all()
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
                # dos formas: con el doc original y sin doc (por si en la
                # corrida anterior el dedupe de documento lo degradó a SD)
                if (rs, t.entidad["nro_documento"], dom) in sin_codigo_existentes or (
                    (rs, None, dom) in sin_codigo_existentes
                ):
                    reporte["salteados_existentes"] += 1
                    continue
                reporte["avisos"].append(
                    f"[? {t.entidad['razon_social']}] sin CODCLI: idempotencia best-effort "
                    "por razón social+documento+domicilio"
                )

            # BUE: el documento es único por tenant. Si dos clientes legacy
            # comparten CUIT (sucursales), el primero se lleva el documento y
            # los siguientes quedan SD con nota (siguen siendo clientes distintos).
            if t.entidad["nro_documento"]:
                clave = (t.entidad["tipo_documento"], t.entidad["nro_documento"])
                if clave in docs_vistos:
                    reporte["documentos_duplicados_legacy"] += 1
                    nota = (
                        f"[migración] documento {clave[0]} {clave[1]} compartido con "
                        f"cliente legacy {docs_vistos[clave]}"
                    )
                    t.entidad["observaciones"] = (
                        (t.entidad["observaciones"] + "\n" + nota) if t.entidad["observaciones"] else nota
                    )
                    t.entidad["tipo_documento"], t.entidad["nro_documento"] = "SD", None
                    if t.entidad["condicion_iva"] == "RI":
                        t.entidad["condicion_iva"] = "CF"
                else:
                    docs_vistos[clave] = t.codigo or "?"

            for aviso in t.avisos:
                reporte["avisos"].append(f"[{t.codigo or '?'} {t.entidad['razon_social']}] {aviso}")

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

            zona_id = None
            if t.cliente["_zona"]:
                z = zonas_por_codigo.get(t.cliente["_zona"])
                if z is None:
                    z = Zona(tenant_id=tenant.id, nombre=t.cliente["_zona"])
                    db.add(z)
                    await db.flush()
                    zonas_por_codigo[t.cliente["_zona"]] = z
                    reporte["zonas_creadas"] += 1
                zona_id = z.id

            cond = cond_por_codigo.get(t.cliente["_ccond"]) if t.cliente["_ccond"] else None
            datos_cliente = {k: v for k, v in t.cliente.items() if not k.startswith("_")}
            cliente = Cliente(
                tenant_id=tenant.id,
                entidad_id=entidad.id,
                zona_id=zona_id,
                condicion_venta_id=cond.id if cond else None,
                **datos_cliente,
            )
            db.add(cliente)

            if t.contacto:
                db.add(
                    EntidadContacto(tenant_id=tenant.id, entidad_id=entidad.id, nombre=t.contacto[:80])
                )
                reporte["contactos_creados"] += 1

            if t.codigo:
                codigos_existentes.add(t.codigo)
            else:
                sin_codigo_existentes.add(
                    (
                        t.entidad["razon_social"].lower(),
                        t.entidad["nro_documento"],  # ya post-dedupe de documento
                        (t.entidad["domicilio"] or "").lower(),
                    )
                )
            reporte["migrados"] += 1

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
    parser = argparse.ArgumentParser(description="Migra CLIENTES.DBF de RevoSolution a la BUE de ZGC")
    parser.add_argument("--carpeta", required=True, help="Carpeta del backup legacy con CLIENTES.DBF")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--tenant-id", help="UUID del tenant destino existente")
    grupo.add_argument("--crear-tenant", help="Crear un tenant nuevo con esta razón social")
    parser.add_argument("--aplicar", action="store_true", help="Escribe en la DB (sin esto: dry-run)")
    parser.add_argument("--encoding", default=ENCODING_DEFAULT)
    parser.add_argument("--limite", type=int, default=None, help="Procesar solo N registros (pruebas)")
    args = parser.parse_args()

    # la consola de Windows es cp1252: los datos legacy pueden traer chars
    # que no existen ahí y tumbarían el print DESPUÉS del commit
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    reporte = asyncio.run(migrar(args))

    # el JSON se escribe ANTES de imprimir: si algo falla en consola,
    # el reporte ya está a salvo
    salida = Path(__file__).parent / "reportes"
    salida.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = salida / f"migracion-clientes-{stamp}.json"
    out.write_text(json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")

    if reporte.get("error"):
        modo = "FALLIDA (abortada de forma atómica)"
    elif reporte["aplicado"]:
        modo = "APLICADO"
    else:
        modo = "DRY-RUN (no se escribió nada)"
    print(f"\n===== MIGRACIÓN DE CLIENTES — {modo} =====")
    if reporte.get("error"):
        print(f"  ERROR: {reporte['error']}")
    for k in (
        "carpeta", "tenant", "tenant_id", "encoding", "leidos", "migrados",
        "salteados_existentes", "sin_nombre", "documentos_duplicados_legacy",
        "condiciones_venta_creadas", "zonas_creadas", "contactos_creados",
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
