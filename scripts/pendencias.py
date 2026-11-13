#!/usr/bin/env python3
"""Lista o que depende de decisão humana: perguntas em aberto, specs sem aprovação e merges pendentes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ash_spec as a  # noqa: E402

APROVACOES = a.RAIZ / ".ash" / "approvals"


def branches_feat() -> list[str]:
    try:
        out = subprocess.run(["git", "branch", "--list", "feat/*", "--no-merged", "main"],
                             cwd=a.RAIZ, capture_output=True, text=True, timeout=10)
        return [b.strip(" *") for b in out.stdout.splitlines() if b.strip()]
    except Exception:
        return []


def main() -> int:
    linhas = []
    for c in a.todas():
        s = a.ler(c)
        abertas = s.perguntas_abertas()
        status = s.meta.get("status")
        if abertas:
            linhas.append(f"- {s.id}: {len(abertas)} pergunta(s) em aberto para o PO")
        if status != "aprovada":
            linhas.append(f"- {s.id}: status '{status}', aguardando portão aprovar-po")
        if s.meta.get("faixa") == "critica" and not s.meta.get("dev_revisor", "").strip():
            linhas.append(f"- {s.id}: faixa critica sem dev_revisor")
        arq = APROVACOES / f"{s.id}.json"
        if status == "aprovada" and arq.exists():
            dados = json.loads(arq.read_text(encoding="utf-8"))
            papeis = {x["papel"] for x in dados.get("aprovacoes", [])}
            if "design" not in papeis:
                linhas.append(f"- {s.id}: aguardando portão aprovar-design")
            if s.meta.get("faixa") == "critica" and "dev" not in papeis:
                linhas.append(f"- {s.id}: aguardando portão aprovar-dev")
    for b in branches_feat():
        linhas.append(f"- branch {b} ainda não entrou na main (aguardando portão merge)")
    if linhas:
        print("Pendências humanas ASH:")
        print("\n".join(linhas))
    else:
        print("Pendências humanas ASH: nenhuma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
