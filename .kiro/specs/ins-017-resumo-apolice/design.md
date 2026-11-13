# INS-017 · Design · Resumo da apólice

Origem: `requirements.md` v2, status `aprovada`, faixa `semiautonoma`, lente de serviços financeiros ativa. Perfil `python` (FastAPI, pytest, `Decimal`). Nenhuma alteração em `requirements.md`.

## 1. Visão geral

Novo endpoint somente de leitura `GET /apolices/{numero}/resumo`, na mesma app FastAPI de `src/endosso/api.py`. Devolve número, situação, cobertura e prêmio. Reaproveita o `Repositorio` e o dataclass `Apolice` (`numero`, `cobertura`, `premio`, `ativa`), sem criar tabela nem campo novo. Fonte dos campos: `Repositorio.buscar`. Endosso, simulação e histórico de endossos não são tocados (bloco 10).

Controle de acesso (autenticação e perfis) está fora de escopo (bloco 8): a rota não cria nem aplica nenhum mecanismo de acesso.

## 2. Componentes

| Componente | Arquivo | Responsabilidade | Efeito colateral |
|---|---|---|---|
| Regra de resumo | `src/endosso/resumo.py` (novo) | `numero_valido(numero)`, `montar_resumo(apolice)` e as exceções `NumeroInvalido` e `ValorInvalido`. Funções puras | Nenhum |
| Auditoria de consulta | `src/endosso/repositorio.py` (acréscimo) | `registrar_consulta_resumo(numero, solicitante)`: acrescenta `{apolice, usuario, quando}` em `consultas_resumo` | Só grava na lista de auditoria em memória, nunca em `apolices` |
| Camada HTTP | `src/endosso/api.py` (acréscimo) | Rota `GET /apolices/{numero}/resumo`, modelo `ResumoApoliceResposta`, leitura do cabeçalho `X-Solicitante`, tradução de erros | Nenhum além da auditoria |
| Testes | `tests/test_ins_017_resumo.py` (novo) | Um ou mais testes por CA, citando `INS-017 CA-NN` | Nenhum |

Regra de negócio fica em `resumo.py`, separada da camada HTTP (`03-stack-cliente.md`). Nenhuma função nova altera `Apolice`.

## 3. Fluxo da requisição

1. `numero_valido`: regex `^AP-\d{4}$` aplicada com `fullmatch`. `AP-0001\n` não pode passar, por isso não se usa `$` sozinho. Se falhar, resposta HTTP 422 `Número de apólice inválido.`, sem auditoria e sem consultar o repositório (CA-04).
2. Com o formato válido, grava a auditoria com o valor de `X-Solicitante`, o número e o horário UTC (CA-08). A gravação vem antes da busca, para existir trilha também de consulta a número válido inexistente, como AP-9999.
3. `repo.buscar(numero)`. Se vier `None`, resposta de apólice não encontrada (CA-03).
4. `montar_resumo`: projeta só os quatro campos permitidos (CA-01, CA-02, CA-06). Se cobertura ou prêmio tiver mais de 2 casas decimais, levanta `ValorInvalido`.
5. Devolve 200. `ValorInvalido` vira erro genérico (ver seção 4).

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
| Valor da base com mais de 2 casas | 500 | Mensagem genérica, sem detalhe interno (por exemplo `Erro interno.`) | bloco 8 |

A mensagem e o 404 de apólice não encontrada reaproveitam o padrão já usado na API. O 500 para valor com mais de 2 casas é escolha de design: a spec pede "erro genérico" e não fixa o status.

## 5. Decisões

