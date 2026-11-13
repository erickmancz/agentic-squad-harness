"""Testes da permissão de execução dos hooks do Git (.githooks/): setup, status e modo no índice."""
import inspect
import os
import platform
import shutil
import subprocess
import stat

import pytest

NO_WINDOWS = platform.system() == "Windows"
so_posix = pytest.mark.skipif(NO_WINDOWS, reason="bits de execução só existem em macOS e Linux")


def _hooks(tmp_path, modo=0o644):
    pasta = tmp_path / ".githooks"
    pasta.mkdir()
    for nome in ("pre-commit", "pre-merge-commit"):
        arq = pasta / nome
        arq.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(arq, modo)
    return pasta


@so_posix
def test_setup_deixa_hooks_executaveis_e_preserva_bits_existentes(ash, tmp_path):
    pasta = _hooks(tmp_path, 0o640)
    assert ash.garantir_hooks_executaveis(tmp_path) == ["pre-commit", "pre-merge-commit"]
    for arq in pasta.iterdir():
        assert stat.S_IMODE(arq.stat().st_mode) == 0o751  # 0o640 somado a 0o111
    assert ash.garantir_hooks_executaveis(tmp_path) == []  # segunda vez: nada a fazer


@so_posix
def test_hooks_sem_execucao_lista_e_zera_depois_da_correcao(ash, tmp_path):
    _hooks(tmp_path)
    assert ash.hooks_sem_execucao(tmp_path) == ["pre-commit", "pre-merge-commit"]
    ash.garantir_hooks_executaveis(tmp_path)
    assert ash.hooks_sem_execucao(tmp_path) == []


@so_posix
def test_status_avisa_com_instrucao_quando_hook_nao_executa(ash, tmp_path):
    _hooks(tmp_path)
    linha = ash.linha_hooks(tmp_path)
    assert linha.startswith("[AVISO]") and "pre-commit" in linha and "chmod +x .githooks/*" in linha
    ash.garantir_hooks_executaveis(tmp_path)
    assert ash.linha_hooks(tmp_path) == "Hooks: executáveis"


@pytest.mark.skipif(not NO_WINDOWS, reason="comportamento do Windows")
def test_no_windows_nada_muda_e_status_fica_em_silencio(ash, tmp_path):
    pasta = _hooks(tmp_path)
    antes = {p.name: p.stat().st_mode for p in pasta.iterdir()}
    assert ash.garantir_hooks_executaveis(tmp_path) == []
    assert ash.hooks_sem_execucao(tmp_path) == []
    assert ash.linha_hooks(tmp_path) == ""
    assert {p.name: p.stat().st_mode for p in pasta.iterdir()} == antes


def test_status_fica_vazio_sem_pasta_githooks(ash, tmp_path):
    assert ash.linha_hooks(tmp_path) == ""
    assert ash.garantir_hooks_executaveis(tmp_path) == []


def test_setup_aplica_permissao_depois_do_hookspath_e_marca_o_indice_antes_do_commit(ash):
    fonte = inspect.getsource(ash.cmd_setup)
    assert fonte.index("core.hooksPath") < fonte.index("garantir_hooks_executaveis(")
    assert fonte.index('"add", "-A"') < fonte.index("marcar_hooks_no_indice(") < fonte.index('"commit"')


@pytest.mark.skipif(shutil.which("git") is None, reason="git ausente")
def test_marcar_hooks_registra_100755_no_indice_de_um_repositorio_novo(ash, tmp_path):
    _hooks(tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    ash.marcar_hooks_no_indice(tmp_path)
    saida = subprocess.run(["git", "-C", str(tmp_path), "ls-files", "-s", ".githooks"],
                           capture_output=True, text=True, check=True).stdout.splitlines()
    assert sorted(l.split()[0] + " " + l.split()[-1] for l in saida) == [
        "100755 .githooks/pre-commit", "100755 .githooks/pre-merge-commit"]


def test_indice_do_repositorio_guarda_100755_para_os_dois_hooks(ash):
    if not (ash.RAIZ / ".git").exists():
        pytest.skip("pasta sem .git (pacote extraído); o modo é conferido no repositório da main")
    saida = subprocess.run(["git", "ls-files", "-s", ".githooks"], capture_output=True, text=True,
                           cwd=ash.RAIZ).stdout.splitlines()
    modos = {l.split()[-1]: l.split()[0] for l in saida}
    assert modos == {".githooks/pre-commit": "100755", ".githooks/pre-merge-commit": "100755"}
