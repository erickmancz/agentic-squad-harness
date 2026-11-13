#!/usr/bin/env python3
"""Relatório local do ASH: linha do tempo e métricas de cada spec a partir de .ash/events (sem AWS).

Usa o mesmo cálculo da Lambda de relatório (infra/lambdas/report/metricas.py).
Saída: tabela no terminal e .ash/relatorio.md (fora do git).
Créditos do Kiro não aparecem aqui: o Kiro mostra "Est. Credits Used" por turno só na tela do chat.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / ".ash" / "events"
sys.path.insert(0, str(RAIZ / "infra" / "lambdas" / "report"))

MARCOS = [("spec_criada", "spec criada"), ("spec_aprovada", "aprovada pelo PO"),
          ("design_aprovado", "design aprovado"), ("merge", "merge na main")]


def eventos() -> list[dict]:
    lista = []
    if PASTA.exists():
        for arq in sorted(PASTA.rglob("*.jsonl")):
            for linha in arq.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if linha:
                    try:
                        lista.append(json.loads(linha))
                    except json.JSONDecodeError:
                        pass
    vistos, unicos = set(), []
    for e in sorted(lista, key=lambda x: x.get("ts", "")):
        chave = (e.get("ts"), e.get("spec_id"), e.get("tipo"))
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(e)
    return unicos


def _dt(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _dur(a: str, b: str) -> str:
    seg = int((_dt(b) - _dt(a)).total_seconds())
    if seg < 0:
        return "-"
    h, m = divmod(seg // 60, 60)
    return f"{h}h{m:02d}min" if h else f"{m}min"


def linha_do_tempo(evs: list[dict], spec: str) -> list[str]:
    meus = [e for e in evs if e.get("spec_id") == spec]
    if not meus:
        return [f"Sem eventos para {spec}."]
    faixa = next((e["faixa"] for e in reversed(meus) if e.get("faixa")), "sem faixa")
    out = [f"## {spec} (faixa {faixa})", "", "| Marco | Quando (UTC) | Desde o marco anterior |", "|---|---|---|"]
    anterior = None
    for tipo, rotulo in MARCOS:
        e = next((x for x in meus if x["tipo"] == tipo), None) if tipo != "merge" else \
            next((x for x in reversed(meus) if x["tipo"] == tipo), None)
        if e:
            out.append(f"| {rotulo} | {e['ts'].replace('T', ' ').rstrip('Z')} | {_dur(anterior, e['ts']) if anterior else '-'} |")
            anterior = e["ts"]
        else:
            out.append(f"| {rotulo} | (sem registro) | - |")
    criada = next((x for x in meus if x["tipo"] == "spec_criada"), None)
    merge = next((x for x in reversed(meus) if x["tipo"] == "merge"), None)
    ci = [x for x in meus if x["tipo"] == "ci_executado"]
    verdes = sum(1 for x in ci if (x.get("detalhe") or {}).get("status") == "ok")
    reescritas = sum(1 for x in meus if x["tipo"] == "reescrita_humana") if merge else "-"
    canais = sorted({(x.get("detalhe") or {}).get("canal", "") for x in meus if x["tipo"] in ("spec_aprovada", "design_aprovado", "merge")} - {""})
    out += ["", "| Indicador | Valor |", "|---|---|",
            f"| Da spec criada ao merge | {_dur(criada['ts'], merge['ts']) if criada and merge else '(incompleto)'} |",
            f"| Execuções do CI local | {len(ci)} ({verdes} verdes) |",
            f"| Reescritas humanas declaradas no merge | {reescritas} |",
            f"| Canal das decisões humanas | {', '.join(canais) or '-'} |"]
    return out


def main(spec: str | None = None) -> int:
    evs = eventos()
    specs = [spec] if spec else sorted({e.get("spec_id") for e in evs if e.get("spec_id") not in (None, "", "HARNESS", "AWS")})
    if not specs:
        print("Sem eventos em .ash/events.")
        return 0
    texto = ["# Relatório local ASH", ""]
    for s in specs:
        texto += linha_do_tempo(evs, s) + [""]
    texto.append("Créditos do Kiro: anote o \"Est. Credits Used\" de cada turno na tela do chat; o Kiro não expõe esse número a scripts.")
    saida = "\n".join(texto)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(saida)
    destino = RAIZ / ".ash" / "relatorio.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(saida + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
