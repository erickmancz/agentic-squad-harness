"""Leitura de specs ASH (front matter + blocos). Sem dependência externa."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SPECS = RAIZ / ".kiro" / "specs"

BLOCOS = [
    "1. Cabeçalho",
    "2. Objetivo e métrica",
    "3. História e contexto",
    "4. Aceite testável",
    "5. Referências de UX",
    "6. Dados e integrações",
    "7. Não funcionais",
    "8. Limites do agente",
    "9. Testes e exemplos",
    "10. Compatibilidade",
]
PERGUNTAS = "Perguntas em aberto"
FAIXAS = {"autonoma", "semiautonoma", "critica"}
STATUS = {"rascunho", "em_revisao", "aprovada"}
CAMPOS = ["id", "dono_po", "faixa", "dev_revisor", "versao", "status"]
RE_CA = re.compile(r"\bCA-(\d{2,3})\b")
VAZIOS = {"", "-", "nenhuma", "nenhuma.", "(nenhuma)", "não há", "não há.", "n/a"}


@dataclass
class Spec:
    caminho: Path
    meta: dict = field(default_factory=dict)
    secoes: dict = field(default_factory=dict)
    ordem: list = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.meta.get("id", "").strip()

    @property
    def criterios(self) -> list[str]:
        texto = self.secoes.get(BLOCOS[3], "")
        vistos = []
        for n in RE_CA.findall(texto):
            ca = f"CA-{n}"
            if ca not in vistos:
                vistos.append(ca)
        return vistos

    def perguntas_abertas(self) -> list[str]:
        itens = []
        for linha in self.secoes.get(PERGUNTAS, "").splitlines():
            t = linha.strip().lstrip("-*0123456789.) ").strip()
            if t.startswith("[x]") or t.startswith("[X]"):
                continue
            t = t.replace("[ ]", "").strip()
            baixo = t.lower()
            if baixo in VAZIOS or baixo.startswith(("nenhuma ", "nenhuma.", "nenhuma,", "não há ", "nao ha ")):
                continue
            itens.append(t)
        return itens


def ler(caminho: Path) -> Spec:
    texto = Path(caminho).read_text(encoding="utf-8")
    spec = Spec(caminho=Path(caminho))
    if texto.startswith("---"):
        partes = texto.split("---", 2)
        if len(partes) == 3:
            for linha in partes[1].splitlines():
                if ":" in linha and not linha.strip().startswith("#"):
                    k, v = linha.split(":", 1)
                    v = v.split("#", 1)[0]
                    spec.meta[k.strip()] = v.strip()
            texto = partes[2]
    atual = None
    for linha in texto.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", linha)
        if m:
            atual = m.group(1).strip()
            spec.ordem.append(atual)
            spec.secoes[atual] = ""
        elif atual is not None:
            spec.secoes[atual] += linha + "\n"
    return spec


def todas() -> list[Path]:
    if not PASTA_SPECS.exists():
        return []
    return sorted(PASTA_SPECS.glob("*/requirements.md"))
