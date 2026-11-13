# Revisão de documentação · INS-018 · Simulação de prêmio por aumento de cobertura

- Spec: `.kiro/specs/ins-018-simulacao-aumento-cobertura/` (id INS-018, versão 1, faixa critica, dev_revisor Dev Revisor Exemplo, status aprovada).
- Branch: `feat/ins-018`.
- Escopo desta revisão: documentação (docstrings de funções públicas, coerência entre código e `design.md`, e o que falta no README para operar a mudança). Não edito código, teste nem spec; escrevo só em `reviews/`.
- Artefatos lidos: `src/endosso/regras.py`, `src/endosso/repositorio.py`, `src/endosso/api.py`, `tests/test_ins_018_simulacao.py`, `requirements.md`, `design.md`, `tasks.md`, `README.md`, `scripts/rastrear_aceite.py`, steering `03-stack-cliente` e lente de serviços financeiros.

## Conclusão

**Sem bloqueio de documentação.** A implementação está coerente com o design e com a spec nos pontos que importam: endpoint, mapeamento de erros (404/409/422), campos da trilha de auditoria, arredondamento HALF_UP em centavos e valor simulado sem validade. Todas as funções públicas novas têm docstring de uma linha citando os CA, e todos os sete critérios têm teste rastreável por `INS-018 CA-NN`.

Há **quatro apontamentos não bloqueantes**: (1) a docstring de cabeçalho de `api.py` cita só INS-014, embora o módulo já contenha INS-016 e agora INS-018; (2) a docstring de `simular_premio` cita apenas CA-01 e CA-02, mas a função também é o ponto que herda as validações de CA-03 e CA-04; (3) a resolução das três "Dúvidas para o FDE" do design não está registrada em nenhum artefato, apesar de o código já ter decidido todas; (4) o README não documenta a nova rota de simulação (mesma lacuna já apontada na INS-016).

## 1. Funções públicas sem docstring

Nenhuma função pública nova da INS-018 ficou sem docstring. Todas têm docstring de uma linha, conforme `03-stack-cliente`. Levantamento:

| Arquivo | Símbolo público novo (INS-018) | Docstring de 1 linha | CA citado na docstring |
|---|---|---|---|
| `regras.py` | `simular_premio` | sim | CA-01, CA-02 |
| `repositorio.py` | `registrar_simulacao` | sim | CA-06, CA-07 |
| `api.py` | `SimulacaoPedido` (modelo) | sim | (modelo Pydantic) |
| `api.py` | `SimulacaoResposta` (modelo) | sim | INS-018 (sem CA) |
| `api.py` | `simular_aumento_cobertura` (rota) | sim | INS-018 (sem CA específico) |

Observações de detalhe (não bloqueantes):

- A rota `simular_aumento_cobertura` tem docstring correta ("Simula o prêmio ... sem alterar a apólice e registra auditoria sem dado pessoal (INS-018)"), mas cita só a spec, sem os CA. É aceitável: a docstring descreve o comportamento com precisão e o rastreio por CA fica nos testes. Os demais handlers do módulo (`aumentar_cobertura`, `historico_endossos`) citam CA na docstring; por consistência, valeria citar CA-05/CA-07 aqui, mas não é exigido pela convenção.
- Os modelos Pydantic `SimulacaoPedido` e `SimulacaoResposta` têm docstring de uma linha. Conformes.

## 2. Docstrings: corretude e citação dos CA

As docstrings descrevem o comportamento real. Pontos verificados:

- `simular_premio` (regras.py): docstring "Simula o prêmio novo reusando a regra de prêmio da INS-014, sem alterar a apólice (INS-018 CA-01, CA-02)". O corpo delega a `recalcular_premio(apolice, cobertura_pedida)` e não muta a apólice (`Apolice` é `frozen=True`, e a função não toca o repositório). Correto quanto ao reuso e à não mutação.
  - **Apontamento não bloqueante:** a docstring cita apenas CA-01 e CA-02 (cálculo e HALF_UP), mas é exatamente esta função que, ao delegar a `recalcular_premio`, herda e propaga as validações de **CA-03** (`ApoliceInativa`) e **CA-04** (`CoberturaInvalida`, limite de 2x). O design (seções 2 e 5) e o `tasks.md` (task 1) atribuem CA-01 a CA-04 a essa função. A docstring subdocumenta o alcance real. Recomendo citar CA-01 a CA-04 para alinhar com design e tasks, mas a lógica está correta.
- `registrar_simulacao` (repositorio.py): docstring "Registra a trilha de auditoria da simulação sem alterar a apólice e sem dado pessoal (INS-018 CA-06, CA-07)". O corpo só faz `self.simulacoes.append({...})` com os seis campos previstos; não chama `aplicar_endosso` nem `replace`, não altera `self.apolices`. Correto e coerente com o design (seção 6) e a spec (bloco 8).

