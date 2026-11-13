"""Cálculo das métricas ASH a partir dos itens da tabela. Funções puras."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median


def _dt(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _horas(a: str, b: str) -> float:
    return round((_dt(b) - _dt(a)).total_seconds() / 3600, 2)


def calcular(itens: list[dict], agora: datetime | None = None) -> list[dict]:
    """Devolve linhas {squad, metrica, faixa, valor, n}."""
    agora = agora or datetime.now(timezone.utc)
    janela = agora - timedelta(days=30)
    por_squad: dict[str, list[dict]] = defaultdict(list)
    for it in itens:
        por_squad[it["pk"].split("#", 1)[1]].append(it)

    linhas: list[dict] = []
    for squad, evs in sorted(por_squad.items()):
        evs.sort(key=lambda e: e["ts"])
        por_spec: dict[str, list[dict]] = defaultdict(list)
        for e in evs:
            por_spec[e["spec_id"]].append(e)

        ciclo = defaultdict(list)
        ate_aprovar = defaultdict(list)
        specs_merge_30d = 0
        for spec_id, lista in por_spec.items():
            faixa = next((e["faixa"] for e in reversed(lista) if e.get("faixa")), "sem_faixa")
            aprov = next((e for e in lista if e["tipo"] == "spec_aprovada"), None)
            criada = next((e for e in lista if e["tipo"] == "spec_criada"), None)
            merge = next((e for e in reversed(lista) if e["tipo"] == "merge"), None)
            if aprov and merge and merge["ts"] >= aprov["ts"]:
                ciclo[faixa].append(_horas(aprov["ts"], merge["ts"]))
            if aprov and criada and aprov["ts"] >= criada["ts"]:
                ate_aprovar[faixa].append(_horas(criada["ts"], aprov["ts"]))
            if merge and _dt(merge["ts"]) >= janela:
                specs_merge_30d += 1

        for faixa, v in sorted(ciclo.items()):
            linhas.append({"squad": squad, "metrica": "cycle_time_mediana_horas", "faixa": faixa,
                           "valor": median(v), "n": len(v)})
        for faixa, v in sorted(ate_aprovar.items()):
            linhas.append({"squad": squad, "metrica": "tempo_ate_spec_aprovada_mediana_horas", "faixa": faixa,
                           "valor": median(v), "n": len(v)})

        defeitos = sum(1 for e in evs if e["tipo"] == "defeito_aberto" and _dt(e["ts"]) >= janela)
        linhas.append({"squad": squad, "metrica": "defect_density_30d", "faixa": "todas",
                       "valor": round(defeitos / specs_merge_30d, 3) if specs_merge_30d else None,
                       "n": specs_merge_30d})

        tasks = defaultdict(lambda: [0, 0])  # faixa -> [tasks do agente, reescritas]
        for e in evs:
            if e["tipo"] == "task_concluida" and e.get("ator") == "agente":
                tasks[e.get("faixa") or "sem_faixa"][0] += 1
            elif e["tipo"] == "reescrita_humana":
                tasks[e.get("faixa") or "sem_faixa"][1] += 1
        for faixa, (t, r) in sorted(tasks.items()):
            if t:
                linhas.append({"squad": squad, "metrica": "proporcao_tasks_agente_sem_reescrita", "faixa": faixa,
                               "valor": round(max(0, t - r) / t, 3), "n": t})

        ci = [e for e in evs if e["tipo"] == "ci_executado"]
        if ci:
            verdes = sum(1 for e in ci if (e.get("detalhe") or {}).get("status") == "ok")
            linhas.append({"squad": squad, "metrica": "taxa_ci_local_verde", "faixa": "todas",
                           "valor": round(verdes / len(ci), 3), "n": len(ci)})
    return linhas


def csv(linhas: list[dict]) -> str:
    """Serializa em CSV."""
    out = ["squad,metrica,faixa,valor,n"]
    for li in linhas:
        valor = "" if li["valor"] is None else li["valor"]
        out.append(f"{li['squad']},{li['metrica']},{li['faixa']},{valor},{li['n']}")
    return "\n".join(out) + "\n"


def html(linhas: list[dict], titulo: str) -> str:
    """Gera um HTML estático simples."""
    corpo = "".join(
        f"<tr><td>{li['squad']}</td><td>{li['metrica']}</td><td>{li['faixa']}</td>"
        f"<td>{'' if li['valor'] is None else li['valor']}</td><td>{li['n']}</td></tr>" for li in linhas)
    return (f"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>{titulo}</title>"
            "<style>body{font-family:system-ui,sans-serif;margin:32px}table{border-collapse:collapse}"
            "td,th{border:1px solid #ccc;padding:6px 10px;text-align:left}th{background:#222;color:#fff}</style>"
            f"<h1>{titulo}</h1><table><tr><th>Squad</th><th>Métrica</th><th>Faixa</th><th>Valor</th><th>n</th></tr>"
            f"{corpo}</table><p>Gerado pelo ash-report. Definições em docs/spec-ash-v4.md, seção 8.</p></html>")
