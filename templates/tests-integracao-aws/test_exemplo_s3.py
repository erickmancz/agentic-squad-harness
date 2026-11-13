"""Exemplo de teste de integração com S3 contra o AWS Emulator. Troque pelos testes do seu projeto.

Os testes reais citam '<ID da spec> CA-NN' no nome, na docstring ou em comentário, como os demais, para o rastreio de
aceite encontrá-los. Chame o código do projeto (a função ou o módulo que usa o SDK), não o SDK direto como aqui."""


def test_exemplo_grava_e_le_um_objeto(s3, bucket):
    """Exemplo: grava um objeto no bucket do emulador e o lê de volta."""
    s3.put_object(Bucket=bucket, Key="exemplo.txt", Body=b"ola")
    assert s3.get_object(Bucket=bucket, Key="exemplo.txt")["Body"].read() == b"ola"
