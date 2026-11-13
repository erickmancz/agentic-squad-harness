# INS-017 · Tarefas · Resumo da apólice

Origem: `design.md` desta pasta. Cada tarefa é pequena, cita os CA que cobre e prevê o teste que cita `INS-017 CA-NN` no nome ou na docstring. Testes ficam em `tests/test_ins_017_resumo.py`. Rodar com `python ash.py testar` e `python ash.py etapa <nome>`. Massa sintética: AP-0001, AP-0002 e AP-9999.

Ordem: T-01 a T-04 não dependem das Dúvidas do design. T-05 depende da Dúvida 1 e T-06 da Dúvida 4.

| # | Tarefa | CA | Teste previsto | Depende de |
|---|---|---|---|---|
| T-01 | Criar `src/endosso/resumo.py` com `numero_valido` (`fullmatch` de `AP-` mais 4 dígitos) e a exceção `NumeroInvalido`, com docstring de uma linha em cada função | CA-04 | `test_ins_017_ca_04_numero_valido_aceita_ap_0001` e `test_ins_017_ca_04_numero_valido_rejeita_12345_ap_123_ap_12345_e_quebra_de_linha` | Nada |
| T-02 | Em `resumo.py`, criar `montar_resumo(apolice)` que devolve só `apolice`, `situacao`, `cobertura` e `premio`, sem arredondar nem calcular | CA-01, CA-02, CA-05, CA-06 | `test_ins_017_ca_01_resumo_ap_0001_ativa`, `test_ins_017_ca_02_resumo_ap_0002_inativa`, `test_ins_017_ca_05_valores_sao_decimal_com_duas_casas` (checa `isinstance(..., Decimal)` e ausência de `float`), `test_ins_017_ca_06_resumo_so_tem_os_quatro_campos` | T-01 |
| T-03 | Em `repositorio.py`, criar a lista `consultas_resumo` e `registrar_consulta_resumo(numero, usuario)` gravando `apolice`, `usuario` e `quando` (UTC). Não tocar nos métodos existentes | CA-09, CA-07 | `test_ins_017_ca_09_registro_tem_usuario_apolice_e_horario`, `test_ins_017_ca_09_registro_nao_tem_dado_pessoal` | Nada |
| T-04 | Em `api.py`, criar `ResumoApoliceResposta` e a rota `GET /apolices/{numero}/resumo`: formato, auditoria, busca e projeção (fluxo do design, seção 3). Número inválido devolve 422 `Número de apólice inválido.`, inexistente devolve 404 `Apólice não encontrada.`, valores serializados como string com 2 casas. Rotas de INS-014, INS-016 e INS-018 sem mudança | CA-01, CA-02, CA-03, CA-04, CA-05, CA-06 | `test_ins_017_ca_01_http_ap_0001`, `test_ins_017_ca_02_http_ap_0002`, `test_ins_017_ca_03_http_ap_9999_nao_encontrada`, `test_ins_017_ca_04_http_invalido_nao_consulta_a_base` (substitui `repo.buscar` por um espião e confirma zero chamadas), `test_ins_017_ca_05_http_valor_nao_e_float`, `test_ins_017_ca_06_http_resposta_sem_dado_pessoal` | T-01, T-02, T-03 |
| T-05 | Aplicar à rota o mecanismo de acesso já existente da API de apólices, como dependência, antes da validação e da base. Proibido criar autenticação, perfil ou controle novo | CA-08 | `test_ins_017_ca_08_nao_autenticado_e_recusado`, `test_ins_017_ca_08_nao_autenticado_nao_consulta_a_base` (espião em `repo.buscar` e em `registrar_consulta_resumo`, zero chamadas) | **Dúvida 1** (bloqueada). Se o mecanismo não existir, parar e avisar o FDE: criar controle novo sobe a faixa para `critica` |
| T-06 | Ligar a auditoria à rota: autenticado com número de formato válido grava um registro. Número inválido e não autenticado não gravam | CA-09 | `test_ins_017_ca_09_http_consulta_valida_grava_um_registro`, `test_ins_017_ca_09_http_numero_invalido_nao_grava`, `test_ins_017_ca_09_http_nao_autenticado_nao_grava` | T-04, T-05, **Dúvidas 2 e 4** |
| T-07 | Teste de somente leitura e de desempenho em memória | CA-07, CA-10 | `test_ins_017_ca_07_consulta_nao_altera_apolices` (compara `repo.apolices`, `auditoria`, `simulacoes` e `historico_endossos` antes e depois de várias consultas), `test_ins_017_ca_10_p95_em_memoria_ate_2s` (100 consultas, p95 até 2 s; sinal de regressão, não prova com a base real) | T-04 |
| T-08 | Teste de compatibilidade: as rotas de endosso, simulação e histórico continuam com o mesmo comportamento. Rodar o conjunto existente (`test_ins_014_*`, `test_ins_016_*`, `test_ins_018_*`) sem edição | bloco 10 (apoio a CA-07) | Suítes existentes verdes. Nenhum teste novo próprio | T-04 |
| T-09 | Rodar `python ash.py testar`, depois `python ash.py ci` (spec-gate, rastreio, cobertura mínima 80% do perfil) e corrigir o que falhar. Conferir que todo CA-01 a CA-10 aparece no rastreio | CA-01 a CA-10 | Rastreio mostra os 10 CA cobertos | T-01 a T-08 |

## Cobertura dos CA

| CA | Tarefas |
|---|---|
| CA-01 | T-02, T-04 |
| CA-02 | T-02, T-04 |
| CA-03 | T-04 |
| CA-04 | T-01, T-04 |
| CA-05 | T-02, T-04 |
| CA-06 | T-02, T-04 |
| CA-07 | T-03, T-07 |
| CA-08 | T-05 |
| CA-09 | T-03, T-06 |
| CA-10 | T-07 |

## Fora do escopo desta story

- Criar autenticação, perfil ou controle de acesso (bloco 8).
- Escrever na base, tocar endosso, simulação ou histórico.
- Persistir a auditoria fora da memória.
- Medir o p95 com a base real (pendência de homologação, ver risco do design).

## Definição de pronto

- Os 10 CA com teste que cita `INS-017 CA-NN`, todos verdes.
- `python ash.py ci` verde, cobertura de pelo menos 80%.
- Dúvidas 1 a 7 do `design.md` respondidas pelo FDE e refletidas no código.
- Aprovação do design pelo FDE (portão `aprovar-design`) antes de qualquer implementação.
