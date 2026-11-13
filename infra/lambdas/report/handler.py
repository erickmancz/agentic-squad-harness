"""ash-report: agrega a tabela ash-metrics e grava CSV + HTML no bucket de relatórios."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from metricas import calcular, csv, html

log = logging.getLogger()
log.setLevel(logging.INFO)


def handler(_event, _context):
    import boto3

    tabela = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    itens, kwargs = [], {}
    while True:  # scan é aceitável no volume de piloto; trocar por query por squad em produção
        r = tabela.scan(**kwargs)
        itens += r.get("Items", [])
        if "LastEvaluatedKey" not in r:
            break
        kwargs["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    agora = datetime.now(timezone.utc)
    ano, semana, _ = agora.isocalendar()
    linhas = calcular(itens, agora)
    pasta = f"reports/semana={ano}-W{semana:02d}"
    s3 = boto3.client("s3")
    bucket = os.environ["REPORTS_BUCKET"]
    s3.put_object(Bucket=bucket, Key=f"{pasta}/relatorio.csv", Body=csv(linhas).encode("utf-8"),
                  ContentType="text/csv; charset=utf-8")
    s3.put_object(Bucket=bucket, Key=f"{pasta}/relatorio.html",
                  Body=html(linhas, f"ASH · métricas · {ano}-W{semana:02d}").encode("utf-8"),
                  ContentType="text/html; charset=utf-8")
    log.info(json.dumps({"msg": "relatório gerado", "pasta": pasta, "itens": len(itens), "linhas": len(linhas)}))
    return {"pasta": pasta, "itens": len(itens), "linhas": len(linhas)}
