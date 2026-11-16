"""Testes do cmd_ci: o núcleo (spec-gate e rastreio) não é pulável e o evento registra o ator certo."""
import argparse
from types import SimpleNamespace

import pytest

PERFIL_FALSO = {
    "nome": "falso", "testado": True, "testar": ["t"],
    "etapas": [{"nome": "testes", "comando": ["/x/prog", "testes"]},
               {"nome": "sast", "comando": ["/x/prog", "sast"]}],
}


@pytest.fixture()
def ci_isolado(ash, monkeypatch):
    """Isola o cmd_ci: nenhum processo real roda e nenhum evento é gravado em .ash/events."""
    import registrar_evento

    chamadas, eventos = [], []

    def run_falso(cmd, *args, **kwargs):
        chamadas.append(list(cmd))
        falha = "FALHA" in cmd
        return SimpleNamespace(returncode=1 if falha else 0, stdout="abc123\n")

    monkeypatch.setattr(ash.subprocess, "run", run_falso)
    monkeypatch.setattr(ash, "perfil", lambda: PERFIL_FALSO)
    monkeypatch.setattr(registrar_evento, "gravar", lambda *a, **k: eventos.append(a) or {})
    monkeypatch.delenv("ASH_PULAR", raising=False)
    monkeypatch.delenv("ASH_ATOR", raising=False)
    return SimpleNamespace(chamadas=chamadas, eventos=eventos, args=argparse.Namespace(spec="T-1"))


@pytest.mark.parametrize("valor", ["spec-gate", "rastreio", "testes,rastreio", "spec-gate,rastreio"])
def test_ash_pular_recusa_etapas_do_nucleo(ash, ci_isolado, monkeypatch, valor):
    monkeypatch.setenv("ASH_PULAR", valor)
    with pytest.raises(SystemExit, match="não pode pular etapas do núcleo"):
        ash.cmd_ci(ci_isolado.args)
    assert ci_isolado.chamadas == []
    assert ci_isolado.eventos == []


def test_ci_verde_roda_as_cinco_etapas_e_sai_com_zero(ash, ci_isolado):
    assert ash.cmd_ci(ci_isolado.args) == 0
    programas = [c for c in ci_isolado.chamadas if c[:1] == ["/x/prog"]]
    assert [c[1] for c in programas] == ["testes", "sast"]
    assert any("validar_spec.py" in " ".join(c) for c in ci_isolado.chamadas)
    assert any("rastrear_aceite.py" in " ".join(c) for c in ci_isolado.chamadas)


def test_ash_pular_etapa_do_perfil_sai_com_codigo_3_e_nao_executa_a_etapa(ash, ci_isolado, monkeypatch):
    monkeypatch.setenv("ASH_PULAR", "sast")
    assert ash.cmd_ci(ci_isolado.args) == 3
    assert ["/x/prog", "sast"] not in ci_isolado.chamadas
    assert ci_isolado.eventos[0][3] == "" and ci_isolado.eventos[0][4]["status"] == "ok_parcial"


def test_etapa_que_falha_faz_o_ci_sair_com_um(ash, ci_isolado, monkeypatch):
    perfil_com_falha = dict(PERFIL_FALSO, etapas=[{"nome": "testes", "comando": ["/x/prog", "FALHA"]}])
    monkeypatch.setattr(ash, "perfil", lambda: perfil_com_falha)
    assert ash.cmd_ci(ci_isolado.args) == 1
    assert ci_isolado.eventos[0][4]["status"] == "falhou"


def test_evento_ci_executado_grava_ator_agente_por_padrao(ash, ci_isolado):
    ash.cmd_ci(ci_isolado.args)
    tipo, spec, ator = ci_isolado.eventos[0][:3]
    assert (tipo, spec, ator) == ("ci_executado", "T-1", "agente")


def test_ash_ator_humano_para_execucao_manual(ash, ci_isolado, monkeypatch):
    monkeypatch.setenv("ASH_ATOR", "humano")
    ash.cmd_ci(ci_isolado.args)
    assert ci_isolado.eventos[0][2] == "humano"


def test_ash_ator_invalido_e_recusado(ash, monkeypatch):
    monkeypatch.setenv("ASH_ATOR", "robo")
    with pytest.raises(SystemExit, match="ASH_ATOR"):
        ash.ator_do_ci()


def test_ator_do_ci_e_um_valor_aceito_pelos_eventos(ash, monkeypatch):
    monkeypatch.delenv("ASH_ATOR", raising=False)
    assert ash.ator_do_ci() == "agente"
    monkeypatch.setenv("ASH_ATOR", " HUMANO ")
    assert ash.ator_do_ci() == "humano"


@pytest.mark.parametrize("branch,esperado", [
    ("feat/ins-017", "INS-017"), ("feat/INS-017", "INS-017"), ("feat/abc-1", "ABC-1"),
    ("main", ""), ("", ""), ("feat/sem-numero", ""), ("feat/ins-017-extra", ""), ("hotfix/ins-017", ""),
])
def test_spec_da_branch_infere_o_id_so_de_feat_id(ash, branch, esperado):
    assert ash.spec_da_branch(branch) == esperado


def _ci_sem_spec(ash, ci_isolado, monkeypatch, branch):
    monkeypatch.setattr(ash, "branch_atual", lambda: branch)
    monkeypatch.delenv("ASH_SPEC", raising=False)
    ash.cmd_ci(argparse.Namespace(spec=None))
    return ci_isolado.eventos[0][1]


def test_ci_sem_spec_infere_a_spec_pela_branch_feat(ash, ci_isolado, monkeypatch):
    assert _ci_sem_spec(ash, ci_isolado, monkeypatch, "feat/ins-017") == "INS-017"


def test_ci_sem_spec_fora_de_feat_grava_na(ash, ci_isolado, monkeypatch):
    assert _ci_sem_spec(ash, ci_isolado, monkeypatch, "main") == "NA"


def test_ci_spec_do_argumento_e_da_variavel_valem_mais_que_a_branch(ash, ci_isolado, monkeypatch):
    monkeypatch.setattr(ash, "branch_atual", lambda: "feat/ins-017")
    monkeypatch.setenv("ASH_SPEC", "INS-099")
    ash.cmd_ci(argparse.Namespace(spec=None))
    assert ci_isolado.eventos[0][1] == "INS-099"
    ash.cmd_ci(argparse.Namespace(spec="INS-050"))
    assert ci_isolado.eventos[1][1] == "INS-050"
