"""Testes da integração do AWS Emulator com o ash.py: perfil, ci, merge, aprovação, hook e higiene do repositório."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import emulador
from emulador import ErroEmulador

RAIZ = Path(__file__).resolve().parent.parent
BLOCO = {"versao": "1.0.343", "fidelidade_minima": 80, "servicos": [{"nome": "s3", "fidelidade": None}]}
PERFIL_EMU = {"nome": "falso", "testado": True, "testar": ["t"], "emulador_aws": BLOCO,
              "etapas": [{"nome": "testes", "comando": ["/x/prog", "testes"]},
                         {"nome": "integracao-aws", "requer": "emulador_aws", "comando": ["/x/prog", "integracao"]}]}


# ---------------------------------------------------------------- perfil
def test_perfil_python_padrao_nao_usa_o_emulador():
    """AC-36: o perfil padrão (perfis/python.json) não declara emulador_aws nem etapa que o exija.

    Não olha o ash-perfil.json: ele é o perfil ATIVO, que pode ser o python-aws sem que isto invalide o padrão."""
    dados = json.loads((RAIZ / "perfis" / "python.json").read_text(encoding="utf-8"))
    assert "emulador_aws" not in dados
    assert not [e["nome"] for e in dados["etapas"] if e.get("requer")]
    assert "integracao-aws" not in [e["nome"] for e in dados["etapas"]]
    ativo = json.loads((RAIZ / "ash-perfil.json").read_text(encoding="utf-8"))
    if ativo["nome"] == "python":
        assert ativo == dados


def test_perfil_python_aws_declara_o_emulador_e_a_etapa_de_integracao_da_aplicacao():
    dados = json.loads((RAIZ / "perfis" / "python-aws.json").read_text(encoding="utf-8"))
    etapa = next(e for e in dados["etapas"] if e["nome"] == "integracao-aws")
    assert etapa["requer"] == "emulador_aws" and etapa["comando"][-3:] == ["pytest", "tests/integracao_aws", "-q"]
    testes = next(e for e in dados["etapas"] if e["nome"] == "testes")
    assert "--ignore=tests/integracao_aws" in testes["comando"] and "--ignore=tests/integracao_aws" in dados["testar"]
    assert dados["testado"] is False and "boto3" in " ".join(dados["_instrucoes"])
    assert not any("boto3" in " ".join(p["comando"] if isinstance(p, dict) else p) for p in dados["setup"])
    assert emulador.validar_bloco(dados["emulador_aws"]) == []
    assert dados["emulador_aws"]["versao"] == "1.0.343" and "downloads.aws.com" in dados["emulador_aws"]["pacote_url_base"]
    assert all(s["fidelidade"] is None for s in dados["emulador_aws"]["servicos"])


def test_validar_perfil_aceita_requer_com_bloco(ash):
    assert ash.validar_perfil(json.loads(json.dumps(PERFIL_EMU)), "p.json")["nome"] == "falso"


def test_validar_perfil_recusa_requer_invalido_ou_sem_bloco(ash):
    invalido = json.loads(json.dumps(PERFIL_EMU))
    invalido["etapas"][1]["requer"] = "outra-coisa"
    with pytest.raises(SystemExit, match="requer"):
        ash.validar_perfil(invalido, "p.json")
    sem_bloco = json.loads(json.dumps(PERFIL_EMU))
    del sem_bloco["emulador_aws"]
    with pytest.raises(SystemExit, match="não tem o bloco emulador_aws"):
        ash.validar_perfil(sem_bloco, "p.json")


def test_validar_perfil_recusa_bloco_malformado(ash):
    ruim = json.loads(json.dumps(PERFIL_EMU))
    ruim["emulador_aws"]["servicos"] = []
    with pytest.raises(SystemExit, match="emulador_aws.servicos"):
        ash.validar_perfil(ruim, "p.json")


def test_modelo_nao_exige_o_emulador_e_aponta_para_o_python_aws(ash):
    dados = json.loads((RAIZ / "perfis" / "modelo.json").read_text(encoding="utf-8"))
    assert "emulador_aws" not in dados and not any(e.get("requer") for e in dados["etapas"])
    assert "perfis/python-aws.json" in " ".join(dados["_instrucoes"])
    with pytest.raises(SystemExit, match="modelo de perfil"):
        ash.validar_perfil(dados, "perfis/modelo.json")


# ---------------------------------------------------------------- cmd_ci com etapa que requer o emulador
@pytest.fixture()
def ci(ash, monkeypatch):
    """Isola o cmd_ci: nenhum processo real, nenhum evento gravado, perfil com a etapa integracao-aws."""
    import registrar_evento

    chamadas, eventos = [], []

    def run_falso(cmd, *args, **kwargs):
        chamadas.append((list(cmd), kwargs.get("env")))
        return SimpleNamespace(returncode=0, stdout="abc\n")

    monkeypatch.setattr(ash.subprocess, "run", run_falso)
    monkeypatch.setattr(ash, "perfil", lambda: PERFIL_EMU)
    monkeypatch.setattr(ash, "config", lambda: {})
    monkeypatch.setattr(registrar_evento, "gravar", lambda *a, **k: eventos.append(a) or {})
    monkeypatch.delenv("ASH_PULAR", raising=False)
    return SimpleNamespace(chamadas=chamadas, eventos=eventos, args=argparse.Namespace(spec="T-1"))


def _contexto_falso(estado):
    from contextlib import contextmanager

    @contextmanager
    def ctx(cfg, bloco, avisar=print):
        yield estado
    return ctx


def test_ci_sem_emulador_falha_so_a_etapa_de_integracao_com_mensagem_clara(ash, ci, monkeypatch, capsys):
    def sem_emulador(cfg, bloco, avisar=print):
        raise emulador.ErroEmulador("Emulador AWS não está de pé. Rode: python ash.py emulador iniciar")

    monkeypatch.setattr(emulador, "emulador_para_ci", sem_emulador)
    assert ash.cmd_ci(ci.args) == 1
    saida = capsys.readouterr().out
    assert "python ash.py emulador iniciar" in saida and "integracao-aws FALHOU" in saida
    assert any(c[0] == ["/x/prog", "testes"] for c in ci.chamadas)
    assert not any(c[0] == ["/x/prog", "integracao"] for c in ci.chamadas)
    assert ci.eventos[0][4]["emulador"] == "falhou" and ci.eventos[0][4]["emulador_versao"] == "1.0.343"


def test_ci_com_emulador_de_pe_roda_a_etapa_com_o_ambiente_isolado(ash, ci, monkeypatch):
    monkeypatch.setattr(emulador, "emulador_para_ci", _contexto_falso({"modo": "wsl"}))
    monkeypatch.setattr(emulador, "ambiente_do_estado", lambda estado, base: {"AWS_ENDPOINT_URL": "https://127.0.0.1:9297"})
    assert ash.cmd_ci(ci.args) == 0
    env_integracao = next(env for cmd, env in ci.chamadas if cmd == ["/x/prog", "integracao"])
    assert env_integracao == {"AWS_ENDPOINT_URL": "https://127.0.0.1:9297"}
    env_testes = next(env for cmd, env in ci.chamadas if cmd == ["/x/prog", "testes"])
    assert "AWS_ENDPOINT_URL" not in env_testes
    assert ci.eventos[0][4]["emulador"] == "ok" and ci.eventos[0][4]["servicos_abaixo_do_corte"] == "s3"


def test_ci_com_ash_pular_integracao_sai_com_codigo_3_e_nao_chama_o_emulador(ash, ci, monkeypatch):
    def nao_deve_chamar(*a, **k):
        raise AssertionError("o emulador não deve ser consultado quando a etapa é pulada")

    monkeypatch.setattr(emulador, "emulador_para_ci", nao_deve_chamar)
    monkeypatch.setenv("ASH_PULAR", "integracao-aws")
    assert ash.cmd_ci(ci.args) == 3
    assert ci.eventos[0][4]["emulador"] == "pulado" and ci.eventos[0][4]["status"] == "ok_parcial"


def test_etapa_isolada_sem_emulador_sai_com_codigo_1_e_mensagem(ash, monkeypatch, capsys):
    def sem_emulador(cfg, bloco, avisar=print):
        raise emulador.ErroEmulador("Emulador AWS não está de pé. Rode: python ash.py emulador iniciar")

    monkeypatch.setattr(ash, "perfil", lambda: PERFIL_EMU)
    monkeypatch.setattr(ash, "config", lambda: {})
    monkeypatch.setattr(emulador, "emulador_para_ci", sem_emulador)
    assert ash.cmd_etapa(argparse.Namespace(nome="integracao-aws")) == 1
    assert "emulador iniciar" in capsys.readouterr().out


# ---------------------------------------------------------------- comando emulador
def test_comando_emulador_iniciar_mostra_o_modo_e_nunca_as_chaves(ash, monkeypatch, capsys):
    monkeypatch.setattr(ash, "perfil", lambda: PERFIL_EMU)
    monkeypatch.setattr(ash, "config", lambda: {})
    estado = {"modo": "container", "endpoint": "https://127.0.0.1:9297", "idle": 1800}
    monkeypatch.setattr(emulador, "iniciar", lambda cfg, bloco, avisar=print: estado)
    assert ash.cmd_emulador(argparse.Namespace(operacao="iniciar")) == 0
    saida = capsys.readouterr().out
    assert "modo container" in saida and "30 min" in saida and "EMULATOR" not in saida


def test_comando_emulador_devolve_1_com_a_mensagem_do_erro(ash, monkeypatch, capsys):
    monkeypatch.setattr(ash, "perfil", lambda: PERFIL_EMU)
    monkeypatch.setattr(ash, "config", lambda: {})

    def falha(cfg, bloco, avisar=print):
        raise emulador.ErroEmulador("Nenhum modo do emulador está disponível")

    monkeypatch.setattr(emulador, "iniciar", falha)
    assert ash.cmd_emulador(argparse.Namespace(operacao="iniciar")) == 1
    assert "Nenhum modo" in capsys.readouterr().out


def test_comando_emulador_parar_e_reset(ash, monkeypatch, capsys):
    monkeypatch.setattr(ash, "perfil", lambda: PERFIL_EMU)
    monkeypatch.setattr(ash, "config", lambda: {})
    eventos = []
    monkeypatch.setattr(emulador, "ler_estado", lambda: {"modo": "linux"})
    monkeypatch.setattr(emulador, "parar", lambda estado=None, avisar=print, dormir=None: eventos.append("parar") or True)
    monkeypatch.setattr(emulador, "iniciar", lambda cfg, bloco, avisar=print: eventos.append("iniciar") or
                        {"modo": "linux", "endpoint": "https://127.0.0.1:9297", "idle": 60})
    assert ash.cmd_emulador(argparse.Namespace(operacao="parar")) == 0 and eventos == ["parar"]
    assert ash.cmd_emulador(argparse.Namespace(operacao="reset")) == 0 and eventos == ["parar", "parar", "iniciar"]


def test_status_do_emulador_lista_cada_modo(ash, monkeypatch, capsys):
    monkeypatch.setattr(ash, "perfil", lambda: PERFIL_EMU)
    monkeypatch.setattr(ash, "config", lambda: {})
    nenhum = {m: {"ok": False, "motivo": f"motivo-{m}", "detalhe": {}} for m in emulador.MODOS}
    monkeypatch.setattr(emulador, "detectar_modos", lambda cfg, *a, **k: nenhum)
    monkeypatch.setattr(emulador, "ler_estado", lambda: None)
    assert ash.cmd_emulador(argparse.Namespace(operacao="status")) == 0
    saida = capsys.readouterr().out
    assert saida.startswith("Emulador AWS: parado") and all(f"motivo-{m}" in saida for m in emulador.MODOS)


# ---------------------------------------------------------------- merge e papel homologacao
def test_homologacao_pendente(ash):
    assert "falta a execução em conta real" in ash.homologacao_pendente({}, "abc12345")
    assert "registre de novo" in ash.homologacao_pendente({"homologacao": {"commit": "zzzz9999"}}, "abc12345")
    assert ash.homologacao_pendente({"homologacao": {"commit": "abc12345"}}, "abc12345") == ""


def test_aprovacao_homologacao_guarda_a_evidencia(monkeypatch, tmp_path):
    import aprovar
    monkeypatch.setattr(aprovar, "PASTA", tmp_path)
    aprovar.registrar_aprovacao("T-1", "homologacao", "Fulana", "feat/t-1", "abc",
                                {"canal": "chat-declarado", "texto_humano": "APROVO", "id": "g1", "evidencia": "execucao-42"})
    aprovar.registrar_aprovacao("T-1", "design", "Fulana", "feat/t-1", "abc", {"canal": "chat-declarado"})
    dados = json.loads((tmp_path / "T-1.json").read_text(encoding="utf-8"))
    por_papel = {x["papel"]: x for x in dados["aprovacoes"]}
    assert por_papel["homologacao"]["evidencia"] == "execucao-42" and "evidencia" not in por_papel["design"]


def test_papel_homologacao_exige_branch_e_evidencia(ash, monkeypatch):
    import aprovar
    monkeypatch.setattr(aprovar, "achar_spec", lambda id_: RAIZ / ".kiro" / "specs" / "ins-018-simulacao-aumento-cobertura" / "requirements.md")
    args = argparse.Namespace(id="INS-018", papel="homologacao", nome="N", branch=None, evidencia=None, mensagem="APROVO")
    with pytest.raises(SystemExit, match="--branch e --evidencia"):
        ash.cmd_aprovar(args)


def test_portao_tem_a_acao_aprovar_homologacao():
    import portao
    assert "aprovar-homologacao" in portao.ACOES


# ---------------------------------------------------------------- AC-20: publicar-proto antes do bootstrap
def test_publicar_proto_sem_bootstrap_pede_o_bootstrap(ash, monkeypatch, tmp_path):
    iniciativa = tmp_path / "portfolio" / "iniciativas" / "demo"
    (iniciativa / "prototipo").mkdir(parents=True)
    (iniciativa / "prototipo" / "index.html").write_text("<html></html>", encoding="utf-8")
    (iniciativa / "prd.md").write_text("---\nid: T-9\nstatus: aprovado\n---\n", encoding="utf-8")
    monkeypatch.setattr(ash, "RAIZ", tmp_path)
    monkeypatch.setattr(ash, "config", lambda: {})
    with pytest.raises(SystemExit, match="bootstrap"):
        ash.cmd_publicar_proto(argparse.Namespace(id="T-9", mensagem="APROVO"))


# ---------------------------------------------------------------- higiene: nada de chave nem de início automático
def test_gitignore_e_gitignore_padrao_cobrem_a_pasta_do_emulador(ash):
    assert ".ash/emulador/" in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".ash/emulador/" in ash.GITIGNORE_PADRAO.splitlines()


def test_publicar_harness_leva_os_testes_de_integracao_do_harness(ash):
    assert "tests_harness_integracao/" in ash.HARNESS and "tests_harness/" in ash.HARNESS
    assert ash._eh_harness("tests_harness_integracao/test_x.py") and not ash._eh_harness(".ash/emulador/estado.json")
    assert ash._eh_harness("templates/tests-integracao-aws/conftest.py")


def test_hook_bloqueia_docker_podman_wsl_e_o_comando_emulador_para_agentes_de_papel():
    import bloquear_atos_humanos as hook
    for cmd in ("docker run x", "podman ps", "wsl.exe -d Ubuntu -- ls", "wsl --shutdown", "python ash.py emulador iniciar",
                "python ash.py aprovar INS-1 --papel homologacao --nome N"):
        assert hook.verificar(json.dumps({"command": cmd})) is not None, cmd
    for cmd in ("python ash.py status", "python ash.py etapa integracao-aws", "python ash.py testar"):
        assert hook.verificar(json.dumps({"command": cmd})) is None, cmd


def _arquivos_versionados() -> list[str]:
    try:
        saida = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=RAIZ,
                               capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git indisponível")
    if saida.returncode != 0:
        pytest.skip("não é um repositório git")
    return [f for f in saida.stdout.splitlines() if not f.endswith((".png", ".zip", ".bundle"))]


def test_nenhuma_chave_do_emulador_em_arquivo_versionado():
    padrao = re.compile(r"EMULATOR[0-9A-F]{12}")
    achados = [f for f in _arquivos_versionados()
               if (RAIZ / f).is_file() and padrao.search((RAIZ / f).read_text(encoding="utf-8", errors="ignore"))]
    assert achados == []


def test_nada_instala_o_emulador_como_servico_nem_cria_inicio_automatico():
    termos = re.compile(r"systemctl|schtasks|New-ScheduledTask|Register-ScheduledJob|CurrentVersion\\Run|vmIdleTimeout\s*=\s*-1|sc\.exe\s+create",
                        re.I)
    codigo = [RAIZ / "scripts" / "emulador.py", RAIZ / "ash.py"]
    assert [c.name for c in codigo if termos.search(c.read_text(encoding="utf-8"))] == []


# ---------------------------------------------------------------- permissões dos agentes
def _agentes():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (RAIZ / ".kiro" / "agents").glob("*.json")}


def _regras(agente: dict, capacidade: str, efeito: str) -> set:
    return {m for r in agente["permissions"]["rules"] if r["capability"] == capacidade and r["effect"] == efeito
            for m in r["match"]}


def test_nenhum_agente_roda_docker_podman_ou_wsl_no_shell():
    for nome, agente in _agentes().items():
        if "shell" not in agente.get("tools", []):
            continue
        negadas = _regras(agente, "shell", "deny")
        assert {"docker *", "podman *", "wsl *", "wsl.exe *"} <= negadas, nome


def test_agentes_de_papel_nao_rodam_o_comando_emulador():
    for nome, agente in _agentes().items():
        if nome == "squad-lead" or "shell" not in agente.get("tools", []):
            continue
        negadas = _regras(agente, "shell", "deny")
        assert "python ash.py emulador*" in negadas or "python ash.py *" in negadas, nome
        assert "python ash.py emulador*" not in _regras(agente, "shell", "allow"), nome


def test_implementador_roda_a_etapa_mas_nao_escreve_nos_testes_do_harness():
    agentes = _agentes()
    assert "python ash.py etapa integracao-aws*" in _regras(agentes["implementador"], "shell", "allow")
    assert {"tests_harness/**", "tests_harness_integracao/**"} <= _regras(agentes["implementador"], "fs_write", "deny")
    assert "tests/**" in _regras(agentes["implementador"], "fs_write", "allow")  # cobre tests/integracao_aws/
    for nome, agente in agentes.items():
        permitidas = _regras(agente, "fs_write", "allow")
        assert not {"tests_harness/**", "tests_harness_integracao/**"} & permitidas, nome


def test_nenhum_agente_roda_testar_harness_integracao():
    for nome, agente in _agentes().items():
        if nome == "squad-lead":
            continue
        permitidas = _regras(agente, "shell", "allow")
        assert not [p for p in permitidas if "testar-harness" in p], nome


# ---------------------------------------------------------------- separação: integração do harness × do cliente
def test_testar_harness_sem_flag_nao_toca_no_emulador(ash, monkeypatch, tmp_path):
    py = tmp_path / ".venv-tools" / "python.exe"
    py.parent.mkdir()
    py.write_text("", encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(ash, "venv_py", lambda nome: py)
    monkeypatch.setattr(ash.subprocess, "run", lambda cmd, **k: chamadas.append(cmd) or SimpleNamespace(returncode=0))

    def nao_deve_chamar(*a, **k):
        raise AssertionError("o emulador não deve ser consultado sem --integracao")

    monkeypatch.setattr(emulador, "emulador_para_ci", nao_deve_chamar)
    assert ash.cmd_testar_harness(argparse.Namespace(integracao=False)) == 0
    assert chamadas == [[str(py), "-m", "pytest", "tests_harness", "-q"]]


def test_testar_harness_integracao_roda_no_ambiente_isolado_e_usa_o_bloco_do_harness(ash, monkeypatch, tmp_path):
    py = tmp_path / ".venv-tools" / "python.exe"
    py.parent.mkdir()
    py.write_text("", encoding="utf-8")
    chamadas, blocos = [], []
    monkeypatch.setattr(ash, "venv_py", lambda nome: py)
    monkeypatch.setattr(ash, "config", lambda: {})
    monkeypatch.setattr(ash.subprocess, "run",
                        lambda cmd, **k: chamadas.append((cmd, k.get("env"))) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(emulador, "ambiente_do_estado", lambda estado, base: {"AWS_ENDPOINT_URL": "https://127.0.0.1:9297"})
    monkeypatch.setattr(emulador, "emulador_para_ci",
                        lambda cfg, bloco, avisar=print: blocos.append(bloco) or _contexto_falso({"modo": "wsl"})(cfg, bloco))
    assert ash.cmd_testar_harness(argparse.Namespace(integracao=True)) == 0
    assert chamadas == [([str(py), "-m", "pytest", "tests_harness_integracao", "-q"],
                         {"AWS_ENDPOINT_URL": "https://127.0.0.1:9297"})]
    assert blocos[0]["versao"] == "1.0.343" and emulador.validar_bloco(blocos[0]) == []


def test_testar_harness_integracao_sem_emulador_falha_com_mensagem_clara(ash, monkeypatch, tmp_path, capsys):
    py = tmp_path / ".venv-tools" / "python.exe"
    py.parent.mkdir()
    py.write_text("", encoding="utf-8")
    monkeypatch.setattr(ash, "venv_py", lambda nome: py)
    monkeypatch.setattr(ash, "config", lambda: {})
    monkeypatch.setattr(emulador, "ler_estado", lambda: None)
    assert ash.cmd_testar_harness(argparse.Namespace(integracao=True)) == 1
    assert "python ash.py emulador iniciar" in capsys.readouterr().out


def test_o_ci_nunca_chama_a_integracao_do_harness():
    perfis = [json.loads((RAIZ / a).read_text(encoding="utf-8")) for a in ("perfis/python.json", "perfis/python-aws.json",
                                                                          "perfis/modelo.json", "ash-perfil.json")]
    for dados in perfis:
        for etapa in dados["etapas"]:
            assert "--integracao" not in etapa["comando"] and "tests_harness_integracao" not in " ".join(etapa["comando"])


def test_bloco_do_harness_e_valido_e_a_pasta_nao_e_coletada_pelo_testar_harness():
    bloco = emulador.bloco_do_harness()
    assert emulador.validar_bloco(bloco) == [] and bloco["versao"] == "1.0.343"
    assert (RAIZ / "tests_harness_integracao").is_dir() and not (RAIZ / "tests_harness" / "integracao").exists()
    assert not (RAIZ / "tests_integracao").exists()


def test_bloco_do_harness_ilegivel_da_erro_claro(monkeypatch, tmp_path):
    monkeypatch.setattr(emulador, "ARQ_BLOCO_HARNESS", tmp_path / "nao-existe.json")
    with pytest.raises(ErroEmulador, match="Não consegui ler"):
        emulador.bloco_do_harness()


def test_emulador_iniciar_sem_bloco_no_perfil_usa_o_do_harness(ash, monkeypatch, capsys):
    perfil_sem_aws = {"nome": "x", "testar": ["t"], "etapas": [{"nome": "testes", "comando": ["c"]}]}
    monkeypatch.setattr(ash, "perfil", lambda: perfil_sem_aws)
    monkeypatch.setattr(ash, "config", lambda: {})
    recebidos = []
    monkeypatch.setattr(emulador, "iniciar", lambda cfg, bloco, avisar=print: recebidos.append(bloco) or
                        {"modo": "linux", "endpoint": "https://127.0.0.1:9297", "idle": 60})
    assert ash.cmd_emulador(argparse.Namespace(operacao="iniciar")) == 0
    assert recebidos[0]["versao"] == "1.0.343" and "usando a versão fixada dos testes de integração do harness" in capsys.readouterr().out


def test_integracao_do_harness_e_do_cliente_tem_as_mesmas_provas_de_isolamento():
    harness = (RAIZ / "tests_harness_integracao" / "conftest.py").read_text(encoding="utf-8")
    cliente = (RAIZ / "templates" / "tests-integracao-aws" / "conftest.py").read_text(encoding="utf-8")
    for prova in ('startswith("https://127.0.0.1:")', 'startswith("EMULATOR")', 'CONTA_EMULADOR = "000000000000"',
                  'endswith(":user/emulator")', "pytest.exit"):
        assert prova in harness and prova in cliente, prova


def test_boto3_fixado_igual_nos_requirements_do_harness_e_da_infra():
    def pin(arquivo):
        achado = re.search(r"^boto3==(\S+)", (RAIZ / arquivo).read_text(encoding="utf-8"), re.M)
        return achado.group(1) if achado else None

    assert pin("requirements-tools.txt") is not None and pin("requirements-tools.txt") == pin("infra/requirements.txt")
    assert pin("requirements-dev.txt") is None and pin("requirements.txt") is None  # a app de exemplo não usa AWS


# ---------------------------------------------------------------- aviso do boto3 do projeto
def test_aviso_boto3_do_projeto():
    assert emulador.aviso_boto3(None, "") == ""
    assert emulador.aviso_boto3(BLOCO, "fastapi==1\nboto3==1.43.122\n") == ""
    assert emulador.aviso_boto3(BLOCO, "  BOTO3 == 1.43.122") == ""
    sem_versao = emulador.aviso_boto3(BLOCO, "boto3>=1.35\n")
    assert "versão exata" in sem_versao
    ausente = emulador.aviso_boto3(BLOCO, "fastapi==1\nbotocore==1.0\n")
    assert "não declara o boto3" in ausente and "dependencias" in ausente


def test_cmd_perfil_avisa_do_boto3_so_quando_o_perfil_tem_emulador(ash, monkeypatch, tmp_path, capsys):
    pasta = tmp_path / "perfis"
    pasta.mkdir()
    com = json.loads(json.dumps(PERFIL_EMU))
    com["nome"] = "com"
    sem = {"nome": "sem", "testar": ["t"], "etapas": [{"nome": "testes", "comando": ["c"]}, {"nome": "harness", "comando": ["c"]}]}
    com["etapas"].append({"nome": "harness", "comando": ["c"]})
    (pasta / "com.json").write_text(json.dumps(com), encoding="utf-8")
    (pasta / "sem.json").write_text(json.dumps(sem), encoding="utf-8")
    monkeypatch.setattr(ash, "PASTA_PERFIS", pasta)
    monkeypatch.setattr(ash, "PERFIL_ARQ", tmp_path / "ash-perfil.json")
    monkeypatch.setattr(ash, "RAIZ", tmp_path)
    (tmp_path / "requirements.txt").write_text("fastapi==1\n", encoding="utf-8")
    ash.cmd_perfil(argparse.Namespace(nome="sem"))
    assert "boto3" not in capsys.readouterr().out
    ash.cmd_perfil(argparse.Namespace(nome="com"))
    assert "não declara o boto3" in capsys.readouterr().out
    (tmp_path / "requirements.txt").write_text("fastapi==1\nboto3==1.43.122\n", encoding="utf-8")
    ash.cmd_perfil(argparse.Namespace(nome="com"))
    assert "boto3" not in capsys.readouterr().out


def test_ci_avisa_do_boto3_quando_o_perfil_tem_emulador_e_o_requirements_nao(ash, ci, monkeypatch, capsys):
    monkeypatch.setattr(emulador, "emulador_para_ci", _contexto_falso({"modo": "wsl"}))
    monkeypatch.setattr(emulador, "ambiente_do_estado", lambda estado, base: {})
    monkeypatch.setattr(ash, "RAIZ", Path(RAIZ) / "tests_harness_integracao")  # sem requirements.txt aqui
    ash.cmd_ci(ci.args)
    assert "[AVISO] o perfil declara emulador_aws, mas o requirements.txt não declara o boto3" in capsys.readouterr().out


# ---------------------------------------------------------------- aviso não bloqueante do publicar-harness
def test_aviso_do_publicar_harness_so_quando_a_mudanca_toca_o_que_a_integracao_cobre(ash):
    assert ash.aviso_integracao_harness(["README.md", "docs/spec-ash-v4.md", ".kiro/steering/06-emulador-aws.md"]) == ""
    for arquivo in ("scripts/emulador.py", "infra/lambdas/ingest/handler.py", "tests_harness_integracao/test_x.py",
                    "ash.py", "infra/emulador/Dockerfile"):
        aviso = ash.aviso_integracao_harness(["README.md", arquivo])
        assert aviso.startswith("[AVISO]") and arquivo in aviso and "testar-harness --integracao" in aviso
        assert "não bloqueia" in aviso


def test_publicar_harness_imprime_o_aviso_e_nao_bloqueia(ash, monkeypatch, capsys):
    monkeypatch.setattr(ash, "branch_atual", lambda: "main")
    monkeypatch.setattr(ash, "_mudancas_harness", lambda: ["scripts/emulador.py"])
    monkeypatch.setattr(ash, "portao_consumir", lambda acao, spec, msg: {"texto_humano": "APROVO"})
    monkeypatch.setattr(ash, "rodar", lambda cmd, env=None, checar=True: 0)
    monkeypatch.setattr(ash, "push", lambda ref, upstream=False: True)
    assert ash.cmd_publicar_harness(argparse.Namespace(mensagem="APROVO")) == 0
    saida = capsys.readouterr().out
    assert "[AVISO]" in saida and "testar-harness --integracao" in saida and "publicado na main" in saida


# ---------------------------------------------------------------- AC-36 e AC-37
def test_ac36_ci_do_perfil_python_padrao_sai_com_zero_sem_emulador(ash, monkeypatch):
    """AC-36: com o perfil python padrão, o ci completo sai com código 0 mesmo sem emulador, Docker ou WSL."""
    import registrar_evento

    chamadas, eventos = [], []
    monkeypatch.setattr(ash.subprocess, "run",
                        lambda cmd, *a, **k: chamadas.append(list(cmd)) or SimpleNamespace(returncode=0, stdout="abc\n"))
    monkeypatch.setattr(registrar_evento, "gravar", lambda *a, **k: eventos.append(a) or {})
    monkeypatch.setattr(ash, "perfil", lambda: json.loads((RAIZ / "perfis" / "python.json").read_text(encoding="utf-8")))
    monkeypatch.setattr(ash, "ferramenta", lambda nome: f"/ferramentas/{nome}")

    def proibido(*a, **k):
        raise AssertionError("o ci do perfil python não pode consultar o emulador")

    for nome in ("emulador_para_ci", "detectar_modos", "iniciar", "ler_estado", "ambiente_do_estado"):
        monkeypatch.setattr(emulador, nome, proibido)
    monkeypatch.delenv("ASH_PULAR", raising=False)
    assert ash.cmd_ci(argparse.Namespace(spec="T-1")) == 0
    assert eventos[0][4]["emulador"] == "nao_aplicavel" and eventos[0][4]["status"] == "ok"
    nomes = " ".join(" ".join(c) for c in chamadas)
    assert "testar-harness" in nomes and "tests_harness_integracao" not in nomes


def test_ac37_ativar_o_python_aws_e_voltar_ao_python(ash, monkeypatch, tmp_path, capsys):
    """AC-37: perfil python-aws acrescenta a etapa e o bloco; perfil python devolve o arquivo ativo ao estado original."""
    ativo = tmp_path / "ash-perfil.json"
    original_bytes = (RAIZ / "perfis" / "python.json").read_bytes()
    ativo.write_bytes(original_bytes)
    monkeypatch.setattr(ash, "PERFIL_ARQ", ativo)
    monkeypatch.setattr(ash, "RAIZ", tmp_path)
    (tmp_path / "requirements.txt").write_text("boto3==1.43.122\n", encoding="utf-8")
    ash.cmd_perfil(argparse.Namespace(nome="python-aws"))
    depois = json.loads(ativo.read_text(encoding="utf-8"))
    assert depois["nome"] == "python-aws" and "emulador_aws" in depois
    assert [e["nome"] for e in depois["etapas"]][-1] == "integracao-aws"
    assert "marcado como não testado" in capsys.readouterr().out
    ash.cmd_perfil(argparse.Namespace(nome="python"))
    assert ativo.read_bytes() == original_bytes  # byte a byte, sem troca de LF por CRLF


def test_pytest_ignore_mantem_a_integracao_do_cliente_fora_da_etapa_testes(tmp_path):
    """O --ignore do perfil python-aws impede que a etapa testes colete tests/integracao_aws/ sem emulador."""
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\naddopts = -p no:cacheprovider\n", encoding="utf-8")
    (tmp_path / "tests" / "integracao_aws").mkdir(parents=True)
    (tmp_path / "tests" / "test_a.py").write_text("def test_a():\n    pass\n", encoding="utf-8")
    (tmp_path / "tests" / "integracao_aws" / "test_b.py").write_text("def test_b():\n    raise SystemExit('rodou sem emulador')\n",
                                                                       encoding="utf-8")
    perfil = json.loads((RAIZ / "perfis" / "python-aws.json").read_text(encoding="utf-8"))
    ignorar = [p for p in next(e for e in perfil["etapas"] if e["nome"] == "testes")["comando"] if p.startswith("--ignore")]
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *ignorar], cwd=tmp_path, capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0 and "1 passed" in r.stdout
    sem_ignorar = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=tmp_path, capture_output=True, text=True,
                                 encoding="utf-8", timeout=120)
    assert sem_ignorar.returncode != 0  # prova de que, sem o --ignore, a pasta seria coletada
