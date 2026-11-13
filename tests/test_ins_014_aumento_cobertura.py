"""Testes da spec INS-014 · aumento de cobertura. Cada teste cita o critério que cobre."""
from decimal import Decimal

import pytest

from src.endosso import api
from src.endosso.regras import Apolice, ApoliceInativa, CoberturaInvalida, recalcular_premio

URL = "/apolices/{}/endossos/aumento-cobertura"


def test_ins_014_ca_01_recalcula_premio_proporcional(cliente):
    """INS-014 CA-01: apólice ativa, cobertura 100.000 para 150.000, prêmio 1.200,00 vira 1.800,00."""
    r = cliente.post(URL.format("AP-0001"), json={"nova_cobertura": "150000.00"})
    assert r.status_code == 200
    assert Decimal(r.json()["premio_novo"]) == Decimal("1800.00")


def test_ins_014_ca_01_arredonda_half_up_em_centavos():
    """INS-014 CA-01: arredondamento HALF_UP em centavos."""
    ap = Apolice("X", Decimal("33333.00"), Decimal("777.77"))
    assert recalcular_premio(ap, Decimal("50000.00")) == Decimal("1166.67")


def test_ins_014_ca_02_apolice_inativa_retorna_409_sem_mudar_premio(cliente):
    """INS-014 CA-02: apólice cancelada não aceita endosso e o prêmio não muda."""
    antes = api.repo.buscar("AP-0002").premio
    r = cliente.post(URL.format("AP-0002"), json={"nova_cobertura": "90000.00"})
    assert r.status_code == 409
    assert api.repo.buscar("AP-0002").premio == antes


def test_ins_014_ca_02_regra_pura_inativa():
    """INS-014 CA-02: a regra pura recusa apólice inativa."""
    with pytest.raises(ApoliceInativa):
        recalcular_premio(Apolice("X", Decimal("10"), Decimal("1"), ativa=False), Decimal("15"))


@pytest.mark.parametrize("valor", ["100000.00", "90000.00"])
def test_ins_014_ca_03_cobertura_menor_ou_igual_retorna_422(cliente, valor):
    """INS-014 CA-03: nova cobertura menor ou igual à atual é recusada."""
    r = cliente.post(URL.format("AP-0001"), json={"nova_cobertura": valor})
    assert r.status_code == 422


def test_ins_014_ca_04_acima_de_duas_vezes_retorna_422(cliente):
    """INS-014 CA-04: nova cobertura acima de 2 vezes a atual é recusada com a mensagem do limite."""
    r = cliente.post(URL.format("AP-0001"), json={"nova_cobertura": "200000.01"})
    assert r.status_code == 422
    assert "2 vezes" in r.json()["detail"]


def test_ins_014_ca_04_limite_exato_aceito():
    """INS-014 CA-04: exatamente 2 vezes a cobertura atual é aceito."""
    ap = Apolice("X", Decimal("100000.00"), Decimal("1200.00"))
    assert recalcular_premio(ap, Decimal("200000.00")) == Decimal("2400.00")


def test_ins_014_ca_05_trilha_de_auditoria_sem_dado_pessoal(cliente):
    """INS-014 CA-05: a alteração registra trilha de auditoria sem dado pessoal."""
    cliente.post(URL.format("AP-0001"), json={"nova_cobertura": "120000.00"},
                 headers={"x-solicitante": "canal-app"})
    reg = api.repo.auditoria[-1]
    assert reg["apolice"] == "AP-0001"
    assert reg["premio_anterior"] == "1200.00"
    assert reg["premio_novo"] == "1440.00"
    assert set(reg) == {"apolice", "solicitante", "quando", "premio_anterior", "premio_novo",
                        "cobertura_anterior", "cobertura_nova"}


def test_apolice_inexistente_retorna_404(cliente):
    r = cliente.post(URL.format("AP-9999"), json={"nova_cobertura": "1.00"})
    assert r.status_code == 404


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_regra_pura_cobertura_invalida():
    with pytest.raises(CoberturaInvalida):
        recalcular_premio(Apolice("X", Decimal("10"), Decimal("1")), Decimal("10"))
