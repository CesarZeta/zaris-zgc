"""Réplica de bajada del NODO de sucursal (F13-LAN N1 — perfil `nodo`).

Corre solo con `PERFIL=nodo`: un task de polling baja los maestros de la nube
(handshake con el token de aparejamiento → /sync/bajada por tabla) y los
upsertea en la base local. Idempotente por construcción (upsert por PK) y
tolerante a cortes: si la nube no responde, el ciclo falla entero y se
reintenta en el próximo intervalo — el POS local sigue operando con lo último
replicado.

La poda de snapshots corre en orden INVERSO al de upsert (FK-safe) y las
tablas `inicial` (stock, numeración) se siembran UNA vez: después el nodo es
autoridad local y reaplicarlas pisaría su avance.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import ArcaConfig, Comprobante, PosCaja, SyncCheckpoint, TipoComprobante
from app.services.arca import ErrorArca, ErrorConexionArca, emitir_fiscal
from app.services.sync_tablas import (
    TABLAS_SUBIDA,
    TABLAS_SYNC,
    TablaSubida,
    TablaSync,
    columnas,
    fila_a_python,
    pk_columnas,
    serializar_fila,
)

log = logging.getLogger("zgc.sync_nodo")

VERSION_APP = "n2.0"
PAGINA = 500
LOTE_SUBIDA = 200
# tope defensivo para la poda por NOT IN (si una tabla snapshot creciera tanto,
# antes hay que moverla a incremental — se loguea y no se poda)
PODA_MAX_IDS = 20_000

_lock = asyncio.Lock()
estado_sync: dict = {
    "ciclos_ok": 0,
    "ultimo_ok": None,
    "ultimo_error": None,
    "contexto": None,  # cache de la fila '_nodo' de sync_checkpoints
}


async def _guardar_checkpoint(
    db: AsyncSession,
    tabla: str,
    hasta: datetime | None,
    filas: int,
    extra: dict | None = None,
) -> None:
    ins = pg_insert(SyncCheckpoint.__table__).values(
        tabla=tabla, hasta=hasta, filas=filas, extra=extra,
        actualizado_at=datetime.now(timezone.utc),
    )
    await db.execute(
        ins.on_conflict_do_update(
            index_elements=["tabla"],
            set_={
                "hasta": ins.excluded.hasta,
                "filas": ins.excluded.filas,
                "extra": ins.excluded.extra,
                "actualizado_at": ins.excluded.actualizado_at,
            },
        )
    )


async def contexto_nodo(db: AsyncSession) -> dict | None:
    """Contexto del aparejamiento (fila '_nodo'): sucursal y PV propio.
    Sobrevive reinicios offline (se persiste en cada handshake exitoso)."""
    if estado_sync["contexto"] is not None:
        return estado_sync["contexto"]
    cp = await db.get(SyncCheckpoint, "_nodo")
    if cp is not None and cp.extra:
        estado_sync["contexto"] = cp.extra
    return estado_sync["contexto"]


async def pvs_del_nodo(db: AsyncSession) -> set[uuid.UUID] | None:
    """PVs con los que este nodo puede emitir: su PV propio (§0-bis) + los de
    las cajas POS activas de su sucursal. None = sin contexto todavía (nodo
    nunca sincronizó): no se puede emitir nada con garantía de numeración."""
    ctx = await contexto_nodo(db)
    if ctx is None:
        return None
    pvs: set[uuid.UUID] = set()
    if ctx.get("punto_venta_id"):
        pvs.add(uuid.UUID(ctx["punto_venta_id"]))
    if ctx.get("sucursal_id"):
        cajas = await db.scalars(
            select(PosCaja.punto_venta_id).where(
                PosCaja.sucursal_id == uuid.UUID(ctx["sucursal_id"]),
                PosCaja.activa.is_(True),
            )
        )
        pvs.update(cajas.all())
    return pvs


def _pk_valor(t: TablaSync, fila_py: dict):
    pks = pk_columnas(t.modelo)
    if len(pks) == 1:
        return fila_py[pks[0]]
    return tuple(fila_py[k] for k in pks)


async def _upsert(db: AsyncSession, t: TablaSync, filas_py: list[dict]) -> None:
    tabla = t.modelo.__table__
    pks = pk_columnas(t.modelo)
    ins = pg_insert(tabla).values(filas_py)
    await db.execute(
        ins.on_conflict_do_update(
            index_elements=pks,
            set_={c: ins.excluded[c] for c in filas_py[0] if c not in pks},
        )
    )


async def _podar(db: AsyncSession, t: TablaSync, ids: list, tenant_id: uuid.UUID) -> None:
    if t.nombre == "tenants":  # una sola fila y sin hard-delete posible
        return
    if len(ids) > PODA_MAX_IDS:
        log.warning("poda de %s salteada: %s ids (> %s)", t.nombre, len(ids), PODA_MAX_IDS)
        return
    tabla = t.modelo.__table__
    pks = pk_columnas(t.modelo)
    stmt = delete(tabla)
    if not t.es_global:
        stmt = stmt.where(tabla.c.tenant_id == tenant_id)
    if ids:
        if len(pks) == 1:
            stmt = stmt.where(tabla.c[pks[0]].notin_(ids))
        else:
            stmt = stmt.where(tuple_(*(tabla.c[k] for k in pks)).notin_(ids))
    await db.execute(stmt)


# ===== CAE diferido (N2 — DISENO-NODO-LAN.md §6) =====

_FILTRO_CAE_PENDIENTE = (
    Comprobante.estado == "emitido",
    Comprobante.cae.is_(None),
    # NULL = nunca respondió ARCA; 'R' = rechazado (queda visible, no reintenta)
    Comprobante.arca_resultado.is_(None),
    TipoComprobante.fiscal.is_(True),
)


def _stmt_cae_pendientes():
    return (
        select(Comprobante)
        .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
        .where(*_FILTRO_CAE_PENDIENTE)
    )


async def contar_cae_pendientes(db: AsyncSession) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(Comprobante)
            .join(TipoComprobante, Comprobante.tipo_codigo == TipoComprobante.codigo)
            .where(*_FILTRO_CAE_PENDIENTE)
        )
    ) or 0


async def resolver_cae_pendientes() -> tuple[int, int]:
    """Pide el CAE de los comprobantes emitidos offline, en ORDEN de numeración
    por PV/tipo (WSFEv1 exige secuencia; el PV exclusivo del nodo garantiza el
    hueco). Devuelve (resueltos, pendientes_restantes). No depende de la nube:
    solo de ARCA — corre ANTES del handshake en cada ciclo."""
    resueltos = 0
    async with SessionLocal() as db:
        pendientes = (
            await db.scalars(
                _stmt_cae_pendientes().order_by(
                    Comprobante.punto_venta_id, Comprobante.tipo_codigo, Comprobante.numero
                )
            )
        ).all()
        if not pendientes:
            return 0, 0
        config = await db.scalar(
            select(ArcaConfig).where(ArcaConfig.tenant_id == pendientes[0].tenant_id)
        )
        for comp in pendientes:
            asociado = None
            if comp.comprobante_asociado_id is not None:
                asociado = await db.scalar(
                    select(Comprobante).where(Comprobante.id == comp.comprobante_asociado_id)
                )
            try:
                resultado = await emitir_fiscal(db, comp, config, comp.numero, asociado)
            except ErrorConexionArca:
                break  # ARCA sigue inalcanzable: se reintenta el próximo ciclo
            except ErrorArca as e:
                # rechazo REAL de un comprobante ya impreso: se marca y queda
                # visible en el monitoreo — resolución manual (no reintenta)
                comp.arca_resultado = "R"
                comp.arca_observaciones = f"CAE diferido RECHAZADO por ARCA: {e}"
                await db.commit()
                log.error("CAE diferido rechazado (%s %s): %s", comp.tipo_codigo, comp.numero, e)
                continue
            if resultado.numero != comp.numero:
                # con PV exclusivo no debería pasar: alguien más numeró en ARCA
                comp.arca_resultado = "R"
                comp.arca_observaciones = (
                    f"CAE diferido: ARCA esperaba el número {resultado.numero} y el "
                    f"local es {comp.numero} — requiere revisión manual"
                )
                await db.commit()
                log.error("CAE diferido: desfasaje de numeración en %s", comp.id)
                continue
            comp.cae = resultado.cae
            comp.cae_vencimiento = resultado.cae_vencimiento
            comp.arca_resultado = resultado.resultado
            comp.arca_observaciones = resultado.observaciones or None
            comp.arca_request = resultado.request_xml
            comp.arca_response = resultado.response_xml
            await db.commit()  # el trigger bumpea updated_at ⇒ re-sube al ciclo
            resueltos += 1
        restantes = await contar_cae_pendientes(db)
    return resueltos, restantes


# ===== Subida nodo → nube (N2, "el origen manda") =====


async def _subir_tabla(
    db: AsyncSession, client: httpx.AsyncClient, headers: dict, t: TablaSubida
) -> int:
    """Empuja las filas nuevas/modificadas de una tabla, paginadas keyset por
    (created_at, id) — orden estable e inmutable, padres antes que hijos en
    los self-FK. El checkpoint avanza recién con TODAS las páginas aceptadas."""
    clave = f"subida:{t.nombre}"
    # select de columna (no db.get): el checkpoint se escribe por Core upsert
    # y el identity map de la sesión NO se entera — db.get devolvería la
    # instancia vieja (bug real cazado por la suite: pendientes fantasma)
    hasta = await db.scalar(
        select(SyncCheckpoint.hasta).where(SyncCheckpoint.tabla == clave)
    )
    cols = columnas(t.modelo)
    col_filtro = cols["updated_at" if t.mutable else "created_at"]
    # keyset inmutable: (created_at, id) — o solo id si la tabla no tiene
    # created_at (numeracion) y el orden padre-antes-que-hijo no aplica
    orden = tuple(c for c in (cols.get("created_at"), cols["id"]) if c is not None)

    stmt = select(t.modelo)
    if hasta is not None:
        # >= y no >: la fila tocada en el mismo instante del checkpoint no se
        # pierde; re-enviar es no-op en la nube (DO NOTHING / LWW)
        stmt = stmt.where(col_filtro >= hasta)
    if t.solo_no_borrador:
        stmt = stmt.where(cols["estado"] != "borrador")
    stmt = stmt.order_by(*orden)

    cursor: tuple | None = None
    maximo = hasta
    filas_total = 0
    while True:
        page = stmt
        if cursor is not None:
            page = page.where(tuple_(*orden) > cursor)
        objetos = (await db.scalars(page.limit(LOTE_SUBIDA))).all()
        if not objetos:
            break
        ids = [o.id for o in objetos]
        hijos_por_tabla: dict[str, dict] = {}
        for nombre_h, modelo_h, fk in t.hijos:
            cols_h = columnas(modelo_h)
            agrupados: dict = {}
            for h in (await db.scalars(select(modelo_h).where(cols_h[fk].in_(ids)))).all():
                agrupados.setdefault(getattr(h, fk), []).append(serializar_fila(modelo_h, h))
            hijos_por_tabla[nombre_h] = agrupados
        entradas = []
        for o in objetos:
            entrada: dict = {"fila": serializar_fila(t.modelo, o, excluir=t.excluir)}
            if t.hijos:
                entrada["hijos"] = {
                    nombre_h: hijos_por_tabla[nombre_h].get(o.id, [])
                    for nombre_h, _m, _f in t.hijos
                }
            entradas.append(entrada)
            valor = getattr(o, col_filtro.key)
            if maximo is None or valor > maximo:
                maximo = valor
        r = await client.post(
            "/api/v1/sync/subida", json={"tabla": t.nombre, "filas": entradas}, headers=headers
        )
        r.raise_for_status()
        filas_total += len(entradas)
        cursor = tuple(getattr(objetos[-1], c.key) for c in orden)
        if len(objetos) < LOTE_SUBIDA:
            break
    await _guardar_checkpoint(db, clave, maximo, filas_total)
    await db.commit()
    return filas_total


async def contar_subida_pendiente(db: AsyncSession) -> int:
    """Filas que todavía no viajaron (estrictamente > checkpoint): el atraso
    que reporta el ping. 0 = al día."""
    total = 0
    for t in TABLAS_SUBIDA:
        hasta = await db.scalar(
            select(SyncCheckpoint.hasta).where(SyncCheckpoint.tabla == f"subida:{t.nombre}")
        )
        cols = columnas(t.modelo)
        col_filtro = cols["updated_at" if t.mutable else "created_at"]
        stmt = select(func.count()).select_from(t.modelo.__table__)
        if hasta is not None:
            stmt = stmt.where(col_filtro > hasta)
        if t.solo_no_borrador:
            stmt = stmt.where(cols["estado"] != "borrador")
        total += (await db.scalar(stmt)) or 0
    return total


async def ciclo_sync() -> dict:
    """Un ciclo completo de réplica. Lanza excepción si la nube no responde o
    rechaza el nodo (revocado ⇒ HTTP 403 en el handshake)."""
    if not (settings.NUBE_URL and settings.NODO_ID and settings.NODO_TOKEN):
        raise RuntimeError("Perfil nodo sin NUBE_URL / NODO_ID / NODO_TOKEN configurados")
    async with _lock:
        # CAE diferido primero: depende de ARCA, no de la nube (si ARCA sigue
        # caída corta solo; los resueltos re-suben en la fase de subida de ESTE
        # mismo ciclo porque el trigger les movió updated_at)
        cae_resueltos, cae_pend = await resolver_cae_pendientes()
        if cae_resueltos:
            log.info("CAE diferido: %s comprobantes autorizados", cae_resueltos)
        async with httpx.AsyncClient(
            base_url=settings.NUBE_URL.rstrip("/"), timeout=60.0
        ) as client:
            r = await client.post(
                "/api/v1/sync/handshake",
                json={
                    "nodo_id": settings.NODO_ID,
                    "token": settings.NODO_TOKEN,
                    "version_app": VERSION_APP,
                },
            )
            if r.status_code >= 400:
                detalle = ""
                try:
                    detalle = r.json().get("detail", "")
                except Exception:
                    pass
                raise RuntimeError(f"Handshake rechazado ({r.status_code}): {detalle}")
            hs = r.json()
            headers = {"Authorization": f"Bearer {hs['access_token']}"}
            tenant_id = uuid.UUID(hs["tenant_id"])
            contexto = {
                "nodo_id": settings.NODO_ID,
                "nodo_nombre": hs["nodo_nombre"],
                "tenant_id": hs["tenant_id"],
                "sucursal_id": hs["sucursal_id"],
                "sucursal_nombre": hs["sucursal_nombre"],
                "punto_venta_id": hs["punto_venta_id"],
                "punto_venta_numero": hs["punto_venta_numero"],
            }
            resumen = {"tablas": 0, "filas": 0}
            podas: list[tuple[TablaSync, list]] = []

            async with SessionLocal() as db:
                await _guardar_checkpoint(db, "_nodo", None, 0, extra=contexto)
                estado_sync["contexto"] = contexto
                checkpoints = {
                    c.tabla: c for c in (await db.scalars(select(SyncCheckpoint))).all()
                }
                for t in TABLAS_SYNC:
                    cp = checkpoints.get(t.nombre)
                    if t.modo == "inicial" and cp is not None:
                        continue  # semilla ya aplicada: el nodo es autoridad local
                    desde = (
                        cp.hasta.isoformat()
                        if (t.modo == "incremental" and cp is not None and cp.hasta)
                        else None
                    )
                    cursor: str | None = None
                    ids: list = []
                    filas_tabla = 0
                    max_updated: datetime | None = cp.hasta if cp is not None else None
                    while True:
                        params: dict = {"limit": PAGINA}
                        if desde:
                            params["desde"] = desde
                        if cursor:
                            params["cursor"] = cursor
                        r = await client.get(
                            f"/api/v1/sync/bajada/{t.nombre}", params=params, headers=headers
                        )
                        r.raise_for_status()
                        data = r.json()
                        filas_py = [fila_a_python(t.modelo, f) for f in data["filas"]]
                        if filas_py:
                            await _upsert(db, t, filas_py)
                            filas_tabla += len(filas_py)
                            if t.modo == "snapshot":
                                ids.extend(_pk_valor(t, f) for f in filas_py)
                            elif t.modo == "incremental":
                                tope = max(f["updated_at"] for f in filas_py)
                                if max_updated is None or tope > max_updated:
                                    max_updated = tope
                        cursor = data["cursor"]
                        if not cursor:
                            break
                    if t.modo == "snapshot":
                        podas.append((t, ids))
                    await _guardar_checkpoint(
                        db,
                        t.nombre,
                        max_updated if t.modo == "incremental" else datetime.now(timezone.utc),
                        filas_tabla,
                    )
                    await db.commit()
                    resumen["tablas"] += 1
                    resumen["filas"] += filas_tabla
                # poda FK-safe: orden inverso al de upsert
                for t, ids in reversed(podas):
                    await _podar(db, t, ids, tenant_id)
                await db.commit()

                # ===== subida (N2): las transacciones del nodo a la nube =====
                resumen["subidas"] = 0
                for ts in TABLAS_SUBIDA:
                    resumen["subidas"] += await _subir_tabla(db, client, headers, ts)
                pend_subida = await contar_subida_pendiente(db)

            await client.post(
                "/api/v1/sync/ping",
                json={
                    **resumen,
                    "version_app": VERSION_APP,
                    "subida_pendientes": pend_subida,
                    "cae_pendientes": cae_pend,
                },
                headers=headers,
            )
            resumen["cae_resueltos"] = cae_resueltos
            resumen["cae_pendientes"] = cae_pend
            return resumen


async def loop_sync() -> None:
    """Task de fondo del perfil nodo: primer ciclo al arrancar (así una
    instalación nueva queda operativa sin esperar), después polling."""
    await asyncio.sleep(2)
    while True:
        try:
            resumen = await ciclo_sync()
            estado_sync["ciclos_ok"] += 1
            estado_sync["ultimo_ok"] = {
                "ts": datetime.now(timezone.utc).isoformat(),
                **resumen,
            }
            estado_sync["ultimo_error"] = None
        except Exception as e:  # corte de internet incluido: se reintenta
            estado_sync["ultimo_error"] = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "error": str(e)[:300],
            }
            log.warning("ciclo de sync falló: %s", e)
        await asyncio.sleep(max(15, settings.SYNC_INTERVALO_SEG))
