"""
Extrae el esquema de todas las tablas DBF del legacy RevoSolution.

Recorre "Revosolution Software/", parsea el encabezado de cada .DBF
(sin dependencias externas: lectura binaria del header xBase/FoxPro),
deduplica por nombre de tabla y genera:

  docs/legacy/esquema-dbf.json  (machine-readable, para la migracion)
  docs/legacy/esquema-dbf.md    (documentacion navegable)

Criterio de canonico por tabla: el archivo con mas registros; a igualdad,
el de fecha de modificacion mas reciente. Se reportan ademas las variantes
de esquema encontradas entre copias (el legacy tuvo varias versiones).
"""

import json
import struct
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LEGACY = RAIZ / "Revosolution Software"
OUT_DIR = RAIZ / "docs" / "legacy"

TIPOS = {
    "C": "Character",
    "N": "Numeric",
    "D": "Date",
    "L": "Logical",
    "M": "Memo",
    "F": "Float",
    "B": "Double",
    "I": "Integer",
    "T": "DateTime",
    "Y": "Currency",
    "G": "General",
    "P": "Picture",
    "V": "Varchar",
    "0": "Flags(_NullFlags)",
}

VERSIONES = {
    0x02: "FoxBASE",
    0x03: "dBASE III/FoxPro sin memo",
    0x30: "Visual FoxPro",
    0x31: "Visual FoxPro autoincrement",
    0x83: "dBASE III con memo (DBT)",
    0x8B: "dBASE IV con memo",
    0xF5: "FoxPro con memo (FPT)",
    0xFB: "FoxBASE con memo",
}


def parsear_dbf(path: Path):
    """Devuelve dict con esquema o None si el archivo no es un DBF valido."""
    try:
        with open(path, "rb") as f:
            header = f.read(32)
            if len(header) < 32:
                return None
            version = header[0]
            n_registros, len_header, len_registro = struct.unpack("<IHH", header[4:12])
            if len_header < 65 or len_header > 65535:
                return None
            campos = []
            # descriptores de campo de 32 bytes hasta el terminador 0x0D
            restante = f.read(len_header - 32)
            for i in range(0, len(restante) - 1, 32):
                bloque = restante[i : i + 32]
                if not bloque or bloque[0] in (0x0D, 0x00):
                    break
                nombre = bloque[:11].split(b"\x00")[0].decode("ascii", "replace").strip()
                tipo = chr(bloque[11])
                longitud = bloque[16]
                decimales = bloque[17]
                if not nombre or tipo not in TIPOS:
                    # descriptor corrupto: abortar este archivo si es el primero
                    if not campos:
                        return None
                    break
                campos.append(
                    {
                        "nombre": nombre,
                        "tipo": tipo,
                        "longitud": longitud,
                        "decimales": decimales,
                    }
                )
            if not campos:
                return None
            return {
                "version": version,
                "registros": n_registros,
                "campos": campos,
            }
    except OSError:
        return None


def firma(campos):
    return tuple((c["nombre"], c["tipo"], c["longitud"], c["decimales"]) for c in campos)


def categoria(nombre: str) -> str:
    n = nombre.upper()
    if n.startswith("_") or n.startswith("AUXI") or n.startswith("AUXM") or n in (
        "AUXART", "CACA", "FALSA", "EQUIS", "MI_EQUIS", "TEMPTEXT", "TEMPVIEW",
        "CONSULTA", "LISTADO", "ZETAS", "C1", "C2", "AMALIA", "FOXUSER",
        "AUXILIO", "AUXILIO1", "AUXILIO2", "AUXILIO3", "AUXILIO4",
    ):
        return "temporal/auxiliar"
    if n.startswith("GV"):
        return "interna (GV)"
    if n.startswith("FE") or n in ("SOL_CAE", "ERR_FE", "F136HIST"):
        return "facturacion electronica"
    return "negocio"


