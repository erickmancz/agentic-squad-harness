---
id: INS-014
dono_po: PO Exemplo
faixa: critica
dev_revisor: Dev Revisor Exemplo
versao: 1
status: aprovada
---

# INS-014 · Aumento de cobertura de incêndio pelo app (exemplo fictício)

## 1. Cabeçalho
- ID: INS-014
- Dono (PO): PO Exemplo
- Faixa: critica (altera cálculo de prêmio, regra monetária)
- Dev revisor: Dev Revisor Exemplo
- Versão: 1

## 2. Objetivo e métrica
- O que muda no negócio: o segurado aumenta a cobertura de incêndio pelo app, sem ligar para a central.
- KPI: percentual de endossos de aumento de cobertura feitos pelo app. Alvo a definir com o negócio no piloto.

## 3. História e contexto
- Story: Como segurado com apólice ativa, quero aumentar minha cobertura de incêndio pelo app, para não depender da central.
- Regra atual: o aumento só é feito pela central, com cálculo manual.
- Regra nova: o prêmio é recalculado de forma proporcional à nova cobertura, com arredondamento HALF_UP em centavos.
- Sistemas envolvidos: API de apólices (fictícia, em memória nesta demo).

## 4. Aceite testável
- CA-01: Dado uma apólice ativa com cobertura 100.000,00 e prêmio 1.200,00, quando o segurado pede cobertura 150.000,00, então o prêmio passa a 1.800,00 (proporcional, HALF_UP em centavos).
- CA-02: Dado uma apólice cancelada, quando o segurado pede aumento, então a resposta é 409 e o prêmio não muda.
- CA-03: Dado uma nova cobertura menor ou igual à atual, quando o pedido é feito, então a resposta é 422.
- CA-04: Dado uma nova cobertura acima de 2 vezes a atual, quando o pedido é feito, então a resposta é 422 com a mensagem do limite; exatamente 2 vezes é aceito.
- CA-05: Dado um endosso aplicado, quando ele é gravado, então a trilha de auditoria registra apólice, solicitante (canal), data, prêmio e cobertura anteriores e novos, sem dado pessoal.

## 5. Referências de UX
- Não se aplica nesta demo: só a API. Tela de endosso v2 fica para outra spec.

## 6. Dados e integrações
- APIs expostas: POST /apolices/{numero}/endossos/aumento-cobertura
- APIs lidas e escritas: repositório de apólices (em memória na demo).
- Permissões: escrita autenticada no ambiente real (fora do escopo da demo).
- Dados pessoais: nenhum. O solicitante é o canal (ex.: canal-app).

## 7. Não funcionais
- Segurança: nenhum dado pessoal em log ou auditoria.
- LGPD: não trata dado pessoal.
- Desempenho: resposta em até 2 s no p95 no ambiente real (não medido na demo).
- Acessibilidade: não se aplica (sem tela).

## 8. Limites do agente
- O agente não altera a fórmula do prêmio, o limite de 2 vezes nem a regra de arredondamento sem aprovação humana.
- O agente não cria novos campos de dado pessoal.

## 9. Testes e exemplos
- Sucesso: 100.000 para 150.000 com prêmio 1.200,00 gera 1.800,00; 33.333,00 para 50.000,00 com prêmio 777,77 gera 1.166,67; exatamente 2 vezes é aceito.
- Exceção: apólice cancelada (409); cobertura igual ou menor (422); acima de 2 vezes (422); apólice inexistente (404).
- Massa: sintética (AP-0001, AP-0002, AP-0003).

## 10. Compatibilidade
- Apólices sem endosso mantêm prêmio e cobertura.
- Rastreio: todo CA tem teste que cita "INS-014 CA-NN".

## Perguntas em aberto
- Nenhuma
