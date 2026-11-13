"""Testes de validar_perfil, perfil, cobertura_minima e expandir."""
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _perfil_minimo(**extra):
    base = {"nome": "x", "testar": ["t"], "etapas": [{"nome": "testes", "comando": ["c"]}]}
    base.update(extra)
    return base


def test_validar_perfil_aceita_o_perfil_python(ash):
    dados = json.loads((RAIZ / "perfis" / "python.json").read_text(encoding="utf-8"))
    assert ash.validar_perfil(dados, "perfis/python.json") is dados


def test_perfil_ativo_e_copia_de_um_perfil_pronto_de_perfis():
    """O ash-perfil.json é cópia de um arquivo de perfis/ (qualquer perfil pronto: os testes do harness não dependem de qual)."""
    ativo = json.loads((RAIZ / "ash-perfil.json").read_text(encoding="utf-8"))
    prontos = {}
    for arq in (RAIZ / "perfis").glob("*.json"):
        dados = json.loads(arq.read_text(encoding="utf-8"))
        if not dados.get("modelo"):
            prontos[dados["nome"]] = dados
    assert ativo["nome"] in prontos
    origem = prontos[ativo["nome"]]
    assert ativo == origem


def test_perfil_python_tem_etapas_dos_revisores_e_do_harness():
    dados = json.loads((RAIZ / "perfis" / "python.json").read_text(encoding="utf-8"))
    nomes = [e["nome"] for e in dados["etapas"]]
    assert {"testes", "sast", "dependencias", "harness"} <= set(nomes)


def test_validar_perfil_recusa_o_modelo(ash):
    with pytest.raises(SystemExit, match="modelo de perfil"):
        ash.validar_perfil(_perfil_minimo(modelo=True), "perfis/modelo.json")


def test_perfil_modelo_do_repositorio_e_recusado(ash):
    dados = json.loads((RAIZ / "perfis" / "modelo.json").read_text(encoding="utf-8"))
    with pytest.raises(SystemExit):
        ash.validar_perfil(dados, "perfis/modelo.json")


@pytest.mark.parametrize("campo", ["nome", "testar", "etapas"])
def test_validar_perfil_recusa_campo_faltando(ash, campo):
    dados = _perfil_minimo()
    dados.pop(campo)
    with pytest.raises(SystemExit, match=campo):
        ash.validar_perfil(dados, "p.json")


@pytest.mark.parametrize("nome", ["spec-gate", "rastreio"])
def test_validar_perfil_recusa_etapa_do_nucleo(ash, nome):
    dados = _perfil_minimo(etapas=[{"nome": nome, "comando": ["c"]}])
    with pytest.raises(SystemExit, match="do núcleo"):
        ash.validar_perfil(dados, "p.json")


def test_validar_perfil_recusa_etapa_sem_comando(ash):
    dados = _perfil_minimo(etapas=[{"nome": "sast", "comando": []}])
    with pytest.raises(SystemExit, match="nome e comando"):
        ash.validar_perfil(dados, "p.json")


def test_perfil_sem_arquivo_usa_o_padrao_embutido(ash, monkeypatch, tmp_path):
    monkeypatch.setattr(ash, "PERFIL_ARQ", tmp_path / "nao-existe.json")
    assert ash.perfil() is ash.PERFIL_PADRAO


def test_perfil_le_o_arquivo_ativo(ash, monkeypatch, tmp_path):
    arq = tmp_path / "ash-perfil.json"
    arq.write_text(json.dumps(_perfil_minimo(nome="outra")), encoding="utf-8")
    monkeypatch.setattr(ash, "PERFIL_ARQ", arq)
    assert ash.perfil()["nome"] == "outra"


def test_perfil_com_json_invalido_da_erro_claro(ash, monkeypatch, tmp_path):
    arq = tmp_path / "ash-perfil.json"
    arq.write_text("{ nao e json", encoding="utf-8")
    monkeypatch.setattr(ash, "PERFIL_ARQ", arq)
    with pytest.raises(SystemExit, match="não é JSON válido"):
        ash.perfil()


def test_cobertura_minima_usa_perfil_e_variavel(ash, monkeypatch):
    monkeypatch.delenv("ASH_COBERTURA_MIN", raising=False)
    assert ash.cobertura_minima({"cobertura_minima": 70}) == "70"
    assert ash.cobertura_minima({}) == "80"
    monkeypatch.setenv("ASH_COBERTURA_MIN", "90")
    assert ash.cobertura_minima({"cobertura_minima": 70}) == "90"


