# INS-018 · Design · Simulação de prêmio por aumento de cobertura

Derivado de `requirements.md` (versão 1, status aprovada, faixa critica, dev_revisor Dev Revisor Exemplo). Operação de consulta: a simulação calcula o prêmio novo e grava um registro na trilha de auditoria, mas NÃO altera cobertura, prêmio nem cria endosso (blocos 3, 8 e 10 da spec). Reaproveita a regra de prêmio proporcional já existente (INS-014) em vez de criar outra.

## 1. Visão geral

A solução expõe um endpoint de leitura que simula o aumento de cobertura de uma apólice e devolve o prêmio novo proporcional, sem mutar a apólice. Segue a convenção do projeto (`03-stack-cliente`): regra de negócio pura e separada da camada HTTP, valores monetários em `decimal.Decimal` (nunca `float`), arredondamento HALF_UP em centavos, docstring de uma linha em funções públicas. A rota e a estrutura de pastas acompanham o padrão já existente no repositório (`src/endosso/`, INS-014/INS-016), em português; os identificadores de contrato e a trilha de auditoria seguem o mesmo estilo já presente.

Na demo os dados vivem em memória: o repositório de apólices e a trilha de auditoria já existentes (`src/endosso/repositorio.py`), com massa sintética (AP-0001, AP-0002 inativa, AP-0003). A simulação acrescenta um tipo de registro de auditoria sem dado pessoal, distinto do registro de endosso efetivo.

## 2. Reuso da regra de prêmio (decisão central)

A regra de prêmio proporcional já existe em `src/endosso/regras.py`:

- `recalcular_premio(apolice, nova_cobertura)`: valida apólice ativa (`ApoliceInativa`), valida a nova cobertura (`validar_nova_cobertura`) e calcula `premio * nova_cobertura / cobertura` com `quantize(CENTAVOS, ROUND_HALF_UP)`.
- `validar_nova_cobertura(atual, nova)`: rejeita `nova <= atual` (`CoberturaInvalida`) e rejeita `nova > atual * 2` (`CoberturaInvalida`), aceitando exatamente 2x.

A simulação REUTILIZA `recalcular_premio` sem modificá-la (bloco 8: o agente não altera a fórmula, o limite de 2x nem o arredondamento). Isso garante, de graça:

- CA-01/CA-02: prêmio proporcional com HALF_UP em centavos, idêntico ao aumento real.
- CA-03: apólice inativa levanta `ApoliceInativa` -> HTTP 409.
- CA-04: cobertura acima de 2x levanta `CoberturaInvalida` -> HTTP 422; exatamente 2x é aceito.

A camada de simulação (nova função pura `simular_premio`) é um fino invólucro sobre `recalcular_premio` que NÃO toca o repositório de apólices, deixando explícito que a simulação é só consulta (CA-06). Ver a seção 7 sobre o tratamento do caso "nova cobertura menor ou igual" (`CoberturaInvalida`).

## 3. Arquitetura

Três camadas, com dependências apontando sempre para o domínio:

| Camada | Responsabilidade | Pasta/arquivo |
|---|---|---|
| Domínio (pura) | Reuso de `recalcular_premio`; nova função pura `simular_premio(apolice, cobertura_pedida)` que calcula o prêmio simulado sem mutar nada; estrutura imutável do resultado da simulação | `src/endosso/regras.py` |
| Repositórios em memória | Ler a apólice (`buscar`); registrar o evento de auditoria da simulação sem alterar a apólice (novo método `registrar_simulacao`) e sem dado pessoal | `src/endosso/repositorio.py` |
| HTTP (FastAPI) | Validar formato do número da apólice; chamar o domínio; mapear erros para 404/409/422; gravar a auditoria; serializar a resposta 200 | `src/endosso/api.py` |

A camada de domínio não importa FastAPI nem conhece HTTP. A camada HTTP não contém a fórmula do prêmio nem o cálculo de limite: apenas orquestra e traduz para status/JSON. A gravação da trilha de auditoria é efeito colateral de infraestrutura (repositório), separada da função pura de cálculo.

### Fluxo da requisição

1. Chegada em `POST /apolices/{numero}/simulacoes/aumento-cobertura` com a cobertura pedida no corpo e o identificador técnico de quem pede no cabeçalho (ex.: `BRK-001`).
2. A camada HTTP valida o formato `AP-` + 4 dígitos (regex `^AP-\d{4}$`, já existente). Fora do formato ou apólice inexistente -> 404 "Apólice não encontrada." (CA-05; mesma mensagem genérica, sem dado pessoal).
3. O domínio calcula o prêmio simulado via `simular_premio`, que reutiliza `recalcular_premio`:
   - apólice inativa -> `ApoliceInativa` -> HTTP 409 (CA-03), sem gravar auditoria de sucesso e sem mutar a apólice;
   - cobertura acima de 2x -> `CoberturaInvalida` -> HTTP 422 (CA-04), idem.
4. Sucesso: a camada HTTP pede ao repositório para registrar o evento de auditoria da simulação (CA-07) e devolve 200 com o prêmio simulado.
5. Em nenhum caminho (sucesso ou erro) a apólice é alterada e nenhum endosso é criado (CA-06).

