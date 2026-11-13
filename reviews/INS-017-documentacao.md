# Revisão de documentação · INS-017 · Resumo da apólice

- Spec: `.kiro/specs/ins-017-resumo-apolice/` (id INS-017, versão 2, faixa semiautonoma, status aprovada).
- Branch: `feat/ins-017`.
- Escopo: docstrings de funções públicas, coerência entre `requirements.md` v2, `design.md`, `tasks.md` e o código, e o que falta no README para operar a mudança. Não edito código, teste, spec nem README; escrevo só em `reviews/`.
- Artefatos lidos: `requirements.md`, `design.md`, `tasks.md`, `src/endosso/resumo.py`, `src/endosso/api.py`, `src/endosso/repositorio.py`, `src/endosso/regras.py`, nomes e docstrings de `tests/test_ins_017_resumo.py`, `README.md`.
- Não verificado: não rodei testes nem o CI (fora do meu papel). A conferência é por leitura.

## Conclusão

**Sem bloqueio de documentação.** Código, design e spec batem nos pontos centrais: status `aprovada` e versão 2, rota, ordem do fluxo (formato, auditoria, busca, projeção), mensagens e status HTTP, campos da auditoria e valor padrão `canal-app`. Há **quatro apontamentos não bloqueantes**: (1) `NumeroInvalido` está no design e na T-01 mas não é usada; (2) o código trata também `InvalidOperation` como `ValorInvalido`, o que o design não descreve; (3) cabeçalhos de módulo desatualizados; (4) README ainda diz que a INS-017 não está implementada e não documenta a rota.

## 1. Funções públicas sem docstring

Nenhuma. Levantamento dos símbolos da INS-017:

| Arquivo | Símbolo | Docstring de 1 linha |
|---|---|---|
| `resumo.py` | `NumeroInvalido`, `ValorInvalido` | sim |
| `resumo.py` | `numero_valido`, `montar_resumo` (e o privado `_checar_duas_casas`) | sim |
| `repositorio.py` | `registrar_consulta_resumo` | sim (cita CA-08) |
| `api.py` | `ResumoApoliceResposta` | sim (cita CA-06) |
| `api.py` | `resumo_apolice` (rota) | sim (cita CA-01 a CA-08) |

Observação: `numero_valido` e `montar_resumo` não citam CA na docstring. A convenção só exige uma linha; o rastreio fica nos testes. Não bloqueia.

## 2. Divergências entre código e design.md / requirements.md / tasks.md

Conferido e **coerente**:

| Item | Documento | Código |
|---|---|---|
| Status e versão | design: "`requirements.md` v2, status `aprovada`" | front matter: `versao: 2`, `status: aprovada`, `faixa: semiautonoma` |
| Rota | `GET /apolices/{numero}/resumo` | idem |
| Formato inválido | 422 `Número de apólice inválido.`, sem auditoria, sem consultar a base | idem; auditoria e `buscar` só depois da validação |
| Inexistente | 404 `Apólice não encontrada.` | idem |
| Valor com mais de 2 casas | 500 genérico, exemplo `Erro interno.` | `HTTPException(500, "Erro interno.")` |
| Regex | `fullmatch`, não `$` sozinho | `_FORMATO.fullmatch` |
| Auditoria | `{apolice, usuario, quando}`, UTC, antes da busca | idem |
| Sem `X-Solicitante` | `canal-app` | `Header(default="canal-app")` |
| Resposta | 4 campos, `extra` proibido, cobertura e prêmio como string de 2 casas | `ConfigDict(extra="forbid")`, `str(Decimal)` após `quantize` |
| Rotas existentes | sem mudança | INS-014, INS-016 e INS-018 intactas |
| Testes | `tests/test_ins_017_resumo.py`, nomes da `tasks.md` | todos os nomes citados em T-01 a T-06 existem |

**Divergências (não bloqueantes):**

