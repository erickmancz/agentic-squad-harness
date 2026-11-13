"""Testes da auditoria das ferramentas do harness (testar-harness --auditoria): dublê do pip-audit e do PyPI, sem rede."""
import argparse
import json
import tempfile
import urllib.request
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

import auditoria_ferramentas as aud

RAIZ = Path(__file__).resolve().parent.parent
IDS_REAIS = {"CVE-2026-59951", "CVE-2026-116684", "CVE-2026-116685", "CVE-2026-116686", "CVE-2026-114603", "CVE-2026-126360"}


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Falha o teste que tentar abrir uma URL de verdade."""
    def proibido(*a, **k):
        raise AssertionError("o teste da auditoria não pode usar a rede")

    monkeypatch.setattr(urllib.request, "urlopen", proibido)


def _aceite(id_="CVE-2026-1111", pacote="mcp", **extra):
    base = {"id": id_, "pacote": pacote, "versao_afetada": "1.0.0", "motivo": "m", "fonte": "f",
            "decidido_em": "2026-11-13", "revisar_em": "2027-02-11", "decidido_por": "autor do harness",
            "validade": aud.FRASE_VALIDADE,
            "sai_quando": {"pacote_que_declara": "semgrep", "exige": {"pacote": pacote, "minimo": "2.0.0"}}}
    base.update(extra)
    return base


def _saida_pip_audit(*vulns, ruido=3):
    """JSON no formato real do pip-audit: dependencies com vulns (id, aliases, fix_versions)."""
    deps = [{"name": f"limpo{i}", "version": "1.0", "vulns": []} for i in range(ruido)]
    por_pacote = {}
    for pacote, versao, id_, alias, fix in vulns:
        por_pacote.setdefault((pacote, versao), []).append({"id": id_, "aliases": [alias], "fix_versions": fix})
    deps += [{"name": p, "version": v, "vulns": vs} for (p, v), vs in por_pacote.items()]
    return json.dumps({"dependencies": deps, "fixes": []})


def _executor(texto, codigo=0, erro=""):
    chamadas = []

    def executar(cmd, **k):
        chamadas.append(cmd)
        return SimpleNamespace(returncode=codigo, stdout=texto, stderr=erro)

    executar.chamadas = chamadas
    return executar


def _buscar(requires_dist, versao="1.185.0", data="2026-11-10T09:33:11"):
    def buscar(url, timeout=30):
        return {"info": {"version": versao, "requires_dist": requires_dist},
                "releases": {versao: [{"upload_time": data}]}}
    return buscar


def _gravar(aceites, destino):
    destino.write_text(json.dumps({"aceites": aceites}), encoding="utf-8")
    return destino


def _rodar(aceites, executor, buscar, hoje=date(2026, 11, 14)):
    linhas = []
    with tempfile.TemporaryDirectory() as pasta:
        codigo = aud.main([], executar=executor, buscar=buscar, hoje=hoje, saida=linhas.append,
                          arq_aceites=_gravar(aceites, Path(pasta) / "aceites.json"))
    return codigo, "\n".join(linhas)


# ---------------------------------------------------------------- o arquivo real
def test_arquivo_de_aceites_real_e_valido_e_cobre_os_seis_cves():
    dados = aud.carregar()
    assert aud.validar(dados) == []
    assert {a["id"] for a in dados["aceites"]} == IDS_REAIS
    for a in dados["aceites"]:
        assert a["decidido_por"] == "autor do harness" and a["validade"] == aud.FRASE_VALIDADE
        assert (date.fromisoformat(a["revisar_em"]) - date.fromisoformat(a["decidido_em"])).days == 90


def test_aceites_reais_nao_trazem_nome_de_pessoa_nem_dado_da_maquina():
    texto = (RAIZ / "tests_harness" / "auditoria_ferramentas.json").read_text(encoding="utf-8").lower()
    for proibido in ("c:\\", "\\users\\", "@"):
        assert proibido not in texto, proibido


def test_arquivo_real_dentro_do_prazo_nao_tem_aceite_vencido_hoje_de_referencia():
    dados = aud.carregar()
    assert aud.vencidos(dados, date(2026, 11, 14)) == []
    assert len(aud.vencidos(dados, date(2027, 2, 12))) == 6
    assert aud.vencidos(dados, date(2027, 2, 11)) == []  # vence só depois da data de revisão


# ---------------------------------------------------------------- validação do arquivo
@pytest.mark.parametrize("mudanca, trecho", [
    ({"id": ""}, "falta o campo 'id'"),
    ({"id": "isto-nao-e-cve"}, "não parece um CVE"),
    ({"decidido_por": "Fulana de Tal"}, "nunca nome de pessoa"),
    ({"validade": "vale para todo mundo"}, "'validade' deve ser exatamente"),
    ({"revisar_em": "2027-03-01"}, "passa de 90 dias"),
    ({"revisar_em": "2026-11-13"}, "depois de decidido_em"),
    ({"revisar_em": "amanhã"}, "AAAA-MM-DD"),
    ({"sai_quando": {"pacote_que_declara": "semgrep"}}, "sai_quando precisa"),
    ({"fonte": ""}, "falta o campo 'fonte'"),
])
def test_validar_recusa_aceite_incompleto_ou_fora_da_regra(mudanca, trecho):
    erros = aud.validar({"aceites": [_aceite(**mudanca)]})
    assert any(trecho in e for e in erros), erros


def test_validar_recusa_aceite_repetido_e_arquivo_sem_lista():
    assert any("repetido" in e for e in aud.validar({"aceites": [_aceite(), _aceite()]}))
    assert aud.validar({}) and aud.validar({"aceites": "x"})
    assert aud.validar({"aceites": [_aceite("CVE-2026-1111", "mcp"), _aceite("CVE-2026-1111", "outro")]}) == []


# ---------------------------------------------------------------- pip-audit
def test_vulns_do_json_extrai_id_aliases_e_correcoes():
    achadas = aud.vulns_do_json(_saida_pip_audit(("mcp", "1.29.0", "CVE-2026-1", "GHSA-aaaa-bbbb-cccc", ["1.30.0", "2.2.0"])))
    assert achadas == [{"pacote": "mcp", "versao": "1.29.0", "ids": ["CVE-2026-1", "GHSA-aaaa-bbbb-cccc"],
                        "corrigida_em": ["1.30.0", "2.2.0"]}]
    assert aud.vulns_do_json(_saida_pip_audit()) == []
    with pytest.raises(aud.ErroAuditoria, match="não é JSON"):
        aud.vulns_do_json("isto nao e json")


def test_executar_pip_audit_nunca_ignora_vulnerabilidade_e_trata_falha():
    executor = _executor(_saida_pip_audit(), codigo=0)
    assert aud.executar_pip_audit(Path("requirements-tools.txt"), executor) == []
    cmd = executor.chamadas[0]
    assert "pip_audit" in cmd and "-r" in cmd and "json" in cmd and "--ignore-vuln" not in cmd
    com_vuln = _executor(_saida_pip_audit(("mcp", "1.0", "CVE-2026-1", "G-1", ["2.0"])), codigo=1)
    assert len(aud.executar_pip_audit(Path("r.txt"), com_vuln)) == 1  # código 1 = achou vulnerabilidade, não é falha
    with pytest.raises(aud.ErroAuditoria, match="precisa de rede"):
        aud.executar_pip_audit(Path("r.txt"), _executor("", codigo=2, erro="rede fora do ar"))


# ---------------------------------------------------------------- classificação
def test_classificar_separa_novos_aceites_em_uso_e_sem_uso():
    aceites = {"aceites": [_aceite("CVE-2026-1111", "mcp"), _aceite("CVE-2026-2222", "mcp"),
                           _aceite("GHSA-aaaa-bbbb-cccc", "opentelemetry-api")]}
    achadas = [{"pacote": "mcp", "versao": "1", "ids": ["CVE-2026-1111", "GHSA-x"], "corrigida_em": []},
               {"pacote": "mcp", "versao": "1", "ids": ["CVE-2026-9999"], "corrigida_em": ["2"]},
               {"pacote": "opentelemetry-api", "versao": "1", "ids": ["CVE-2026-3", "GHSA-aaaa-bbbb-cccc"], "corrigida_em": []},
               {"pacote": "outro", "versao": "1", "ids": ["CVE-2026-2222"], "corrigida_em": []}]
    novos, em_uso, sem_uso = aud.classificar(achadas, aceites)
    assert [v["ids"][0] for v in novos] == ["CVE-2026-9999", "CVE-2026-2222"]  # o aceite é por id E pacote
    assert [a["id"] for a in em_uso] == ["CVE-2026-1111", "GHSA-aaaa-bbbb-cccc"]  # casa também pelo alias
    assert [a["id"] for a in sem_uso] == ["CVE-2026-2222"]


# ---------------------------------------------------------------- "aceite pode sair"
def test_pode_sair_quando_o_semgrep_declara_faixa_que_admite_a_versao_corrigida():
    aceite = _aceite(sai_quando={"pacote_que_declara": "semgrep", "exige": {"pacote": "mcp", "minimo": "1.30.0"}})
    assert aud.pode_sair_pelo_semgrep(aceite, ["mcp==1.29.0"], "1.185.0") == ""
    assert "admite 1.30.0 ou superior" in aud.pode_sair_pelo_semgrep(aceite, ["mcp>=1.30.0,<2"], "1.190.0")
    assert "não declara mais mcp" in aud.pode_sair_pelo_semgrep(aceite, ["rich>=13"], "1.190.0")
    assert aud.pode_sair_pelo_semgrep(aceite, ['mcp>=1.30; extra == "mcp"', "mcp==1.29.0"], "1") == ""  # ignora extras
    otel = _aceite(pacote="opentelemetry-api",
                   sai_quando={"pacote_que_declara": "semgrep", "exige": {"pacote": "opentelemetry-api", "minimo": "1.45.2"}})
    assert aud.pode_sair_pelo_semgrep(otel, ["opentelemetry-api~=1.37.0"], "1.185.0") == ""
    assert aud.pode_sair_pelo_semgrep(otel, ["opentelemetry-api~=1.45.0"], "1.200.0") != ""
    assert aud.pode_sair_pelo_semgrep(otel, ["opentelemetry-api~=1.45.0"], "1.200.0").startswith("o semgrep 1.200.0 declara")


def test_semgrep_mais_recente_le_versao_data_e_requires_dist():
    versao, data, req = aud.semgrep_mais_recente(_buscar(["mcp==1.29.0"], "1.185.0", "2026-11-10T09:33:11"))
    assert (versao, data, req) == ("1.185.0", "2026-11-10", ["mcp==1.29.0"])


# ---------------------------------------------------------------- relatório e código de saída
def _aceites_reais():
    return aud.carregar()["aceites"]


def _achadas_reais():
    return _saida_pip_audit(
        ("mcp", "1.29.0", "CVE-2026-59951", "G-1", ["1.30.0"]), ("mcp", "1.29.0", "CVE-2026-116684", "G-2", ["1.30.0"]),
        ("mcp", "1.29.0", "CVE-2026-116685", "G-3", ["1.30.0"]), ("mcp", "1.29.0", "CVE-2026-116686", "G-4", ["1.30.0"]),
        ("opentelemetry-api", "1.37.0", "CVE-2026-114603", "G-5", ["1.45.1"]),
        ("opentelemetry-api", "1.37.0", "CVE-2026-126360", "G-6", ["1.45.2"]))


REQUIRES_ATUAL = ["mcp==1.29.0", "opentelemetry-api~=1.37.0"]


def test_auditoria_com_tudo_aceito_e_no_prazo_sai_com_zero_e_mostra_as_tres_listas():
    codigo, texto = _rodar(_aceites_reais(), _executor(_achadas_reais(), 1), _buscar(REQUIRES_ATUAL))
    assert codigo == 0 and "AUDITORIA: OK" in texto
    assert "CVEs novos (sem aceite): 0" in texto and "Aceites vencidos (revisão passada): 0" in texto
    assert "Aceites que podem sair: 0" in texto and "Aceites em vigor: 6" in texto
    assert "cada cliente revalida com o seu time de segurança" in texto
    assert "Semgrep mais recente no PyPI: 1.185.0 (2026-11-10)" in texto


def test_cve_novo_sem_aceite_faz_a_auditoria_sair_com_um():
    achadas = _saida_pip_audit(("mcp", "1.29.0", "CVE-2026-59951", "G-1", ["1.30.0"]),
                               ("fastapi", "1.0", "CVE-2026-777", "G-9", ["2.0"]))
    codigo, texto = _rodar([_aceite("CVE-2026-59951", "mcp")], _executor(achadas, 1), _buscar(REQUIRES_ATUAL))
    assert codigo == 1 and "CVEs novos (sem aceite): 1" in texto and "CVE-2026-777 em fastapi 1.0" in texto
    assert "AUDITORIA: PENDENTE" in texto


def test_aceite_vencido_faz_a_auditoria_sair_com_um():
    codigo, texto = _rodar(_aceites_reais(), _executor(_achadas_reais(), 1), _buscar(REQUIRES_ATUAL), hoje=date(2027, 2, 12))
    assert codigo == 1 and "Aceites vencidos (revisão passada): 6" in texto and "revisar em 2027-02-11" in texto
    assert "CVEs novos (sem aceite): 0" in texto


def test_aceite_sem_vulnerabilidade_correspondente_aparece_em_podem_sair_e_nao_falha():
    codigo, texto = _rodar([_aceite("CVE-2026-1111", "mcp")], _executor(_saida_pip_audit(), 0), _buscar(REQUIRES_ATUAL))
    assert codigo == 0 and "Aceites que podem sair: 1" in texto and "não aparece mais na auditoria" in texto


def test_semgrep_novo_com_faixa_corrigida_coloca_o_aceite_em_podem_sair():
    achadas = _saida_pip_audit(("mcp", "1.29.0", "CVE-2026-1111", "G-1", ["1.30.0"]))
    aceite = _aceite("CVE-2026-1111", "mcp",
                     sai_quando={"pacote_que_declara": "semgrep", "exige": {"pacote": "mcp", "minimo": "1.30.0"}})
    codigo, texto = _rodar([aceite], _executor(achadas, 1), _buscar(["mcp>=1.30.0,<2"], "1.190.0", "2026-12-01T00:00:00"))
    assert codigo == 0 and "Aceites que podem sair: 1" in texto
    assert "declara mcp" in texto and "publicado em 2026-12-01" in texto and "regra de 14 dias" in texto


def test_pypi_fora_do_ar_avisa_mas_nao_muda_o_codigo():
    def buscar_quebrado(url, timeout=30):
        raise OSError("sem rede")

    codigo, texto = _rodar(_aceites_reais(), _executor(_achadas_reais(), 1), buscar_quebrado)
    assert codigo == 0 and "não consegui consultar o PyPI" in texto and "Semgrep mais recente no PyPI: não consultado" in texto


def test_falha_do_pip_audit_sai_com_dois_e_nao_finge_sucesso():
    codigo, texto = _rodar(_aceites_reais(), _executor("", 2, "sem rede"), _buscar(REQUIRES_ATUAL))
    assert codigo == 2 and "[ERRO]" in texto and "AUDITORIA: OK" not in texto


def test_arquivo_de_aceites_invalido_sai_com_dois():
    codigo, texto = _rodar([_aceite(decidido_por="Fulana")], _executor(_saida_pip_audit(), 0), _buscar(REQUIRES_ATUAL))
    assert codigo == 2 and "arquivo de aceites inválido" in texto


# ---------------------------------------------------------------- integração com o ash.py
def test_ash_testar_harness_auditoria_roda_o_script_com_a_venv_tools(ash, monkeypatch, tmp_path):
    py = tmp_path / ".venv-tools" / "python.exe"
    py.parent.mkdir()
    py.write_text("", encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(ash, "venv_py", lambda nome: py)
    monkeypatch.setattr(ash.subprocess, "run", lambda cmd, **k: chamadas.append(cmd) or SimpleNamespace(returncode=1))
    assert ash.cmd_testar_harness(argparse.Namespace(integracao=False, auditoria=True)) == 1
    assert chamadas == [[str(py), "scripts/auditoria_ferramentas.py"]]


def test_integracao_e_auditoria_sao_excludentes(ash):
    with pytest.raises(SystemExit) as e:
        ash.main(["testar-harness", "--integracao", "--auditoria"])
    assert e.value.code == 2


def test_o_ci_nunca_chama_a_auditoria():
    for arquivo in ("perfis/python.json", "perfis/python-aws.json", "perfis/modelo.json", "ash-perfil.json"):
        dados = json.loads((RAIZ / arquivo).read_text(encoding="utf-8"))
        for etapa in dados["etapas"]:
            assert "--auditoria" not in etapa["comando"] and "auditoria_ferramentas" not in " ".join(etapa["comando"])


def test_testar_harness_sem_flag_nao_chama_a_auditoria(ash, monkeypatch, tmp_path):
    py = tmp_path / ".venv-tools" / "python.exe"
    py.parent.mkdir()
    py.write_text("", encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(ash, "venv_py", lambda nome: py)
    monkeypatch.setattr(ash.subprocess, "run", lambda cmd, **k: chamadas.append(cmd) or SimpleNamespace(returncode=0))
    ash.cmd_testar_harness(argparse.Namespace(integracao=False, auditoria=False))
    assert chamadas == [[str(py), "-m", "pytest", "tests_harness", "-q"]]


def test_auditoria_pertence_ao_harness_e_nao_ao_trabalho(ash):
    assert ash._eh_harness("tests_harness/auditoria_ferramentas.json") and ash._eh_harness("scripts/auditoria_ferramentas.py")
    assert ash._eh_harness("requirements-tools.txt")


# ---------------------------------------------------------------- aviso do publicar-harness
def test_aviso_so_quando_ferramentas_ou_aceites_mudam_ou_ha_aceite_vencido(ash, tmp_path):
    arq = _gravar([_aceite("CVE-2026-1111")], tmp_path / "a.json")  # tmp_path é do pytest e é apagada por ele
    antes = date(2026, 11, 14)
    assert ash.aviso_auditoria_harness(["README.md", "ash.py"], antes, arq) == ""
    for tocado in ("requirements-tools.txt", "tests_harness/auditoria_ferramentas.json"):
        aviso = ash.aviso_auditoria_harness(["README.md", tocado], antes, arq)
        assert aviso.startswith("[AVISO]") and tocado in aviso and "testar-harness --auditoria" in aviso
        assert "não bloqueia" in aviso and "nunca de um agente" in aviso
    vencido = ash.aviso_auditoria_harness(["README.md"], date(2027, 2, 12), arq)
    assert "vencido" in vencido and "CVE-2026-1111" in vencido
    ilegivel = ash.aviso_auditoria_harness(["README.md"], antes, tmp_path / "nao-existe.json")
    assert "não consegui ler o arquivo de aceites" in ilegivel


def test_publicar_harness_imprime_o_aviso_da_auditoria_e_nao_bloqueia(ash, monkeypatch, capsys):
    monkeypatch.setattr(ash, "branch_atual", lambda: "main")
    monkeypatch.setattr(ash, "_mudancas_harness", lambda: ["requirements-tools.txt"])
    monkeypatch.setattr(ash, "portao_consumir", lambda acao, spec, msg: {"texto_humano": "APROVO"})
    monkeypatch.setattr(ash, "rodar", lambda cmd, env=None, checar=True: 0)
    monkeypatch.setattr(ash, "push", lambda ref, upstream=False: True)
    assert ash.cmd_publicar_harness(argparse.Namespace(mensagem="APROVO")) == 0
    saida = capsys.readouterr().out
    assert "testar-harness --auditoria" in saida and "publicado na main" in saida
