# Revisão de cobertura · INS-016 · histórico de endossos

- Spec: `.kiro/specs/ins-016-historico-endossos-v2/requirements.md` (faixa semiautonoma, versão 2, status aprovada).
- Branch: `feat/ins-016`.
- Testes avaliados: `tests/test_ins_016_dominio.py`, `tests/test_ins_016_historico_endossos.py`.
- Código avaliado: `src/endosso/api.py`, `src/endosso/regras.py`, `src/endosso/repositorio.py`.
- Papel: revisor de cobertura. Não escrevo testes nem corrijo código; escrevo só em `reviews/`.

## 1. Comandos e números (cálculo fora do modelo)

- `python scripts/rastrear_aceite.py` → `[OK] 11 critério(s) com teste rastreado`.
- `python -m pytest --cov=src --cov-report=term-missing` (suíte completa, venv do projeto) → **26 passed**, cobertura de linha **100%** nos três módulos de `src/endosso`:

| Arquivo | Stmts | Miss | Cobertura |
|---|---|---|---|
| src/endosso/api.py | 48 | 0 | 100% |
| src/endosso/regras.py | 40 | 0 | 100% |
| src/endosso/repositorio.py | 29 | 0 | 100% |
| **TOTAL** | 117 | 0 | 100% |

Observação: rodando só os dois arquivos de teste da INS-016, a cobertura cai para 78% (api 75%, regras 78%, repositorio 83%); as linhas restantes (`recalcular_premio`, `validar_nova_cobertura`, endpoint de aumento de cobertura, `aplicar_endosso`) são da INS-014, cobertas por `test_ins_014_aumento_cobertura.py`. Para a INS-016, todo o caminho de leitura do histórico está coberto.

## 2. Rastreio CA → teste (cada CA tem ao menos um teste citando "INS-016 CA-NN")

| CA | Testes que citam o CA | Rastreado |
|---|---|---|
| CA-01 | `test_ins_016_ca_01_ordena_recente_primeiro` (domínio), `test_ins_016_ca_01_ap0001_dois_itens_ordenados` (endpoint) | Sim |
| CA-02 | `test_ins_016_ca_02_item_sem_dado_pessoal` (domínio), `test_ins_016_ca_02_item_contrato_iso8601` (endpoint) | Sim |
| CA-03 | `test_ins_016_ca_03_ap0003_lista_vazia` (endpoint) | Sim |
| CA-04 | `test_ins_016_ca_04_ap9999_nao_encontrada`, `test_ins_016_ca_04_formato_invalido_tambem_404` (endpoint) | Sim |
| CA-05 | `test_ins_016_ca_05_monetario_decimal_sem_recalculo` (domínio), `test_ins_016_ca_05_monetario_string_duas_casas` (endpoint) | Sim |
| CA-06 | `test_ins_016_ca_06_desempate_id_decrescente` (domínio), `test_ins_016_ca_06_empate_data_id_decrescente` (endpoint) | Sim |

Nenhum CA sem teste. Todos os CA têm cobertura dupla (regra pura + endpoint), exceto CA-03 e CA-04, cobertos só no endpoint: o que é adequado porque são comportamentos de borda/HTTP sem regra pura associada.

## 3. Cobertura é significativa, não só de linha?

A cobertura de 100% é acompanhada de asserções de comportamento, não só de status code. Avaliação por critério:

