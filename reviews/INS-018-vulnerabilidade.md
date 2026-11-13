# Revisão de vulnerabilidades e proteção de dado pessoal: INS-018

- Spec: INS-018 · Simulação de prêmio por aumento de cobertura
- Faixa: critica (cálculo de prêmio, lente de serviços financeiros)
- Branch: feat/ins-018
- Escopo revisado: `src/endosso/regras.py`, `src/endosso/repositorio.py`, `src/endosso/api.py`, `tests/test_ins_018_simulacao.py`
- Ferramentas: Semgrep CE (`--config .semgrep/ --metrics=off src/`) e pip-audit (`-r requirements.txt`)

## Veredito

Sem bloqueio. Nenhum achado de severidade alta. O código da simulação não trata dado pessoal, usa mensagens de erro genéricas, é só consulta (não altera apólice nem cria endosso) e a trilha de auditoria grava apenas identificadores técnicos e valores monetários.

## Resultado das ferramentas

| Ferramenta | Resultado |
|---|---|
| Semgrep CE (`.semgrep/`, 5 regras) | 5 arquivos escaneados, 0 achados (0 blocking). Os três arquivos da INS-018 estão rastreados pelo git na branch e entraram no escopo. |
| pip-audit (`requirements.txt`) | No known vulnerabilities found. |

O aviso do pip-audit sobre "environment location may have moved" é ruído de junction/redirect do diretório temporário do Windows, não um achado de segurança; a varredura concluiu e não reportou CVE.

## Achados

### A-01 · Cabeçalho `x-corretor` gravado na auditoria sem validação de formato
- Arquivo e linha: `src/endosso/api.py` (parâmetro `x_corretor: str = Header(default="BRK-001")` em `simular_aumento_cobertura`, ~linha 90) e `src/endosso/repositorio.py` (`registrar_simulacao`, campo `solicitante`, ~linha 92).
- Severidade: baixa.
- Risco: o valor do cabeçalho entra no registro de auditoria sem allowlist nem checagem de formato; um chamador poderia colocar texto arbitrário (inclusive dado pessoal) no campo `solicitante`. Na demo o efeito é contido: destino em memória, sem log, sem sink externo, sem PII na massa sintética.
- Recomendação: no ambiente real, validar o identificador técnico contra um padrão (ex.: `^BRK-\d{3}$`) ou obtê-lo do contexto autenticado em vez do cabeçalho livre, para garantir que nunca entre PII na trilha. Não corrigir nesta demo; registrar como hardening para a versão com autenticação (bloco 6 já marca "leitura autenticada no ambiente real" como fora do escopo).

## Verificações de proteção de dado pessoal e injeção (conformes)

- **Sem PII em resposta, log ou erro**: nenhum uso de `logging`, `print` ou escrita em stdout com dados. A resposta de sucesso (`SimulacaoResposta`) expõe só número de apólice fictício e valores monetários. Nenhum campo de CPF, nome, e-mail ou telefone em qualquer camada.
- **Mensagens de erro genéricas**: 404 "Apólice não encontrada." (mesma mensagem para formato inválido e inexistente, não revela existência); 409 e 422 citam apenas o identificador técnico da apólice e a regra de negócio. Sem dado pessoal. Atende blocos 6 e 7 e CA-05.
- **Só consulta (CA-06)**: `simular_premio` delega a `recalcular_premio` sem receber nem tocar o repositório; `registrar_simulacao` só faz `append` em `self.simulacoes` e nunca chama `aplicar_endosso` nem `replace`. A dataclass `Apolice` é `frozen=True`. Nenhum caminho (200/404/409/422) altera cobertura, prêmio ou cria endosso.
- **Trilha de auditoria sem dado pessoal (CA-07, lente financeira)**: projeção fixa de seis campos: `apolice`, `cobertura_atual` (valor anterior), `cobertura_pedida`, `premio_simulado` (valor novo), `solicitante` (identificador técnico BRK-001) e `quando` (ISO-8601 UTC). Cobre quem pediu, quando, valor anterior e valor novo, sem PII. Distinta da trilha de endosso efetivo (`self.auditoria`).
- **Validação de entrada / injeção**: path `numero` validado por regex `^AP-\d{4}$` antes de qualquer uso; `cobertura_pedida` validada por Pydantic (`Decimal`, `gt=0`, `max_digits=12`, `decimal_places=2`). Acesso a apólice é lookup em `dict` em memória: sem SQL, sem shell, sem `eval`/`exec`, sem concatenação em consulta. Sem superfície de injeção. Valores monetários em `decimal.Decimal` com HALF_UP em centavos, sem `float`.

## Observação de não bloqueio

A revisão é de segurança e proteção de dado pessoal; corretude funcional dos valores de prêmio e cobertura de critérios ficam com os revisores de cobertura e de lógica. Nenhum achado aqui impede o merge.
