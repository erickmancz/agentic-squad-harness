# INS-017 · Design · Resumo da apólice

Origem: `requirements.md` v1, status `aprovada`, faixa `semiautonoma`, lente de serviços financeiros ativa. Perfil `python` (FastAPI, pytest, `Decimal`). Nenhuma alteração em `requirements.md`.

## 1. Visão geral

Novo endpoint somente de leitura `GET /apolices/{numero}/resumo`, na mesma app FastAPI de `src/endosso/api.py`. Devolve número, situação, cobertura e prêmio. Reaproveita o `Repositorio` e o dataclass `Apolice` (`numero`, `cobertura`, `premio`, `ativa`), sem criar tabela nem campo novo. Endosso, simulação e histórico de endossos não são tocados (bloco 10).

## 2. Componentes

| Componente | Arquivo | Responsabilidade | Efeito colateral |
|---|---|---|---|
| Regra de resumo | `src/endosso/resumo.py` (novo) | `numero_valido(numero)`, `montar_resumo(apolice)` e a exceção `NumeroInvalido`. Funções puras | Nenhum |
| Auditoria de consulta | `src/endosso/repositorio.py` (acréscimo) | `registrar_consulta_resumo(numero, usuario)`: acrescenta `{apolice, usuario, quando}` em `consultas_resumo` | Só grava na lista de auditoria em memória, nunca em `apolices` |
| Camada HTTP | `src/endosso/api.py` (acréscimo) | Rota `GET /apolices/{numero}/resumo`, modelo `ResumoApoliceResposta`, tradução de erros | Nenhum além da auditoria |
| Testes | `tests/test_ins_017_resumo.py` (novo) | Um ou mais testes por CA, citando `INS-017 CA-NN` | Nenhum |

Regra de negócio fica em `resumo.py`, separada da camada HTTP (`03-stack-cliente.md`). Nenhuma função nova altera `Apolice`.

## 3. Fluxo da requisição

1. O mecanismo de acesso recusa o chamador não autenticado antes de qualquer outra coisa (CA-08). Nem o repositório nem a auditoria são chamados.
2. `numero_valido`: regex `^AP-\d{4}$` aplicada com `fullmatch`. `AP-0001\n` não pode passar, por isso não se usa `$` sozinho. Se falhar, resposta de número inválido, sem consultar o repositório (CA-04).
3. Com o número válido, grava a auditoria com usuário, número e horário UTC (CA-09). A gravação vem antes da busca, para existir trilha também de consulta a número inexistente (ver Dúvida 4).
4. `repo.buscar(numero)`. Se vier `None`, resposta de apólice não encontrada (CA-03).
5. `montar_resumo`: projeta só os quatro campos permitidos (CA-01, CA-02, CA-06).
6. Devolve 200.

## 4. Contrato de saída

`GET /apolices/{numero}/resumo`, 200:

```json
{"apolice": "AP-0001", "situacao": "ativa", "cobertura": "100000.00", "premio": "1200.00"}
```

| Campo | Tipo | Regra |
|---|---|---|
| `apolice` | string | Número consultado |
| `situacao` | `"ativa"` ou `"inativa"` | Derivada de `Apolice.ativa` |
| `cobertura` | `Decimal`, serializado como string com 2 casas | Valor lido da base, sem recálculo (CA-05) |
| `premio` | `Decimal`, serializado como string com 2 casas | Idem |

Erros, com corpo `{"detail": "<mensagem>"}` e sem detalhe interno:

| Situação | Status | Mensagem | CA |
|---|---|---|---|
| Número fora do formato | 422 | `Número de apólice inválido.` | CA-04 |
| Apólice inexistente | 404 | `Apólice não encontrada.` | CA-03 |
| Não autenticado | Definido pelo mecanismo existente | Definida pelo mecanismo existente | CA-08 |

A mensagem de apólice não encontrada reaproveita o texto já usado na API (`"Apólice não encontrada."`). O status 422 para número inválido é proposta do design, para distinguir de 404 (INS-016 e INS-018 devolvem 404 para os dois casos; aqui o CA-04 pede mensagem própria). Ver Dúvida 3.

## 5. Decisões

