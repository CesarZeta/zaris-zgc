"""Padrón ARCA — consulta de constancia de inscripción por CUIT (Fase 7).

Quick win del motor fiscal (ROADMAP F7): dado un CUIT, trae razón social,
condición frente a IVA y domicilio fiscal para autocompletar la entidad BUE
y validar la condición que el usuario eligió.

WS de ARCA: `ws_sr_constancia_inscripcion` (padrón A5 unificado). El emisor
consulta con SU propio certificado (el mismo de WSFEv1); el TA se pide para
el servicio `ws_sr_constancia_inscripcion` (WSAA ya es multi-servicio).

Modos (espejo de emision.py):
- deshabilitado / simulado: no hay llamada real. Simulado devuelve un registro
  ficticio derivado del CUIT (para dev/demo sin certificado) marcado `simulado`.
- homologacion / produccion: WSAA + SOAP real al padrón.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cuit import solo_digitos, validar_documento
from app.models import ArcaConfig, ArcaToken
from app.services.arca import wsaa

SERVICIO = "ws_sr_constancia_inscripcion"

URLS_PADRON = {
    "homologacion": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5",
    "produccion": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5",
}
_NS = "http://a5.soap.ws.server.puc.sr/"

# Mapeo de la descripción de provincia del padrón al código ARCA del catálogo.
_PROVINCIAS_ARCA = {
    "CIUDAD AUTONOMA BUENOS AIRES": 0, "CAPITAL FEDERAL": 0, "CABA": 0,
    "BUENOS AIRES": 1, "CATAMARCA": 2, "CORDOBA": 3, "CORRIENTES": 4,
    "ENTRE RIOS": 5, "JUJUY": 6, "MENDOZA": 7, "LA RIOJA": 8, "SALTA": 9,
    "SAN JUAN": 10, "SAN LUIS": 11, "SANTA FE": 12, "SANTIAGO DEL ESTERO": 13,
    "TUCUMAN": 14, "CHACO": 16, "CHUBUT": 17, "FORMOSA": 18, "MISIONES": 19,
    "NEUQUEN": 20, "LA PAMPA": 21, "RIO NEGRO": 22, "SANTA CRUZ": 23,
    "TIERRA DEL FUEGO": 24,
}


class ErrorPadron(Exception):
    """Consulta imposible o configuración incompleta — el mensaje va al usuario."""


@dataclass
class DatosPadron:
    cuit: str
    razon_social: str | None
    tipo_persona: str            # 'F' física · 'J' jurídica
    condicion_iva: str           # RI · MT · EX · CF (mapeada)
    domicilio: str | None
    localidad: str | None
    provincia_id: int | None
    codigo_postal: str | None
    fuente: str                  # 'padron' · 'simulado'


def _provincia_arca(descripcion: str | None) -> int | None:
    if not descripcion:
        return None
    return _PROVINCIAS_ARCA.get(descripcion.strip().upper())


def _mapear_condicion(impuestos_iva: bool, monotributo: bool, exento: bool) -> str:
    if monotributo:
        return "MT"
    if exento:
        return "EX"
    if impuestos_iva:
        return "RI"
    return "CF"


async def _ta_vigente(db: AsyncSession, config: ArcaConfig) -> tuple[str, str]:
    """TA cacheado por tenant/modo para el servicio de padrón."""
    ahora = datetime.now(timezone.utc)
    fila = await db.scalar(
        select(ArcaToken).where(
            ArcaToken.tenant_id == config.tenant_id,
            ArcaToken.servicio == SERVICIO,
            ArcaToken.modo == config.modo,
        )
    )
    if fila is not None and fila.expira > ahora + timedelta(minutes=30):
        return fila.token, fila.sign
    ta = await wsaa.solicitar_ta(config.modo, config.cert_pem, config.key_pem, SERVICIO)
    if fila is None:
        fila = ArcaToken(
            tenant_id=config.tenant_id, servicio=SERVICIO, modo=config.modo,
            token=ta["token"], sign=ta["sign"], expira=ta["expira"],
        )
        db.add(fila)
    else:
        fila.token, fila.sign, fila.expira = ta["token"], ta["sign"], ta["expira"]
    await db.flush()
    return ta["token"], ta["sign"]


def _parsear_persona(raiz: ET.Element, cuit: str) -> DatosPadron:
    def txt(camino: str) -> str | None:
        for nodo in raiz.iter():
            if nodo.tag.endswith(camino):
                return (nodo.text or "").strip() or None
        return None

    razon = txt("razonSocial")
    if not razon:
        nombre = txt("nombre")
        apellido = txt("apellido")
        razon = " ".join(p for p in (apellido, nombre) if p) or None

    tipo_persona = "J" if (txt("tipoPersona") or "").upper().startswith("JU") else "F"

    # impuestos activos: IVA (id 30) ⇒ RI; monotributo trae categoría
    impuestos = {(n.text or "").strip() for n in raiz.iter() if n.tag.endswith("idImpuesto")}
    tiene_iva = "30" in impuestos or "32" in impuestos
    monotributo = any(n.tag.endswith("categoriaMonotributo") for n in raiz.iter()) or "20" in impuestos
    exento = "32" in impuestos and not tiene_iva
    condicion = _mapear_condicion(tiene_iva, monotributo, exento)

    return DatosPadron(
        cuit=cuit,
        razon_social=razon,
        tipo_persona=tipo_persona,
        condicion_iva=condicion,
        domicilio=txt("direccion"),
        localidad=txt("localidad"),
        provincia_id=_provincia_arca(txt("descripcionProvincia")),
        codigo_postal=txt("codPostal"),
        fuente="padron",
    )


def _simulado(cuit: str) -> DatosPadron:
    """Registro ficticio determinístico (dev/demo sin certificado)."""
    return DatosPadron(
        cuit=cuit,
        razon_social=f"CONTRIBUYENTE SIMULADO {cuit}",
        tipo_persona="J" if cuit.startswith(("30", "33", "34")) else "F",
        condicion_iva="RI",
        domicilio=None,
        localidad=None,
        provincia_id=None,
        codigo_postal=None,
        fuente="simulado",
    )


async def consultar_cuit(db: AsyncSession, config: ArcaConfig | None, cuit_raw: str) -> DatosPadron:
    # valida CUIT/CUIL con dígito verificador (reusa el core fiscal)
    cuit = validar_documento("CUIT", solo_digitos(cuit_raw))

    if config is None or config.modo == "deshabilitado":
        raise ErrorPadron(
            "Padrón ARCA no disponible: configurá el modo (simulado para probar) "
            "en Configuración → ARCA."
        )
    if config.modo == "simulado":
        return _simulado(cuit)

    if not (config.cuit and config.cert_pem and config.key_pem):
        raise ErrorPadron("Config ARCA incompleta: falta CUIT, certificado o clave privada.")

    token, sign = await _ta_vigente(db, config)
    cuerpo = (
        f'<a5:getPersona_v2 xmlns:a5="{_NS}">'
        f"<token>{token}</token><sign>{sign}</sign>"
        f"<cuitRepresentada>{config.cuit}</cuitRepresentada>"
        f"<idPersona>{cuit}</idPersona>"
        "</a5:getPersona_v2>"
    )
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<soapenv:Body>{cuerpo}</soapenv:Body></soapenv:Envelope>"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                URLS_PADRON[config.modo],
                content=envelope.encode(),
                headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
            )
    except httpx.HTTPError:
        raise ErrorPadron("No se pudo contactar al padrón de ARCA (reintentá en unos minutos).")
    if resp.status_code != 200:
        raise ErrorPadron(f"Padrón ARCA respondió HTTP {resp.status_code}.")
    raiz = ET.fromstring(resp.text)
    if any(n.tag.endswith("Fault") for n in raiz.iter()):
        detalle = next((n.text for n in raiz.iter() if n.tag.endswith("faultstring")), "")
        raise ErrorPadron(f"Padrón ARCA: {detalle or 'sin datos para ese CUIT'}")
    if not any(n.tag.endswith("persona") for n in raiz.iter()):
        raise ErrorPadron("El CUIT no figura en el padrón de ARCA.")
    return _parsear_persona(raiz, cuit)
