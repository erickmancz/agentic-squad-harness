"""Testes da spec INS-018 · simulação de prêmio por aumento de cobertura. Cada teste cita o critério que cobre."""
from decimal import Decimal

import pytest

from src.endosso import api
from src.endosso.regras import Apolice, ApoliceInativa, CoberturaInvalida, simular_premio

URL = "/apolices/{}/simulacoes/aumento-cobertura"

CAMPOS_AUDITORIA = {
    "apolice",
    "cobertura_atual",
    "cobertura_pedida",
    "premio_simulado",
    "solicitante",
    "quando",
}


# --- Task 5: testes puros de domínio (cálculo e HALF_UP) ---


def test_ins_018_ca_01_premio_proporcional():
    """INS-018 CA-01: AP-0001 de 100.000 para 150.000 simula prêmio 1.800,00 (proporcional)."""
    ap = Apolice("AP-0001", Decimal("100000.00"), Decimal("1200.00"))
    assert simular_premio(ap, Decimal("150000.00")) == Decimal("1800.00")


def test_ins_018_ca_02_half_up_centavos():
    """INS-018 CA-02: AP-0003 de 33.333 para 50.000 simula 1.166,67 por HALF_UP em centavos."""
    ap = Apolice("AP-0003", Decimal("33333.00"), Decimal("777.77"))
    assert simular_premio(ap, Decimal("50000.00")) == Decimal("1166.67")


def test_ins_018_ca_03_regra_pura_inativa():
    """INS-018 CA-03: a regra pura de simulação recusa apólice inativa."""
    with pytest.raises(ApoliceInativa):
        simular_premio(Apolice("X", Decimal("10"), Decimal("1"), ativa=False), Decimal("15"))


def test_ins_018_ca_04_limite_2x():
    """INS-018 CA-04: acima de 2x levanta CoberturaInvalida e exatamente 2x é aceito."""
    ap = Apolice("X", Decimal("100000.00"), Decimal("1200.00"))
    with pytest.raises(CoberturaInvalida):
        simular_premio(ap, Decimal("200000.01"))
    assert simular_premio(ap, Decimal("200000.00")) == Decimal("2400.00")


# --- Task 6: testes do endpoint (status e contrato) ---


def test_ins_018_ca_01_endpoint_200(cliente):
    """INS-018 CA-01: POST AP-0001 para 150.000 retorna 200 com premio_simulado 1.800,00."""
    r = cliente.post(URL.format("AP-0001"), json={"cobertura_pedida": "150000.00"})
    assert r.status_code == 200
    assert Decimal(r.json()["premio_simulado"]) == Decimal("1800.00")


def test_ins_018_ca_02_endpoint_200(cliente):
    """INS-018 CA-02: POST AP-0003 para 50.000 retorna 200 com premio_simulado 1.166,67."""
    r = cliente.post(URL.format("AP-0003"), json={"cobertura_pedida": "50000.00"})
    assert r.status_code == 200
    assert Decimal(r.json()["premio_simulado"]) == Decimal("1166.67")


def test_ins_018_ca_03_inativa_409(cliente):
    """INS-018 CA-03: apólice inativa (AP-0002) retorna 409."""
    r = cliente.post(URL.format("AP-0002"), json={"cobertura_pedida": "90000.00"})
    assert r.status_code == 409


def test_ins_018_ca_04_acima_2x_422(cliente):
    """INS-018 CA-04: acima de 2x retorna 422 e exatamente 2x retorna 200."""
    acima = cliente.post(URL.format("AP-0001"), json={"cobertura_pedida": "200000.01"})
    assert acima.status_code == 422
    assert "2 vezes" in acima.json()["detail"]
    exato = cliente.post(URL.format("AP-0001"), json={"cobertura_pedida": "200000.00"})
    assert exato.status_code == 200
    assert Decimal(exato.json()["premio_simulado"]) == Decimal("2400.00")


def test_ins_018_ca_05_inexistente_404(cliente):
    """INS-018 CA-05: apólice inexistente (AP-9999) retorna 404 com mensagem genérica, sem dado pessoal."""
    r = cliente.post(URL.format("AP-9999"), json={"cobertura_pedida": "1.00"})
    assert r.status_code == 404
    detalhe = r.json()["detail"]
    assert detalhe == "Apólice não encontrada."
    for pessoal in ("cpf", "nome", "email", "telefone"):
        assert pessoal not in detalhe.lower()


# --- Task 7: testes de não mutação (só consulta) ---


@pytest.mark.parametrize(
    "numero,cobertura",
    [
        ("AP-0001", "150000.00"),  # sucesso
        ("AP-0002", "90000.00"),   # 409 inativa
        ("AP-0001", "500000.00"),  # 422 acima de 2x
        ("AP-9999", "1.00"),       # 404 inexistente
    ],
)
def test_ins_018_ca_06_apolice_intacta(cliente, numero, cobertura):
    """INS-018 CA-06: após qualquer cenário a apólice mantém cobertura, prêmio e nenhum endosso criado."""
    antes = api.repo.buscar(numero)
    auditoria_antes = len(api.repo.auditoria)
    cliente.post(URL.format(numero), json={"cobertura_pedida": cobertura})
    depois = api.repo.buscar(numero)
    assert depois == antes
    # Simulação nunca escreve na trilha de endosso efetivo (nenhum endosso criado).
    assert len(api.repo.auditoria) == auditoria_antes


# --- Task 8: trilha de auditoria sem dado pessoal ---


def test_ins_018_ca_07_auditoria_sem_dado_pessoal(cliente):
    """INS-018 CA-07: simulação bem-sucedida por BRK-001 grava registro de auditoria sem dado pessoal."""
    r = cliente.post(URL.format("AP-0001"), json={"cobertura_pedida": "150000.00"},
                     headers={"x-corretor": "BRK-001"})
    assert r.status_code == 200
    reg = api.repo.simulacoes[-1]
    assert set(reg) == CAMPOS_AUDITORIA
    assert reg["apolice"] == "AP-0001"
    assert reg["cobertura_atual"] == "100000.00"
    assert reg["cobertura_pedida"] == "150000.00"
    assert reg["premio_simulado"] == "1800.00"
    assert reg["solicitante"] == "BRK-001"
    assert reg["quando"].endswith("+00:00") or reg["quando"].endswith("Z")
    for pessoal in ("cpf", "nome", "email", "telefone"):
        assert pessoal not in set(reg)