def test_expandir_troca_os_marcadores(ash, monkeypatch):
    monkeypatch.delenv("ASH_COBERTURA_MIN", raising=False)
    monkeypatch.setattr(ash, "py_projeto", lambda: "/x/py")
    pf = {"pasta_codigo": "app", "pasta_testes": "spec", "cobertura_minima": 75}
    cmd = ["{py}", "-m", "pytest", "--cov={codigo}", "--cov-fail-under={cobertura}", "{testes}"]
    assert ash.expandir(cmd, pf) == ["/x/py", "-m", "pytest", "--cov=app", "--cov-fail-under=75", "spec"]


def test_expandir_resolve_ferramentas_do_harness_so_como_argumento_inteiro(ash, monkeypatch):
    monkeypatch.setattr(ash, "py_projeto", lambda: "/x/py")
    monkeypatch.setattr(ash, "ferramenta", lambda nome: f"/tools/{nome}")
    pf = {}
    assert ash.expandir(["{semgrep}", "scan"], pf) == ["/tools/semgrep", "scan"]
    assert ash.expandir(["{pip-audit}", "-r", "x"], pf)[0] == "/tools/pip-audit"
    assert ash.expandir(["/bin/prog", "pre-{semgrep}"], pf)[1] == "pre-{semgrep}"


def test_expandir_python_do_harness(ash, monkeypatch):
    import sys
    monkeypatch.setattr(ash, "py_projeto", lambda: "/x/py")
    assert ash.expandir(["{python}", "-V"], {})[0] == sys.executable


# ---- etapa harness e comando testar-harness


COMANDO_HARNESS = ["{python}", "ash.py", "testar-harness"]


@pytest.mark.parametrize("arquivo", ["perfis/python.json", "perfis/python-aws.json", "perfis/modelo.json", "ash-perfil.json"])
def test_todo_perfil_leva_a_etapa_harness_com_o_comando_padrao(arquivo):
    dados = json.loads((RAIZ / arquivo).read_text(encoding="utf-8"))
    etapa = next(e for e in dados["etapas"] if e["nome"] == "harness")
    assert etapa["comando"] == COMANDO_HARNESS


def test_testar_harness_sem_venv_tools_da_erro_claro(ash, monkeypatch, tmp_path):
    monkeypatch.setattr(ash, "venv_py", lambda nome: tmp_path / nome / "python.exe")
    with pytest.raises(SystemExit, match="setup"):
        ash.cmd_testar_harness(None)


def test_testar_harness_usa_o_pytest_da_venv_tools(ash, monkeypatch, tmp_path):
    from types import SimpleNamespace
    py = tmp_path / ".venv-tools" / "python.exe"
    py.parent.mkdir()
    py.write_text("", encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(ash, "venv_py", lambda nome: py if nome == ".venv-tools" else tmp_path / nome)
    monkeypatch.setattr(ash.subprocess, "run", lambda cmd, **k: chamadas.append(cmd) or SimpleNamespace(returncode=0))
    assert ash.cmd_testar_harness(None) == 0
    assert chamadas == [[str(py), "-m", "pytest", "tests_harness", "-q"]]


def _ativar_perfil(ash, monkeypatch, tmp_path, etapas):
    pasta = tmp_path / "perfis"
    pasta.mkdir()
    (pasta / "novo.json").write_text(json.dumps(_perfil_minimo(nome="novo", etapas=etapas)), encoding="utf-8")
    monkeypatch.setattr(ash, "PASTA_PERFIS", pasta)
    monkeypatch.setattr(ash, "PERFIL_ARQ", tmp_path / "ash-perfil.json")
    return ash.cmd_perfil(SimpleNamespaceNome("novo"))


class SimpleNamespaceNome:
    """Argumentos mínimos do comando perfil."""

    def __init__(self, nome):
        self.nome = nome


def test_perfil_sem_etapa_harness_avisa(ash, monkeypatch, tmp_path, capsys):
    etapas = [{"nome": n, "comando": ["c"]} for n in ("testes", "sast", "dependencias")]
    _ativar_perfil(ash, monkeypatch, tmp_path, etapas)
    assert "todo perfil leva a etapa harness" in capsys.readouterr().out


def test_perfil_com_etapa_harness_nao_avisa(ash, monkeypatch, tmp_path, capsys):
    etapas = [{"nome": n, "comando": ["c"]} for n in ("testes", "sast", "dependencias", "harness")]
    _ativar_perfil(ash, monkeypatch, tmp_path, etapas)
    assert "todo perfil leva" not in capsys.readouterr().out
