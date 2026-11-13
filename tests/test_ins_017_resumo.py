"""Testes da INS-017 · resumo da apólice. Massa sintética: AP-0001, AP-0002 e AP-9999."""
import copy
import time
from decimal import Decimal

import pytest

from src.endosso import api
from src.endosso.regras import Apolice
from src.endosso.resumo import ValorInvalido, montar_resumo, numero_valido


# --- Regra pura (T-01, T-02) ---


def test_ins_017_ca_04_numero_valido_aceita_ap_0001():
    """INS-017 CA-04: AP-0001 tem o formato válido."""
    assert numero_valido("AP-0001")


@pytest.mark.parametrize("numero", ["12345", "AP-123", "AP-12345", "AP-0001\n", "", "ap-0001", "AP-000a"])
def test_ins_017_ca_04_numero_valido_rejeita_12345_ap_123_ap_12345_e_quebra_de_linha(numero):
    """INS-017 CA-04: formatos fora de AP- mais 4 dígitos, inclusive com quebra de linha, são rejeitados."""
    assert not numero_valido(numero)


def test_ins_017_ca_01_resumo_ap_0001_ativa():
    """INS-017 CA-01: resumo de AP-0001 ativa."""
    r = montar_resumo(Apolice("AP-0001", Decimal("100000.00"), Decimal("1200.00"), True))
    assert r == {"apolice": "AP-0001", "situacao": "ativa",
                 "cobertura": Decimal("100000.00"), "premio": Decimal("1200.00")}


def test_ins_017_ca_02_resumo_ap_0002_inativa():
    """INS-017 CA-02: resumo de AP-0002 inativa."""
    r = montar_resumo(Apolice("AP-0002", Decimal("80000.00"), Decimal("950.00"), False))
    assert r["situacao"] == "inativa"
    assert r["cobertura"] == Decimal("80000.00")
    assert r["premio"] == Decimal("950.00")


def test_ins_017_ca_05_valores_sao_decimal_com_duas_casas():
    """INS-017 CA-05: valores são Decimal com 2 casas, nunca float; completar zeros não é arredondar."""
    r = montar_resumo(Apolice("AP-0001", Decimal("100000"), Decimal("1200.5"), True))
    for campo in ("cobertura", "premio"):
        assert isinstance(r[campo], Decimal)
        assert not isinstance(r[campo], float)
    assert str(r["cobertura"]) == "100000.00"
    assert str(r["premio"]) == "1200.50"


def test_ins_017_ca_05_valor_com_tres_casas_levanta_erro_sem_arredondar():
    """INS-017 CA-05: valor com 3 casas levanta ValorInvalido em vez de arredondar."""
    with pytest.raises(ValorInvalido):
        montar_resumo(Apolice("AP-0001", Decimal("100000.001"), Decimal("1200.00"), True))
    with pytest.raises(ValorInvalido):
        montar_resumo(Apolice("AP-0001", Decimal("100000.00"), Decimal("1200.005"), True))


def test_ins_017_ca_06_resumo_so_tem_os_quatro_campos():
    """INS-017 CA-06: o resumo só tem os quatro campos permitidos."""
    r = montar_resumo(Apolice("AP-0001", Decimal("100000.00"), Decimal("1200.00"), True))
    assert set(r) == {"apolice", "situacao", "cobertura", "premio"}


# --- Repositório (T-03) ---


def test_ins_017_ca_08_registro_tem_usuario_apolice_e_horario(cliente):
    """INS-017 CA-08: o registro de auditoria traz usuário, apólice e horário."""
    api.repo.registrar_consulta_resumo("AP-0001", "atendente-01")
    reg = api.repo.consultas_resumo[-1]
    assert reg["apolice"] == "AP-0001"
    assert reg["usuario"] == "atendente-01"
    assert reg["quando"]


def test_ins_017_ca_08_registro_nao_tem_outro_dado_pessoal(cliente):
    """INS-017 CA-08: o registro tem só as três chaves."""
    api.repo.registrar_consulta_resumo("AP-0001", "atendente-01")
    assert set(api.repo.consultas_resumo[-1]) == {"apolice", "usuario", "quando"}


# --- HTTP (T-04) ---


def test_ins_017_ca_01_http_ap_0001(cliente):
    """INS-017 CA-01: GET do resumo de AP-0001."""
    r = cliente.get("/apolices/AP-0001/resumo")
    assert r.status_code == 200
    assert r.json() == {"apolice": "AP-0001", "situacao": "ativa", "cobertura": "100000.00", "premio": "1200.00"}


def test_ins_017_ca_02_http_ap_0002(cliente):
    """INS-017 CA-02: GET do resumo de AP-0002 inativa."""
    r = cliente.get("/apolices/AP-0002/resumo")
    assert r.status_code == 200
    assert r.json() == {"apolice": "AP-0002", "situacao": "inativa", "cobertura": "80000.00", "premio": "950.00"}


def test_ins_017_ca_03_http_ap_9999_nao_encontrada(cliente):
    """INS-017 CA-03: apólice inexistente devolve 404 com a mensagem."""
    r = cliente.get("/apolices/AP-9999/resumo")
    assert r.status_code == 404
    assert r.json() == {"detail": "Apólice não encontrada."}


