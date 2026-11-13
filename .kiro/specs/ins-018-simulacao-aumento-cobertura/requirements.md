---
id: INS-018
dono_po: PO Exemplo
faixa: critica
dev_revisor: Dev Revisor Exemplo
versao: 1
status: aprovada
---

# INS-018 · Simulação de prêmio por aumento de cobertura

## 1. Cabeçalho
- ID: INS-018
- Dono (PO): PO Exemplo
- Faixa proposta: critica (a simulação executa o cálculo de prêmio, regra monetária; pela lente de serviços financeiros, cálculo de prêmio é sempre crítica)
- Dev revisor: Dev Revisor Exemplo
- Versão: 1
- Recomendação de faixa do intake: critica (mantida; decisão humana no portão de aprovação)

## 2. Objetivo e métrica
- O que muda no negócio: o corretor simula o aumento de cobertura e vê o prêmio novo antes de pedir o endosso, conversando com o segurado já com o número na mão.
- KPI e alvo: percentual de simulações que viram endosso aprovado (taxa de conversão da simulação). Alvo a definir com o negócio no piloto.

## 3. História e contexto
- Story: Como corretor, quero simular o aumento de cobertura de uma apólice e ver o prêmio novo antes de levar a proposta ao segurado, sem que nada seja alterado na apólice.
- Regra atual: o corretor só descobre o prêmio novo depois de pedir o endosso; se o valor não agrada, o pedido volta e o trabalho se perde.
- Regra nova: uma consulta de simulação calcula o prêmio novo de forma proporcional à cobertura pedida, usando a mesma regra de prêmio já aplicada no aumento de cobertura (ver INS-014), sem alterar a apólice.
- Arredondamento monetário: HALF_UP em centavos, igual ao aumento de cobertura já existente (INS-014). Regra explícita conforme a lente de serviços financeiros.
- Validade do valor simulado: não há validade formal. A simulação é informativa e sempre recalculada na hora; o corretor apresenta o número como referência do momento, sem prazo de garantia.
- Sistemas envolvidos: API de apólices (fictícia, em memória nesta demo) e log de auditoria da simulação (sem dado pessoal).

## 4. Aceite testável
- CA-01: Dado a apólice ativa AP-0001 (cobertura 100.000,00 e prêmio 1.200,00), quando o corretor simula a cobertura 150.000,00, então a resposta é 200 com prêmio novo 1.800,00 (proporcional à cobertura pedida).
- CA-02: Dado a apólice ativa AP-0003 (cobertura 33.333,00 e prêmio 777,77), quando o corretor simula a cobertura 50.000,00, então a resposta é 200 com prêmio novo 1.166,67 (proporcional à cobertura pedida).
- CA-03: Dado uma apólice inativa, quando o corretor simula um aumento, então a resposta é 409 com aviso de que a apólice não está ativa e por isso não aceita simulação, e nada muda na apólice.
- CA-04: Dado uma apólice ativa, quando o corretor simula uma cobertura acima de 2 vezes a cobertura atual, então a resposta é 422 com aviso de que o aumento passa do limite permitido, e nada muda na apólice; exatamente 2 vezes é aceito.
- CA-05: Dado uma apólice que não existe, quando o corretor simula um aumento, então a resposta é 404 com aviso de que a apólice não foi encontrada.
- CA-06: Dado qualquer simulação (sucesso ou erro), quando ela termina, então a apólice continua com a mesma cobertura, o mesmo prêmio e sem nenhum endosso criado (só consulta).
- CA-07: Dado uma simulação bem-sucedida pedida por um corretor identificado por identificador técnico (ex.: corretor BRK-001), quando ela termina, então é gravado um registro na trilha de auditoria com número da apólice, cobertura atual, cobertura pedida, prêmio simulado, identificador de quem pediu e data/hora, e esse registro não contém nenhum dado pessoal (sem CPF, nome, e-mail ou telefone).

## 5. Referências de UX
- Não se aplica nesta demo: só a API. A tela de simulação para o corretor fica para outra spec.

