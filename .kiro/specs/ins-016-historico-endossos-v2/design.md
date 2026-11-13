# INS-016 · Design · Consulta do histórico de endossos de uma apólice

Derivado de `requirements.md` (versão 2, status aprovada, faixa semiautonoma). Operação somente de leitura; nenhuma alteração de cálculo de prêmio nem da regra de endosso (bloco 8 da spec).

## 1. Visão geral

A solução expõe um endpoint de leitura que devolve o histórico de endossos de uma apólice. Segue a convenção do projeto (`03-stack-cliente`): regra de negócio pura e separada da camada HTTP, valores monetários em `decimal.Decimal`, docstring de uma linha em funções públicas. A rota e a estrutura de pastas acompanham o padrão já existente no repositório (INS-014), em português; os campos do contrato de saída e as funções de domínio ficam em inglês. Esta documentação em português. Ver a nota de nomenclatura na seção 2.

Na demo os dados vivem em memória: um repositório de apólices e uma trilha de auditoria de endossos, ambos fictícios, com massa sintética (bloco 6 e bloco 9 da spec).

## 2. Arquitetura

Três camadas, com dependências apontando sempre para o domínio:

| Camada | Responsabilidade | Pasta/arquivo |
|---|---|---|
| Domínio (pura) | Modelo do item de endosso (`EndorsementItem`), regra de ordenação com desempate (`sort_endorsements`), montagem da resposta sem recálculo e sem dado pessoal (`project_endorsement`, `build_history`) | `src/endosso/regras.py` |
| Repositórios em memória | Guardar apólices e a trilha de auditoria; dizer se uma apólice existe (`existe`) e devolver seus endossos (`endossos_de`) | `src/endosso/repositorio.py` |
| HTTP (FastAPI) | Validar o formato do número da apólice, chamar o domínio (`historico_endossos`, `buscar`), mapear para 200/404, serializar | `src/endosso/api.py` |

A camada de domínio não importa FastAPI nem conhece HTTP. A camada HTTP não contém regra de ordenação nem de montagem: apenas orquestra e traduz para status/JSON. Isso atende à convenção "funções de regra de negócio são puras e ficam separadas da camada HTTP".

### Fluxo da requisição

1. Chegada em `GET /apolices/{numero}/endossos` com perfil de atendente autenticado (bloco 6: qualquer atendente autenticado consulta qualquer apólice; sem segregação por carteira nesta demo).
2. A camada HTTP valida o formato `AP-` + 4 dígitos (regex `^AP-\d{4}$`). Fora do formato, não corresponde a apólice válida -> 404 "Apólice não encontrada." (bloco 6; mesma mensagem de inexistente para não vazar informação).
3. O domínio consulta o repositório (`existe`/`endossos_de`). Apólice inexistente -> sinal de "não encontrada" -> HTTP devolve 404.
4. Apólice existente: o repositório devolve os endossos da trilha; o domínio ordena (`sort_endorsements`) e monta os itens (`project_endorsement`/`build_history`) preservando os valores gravados.
5. HTTP devolve 200 com a lista (possivelmente vazia).

### Decisão de nomenclatura

A rota e a estrutura de pastas seguem o padrão já existente no repositório (INS-014), em português: módulo `src/endosso/` com `api.py` (FastAPI), `regras.py` (domínio puro) e `repositorio.py` (dados em memória); rota `GET /apolices/{numero}/endossos`, coerente com a rota POST existente `/apolices/{numero}/endossos/aumento-cobertura`. Não existe `src/endorsements/`. Os campos do contrato de saída e as funções de domínio ficam em inglês por serem contrato (`EndorsementItem`; `endorsement_id`, `date`, `coverage_before`, `coverage_after`, `premium_before`, `premium_after`; `project_endorsement`, `sort_endorsements`, `build_history`); as funções e a rota de aplicação ficam em português acompanhando a INS-014 (`buscar`, `existe`, `endossos_de`, `historico_endossos`). Essa escolha também resolve a dúvida sobre o formato da apólice: mantém-se o hífen (`AP-0001`, regex `^AP-\d{4}$`), coerente com os exemplos da spec e com a rota da INS-014.

## 3. Modelo de dados

### Item de endosso devolvido (contrato de saída)

Exatamente os campos definidos no bloco 4 (CA-02) e no exemplo do bloco 9. Nenhum campo pessoal.

| Campo | Tipo interno | Serialização | Origem |
|---|---|---|---|
| `endorsement_id` | `int` | número | trilha de auditoria |
| `date` | `datetime` (UTC, tz-aware) | string ISO-8601 em UTC, ex.: `2026-02-10T13:45:00Z` | trilha de auditoria |
| `coverage_before` | `Decimal` | string com 2 casas, ex.: `"100000.00"` | trilha, sem recálculo |
| `coverage_after` | `Decimal` | string com 2 casas | trilha, sem recálculo |
| `premium_before` | `Decimal` | string com 2 casas | trilha, sem recálculo |
| `premium_after` | `Decimal` | string com 2 casas | trilha, sem recálculo |

O item de domínio é a dataclass imutável `EndorsementItem` (`dataclass(frozen=True)`) com esses campos. A trilha de auditoria interna pode conter outros campos (inclusive eventuais campos pessoais); o domínio projeta apenas os seis campos acima, garantindo o bloco 6/7 (omissão de qualquer dado pessoal da resposta, log e erro).

### Repositório de apólices (em memória)

- `existe(numero) -> bool`: informa se a apólice existe (`buscar` recupera o registro da apólice).
- Massa sintética: AP-0001 (existe, com endossos), AP-0003 (existe, sem endosso), AP-9999 (não existe).

### Trilha de auditoria (em memória)

