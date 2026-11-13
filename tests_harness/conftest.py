"""Fixtures dos testes do harness (ash.py e scripts/). Não citam specs: o rastreio só varre tests/."""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
for pasta in (RAIZ / "scripts", RAIZ):
    if str(pasta) not in sys.path:
        sys.path.insert(0, str(pasta))


@pytest.fixture(scope="session")
def ash():
    """Carrega o ash.py por caminho e devolve o diretório de trabalho, que o módulo muda ao ser importado."""
    cwd = os.getcwd()
    spec = importlib.util.spec_from_file_location("ash_harness", RAIZ / "ash.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    os.chdir(cwd)
    return modulo