## 6. Dados e integrações
- APIs expostas: endpoint de simulação de aumento de cobertura (não altera a apólice), a definir no design.
- APIs lidas: repositório de apólices (em memória na demo).
- APIs escritas: trilha de auditoria da simulação. A simulação não altera a apólice, mas grava um registro de auditoria sem dado pessoal, com número da apólice, cobertura atual, cobertura pedida, prêmio simulado, identificador de quem pediu (técnico/corretor, ex.: BRK-001) e data/hora. Essa escrita atende a trilha de auditoria da lente de serviços financeiros (quem pediu, quando, valor anterior e valor novo).
- Permissões: leitura autenticada no ambiente real (fora do escopo da demo).
- Dados pessoais e finalidade: nenhum dado pessoal. A apólice é identificada por número fictício (ex.: AP-0001) e quem pediu é identificado por identificador técnico/corretor (ex.: BRK-001), nunca por nome, CPF, e-mail ou telefone. Finalidade do registro de auditoria: rastrear quem pediu a simulação, quando, valor anterior e valor novo, sem tratar dado pessoal.

## 7. Não funcionais
- Segurança: nenhum dado pessoal em log, resposta ou mensagem de erro. O log de auditoria da simulação registra apenas número da apólice, cobertura atual, cobertura pedida, prêmio simulado, identificador técnico de quem pediu e data/hora.
- LGPD: não trata dado pessoal; nenhum campo novo de dado pessoal. A trilha de auditoria usa identificador técnico/corretor (ex.: BRK-001), sem CPF, nome, e-mail ou telefone.
- Desempenho: resposta em até 2 s no p95 no ambiente real (não medido na demo).
- Acessibilidade: não se aplica (sem tela).

## 8. Limites do agente
- O agente não altera a fórmula do prêmio, o limite de 2 vezes nem a regra de arredondamento sem aprovação humana.
- O agente não transforma a simulação em escrita na apólice: nenhum endosso, nenhuma alteração na apólice. A única escrita permitida é o registro na trilha de auditoria (sem dado pessoal).
- O agente não cria novos campos de dado pessoal nem grava dado pessoal no log de auditoria.
- O agente não altera a regra de arredondamento (HALF_UP em centavos), o formato do registro de auditoria nem a natureza informativa (sem validade) do valor simulado sem aprovação humana.

## 9. Testes e exemplos
- Cenários de sucesso: AP-0001 de 100.000,00 para 150.000,00 gera prêmio 1.800,00; AP-0003 de 33.333,00 para 50.000,00 gera prêmio 1.166,67; exatamente 2 vezes a cobertura atual é aceito.
- Cenários de exceção: apólice inativa (409); cobertura acima de 2 vezes a atual (422); apólice inexistente (404).
- Arredondamento: o prêmio simulado usa HALF_UP em centavos (igual ao INS-014). O caso AP-0003 de 33.333,00 para 50.000,00 gera 1.166,67 justamente por HALF_UP em centavos.
- Trilha de auditoria (CA-07): após uma simulação bem-sucedida, há um registro de auditoria com número da apólice, cobertura atual, cobertura pedida, prêmio simulado, identificador técnico de quem pediu e data/hora; o teste verifica que o registro não contém dado pessoal (sem CPF, nome, e-mail ou telefone).
- Garantia de não mutação: após cada cenário, a apólice mantém cobertura, prêmio e ausência de endosso.
- Massa de dados: sintética (AP-0001, AP-0003 e demais apólices fictícias da demo; quem pede é um identificador técnico/corretor fictício, ex.: BRK-001).

## 10. Compatibilidade
- O que não pode mudar: a apólice permanece exatamente como estava (mesma cobertura, mesmo prêmio, nenhum endosso criado); a simulação não altera a apólice nem o comportamento do aumento de cobertura existente (INS-014). A única escrita nova é o registro na trilha de auditoria (sem dado pessoal), que não toca a apólice.
- Validade do valor simulado: não há validade formal; o número é informativo e recalculado a cada simulação.
- Rastreio: todo CA tem teste que cita "INS-018 CA-NN".

## Perguntas em aberto
- Nenhuma. Todas as pendências foram decididas pelo PO (PO Exemplo): arredondamento HALF_UP em centavos (bloco 3 e 9); registro em trilha de auditoria sem dado pessoal (blocos 6, 7 e CA-07); valor simulado sem validade formal, informativo e recalculado na hora (blocos 3 e 10).