- `endossos_de(numero) -> list`: endossos brutos da apólice, sem ordem garantida.
- AP-0001: 2 endossos. Para cobrir CA-01 (ordenação por data) e CA-06 (empate de data com desempate por id decrescente), a massa inclui dois endossos na mesma data com identificadores distintos (ex.: 11 e 12), conforme bloco 9.

## 4. Contrato do endpoint

- Método e rota: `GET /apolices/{numero}/endossos`.
- Parâmetro de caminho: `numero`, formato `AP-` + 4 dígitos (regex `^AP-\d{4}$`; a spec cita `AP-0001` e a INS-014 já usa o hífen na rota, então o design adota o hífen).
- Autenticação: perfil de atendente (demo). Sem segregação por carteira.
- Respostas:

| Situação | Status | Corpo |
|---|---|---|
| Apólice existente com N endossos | 200 | lista JSON com N itens ordenados |
| Apólice existente sem endosso (AP-0003) | 200 | `[]` |
| Apólice inexistente (AP-9999) ou formato inválido | 404 | `{"detail": "Apólice não encontrada."}` sem dado pessoal |

Exemplo de item (massa sintética, bloco 9):

```json
{"endorsement_id": 12, "date": "2026-02-10T13:45:00Z", "coverage_before": "100000.00", "coverage_after": "150000.00", "premium_before": "1200.00", "premium_after": "1500.00"}
```

## 5. Regra de ordenação com desempate

Definida nos blocos 3 e 4 (CA-01, CA-06). A lista é ordenada:

1. por `date` decrescente (mais recente primeiro);
2. em empate de `date`, por `endorsement_id` decrescente (identificador maior primeiro).

Implementação pura no domínio em `sort_endorsements`, com uma chave composta, ex.: `sorted(items, key=lambda e: (e.date, e.endorsement_id), reverse=True)`. Como `reverse=True` aplica decrescente aos dois critérios da tupla, atende data decrescente e id decrescente no empate de uma só vez. A ordenação não depende de ordem de inserção na trilha.

## 6. Tratamento monetário

Definido no bloco 4 (CA-05) e no bloco 9. Regras:

- `coverage_*` e `premium_*` são `decimal.Decimal`, nunca `float` (convenção do projeto).
- Os valores são os gravados na trilha; o domínio não recalcula nem arredonda de forma que altere o valor. Mantém-se duas casas decimais como na trilha.
- Na serialização, cada `Decimal` vira string com duas casas (ex.: `"1500.00"`), preservando o valor. A conversão para string evita a imprecisão de `float` no JSON.
- A massa sintética guarda os valores como strings de `Decimal` com duas casas, convertidas para `Decimal` ao carregar.

## 7. Como cada decisão da spec se reflete no design

| Decisão da spec | Reflexo no design |
|---|---|
| Somente leitura (blocos 3, 6, 10) | Apenas `GET`; nenhum método de escrita; repositórios só leem |
| Formato AP+4 dígitos (bloco 6) | Validação de caminho `^AP-\d{4}$`; inválido -> 404 |
| Ordenação recente->antigo + desempate id decrescente (blocos 3, 4) | Chave composta `(date, endorsement_id)` com `reverse=True` em `sort_endorsements` |
| Data UTC ISO-8601 (blocos 3, 9) | `datetime` tz-aware em UTC serializado como `...Z` |
| Monetário em `Decimal`, sem recálculo (bloco 4 CA-05) | `Decimal` no domínio, string de 2 casas na saída |
| Sem dado pessoal em resposta/log/erro (blocos 6, 7) | Projeção fixa de 6 campos; mensagem de erro genérica; nada de PII em log |
| Apólice sem endosso -> lista vazia + sucesso (bloco 4 CA-03) | 200 com `[]` |
| Apólice inexistente -> 404 (bloco 4 CA-04) | 404 "Apólice não encontrada." |
| Acesso de atendente sem segregação (bloco 6) | Dependência de autenticação simples na demo, sem filtro por carteira |
| Não alterar cálculo de prêmio nem endosso INS-014 (bloco 8) | Nenhuma rota/func de escrita ou cálculo; só leitura da trilha |

## 8. Riscos e mitigações

- Vazamento de dado pessoal da trilha: mitigado pela projeção explícita de seis campos no domínio; o item de saída nunca carrega o registro bruto.
- Mensagem de 404 revelar existência: usa-se a mesma mensagem genérica "Apólice não encontrada." para formato inválido e para inexistente, evitando enumeração.
- Imprecisão monetária: uso de `Decimal` e serialização como string com duas casas; proibido `float`.
- Ordenação instável em empate: a chave inclui `endorsement_id`, tornando a ordem determinística mesmo com datas iguais (CA-06).
- Fuso da data: exigir `datetime` tz-aware em UTC na massa e na serialização, para o sufixo `Z` ser sempre correto.

## 9. Escopo de teste

Testes `pytest` com massa sintética cobrindo CA-01 a CA-06 (detalhado em `tasks.md`), com cada teste citando `INS-016 CA-NN`. Cobertura mínima do projeto: 80% (`03-stack-cliente`).

## Dúvidas para o FDE

- Nenhuma. A spec aprovada define formato da apólice, ordenação, desempate, formato de data, tratamento monetário e perfil de acesso; não foi preciso inventar requisito. A antiga dúvida sobre o formato da apólice está resolvida: mantém-se o hífen (`AP-0001`, regex `^AP-\d{4}$`), por ser o literal dos blocos 6 e 9 e coerente com a rota já existente da INS-014. A decisão de nomenclatura (rota e pastas em português seguindo a INS-014, campos do contrato de saída em inglês) está registrada na seção 2.
