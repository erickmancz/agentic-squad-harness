"""Testes de limpar_certificados_invalidos: só variável apontando para caminho inexistente é ignorada."""


def test_remove_variavel_que_aponta_para_arquivo_inexistente(ash, tmp_path):
    amb = {"REQUESTS_CA_BUNDLE": str(tmp_path / "nao-existe.pem"), "OUTRA": "valor"}
    assert ash.limpar_certificados_invalidos(amb) == ["REQUESTS_CA_BUNDLE"]
    assert amb == {"OUTRA": "valor"}


def test_mantem_variavel_que_aponta_para_arquivo_existente(ash, tmp_path):
    pem = tmp_path / "corp.pem"
    pem.write_text("x", encoding="utf-8")
    amb = {"SSL_CERT_FILE": str(pem)}
    assert ash.limpar_certificados_invalidos(amb) == []
    assert amb == {"SSL_CERT_FILE": str(pem)}


def test_mantem_variavel_que_aponta_para_pasta_existente(ash, tmp_path):
    amb = {"AWS_CA_BUNDLE": str(tmp_path)}
    assert ash.limpar_certificados_invalidos(amb) == []
    assert "AWS_CA_BUNDLE" in amb


def test_aceita_caminho_entre_aspas(ash, tmp_path):
    amb = {"NODE_EXTRA_CA_CERTS": f'"{tmp_path / "x.pem"}"'}
    assert ash.limpar_certificados_invalidos(amb) == ["NODE_EXTRA_CA_CERTS"]


def test_ignora_variavel_vazia_e_variavel_fora_da_lista(ash, tmp_path):
    amb = {"CURL_CA_BUNDLE": "", "OUTRA_CA": str(tmp_path / "nao.pem")}
    assert ash.limpar_certificados_invalidos(amb) == []
    assert set(amb) == {"CURL_CA_BUNDLE", "OUTRA_CA"}


def test_trata_todas_as_variaveis_da_lista(ash, tmp_path):
    inexistente = str(tmp_path / "nao.pem")
    amb = {nome: inexistente for nome in ash.VARS_CERTIFICADO}
    assert sorted(ash.limpar_certificados_invalidos(amb)) == sorted(ash.VARS_CERTIFICADO)
    assert amb == {}
