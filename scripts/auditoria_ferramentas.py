#!/usr/bin/env python3
"""Auditoria das ferramentas do harness (requirements-tools.txt) com riscos aceitos de forma explícita e revisável.

Uso (pelo ash.py, com o Python da .venv-tools): python ash.py testar-harness --auditoria

Roda o pip-audit sobre o requirements-tools.txt e compara com tests_harness/auditoria_ferramentas.json, que guarda os
aceites de vulnerabilidades que o autor do harness decidiu aceitar. Mostra três listas:
  1. CVEs novos (sem aceite);
  2. aceites vencidos (data de revisão passada);
  3. aceites que podem sair (a vulnerabilidade não aparece mais, ou o Semgrep mais recente já declara versões corrigidas).
Sai com código 1 se houver CVE novo ou aceite vencido; 2 se não conseguiu auditar; 0 caso contrário.
Nunca roda no CI de um projeto: o CI roda `testar-harness` sem flag. Precisa de rede (pip-audit e PyPI).

O topo do módulo usa só a biblioteca padrão (o ash.py o importa com o Python do sistema); o `packaging` é importado
só dentro das funções que comparam versões, que rodam na .venv-tools.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ_ACEITES = RAIZ / "tests_harness" / "auditoria_ferramentas.json"
ARQ_REQUIREMENTS = RAIZ / "requirements-tools.txt"
URL_SEMGREP = "https://pypi.org/pypi/semgrep/json"

PRAZO_REVISAO_DIAS = 90
PAPEIS_VALIDOS = ("autor do harness",)
FRASE_VALIDADE = "aceite válido para o template; cada cliente revalida com o seu time de segurança"
CAMPOS = ("id", "pacote", "versao_afetada", "motivo", "fonte", "decidido_em", "revisar_em", "decidido_por",
          "validade", "sai_quando")
RE_ID = re.compile(r"^(CVE-\d{4}-\d{4,}|GHSA(-[a-z0-9]{4}){3}|PYSEC-\d{4}-\d+)$")


class ErroAuditoria(Exception):
    """Falha esperada da auditoria, com mensagem pronta para o usuário."""


def hoje_utc() -> date:
    """Data de hoje em UTC."""
    return datetime.now(timezone.utc).date()


def _data(texto) -> date | None:
    try:
        return date.fromisoformat(str(texto))
    except ValueError:
        return None


# ---------------------------------------------------------------- arquivo de aceites
def carregar(caminho: Path = ARQ_ACEITES) -> dict:
    """Lê o arquivo de aceites (JSON em UTF-8)."""
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ErroAuditoria(f"Não consegui ler {Path(caminho).name}: {e}")


def validar(dados: dict) -> list[str]:
    """Confere o arquivo de aceites e devolve a lista de erros (vazia se está tudo certo)."""
    erros = []
    aceites = dados.get("aceites") if isinstance(dados, dict) else None
    if not isinstance(aceites, list):
        return ["o arquivo precisa ter a lista 'aceites'"]
    vistos = set()
    for i, a in enumerate(aceites, 1):
        rotulo = f"aceite {i} ({a.get('id', '?') if isinstance(a, dict) else '?'})"
        if not isinstance(a, dict):
            erros.append(f"{rotulo}: deve ser um objeto")
            continue
        for campo in CAMPOS:
            if not a.get(campo):
                erros.append(f"{rotulo}: falta o campo '{campo}'")
        if a.get("id") and not RE_ID.match(a["id"]):
            erros.append(f"{rotulo}: id '{a['id']}' não parece um CVE, GHSA ou PYSEC")
        chave = (a.get("id"), a.get("pacote"))
        if chave in vistos:
            erros.append(f"{rotulo}: aceite repetido para o mesmo id e pacote")
        vistos.add(chave)
        decidido, revisar = _data(a.get("decidido_em")), _data(a.get("revisar_em"))
        if a.get("decidido_em") and decidido is None:
            erros.append(f"{rotulo}: decidido_em deve ser AAAA-MM-DD")
        if a.get("revisar_em") and revisar is None:
            erros.append(f"{rotulo}: revisar_em deve ser AAAA-MM-DD")
        if decidido and revisar:
            if revisar <= decidido:
                erros.append(f"{rotulo}: revisar_em deve ser depois de decidido_em")
            elif revisar - decidido > timedelta(days=PRAZO_REVISAO_DIAS):
                erros.append(f"{rotulo}: revisar_em passa de {PRAZO_REVISAO_DIAS} dias depois de decidido_em; "
                             "para estender, faça uma nova decisão com nova data de decisão")
        if a.get("decidido_por") and a["decidido_por"] not in PAPEIS_VALIDOS:
            erros.append(f"{rotulo}: decidido_por deve ser um papel ({', '.join(PAPEIS_VALIDOS)}), nunca nome de pessoa")
        if a.get("validade") and a["validade"] != FRASE_VALIDADE:
            erros.append(f"{rotulo}: 'validade' deve ser exatamente: {FRASE_VALIDADE}")
        sai = a.get("sai_quando")
        if sai:
            exige = sai.get("exige") if isinstance(sai, dict) else None
            if not (isinstance(sai, dict) and sai.get("pacote_que_declara") and isinstance(exige, dict)
                    and exige.get("pacote") and exige.get("minimo")):
                erros.append(f"{rotulo}: sai_quando precisa de pacote_que_declara e exige.pacote e exige.minimo")
    return erros


def vencidos(dados: dict, hoje: date) -> list[dict]:
    """Aceites cuja data de revisão já passou."""
    saida = []
    for a in dados.get("aceites", []):
        revisar = _data(a.get("revisar_em"))
        if revisar is None or revisar < hoje:
            saida.append(a)
    return saida


# ---------------------------------------------------------------- pip-audit
def vulns_do_json(texto: str) -> list[dict]:
    """Extrai do JSON do pip-audit uma lista de {pacote, versao, ids, corrigida_em}, uma por vulnerabilidade."""
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as e:
        raise ErroAuditoria(f"A saída do pip-audit não é JSON: {e}")
    achadas = []
    for dep in dados.get("dependencies", []):
        for v in dep.get("vulns", []) or []:
            achadas.append({"pacote": dep.get("name", ""), "versao": dep.get("version", ""),
                            "ids": [v.get("id", "")] + list(v.get("aliases", []) or []),
                            "corrigida_em": list(v.get("fix_versions", []) or [])})
    return achadas


def executar_pip_audit(requirements: Path = ARQ_REQUIREMENTS, executar=subprocess.run) -> list[dict]:
    """Roda `python -m pip_audit -r requirements -f json` e devolve as vulnerabilidades (sem ignorar nenhuma)."""
    cmd = [sys.executable, "-m", "pip_audit", "-r", str(requirements), "-f", "json", "--progress-spinner", "off"]
    try:
        r = executar(cmd, capture_output=True, text=True, encoding="utf-8", cwd=RAIZ)
    except OSError as e:
        raise ErroAuditoria(f"Não consegui rodar o pip-audit: {e}")
    if r.returncode not in (0, 1):
        resto = (r.stderr or "").strip().splitlines()[-1:] or ["sem detalhe"]
        raise ErroAuditoria(f"O pip-audit falhou (código {r.returncode}; ele precisa de rede): {resto[0]}")
    return vulns_do_json(r.stdout)


# ---------------------------------------------------------------- classificação
def classificar(achadas: list[dict], dados: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Devolve (novos, em_uso, sem_uso): vulnerabilidades sem aceite, aceites que cobrem algo achado e aceites sem achado."""
    aceites = dados.get("aceites", [])
    novos, usados = [], set()
    for v in achadas:
        cobertos = [i for i, a in enumerate(aceites) if a.get("pacote") == v["pacote"] and a.get("id") in v["ids"]]
        if cobertos:
            usados.update(cobertos)
        else:
            novos.append(v)
    em_uso = [a for i, a in enumerate(aceites) if i in usados]
    sem_uso = [a for i, a in enumerate(aceites) if i not in usados]
    return novos, em_uso, sem_uso