| # | Decisão | Motivo | CA |
|---|---|---|---|
| D1 | Cobertura e prêmio ficam como `Decimal` em todo o caminho; o modelo de resposta usa `Decimal` e a serialização é string de 2 casas, igual ao `_serializar_valor` do histórico | Nunca `float`, nem em `json`, nem em parse de entrada | CA-05 |
| D2 | O resumo não calcula, não arredonda e não recalcula. Só formata o valor que a base já guarda | Bloco 8 proíbe regra de arredondamento ou cálculo. A lente financeira exige arredondamento explícito na spec, e a spec o exclui por não haver cálculo | CA-05 |
| D3 | Modelo de resposta com os quatro campos e `extra` proibido. Nada é copiado do objeto da apólice por reflexão | Impede vazamento de dado pessoal se a base ganhar campos | CA-06 |
| D4 | O repositório ganha só `registrar_consulta_resumo`. A rota usa `buscar`, que é leitura | Somente leitura | CA-07 |
| D5 | Validação do formato antes do acesso ao repositório | Entrada validada antes da base | CA-04 |
| D6 | A auditoria grava `usuario`, `apolice` e `quando`. Não grava corpo, cabeçalhos nem IP | Sem dado pessoal em auditoria ou log | CA-09 |
| D7 | Rota nova no `app` existente, sem router novo e sem mexer nas rotas de INS-014, INS-016 e INS-018 | Compatibilidade | bloco 10 |
| D8 | Teste de desempenho em memória como sinal de regressão. A medição do p95 real fica para ambiente com a base real | O repositório atual é em memória e não representa a base de produção | CA-10 |

## 6. Lente de serviços financeiros

- Faixa: o resumo só exibe prêmio e cobertura, não os calcula nem os altera, então fica `semiautonoma` (decisão humana já registrada no bloco 1).
- Trilha de auditoria: a regra 2 da lente trata de alteração de valor monetário. Aqui não há alteração, mas a spec pede auditoria de acesso (CA-09), atendida em D6.
- Arredondamento: não há cálculo. Ver Dúvida 5 sobre valores com mais de 2 casas na base.
- Separação de funções: o dev revisor (Mancz) é pessoa diferente do FDE (Erick) e só atua se a faixa subir para `critica`.

## 7. Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| A API não tem autenticação de verdade hoje (ver Dúvida 1) | CA-08 não pode ser implementado sem criar controle de acesso novo, o que o bloco 8 proíbe e sobe a faixa para `critica` | Tarefa T-05 bloqueada até a resposta do FDE |
| Cabeçalho de usuário forjável | A auditoria pode registrar identidade falsa | Depende da resposta da Dúvida 1 |
| Regex com `$` aceita quebra de linha final | Número inválido passa | `fullmatch` e teste com `AP-0001\n` |
| Valor da base com mais de 2 casas | Resposta mostra valor diferente do guardado, ou erro | Dúvida 5 |
| Auditoria em memória some ao reiniciar | Perda de trilha | Mesmo padrão de `auditoria` e `simulacoes`. Persistência fica fora desta story |
| CA-10 não prova p95 com a base real | Falsa segurança | D8 e pendência registrada na tarefa T-07 |

## 8. Dúvidas para o FDE

Nenhuma é pergunta em aberto da spec (o bloco "Perguntas em aberto" diz "Nenhuma"). São lacunas encontradas ao ler o código, e eu não as decidi sozinho.

1. **Mecanismo de autenticação (CA-08, CA-09).** O bloco 6 diz que se usa "o mecanismo de acesso que a API de apólices já usa". Em `src/endosso/api.py` não achei nenhum: as rotas só leem um cabeçalho opcional com valor padrão (`X-Solicitante` com padrão `canal-app`, `X-Corretor` com padrão `BRK-001`), que não autentica ninguém. Onde está o mecanismo (gateway, outro serviço, outro arquivo)? Se ele não existir no código, criar um é proibido pelo bloco 8 e levaria a faixa para `critica`. Proposta: o FDE indica o ponto de integração, e eu só o aplico como dependência da rota. Sem resposta, a task T-05 fica bloqueada e CA-08 não é entregue.
2. **Origem do usuário da auditoria (CA-09).** O usuário vem do mecanismo da Dúvida 1 (identidade autenticada) ou do cabeçalho `X-Solicitante`? Só a primeira serve como prova de quem consultou.
3. **Status do número inválido (CA-04).** Proposta: 422. As rotas de INS-016 e INS-018 devolvem 404 para formato inválido. Confirma 422 com mensagem própria, ou prefere 400 ou 404?
4. **Auditar consulta a número válido porém inexistente (CA-09).** O CA fala em "número de apólice válido", e proponho ler como formato válido, gravando também AP-9999. Confirma, ou só se grava quando a apólice existe?
5. **Valores com mais de 2 casas (CA-05).** A massa atual tem 2 casas. Se a base guardar mais, `quantize` seria arredondar, o que o bloco 8 proíbe. Proposta: não arredondar e devolver erro 500 genérico, para a divergência aparecer. Confirma?
6. **Fonte exata dos campos (bloco 6).** O bloco diz "a confirmar com o FDE". Neste design uso o `Repositorio.buscar` existente como a base de apólices. Confirma que é essa a fonte?
7. **Formato do valor na resposta (CA-01).** Proposta: string `"100000.00"`, igual ao histórico de endossos. O INS-014 e o INS-018 devolvem `Decimal` pelo pydantic. Confirma a string?
