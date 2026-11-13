# Revisão de dívida técnica · INS-018

Spec: INS-018 · Simulação de prêmio por aumento de cobertura
Faixa: critica
Branch: feat/ins-018
Base da comparação: `git diff main...HEAD`
Arquivos tocados no código: `src/endosso/regras.py`, `src/endosso/repositorio.py`, `src/endosso/api.py`
Testes: `tests/test_ins_018_simulacao.py`

## Veredito

Sem bloqueios. A implementação reusa a regra de prêmio da INS-014 sem duplicar fórmula, limite ou arredondamento, mantém domínio e HTTP separados, usa `decimal.Decimal` em todo o fluxo monetário e tem docstrings de uma linha. Abaixo, apenas dívidas menores e observações, nenhuma delas impeditiva.

## Itens avaliados (checklist da tarefa)

### Reuso correto da regra de prêmio: OK
- `simular_premio` (`src/endosso/regras.py:48`) delega inteiramente a `recalcular_premio`. Não há cópia da fórmula proporcional (`premio * nova / atual`), do limite de 2x (`LIMITE_MULTIPLICADOR`) nem do arredondamento (`quantize(CENTAVOS, ROUND_HALF_UP)`). A simulação herda fórmula, validação de limite e HALF_UP de uma única fonte.
- Consequência positiva: a fórmula, o limite e o arredondamento continuam com um só dono (INS-014). Não há risco de divergência futura entre simulação e endosso efetivo.

### Separação domínio / HTTP: OK
- Cálculo em `regras.py` (puro, sem FastAPI). HTTP em `api.py` traduz exceções de domínio (`ApoliceInativa` -> 409, `CoberturaInvalida` -> 422) sem reimplementar regra. Persistência/auditoria em `repositorio.py`. A camada de regra não importa nada de HTTP.

### Uso de `decimal.Decimal`, OK
- Nenhum `float` no caminho monetário. `SimulacaoPedido.cobertura_pedida` e os campos de `SimulacaoResposta` são `Decimal`; o registro de auditoria serializa via `str(...quantize(CENTAVOS))`.

### Docstrings de uma linha: OK
- Todas as funções e classes novas (`simular_premio`, `SimulacaoPedido`, `SimulacaoResposta`, `simular_aumento_cobertura`, `registrar_simulacao`) têm docstring de uma linha. Conforme a convenção da stack.

### Clareza do registro de auditoria: OK, com ressalva menor
- `registrar_simulacao` grava exatamente os campos pedidos pelo CA-07 (apólice, cobertura atual, cobertura pedida, prêmio simulado, solicitante, data/hora), sem dado pessoal. O teste `test_ins_018_ca_07` trava o conjunto de campos.

## Dívidas técnicas apontadas

### 1. Duplicação de validação de formato de apólice (acoplamento fraco entre endpoints): esforço P
- Arquivo/linha: `src/endosso/api.py:89-90` (simulação) repete o padrão de `src/endosso/api.py:152` (histórico INS-016): `if not FORMATO_APOLICE.match(numero): raise HTTPException(404, "Apólice não encontrada.")`.
- Nota: o endpoint de endosso efetivo (`aumentar_cobertura`) NÃO faz essa checagem de formato, só `repo.buscar`. Há três endpoints com três tratamentos ligeiramente diferentes de "apólice não encontrada". É duplicação pequena e inconsistência de guarda, não erro. Extrair um helper (ex.: `_exigir_apolice(numero) -> Apolice`) uniformizaria. Esforço P.

### 2. Constante `CENTAVOS` definida em dois módulos: esforço P
- Arquivo/linha: `src/endosso/api.py:24` (`CENTAVOS = Decimal("0.01")`) duplica a constante já exportada por `src/endosso/regras.py:10`. O `repositorio.py` já importa `CENTAVOS` de `regras`; `api.py` redefine a sua. Risco baixo (mesmo valor), mas é duplicação de uma constante de domínio monetário que deveria ter dono único em `regras.py`. Esforço P.

### 3. `simular_premio` como wrapper de uma linha: dívida aceitável, esforço P (não recomendado mexer)
- Arquivo/linha: `src/endosso/regras.py:48-50`. A função apenas chama `recalcular_premio`. É uma indireção sem lógica própria. Porém o nome documenta a intenção de reuso (CA-01/CA-02) e dá um ponto de extensão caso a simulação ganhe regra própria no futuro. Mantê-la é defensável; registro apenas como observação. Não corrigir agora.

### 4. Serialização de valores monetários duplicada entre endpoints: esforço M
- Arquivo/linha: `src/endosso/repositorio.py:92-96` (`registrar_simulacao` serializa via `str(...quantize(CENTAVOS))`) e `src/endosso/api.py:124-126` (`_serializar_valor` do INS-016, mesma ideia). Lógicas de serialização monetária para string de duas casas vivem em módulos diferentes com implementações próprias. Convergir numa função única (em `regras.py` ou um módulo de serialização) reduziria o risco de formatos divergentes. Esforço M.

## Itens procurados e NÃO encontrados (sem dívida)

- Função longa demais: não há. O maior corpo novo é `simular_aumento_cobertura`, com guarda + try/except + retorno; dentro de limite razoável.
- Uso de `float` para dinheiro: nenhum.
- Acoplamento regra de negócio <-> HTTP: não há; a regra é pura.
- TODO sem dono: nenhum (busca por TODO/FIXME/XXX/HACK em `src/endosso/*.py` sem resultados).

## Resumo dos esforços

| Item | Tipo | Esforço |
|---|---|---|
| 1. Guarda de formato de apólice duplicada/inconsistente | Duplicação + acoplamento fraco | P |
| 2. `CENTAVOS` redefinida em `api.py` | Duplicação de constante | P |
| 3. `simular_premio` wrapper de uma linha | Indireção (aceitável) | P |
| 4. Serialização monetária duplicada entre endpoints | Duplicação | M |

Nenhum item bloqueia o merge. São melhorias de manutenção de baixo a médio esforço, a serem agendadas a critério do FDE.
