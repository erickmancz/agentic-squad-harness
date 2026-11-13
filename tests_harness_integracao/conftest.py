"""Testes de integração do PRÓPRIO ASH (Lambdas de infra/ e backup) contra o AWS Emulator local.

Rode por: python ash.py testar-harness --integracao. Não fazem parte do CI de nenhum projeto: quem os roda é o autor do
harness, por exemplo antes do publicar-harness. Os testes de integração de um projeto que usa AWS ficam em
tests/integracao_aws/ (perfil python-aws).

O ash.py entrega, no ambiente deste processo, o endpoint local e as credenciais geradas pelo emulador.
Antes de qualquer teste, a fixture abaixo prova que o endpoint é local e que as credenciais são as do
emulador; se algo não bater, a execução inteira é abortada antes de criar qualquer recurso.
As chaves nunca são impressas.
"""
import importlib.util
import os
import uuid
from pathlib import Path

import boto3
import pytest

RAIZ = Path(__file__).resolve().parent.parent
CONTA_EMULADOR = "000000000000"


def _abortar(motivo: str) -> None:
    pytest.exit(f"[integracao-aws] {motivo}", returncode=2)


@pytest.fixture(scope="session", autouse=True)
def provar_emulador():
    """Aborta a sessão se o endpoint não for https://127.0.0.1:<porta> ou se as credenciais não forem do emulador."""
    endpoint = os.environ.get("AWS_ENDPOINT_URL", "")
    if not endpoint.startswith("https://127.0.0.1:"):
        _abortar("AWS_ENDPOINT_URL ausente ou não local. Rode por: python ash.py testar-harness --integracao")
    credenciais = boto3.session.Session().get_credentials()
    if credenciais is None or not credenciais.access_key.startswith("EMULATOR"):
        _abortar("as credenciais não são as geradas pelo emulador (o ID da chave deve começar com EMULATOR)")
    identidade = boto3.client("sts").get_caller_identity()
    if identidade["Account"] != CONTA_EMULADOR or not identidade["Arn"].endswith(":user/emulator"):
        _abortar("o sts não respondeu como o emulador (conta 000000000000, usuário emulator)")


@pytest.fixture()
def s3():
    """Cliente S3 apontado para o emulador."""
    return boto3.client("s3")


@pytest.fixture()
def dynamodb():
    """Cliente DynamoDB apontado para o emulador."""
    return boto3.client("dynamodb")


@pytest.fixture()
def bucket(s3):
    """Bucket S3 com nome único, apagado ao final."""
    nome = f"ash-teste-{uuid.uuid4().hex[:12]}"
    s3.create_bucket(Bucket=nome)
    yield nome
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=nome):
        for obj in pagina.get("Contents", []):
            s3.delete_object(Bucket=nome, Key=obj["Key"])
    s3.delete_bucket(Bucket=nome)


@pytest.fixture()
def tabela(dynamodb):
    """Tabela com as chaves pk e sk (como a ash-metrics), com nome único, apagada ao final."""
    nome = f"ash-teste-{uuid.uuid4().hex[:12]}"
    dynamodb.create_table(
        TableName=nome,
        AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.get_waiter("table_exists").wait(TableName=nome)
    yield nome
    dynamodb.delete_table(TableName=nome)


def carregar_modulo(apelido: str, caminho: Path):
    """Importa um arquivo Python por caminho, com um nome único para não colidir (os dois handlers se chamam handler)."""
    spec = importlib.util.spec_from_file_location(apelido, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo
