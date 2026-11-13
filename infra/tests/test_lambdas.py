import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "lambdas"
sys.path.insert(0, str(BASE / "report"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("ingest_handler", BASE / "ingest" / "handler.py")
_ingest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ingest)
item_de = _ingest.item_de
import metricas  # noqa: E402


def ev(ts, tipo, spec="INS-015", faixa="semiautonoma", ator="humano", detalhe=None):
    return {"ts": ts, "squad": "demo", "spec_id": spec, "tipo": tipo, "faixa": faixa, "ator": ator,
            "detalhe": detalhe or {}}


def test_item_de_linha_valida_e_idempotente():
    linha = json.dumps(ev("2026-10-20T10:00:00Z", "spec_criada"))
    a, b = item_de(linha), item_de(linha)
    assert a["pk"] == "SQUAD#demo" and a["sk"] == b["sk"]


def test_item_de_linha_invalida():
    assert item_de("nao e json") is None
    assert item_de(json.dumps({"ts": "x"})) is None
    assert item_de("   ") is None


def test_metricas_ciclo_aprovacao_proporcao_ci():
    linhas_jsonl = [
        ev("2026-10-20T10:00:00Z", "spec_criada", ator="agente"),
        ev("2026-10-20T12:00:00Z", "spec_aprovada"),
        ev("2026-10-20T13:00:00Z", "task_concluida", ator="agente"),
        ev("2026-10-20T14:00:00Z", "task_concluida", ator="agente"),
        ev("2026-10-20T15:00:00Z", "reescrita_humana"),
        ev("2026-10-20T16:00:00Z", "ci_executado", detalhe={"status": "ok"}),
        ev("2026-10-20T17:00:00Z", "ci_executado", detalhe={"status": "falhou"}),
        ev("2026-10-20T20:00:00Z", "merge"),
        ev("2026-10-21T09:00:00Z", "defeito_aberto"),
    ]
    itens = [item_de(json.dumps(e)) for e in linhas_jsonl]
    agora = datetime(2026, 10, 22, tzinfo=timezone.utc)
    m = {(l["metrica"], l["faixa"]): l for l in metricas.calcular(itens, agora)}
    assert m[("cycle_time_mediana_horas", "semiautonoma")]["valor"] == 8.0
    assert m[("tempo_ate_spec_aprovada_mediana_horas", "semiautonoma")]["valor"] == 2.0
    assert m[("proporcao_tasks_agente_sem_reescrita", "semiautonoma")]["valor"] == 0.5
    assert m[("taxa_ci_local_verde", "todas")]["valor"] == 0.5
    assert m[("defect_density_30d", "todas")]["valor"] == 1.0
    assert "cycle_time" in metricas.csv(list(m.values()))
    assert "<table>" in metricas.html(list(m.values()), "t")