Nenhuma docstring foi encontrada descrevendo comportamento diferente do código.

## 3. Coerência entre design.md e implementação

A implementação segue o design com fidelidade alta. Conferência item a item:

| Item | design.md | Implementação (`api.py`/`regras.py`/`repositorio.py`) | Coerência |
|---|---|---|---|
| Rota | `POST /apolices/{numero}/simulacoes/aumento-cobertura` | `@app.post("/apolices/{numero}/simulacoes/aumento-cobertura")` | coerente |
| Corpo do pedido | `cobertura_pedida: Decimal` (`gt=0`, `max_digits=12`, `decimal_places=2`) | `SimulacaoPedido.cobertura_pedida: Decimal = Field(gt=0, max_digits=12, decimal_places=2)` | coerente |
| Cabeçalho de quem pede | `X-Corretor: BRK-001` (padrão de demo) | `x_corretor: str = Header(default="BRK-001")` | coerente |
| Validação de formato | regex `^AP-\d{4}$`; fora do formato ou inexistente -> 404 genérico | `FORMATO_APOLICE.match(numero)` -> 404 "Apólice não encontrada."; `buscar` None -> 404 | coerente |
| Apólice inativa | `ApoliceInativa` -> 409 | `except ApoliceInativa -> 409` | coerente (CA-03) |
| Cobertura acima de 2x | `CoberturaInvalida` -> 422 | `except CoberturaInvalida -> 422` | coerente (CA-04) |
| Reuso da regra | `simular_premio` delega a `recalcular_premio` sem reescrever fórmula/limite/arredondamento | `simular_premio` retorna `recalcular_premio(apolice, cobertura_pedida)` | coerente (bloco 8) |
| Arredondamento | HALF_UP em centavos, herdado da INS-014 | `recalcular_premio` usa `quantize(CENTAVOS, rounding=ROUND_HALF_UP)` | coerente |
| Campos da auditoria | 6 campos: `apolice`, `cobertura_atual`, `cobertura_pedida`, `premio_simulado`, `solicitante`, `quando` (ISO-8601 UTC) | `registrar_simulacao` grava exatamente esses 6 campos; `quando = datetime.now(timezone.utc).isoformat()` | coerente (CA-07) |
| Auditoria distinta do endosso | lista dedicada, nunca reaproveitar `aplicar_endosso` | grava em `self.simulacoes` (lista própria); endosso usa `self.auditoria` | coerente |
| Auditoria só no sucesso | registra apenas em 200 | `registrar_simulacao` chamado após o `try`, antes do `return 200` | coerente |
| Resposta de sucesso | `apolice`, `cobertura_atual`, `cobertura_pedida`, `premio_atual`, `premio_simulado` | `SimulacaoResposta` com esses cinco campos | coerente |
| Não mutação | função pura não toca repositório; auditoria não muta apólice | `simular_premio` não recebe repo; `registrar_simulacao` não altera `self.apolices` | coerente (CA-06) |
| Valor sem validade | número informativo, recalculado na hora, sem prazo | não há persistência de validade nem TTL; cálculo por requisição | coerente (sem campo de validade) |

Pontos de atenção de documentação (não bloqueantes):

- **Decisão de borda "cobertura <= atual" não registrada.** O design (seção 7 e "Dúvidas para o FDE") levanta que `recalcular_premio` recusa `cobertura_pedida <= cobertura_atual` como `CoberturaInvalida` -> 422, e pede confirmação do FDE. O código mantém esse comportamento herdado (via `validar_nova_cobertura`), e o teste de não mutação CA-06 inclusive exercita um caso de 422 por limite superior, mas **não há teste nem nota documentando a borda inferior** e a confirmação do FDE não está registrada em nenhum artefato. Nenhum CA depende disso; é só uma decisão de borda que ficou em aberto no design e foi silenciosamente resolvida no código.
- **"Dúvidas para o FDE" do design sem resolução escrita.** O design lista três dúvidas (borda inferior; verbo HTTP POST para consulta; nome do cabeçalho `X-Corretor`). O código decidiu todas (422 na borda, POST, `x-corretor` com default `BRK-001`), mas o design continua marcando-as como dúvidas em aberto. Como a faixa é `critica` e há um dev_revisor, recomendo que a resolução dessas três dúvidas fique registrada (no design ou na conversa do portão) para rastreabilidade: não trava a lógica, mas deixa o design "em aberto" enquanto o código já fechou.
- **Cabeçalho de módulo desatualizado em `api.py` e `regras.py`.** A docstring de topo de `api.py` diz "Camada HTTP do endosso de aumento de cobertura (INS-014)." e a de `regras.py` diz "Regras de negócio puras do endosso (INS-014 e INS-016)." Ambos os módulos agora contêm também INS-018 (rota de simulação, `simular_premio`). O cabeçalho de `repositorio.py` igualmente cita só INS-014/INS-016, embora tenha `registrar_simulacao`. É débito de documentação de superfície, idêntico ao já apontado na revisão da INS-016; não afeta o comportamento.

