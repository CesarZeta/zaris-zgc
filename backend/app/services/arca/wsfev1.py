"""WSFEv1 — factura electrónica ARCA (SOAP 1.1 a mano, ver FACTURACION-ARCA.md §5).

Métodos usados: FECompUltimoAutorizado (numeración la manda ARCA),
FECAESolicitar (emisión), FECompConsultar (recuperación ante timeout).
El request/response XML crudos se devuelven para auditoría (se guardan en
comprobantes.arca_request/arca_response).
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date

import httpx

URLS_WSFE = {
    "homologacion": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx",
    "produccion": "https://servicios1.afip.gov.ar/wsfev1/service.asmx",
}
_NS = "http://ar.gov.afip.dif.FEV1/"


class ErrorWsfe(Exception):
    """Error de infraestructura o rechazo del WS (con detalle de ARCA)."""


@dataclass
class RespuestaCae:
    resultado: str                 # 'A' aprobado · 'R' rechazado · 'P' parcial
    cae: str | None
    cae_vencimiento: date | None
    observaciones: str             # códigos+mensajes de Obs/Errors/Events
    request_xml: str
    response_xml: str


@dataclass
class DatosComprobante:
    """Lo que WSFEv1 necesita de un comprobante ZGC ya calculado."""
    punto_venta: int
    tipo_arca: int
    concepto: int
    doc_tipo: int
    doc_nro: int
    numero: int
    fecha: date
    total: str
    neto: str
    no_gravado: str
    exento: str
    iva: str
    tributos: str
    moneda: str
    cotizacion: str
    condicion_iva_receptor_id: int
    alicuotas: list[dict] = field(default_factory=list)   # {codigo_arca, base, importe}
    asociados: list[dict] = field(default_factory=list)   # {tipo_arca, punto_venta, numero}


def _auth_xml(token: str, sign: str, cuit: str) -> str:
    return (
        f"<ar:Auth><ar:Token>{token}</ar:Token><ar:Sign>{sign}</ar:Sign>"
        f"<ar:Cuit>{cuit}</ar:Cuit></ar:Auth>"
    )


def _envelope(cuerpo: str) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:ar="{_NS}">'
        f"<soap:Body>{cuerpo}</soap:Body></soap:Envelope>"
    )


async def _llamar(modo: str, metodo: str, cuerpo: str) -> tuple[str, ET.Element]:
    request_xml = _envelope(cuerpo)
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            URLS_WSFE[modo],
            content=request_xml.encode(),
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f"{_NS}{metodo}",
            },
        )
    if resp.status_code != 200:
        raise ErrorWsfe(f"WSFEv1 {metodo} HTTP {resp.status_code}: {resp.text[:400]}")
    return request_xml, ET.fromstring(resp.text)


def _texto(nodo: ET.Element | None, camino: str) -> str | None:
    if nodo is None:
        return None
    hijo = nodo.find(f".//{{{_NS}}}{camino}")
    return hijo.text if hijo is not None else None


def _mensajes(raiz: ET.Element) -> str:
    """Junta Errors/Obs/Events del response en un texto legible."""
    partes = []
    for etiqueta in ("Err", "Obs", "Evt"):
        for nodo in raiz.iter(f"{{{_NS}}}{etiqueta}"):
            codigo = _texto(nodo, "Code")
            msg = _texto(nodo, "Msg")
            partes.append(f"[{etiqueta} {codigo}] {msg}")
    return " · ".join(partes)


async def ultimo_autorizado(
    modo: str, token: str, sign: str, cuit: str, punto_venta: int, tipo_arca: int
) -> int:
    cuerpo = (
        "<ar:FECompUltimoAutorizado>"
        + _auth_xml(token, sign, cuit)
        + f"<ar:PtoVta>{punto_venta}</ar:PtoVta><ar:CbteTipo>{tipo_arca}</ar:CbteTipo>"
        + "</ar:FECompUltimoAutorizado>"
    )
    _, raiz = await _llamar(modo, "FECompUltimoAutorizado", cuerpo)
    nro = _texto(raiz, "CbteNro")
    if nro is None:
        raise ErrorWsfe(f"FECompUltimoAutorizado sin CbteNro: {_mensajes(raiz)}")
    return int(nro)


async def solicitar_cae(
    modo: str, token: str, sign: str, cuit: str, datos: DatosComprobante
) -> RespuestaCae:
    fecha = datos.fecha.strftime("%Y%m%d")
    alic = "".join(
        f"<ar:AlicIva><ar:Id>{a['codigo_arca']}</ar:Id>"
        f"<ar:BaseImp>{a['base']}</ar:BaseImp><ar:Importe>{a['importe']}</ar:Importe>"
        "</ar:AlicIva>"
        for a in datos.alicuotas
    )
    iva_xml = f"<ar:Iva>{alic}</ar:Iva>" if alic else ""
    asoc = "".join(
        f"<ar:CbteAsoc><ar:Tipo>{a['tipo_arca']}</ar:Tipo>"
        f"<ar:PtoVta>{a['punto_venta']}</ar:PtoVta><ar:Nro>{a['numero']}</ar:Nro>"
        "</ar:CbteAsoc>"
        for a in datos.asociados
    )
    asoc_xml = f"<ar:CbtesAsoc>{asoc}</ar:CbtesAsoc>" if asoc else ""

    detalle = (
        "<ar:FECAEDetRequest>"
        f"<ar:Concepto>{datos.concepto}</ar:Concepto>"
        f"<ar:DocTipo>{datos.doc_tipo}</ar:DocTipo><ar:DocNro>{datos.doc_nro}</ar:DocNro>"
        f"<ar:CbteDesde>{datos.numero}</ar:CbteDesde><ar:CbteHasta>{datos.numero}</ar:CbteHasta>"
        f"<ar:CbteFch>{fecha}</ar:CbteFch>"
        f"<ar:ImpTotal>{datos.total}</ar:ImpTotal>"
        f"<ar:ImpTotConc>{datos.no_gravado}</ar:ImpTotConc>"
        f"<ar:ImpNeto>{datos.neto}</ar:ImpNeto>"
        f"<ar:ImpOpEx>{datos.exento}</ar:ImpOpEx>"
        f"<ar:ImpTrib>{datos.tributos}</ar:ImpTrib>"
        f"<ar:ImpIVA>{datos.iva}</ar:ImpIVA>"
        f"<ar:MonId>{datos.moneda}</ar:MonId><ar:MonCotiz>{datos.cotizacion}</ar:MonCotiz>"
        f"<ar:CondicionIVAReceptorId>{datos.condicion_iva_receptor_id}</ar:CondicionIVAReceptorId>"
        + asoc_xml
        + iva_xml
        + "</ar:FECAEDetRequest>"
    )
    cuerpo = (
        "<ar:FECAESolicitar>"
        + _auth_xml(token, sign, cuit)
        + "<ar:FeCAEReq><ar:FeCabReq>"
        + f"<ar:CantReg>1</ar:CantReg><ar:PtoVta>{datos.punto_venta}</ar:PtoVta>"
        + f"<ar:CbteTipo>{datos.tipo_arca}</ar:CbteTipo></ar:FeCabReq>"
        + f"<ar:FeDetReq>{detalle}</ar:FeDetReq></ar:FeCAEReq>"
        + "</ar:FECAESolicitar>"
    )
    request_xml, raiz = await _llamar(modo, "FECAESolicitar", cuerpo)
    response_xml = ET.tostring(raiz, encoding="unicode")

    resultado = _texto(raiz, "Resultado") or "R"
    cae = None
    vto = None
    det = raiz.find(f".//{{{_NS}}}FECAEDetResponse")
    if det is not None:
        cae = _texto(det, "CAE") or None
        vto_txt = _texto(det, "CAEFchVto")
        if vto_txt and len(vto_txt) == 8:
            vto = date(int(vto_txt[:4]), int(vto_txt[4:6]), int(vto_txt[6:8]))
    return RespuestaCae(
        resultado=resultado,
        cae=cae,
        cae_vencimiento=vto,
        observaciones=_mensajes(raiz),
        request_xml=request_xml,
        response_xml=response_xml,
    )


async def consultar_comprobante(
    modo: str, token: str, sign: str, cuit: str, punto_venta: int, tipo_arca: int, numero: int
) -> RespuestaCae | None:
    """FECompConsultar: recupera un comprobante ya autorizado (idempotencia
    ante timeout — FACTURACION-ARCA.md §5). None si ARCA no lo tiene."""
    cuerpo = (
        "<ar:FECompConsultar>"
        + _auth_xml(token, sign, cuit)
        + "<ar:FeCompConsReq>"
        + f"<ar:CbteTipo>{tipo_arca}</ar:CbteTipo><ar:CbteNro>{numero}</ar:CbteNro>"
        + f"<ar:PtoVta>{punto_venta}</ar:PtoVta>"
        + "</ar:FeCompConsReq></ar:FECompConsultar>"
    )
    request_xml, raiz = await _llamar(modo, "FECompConsultar", cuerpo)
    cae = _texto(raiz, "CodAutorizacion")
    if not cae:
        return None
    vto_txt = _texto(raiz, "FchVto")
    vto = (
        date(int(vto_txt[:4]), int(vto_txt[4:6]), int(vto_txt[6:8]))
        if vto_txt and len(vto_txt) == 8
        else None
    )
    return RespuestaCae(
        resultado="A",
        cae=cae,
        cae_vencimiento=vto,
        observaciones=_mensajes(raiz),
        request_xml=request_xml,
        response_xml=ET.tostring(raiz, encoding="unicode"),
    )
