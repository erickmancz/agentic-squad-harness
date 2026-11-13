"""Regras de negócio puras do endosso (INS-014 e INS-016). Domínio fictício."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

LIMITE_MULTIPLICADOR = Decimal("2")
CENTAVOS = Decimal("0.01")


class ApoliceInativa(Exception):
    """A apólice não está ativa e não aceita endosso."""


class CoberturaInvalida(Exception):
    """A nova cobertura não respeita as regras do endosso."""


@dataclass(frozen=True)
class Apolice:
    """Apólice fictícia usada na demonstração."""

    numero: str
    cobertura: Decimal
    premio: Decimal
    ativa: bool = True


def validar_nova_cobertura(atual: Decimal, nova: Decimal) -> None:
    """Valida a nova cobertura contra a atual (INS-014 CA-03 e CA-04)."""
    if nova <= atual:
        raise CoberturaInvalida("A nova cobertura precisa ser maior que a atual.")
    if nova > atual * LIMITE_MULTIPLICADOR:
        raise CoberturaInvalida("A nova cobertura não pode passar de 2 vezes a cobertura atual.")


def recalcular_premio(apolice: Apolice, nova_cobertura: Decimal) -> Decimal:
    """Recalcula o prêmio de forma proporcional, com arredondamento HALF_UP em centavos (INS-014 CA-01)."""
    if not apolice.ativa:
        raise ApoliceInativa(f"Apólice {apolice.numero} não está ativa.")
    validar_nova_cobertura(apolice.cobertura, nova_cobertura)
    novo = apolice.premio * nova_cobertura / apolice.cobertura
    return novo.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def simular_premio(apolice: Apolice, cobertura_pedida: Decimal) -> Decimal:
    """Simula o prêmio novo reusando a regra de prêmio da INS-014, sem alterar a apólice (INS-018 CA-01, CA-02)."""
    return recalcular_premio(apolice, cobertura_pedida)


# --- INS-016 · histórico de endossos (somente leitura) ---

# Campos pessoais que, se presentes no registro bruto da trilha, nunca entram na resposta.
CAMPOS_ITEM_ENDOSSO = (
    "endorsement_id",
    "date",
    "coverage_before",
    "coverage_after",
    "premium_before",
    "premium_after",
)


@dataclass(frozen=True)
class EndorsementItem:
    """Item imutável do histórico de endossos devolvido na resposta (INS-016 CA-02)."""

    endorsement_id: int
    date: datetime
    coverage_before: Decimal
    coverage_after: Decimal
    premium_before: Decimal
    premium_after: Decimal


def project_endorsement(registro: dict) -> EndorsementItem:
    """Projeta o registro bruto da trilha nos seis campos do contrato, sem recálculo e sem dado pessoal (INS-016 CA-02, CA-05)."""
    return EndorsementItem(
        endorsement_id=int(registro["endorsement_id"]),
        date=registro["date"],
        coverage_before=Decimal(registro["coverage_before"]),
        coverage_after=Decimal(registro["coverage_after"]),
        premium_before=Decimal(registro["premium_before"]),
        premium_after=Decimal(registro["premium_after"]),
    )


def sort_endorsements(itens: list[EndorsementItem]) -> list[EndorsementItem]:
    """Ordena por data decrescente e, em empate, por endorsement_id decrescente (INS-016 CA-01, CA-06)."""
    return sorted(itens, key=lambda e: (e.date, e.endorsement_id), reverse=True)


def build_history(registros: list[dict]) -> list[EndorsementItem]:
    """Monta o histórico ordenado a partir dos registros brutos da trilha (INS-016 CA-01, CA-06)."""
    return sort_endorsements([project_endorsement(r) for r in registros])
