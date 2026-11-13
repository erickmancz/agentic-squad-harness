#!/usr/bin/env python3
"""Valida specs ASH de dez blocos.

Uso:
  python scripts/validar_spec.py <requirements.md> [...]
  python scripts/validar_spec.py --todas
  python scripts/validar_spec.py --todas --sem-status   # ignora status e perguntas (rascunho)

Exit 0 quando tudo está ok; exit 1 com a lista de erros em stderr.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ash_spec as a  # noqa: E402


def validar(spec: a.Spec, checar_status: bool = True) -> list[str]:
    erros = []
    for campo in a.CAMPOS:
        if campo not in spec.meta:
            erros.append(f"front matter sem o campo '{campo}'")
    if not spec.id:
        erros.append("campo 'id' vazio")
    faixa = spec.meta.get("faixa", "")
    if faixa not in a.FAIXAS:
        erros.append(f"faixa '{faixa}' inválida; use {sorted(a.FAIXAS)}")
    if faixa == "critica" and not spec.meta.get("dev_revisor", "").strip():
        erros.append("faixa critica exige dev_revisor preenchido")
    status = spec.meta.get("status", "")
    if status not in a.STATUS:
        erros.append(f"status '{status}' inválido; use {sorted(a.STATUS)}")

    presentes = [s for s in spec.ordem if s in a.BLOCOS]
    for bloco in a.BLOCOS:
        if bloco not in spec.secoes:
            erros.append(f"bloco ausente: '## {bloco}'")
        elif not spec.secoes[bloco].strip():
            erros.append(f"bloco vazio: '## {bloco}'")
    if presentes and presentes != [b for b in a.BLOCOS if b in presentes]:
        erros.append("blocos fora da ordem do template")
    if a.PERGUNTAS not in spec.secoes:
        erros.append(f"seção ausente: '## {a.PERGUNTAS}'")
    if a.BLOCOS[3] in spec.secoes and not spec.criterios:
        erros.append("'Aceite testável' sem nenhum critério CA-NN")

    if checar_status and status == "aprovada":
        abertas = spec.perguntas_abertas()
        if abertas:
            erros.append(f"status aprovada com {len(abertas)} pergunta(s) em aberto: {abertas[0][:80]}")
    return erros


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("arquivos", nargs="*")
    p.add_argument("--todas", action="store_true", help="valida todas as specs em .kiro/specs/")
    p.add_argument("--sem-status", action="store_true", help="não cobra status nem perguntas em aberto")
    p.add_argument("--exigir-aprovada", action="store_true", help="falha se alguma spec não estiver aprovada")
    args = p.parse_args(argv)

    caminhos = [Path(x) for x in args.arquivos]
    if args.todas:
        caminhos += a.todas()
    if not caminhos:
        print("nenhuma spec encontrada", file=sys.stderr)
        return 0 if args.todas else 1

    falhou = False
    for c in caminhos:
        if not c.exists():
            print(f"[ERRO] {c}: arquivo não existe", file=sys.stderr)
            falhou = True
            continue
        spec = a.ler(c)
        erros = validar(spec, checar_status=not args.sem_status)
        if args.exigir_aprovada and spec.meta.get("status") != "aprovada":
            erros.append("spec não está aprovada")
        if erros:
            falhou = True
            print(f"[ERRO] {c} ({spec.id or 'sem id'})", file=sys.stderr)
            for e in erros:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"[OK] {c} ({spec.id}, faixa {spec.meta.get('faixa')}, status {spec.meta.get('status')}, {len(spec.criterios)} critério(s))")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
