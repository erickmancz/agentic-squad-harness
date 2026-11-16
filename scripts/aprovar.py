#!/usr/bin/env python3
"""Registro de aprovações humanas do ASH (biblioteca usada pelo ash.py).

A aprovação acontece no CHAT: o humano responde APROVO a um portão aberto, o squad-lead passa a
frase literal em --mensagem e o ash.py chama estas funções com a evidência (texto literal do
humano, canal chat-declarado e horário). Use pelo comando:

  python ash.py aprovar INS-016 --papel po --nome "Nome do PO"
  python ash.py aprovar INS-016 --papel design --nome "Nome do FDE"
  python ash.py aprovar INS-016 --papel dev --nome "Nome do dev_revisor" --branch feat/ins-016
  python ash.py merge feat/ins-016 INS-016 --fde "Nome do FDE"
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ash_spec as a  # noqa: E402
import registrar_evento as ev  # noqa: E402
from validar_spec import validar  # noqa: E402

PASTA = a.RAIZ / ".ash" / "approvals"


def agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def achar_spec(spec_id: str) -> Path:
    for c in a.todas():
        if a.ler(c).id == spec_id:
            return c
    raise SystemExit(f"[ERRO] spec {spec_id} não encontrada em .kiro/specs/")


def commit_da_branch(branch: str) -> str:
    r = subprocess.run(["git", "rev-parse", branch], cwd=a.RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"[ERRO] branch '{branch}' não existe")
    return r.stdout.strip()


def registrar_aprovacao(spec_id: str, papel: str, nome: str, branch: str, commit: str, evidencia: dict) -> None:
    """Grava a aprovação em .ash/approvals/<ID>.json com a evidência do chat."""
    arq = PASTA / f"{spec_id}.json"
    dados = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {"spec_id": spec_id, "aprovacoes": []}
    dados["aprovacoes"] = [x for x in dados["aprovacoes"] if x["papel"] != papel] + [{
        "papel": papel, "nome": nome, "branch": branch, "commit": commit, "ts": agora(),
        "canal": evidencia.get("canal", ""), "texto_humano": evidencia.get("texto_humano", ""),
        "portao": evidencia.get("id", ""),
        **({"evidencia": evidencia["evidencia"]} if evidencia.get("evidencia") else {}),
    }]
    PASTA.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def checar_spec_aprovavel(caminho: Path) -> None:
    spec = a.ler(caminho)
    erros = validar(spec, checar_status=False)
    abertas = spec.perguntas_abertas()
    if abertas:
        erros.append(f"{len(abertas)} pergunta(s) em aberto")
    if erros:
        raise SystemExit("[ERRO] spec não pode ser aprovada:\n  - " + "\n  - ".join(erros))


def aprovar_spec(caminho: Path, nome: str, evidencia: dict) -> None:
    checar_spec_aprovavel(caminho)
    spec = a.ler(caminho)
    texto = caminho.read_text(encoding="utf-8")
    texto = re.sub(r"^status:.*$", "status: aprovada", texto, count=1, flags=re.M)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    registrar_aprovacao(spec.id, "po", nome, "", "", evidencia)
    ev.gravar("spec_aprovada", spec.id, "humano", spec.meta["faixa"],
              {"po": nome, "canal": evidencia.get("canal", "")})
    print(f"[OK] spec {spec.id} aprovada por {nome} ({evidencia.get('canal', '')})")


def checar_merge_aprovavel(caminho: Path, papel: str, nome: str) -> None:
    spec = a.ler(caminho)
    if spec.meta.get("status") != "aprovada":
        raise SystemExit("[ERRO] a spec precisa estar aprovada pelo PO antes da aprovação de merge")
    if papel == "dev":
        dev = spec.meta.get("dev_revisor", "").strip()
        if not dev:
            raise SystemExit("[ERRO] a spec não tem dev_revisor")
        if dev.lower() != nome.lower():
            raise SystemExit(f"[ERRO] o dev_revisor desta spec é '{dev}', não '{nome}'")


def aprovar_dev(caminho: Path, nome: str, branch: str, evidencia: dict) -> None:
    checar_merge_aprovavel(caminho, "dev", nome)
    spec = a.ler(caminho)
    commit = commit_da_branch(branch)
    registrar_aprovacao(spec.id, "dev", nome, branch, commit, evidencia)
    ev.gravar("aprovacao_merge", spec.id, "humano", spec.meta["faixa"],
              {"papel": "dev", "commit": commit[:12], "canal": evidencia.get("canal", "")})
    print(f"[OK] aprovação do dev_revisor registrada para {spec.id} no commit {commit[:8]}")


if __name__ == "__main__":
    print(__doc__)
    sys.exit(0)