def _requisito(requires_dist: list[str], pacote: str):
    from packaging.requirements import Requirement
    alvo = pacote.lower().replace("_", "-")
    for linha in requires_dist or []:
        try:
            req = Requirement(linha)
        except Exception:
            continue
        if req.name.lower().replace("_", "-") == alvo and not (req.marker and "extra" in str(req.marker)):
            return req
    return None


def pode_sair_pelo_semgrep(aceite: dict, requires_dist: list[str], versao: str) -> str:
    """Motivo (texto) se o Semgrep da versão dada já declara uma faixa que admite a versão corrigida; vazio se não."""
    from packaging.version import Version
    sai = aceite["sai_quando"]
    req = _requisito(requires_dist, sai["exige"]["pacote"])
    if req is None:
        return f"o {sai['pacote_que_declara']} {versao} não declara mais {sai['exige']['pacote']}"
    if req.specifier.contains(Version(sai["exige"]["minimo"]), prereleases=True):
        return (f"o {sai['pacote_que_declara']} {versao} declara {req.name}{req.specifier}, que admite "
                f"{sai['exige']['minimo']} ou superior")
    return ""


def buscar_json(url: str, timeout: int = 30) -> dict:
    """GET de uma URL JSON (PyPI)."""
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def semgrep_mais_recente(buscar=buscar_json) -> tuple[str, str, list[str]]:
    """(versão, data de publicação AAAA-MM-DD, requires_dist) do Semgrep mais recente no PyPI."""
    dados = buscar(URL_SEMGREP)
    versao = dados["info"]["version"]
    arquivos = dados.get("releases", {}).get(versao) or []
    data = min((f["upload_time"] for f in arquivos), default="")[:10]
    return versao, data, list(dados["info"].get("requires_dist") or [])


