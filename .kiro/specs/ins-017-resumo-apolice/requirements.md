---
id: INS-017
dono_po: Igor
faixa: semiautonoma
dev_revisor: Mancz
versao: 1
status: aprovada
---

# INS-017 · Resumo da apólice

## 1. Cabeçalho
- ID: INS-017
- Dono (PO): Igor
- FDE: Erick
- Dev revisor: Mancz (nomeado; só atua se a faixa passar para `critica`)
- Faixa proposta: semiautonoma. Novo endpoint somente de leitura, sem dado pessoal; prêmio e cobertura são exibidos, não calculados nem alterados, então não entram na linha `critica` (a lente financeira trata regra que altera valor cobrado ou pago). Decisão humana: semiautonoma. O acesso reaproveita o mecanismo de autenticação que a API de apólices já usa, sem controle de acesso novo; se esta story passar a criar autenticação ou perfil novo, a faixa sobe para `critica`.
- Lente ativa: serviços financeiros (seguros).
- Versão: 1

## 2. Objetivo e métrica
- O que muda no negócio: o atendente da central consulta sozinho, durante a ligação, o resumo de uma apólice (número, situação, cobertura e prêmio), sem abrir chamado para a TI.
- KPI e alvo: redução dos chamados de consulta de situação de apólice. Alvo: redução de 50% em 90 dias, com a linha de base medida antes do lançamento.

## 3. História e contexto
- Story: Como atendente da central, quero consultar o resumo de uma apólice pelo número, para confirmar com o segurado a situação, a cobertura e o prêmio sem abrir chamado para a TI.
- Regra atual: o atendente pede a informação à TI, que consulta a base e responde por e-mail.
- Regra nova: consulta pela API informando o número da apólice. A resposta traz número, situação (ativa ou inativa), cobertura atual e prêmio atual, em reais com duas casas decimais.
- Sistemas envolvidos: API de apólices (nova consulta) e a base de apólices existente, apenas leitura. Endosso de aumento de cobertura, simulação e histórico de endossos não são tocados.

## 4. Aceite testável
- CA-01: Dado que existe a apólice AP-0001 ativa, com cobertura 100.000,00 e prêmio 1.200,00, quando o atendente consulta o número AP-0001, então a resposta traz número AP-0001, situação ativa, cobertura 100.000,00 e prêmio 1.200,00.
- CA-02: Dado que existe a apólice AP-0002 inativa, com cobertura 80.000,00 e prêmio 950,00, quando o atendente consulta o número AP-0002, então a resposta traz situação inativa, cobertura 80.000,00 e prêmio 950,00.
- CA-03: Dado que não existe a apólice AP-9999, quando o atendente consulta o número AP-9999, então a resposta é a mensagem de apólice não encontrada.
- CA-04: Dado um número fora do formato `AP-` seguido de exatamente 4 dígitos (por exemplo 12345, AP-123 ou AP-12345), quando o atendente consulta esse número, então a resposta é a mensagem de número inválido e a base não é consultada.
- CA-05: Dado qualquer consulta bem-sucedida, quando a resposta é montada, então cobertura e prêmio são valores monetários com duas casas decimais, calculados e transportados como `Decimal`, nunca como ponto flutuante.
- CA-06: Dado qualquer consulta, quando a resposta é devolvida, então ela não contém nenhum dado pessoal do segurado.
- CA-07: Dado qualquer consulta, quando ela é executada, então nenhum dado é criado, alterado ou removido na base (somente leitura).
- CA-08: Dado um chamador não autenticado pelo mecanismo de acesso já usado pela API de apólices, quando ele consulta qualquer número, então a consulta é recusada por esse mecanismo e a base não é consultada.
- CA-09: Dado um atendente autenticado, quando ele consulta um número de apólice válido, então é gravado um registro de auditoria com usuário, número da apólice e horário, sem nenhum dado pessoal do segurado.
- CA-10: Dado o uso normal da consulta, quando se mede o tempo de resposta, então o percentil 95 é de até 2 segundos.

## 5. Referências de UX
- Não se aplica: a story não prevê tela, a consulta é pela API.

## 6. Dados e integrações
- APIs lidas: base de apólices (número, situação, cobertura atual, prêmio atual). Fonte exata dos campos a confirmar com o FDE.
- APIs escritas: nenhuma.
- Permissões: somente leitura. Só atendentes autenticados pelo mecanismo de acesso que a API de apólices já usa; nenhum controle novo.
- Auditoria de acesso: cada consulta de número válido por usuário autenticado registra usuário, número da apólice e horário, sem dado pessoal do segurado.
- Dados pessoais e finalidade: nenhum dado pessoal é lido nem devolvido. Cobertura e prêmio são dados financeiros da apólice, expostos só para o atendente confirmar a situação com o segurado.

## 7. Não funcionais
- Segurança: apenas leitura; entrada validada antes de qualquer acesso à base (formato do número); erros sem detalhes internos; acesso só por atendente autenticado (CA-08).
- LGPD: resposta sem dado pessoal do segurado. Logs e registro de auditoria não registram dado pessoal.
- Auditoria: usuário, número da apólice e horário de cada consulta (CA-09).
- Desempenho: p95 de até 2 segundos (CA-10).
- Acessibilidade: não se aplica, não há tela.

## 8. Limites do agente
- O agente não decide sozinho nem cria autenticação, perfil ou controle de acesso novo (usa o mecanismo existente), nem qualquer regra de arredondamento ou cálculo de valores (os valores são exibidos como estão na base).
- O agente não altera endosso, simulação nem histórico de endossos, e não escreve na base.

## 9. Testes e exemplos
- Cenários de sucesso: AP-0001 (ativa, 100.000,00, 1.200,00) e AP-0002 (inativa, 80.000,00, 950,00).
- Cenários de exceção: AP-9999 (não encontrada); 12345, AP-123 e AP-12345 (formato inválido); chamador não autenticado; consulta válida gerando registro de auditoria.
- Massa de dados: sintética.

## 10. Compatibilidade
- O que não pode mudar: a consulta é só leitura; o endosso de aumento de cobertura, a simulação e o histórico de endossos continuam iguais.
- Rastreio: todo CA tem teste que cita "INS-017 CA-NN".

## Perguntas em aberto
- Nenhuma