def main():
    if not LEGACY.exists():
        sys.exit(f"No existe {LEGACY}")

    archivos = sorted(LEGACY.rglob("*.dbf")) + sorted(LEGACY.rglob("*.DBF"))
    vistos, unicos = set(), []
    for p in archivos:
        clave = str(p).lower()
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(p)

    por_tabla = defaultdict(list)  # nombre -> [(info, path, mtime)]
    ilegibles = []
    for p in unicos:
        info = parsear_dbf(p)
        if info is None:
            ilegibles.append(str(p.relative_to(RAIZ)))
            continue
        por_tabla[p.stem.upper()].append((info, p, p.stat().st_mtime))

    print(f"DBF encontrados: {len(unicos)} | legibles: {sum(len(v) for v in por_tabla.values())} "
          f"| ilegibles: {len(ilegibles)} | tablas unicas: {len(por_tabla)}")

    resultado = {}
    for nombre, copias in sorted(por_tabla.items()):
        # canonico: mas registros, luego mtime mas reciente
        canon_info, canon_path, canon_mtime = max(
            copias, key=lambda t: (t[0]["registros"], t[2])
        )
        firmas = {}
        for info, p, _ in copias:
            firmas.setdefault(firma(info["campos"]), 0)
            firmas[firma(info["campos"])] += 1
        resultado[nombre] = {
            "categoria": categoria(nombre),
            "copias": len(copias),
            "variantes_esquema": len(firmas),
            "canonico": {
                "ruta": str(canon_path.relative_to(RAIZ)),
                "modificado": datetime.fromtimestamp(canon_mtime).strftime("%Y-%m-%d"),
                "version_dbf": VERSIONES.get(canon_info["version"], f"0x{canon_info['version']:02X}"),
                "registros": canon_info["registros"],
                "campos": canon_info["campos"],
            },
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUT_DIR / "esquema-dbf.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "fuente": str(LEGACY),
                "tablas": resultado,
                "ilegibles": ilegibles,
            },
            f,
            ensure_ascii=False,
            indent=1,
        )

    # ---- Markdown ----
    md = []
    md.append("# Esquema del legacy RevoSolution (tablas DBF)\n")
    md.append(f"Generado el {datetime.now().strftime('%Y-%m-%d')} por `tools/extraer_esquema_dbf.py`. ")
    md.append(f"Se analizaron {len(unicos)} archivos DBF; {len(por_tabla)} tablas únicas. ")
    md.append("Para cada tabla se documenta la copia **canónica** (la de más registros / más reciente).\n")
    md.append("\nTipos: C=Character, N=Numeric, D=Date, L=Logical, M=Memo, F=Float.\n")

    orden_cat = ["negocio", "facturacion electronica", "interna (GV)", "temporal/auxiliar"]
    por_cat = defaultdict(list)
    for nombre, t in resultado.items():
        por_cat[t["categoria"]].append(nombre)

    md.append("\n## Resumen por categoría\n")
    md.append("| Categoría | Tablas |\n|---|---|\n")
    for cat in orden_cat:
        md.append(f"| {cat} | {len(por_cat.get(cat, []))} |\n")

    for cat in orden_cat:
        nombres = sorted(por_cat.get(cat, []))
        if not nombres:
            continue
        md.append(f"\n---\n\n# Categoría: {cat}\n")
        for nombre in nombres:
            t = resultado[nombre]
            c = t["canonico"]
            md.append(f"\n## {nombre}\n")
            md.append(f"- Registros (canónico): **{c['registros']:,}** · copias en el árbol: {t['copias']} · "
                      f"variantes de esquema: {t['variantes_esquema']}\n")
            md.append(f"- Fuente: `{c['ruta']}` (mod. {c['modificado']}, {c['version_dbf']})\n")
            md.append("\n| # | Campo | Tipo | Long | Dec |\n|--:|---|---|--:|--:|\n")
            for i, campo in enumerate(c["campos"], 1):
                md.append(f"| {i} | {campo['nombre']} | {campo['tipo']} | {campo['longitud']} | {campo['decimales']} |\n")

    with open(OUT_DIR / "esquema-dbf.md", "w", encoding="utf-8") as f:
        f.write("".join(md))

    print(f"OK -> {OUT_DIR / 'esquema-dbf.json'}")
    print(f"OK -> {OUT_DIR / 'esquema-dbf.md'}")


if __name__ == "__main__":
    main()
