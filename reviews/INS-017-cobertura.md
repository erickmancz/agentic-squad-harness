# INS-017 · Revisão de cobertura

Revisor: cobertura. Spec: `requirements.md` v2 (aprovada, `semiautonoma`). Branch: `feat/ins-017`.
Arquivos lidos: `requirements.md`, `design.md` (trechos de CA, D1 a D9 e riscos), `tasks.md`, `src/endosso/resumo.py`, `repositorio.py`, `api.py`, `tests/test_ins_017_resumo.py`, `tests/conftest.py`. Nenhum teste foi escrito ou alterado.

## Veredito: APROVADO COM RESSALVAS (nenhum bloqueio)

Os 9 CA têm teste que exercita o comportamento. Há uma lacuna de teste em `resumo.py` (linhas 31-32) e dois testes com pouco poder de detecção (CA-09 e o campo `quando` do CA-08). Nenhum deles impede o merge na faixa `semiautonoma`. Recomendo fechar a lacuna das linhas 31-32 antes do merge, porque custa um teste pequeno.

## Resultados dos scripts

| Execução | Resultado |
|---|---|
| `python scripts/rastrear_aceite.py` | [OK] 27 critérios com teste rastreado (INS-014, 016, 017 e 018 juntos) |
| `python ash.py etapa testes` | 72 passaram, 0 falhas |
| Cobertura total | 98,41% (mínimo do perfil: 80%) |
| `resumo.py` | 90%, faltam as linhas 31-32 |
| `repositorio.py` | 100% |
| `api.py` | 99%, falta a linha 95 |

A linha 95 de `api.py` é o `404` por formato inválido da simulação (INS-018). Não pertence à INS-017 e não é relevante aqui. A rota do resumo (`api.py`, linhas 157 em diante) está 100% coberta.

## Matriz CA × teste

| CA | Testes que cobrem | Cobre de fato? | Observação |
|---|---|---|---|
| CA-01 | `ca_01_resumo_ap_0001_ativa` (regra), `ca_01_http_ap_0001` | Sim | Compara o corpo inteiro, com valores em string |
| CA-02 | `ca_02_resumo_ap_0002_inativa`, `ca_02_http_ap_0002` | Sim | Idem, situação `inativa` |
| CA-03 | `ca_03_http_ap_9999_nao_encontrada` | Sim | Confere 404 e a mensagem exata |
| CA-04 | `ca_04_numero_valido_*` (7 formatos, com `\n`, minúscula e letra), `ca_04_http_invalido_422_e_nao_consulta_a_base` (3 números), `ca_04_http_quebra_de_linha_e_422` | Sim | Confere 422, mensagem exata e zero chamadas a `repo.buscar` |
| CA-05 | `ca_05_valores_sao_decimal_com_duas_casas`, `ca_05_valor_com_tres_casas_levanta_erro_sem_arredondar`, `ca_05_http_valor_nao_e_float`, `ca_05_http_valor_com_tres_casas_devolve_erro_generico` | Parcial | Cobre `Decimal`, completar zeros, 3 casas e 500 genérico. Não cobre valor não finito nem fora de precisão (lacuna L1) |
| CA-06 | `ca_06_resumo_so_tem_os_quatro_campos`, `ca_06_http_resposta_sem_dado_pessoal` | Sim | Confere o conjunto exato de chaves e que o solicitante não vaza |
| CA-07 | `ca_07_consulta_nao_altera_apolices` | Sim | Compara cópia profunda de `apolices`, `auditoria`, `simulacoes` e `historico_endossos` antes e depois, e o tamanho de `consultas_resumo` (3, porque AP-123 não grava) |
| CA-08 | 2 testes do repositório e 5 testes HTTP (existente, inexistente, inválido não grava, só 3 chaves, padrão `canal-app`) | Sim, com ressalva L3 | O CA em si não trata do caso sem cabeçalho. O design D6 e a T-05 o tratam, e ele está testado |
| CA-09 | `ca_09_p95_em_memoria_ate_2s` | Formal | Roda e cita o CA, mas quase não detecta regressão (ver F2). O próprio design (D8) diz que é só sinal de regressão |

Todos os 9 CA têm teste que os exercita, e não só cita. Nenhum CA está sem teste.

## Lacunas

### L1 · `resumo.py` linhas 31-32 sem teste (relevante)
É o ramo `except InvalidOperation` de `_checar_duas_casas`, que levanta `ValorInvalido("Valor inválido na base.")`. Ele é alcançado quando `Decimal.quantize` não consegue produzir o resultado:

- `Decimal("NaN")` e `Decimal("sNaN")`;
- `Decimal("Infinity")` e `Decimal("-Infinity")`;
- valores acima da precisão do contexto, por exemplo `Decimal("1E+30")`, cujo `quantize` para duas casas estoura 28 dígitos.

Por que importa: a spec (bloco 8) diz que valor inválido na base devolve erro genérico, sem detalhe interno e sem arredondar. Esse ramo é a defesa para valor que não é número finito. Hoje nada impede uma regressão que o apague ou o troque por `return valor`, e então um `NaN` ou `Infinity` chegaria à resposta como string.

Teste sugerido (para o implementador, não escrevi):
- Parametrizado com `Decimal("NaN")`, `Decimal("Infinity")`, `Decimal("-Infinity")` e `Decimal("1E+30")`, em cobertura e em prêmio: `montar_resumo` deve levantar `ValorInvalido`. Citar `INS-017 CA-05`.
- Um caso HTTP com `NaN` na base, esperando 500 com `{"detail": "Erro interno."}`. Citar `INS-017 CA-05`.

Com esses testes, `resumo.py` vai a 100%.

### L2 · Valor negativo ou zero não é coberto (informativo)
A spec não define regra para valor negativo ou zero, e o código os deixa passar se tiverem 2 casas. Não há teste e não há CA. Não bloqueia, mas vale registrar como pergunta para a spec, se o PO quiser rejeitá-los.

### L3 · Auditoria em caso de erro 500 (informativo)
A auditoria é gravada antes da busca e do `montar_resumo` (design, passo 2). Numa consulta que acaba em 500 por valor inválido, o registro é gravado. Isso é coerente com o design, mas nenhum teste fixa o comportamento. O CA-08 não o exige. Sugestão de baixa prioridade: um teste que afirme o comportamento escolhido.

## Testes frágeis ou fracos

| # | Teste | Problema | Gravidade |
|---|---|---|---|
| F1 | `ca_08_registro_tem_usuario_apolice_e_horario` | `assert reg["quando"]` só confere que não é vazio. Não verifica que é ISO-8601 em UTC, que é o que o design promete (horário UTC). Trocar o horário por qualquer texto continuaria verde | Baixa |
| F2 | `ca_09_p95_em_memoria_ate_2s` | Mede 100 chamadas em memória com limite de 2 s. Uma chamada em memória leva milissegundos, então o teste não falha nem com uma regressão de 100 vezes. A primeira chamada inclui o aquecimento do `TestClient`. O limite fixo em tempo absoluto também pode oscilar em máquina de CI lenta, embora a folga seja grande. O design (D8, T-06) já declara que não prova o CA-09 com a base real | Baixa. Seguir como pendência de homologação |
| F3 | `ca_05_http_valor_nao_e_float` | Só confere `isinstance(..., str)`. Não confere o formato de duas casas na resposta HTTP. O formato está coberto pelo teste de regra e pelos CA-01/02, que comparam a string exata. A cobertura existe, mas por outro teste | Muito baixa |
| F4 | `ca_04_http_invalido_422_e_nao_consulta_a_base` | O espião só verifica `repo.buscar`. O CA-04 diz "a base não é consultada", e o teste não afirma explicitamente que a auditoria também não foi gravada neste caso. O caso `AP-123` está em `ca_08_http_numero_invalido_nao_grava` (`consultas_resumo == []`), então não há buraco, só a dependência entre dois testes | Muito baixa |
| F5 | `ca_07_consulta_nao_altera_apolices` | A cópia profunda compara dicionários de `Apolice` e depende de a dataclass ter igualdade por valor. Funciona hoje. Se `Apolice` mudar para comparação por identidade, o teste passaria sem detectar mutação. É risco teórico | Muito baixa |

Pontos positivos: a fixture `cliente` recria `api.repo` a cada teste, então não há vazamento de estado entre testes. Os testes usam só massa sintética (AP-0001, AP-0002, AP-9999, `atendente-01`), sem dado pessoal. Os testes de formato incluem `AP-0001\n`, o caso que o `$` sozinho deixaria passar, e a versão HTTP com `%0A`.

## Resumo

- CA sem teste: nenhum.
- Cobertura: 98,41% total. `resumo.py` em 90%.
- Trecho sem cobertura relevante para a spec: `resumo.py` linhas 31-32 (valor não finito ou fora da precisão, CA-05 e bloco 8). A linha 95 de `api.py` é da INS-018.
- Ação recomendada antes do merge: adicionar os testes de L1 (implementador). F1 e F2 podem seguir como dívida. L2 e L3 são perguntas para o PO e o FDE, sem bloqueio.
