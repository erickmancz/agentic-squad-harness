---
id: INS-016
dono_po: PO Exemplo
faixa: semiautonoma
dev_revisor:
versao: 2
status: aprovada
---

# INS-016 · Consulta do histórico de endossos de uma apólice (exemplo fictício)

## 1. Cabeçalho
- ID: INS-016
- Dono (PO): PO Exemplo
- Faixa: semiautonoma (decidida pelo PO e pelo FDE).
- Recomendação do intake: critica. Motivo: a consulta lê valores de prêmio e dado potencialmente pessoal/financeiro da trilha de auditoria; pela lente de serviços financeiros, leitura de prêmio e exposição de histórico pediriam revisão linha a linha. O PO e o FDE decidiram semiautonoma; registra-se a recomendação uma vez, conforme o steering, e segue-se a decisão humana.
- Dev revisor: (vazio; não exigido na faixa semiautonoma).
- Versão: 2

## 2. Objetivo e métrica
- O que muda no negócio: o atendente da central consulta o histórico de endossos de uma apólice pela API, sem abrir chamado para a TI.
- KPI e alvo: reduzir os chamados de consulta de histórico de endosso. Alvo (de quanto para quanto) a definir com o negócio no piloto.

## 3. História e contexto
- Story: Como atendente da central, quero consultar o histórico de endossos de uma apólice, para responder o segurado sem abrir chamado para a TI.
- Regra atual: o histórico só existe na trilha de auditoria e ninguém do atendimento consegue ver.
- Regra nova: informado o número da apólice (formato AP seguido de 4 dígitos, ex.: AP-0001), a API devolve a lista de endossos do mais recente para o mais antigo, cada item com data, cobertura anterior, cobertura nova, prêmio anterior e prêmio novo; sem dado pessoal. É uma operação de leitura: não altera cálculo de prêmio nem a regra de endosso de aumento de cobertura.
- Regra de ordenação em empate de data: quando dois endossos têm a mesma data, o desempate é pelo identificador do endosso em ordem decrescente (identificador maior primeiro).
- Formato da data devolvida: data e hora em UTC, no padrão ISO-8601.
- Sistemas envolvidos: API de apólices e trilha de auditoria de endossos (fictícias, em memória nesta demo).

## 4. Aceite testável
- CA-01: Dado a apólice AP-0001 com 2 endossos registrados, quando o atendente consulta o histórico, então a resposta tem 2 itens ordenados do mais recente para o mais antigo.
- CA-02: Dado um item do histórico, quando ele é devolvido, então contém data, cobertura anterior, cobertura nova, prêmio anterior e prêmio novo, a data vem em UTC no padrão ISO-8601, e nenhum campo de dado pessoal.
- CA-03: Dado a apólice AP-0003 sem endosso, quando o atendente consulta o histórico, então a resposta é uma lista vazia e o status é de sucesso.
- CA-04: Dado a apólice AP-9999 que não existe, quando o atendente consulta o histórico, então a resposta indica "apólice não encontrada" (404) sem expor dado pessoal.
- CA-05: Dado valores de prêmio e cobertura no histórico, quando são devolvidos, então os valores monetários usam decimal.Decimal com duas casas e preservam o valor gravado na trilha, sem recálculo.
- CA-06: Dado a apólice AP-0001 com dois endossos registrados na mesma data e identificadores distintos, quando o atendente consulta o histórico, então o endosso de identificador maior aparece primeiro (desempate pelo identificador em ordem decrescente).

## 5. Referências de UX
- Não se aplica nesta demo: só a API, sem tela.

## 6. Dados e integrações
- APIs lidas: repositório de apólices e trilha de auditoria de endossos (em memória na demo).
- APIs escritas: nenhuma; a operação é somente leitura.
- Permissões: acesso autenticado com perfil de atendente, sem segregação por carteira nesta demo. Qualquer atendente autenticado pode consultar o histórico de qualquer apólice.
- Formato do número da apólice: AP seguido de 4 dígitos (ex.: AP-0001, AP-0003, AP-9999). Valores fora desse formato não correspondem a uma apólice válida.
- Dados pessoais e finalidade: a resposta não deve conter dado pessoal (CPF, nome, e-mail, telefone). O número da apólice é identificador de contrato, não dado pessoal direto. Se algum campo pessoal existir na trilha, ele é omitido da resposta.

## 7. Não funcionais
- Segurança: nenhum dado pessoal em resposta, log ou mensagem de erro; a consulta não altera estado.
- LGPD: não introduz novo campo de dado pessoal; a finalidade da leitura é atendimento ao segurado. Nenhum dado pessoal em teste, log ou exemplo; massa sintética.
- Desempenho: resposta em até 2 s no p95 no ambiente real (não medido na demo).
- Acessibilidade: não se aplica (sem tela).

## 8. Limites do agente
- O agente não altera o cálculo do prêmio nem a regra de endosso de aumento de cobertura (INS-014).
- O agente não cria novos campos de dado pessoal nem expõe na resposta campos pessoais existentes na trilha.
- O agente segue as decisões já tomadas na spec: número da apólice no formato AP+4 dígitos (bloco 6), desempate de data pelo identificador do endosso decrescente (bloco 3) e acesso autenticado com perfil de atendente sem segregação por carteira (bloco 6). O agente não altera essas decisões sem nova aprovação humana.

## 9. Testes e exemplos
- Cenários de sucesso: AP-0001 retorna 2 itens ordenados do mais recente para o mais antigo (CA-01, CA-02); AP-0003 retorna lista vazia (CA-03).
- Cenário de empate de data: AP-0001 com dois endossos na mesma data e identificadores distintos (ex.: 11 e 12) retorna o identificador 12 antes do 11 (CA-06).
- Cenário de exceção: AP-9999 inexistente retorna "apólice não encontrada" (CA-04).
- Formato da data nos exemplos: UTC ISO-8601, ex.: "2026-02-10T13:45:00Z".
- Exemplo de item devolvido (massa sintética): {"endorsement_id": 12, "date": "2026-02-10T13:45:00Z", "coverage_before": "100000.00", "coverage_after": "150000.00", "premium_before": "1200.00", "premium_after": "1500.00"}.
- Massa de dados: sintética (AP-0001 com 2 endossos, AP-0003 sem endosso, AP-9999 inexistente), valores monetários como strings de decimal.Decimal com duas casas.

## 10. Compatibilidade
- O cálculo do prêmio e o endosso de aumento de cobertura continuam iguais; esta spec só adiciona leitura.
- Rastreio: todo CA tem teste que cita "INS-016 CA-NN".

## Perguntas em aberto
- Nenhuma.
