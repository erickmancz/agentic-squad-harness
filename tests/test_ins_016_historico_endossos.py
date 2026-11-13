"""Testes de endpoint da spec INS-016 · histórico de endossos. Cada teste cita o critério que cobre."""
from decimal import Decimal

URL = "/apolices/{}/endossos"

CAMPOS_ESPERADOS = {
    "endorsement_id",
    "date",
    "coverage_before",
    "coverage_after",
    "premium_before",
    "premium_after",
}


def test_ins_016_ca_01_ap0001_dois_itens_ordenados(cliente):
    """INS-016 CA-01: AP-0001 retorna 200 com 2 itens ordenados do mais recente para o mais antigo."""
    r = cliente.get(URL.format("AP-0001"))
    assert r.status_code == 200
    corpo = r.json()
    assert len(corpo) == 2
    datas = [item["date"] for item in corpo]
    assert datas == sorted(datas, reverse=True)


def test_ins_016_ca_02_item_contrato_iso8601(cliente):
    """INS-016 CA-02: cada item tem exatamente os seis campos, data em UTC ISO-8601 (Z) e nenhum dado pessoal."""
    r = cliente.get(URL.format("AP-0001"))
    assert r.status_code == 200
    for item in r.json():
        assert set(item) == CAMPOS_ESPERADOS
        assert item["date"].endswith("Z")
        assert "cpf" not in item and "nome" not in item and "email" not in item


def test_ins_016_ca_03_ap0003_lista_vazia(cliente):
    """INS-016 CA-03: AP-0003 existe sem endosso, retorna 200 com lista vazia."""
    r = cliente.get(URL.format("AP-0003"))
    assert r.status_code == 200
    assert r.json() == []


def test_ins_016_ca_04_ap9999_nao_encontrada(cliente):
    """INS-016 CA-04: AP-9999 inexistente retorna 404 com mensagem genérica, sem dado pessoal."""
    r = cliente.get(URL.format("AP-9999"))
    assert r.status_code == 404
    detalhe = r.json()["detail"]
    assert detalhe == "Apólice não encontrada."
    for pessoal in ("cpf", "nome", "email", "telefone"):
        assert pessoal not in detalhe.lower()


def test_ins_016_ca_04_formato_invalido_tambem_404(cliente):
    """INS-016 CA-04: número fora do formato AP+4 dígitos cai na mesma resposta 404 genérica."""
    r = cliente.get(URL.format("XYZ"))
    assert r.status_code == 404
    assert r.json()["detail"] == "Apólice não encontrada."


def test_ins_016_ca_05_monetario_string_duas_casas(cliente):
    """INS-016 CA-05: os valores monetários vêm como string de duas casas, preservados sem recálculo."""
    r = cliente.get(URL.format("AP-0001"))
    assert r.status_code == 200
    item = next(i for i in r.json() if i["endorsement_id"] == 12)
    assert item["coverage_before"] == "100000.00"
    assert item["coverage_after"] == "150000.00"
    assert item["premium_before"] == "1200.00"
    assert item["premium_after"] == "1500.00"
    # os valores são Decimal exatos, sem imprecisão de float
    assert Decimal(item["premium_after"]) == Decimal("1500.00")


def test_ins_016_ca_06_empate_data_id_decrescente(cliente):
    """INS-016 CA-06: AP-0001 tem dois endossos na mesma data; o id 12 aparece antes do 11."""
    r = cliente.get(URL.format("AP-0001"))
    assert r.status_code == 200
    ids = [item["endorsement_id"] for item in r.json()]
    assert ids == [12, 11]
