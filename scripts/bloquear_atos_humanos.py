#!/usr/bin/env python3
"""Hook PreToolUse dos AGENTES DE PAPEL (declarado em cada .kiro/agents/*.json).

Lê o contexto do evento em STDIN (JSON do Kiro), extrai só os campos de comando de shell
(chaves "command", "cmd" ou "commands", em qualquer nível) e bloqueia atos humanos.
Escrita de arquivo que apenas CITA um comando não é bloqueada.

Saída 0 libera. Para bloquear, sai com ASH_EXIT_BLOQUEIO (padrão 2) e escreve o motivo em stderr.
ATENÇÃO: o código de saída que o Kiro interpreta como bloqueio NÃO foi confirmado na documentação
consultada em 20/10/2026.
"""
from __future__ import annotations

import json
import os
import re
import sys

CHAVES = {"command", "cmd", "commands"}
PADROES = [
    r"\bgit\s+push\b",
    r"\bgit\s+merge\b",
    r"\bgit\s+(checkout|switch)\s+main\b(?![-/\w])",
    r"\bgit\s+rebase\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+config\b",
    r"\bgit\s+commit\b.*--no-verify",
    r"ash\.py\s+(setup|configurar|nova-spec|aprovar|merge|metricas|backup|restaurar|bootstrap|teardown|portao|sync|publicar-harness|publicar-proto|nova-descoberta|perfil|emulador)\b",
    r"(^|[;&|\s])(docker|podman|wsl)(\.exe)?\s",
    r"\.ash[/\\]gate",
    r"portao\.py",
    r"aprovar\.py",
    r"ASH_MERGE",
    r"(^|[;&|\s])aws\s",
    r"(^|[;&|\s])cdk\s",
]


def comandos(obj) -> list[str]:
    achados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CHAVES:
                if isinstance(v, str):
                    achados.append(v)
                elif isinstance(v, list):
                    achados += [x for x in v if isinstance(x, str)]
            else:
                achados += comandos(v)
    elif isinstance(obj, list):
        for x in obj:
            achados += comandos(x)
    return achados


def verificar(texto: str) -> str | None:
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        return None
    for cmd in comandos(dados):
        for p in PADROES:
            if re.search(p, cmd):
                return p
    return None


def main() -> int:
    texto = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not texto.strip():
        return 0
    padrao = verificar(texto)
    if padrao:
        print(f"ASH: bloqueado. Comando casa com '{padrao}', que é ato humano pela regra 8 "
              "da governança. Peça ao humano para executar.", file=sys.stderr)
        return int(os.environ.get("ASH_EXIT_BLOQUEIO", "2"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
