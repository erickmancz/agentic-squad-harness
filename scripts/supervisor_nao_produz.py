#!/usr/bin/env python3
"""DESLIGADO desde a v4.8: não está declarado em nenhum perfil.

Observado no Kiro (Windows) em 22/10/2026: o hook PreToolUse do perfil do squad-lead também dispara nas
subagentes que ele chama, e o payload não traz o nome do agente. Ligado, este hook travava o intake-spec,
o planejador, o implementador e os revisores. Mantido só como referência.

Texto original: hook PreToolUse do PERFIL DO SQUAD-LEAD, trava dura da regra 4 (supervisor não produz).

As permissões de escrita do squad-lead não podem negar as pastas de trabalho, porque no Kiro elas
valem também para os subagentes. Os gatilhos de hook, segundo a documentação do Kiro, ficam isolados
por subagente. Por isso este hook, declarado só no perfil do squad-lead, bloqueia a escrita do
próprio squad-lead em .kiro/specs/, stories/, src/, tests/ e reviews/, sem atingir o intake-spec,
o planejador, o implementador e os revisores.

Saída 2 bloqueia a ferramenta (documentado para PreToolUse). Saída 0 libera.
Diagnóstico: o último payload recebido fica em .ash/hook-debug/supervisor.json (fora do git).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PRODUCAO = (".kiro/specs/", "stories/", "src/", "tests/", "reviews/")
CHAVES_CAMINHO = {"path", "file_path", "filePath", "file", "target", "targetFile", "filename", "paths"}


def caminhos(obj) -> list[str]:
    achados = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CHAVES_CAMINHO:
                if isinstance(v, str):
                    achados.append(v)
                elif isinstance(v, list):
                    achados += [x for x in v if isinstance(x, str)]
            else:
                achados += caminhos(v)
    elif isinstance(obj, list):
        for x in obj:
            achados += caminhos(x)
    return achados


def normalizar(c: str) -> str:
    c = c.replace("\\", "/")
    raiz = str(RAIZ).replace("\\", "/")
    if c.lower().startswith(raiz.lower()):
        c = c[len(raiz):]
    return re.sub(r"^\./", "", c.lstrip("/"))


def verificar(texto: str) -> str | None:
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        return None
    for c in caminhos(dados):
        n = normalizar(c)
        if n.startswith(PRODUCAO) or any(f"/{pasta}" in "/" + n for pasta in PRODUCAO):
            return n
    return None


def main() -> int:
    texto = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        pasta = RAIZ / ".ash" / "hook-debug"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "supervisor.json").write_text(texto or "(vazio)", encoding="utf-8")
    except Exception:
        pass
    alvo = verificar(texto) if texto.strip() else None
    if alvo:
        print(f"ASH: bloqueado. O squad-lead não produz artefatos (regra 4): '{alvo}' é trabalho de um "
              "agente de papel. Delegue ao intake-spec, planejador, implementador ou revisores.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
