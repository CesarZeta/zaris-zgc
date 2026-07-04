r"""
Migrador de artículos y stock RevoSolution -> ZGC (Fase 2).

Lee de la carpeta del backup legacy: ARTICULO.DBF (maestro), familias.DBF y
SUBFLIA.DBF (catálogos), DEPOSITO.DBF y stock.DBF (saldos/mínimos/ubicación).
Idempotente: los artículos ya migrados (mismo código) se saltean; las filas de
stock solo se crean si no existen para (artículo, depósito).

Uso:
    cd backend
    $env:ENV_FILE=".env.local"
    .venv\Scripts\python.exe ..\tools\migrar_articulos.py `
        --carpeta "..\Revosolution Software\USB Pendrive Revosolution\Super Backups\Super" `
        --crear-tenant "Super (prueba)" [--aplicar] [--limite 100]

Sin --aplicar hace un dry-run: transforma y reporta, no escribe nada.

Calibrado con recon de datos reales (Super, 12.208 artículos — 2026-07-04):
- Encoding por LDID del header DBF (byte 29): los ARTICULO/DEPOSITO reales son
  0x03 (cp1252), a diferencia de CLIENTES.DBF (0x02, cp850). --encoding fuerza.
- COSTIVA es 1/2, NO booleano: 1 = costo con IVA (7 casos), 2 = sin IVA (12.201).
- UNIDAD viene sucia ('0', '1', '', '11'): solo se migran valores con letras.
- Los precios se copian LITERALES (UTIL_x/PVENTA_x tal cual): el 99% de los
  artículos tiene precio sin costo — recalcular pisaría los precios reales.
- NSUBF placeholder 'No hay subfamilias definidas' => sin subfamilia.
- MARCA en ARTICULO es C(1), un flag de selección del legacy — no hay marcas
  que migrar (MARCA.DBF es otra cosa: un reporte de cta. cte.).
- stock.DBF puede ser una matriz artículo×depósito llena de ceros (Super:
  127.480 filas, 0 saldos): solo se migran filas con saldo, mínimo o ubicación.
- Se difieren con nota en observaciones: proveedor (CPROV/NOMPROV/CODPROVE,
  Fase 4), unidad de compra (UNICOMP/COEFICIENT), bonificaciones (BONIF_xx),
  cuenta contable (CUENTA).
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("ENV_FILE", str(BACKEND / ".env.local"))

from dbfread import DBF  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Articulo,
    ArticuloStock,
    Deposito,
    Familia,
    StockMovimiento,
    Subfamilia,
    Tenant,
    Unidad,
)

# LDID (byte 29 del header DBF) -> codec. Fallback: --encoding (default cp850,
# el de los CLIENTES.DBF reales).
LDID_ENCODINGS = {
    0x01: "cp437",
    0x02: "cp850",
    0x03: "cp1252",
    0x57: "cp1252",
    0x64: "cp852",
    0x65: "cp866",
    0xC8: "cp1250",
}

SUBF_PLACEHOLDER = "no hay subfamilias definidas"
TIENE_LETRAS = re.compile(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]")


def txt(valor) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    return s or None


def encoding_de(path: Path, forzado: str | None, fallback: str) -> str:
    if forzado:
        return forzado
    with open(path, "rb") as f:
        header = f.read(30)
    return LDID_ENCODINGS.get(header[29], fallback) if len(header) >= 30 else fallback


def leer_dbf(path: Path, forzado: str | None, fallback: str) -> list[dict]:
    enc = encoding_de(path, forzado, fallback)
    tabla = DBF(str(path), encoding=enc, ignore_missing_memofile=True, char_decode_errors="replace")
    return [dict(r) for r in tabla]  # dbfread saltea los registros borrados


def buscar_archivo(carpeta: Path, nombre: str) -> Path | None:
    return next((p for p in carpeta.iterdir() if p.name.lower() == nombre.lower()), None)


def num(valor, defecto=0) -> Decimal:
    if valor is None:
        return Decimal(defecto)
    try:
        return Decimal(str(valor))
    except Exception:
        return Decimal(defecto)


def transformar_articulo(rec: dict) -> tuple[dict | None, list[str]]:
    """Devuelve (datos, avisos); datos=None si el registro no es migrable.
    Claves con _ son resoluciones pendientes (catálogos, envase)."""
    avisos: list[str] = []
    codigo = txt(rec.get("CODART"))
    descripcion = txt(rec.get("DESART"))
    if not codigo or not descripcion:
        return None, avisos

    familia = txt(rec.get("FAMILIA"))
    subfamilia = txt(rec.get("NSUBF"))
    if subfamilia and subfamilia.lower() == SUBF_PLACEHOLDER:
        subfamilia = None
    if subfamilia and not familia:
        avisos.append(f"subfamilia '{subfamilia}' sin familia -> descartada")
        subfamilia = None

    unidad = (txt(rec.get("UNIDAD")) or "").upper()
    if unidad and not TIENE_LETRAS.search(unidad):
        unidad = ""  # basura numérica observada en datos reales ('0', '1', '11')

    try:
        costo_con_iva = int(rec.get("COSTIVA") or 2) == 1
    except (TypeError, ValueError):
        costo_con_iva = False

    tasa = rec.get("TASA")
    tasa_iva = num(tasa, 21) if tasa is not None else Decimal(21)

    ult_prc = rec.get("ULT_PRC")
    precio_actualizado = (
        datetime.combine(ult_prc, time.min, tzinfo=timezone.utc)
        if isinstance(ult_prc, date)
        else None
    )

    # trazabilidad de campos diferidos a fases posteriores
    obs_partes = []
    nota = txt(rec.get("NOTA"))
    if nota:
        obs_partes.append(nota)
    prov = " ".join(p for p in (txt(rec.get("CPROV")), txt(rec.get("NOMPROV"))) if p)
    if prov:
        obs_partes.append(f"[migración] proveedor legacy: {prov}")
    codprove = txt(rec.get("CODPROVE"))
    if codprove:
        obs_partes.append(f"[migración] código de proveedor legacy: {codprove}")
    unicomp = txt(rec.get("UNICOMP"))
    coef = num(rec.get("COEFICIENT"), 1)
    if unicomp and TIENE_LETRAS.search(unicomp.upper()) and unicomp.upper() != unidad:
        obs_partes.append(f"[migración] unidad de compra legacy: {unicomp} (coef. {coef})")
    bonifs = {
        f"BONIF_{i}{j}": num(rec.get(f"BONIF_{i}{j}"))
        for i in (1, 2, 3, 4)
        for j in (1, 2)
    }
    if any(v != 0 for v in bonifs.values()):
        detalle = ", ".join(f"{k}={v}" for k, v in bonifs.items() if v != 0)
        obs_partes.append(f"[migración] bonificaciones legacy: {detalle}")
    cuenta = txt(rec.get("CUENTA"))
    if cuenta:
        obs_partes.append(f"[migración] cuenta contable legacy: {cuenta}")

    datos = dict(
        codigo=codigo[:20],
        codigo_barras=(txt(rec.get("CBARRA")) or None),
        descripcion=descripcion[:80],
        controla_stock=bool(rec.get("STOCK")) if rec.get("STOCK") is not None else True,
        costo=num(rec.get("COSTO")),
        costo_con_iva=costo_con_iva,
        tasa_iva=tasa_iva,
        utilidad_1=num(rec.get("UTIL_1")),
        utilidad_2=num(rec.get("UTIL_2")),
        utilidad_3=num(rec.get("UTIL_3")),
        utilidad_4=num(rec.get("UTIL_4")),
        precio_1=num(rec.get("PVENTA_1")),
        precio_2=num(rec.get("PVENTA_2")),
        precio_3=num(rec.get("PVENTA_3")),
        precio_4=num(rec.get("PVENTA_4")),
        en_dolares=bool(rec.get("EN_DOLARES")),
        impuesto_interno=num(rec.get("IMP_INT")),
        pesable=bool(rec.get("PESABLE")),
        venta_por_depto=bool(rec.get("VENTAXDEPT")),
        es_envase_retornable=bool(rec.get("DEVOLUCION")),
        precio_actualizado_at=precio_actualizado,
        observaciones="\n".join(obs_partes) or None,
        _familia=familia,
        _subfamilia=subfamilia,
        _unidad=unidad[:6] or None,
        _envase=txt(rec.get("ENVASE")),
    )
    if datos["codigo_barras"]:
        datos["codigo_barras"] = datos["codigo_barras"][:20]
    return datos, avisos


async def migrar(args) -> dict:
    carpeta = Path(args.carpeta).resolve()
    dbf_articulo = buscar_archivo(carpeta, "articulo.dbf")
    if dbf_articulo is None:
        sys.exit(f"No se encontró ARTICULO.DBF en {carpeta}")

    registros = leer_dbf(dbf_articulo, args.encoding, args.encoding_fallback)
    if args.limite is not None:
        registros = registros[: args.limite]

    reporte = {
        "carpeta": str(carpeta),
        "aplicado": bool(args.aplicar),
        "leidos": len(registros),
        "migrados": 0,
        "salteados_existentes": 0,
        "sin_codigo_o_descripcion": 0,
        "cbarra_duplicados": 0,
        "familias_creadas": 0,
        "subfamilias_creadas": 0,
        "unidades_creadas": 0,
        "depositos_creados": 0,
        "stock_filas_creadas": 0,
        "movimientos_iniciales": 0,
        "stock_huerfano": 0,
        "envases_vinculados": 0,
        "avisos": [],
    }

    async with SessionLocal() as db:
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

        # --- catálogos: familias y subfamilias (del DBF de catálogo + on-the-fly) ---
        familias: dict[str, Familia] = {
            f.nombre: f
            for f in (await db.scalars(select(Familia).where(Familia.tenant_id == tenant.id))).all()
        }
        subfamilias: dict[tuple[str, str], Subfamilia] = {}
        for s, f in (
            await db.execute(
                select(Subfamilia, Familia)
                .join(Familia, Subfamilia.familia_id == Familia.id)
                .where(Subfamilia.tenant_id == tenant.id)
            )
        ).all():
            subfamilias[(f.nombre, s.nombre)] = s

        async def familia_de(nombre: str | None) -> Familia | None:
            if not nombre:
                return None
            clave = nombre[:40]
            if clave not in familias:
                f = Familia(tenant_id=tenant.id, nombre=clave)
                db.add(f)
                await db.flush()
                familias[clave] = f
                reporte["familias_creadas"] += 1
            return familias[clave]

        async def subfamilia_de(familia: Familia | None, nombre: str | None) -> Subfamilia | None:
            if familia is None or not nombre:
                return None
            clave = (familia.nombre, nombre[:40])
            if clave not in subfamilias:
                s = Subfamilia(tenant_id=tenant.id, familia_id=familia.id, nombre=nombre[:40])
                db.add(s)
                await db.flush()
                subfamilias[clave] = s
                reporte["subfamilias_creadas"] += 1
            return subfamilias[clave]

        dbf_familias = buscar_archivo(carpeta, "familias.dbf")
        if dbf_familias:
            for rec in leer_dbf(dbf_familias, args.encoding, args.encoding_fallback):
                await familia_de(txt(rec.get("NFAMILIA")))
        dbf_subflia = buscar_archivo(carpeta, "subflia.dbf")
        if dbf_subflia:
            for rec in leer_dbf(dbf_subflia, args.encoding, args.encoding_fallback):
                f = await familia_de(txt(rec.get("NFAMILIA")))
                await subfamilia_de(f, txt(rec.get("NSUBF")))

        # --- unidades ---
        unidades: dict[str, Unidad] = {
            u.codigo: u
            for u in (await db.scalars(select(Unidad).where(Unidad.tenant_id == tenant.id))).all()
        }

        async def unidad_de(codigo: str | None) -> Unidad | None:
            if not codigo:
                return None
            if codigo not in unidades:
                u = Unidad(tenant_id=tenant.id, codigo=codigo, nombre=codigo)
                db.add(u)
                await db.flush()
                unidades[codigo] = u
                reporte["unidades_creadas"] += 1
            return unidades[codigo]

        # --- depósitos: solo los que tienen nombre; el resto on-demand ---
        depositos: dict[str, Deposito] = {
            d.codigo: d
            for d in (await db.scalars(select(Deposito).where(Deposito.tenant_id == tenant.id))).all()
        }

        async def deposito_de(cdep: str, nombre: str | None = None) -> Deposito:
            if cdep not in depositos:
                d = Deposito(
                    tenant_id=tenant.id,
                    codigo=cdep[:4],
                    nombre=(nombre or f"Depósito {cdep}")[:40],
                )
                db.add(d)
                await db.flush()
                depositos[cdep] = d
                reporte["depositos_creados"] += 1
            return depositos[cdep]

        dbf_deposito = buscar_archivo(carpeta, "deposito.dbf")
        if dbf_deposito:
            for rec in leer_dbf(dbf_deposito, args.encoding, args.encoding_fallback):
                cdep, ndep = txt(rec.get("CDEP")), txt(rec.get("NDEP"))
                if cdep and ndep:  # los depósitos sin nombre del legacy son slots vacíos
                    await deposito_de(cdep, ndep)

        # --- idempotencia y unicidad de código de barras ---
        codigos_existentes = set(
            (await db.scalars(select(Articulo.codigo).where(Articulo.tenant_id == tenant.id))).all()
        )
        cbarras_vistos = set(
            (
                await db.scalars(
                    select(Articulo.codigo_barras).where(
                        Articulo.tenant_id == tenant.id, Articulo.codigo_barras.is_not(None)
                    )
                )
            ).all()
        )

        articulos_por_codigo: dict[str, Articulo] = {}
        pendientes_envase: list[tuple[Articulo, str]] = []
        registro_actual = "?"

        for rec in registros:
            datos, avisos = transformar_articulo(rec)
            if datos is None:
                reporte["sin_codigo_o_descripcion"] += 1
                continue
            registro_actual = f"{datos['codigo']} {datos['descripcion']}"
            for a in avisos:
                reporte["avisos"].append(f"[{datos['codigo']}] {a}")
            if datos["codigo"] in codigos_existentes:
                reporte["salteados_existentes"] += 1
                continue
            codigos_existentes.add(datos["codigo"])

            if datos["codigo_barras"]:
                if datos["codigo_barras"] in cbarras_vistos:
                    reporte["cbarra_duplicados"] += 1
                    reporte["avisos"].append(
                        f"[{datos['codigo']}] código de barras {datos['codigo_barras']} "
                        "duplicado -> queda sin código de barras"
                    )
                    datos["codigo_barras"] = None
                else:
                    cbarras_vistos.add(datos["codigo_barras"])

            familia = await familia_de(datos.pop("_familia"))
            subfamilia = await subfamilia_de(familia, datos.pop("_subfamilia"))
            unidad = await unidad_de(datos.pop("_unidad"))
            envase = datos.pop("_envase")

            articulo = Articulo(
                tenant_id=tenant.id,
                familia_id=familia.id if familia else None,
                subfamilia_id=subfamilia.id if subfamilia else None,
                unidad_id=unidad.id if unidad else None,
                **datos,
            )
            db.add(articulo)
            articulos_por_codigo[datos["codigo"]] = articulo
            if envase:
                pendientes_envase.append((articulo, envase))
            reporte["migrados"] += 1

        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            reporte["error"] = (
                f"Unicidad violada al insertar '{registro_actual}': {exc.orig}. "
                "Corrida abortada de forma atómica: no se escribió nada."
            )
            return reporte

        # --- segunda pasada: vincular envases (ENVASE = CODART del envase) ---
        for articulo, cod_envase in pendientes_envase:
            destino = articulos_por_codigo.get(cod_envase[:20])
            if destino is None:
                destino = await db.scalar(
                    select(Articulo).where(
                        Articulo.tenant_id == tenant.id, Articulo.codigo == cod_envase[:20]
                    )
                )
            if destino is None:
                reporte["avisos"].append(
                    f"[{articulo.codigo}] envase '{cod_envase}' no existe -> sin vincular"
                )
            else:
                articulo.envase_articulo_id = destino.id
                reporte["envases_vinculados"] += 1

        # --- stock: solo filas con contenido real (saldo, mínimo o ubicación) ---
        dbf_stock = buscar_archivo(carpeta, "stock.dbf")
        if dbf_stock:
            stock_existente = {
                (st.articulo_id, st.deposito_id)
                for st in (
                    await db.scalars(
                        select(ArticuloStock).where(ArticuloStock.tenant_id == tenant.id)
                    )
                ).all()
            }
            for rec in leer_dbf(dbf_stock, args.encoding, args.encoding_fallback):
                saldo = num(rec.get("SALDO"))
                minimo = num(rec.get("MINIMO"))
                ubicacion = txt(rec.get("UBICACION"))
                if saldo == 0 and minimo == 0 and not ubicacion:
                    continue
                codart = txt(rec.get("CODART"))
                cdep = txt(rec.get("CDEP"))
                if not codart or not cdep:
                    continue
                articulo = articulos_por_codigo.get(codart[:20])
                if articulo is None:
                    articulo = await db.scalar(
                        select(Articulo).where(
                            Articulo.tenant_id == tenant.id, Articulo.codigo == codart[:20]
                        )
                    )
                if articulo is None:
                    reporte["stock_huerfano"] += 1
                    continue
                deposito = await deposito_de(cdep)
                if (articulo.id, deposito.id) in stock_existente:
                    continue
                stock_existente.add((articulo.id, deposito.id))
                db.add(
                    ArticuloStock(
                        tenant_id=tenant.id,
                        articulo_id=articulo.id,
                        deposito_id=deposito.id,
                        cantidad=saldo,
                        stock_minimo=minimo,
                        ubicacion=ubicacion[:20] if ubicacion else None,
                    )
                )
                reporte["stock_filas_creadas"] += 1
                if saldo != 0:
                    fsaldo = rec.get("FSALDO")
                    fecha = (
                        datetime.combine(fsaldo, time.min, tzinfo=timezone.utc)
                        if isinstance(fsaldo, date)
                        else datetime.now(timezone.utc)
                    )
                    db.add(
                        StockMovimiento(
                            tenant_id=tenant.id,
                            articulo_id=articulo.id,
                            deposito_id=deposito.id,
                            fecha=fecha,
                            tipo="inicial",
                            cantidad=saldo,
                            saldo_resultante=saldo,
                            comprobante="migración",
                            observaciones="Saldo inicial migrado del legacy (stock.DBF)",
                        )
                    )
                    reporte["movimientos_iniciales"] += 1

        try:
            if args.aplicar:
                await db.commit()
            else:
                await db.rollback()
        except IntegrityError as exc:
            await db.rollback()
            reporte["error"] = f"Unicidad violada al confirmar: {exc.orig}"

    return reporte


def main():
    parser = argparse.ArgumentParser(
        description="Migra ARTICULO.DBF + familias + stock de RevoSolution a ZGC"
    )
    parser.add_argument("--carpeta", required=True, help="Carpeta del backup legacy con ARTICULO.DBF")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--tenant-id", help="UUID del tenant destino existente")
    grupo.add_argument("--crear-tenant", help="Crear un tenant nuevo con esta razón social")
    parser.add_argument("--aplicar", action="store_true", help="Escribe en la DB (sin esto: dry-run)")
    parser.add_argument(
        "--encoding", default=None, help="Forzar codec (default: autodetección por LDID)"
    )
    parser.add_argument("--encoding-fallback", default="cp850", help="Codec si el LDID es desconocido")
    parser.add_argument("--limite", type=int, default=None, help="Procesar solo N registros (pruebas)")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    reporte = asyncio.run(migrar(args))

    salida = Path(__file__).parent / "reportes"
    salida.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = salida / f"migracion-articulos-{stamp}.json"
    out.write_text(json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")

    if reporte.get("error"):
        modo = "FALLIDA (abortada de forma atómica)"
    elif reporte["aplicado"]:
        modo = "APLICADO"
    else:
        modo = "DRY-RUN (no se escribió nada)"
    print(f"\n===== MIGRACIÓN DE ARTÍCULOS — {modo} =====")
    if reporte.get("error"):
        print(f"  ERROR: {reporte['error']}")
    for k in (
        "carpeta", "tenant", "tenant_id", "leidos", "migrados", "salteados_existentes",
        "sin_codigo_o_descripcion", "cbarra_duplicados", "familias_creadas",
        "subfamilias_creadas", "unidades_creadas", "depositos_creados",
        "stock_filas_creadas", "movimientos_iniciales", "stock_huerfano",
        "envases_vinculados",
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