@pytest.mark.parametrize("numero", ["12345", "AP-123", "AP-12345"])
def test_ins_017_ca_04_http_invalido_422_e_nao_consulta_a_base(cliente, monkeypatch, numero):
    """INS-017 CA-04: número inválido devolve 422 e não chama repo.buscar."""
    chamadas = []
    original = api.repo.buscar
    monkeypatch.setattr(api.repo, "buscar", lambda n: chamadas.append(n) or original(n))
    r = cliente.get(f"/apolices/{numero}/resumo")
    assert r.status_code == 422
    assert r.json() == {"detail": "Número de apólice inválido."}
    assert chamadas == []


def test_ins_017_ca_04_http_quebra_de_linha_e_422(cliente):
    """INS-017 CA-04: AP-0001 seguido de quebra de linha codificada é rejeitado."""
    r = cliente.get("/apolices/AP-0001%0A/resumo")
    assert r.status_code == 422


def test_ins_017_ca_05_http_valor_nao_e_float(cliente):
    """INS-017 CA-05: o JSON traz cobertura e prêmio como string."""
    corpo = cliente.get("/apolices/AP-0001/resumo").json()
    assert isinstance(corpo["cobertura"], str)
    assert isinstance(corpo["premio"], str)


def test_ins_017_ca_05_http_valor_com_tres_casas_devolve_erro_generico(cliente):
    """INS-017 CA-05: valor da base com 3 casas devolve 500 genérico, sem detalhe interno."""
    api.repo.apolices["AP-0001"] = Apolice("AP-0001", Decimal("100000.001"), Decimal("1200.00"), True)
    r = cliente.get("/apolices/AP-0001/resumo")
    assert r.status_code == 500
    assert r.json() == {"detail": "Erro interno."}


def test_ins_017_ca_06_http_resposta_sem_dado_pessoal(cliente):
    """INS-017 CA-06: a resposta tem só os quatro campos."""
    corpo = cliente.get("/apolices/AP-0001/resumo", headers={"X-Solicitante": "atendente-01"}).json()
    assert set(corpo) == {"apolice", "situacao", "cobertura", "premio"}
    assert "atendente-01" not in str(corpo)


# --- Auditoria (T-05) ---


def test_ins_017_ca_08_http_consulta_existente_grava_um_registro(cliente):
    """INS-017 CA-08: consulta de AP-0001 com X-Solicitante grava um registro."""
    cliente.get("/apolices/AP-0001/resumo", headers={"X-Solicitante": "atendente-01"})
    assert len(api.repo.consultas_resumo) == 1
    reg = api.repo.consultas_resumo[0]
    assert reg["usuario"] == "atendente-01"
    assert reg["apolice"] == "AP-0001"


def test_ins_017_ca_08_http_consulta_inexistente_ap_9999_grava_um_registro(cliente):
    """INS-017 CA-08: consulta de AP-9999 também grava um registro."""
    cliente.get("/apolices/AP-9999/resumo", headers={"X-Solicitante": "atendente-01"})
    assert [r["apolice"] for r in api.repo.consultas_resumo] == ["AP-9999"]


def test_ins_017_ca_08_http_numero_invalido_nao_grava(cliente):
    """INS-017 CA-08: número de formato inválido não grava auditoria."""
    cliente.get("/apolices/AP-123/resumo", headers={"X-Solicitante": "atendente-01"})
    assert api.repo.consultas_resumo == []


def test_ins_017_ca_08_http_registro_so_tem_usuario_apolice_e_horario(cliente):
    """INS-017 CA-08: o registro não leva IP, nome nem outros cabeçalhos."""
    cliente.get("/apolices/AP-0001/resumo", headers={"X-Solicitante": "atendente-01", "X-Outro": "valor"})
    assert set(api.repo.consultas_resumo[0]) == {"apolice", "usuario", "quando"}
    assert "valor" not in str(api.repo.consultas_resumo[0])


def test_ins_017_ca_08_http_sem_cabecalho_grava_canal_app(cliente):
    """INS-017 CA-08: sem X-Solicitante grava usuario canal-app."""
    cliente.get("/apolices/AP-0001/resumo")
    assert api.repo.consultas_resumo[0]["usuario"] == "canal-app"


# --- Somente leitura e desempenho (T-06) ---


def test_ins_017_ca_07_consulta_nao_altera_apolices(cliente):
    """INS-017 CA-07: várias consultas não alteram apólices, auditoria, simulações nem histórico."""
    antes = (copy.deepcopy(api.repo.apolices), copy.deepcopy(api.repo.auditoria),
             copy.deepcopy(api.repo.simulacoes), copy.deepcopy(api.repo.historico_endossos))
    for numero in ("AP-0001", "AP-0002", "AP-9999", "AP-123"):
        cliente.get(f"/apolices/{numero}/resumo")
    depois = (api.repo.apolices, api.repo.auditoria, api.repo.simulacoes, api.repo.historico_endossos)
    assert antes == depois
    assert len(api.repo.consultas_resumo) == 3


def test_ins_017_ca_09_p95_em_memoria_ate_2s(cliente):
    """INS-017 CA-09: p95 de 100 consultas em memória até 2 s (sinal de regressão, não prova com a base real)."""
    tempos = []
    for _ in range(100):
        inicio = time.perf_counter()
        cliente.get("/apolices/AP-0001/resumo")
        tempos.append(time.perf_counter() - inicio)
    tempos.sort()
    assert tempos[94] <= 2.0
