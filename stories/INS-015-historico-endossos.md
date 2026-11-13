---
id: INS-015
dono_po: PO Exemplo
---

# Story do PO

## O que você quer
Como atendente da central, quero consultar o histórico de endossos de uma apólice, para responder o segurado sem abrir chamado para a TI.

## Por que agora e como saber que deu certo
Hoje cada consulta vira chamado. Quero reduzir os chamados de consulta de histórico.

## Como funciona hoje
O histórico só existe na trilha de auditoria e ninguém do atendimento consegue ver.

## Como deve funcionar
Informo o número da apólice e vejo a lista de endossos, do mais recente para o mais antigo, com data, cobertura anterior, cobertura nova, prêmio anterior e prêmio novo.

## Exemplos
| Situação | Entrada | Resultado esperado |
|---|---|---|
| Apólice com 2 endossos | AP-0001 | Lista com 2 itens, o mais recente primeiro |
| Apólice sem endosso | AP-0003 | Lista vazia |
| Apólice que não existe | AP-9999 | Mensagem de apólice não encontrada |

## O que não pode mudar
O cálculo do prêmio e o endosso de aumento de cobertura continuam iguais.

## Telas ou protótipos
Não tem tela por enquanto, só a API.

## Restrições que você conhece
Não mostrar nenhum dado pessoal.