Não encontrei divergência de regra entre design e código. Diferente da INS-016, aqui o design já foi escrito em português e com a rota/pasta reais (`/apolices`, `src/endosso`), então não há a divergência de nomenclatura que existia lá.

## 4. Rastreio dos CA (conferência de documentação do rastreio)

`scripts/rastrear_aceite.py` aceita `INS-018 CA-NN` na docstring ou `ins_018_ca_nn` no nome do teste. Conferência em `tests/test_ins_018_simulacao.py`:

| CA | Teste(s) que citam o CA | Rastreável |
|---|---|---|
| CA-01 | `test_ins_018_ca_01_premio_proporcional`, `test_ins_018_ca_01_endpoint_200` | sim |
| CA-02 | `test_ins_018_ca_02_half_up_centavos`, `test_ins_018_ca_02_endpoint_200` | sim |
| CA-03 | `test_ins_018_ca_03_regra_pura_inativa`, `test_ins_018_ca_03_inativa_409` | sim |
| CA-04 | `test_ins_018_ca_04_limite_2x`, `test_ins_018_ca_04_acima_2x_422` | sim |
| CA-05 | `test_ins_018_ca_05_inexistente_404` | sim |
| CA-06 | `test_ins_018_ca_06_apolice_intacta` (parametrizado: sucesso, 409, 422, 404) | sim |
| CA-07 | `test_ins_018_ca_07_auditoria_sem_dado_pessoal` | sim |

Os sete CA têm ao menos um teste com citação válida, tanto no nome quanto na docstring. O rastreio de documentação está completo. Observação de detalhe: o nome da função `test_ins_018_ca_03_regra_pura_inativa` não cita a letra do CA no nome com hífen (usa `ca_03`), que é a forma que o script normaliza e aceita: está correto.

## 5. O que falta no README para operar a mudança

O `README.md` é o do harness (fluxo de squad e comandos `ash.py`) e **não documenta a aplicação de demo**: nem a rota da INS-014, nem a consulta da INS-016, nem agora a simulação da INS-018. Para outra pessoa operar a simulação só com o README, hoje faltam:

- A existência da rota `POST /apolices/{numero}/simulacoes/aumento-cobertura` e o que ela faz (simula o prêmio sem alterar a apólice; grava auditoria sem dado pessoal).
- O corpo do pedido (`cobertura_pedida`, duas casas) e o cabeçalho `x-corretor` (identificador técnico, padrão `BRK-001`).
- O contrato de resposta 200 (`apolice`, `cobertura_atual`, `cobertura_pedida`, `premio_atual`, `premio_simulado`, valores como string de duas casas) e os códigos de erro (409 inativa, 422 acima de 2x/cobertura inválida, 404 inexistente/formato inválido).
- A massa sintética para teste manual (AP-0001 ativa 100.000/1.200; AP-0002 inativa; AP-0003 ativa 33.333/777,77; AP-9999 inexistente) e como subir a API localmente (uvicorn está no `.venv-tools`, mas o README não cita o app FastAPI).

Ressalva (igual à da INS-016): pode ser decisão consciente não documentar a app de demo no README do harness. Se for, convém registrar essa decisão uma vez. Caso contrário, a lacuna acima impede operar a mudança só pelo README.

## Resumo para o portão

- Funções públicas sem docstring: **nenhuma**. Todas as novas (`simular_premio`, `registrar_simulacao`, `SimulacaoPedido`, `SimulacaoResposta`, `simular_aumento_cobertura`) têm docstring de uma linha. **OK.**
- Coerência design x código (endpoint, erros 404/409/422, campos da auditoria, HALF_UP, valor sem validade): **coerente em todos os itens.** **OK.**
- Rastreio dos CA: **CA-01 a CA-07 cobertos** e citáveis por `INS-018 CA-NN`. **OK.**
- Apontamentos não bloqueantes: docstring de `simular_premio` subdocumenta CA-03/CA-04; cabeçalhos de módulo (`api.py`, `regras.py`, `repositorio.py`) ainda citam só INS-014/INS-016; as três "Dúvidas para o FDE" do design (borda `<=` atual, verbo POST, cabeçalho) foram decididas no código mas não têm resolução escrita no design: relevante por ser faixa crítica; README não cobre a rota de simulação.
- **Veredito: sem bloqueio de documentação.** Apontamentos a tratar a critério do FDE/dev revisor antes do merge.
