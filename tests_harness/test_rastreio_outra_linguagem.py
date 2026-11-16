"""Testes do rastreio de aceite com arquivos_teste de outra linguagem (perfil não Python)."""
import json

import pytest

SPEC = """---
id: INS-900
dono_po: PO Teste
faixa: autonoma
dev_revisor:
versao: 1
status: aprovada
---

# INS-900 · Spec de teste

## 4. Aceite testável
- CA-01: Dado A, quando B, então C.
- CA-02: Dado D, quando E, então F.

## Perguntas em aberto
- Nenhuma
"""


@pytest.fixture()
def repo_falso(ash, monkeypatch, tmp_path):
    """Repositório temporário com uma spec aprovada e um perfil de testes em TypeScript."""
    import ash_spec
    pasta = tmp_path / ".kiro" / "specs" / "ins-900-teste"
    pasta.mkdir(parents=True)
    (pasta / "requirements.md").write_text(SPEC, encoding="utf-8")
    (tmp_path / "ash-perfil.json").write_text(json.dumps({"arquivos_teste": ["test/**/*.spec.ts"]}), encoding="utf-8")
    (tmp_path / "test").mkdir()
    monkeypatch.setattr(ash_spec, "RAIZ", tmp_path)
    monkeypatch.setattr(ash_spec, "PASTA_SPECS", tmp_path / ".kiro" / "specs")
    return tmp_path


def test_criterio_citado_em_comentario_typescript_e_encontrado(repo_falso, capsys):
    import rastrear_aceite
    (repo_falso / "test" / "a.spec.ts").write_text(
        "// INS-900 CA-01\n// INS-900 CA-02\nit('ok', () => {});\n", encoding="utf-8")
    assert rastrear_aceite.main([]) == 0
    assert "2 critério(s)" in capsys.readouterr().out


def test_criterio_sem_citacao_faz_o_rastreio_falhar(repo_falso, capsys):
    import rastrear_aceite
    (repo_falso / "test" / "a.spec.ts").write_text("// INS-900 CA-01\n", encoding="utf-8")
    assert rastrear_aceite.main([]) == 1
    assert "INS-900 CA-02" in capsys.readouterr().err


def test_so_vale_o_padrao_de_arquivos_do_perfil(repo_falso):
    import rastrear_aceite
    (repo_falso / "test" / "a.spec.ts").write_text("// INS-900 CA-01\n", encoding="utf-8")
    (repo_falso / "tests").mkdir()
    (repo_falso / "tests" / "test_x.py").write_text('"""INS-900 CA-02"""\n', encoding="utf-8")
    assert rastrear_aceite.main([]) == 1


def test_forma_snake_case_no_nome_do_teste_tambem_vale(repo_falso):
    import rastrear_aceite
    (repo_falso / "test" / "a.spec.ts").write_text(
        "it('ins_900_ca_01', () => {});\nit('ins_900_ca_02', () => {});\n", encoding="utf-8")
    assert rastrear_aceite.main([]) == 0


def test_padroes_de_teste_leem_o_perfil_e_caem_no_padrao_python(repo_falso):
    import rastrear_aceite
    assert rastrear_aceite.padroes_de_teste() == ["test/**/*.spec.ts"]
    (repo_falso / "ash-perfil.json").write_text("{ invalido", encoding="utf-8")
    assert rastrear_aceite.padroes_de_teste() == rastrear_aceite.PADRAO_TESTES
    (repo_falso / "ash-perfil.json").unlink()
    assert rastrear_aceite.padroes_de_teste() == rastrear_aceite.PADRAO_TESTES


def test_spec_nao_aprovada_fica_fora_do_rastreio_por_padrao(repo_falso):
    import rastrear_aceite
    arq = repo_falso / ".kiro" / "specs" / "ins-900-teste" / "requirements.md"
    arq.write_text(SPEC.replace("status: aprovada", "status: rascunho"), encoding="utf-8")
    assert rastrear_aceite.main([]) == 0
    assert rastrear_aceite.main(["--todas-as-specs"]) == 1


def _segunda_spec(repo_falso):
    pasta = repo_falso / ".kiro" / "specs" / "ins-901-outra"
    pasta.mkdir(parents=True)
    texto = SPEC.replace("INS-900", "INS-901")
    (pasta / "requirements.md").write_text(texto, encoding="utf-8")


def test_com_id_so_conta_e_informa_os_criterios_daquela_spec(repo_falso, capsys):
    import rastrear_aceite
    _segunda_spec(repo_falso)
    (repo_falso / "test" / "a.spec.ts").write_text("// INS-900 CA-01\n// INS-900 CA-02\n", encoding="utf-8")
    assert rastrear_aceite.main(["INS-900"]) == 0
    saida = capsys.readouterr().out
    assert "2 critério(s) de INS-900" in saida
    assert "INS-901" not in saida


def test_com_id_nao_falha_por_criterio_de_outra_spec(repo_falso, capsys):
    import rastrear_aceite
    _segunda_spec(repo_falso)
    (repo_falso / "test" / "a.spec.ts").write_text("// INS-900 CA-01\n// INS-900 CA-02\n", encoding="utf-8")
    assert rastrear_aceite.main([]) == 1  # sem ID, a INS-901 sem teste derruba o rastreio
    capsys.readouterr()
    assert rastrear_aceite.main(["INS-900"]) == 0
    assert rastrear_aceite.main(["ins-900"]) == 0  # o ID não diferencia maiúsculas


def test_com_id_aponta_so_os_criterios_faltantes_daquela_spec(repo_falso, capsys):
    import rastrear_aceite
    _segunda_spec(repo_falso)
    (repo_falso / "test" / "a.spec.ts").write_text("// INS-900 CA-01\n// INS-901 CA-01\n", encoding="utf-8")
    assert rastrear_aceite.main(["INS-900"]) == 1
    erro = capsys.readouterr().err
    assert "INS-900 CA-02" in erro
    assert "INS-901" not in erro


def test_id_inexistente_sai_com_erro_dois(repo_falso, capsys):
    import rastrear_aceite
    assert rastrear_aceite.main(["INS-777"]) == 2
    assert "INS-777" in capsys.readouterr().err


def test_id_de_spec_nao_aprovada_so_vale_com_todas_as_specs(repo_falso):
    import rastrear_aceite
    arq = repo_falso / ".kiro" / "specs" / "ins-900-teste" / "requirements.md"
    arq.write_text(SPEC.replace("status: aprovada", "status: rascunho"), encoding="utf-8")
    assert rastrear_aceite.main(["INS-900"]) == 2
    assert rastrear_aceite.main(["INS-900", "--todas-as-specs"]) == 1


def test_varios_ids_somam_os_criterios(repo_falso, capsys):
    import rastrear_aceite
    _segunda_spec(repo_falso)
    (repo_falso / "test" / "a.spec.ts").write_text(
        "// INS-900 CA-01\n// INS-900 CA-02\n// INS-901 CA-01\n// INS-901 CA-02\n", encoding="utf-8")
    assert rastrear_aceite.main(["INS-900", "INS-901"]) == 0
    assert "4 critério(s) de INS-900, INS-901" in capsys.readouterr().out