| # | Decisão | Motivo | CA |
|---|---|---|---|
| D1 | Cobertura e prêmio ficam como `Decimal` em todo o caminho; a resposta serializa string de 2 casas, igual ao `_serializar_valor` do histórico | Nunca `float`, nem em `json`, nem em parse de entrada | CA-05 |
| D2 | O resumo não calcula, não arredonda e não recalcula. Só formata o valor que a base já guarda. Valor com mais de 2 casas (detectado quando o valor difere do mesmo valor com 2 casas) levanta `ValorInvalido` e a rota devolve erro genérico. Completar com zeros (`1200` para `1200.00`) não é arredondar e é permitido | Bloco 8 proíbe arredondamento e cálculo. A divergência aparece em vez de ser escondida | CA-05 |
| D3 | Modelo de resposta com os quatro campos e `extra` proibido. Nada é copiado do objeto da apólice por reflexão | Impede vazamento de dado pessoal se a base ganhar campos | CA-06 |
| D4 | O repositório ganha só `registrar_consulta_resumo`. A rota usa `buscar`, que é leitura | Somente leitura | CA-07 |
| D5 | Validação do formato antes do acesso ao repositório | Entrada validada antes da base | CA-04 |
| D6 | A auditoria grava `usuario` (valor de `X-Solicitante`), `apolice` e `quando`. Não grava IP, nome, outros cabeçalhos nem dado do segurado. `X-Solicitante` é dado pessoal comum do atendente, declarado e não comprovado: o registro não prova quem consultou | Mínimo necessário para a finalidade (rastrear quem consultou). LGPD | CA-08 |
| D7 | Rota nova no `app` existente, sem router novo e sem mexer nas rotas de INS-014, INS-016 e INS-018 | Compatibilidade | bloco 10 |
| D8 | Teste de desempenho em memória como sinal de regressão. A medição do p95 real fica para ambiente com a base real | O repositório atual é em memória e não representa a base de produção | CA-09 |
| D9 | Nenhuma expiração ou descarte dos registros de auditoria. A lista em memória não tem rotina de descarte | Descarte automático após 6 meses é fora de escopo (bloco 8) | CA-08 |

## 6. Lente de serviços financeiros

- Faixa: o resumo só exibe prêmio e cobertura, não os calcula nem os altera, então fica `semiautonoma` (decisão humana registrada no bloco 1). Se a story passar a criar autenticação ou perfil, a faixa sobe para `critica`.
- Trilha de auditoria: a regra 2 da lente trata de alteração de valor monetário. Aqui não há alteração, mas a spec pede auditoria de acesso (CA-08), atendida em D6.
- Arredondamento: não há cálculo nem arredondamento. Valor com mais de 2 casas gera erro genérico (D2).
- Separação de funções: o dev revisor (Mancz) é pessoa diferente do FDE (Erick) e só atua se a faixa subir para `critica`.

## 7. Riscos

| Risco | Efeito | Mitigação |
|---|---|---|
| `X-Solicitante` é declarado e forjável | A auditoria pode registrar identidade falsa | Aceito pela spec (declarado, não comprovado). Documentado em D6; não usar a auditoria como prova de identidade |
| `X-Solicitante` é dado pessoal do atendente | Tratamento sem prazo de descarte | Finalidade e retenção de 6 meses no bloco 6, a confirmar pelo cliente. Descarte automático fica para story futura (D9) |
| Regex com `$` aceita quebra de linha final | Número inválido passa | `fullmatch` e teste com `AP-0001\n` |
| Valor da base com mais de 2 casas | Consulta falha | Erro genérico intencional (D2); sem arredondar |
| Auditoria em memória some ao reiniciar | Perda de trilha | Mesmo padrão de `auditoria` e `simulacoes`. Persistência fora desta story |
| CA-09 não prova p95 com a base real | Falsa segurança | D8 e pendência registrada na tarefa T-07 |
| Rota sem controle de acesso | Qualquer chamador consulta prêmio e cobertura | Decisão do PO, registrada como fora de escopo (bloco 8) |

## 8. Dúvidas para o FDE

Nenhuma é pergunta em aberto da spec. As dúvidas anteriores foram respondidas pela v2 e saíram deste documento.

1. **`X-Solicitante` ausente (CA-08).** O CA-08 trata o caso "com o cabeçalho informado". A spec não diz o que fazer sem ele. As rotas atuais usam um valor padrão (`canal-app`) quando o cabeçalho falta. Proposta: seguir esse padrão e gravar o valor padrão. Alternativa: recusar a consulta. Qual vale?
2. **Texto do CA-05.** O CA diz que cobertura e prêmio são "calculados e transportados como `Decimal`", mas o bloco 8 proíbe cálculo. Leio como "lidos e transportados", sem cálculo. Confirma?
