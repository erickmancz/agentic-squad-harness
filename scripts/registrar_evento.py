#!/usr/bin/env python3
"""Grava um evento de métrica ASH em .ash/events/AAAA-MM-DD.jsonl.

Uso:
  python scripts/registrar_evento.py <tipo> --spec INS-014 [--ator agente|humano] [--faixa semiautonoma] [--detalhe chave=valor ...]

Tipos: spec_criada, spec_aprovada, task_concluida, reescrita_humana, ci_executado,
       aprovacao_merge, merge, defeito_aberto, design_aprovado,
       descoberta_etapa, prd_aprovado, proto_publicado
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / ".ash" / "events"
TIPOS = {
    "spec_criada", "spec_aprovada", "task_concluida", "reescrita_humana",
    "ci_executado", "aprovacao_merge", "merge", "defeito_aberto", "design_aprovado",
    "descoberta_etapa", "prd_aprovado", "proto_publicado",
}


def squad_atual() -> str:
    cfg = RAIZ / ".ash" / "config.env"
    if cfg.exists():
        for linha in cfg.read_text(encoding="utf-8").splitlines():
            if linha.startswith("ASH_SQUAD="):
                return linha.split("=", 1)[1].strip().strip('"')
    return os.environ.get("ASH_SQUAD", "minha-squad")


def gravar(tipo: str, spec: str, ator: str = "humano", faixa: str = "", detalhe: dict | None = None,
           ts: str | None = None) -> dict:
    if tipo not in TIPOS:
        raise ValueError(f"tipo '{tipo}' inválido; use {sorted(TIPOS)}")
    if ator not in {"agente", "humano"}:
        raise ValueError("ator deve ser 'agente' ou 'humano'")
    agora = ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    evento = {
        "ts": agora,
        "squad": squad_atual(),
        "spec_id": spec,
        "tipo": tipo,
        "faixa": faixa,
        "ator": ator,
        "usuario": getpass.getuser(),
        "detalhe": detalhe or {},
    }
    PASTA.mkdir(parents=True, exist_ok=True)
    arquivo = PASTA / f"{agora[:10]}.jsonl"
    with arquivo.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")
    return evento


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tipo")
    p.add_argument("--spec", required=True)
    p.add_argument("--ator", default="humano")
    p.add_argument("--faixa", default="")
    p.add_argument("--detalhe", nargs="*", default=[], help="pares chave=valor")
    args = p.parse_args(argv)
    detalhe = dict(x.split("=", 1) for x in args.detalhe if "=" in x)
    try:
        ev = gravar(args.tipo, args.spec, args.ator, args.faixa, detalhe)
    except ValueError as e:
        print(f"[ERRO] {e}", file=sys.stderr)
        return 1
    print(f"[OK] evento {ev['tipo']} de {ev['spec_id']} registrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
