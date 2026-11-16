#!/usr/bin/env python3
"""Confere que cada critério CA-NN de cada spec aprovada tem ao menos um teste.

O teste precisa citar '<ID da spec> CA-NN' (ex.: 'INS-014 CA-01') no nome, na docstring ou em comentário.
Nomes de função não aceitam hífen, então também vale 'ins_014_ca_01' no nome do teste.
Os arquivos de teste vêm do campo arquivos_teste do perfil de stack (ash-perfil.json); sem perfil,
vale o padrão Python tests/**/test_*.py.

Uso: python scripts/rastrear_aceite.py [ID ...] [--todas-as-specs]
Sem ID, confere todas as specs aprovadas (é o que o ci faz). Com um ou mais IDs, confere e informa só os critérios dessas specs.
Exit 0 se todos os critérios têm teste; exit 1 se faltar teste; exit 2 se um ID não existe entre as specs consideradas.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ash_spec as a  # noqa: E402

PADRAO_TESTES = ["tests/**/test_*.py"]


def padroes_de_teste() -> list[str]:
    """Padrões glob dos arquivos de teste, lidos do perfil de stack ativo."""
    arq = a.RAIZ / "ash-perfil.json"
    if not arq.exists():
        return PADRAO_TESTES
    try:
        return json.loads(arq.read_text(encoding="utf-8")).get("arquivos_teste") or PADRAO_TESTES
    except json.JSONDecodeError:
        return PADRAO_TESTES


def texto_dos_testes() -> str:
    arquivos = sorted({f for padrao in padroes_de_teste() for f in a.RAIZ.glob(padrao) if f.is_file()})
    return "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in arquivos)


def referencias(texto_testes: str, spec_id: str, ca: str) -> bool:
    alvo = f"{spec_id} {ca}"
    if alvo.lower() in texto_testes.lower():
        return True
    snake = re.sub(r"[^a-z0-9]+", "_", f"{spec_id}_{ca}".lower())
    return snake in texto_testes.lower()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--todas-as-specs", action="store_true", help="inclui specs que não estão aprovadas")
    p.add_argument("ids", nargs="*", help="IDs das specs a conferir (ex.: INS-017); sem ID, todas as specs aprovadas")
    args = p.parse_args(argv)

    texto = texto_dos_testes()

    pedidos = {i.strip().upper() for i in args.ids}
    encontrados = set()
    faltando = []
    total = 0
    for caminho in a.todas():
        spec = a.ler(caminho)
        if not args.todas_as_specs and spec.meta.get("status") != "aprovada":
            continue
        if pedidos and spec.id.upper() not in pedidos:
            continue
        encontrados.add(spec.id.upper())
        for ca in spec.criterios:
            total += 1
            if not referencias(texto, spec.id, ca):
                faltando.append(f"{spec.id} {ca}")
    ausentes = sorted(pedidos - encontrados)
    if ausentes:
        print(f"[ERRO] spec não encontrada entre as consideradas (aprovadas, ou todas com --todas-as-specs): "
              f"{', '.join(ausentes)}", file=sys.stderr)
        return 2
    if faltando:
        print(f"[ERRO] {len(faltando)} de {total} critério(s) sem teste:", file=sys.stderr)
        for f in faltando:
            print(f"  - {f}", file=sys.stderr)
        return 1
    alvo = f" de {', '.join(sorted(encontrados))}" if pedidos else ""
    print(f"[OK] {total} critério(s){alvo} com teste rastreado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