- **CA-01 (ordenação recente→antigo):** significativa no domínio. `test_ins_016_ca_01_ordena_recente_primeiro` usa duas datas **distintas** (`MESMA_DATA` > `DATA_ANTERIOR`) e verifica a ordem resultante: exercita de fato o critério de data. O teste de endpoint verifica `datas == sorted(datas, reverse=True)`, mas a massa de AP-0001 tem os dois endossos na **mesma data**; logo o endpoint não distingue ordenação por data (ver borda na seção 4). O comportamento de data fica garantido pelo teste de domínio.
- **CA-02 (seis campos, ISO-8601 UTC, sem PII):** significativa. O domínio injeta campos pessoais (`nome_segurado`, `cpf`) no registro bruto e prova que a projeção os descarta (conjunto de campos == os seis do contrato). O endpoint confere o conjunto exato de campos, o sufixo `Z` na data e a ausência de `cpf`/`nome`/`email`. Verifica comportamento real, não só o 200.
- **CA-03 (lista vazia):** significativa. AP-0003 existe e tem trilha vazia; o teste prova 200 + `[]`, distinguindo "existe sem endosso" de "não existe".
- **CA-04 (404 sem PII):** significativa e com borda extra. Cobre inexistente (AP-9999) e formato inválido (`XYZ`), ambos com a mesma mensagem genérica, e verifica ausência de termos pessoais no detalhe.
- **CA-05 (decimal sem recálculo):** significativa. Domínio prova `isinstance Decimal`, igualdade exata e preservação de string (`"1500.00"`); endpoint prova as quatro strings de duas casas e `Decimal(...)` sem imprecisão de float.
- **CA-06 (desempate por id decrescente):** significativa e direta. Domínio e endpoint provam `ids == [12, 11]` com os dois endossos na mesma data.

Conclusão desta seção: é cobertura significativa de comportamento, não apenas de linha.

## 4. Lacunas e casos de borda (não bloqueantes)

1. **CA-01 no endpoint não exercita ordenação por data.** A massa de AP-0001 tem os dois endossos na mesma data, então `sorted(datas, reverse=True)` é trivialmente verdadeiro e o teste de endpoint não falharia se a ordenação por data quebrasse. A garantia de data vem só do teste de domínio. Sugestão (a quem escreve teste): massa de endpoint com datas distintas, ou um caso de endpoint específico de ordenação por data. Não bloqueia porque o domínio cobre o critério de data e o endpoint delega a `build_history`.
2. **CA-02 valida o formato ISO-8601 de modo fraco.** O endpoint só checa `item["date"].endswith("Z")`; não valida o formato completo nem que o offset seja realmente UTC. Uma string malformada terminada em `Z` passaria. O código (`_serializar_data` com `astimezone(timezone.utc)`) está correto, mas o teste não o prova integralmente. Não bloqueia.
3. **CA-05 não exercita o arredondamento/`quantize`.** Todos os valores de massa já têm exatamente duas casas, então `_serializar_valor` (que faz `quantize(CENTAVOS)`) nunca é testado com entrada de mais/menos casas (ex.: `"1500.5"` ou `"1500.005"`). O critério fala em "duas casas" e "sem recálculo"; um valor que force `quantize` tornaria o teste mais fiel. Não bloqueia na massa atual.
4. **Ausência de PII testada só contra campos conhecidos.** CA-02 verifica a ausência de `cpf`/`nome`/`email`/`telefone` nominalmente. Como a projeção usa allow-list fixa de seis campos (`_serializar_item` / `project_endorsement`), qualquer campo pessoal novo seria descartado por construção; o teste de domínio já prova isso injetando campos extras. Cobertura adequada.

Nenhum desses pontos deixa um CA sem verificação de comportamento; são reforços de robustez de massa e de borda.

## 5. Conclusão

**Sem bloqueio de cobertura.** Os seis critérios CA-01 a CA-06 têm teste que cita "INS-016 CA-NN" e verificam o comportamento do critério (ordenação, desempate por id decrescente, ausência de dado pessoal, formato com sufixo Z, lista vazia, 404 genérico, decimal preservado), não apenas status code. A cobertura de linha de 100% nos módulos da INS-016 corresponde a cobertura significativa. As quatro observações da seção 4 são melhorias de borda (ordenação por data no endpoint, validação ISO-8601 completa, exercício do `quantize`), recomendadas para fortalecer a suíte, mas não impedem o avanço nesta faixa semiautonoma.
