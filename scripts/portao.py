#!/usr/bin/env python3
"""Portões humanos do ASH: a decisão humana acontece no CHAT do Kiro.

Modo padrão (declarado), o único que funciona no Kiro IDE hoje: o hook UserPromptSubmit recebe
"prompt": "" (observado em 21/10/2026), então o texto da mensagem não chega a scripts.

1. squad-lead: python ash.py portao abrir --acao <acao> --spec <ID> --resumo "..."
2. squad-lead mostra a decisão no chat e pede: Responda APROVO para seguir.
3. humano responde APROVO.
4. squad-lead: python ash.py <comando do portão> --mensagem "<texto literal do humano>"
   O comando exige portão aberto para a MESMA ação e spec e uma palavra de aprovação no texto.
   Registra canal chat-declarado, texto literal, id do portão e horário.
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / ".ash" / "gate"
PENDENTE = PASTA / "pendente.json"
CONFIRMACAO = PASTA / "confirmacao.json"
USADAS = PASTA / "usadas.jsonl"
HOOK_OK = PASTA / "hook_texto_ok"   # só existe quando o hook já recebeu o TEXTO de uma mensagem

ACOES = {"aprovar-po", "aprovar-design", "aprovar-dev", "aprovar-homologacao", "merge", "bootstrap", "teardown",
         "publicar-harness", "aprovar-prd", "publicar-proto"}
RE_SIM = re.compile(r"\b(aprovo|aprovado|aprovada|confirmo|confirmado|merge|criar stacks|remover stacks|pode seguir)\b",
                    re.IGNORECASE)
RE_NAO = re.compile(r"\b(n[aã]o|nunca|ainda\s+n[aã]o)\s+(est[aá]\s+|foi\s+|ser[aá]\s+)?(aprovo|aprovado|aprovada|confirmo|confirmado|pode)\b"
                    r"|\b(reprovo|reprovado|recuso|cancela|cancele|cancelar)\b", re.IGNORECASE)


def agora() -> datetime:
    return datetime.now(timezone.utc)


def _ts(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _ler(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def validade() -> timedelta:
    return timedelta(minutes=int(os.environ.get("ASH_GATE_MINUTOS", "30")))


def abrir(acao: str, spec: str, resumo: str) -> dict:
    if acao not in ACOES:
        raise SystemExit(f"[ERRO] ação '{acao}' inválida; use {sorted(ACOES)}")
    PASTA.mkdir(parents=True, exist_ok=True)
    p = {"id": uuid.uuid4().hex[:8], "acao": acao, "spec": spec, "resumo": resumo, "aberto_em": _ts(agora())}
    PENDENTE.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    if CONFIRMACAO.exists():
        CONFIRMACAO.unlink()
    return p


CHAVES_TEXTO = ("prompt", "user_prompt", "userPrompt", "USER_PROMPT", "message", "text", "content", "input", "query")


def _buscar_texto(obj) -> str:
    """Procura, em qualquer nível do JSON, o primeiro texto em uma chave típica de mensagem."""
    if isinstance(obj, dict):
        for k in CHAVES_TEXTO:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v
        for v in obj.values():
            achado = _buscar_texto(v)
            if achado:
                return achado
    elif isinstance(obj, list):
        for v in obj:
            achado = _buscar_texto(v)
            if achado:
                return achado
    return ""


def texto_do_prompt() -> str:
    bruto = ""
    if not sys.stdin.isatty():
        try:
            bruto = sys.stdin.read()
        except Exception:
            bruto = ""
    texto = os.environ.get("USER_PROMPT", "")
    if not texto and bruto.strip():
        try:
            texto = _buscar_texto(json.loads(bruto))
        except Exception:
            texto = bruto
    return texto


def eh_aprovacao(texto: str) -> bool:
    return bool(RE_SIM.search(texto)) and not RE_NAO.search(texto)


def capturar(texto: str) -> str:
    """Chamado pelo hook UserPromptSubmit. Devolve a mensagem que vai para o contexto do agente."""
    PASTA.mkdir(parents=True, exist_ok=True)
    pend = _ler(PENDENTE)
    if not texto.strip():
        return ""
    HOOK_OK.write_text(_ts(agora()), encoding="utf-8")
    if not eh_aprovacao(texto):
        if pend:
            return (f"[ASH] Portão {pend['acao']} {pend['spec']} continua ABERTO. "
                    "A mensagem do humano não é uma aprovação.")
        return ""
    if not pend:
        return "[ASH] Mensagem de aprovação recebida, mas não há portão aberto. Nada foi registrado."
    aberto = datetime.strptime(pend["aberto_em"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if agora() - aberto > validade():
        PENDENTE.unlink()
        return f"[ASH] Portão {pend['acao']} {pend['spec']} expirou. Abra de novo."
    conf = {**pend, "texto_humano": texto.strip()[:500], "confirmado_em": _ts(agora()), "canal": "chat-hook"}
    CONFIRMACAO.write_text(json.dumps(conf, ensure_ascii=False, indent=2), encoding="utf-8")
    PENDENTE.unlink()
    return (f"[ASH] CONFIRMAÇÃO HUMANA REGISTRADA para {pend['acao']} {pend['spec']} "
            f"(portão {pend['id']}). Execute agora o comando desse ato humano.")


def _confirmacao_hook(acao: str, spec: str) -> dict | None:
    conf = _ler(CONFIRMACAO)
    if conf and conf.get("acao") == acao and conf.get("spec") == spec:
        confirmado = datetime.strptime(conf["confirmado_em"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if agora() - confirmado <= validade():
            return conf
    return None


def _erro_sem_confirmacao(acao: str, spec: str) -> SystemExit:
    return SystemExit(f"[PORTÃO] sem confirmação humana para {acao} {spec}. Abra o portão "
                      f"(python ash.py portao abrir --acao {acao} --spec {spec} --resumo \"...\"), mostre a decisão, "
                      "espere o APROVO do humano no chat e rode o comando com --mensagem \"<texto literal do humano>\".")


def verificar(acao: str, spec: str, mensagem: str | None = None) -> None:
    """Confere, sem consumir, se a confirmação humana é válida."""
    if _confirmacao_hook(acao, spec):
        return
    pend = _ler(PENDENTE)
    if mensagem and eh_aprovacao(mensagem) and pend and pend["acao"] == acao and pend["spec"] == spec:
        return
    raise _erro_sem_confirmacao(acao, spec)


def consumir(acao: str, spec: str, mensagem: str | None = None) -> dict:
    """Modo padrão (declarado): portão aberto para esta ação e spec + texto literal do humano com APROVO.
    Se algum dia o hook UserPromptSubmit entregar o texto, a confirmação capturada também é aceita."""
    conf = _confirmacao_hook(acao, spec)
    if conf:
        CONFIRMACAO.unlink()
    else:
        pend = _ler(PENDENTE)
        if not (mensagem and eh_aprovacao(mensagem)):
            raise _erro_sem_confirmacao(acao, spec)
        if not pend or pend["acao"] != acao or pend["spec"] != spec:
            raise SystemExit(f"[PORTÃO] abra antes o portão {acao} {spec} e mostre a decisão ao humano.")
        PENDENTE.unlink()
        conf = {**pend, "texto_humano": mensagem.strip()[:500], "confirmado_em": _ts(agora()),
                "canal": "chat-declarado"}
    PASTA.mkdir(parents=True, exist_ok=True)
    with USADAS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**conf, "usada_em": _ts(agora())}, ensure_ascii=False) + "\n")
    return conf


def status() -> str:
    pend, conf = _ler(PENDENTE), _ler(CONFIRMACAO)
    linhas = ["modo do portão: declarado (APROVO do humano no chat + --mensagem com o texto literal)"]
    linhas.append(f"portão aberto: {pend['acao']} {pend['spec']} ({pend['id']})" if pend else "portão aberto: nenhum")
    linhas.append(f"confirmação pendente de uso: {conf['acao']} {conf['spec']}" if conf else "confirmação pendente de uso: nenhuma")
    return "\n".join(linhas)


def main_hook() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    msg = capturar(texto_do_prompt())
    if msg:
        print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main_hook())