# ---------------------------------------------------------------- relatório
def _linha_aceite(a: dict) -> str:
    return f"{a['id']} ({a['pacote']} {a['versao_afetada']}), revisar em {a['revisar_em']}"


def main(argv=None, *, executar=subprocess.run, buscar=buscar_json, hoje: date | None = None, saida=print,
         arq_aceites: Path = ARQ_ACEITES, requirements: Path = ARQ_REQUIREMENTS) -> int:
    """Roda a auditoria e imprime as três listas. Código 0, 1 (CVE novo ou aceite vencido) ou 2 (não conseguiu auditar)."""
    hoje = hoje or hoje_utc()
    try:
        dados = carregar(arq_aceites)
        erros = validar(dados)
        if erros:
            raise ErroAuditoria("arquivo de aceites inválido:\n  - " + "\n  - ".join(erros))
        achadas = executar_pip_audit(requirements, executar)
    except ErroAuditoria as e:
        saida(f"[ERRO] {e}")
        return 2
    novos, em_uso, sem_uso = classificar(achadas, dados)
    expirados = vencidos(dados, hoje)

    pode_sair = [(a, "a vulnerabilidade não aparece mais na auditoria") for a in sem_uso]
    aviso_rede = ""
    try:
        versao, data, requires_dist = semgrep_mais_recente(buscar)
        for a in em_uso:
            motivo = pode_sair_pelo_semgrep(a, requires_dist, versao)
            if motivo:
                pode_sair.append((a, f"{motivo} (publicado em {data}; confira a regra de 14 dias antes de atualizar)"))
        info_semgrep = f"Semgrep mais recente no PyPI: {versao} ({data})"
    except Exception as e:  # rede fora do ar ou formato inesperado: a lista 'podem sair' fica incompleta, sem falhar
        info_semgrep = "Semgrep mais recente no PyPI: não consultado"
        aviso_rede = f"[AVISO] não consegui consultar o PyPI ({type(e).__name__}); a lista 'podem sair' ficou incompleta"

    saida(f"== Auditoria das ferramentas do harness ({Path(requirements).name}) em {hoje.isoformat()} ==")
    saida(info_semgrep)
    saida("")
    saida(f"CVEs novos (sem aceite): {len(novos)}")
    for v in novos:
        saida(f"  - {v['ids'][0]} em {v['pacote']} {v['versao']} (corrigida em: {', '.join(v['corrigida_em']) or 'sem correção publicada'})")
    saida(f"Aceites vencidos (revisão passada): {len(expirados)}")
    for a in expirados:
        saida(f"  - {_linha_aceite(a)}: decida de novo (nova data de decisão) ou remova")
    saida(f"Aceites que podem sair: {len(pode_sair)}")
    for a, motivo in pode_sair:
        saida(f"  - {a['id']} ({a['pacote']}): {motivo}")
    if aviso_rede:
        saida(aviso_rede)
    saida(f"Aceites em vigor: {len(em_uso)} (cada cliente revalida com o seu time de segurança)")
    if novos or expirados:
        saida("AUDITORIA: PENDENTE (CVE novo ou aceite vencido exige decisão do autor do harness)")
        return 1
    saida("AUDITORIA: OK")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
