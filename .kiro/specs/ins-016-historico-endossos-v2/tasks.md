# INS-016 · Tasks · Consulta do histórico de endossos de uma apólice

Derivado de `requirements.md` (v2, aprovada) e de `design.md`. Tarefas pequenas, em ordem de implementação. Cada tarefa cita os CA que atende. Testes `pytest` citam `INS-016 CA-NN` no nome ou docstring (regra de rastreio). Cobertura mínima do projeto: 80%. Código e identificadores em inglês.

## 1. Modelo de domínio do item de endosso
- Criar o objeto imutável do item de endosso em `src/endorsements/domain.py` com os campos `endorsement_id`, `date` (datetime UTC tz-aware), `coverage_before`, `coverage_after`, `premium_before`, `premium_after` (todos `decimal.Decimal`).
- Docstring de uma linha. Sem campos de dado pessoal.
- Atende: INS-016 CA-02, CA-05.

## 2. Função pura de ordenação com desempate
- Em `src/endorsements/domain.py`, implementar função pura que ordena os endossos por `date` decrescente e, em empate de data, por `endorsement_id` decrescente (chave composta `(date, endorsement_id)` com ordem decrescente).
- Não depende da ordem de inserção na trilha.
- Atende: INS-016 CA-01, CA-06.

## 3. Projeção sem dado pessoal e sem recálculo
- Em `src/endorsements/domain.py`, implementar a montagem do item de saída a partir do registro bruto da trilha, copiando apenas os seis campos do contrato e preservando os valores monetários gravados (sem recálculo, mantendo duas casas em `Decimal`).
- Garantir que nenhum campo pessoal eventualmente presente no registro bruto seja copiado.
- Atende: INS-016 CA-02, CA-05.

## 4. Repositórios em memória com massa sintética
- Criar `src/endorsements/repository.py` com repositório de apólices (`exists`) e trilha de auditoria (`endorsements_of`), em memória.
- Massa sintética: AP-0001 com 2 endossos na mesma data e identificadores distintos (ex.: 11 e 12); AP-0003 existente sem endosso; AP-9999 inexistente. Valores monetários como `Decimal` de duas casas. Nenhum dado pessoal.
- Atende: INS-016 CA-01, CA-03, CA-04, CA-06.

## 5. Serialização ISO-8601 UTC e monetário em string
- Implementar a conversão da `date` para string ISO-8601 em UTC (sufixo `Z`) e de cada `Decimal` monetário para string com duas casas, na fronteira de saída.
- Atende: INS-016 CA-02, CA-05.

## 6. Endpoint FastAPI de leitura
- Criar `src/endorsements/api.py` com `GET /policies/{policy_number}/endorsements`, dependência de autenticação com perfil de atendente (demo, sem segregação por carteira).
- Validar o formato do número da apólice (`AP` + 4 dígitos). Formato inválido ou apólice inexistente -> 404 `{"detail": "apólice não encontrada"}` sem dado pessoal. Apólice existente -> 200 com a lista ordenada (vazia se não houver endosso).
- A camada HTTP apenas orquestra: ordenação e projeção ficam no domínio.
- Atende: INS-016 CA-01, CA-03, CA-04.

## 7. Garantia de ausência de dado pessoal em log e erro
- Revisar o endpoint e o tratamento de erro para não registrar número de apólice com dado pessoal associado nem incluir dado pessoal na mensagem de 404; usar mensagem genérica.
- Atende: INS-016 CA-04 (parte de não expor dado pessoal); não funcionais blocos 6 e 7.

## 8. Testes de domínio (ordenação, desempate, monetário, projeção)
- Em `tests/`, testes `pytest` puros do domínio:
  - ordenação do mais recente para o mais antigo (`test_ordena_recente_primeiro`, INS-016 CA-01);
  - desempate de data por `endorsement_id` decrescente, id 12 antes do 11 (`test_desempate_id_decrescente`, INS-016 CA-06);
  - valores monetários em `Decimal` de duas casas preservados sem recálculo (`test_monetario_decimal_sem_recalculo`, INS-016 CA-05);
  - item contém só os seis campos e nenhum dado pessoal (`test_item_sem_dado_pessoal`, INS-016 CA-02).
- Massa sintética.
- Atende: INS-016 CA-01, CA-02, CA-05, CA-06.

## 9. Testes do endpoint (sucesso, vazio, 404, formato de data)
- Em `tests/`, testes `pytest` com `TestClient` do FastAPI:
  - AP-0001 retorna 200 com 2 itens ordenados (`test_ap0001_dois_itens_ordenados`, INS-016 CA-01);
  - item devolvido tem os cinco campos de dados + id, data em UTC ISO-8601 e nenhum campo pessoal (`test_item_contrato_iso8601`, INS-016 CA-02);
  - AP-0003 retorna 200 com lista vazia (`test_ap0003_lista_vazia`, INS-016 CA-03);
  - AP-9999 retorna 404 "apólice não encontrada" sem dado pessoal (`test_ap9999_nao_encontrada`, INS-016 CA-04);
  - AP-0001 com empate de data devolve id 12 antes do 11 (`test_empate_data_id_decrescente`, INS-016 CA-06).
- Atende: INS-016 CA-01, CA-02, CA-03, CA-04, CA-06.

## 10. Verificação de cobertura e CI local
- Rodar `pytest` com coverage e garantir cobertura mínima de 80% do projeto; rodar análise estática (Semgrep CE) e `pip-audit`, conforme a stack.
- Confirmar que todos os CA (CA-01 a CA-06) têm teste citando `INS-016 CA-NN` para o rastreio.
- Atende: rastreio do bloco 10 e não funcionais; fecha CA-01 a CA-06.
