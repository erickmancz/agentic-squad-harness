"""Regras escritas nos agentes, no steering, na story e no README (ensaio da INS-017). Provam que o texto está lá.

O comportamento dos agentes é conferido por leitura fria, fora destes testes.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _prompt(nome: str) -> str:
    return json.loads((RAIZ / ".kiro" / "agents" / f"{nome}.json").read_text(encoding="utf-8"))["prompt"]


def _ler(caminho: str) -> str:
    return (RAIZ / caminho).read_text(encoding="utf-8")


def test_intake_confere_o_codigo_antes_de_recomendar_mecanismo_existente():
    p = _prompt("intake-spec")
    assert "CONFERIR ANTES DE RECOMENDAR" in p
    assert "leia o código" in p
    assert "Se não existir, não o ofereça como opção" in p
    assert "pergunta em aberto" in p


def test_intake_trata_identificador_de_pessoa_como_dado_pessoal():
    p = _prompt("intake-spec")
    assert "identificador de pessoa" in p
    assert "é dado pessoal" in p
    assert "finalidade" in p and "retenção" in p
    assert "Nunca descreva esse registro, log ou auditoria como 'sem dado pessoal'" in p


def test_intake_nao_inventa_numero_sem_fonte():
    p = _prompt("intake-spec")
    assert "SEM FONTE, SEM NÚMERO" in p
    assert "'a definir'" in p


def test_governanca_tem_a_regra_de_identificador_de_pessoa():
    g = _ler(".kiro/steering/00-governanca.md")
    assert "Identificador de pessoa" in g
    assert "é dado pessoal, mesmo quando é só declarado e não comprovado" in g
    assert 'Nenhum agente descreve esse registro, log ou auditoria como "sem dado pessoal"' in g


def test_governanca_proibe_numero_sem_fonte():
    g = _ler(".kiro/steering/00-governanca.md")
    assert "## Números sem fonte" in g
    assert "Nenhum agente inventa prazo, meta, limite" in g
    assert '"a definir"' in g and "Perguntas em aberto" in g


def test_planejador_recomenda_corrigir_a_spec_em_vez_de_reinterpretar():
    p = _prompt("planejador")
    assert "CONTRADIÇÃO COM A SPEC" in p
    assert "não reinterprete" in p
    assert "corrigir a spec" in p and "nova aprovação do PO" in p
    assert "bloqueadas" in p


def test_implementador_devolve_acrescimo_fora_do_design_como_duvida():
    p = _prompt("implementador")
    assert "FORA DO DESIGN" in p
    assert "não implemente" in p
    assert "squad-lead" in p and "dúvida" in p


def test_story_ins_017_diz_que_a_consulta_e_interna_sem_autenticacao_nova():
    s = _ler("stories/INS-017-resumo-apolice.md")
    assert "A consulta é interna" in s
    assert "não cria autenticação nem controle de acesso novo" in s


def test_readme_nao_diz_mais_que_a_ins_017_ainda_nao_foi_implementada():
    r = _ler("README.md")
    assert "ainda não implementada" not in r
    assert "story de demonstração, não implementada no pacote" in r


def test_planejador_marca_task_bloqueada_e_o_implementador_sabe_ler_a_marca():
    assert "'[BLOQUEADA]'" in _prompt("planejador")
    impl = _prompt("implementador")
    assert "'[BLOQUEADA]'" in impl
    assert "não se implementa" in impl


def test_intake_procura_alem_da_pasta_de_codigo_e_so_conclui_nao_existe_depois():
    p = _prompt("intake-spec")
    assert "infra/" in p
    assert "Só conclua 'não existe' depois dessa busca" in p
    assert "a faixa é critica" in p


def test_implementador_define_o_alcance_da_parada_e_nao_trava_em_detalhe_interno():
    p = _prompt("implementador")
    assert "helper privado" in p
    assert "Pare a task afetada" in p
    assert "não deixe código parcial" in p


def test_governanca_manda_parar_em_contradicao_de_spec_e_em_numero_sem_fonte():
    g = _ler(".kiro/steering/00-governanca.md")
    parar = g.split("## Quando parar e perguntar", 1)[1]
    assert "A spec se contradiz" in parar
    assert "Falta um número que a story, o PO ou o FDE não deram" in parar


def test_governanca_permite_o_registro_de_execucao_previsto_na_spec():
    g = _ler(".kiro/steering/00-governanca.md")
    assert "Nenhum dado pessoal em log, teste ou exemplo" not in g
    assert "O registro de execução que a spec aprovada manda gravar" in g
