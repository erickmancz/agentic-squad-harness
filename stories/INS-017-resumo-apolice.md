---
id: INS-017
dono_po: PO Exemplo
---

# Story do PO

## O que você quer
Como atendente da central, quero consultar o resumo de uma apólice pelo número, para confirmar com o segurado a situação, a cobertura e o prêmio sem abrir chamado para a TI.

## Por que agora e como saber que deu certo
Hoje a consulta de situação da apólice vira chamado. Quero que o atendente resolva sozinho na hora da ligação e que os chamados desse tipo caiam.

## Como funciona hoje
O atendente pede a informação para a TI, que consulta a base e responde por e-mail.

## Como deve funcionar
Informo o número da apólice e vejo o número, se ela está ativa ou inativa, a cobertura atual e o prêmio atual. Valores em reais com duas casas decimais.

## Exemplos
| Situação | Entrada | Resultado esperado |
|---|---|---|
| Apólice ativa | AP-0001 | Ativa, cobertura 100.000,00, prêmio 1.200,00 |
| Apólice inativa | AP-0002 | Inativa, cobertura 80.000,00, prêmio 950,00 |
| Apólice que não existe | AP-9999 | Mensagem de apólice não encontrada |
| Número em formato inválido | 12345 | Mensagem de número inválido |

## O que não pode mudar
A consulta é só leitura. O endosso de aumento de cobertura, a simulação e o histórico de endossos continuam iguais.

## Telas ou protótipos
Não tem tela. Consulta pela API.

## Restrições que você conhece
Nenhum dado pessoal do segurado aparece na resposta.