## 4. Contrato do endpoint

- Método e rota: `POST /apolices/{numero}/simulacoes/aumento-cobertura`. Usa POST porque recebe um corpo com a cobertura pedida e gera um registro de auditoria; a semântica é de consulta (não altera a apólice), mas o verbo acompanha o padrão da rota de endosso existente e o fato de haver um corpo e uma escrita de auditoria. A rota em `/simulacoes/` deixa explícito que é simulação, nunca endosso.
- Parâmetro de caminho: `numero`, formato `AP-` + 4 dígitos (regex `^AP-\d{4}$`).
- Corpo (`SimulacaoPedido`): `cobertura_pedida: Decimal` (`gt=0`, `max_digits=12`, `decimal_places=2`), espelhando o `PedidoAumento` da INS-014.
- Cabeçalho: identificador técnico de quem pede, ex.: `X-Corretor: BRK-001` (valor padrão de demo; nunca dado pessoal).
- Respostas:

| Situação | Status | Corpo |
|---|---|---|
| Apólice ativa, cobertura válida (<= 2x, > atual) | 200 | resultado da simulação (ver abaixo) |
| Apólice inativa | 409 | `{"detail": "Apólice <n> não está ativa."}` sem dado pessoal (CA-03) |
| Cobertura acima de 2x a atual | 422 | `{"detail": "A nova cobertura não pode passar de 2 vezes a cobertura atual."}` (CA-04) |
| Apólice inexistente ou formato inválido | 404 | `{"detail": "Apólice não encontrada."}` sem dado pessoal (CA-05) |

Corpo de sucesso (`SimulacaoResposta`), espelhando o estilo da INS-014, deixando claro que é simulação:

```json
{"apolice": "AP-0001", "cobertura_atual": "100000.00", "cobertura_pedida": "150000.00", "premio_atual": "1200.00", "premio_simulado": "1800.00"}
```

Valores monetários serializados como string de duas casas, preservando `Decimal`.

## 5. Função pura de cálculo (`simular_premio`)

Em `src/endosso/regras.py`, nova função pura:

- Assinatura: `simular_premio(apolice: Apolice, cobertura_pedida: Decimal) -> Decimal`.
- Corpo: delega a `recalcular_premio(apolice, cobertura_pedida)`, mesma fórmula, mesmo limite de 2x, mesmo HALF_UP em centavos. Não altera o objeto `Apolice` (a dataclass é `frozen=True`) e não toca o repositório.
- Docstring de uma linha citando INS-018 e o reuso da regra da INS-014.
- Opcionalmente um resultado imutável (`dataclass(frozen=True)` `SimulacaoResultado` com `cobertura_atual`, `cobertura_pedida`, `premio_atual`, `premio_simulado`) para a camada HTTP serializar sem recalcular. A decisão de usar struct ou tupla fica para a implementação; o contrato de saída da seção 4 é o que importa.

Reuso é explícito: NÃO se reescreve a fórmula de proporção, o limite de 2x nem o arredondamento (bloco 8). Qualquer mudança nessas regras exigiria aprovação humana e não faz parte desta spec.

## 6. Trilha de auditoria da simulação (sem dado pessoal)

A simulação é só consulta sobre a apólice, mas grava um registro na trilha de auditoria (blocos 6, 7 e CA-07). Esse registro é DISTINTO do registro de endosso efetivo (INS-014) e não altera a apólice.

- Novo método no repositório: `registrar_simulacao(apolice, cobertura_pedida, premio_simulado, solicitante)`.
- O método NÃO chama `aplicar_endosso`, NÃO faz `replace` na apólice e NÃO cria endosso; apenas acrescenta um dicionário a uma lista de auditoria (reaproveitando `self.auditoria` ou uma lista dedicada `self.simulacoes`; a implementação escolhe, desde que não misture com o endosso efetivo).
- Campos do registro (exatamente os do CA-07, todos sem dado pessoal):

| Campo | Conteúdo | Observação |
|---|---|---|
| `apolice` | número da apólice, ex.: `AP-0001` | identificador fictício, sem PII |
| `cobertura_atual` | cobertura atual, string de 2 casas | valor anterior (lente financeira) |
| `cobertura_pedida` | cobertura simulada, string de 2 casas | valor pedido |
| `premio_simulado` | prêmio calculado, string de 2 casas | valor novo (lente financeira) |
| `solicitante` | identificador técnico/corretor, ex.: `BRK-001` | nunca nome, CPF, e-mail ou telefone |
| `quando` | data/hora em ISO-8601 UTC | carimbo do momento |

- O registro é gravado apenas na simulação bem-sucedida (200). Em 404/409/422 nada é gravado como sucesso (coerente com "após uma simulação bem-sucedida" no CA-07).
- Nenhum campo pessoal entra no registro: a projeção é fixa nos seis campos acima. Isso atende aos blocos 6 e 7 e à lente de serviços financeiros (quem pediu, quando, valor anterior, valor novo), sem tratar dado pessoal.

## 7. Tratamento do caso "cobertura menor ou igual à atual"

