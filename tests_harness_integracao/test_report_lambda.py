"""AC-32: a Lambda de relatório (DynamoDB para S3) contra o AWS Emulator.

O handler roda em processo. O agendamento do EventBridge Scheduler continua exigindo conta real."""
import json

from conftest import RAIZ, carregar_modulo

EVENTOS = [
    {"ts": "2026-11-01T10:00:00Z", "squad": "demo", "spec_id": "T-1", "tipo": "spec_criada", "faixa": "autonoma",
     "ator": "agente", "detalhe": {}},
    {"ts": "2026-11-01T12:00:00Z", "squad": "demo", "spec_id": "T-1", "tipo": "spec_aprovada", "faixa": "autonoma",
     "ator": "humano", "detalhe": {}},
    {"ts": "2026-11-01T20:00:00Z", "squad": "demo", "spec_id": "T-1", "tipo": "merge", "faixa": "autonoma",
     "ator": "humano", "detalhe": {}},
]


def test_ac32_relatorio_grava_csv_e_html_no_s3(s3, dynamodb, bucket, tabela, monkeypatch):
    """AC-32: com eventos na tabela, o handler grava relatorio.csv e relatorio.html em reports/semana=AAAA-Www/."""
    pasta_report = RAIZ / "infra" / "lambdas" / "report"
    monkeypatch.syspath_prepend(str(pasta_report))
    ingest = carregar_modulo("ingest_handler_para_relatorio", RAIZ / "infra" / "lambdas" / "ingest" / "handler.py")
    report = carregar_modulo("report_handler_integracao", pasta_report / "handler.py")
    monkeypatch.setenv("TABLE", tabela)
    monkeypatch.setenv("REPORTS_BUCKET", bucket)
    for evento in EVENTOS:
        item = ingest.item_de(json.dumps(evento))
        dynamodb.put_item(TableName=tabela, Item={k: {"S": v} for k, v in item.items() if isinstance(v, str)})

    resultado = report.handler(None, None)

    assert resultado["itens"] == 3 and resultado["linhas"] > 0
    csv = s3.get_object(Bucket=bucket, Key=f"{resultado['pasta']}/relatorio.csv")["Body"].read().decode("utf-8")
    html = s3.get_object(Bucket=bucket, Key=f"{resultado['pasta']}/relatorio.html")["Body"].read().decode("utf-8")
    assert csv.startswith("squad,metrica,faixa,valor,n") and "<table>" in html
