"""Validación de CUIT/CUIL/DNI (dígito verificador ARCA)."""

import re


def solo_digitos(valor: str | None) -> str:
    return re.sub(r"\D", "", valor or "")


def validar_cuit(cuit: str) -> bool:
    """DV módulo 11 con pesos 5,4,3,2,7,6,5,4,3,2. Acepta con o sin guiones."""
    c = solo_digitos(cuit)
    if len(c) != 11:
        return False
    pesos = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    resto = sum(int(d) * p for d, p in zip(c[:10], pesos)) % 11
    dv = 11 - resto
    if dv == 11:
        dv = 0
    elif dv == 10:
        return False
    return dv == int(c[10])


def validar_documento(tipo: str, numero: str | None) -> str | None:
    """Normaliza a dígitos y valida según tipo. Devuelve el número normalizado.

    Lanza ValueError si es inválido.
    """
    if tipo == "SD":
        return None
    n = solo_digitos(numero)
    if tipo in ("CUIT", "CUIL"):
        if not validar_cuit(n):
            raise ValueError(f"{tipo} inválido (dígito verificador no coincide)")
        return n
    if tipo == "DNI":
        if not (6 <= len(n) <= 8):
            raise ValueError("DNI inválido (se esperan 6 a 8 dígitos)")
        return n
    raise ValueError(f"Tipo de documento desconocido: {tipo}")