`recalcular_premio` reutilizado levanta `CoberturaInvalida` quando `cobertura_pedida <= cobertura_atual`. A spec da INS-018 só define explicitamente o limite superior (2x -> 422), os casos de sucesso (aumento) e os três erros (409/404/422 para o limite superior). Para não inventar requisito e para reusar a regra sem alterá-la:

- O design mantém o comportamento herdado da INS-014: cobertura pedida menor ou igual à atual é recusada como cobertura inválida -> HTTP 422, mesma família de erro do limite. Isso é coerente com "aumento de cobertura" (o caso de uso é aumentar) e não contraria nenhum CA.
- Esse comportamento está listado em "Dúvidas para o FDE" para confirmação explícita, já que a spec não cita o limite inferior. Nenhum CA quebra com essa escolha; é só uma confirmação de borda.

## 8. Como cada decisão da spec se reflete no design (mapa CA -> parte do design)

| CA | O que exige | Onde o design atende |
|---|---|---|
| CA-01 | AP-0001 100.000 -> 150.000 = prêmio 1.800,00 (200) | `simular_premio` reusa `recalcular_premio` (seção 2, 5); endpoint 200 (seção 4). `1200 * 150000 / 100000 = 1800.00` |
| CA-02 | AP-0003 33.333 -> 50.000 = prêmio 1.166,67 (200) | mesma função + HALF_UP em centavos (seção 5). `777,77 * 50000 / 33333 = 1166,67` por HALF_UP |
| CA-03 | apólice inativa -> 409, nada muda | `ApoliceInativa` -> 409 (seção 3, 4); simulação não muta apólice (seção 2, 6) |
| CA-04 | cobertura > 2x -> 422; exatamente 2x aceito | `CoberturaInvalida` do limite -> 422 (seção 3, 4); `validar_nova_cobertura` aceita 2x exato |
| CA-05 | apólice inexistente -> 404 | validação de formato + `buscar` None -> 404 genérico (seção 3, 4) |
| CA-06 | sucesso ou erro: apólice intacta, sem endosso | função pura não toca repositório; auditoria não chama `aplicar_endosso`/`replace` (seções 2, 6) |
| CA-07 | registro de auditoria com 6 campos, sem dado pessoal | `registrar_simulacao` grava os seis campos fixos sem PII (seção 6) |

## 9. Riscos e mitigações

- Simulação acidentalmente mutar a apólice: mitigado por `Apolice` ser `frozen=True`, por `simular_premio` não receber nem chamar o repositório, e por `registrar_simulacao` nunca chamar `aplicar_endosso`/`replace`. Teste de não mutação cobre CA-06.
- Divergir da regra de prêmio da INS-014: mitigado reusando `recalcular_premio` diretamente, sem copiar a fórmula. Mudança de fórmula/limite/arredondamento é proibida sem aprovação humana (bloco 8).
- Vazamento de dado pessoal na auditoria, log ou erro: mitigado pela projeção fixa de seis campos sem PII e por mensagens de erro genéricas (sem nome, CPF, e-mail, telefone). Teste verifica a ausência de dado pessoal (CA-07).
- Imprecisão monetária: uso de `Decimal` e HALF_UP em centavos herdados da regra; serialização como string de duas casas. Proibido `float`.
- Confusão entre registro de simulação e de endosso: mitigada por método dedicado `registrar_simulacao` e, se preciso, lista de auditoria separada, nunca reaproveitando `aplicar_endosso`.
- Semântica do verbo HTTP: POST com corpo e escrita de auditoria pode sugerir mutação; mitigado pela rota `/simulacoes/` e por testes de não mutação da apólice.

## 10. Escopo de teste

Testes `pytest` com massa sintética cobrindo CA-01 a CA-07 (detalhado em `tasks.md`), cada teste citando `INS-018 CA-NN` no nome ou docstring (regra de rastreio, `scripts/rastrear_aceite.py`). Cobertura mínima do projeto: 80% (`03-stack-cliente`). Testes puros de domínio para o cálculo e HALF_UP; testes de endpoint com `TestClient` para status, não mutação e registro de auditoria sem dado pessoal. Análise estática (Semgrep CE) e `pip-audit` conforme a stack.

## Dúvidas para o FDE

- Borda não citada na spec: cobertura pedida MENOR OU IGUAL à atual. O design adota o comportamento herdado da INS-014 (recusa como cobertura inválida -> 422), por ser "aumento de cobertura" e por reusar a regra sem alterá-la. Confirmar se o FDE concorda em responder 422 nesse caso (nenhum CA depende disso; é só confirmação de borda).
- Verbo HTTP da rota de simulação: o design propõe `POST /apolices/{numero}/simulacoes/aumento-cobertura` (há corpo com a cobertura pedida e escrita de auditoria). Se o FDE preferir expor como `POST` mesmo sendo consulta, está atendido; não há requisito de idempotência na spec. Confirmar a rota.
- Identificador de quem pede: o design usa um cabeçalho (ex.: `X-Corretor: BRK-001`) com valor padrão de demo. Confirmar o nome do cabeçalho; o conteúdo é sempre identificador técnico, nunca dado pessoal.
