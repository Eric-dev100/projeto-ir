"""Validação de CPF e CNPJ pelos dígitos verificadores."""
from __future__ import annotations

import re

CPF_RE = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
CNPJ_RE = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")


def somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _dv(numeros: list[int], pesos: list[int]) -> int:
    resto = sum(n * p for n, p in zip(numeros, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(cpf: str) -> bool:
    d = [int(c) for c in somente_digitos(cpf)]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    return _dv(d[:9], list(range(10, 1, -1))) == d[9] and _dv(d[:10], list(range(11, 1, -1))) == d[10]


def cnpj_valido(cnpj: str) -> bool:
    d = [int(c) for c in somente_digitos(cnpj)]
    if len(d) != 14 or len(set(d)) == 1:
        return False
    return (_dv(d[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]) == d[12]
            and _dv(d[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]) == d[13])


def tipo_documento(doc: str) -> str | None:
    n = len(somente_digitos(doc))
    return "cpf" if n == 11 else "cnpj" if n == 14 else None


def documento_valido(doc: str) -> bool:
    tipo = tipo_documento(doc)
    if tipo == "cpf":
        return cpf_valido(doc)
    if tipo == "cnpj":
        return cnpj_valido(doc)
    return False
