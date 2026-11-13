"""AC-33: o backup do repositório (git bundle para S3) contra o AWS Emulator.

Roda o cmd_backup do ash.py com um config falso (o .ash/config.env real não é lido nem alterado).
O AWS CLI herda o endpoint e as credenciais do emulador do ambiente deste processo."""
import importlib.util
import shutil

import pytest

from conftest import RAIZ


@pytest.mark.skipif(shutil.which("aws") is None, reason="o backup usa o AWS CLI, que não está no PATH")
def test_ac33_backup_envia_o_bundle_para_o_s3_local(s3, bucket, monkeypatch):
    """AC-33: o bundle e o latest.bundle aparecem em bundles/<repo>/ no bucket do emulador."""
    spec = importlib.util.spec_from_file_location("ash_backup_integracao", RAIZ / "ash.py")
    ash = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ash)
    monkeypatch.setattr(ash, "config", lambda: {"ASH_CODE_BUCKET": bucket, "AWS_REGION": "us-east-1"})

    assert ash.cmd_backup(None) == 0

    chaves = [o["Key"] for o in s3.list_objects_v2(Bucket=bucket, Prefix="bundles/").get("Contents", [])]
    assert any(c.endswith("/latest.bundle") for c in chaves) and len(chaves) == 2
