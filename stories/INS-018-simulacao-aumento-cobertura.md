# INS-018 · Simulação de aumento de cobertura

Story do PO para a squad agêntica (ASH). Escrita em linguagem de negócio; a especificação de 10 blocos é gerada pelo intake.

## O pedido

Como corretor, quero simular o aumento de cobertura de uma apólice e ver o prêmio novo antes de levar a proposta ao segurado, sem que nada seja alterado na apólice.

## Por que isso importa

Hoje o corretor só descobre o prêmio novo depois de pedir o endosso. Se o valor não agrada ao segurado, o pedido volta e o trabalho se perde. Com a simulação, ele conversa com o segurado já com o número na mão.

## Exemplos que precisam dar certo

Calculados com a regra de prêmio que o sistema já usa hoje.

| Apólice | Cobertura pedida | Prêmio novo esperado |
|---|---|---|
| AP-0001 | 150.000,00 | 1.800,00 |
| AP-0003 | 50.000,00 | 1.166,67 |

## Situações em que a simulação não pode ser feita

| Situação | O que o corretor precisa ver |
|---|---|
| Apólice inativa | Aviso de que a apólice não está ativa e por isso não aceita simulação |
| Cobertura pedida acima de 2 vezes a cobertura atual | Aviso de que o aumento passa do limite permitido |
| Apólice que não existe | Aviso de que a apólice não foi encontrada |

## O que não pode mudar

A simulação é só consulta. A apólice continua exatamente como estava: mesma cobertura, mesmo prêmio, nenhum endosso criado.

## Dúvida que ainda tenho

Ainda não sei se a simulação precisa ficar registrada em algum lugar, nem por quanto tempo o valor simulado continua valendo para o corretor apresentar ao segurado.
