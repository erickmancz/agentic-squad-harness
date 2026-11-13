"""Regra do resumo da apólice (INS-017): validação do número e projeção dos quatro campos permitidos."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from src.endosso.regras import Apolice

# `fullmatch` evita que "AP-0001\n" passe, o que aconteceria com `$` sozinho (INS-017 CA-04).
_FORMATO = re.compile(r"AP-\d{4}")
_CENTAVOS = Decimal("0.01")


class NumeroInvalido(ValueError):
    """Número de apólice fora do formato AP- mais 4 dígitos."""


class ValorInvalido(ValueError):
    """Valor da base com mais de 2 casas decimais; não é arredondado (INS-017 bloco 8)."""


def numero_valido(numero: str) -> bool:
    """Informa se o número tem o formato AP- seguido de exatamente 4 dígitos."""
    return _FORMATO.fullmatch(numero) is not None


def _checar_duas_casas(valor: Decimal) -> Decimal:
    """Devolve o valor com 2 casas sem arredondar; levanta ValorInvalido se houver mais casas."""
    try:
        ajustado = valor.quantize(_CENTAVOS)
    except InvalidOperation as e:
        raise ValorInvalido("Valor inválido na base.") from e
    if ajustado != valor:
        raise ValorInvalido("Valor com mais de 2 casas decimais.")
    return ajustado


def montar_resumo(apolice: Apolice) -> dict:
    """Projeta só apolice, situacao, cobertura e premio, sem cálculo nem arredondamento."""
    return {
        "apolice": apolice.numero,
        "situacao": "ativa" if apolice.ativa else "inativa",
        "cobertura": _checar_duas_casas(apolice.cobertura),
        "premio": _checar_duas_casas(apolice.premio),
    }
