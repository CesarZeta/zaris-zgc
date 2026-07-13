"""Fachada de emisión fiscal por modo (FACTURACION-ARCA.md §8).

- simulado: CAE ficticio 99999999999999 marcado 'S' — para desarrollo/demo;
  la impresión sale con "COMPROBANTE NO VÁLIDO — PRUEBA" y sin QR.
- homologacion / produccion: WSAA (TA cacheado en arca_tokens) + WSFEv1.
  La numeración la manda ARCA: FECompUltimoAutorizado + 1.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import ArcaConfig, ArcaToken, Comprobante
from app.services.arca import wsaa, wsfev1
from app.services.ventas import COND_IVA_RECEPTOR_ID

CAE_SIMULADO = "99999999999999"


class ErrorArca(Exception):
    """Rechazo de ARCA o configuración incompleta — el mensaje va al usuario."""


class ErrorConexionArca(Exception):
    """ARCA inalcanzable (red caída / timeout de transporte) — distinto de un
    rechazo: en la nube es un 502; en el NODO habilita el CAE diferido
    (F13-LAN N2, DISENO-NODO-LAN.md §6): el comprobante sale emitido con su
    numeración local y el CAE se solicita al reconectar."""


@dataclass
class ResultadoEmision:
    numero: int
    cae: str
    cae_vencimiento: date
    resultado: str          # 'A' aprobado real · 'S' simulado
    observaciones: str
    request_xml: str | None
    response_xml: str | None


def _validar_config(config: ArcaConfig | None, modo_requerido: bool) -> None:
    if config is None or config.modo == "deshabilitado":
        raise ErrorArca(
            "Facturación electrónica no configurada para esta empresa "
            "(Configuración → ARCA). Configurá el modo simulado para probar."
        )
    if config.modo in ("homologacion", "produccion"):
        faltan = [
            campo
            for campo, valor in (
                ("CUIT", config.cuit),
                ("certificado", config.cert_pem),
                ("clave privada", config.key_pem),
            )
            if not valor
        ]
        if faltan:
            raise ErrorArca(f"Config ARCA incompleta: falta {', '.join(faltan)}")


async def _ta_vigente(db: AsyncSession, config: ArcaConfig) -> tuple[str, str]:
    """TA cacheado por tenant/servicio/modo; renueva si faltan <30 min."""
    ahora = datetime.now(timezone.utc)
    fila = await db.scalar(
        select(ArcaToken).where(
            ArcaToken.tenant_id == config.tenant_id,
            ArcaToken.servicio == "wsfe",
            ArcaToken.modo == config.modo,
        )
    )
    if fila is not None and fila.expira > ahora + timedelta(minutes=30):
        return fila.token, fila.sign

    ta = await wsaa.solicitar_ta(config.modo, config.cert_pem, config.key_pem, "wsfe")
    if fila is None:
        fila = ArcaToken(
            tenant_id=config.tenant_id,
            servicio="wsfe",
            modo=config.modo,
            token=ta["token"],
            sign=ta["sign"],
            expira=ta["expira"],
        )
        db.add(fila)
    else:
        fila.token, fila.sign, fila.expira = ta["token"], ta["sign"], ta["expira"]
    await db.flush()
    return ta["token"], ta["sign"]


async def emitir_fiscal(
    db: AsyncSession,
    comp: Comprobante,
    config: ArcaConfig | None,
    numero_local_siguiente: int,
    asociado: Comprobante | None,
) -> ResultadoEmision:
    """Autoriza el comprobante fiscal según el modo. NO commitea: el caller
    persiste todo junto (comprobante + stock + numeración) en una transacción."""
    _validar_config(config, True)

    # Hook de prueba (suite del nodo): simula ARCA caída sin tocar la red.
    # Jamás se setea en prod — default False, solo vía env del proceso de test.
    if settings.ARCA_SIMULAR_CAIDA:
        raise ErrorConexionArca("simulación de caída de ARCA (ARCA_SIMULAR_CAIDA)")

    if config.modo == "simulado":
        return ResultadoEmision(
            numero=numero_local_siguiente,
            cae=CAE_SIMULADO,
            cae_vencimiento=comp.fecha + timedelta(days=10),
            resultado="S",
            observaciones="MODO SIMULADO — comprobante SIN validez fiscal",
            request_xml=None,
            response_xml=None,
        )

    tipo_arca = comp.tipo.codigo_arca
    pv = comp.punto_venta.numero
    try:
        token, sign = await _ta_vigente(db, config)
        ultimo = await wsfev1.ultimo_autorizado(
            config.modo, token, sign, config.cuit, pv, tipo_arca
        )
    except httpx.TransportError as e:
        # red caída ANTES de enviar nada: no hay comprobante en juego en ARCA
        raise ErrorConexionArca(str(e) or type(e).__name__)
    numero = ultimo + 1

    asociados = []
    if asociado is not None:
        asociados.append(
            {
                "tipo_arca": asociado.tipo.codigo_arca,
                "punto_venta": asociado.punto_venta.numero,
                "numero": asociado.numero,
            }
        )
    datos = wsfev1.DatosComprobante(
        punto_venta=pv,
        tipo_arca=tipo_arca,
        concepto=config.concepto,
        doc_tipo=comp.receptor_doc_tipo,
        doc_nro=int(comp.receptor_doc_nro or 0),
        numero=numero,
        fecha=comp.fecha,
        total=str(comp.total),
        neto=str(comp.neto_gravado),
        no_gravado=str(comp.neto_no_gravado),
        exento=str(comp.exento),
        iva=str(comp.iva),
        tributos=str(comp.otros_tributos),
        moneda=comp.moneda,
        cotizacion=str(comp.cotizacion if comp.moneda != "PES" else Decimal("1")),
        condicion_iva_receptor_id=COND_IVA_RECEPTOR_ID[comp.receptor_condicion_iva],
        alicuotas=[
            {"codigo_arca": a.codigo_arca, "base": str(a.base), "importe": str(a.importe)}
            for a in comp.alicuotas
        ],
        asociados=asociados,
    )
    try:
        resp = await wsfev1.solicitar_cae(config.modo, token, sign, config.cuit, datos)
    except (wsfev1.ErrorWsfe, httpx.TransportError) as e:
        # Timeout/corte DESPUÉS de enviar: consultar si ARCA lo autorizó igual
        # antes de que el usuario reintente (idempotencia, §5 del diseño).
        try:
            recuperado = await wsfev1.consultar_comprobante(
                config.modo, token, sign, config.cuit, pv, tipo_arca, numero
            )
        except httpx.TransportError:
            recuperado = None
        if recuperado is None:
            if isinstance(e, httpx.TransportError):
                raise ErrorConexionArca(str(e) or type(e).__name__)
            raise
        resp = recuperado

    if resp.resultado == "R" or not resp.cae:
        raise ErrorArca(f"ARCA rechazó el comprobante: {resp.observaciones or 'sin detalle'}")

    return ResultadoEmision(
        numero=numero,
        cae=resp.cae,
        cae_vencimiento=resp.cae_vencimiento or comp.fecha + timedelta(days=10),
        resultado=resp.resultado,
        observaciones=resp.observaciones,
        request_xml=resp.request_xml,
        response_xml=resp.response_xml,
    )
