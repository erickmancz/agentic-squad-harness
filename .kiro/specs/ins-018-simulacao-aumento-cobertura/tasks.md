# INS-018 · Tasks · Simulação de prêmio por aumento de cobertura

Derivado de `requirements.md` (v1, aprovada, faixa critica) e de `design.md`. Tarefas pequenas, em ordem de implementação. Cada tarefa cita os CA que atende. Testes `pytest` citam `INS-018 CA-NN` no nome ou docstring (regra de rastreio, `scripts/rastrear_aceite.py`). Cobertura mínima do projeto: 80%. Valores monetários em `decimal.Decimal` (nunca `float`), HALF_UP em centavos. Funções de regra puras e separadas da camada HTTP. Toda função pública com docstring de uma linha. Não alterar a fórmula do prêmio, o limite de 2x nem o arredondamento (bloco 8); reusar `recalcular_premio` da INS-014.

## 1. Função pura de simulação (reuso da regra de prêmio)
- Em `src/endosso/regras.py`, criar a função pura `simular_premio(apolice, cobertura_pedida)` que delega a `recalcular_premio` já existente (mesma fórmula proporcional, mesmo limite de 2x, mesmo HALF_UP em centavos), sem alterar a apólice e sem tocar o repositório.
- Não copiar nem reescrever a fórmula, o limite nem o arredondamento; apenas reutilizar.
- Docstring de uma linha citando o reuso da regra da INS-014.
- Atende: INS-018 CA-01, CA-02, CA-03, CA-04 (herda validações e cálculo de `recalcular_premio`).

## 2. Método de auditoria da simulação no repositório (sem dado pessoal)
- Em `src/endosso/repositorio.py`, criar `registrar_simulacao(apolice, cobertura_pedida, premio_simulado, solicitante)` que acrescenta um registro à trilha de auditoria SEM alterar a apólice e SEM criar endosso.
- O registro contém exatamente: `apolice`, `cobertura_atual`, `cobertura_pedida`, `premio_simulado`, `solicitante` (identificador técnico, ex.: BRK-001) e `quando` (ISO-8601 UTC). Nenhum campo pessoal (sem CPF, nome, e-mail, telefone). Valores monetários como string de duas casas.
- Não reutilizar `aplicar_endosso` nem `replace`; manter o registro de simulação distinto do endosso efetivo.
- Atende: INS-018 CA-06 (não mutação/sem endosso), CA-07 (registro de auditoria sem dado pessoal).

## 3. Endpoint FastAPI de simulação
- Em `src/endosso/api.py`, criar `POST /apolices/{numero}/simulacoes/aumento-cobertura` com corpo `SimulacaoPedido` (`cobertura_pedida: Decimal`, `gt=0`, `max_digits=12`, `decimal_places=2`) e cabeçalho de identificador técnico de quem pede (ex.: `X-Corretor`, padrão de demo).
- Validar o formato do número da apólice (`^AP-\d{4}$`); formato inválido ou apólice inexistente -> 404 "Apólice não encontrada." sem dado pessoal.
- Chamar `simular_premio`; mapear `ApoliceInativa` -> 409 e `CoberturaInvalida` -> 422; em sucesso, chamar `registrar_simulacao` e devolver 200 com `SimulacaoResposta` (`apolice`, `cobertura_atual`, `cobertura_pedida`, `premio_atual`, `premio_simulado`), valores como string de duas casas.
- A camada HTTP só orquestra: nenhuma fórmula de prêmio nem cálculo de limite aqui.
- Atende: INS-018 CA-01, CA-02, CA-03, CA-04, CA-05, CA-07.

## 4. Garantia de não mutação e ausência de dado pessoal
- Revisar o endpoint e o método de auditoria para assegurar que nenhum caminho (sucesso ou erro) altera cobertura, prêmio ou cria endosso, e que nem o log nem as mensagens de erro contêm dado pessoal (usar mensagens genéricas).
- Atende: INS-018 CA-06, CA-07; não funcionais blocos 7 e 8.

## 5. Testes puros de domínio (cálculo e HALF_UP)
- Em `tests/test_ins_018_simulacao.py`, testes `pytest` puros:
  - AP-0001 100.000 -> 150.000 dá prêmio 1.800,00 (`test_ins_018_ca_01_premio_proporcional`, INS-018 CA-01);
  - 33.333 -> 50.000 dá 1.166,67 por HALF_UP em centavos (`test_ins_018_ca_02_half_up_centavos`, INS-018 CA-02);
  - apólice inativa levanta `ApoliceInativa` (`test_ins_018_ca_03_regra_pura_inativa`, INS-018 CA-03);
  - cobertura acima de 2x levanta `CoberturaInvalida` e exatamente 2x é aceito (`test_ins_018_ca_04_limite_2x`, INS-018 CA-04).
- Massa sintética; valores em `Decimal`.
- Atende: INS-018 CA-01, CA-02, CA-03, CA-04.

## 6. Testes do endpoint (status e contrato)
- No mesmo arquivo de teste, testes com `TestClient` (fixture `cliente`):
  - AP-0001 -> 150.000 retorna 200 com `premio_simulado` 1.800,00 (`test_ins_018_ca_01_endpoint_200`, INS-018 CA-01);
  - AP-0003 -> 50.000 retorna 200 com `premio_simulado` 1.166,67 (`test_ins_018_ca_02_endpoint_200`, INS-018 CA-02);
  - apólice inativa (AP-0002) retorna 409 (`test_ins_018_ca_03_inativa_409`, INS-018 CA-03);
  - cobertura acima de 2x retorna 422 e exatamente 2x retorna 200 (`test_ins_018_ca_04_acima_2x_422`, INS-018 CA-04);
  - apólice inexistente (AP-9999) retorna 404 (`test_ins_018_ca_05_inexistente_404`, INS-018 CA-05).
- Atende: INS-018 CA-01, CA-02, CA-03, CA-04, CA-05.

## 7. Testes de não mutação (só consulta)
- Testes que, após cada cenário (sucesso, 409, 422, 404), conferem que a apólice mantém a mesma cobertura e o mesmo prêmio e que nenhum endosso foi criado (`test_ins_018_ca_06_apolice_intacta`, INS-018 CA-06).
- Comparar o estado da apólice antes e depois da chamada.
- Atende: INS-018 CA-06.

## 8. Teste da trilha de auditoria sem dado pessoal
- Teste que, após uma simulação bem-sucedida pedida por `BRK-001`, verifica o último registro de auditoria da simulação: contém `apolice`, `cobertura_atual`, `cobertura_pedida`, `premio_simulado`, `solicitante` e `quando`, com os valores esperados, e NÃO contém nenhum dado pessoal (sem CPF, nome, e-mail, telefone). Conferir o conjunto exato de chaves (`test_ins_018_ca_07_auditoria_sem_dado_pessoal`, INS-018 CA-07).
- Atende: INS-018 CA-07.

## 9. Verificação de cobertura e CI local
- Rodar `pytest` com coverage e garantir cobertura mínima de 80% do projeto; rodar Semgrep CE (regras em `.semgrep/`) e `pip-audit` sobre `requirements.txt`, conforme a stack.
- Confirmar que todos os CA (CA-01 a CA-07) têm teste citando `INS-018 CA-NN` para o rastreio (`scripts/rastrear_aceite.py`).
- Atende: rastreio do bloco 10 e não funcionais; fecha CA-01 a CA-07.
