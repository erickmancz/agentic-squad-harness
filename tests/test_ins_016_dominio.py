"""Testes de regra pura da spec INS-016 · histórico de endossos. Cada teste cita o critério que cobre."""
from datetime import datetime, timezone
from decimal import Decimal

from src.endosso.regras import (
    EndorsementItem,
    build_history,
    project_endorsement,
    sort_endorsements,
)

MESMA_DATA = datetime(2026, 2, 10, 13, 45, 0, tzinfo=timezone.utc)
DATA_ANTERIOR = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)


def _registro(endorsement_id: int, date: datetime, extra: dict | None = None) -> dict:
    """Monta um registro bruto de trilha com os seis campos (e campos extras opcionais)."""
    base = {
        "endorsement_id": endorsement_id,
        "date": date,
        "coverage_before": "100000.00",
        "coverage_after": "150000.00",
        "premium_before": "1200.00",
        "premium_after": "1500.00",
    }
    if extra:
        base.update(extra)
    return base


def test_ins_016_ca_01_ordena_recente_primeiro():
    """INS-016 CA-01: a ordenação devolve o endosso mais recente antes do mais antigo."""
    itens = [
        project_endorsement(_registro(1, DATA_ANTERIOR)),
        project_endorsement(_registro(2, MESMA_DATA)),
    ]
    ordenado = sort_endorsements(itens)
    assert [i.date for i in ordenado] == [MESMA_DATA, DATA_ANTERIOR]


def test_ins_016_ca_06_desempate_id_decrescente():
    """INS-016 CA-06: na mesma data, o endosso de id maior (12) vem antes do id menor (11)."""
    itens = build_history([_registro(11, MESMA_DATA), _registro(12, MESMA_DATA)])
    assert [i.endorsement_id for i in itens] == [12, 11]


def test_ins_016_ca_05_monetario_decimal_sem_recalculo():
    """INS-016 CA-05: os valores monetários ficam em Decimal de duas casas, preservados sem recálculo."""
    item = project_endorsement(_registro(1, MESMA_DATA, {"premium_after": "1500.00"}))
    assert isinstance(item.premium_after, Decimal)
    assert item.premium_after == Decimal("1500.00")
    assert item.coverage_before == Decimal("100000.00")
    # valor preservado exatamente como gravado na trilha, sem arredondamento que altere o número
    assert str(item.premium_after) == "1500.00"


def test_ins_016_ca_02_item_sem_dado_pessoal():
    """INS-016 CA-02: a projeção copia só os seis campos do contrato, descartando qualquer dado pessoal do registro bruto."""
    registro = _registro(1, MESMA_DATA, {"nome_segurado": "Fulano", "cpf": "000.000.000-00"})
    item = project_endorsement(registro)
    campos = set(vars(item))
    assert campos == {
        "endorsement_id",
        "date",
        "coverage_before",
        "coverage_after",
        "premium_before",
        "premium_after",
    }
    assert "nome_segurado" not in campos
    assert "cpf" not in campos
    assert isinstance(item, EndorsementItem)
