"""ash-ingest: lê JSONL de eventos do S3 e grava na tabela ash-metrics. Idempotente."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from urllib.parse import unquote_plus

log = logging.getLogger()
log.setLevel(logging.INFO)

OBRIGATORIOS = ("ts", "squad", "spec_id", "tipo")


def item_de(linha: str) -> dict | None:
    """Converte uma linha JSONL em item DynamoDB, ou None se inválida."""
    linha = linha.strip()
    if not linha:
        return None
    try:
        ev = json.loads(linha)
    except json.JSONDecodeError:
        return None
    if not all(ev.get(k) for k in OBRIGATORIOS):
        return None
    h = hashlib.sha256(linha.encode("utf-8")).hexdigest()[:10]
    return {
        "pk": f"SQUAD#{ev['squad']}",
        "sk": f"SPEC#{ev['spec_id']}#{ev['ts']}#{ev['tipo']}#{h}",
        "ts": ev["ts"],
        "spec_id": ev["spec_id"],
        "tipo": ev["tipo"],
        "faixa": ev.get("faixa", ""),
        "ator": ev.get("ator", ""),
        "detalhe": {str(k): str(v) for k, v in (ev.get("detalhe") or {}).items()},
    }


def handler(event, _context):
    import boto3  # importado aqui para os testes unitários rodarem sem AWS

    s3 = boto3.client("s3")
    tabela = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    gravados = invalidos = 0
    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        chave = unquote_plus(rec["s3"]["object"]["key"])
        corpo = s3.get_object(Bucket=bucket, Key=chave)["Body"].read().decode("utf-8")
        with tabela.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as lote:
            for linha in corpo.splitlines():
                item = item_de(linha)
                if item is None:
                    invalidos += 1 if linha.strip() else 0
                    continue
                lote.put_item(Item=item)
                gravados += 1
        log.info(json.dumps({"msg": "arquivo ingerido", "chave": chave, "gravados": gravados,
                             "invalidos": invalidos}))
    # métrica customizada via Embedded Metric Format (sem chamada extra de API)
    print(json.dumps({
        "_aws": {"Timestamp": int(time.time() * 1000), "CloudWatchMetrics": [{
            "Namespace": "ASH", "Dimensions": [[]],
            "Metrics": [{"Name": "EventosIngeridos", "Unit": "Count"},
                        {"Name": "LinhasInvalidas", "Unit": "Count"}]}]},
        "EventosIngeridos": gravados, "LinhasInvalidas": invalidos,
    }))
    return {"gravados": gravados, "invalidos": invalidos}
