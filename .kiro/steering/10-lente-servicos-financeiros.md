---
inclusion: auto
name: lente-servicos-financeiros
description: Regras adicionais para squads de bancos, seguradoras, meios de pagamento e crédito. Use quando a spec tratar de prêmio, juros, saldo, pagamento, crédito, cobrança, tarifa ou dado financeiro de pessoa.
---

# Lente de serviços financeiros (Brasil)

Lente de vertical. Ela só acrescenta regras ao núcleo (`00-governanca.md`, `01-faixas-autonomia.md`) e nunca remove nenhuma. Dado pessoal e LGPD já estão no núcleo e valem para qualquer setor. Use este arquivo também como exemplo pronto para criar lentes de outros setores a partir de `templates/lente-vertical.md`.

## Exemplos que entram na faixa `critica` neste setor

Cálculo de prêmio, juros, saldo, limite de crédito, tarifa, cobrança, parcelamento, conciliação e qualquer regra que altere valor cobrado ou pago ao cliente final.

## Regras do setor

1. **Separação de funções.** Quem implementa uma regra de cálculo não aprova a mesma regra. Em faixa `critica`, o `dev_revisor` e o FDE são pessoas diferentes.
2. **Trilha de auditoria.** Toda alteração de valor monetário registra quem pediu, quando, valor anterior e valor novo.
3. **Arredondamento.** A regra de arredondamento monetário é explícita na spec. Na ausência dela, a spec volta para "Perguntas em aberto".
4. **Mudança em regra regulatória.** Faixa `critica`, sempre, e a spec cita a norma ou o documento interno que motivou a mudança.
