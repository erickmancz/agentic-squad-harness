"""Testes de integração do projeto contra o AWS Emulator local.

Copie esta pasta para tests/integracao_aws/ ao ativar o perfil python-aws (README, seção "Testes contra o AWS Emulator").
Rode por: python ash.py etapa integracao-aws (ou python ash.py ci), com o emulador de pé (python ash.py emulador iniciar).

O ash.py entrega, no ambiente do processo desta etapa, o endpoint local e as credenciais geradas pelo emulador; nada vai
para o seu ambiente nem para ~/.aws. Antes de qualquer teste, a fixture abaixo prova que o endpoint é local e que as
credenciais são as do emulador; se algo não bater, a execução inteira é abortada antes de criar qualquer recurso.
As chaves nunca são impressas.
"""
import uuid

import boto3
import pytest

CONTA_EMULADOR = "000000000000"


def _abortar(motivo: str) -> None:
    pytest.exit(f"[integracao-aws] {motivo}", returncode=2)


@pytest.fixture(scope="session", autouse=True)
def provar_emulador():
    """Aborta a sessão se o endpoint não for https://127.0.0.1:<porta> ou se as credenciais não forem do emulador."""
    import os

    endpoint = os.environ.get("AWS_ENDPOINT_URL", "")
    if not endpoint.startswith("https://127.0.0.1:"):
        _abortar("AWS_ENDPOINT_URL ausente ou não local. Rode por: python ash.py etapa integracao-aws")
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
def bucket(s3):
    """Bucket S3 com nome único, apagado ao final."""
    nome = f"teste-{uuid.uuid4().hex[:12]}"
    s3.create_bucket(Bucket=nome)
    yield nome
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=nome):
        for obj in pagina.get("Contents", []):
            s3.delete_object(Bucket=nome, Key=obj["Key"])
    s3.delete_bucket(Bucket=nome)
