"""WSAA — autenticación de web services ARCA (docs/FACTURACION-ARCA.md §9).

Flujo estándar: TRA (XML con uniqueId y vigencia) → firma CMS/PKCS#7 con el
certificado del contribuyente → loginCms → TA (token + sign, vigencia 12 h).
El TA se cachea por tenant/servicio/modo en arca_tokens (lo maneja emision.py).

Cliente propio con httpx + cryptography: mismos protocolos que pyafipws
(implementación de referencia), sin sus dependencias legacy.
"""

import base64
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509 import load_pem_x509_certificate

URLS_WSAA = {
    "homologacion": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
    "produccion": "https://wsaa.afip.gov.ar/ws/services/LoginCms",
}


class ErrorWsaa(Exception):
    pass


def _armar_tra(servicio: str, ttl_horas: int = 12) -> bytes:
    ahora = datetime.now(timezone.utc)
    gen = (ahora - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    exp = (ahora + timedelta(hours=ttl_horas)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    unique = uuid.uuid4().int % 4_000_000_000
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<loginTicketRequest version="1.0">'
        f"<header><uniqueId>{unique}</uniqueId>"
        f"<generationTime>{gen}</generationTime>"
        f"<expirationTime>{exp}</expirationTime></header>"
        f"<service>{servicio}</service>"
        "</loginTicketRequest>"
    ).encode()


def _firmar_cms(tra: bytes, cert_pem: str, key_pem: str) -> str:
    cert = load_pem_x509_certificate(cert_pem.encode())
    key = serialization.load_pem_private_key(key_pem.encode(), password=None)
    cms = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(tra)
        .add_signer(cert, key, hashes.SHA256())
        .sign(serialization.Encoding.DER, [])
    )
    return base64.b64encode(cms).decode()


async def solicitar_ta(
    modo: str, cert_pem: str, key_pem: str, servicio: str = "wsfe"
) -> dict:
    """Devuelve {token, sign, expira: datetime} pidiendo un TA nuevo al WSAA."""
    cms_b64 = _firmar_cms(_armar_tra(servicio), cert_pem, key_pem)
    envelope = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">'
        "<soapenv:Header/><soapenv:Body>"
        f"<wsaa:loginCms><wsaa:in0>{cms_b64}</wsaa:in0></wsaa:loginCms>"
        "</soapenv:Body></soapenv:Envelope>"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            URLS_WSAA[modo],
            content=envelope.encode(),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
        )
    cuerpo = resp.text
    if resp.status_code != 200:
        # el fault de WSAA viene como XML; extraer faultstring si está
        detalle = cuerpo
        try:
            fault = ET.fromstring(cuerpo).find(".//faultstring")
            if fault is not None:
                detalle = fault.text or cuerpo
        except ET.ParseError:
            pass
        raise ErrorWsaa(f"WSAA rechazó el login ({resp.status_code}): {detalle[:400]}")

    raiz = ET.fromstring(cuerpo)
    retorno = raiz.find(".//{http://wsaa.view.sua.dvadac.desein.afip.gov}loginCmsReturn")
    if retorno is None or not retorno.text:
        raise ErrorWsaa("WSAA no devolvió loginCmsReturn")
    ta = ET.fromstring(retorno.text)
    token = ta.findtext(".//token")
    sign = ta.findtext(".//sign")
    expira_txt = ta.findtext(".//expirationTime")
    if not token or not sign or not expira_txt:
        raise ErrorWsaa("TA incompleto (sin token/sign/expirationTime)")
    expira = datetime.fromisoformat(expira_txt)
    return {"token": token, "sign": sign, "expira": expira}
