import pytest
from fastapi.testclient import TestClient

from src.endosso import api


@pytest.fixture()
def cliente():
    api.repo = api.Repositorio()
    return TestClient(api.app)
