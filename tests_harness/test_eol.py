"""Fim de linha em LF nos arquivos que o Kiro e o ash.py escrevem no Windows (sem aviso de CRLF no Git)."""
import inspect
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("git") is None, reason="git não instalado")
@pytest.mark.parametrize("arquivo", ["spec.md", "design.md", "aprovacao.json", "agente.json"])
def test_gitattributes_forca_lf_em_md_e_json(arquivo):
    saida = subprocess.run(["git", "check-attr", "eol", "--", arquivo], cwd=RAIZ, capture_output=True,
                           text=True).stdout
    assert saida.strip().endswith("eol: lf")


def test_registrar_aprovacao_grava_json_sem_crlf(monkeypatch, tmp_path):
    import aprovar
    monkeypatch.setattr(aprovar, "PASTA", tmp_path / "approvals")
    aprovar.registrar_aprovacao("T-1", "po", "Pessoa Teste", "", "", {"canal": "chat-declarado", "texto_humano": "APROVO"})
    assert b"\r" not in (tmp_path / "approvals" / "T-1.json").read_bytes()


def test_aprovar_spec_reescreve_a_spec_com_lf_mesmo_se_estava_em_crlf(monkeypatch, tmp_path):
    import aprovar
    spec = tmp_path / "requirements.md"
    spec.write_bytes(b"---\r\nid: T-1\r\nstatus: rascunho\r\n---\r\n# T-1\r\n")
    monkeypatch.setattr(aprovar, "PASTA", tmp_path / "approvals")
    monkeypatch.setattr(aprovar, "checar_spec_aprovavel", lambda caminho: None)
    monkeypatch.setattr(aprovar.a, "ler", lambda caminho: SimpleNamespace(id="T-1", meta={"faixa": "autonoma"}))
    monkeypatch.setattr(aprovar.ev, "gravar", lambda *args, **kwargs: {})
    aprovar.aprovar_spec(spec, "Pessoa Teste", {"canal": "chat-declarado", "texto_humano": "APROVO"})
    dados = spec.read_bytes()
    assert b"status: aprovada" in dados
    assert b"\r" not in dados
    assert b"\r" not in (tmp_path / "approvals" / "T-1.json").read_bytes()


def test_setup_desliga_o_aviso_de_crlf_no_git(ash):
    codigo = inspect.getsource(ash.cmd_setup)
    assert '["git", "config", "core.autocrlf", "false"]' in codigo
    assert '["git", "config", "core.safecrlf", "false"]' in codigo


@pytest.mark.parametrize("funcao", ["cmd_nova_spec", "cmd_aprovar_prd", "cmd_nova_descoberta"])
def test_ash_grava_story_prd_e_aprovacao_do_prd_com_lf(ash, funcao):
    codigo = inspect.getsource(getattr(ash, funcao))
    gravacoes = codigo.count(".write_text(")
    assert gravacoes >= 1
    assert codigo.count('newline="\\n"') == gravacoes
