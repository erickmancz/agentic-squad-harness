"""AC-31: a Lambda de ingestão (S3 para DynamoDB) contra o AWS Emulator.

O handler roda em processo, com o endpoint local do ambiente. Não se usa o 'lambda invoke' do emulador,
porque ele executa código sem isolamento. O gatilho S3 para Lambda não é coberto aqui (continua exigindo conta real)."""
import json

from conftest import RAIZ, carregar_modulo

EVENTO = {"ts": "2026-11-01T10:00:00Z", "squad": "demo", "spec_id": "T-1", "tipo": "spec_criada",
          "faixa": "autonoma", "ator": "agente", "detalhe": {}}


def _jsonl() -> str:
    segundo = dict(EVENTO, ts="2026-11-01T11:00:00Z", tipo="spec_aprovada", ator="humano")
    return "\n".join([json.dumps(EVENTO), "isto nao e json", json.dumps(segundo)]) + "\n"


def _evento_s3(bucket: str, chave: str) -> dict:
    return {"Records": [{"s3": {"bucket": {"name": bucket}, "object": {"key": chave}}}]}


def test_ac31_ingestao_grava_itens_validos_e_conta_invalidos(s3, dynamodb, bucket, tabela, monkeypatch):
    """AC-31: duas linhas válidas viram itens, a inválida é contada e a segunda execução é idempotente."""
    ingest = carregar_modulo("ingest_handler_integracao", RAIZ / "infra" / "lambdas" / "ingest" / "handler.py")
    monkeypatch.setenv("TABLE", tabela)
    chave = "raw/squad=demo/maquina-2026-11-01.jsonl"
    s3.put_object(Bucket=bucket, Key=chave, Body=_jsonl().encode("utf-8"))

    assert ingest.handler(_evento_s3(bucket, chave), None) == {"gravados": 2, "invalidos": 1}
    assert dynamodb.scan(TableName=tabela)["Count"] == 2

    ingest.handler(_evento_s3(bucket, chave), None)
    assert dynamodb.scan(TableName=tabela)["Count"] == 2