1. **`NumeroInvalido` sem uso.** O design (seção 2) lista a exceção como parte de `resumo.py` e a T-01 manda criá-la. Ela existe, mas nada a levanta nem a captura: a validação é `numero_valido` (bool) e a rota levanta `HTTPException` direto. Ou o design/tasks deixam de listá-la, ou ela é usada. Nenhum CA depende disso.
2. **`ValorInvalido` por `InvalidOperation`.** `_checar_duas_casas` também levanta `ValorInvalido("Valor inválido na base.")` quando `quantize` falha (valor com dígitos demais, por exemplo). O design (seção 3 passo 4, D2) e o bloco 8 só descrevem "mais de 2 casas". O resultado para o cliente é o mesmo 500 genérico, então é só lacuna de descrição. Esse ramo não tem teste citado em `tasks.md`.
3. **Auditoria também no 500.** Como a auditoria é gravada antes de `montar_resumo`, uma consulta que termina em 500 por `ValorInvalido` também deixa registro. O design diz "antes da busca" e CA-08 fala em consulta de formato válido, então é coerente, mas não está dito de forma explícita.
4. **Dois formatos de validação no mesmo módulo.** `api.py` mantém `FORMATO_APOLICE` (`^AP-\d{4}$` com `match`) para INS-016 e INS-018, e `resumo.numero_valido` (`fullmatch`) para INS-017. Não é erro: o design da INS-017 justifica o `fullmatch` e proíbe mexer nas outras rotas (bloco 10). Registro só para que ninguém "unifique" sem passar por spec.
5. **Teste fora da `tasks.md`.** `test_ins_017_ca_04_http_quebra_de_linha_e_422` não aparece na T-04. Cobre CA-04 e é bem-vindo; a lista da tarefa fica um item atrás.

**Docstrings de módulo e comentário desatualizados:**

- `api.py`: "Camada HTTP do endosso de aumento de cobertura (INS-014)." O módulo agora tem INS-014, 016, 017 e 018.
- `repositorio.py`: "(INS-014 CA-05, INS-016)." Já contém INS-017 (e INS-018).
- `regras.py`: "(INS-014 e INS-016)." Já contém `simular_premio` da INS-018. Não é da INS-017, só registro.

## 3. Rastreio dos CA

Todos os nove CA têm teste com `INS-017 CA-NN` na docstring e `ins_017_ca_NN` no nome: CA-01, 02, 03, 04, 05, 06, 07, 08 e 09. Conferido por leitura; a execução do rastreio é do `ci`.

## 4. O que falta no README para outra pessoa operar a mudança

1. **Texto desatualizado.** A seção "Exemplos incluídos" diz que a INS-017 "é uma story nova, ainda não implementada". Na `feat/ins-017` isso já não é verdade e, depois do merge, será falso para quem clonar. Também fala em "três rodadas"; passam a ser quatro.
2. **Rota não documentada.** O README do harness não descreve a app de exemplo (mesma lacuna das INS-016 e INS-018). Para operar a INS-017 faltam: `GET /apolices/{numero}/resumo`; cabeçalho opcional `X-Solicitante` (padrão `canal-app`); resposta 200 (`apolice`, `situacao`, `cobertura`, `premio`, valores como string de 2 casas); erros 422, 404 e 500 genérico, com as mensagens.
3. **Auditoria não é consultável.** Os registros ficam só em `repo.consultas_resumo`, em memória, e nenhuma rota os lê. Reiniciar a app apaga tudo. Quem opera precisa saber disso, e que a retenção de 6 meses (bloco 6) é só intenção: não há descarte nem persistência (bloco 8, D9).
4. **Pendências de homologação sem dono visível fora da spec.** Prazo e base legal do `X-Solicitante` a confirmar pelo cliente; p95 de CA-09 medido só em memória (sinal de regressão); ausência de controle de acesso à rota (decisão do PO, fora de escopo). Estão no `requirements.md` e no `design.md`, mas quem lê só o README não as vê.
5. **Massa sintética e como subir a API.** AP-0001, AP-0002 e AP-9999 para teste manual, e como subir o FastAPI localmente, não estão no README.

Ressalva igual à das revisões anteriores: pode ser decisão consciente não documentar a app de demo no README do harness. Nesse caso, basta corrigir o item 1 (frase desatualizada) e registrar a decisão uma vez.

## Resumo para o portão

| Pergunta | Resultado |
|---|---|
| Funções públicas sem docstring | Nenhuma |
| Design diz "status aprovada" e bate com a spec e o código | Sim (v2, `aprovada`, `semiautonoma`) |
| Mensagens e status HTTP batem com o código | Sim (422, 404, 500 genérico, `canal-app`) |
| Divergências código x design | 2 pequenas (`NumeroInvalido` sem uso; `InvalidOperation` não descrito), não bloqueantes |
| README suficiente para operar | Não: frase "ainda não implementada" desatualizada e rota não documentada |

**Veredito: sem bloqueio de documentação.** Tratar, a critério do FDE antes do merge: corrigir a frase do README (item 4.1), decidir sobre `NumeroInvalido` (usar ou retirar de design e tasks) e atualizar os cabeçalhos de módulo.
