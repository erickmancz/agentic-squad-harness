# Estimativa de custo · Agentic Squad Harness (ASH) · sa-east-1 · v2

Compass UOL
Data de referência dos preços: 20/10/2026
Mudança da v2: entra o bucket S3 de código (backup por git bundle, versionado); sai o CI em GitHub Actions (CI local, custo zero).
Mudança da v3 (12/11/2026): entra a stack de protótipo da fase de descoberta (S3 privado, CloudFront e WAF). O WAF cobra mensalidade fixa, então a parte AWS deixa de custar perto de zero parada enquanto a `AshProtoStack` existir. O `teardown` passa a remover essa stack.

## Leitura rápida

| Parte | Como cobra | Situação do preço |
|---|---|---|
| Kiro (onde a squad trabalha) | Assinatura por usuário + créditos extras a US$ 0,04 | **Verificado** em kiro.dev/pricing em 20/10/2026. O preço é por usuário e não varia por região AWS |
| Hospedagem de protótipo (S3, CloudFront, WAF) | WAF com mensalidade fixa por web ACL e por regra, mais requisições; S3 e CloudFront por uso | WAF **verificado** em aws.amazon.com/waf/pricing em 12/11/2026: US$ 5,00 por web ACL/mês, US$ 1,00 por regra/mês, US$ 0,60 por milhão de requisições. O WAF de escopo CloudFront é criado em us-east-1, fora de sa-east-1. S3 e CloudFront **não verificados** |
| Coletor de métricas e bucket de código AWS (S3, Lambda, DynamoDB, EventBridge Scheduler, CloudWatch Logs, X-Ray) | Por uso, ocioso perto de zero | **Preço sa-east-1 não verificado**: as páginas de pricing e a Price List API não abriram a partir deste ambiente. Preencher no AWS Pricing Calculator com os volumes abaixo |

O custo é dominado pelo Kiro. A parte AWS do ASH foi desenhada para custar quase nada parada, sem NAT, cluster, assinatura de BI ou throughput provisionado. A exceção é o WAF do protótipo: US$ 6,00 por mês fixos (1 web ACL e 1 regra) enquanto a `AshProtoStack` existir.

## Preços Kiro usados (kiro.dev/pricing, 20/10/2026)

| Plano | US$/usuário/mês | Créditos incluídos |
|---|---|---|
| Pro | 20 | 1.000 |
| Pro+ | 40 | 2.000 |
| Pro Max | 100 | 5.000 |
| Power | 200 | 10.000 |
| Crédito extra | 0,04 por crédito | Overage no enterprise vem desligado por padrão e é ligado pelo admin |
| Enterprise (cobrado via AWS, com SSO e analytics) | Sob consulta a vendas | **Não verificado** |

Os preços não incluem impostos. **[LACUNA]** O consumo de créditos por spec ainda não foi medido; essa medição é um dos resultados da demonstração.

## Premissas de volume

| Cenário | Pessoas com Kiro | Specs/mês | Eventos de métrica/mês | Backups no S3/mês (bundle de até 5 MB) |
|---|---|---|---|---|
| Demonstração | 1 FDE | 3 | 300 | 10 |
| Piloto (2 squads, 1 domínio) | 1 FDE, 2 PO, 1 Dev revisor | 30 | 6.000 | 60 |
| Produção pequena (3 squads) | 1 FDE, 3 PO, 1 Dev revisor | 60 | 15.000 | 120 |

Planos assumidos: FDE em Pro Max (orquestra e consome mais), PO e Dev revisor em Pro. Créditos extras: zero na demo, a definir após a medição na demonstração nos demais cenários.

## Cenário 1 · Demo

| Componente | Dimensão de cobrança | Premissa | Custo mensal (USD) | Ocioso ou por uso |
|---|---|---|---|---|
| Kiro, 1 FDE | Por usuário | Pro+ (suficiente para a demo) | 40,00 | Fixo por usuário |
| S3 (eventos e relatórios) | GB-mês + requisições PUT/GET | < 0,01 GB, ~50 PUT | não verificado | Por uso |
| S3 (bucket de código, versionado) | GB-mês incluindo versões antigas + PUT | 10 bundles × 5 MB, versões por 180 dias | não verificado | Ocioso (armazenamento) |
| Lambda | Requisições + GB-s | ~60 invocações, 256 MB, < 2 s | não verificado | Por uso |
| DynamoDB on-demand | Write/read request units + GB-mês | 300 escritas, ~1.000 leituras | não verificado | Por uso |
| EventBridge Scheduler | Invocações | 4/mês | não verificado | Por uso |
| CloudWatch Logs | GB ingerido + GB armazenado | < 0,01 GB, retenção de 30 dias | não verificado | Por uso |
| X-Ray | Traces registrados | ~60 | não verificado | Por uso |
| WAF do protótipo (AshProtoStack) | Web ACL e regra por mês + requisições | 1 web ACL, 1 regra de limite por IP, tráfego de demo | 6,00 + 0,60 por milhão de requisições | Fixo enquanto a stack existir |
| CloudFront e S3 do protótipo | Transferência, requisições e GB-mês | Protótipo estático, acesso interno | não verificado | Por uso |

## Cenário 2 · Piloto

| Componente | Dimensão de cobrança | Premissa | Custo mensal (USD) | Ocioso ou por uso |
|---|---|---|---|---|
| Kiro, FDE | Por usuário | Pro Max | 100,00 | Fixo por usuário |
| Kiro, 2 PO | Por usuário | Pro | 40,00 | Fixo por usuário |
| Kiro, Dev revisor | Por usuário | Pro | 20,00 | Fixo por usuário |
| Kiro, créditos extras | US$ 0,04/crédito | A medir na demonstração | não estimado | Por uso |
| S3 (eventos e relatórios) | GB-mês + requisições | ~0,05 GB, ~1.000 PUT | não verificado | Por uso |
| S3 (bucket de código) | GB-mês incluindo versões + PUT | 60 bundles × 5 MB acumulando até 180 dias | não verificado | Ocioso (armazenamento) |
| Lambda | Requisições + GB-s | ~1.000 invocações | não verificado | Por uso |
| DynamoDB on-demand | WRU/RRU + GB-mês | 6.000 escritas, ~20.000 leituras | não verificado | Por uso |
| EventBridge Scheduler | Invocações | 4/mês | não verificado | Por uso |
| CloudWatch Logs | GB ingerido + armazenado | ~0,1 GB | não verificado | Por uso |
| WAF do protótipo (AshProtoStack) | Web ACL e regra por mês + requisições | 1 web ACL, 1 regra de limite por IP, tráfego de demo | 6,00 + 0,60 por milhão de requisições | Fixo enquanto a stack existir |
| CloudFront e S3 do protótipo | Transferência, requisições e GB-mês | Protótipo estático, acesso interno | não verificado | Por uso |

## Cenário 3 · Produção pequena

| Componente | Dimensão de cobrança | Premissa | Custo mensal (USD) | Ocioso ou por uso |
|---|---|---|---|---|
| Kiro, FDE | Por usuário | Pro Max | 100,00 | Fixo por usuário |
| Kiro, 3 PO | Por usuário | Pro | 60,00 | Fixo por usuário |
| Kiro, Dev revisor | Por usuário | Pro | 20,00 | Fixo por usuário |
| Kiro, créditos extras | US$ 0,04/crédito | A medir na demonstração | não estimado | Por uso |
| Coletor AWS (mesmos itens) | Por uso | ~15.000 eventos, ~2.000 invocações | não verificado | Por uso |
| S3 (bucket de código) | GB-mês incluindo versões + PUT | 120 bundles × 5 MB acumulando até 180 dias | não verificado | Ocioso (armazenamento) |
| WAF do protótipo (AshProtoStack) | Web ACL e regra por mês + requisições | 1 web ACL, 1 regra de limite por IP, tráfego de demo | 6,00 + 0,60 por milhão de requisições | Fixo enquanto a stack existir |
| CloudFront e S3 do protótipo | Transferência, requisições e GB-mês | Protótipo estático, acesso interno | não verificado | Por uso |

## Fechamento

| | Demo | Piloto | Produção pequena |
|---|---|---|---|
| Custo ocioso mensal AWS | US$ 6,00 do WAF do protótipo (verificado) + armazenamento residual em S3, DynamoDB e logs (não verificado). Sem a `AshProtoStack`, perto de zero | Idem | Idem |
| Kiro (assinaturas, verificado) | US$ 40 | US$ 160 | US$ 180 |
| Kiro (créditos extras) | 0 | A medir | A medir |
| AWS por uso | Não verificado | Não verificado | Não verificado |

**Principal alavanca de custo:** créditos Kiro. O que faria a conta explodir é overage ligado sem limite, ou specs mal escritas que geram retrabalho de agente. O agente de intake e o `spec-gate` existem também para segurar esse custo.

**Armadilhas checadas e evitadas:** NAT Gateway, cluster provisionado, assinatura de BI por usuário, throughput provisionado no Bedrock, log sem retenção (30 dias definidos), transferência entre regiões. O envio de eventos e o backup vão para a região onde as stacks estiverem. Ponto de atenção: o bucket de código cresce com as versões antigas; a regra de 180 dias limita isso.

**Ponto de residência de dados:** o custo AWS do coletor pode ficar em sa-east-1, mas o processamento do Kiro acontece fora do Brasil. O perfil enterprise fica em US East (N. Virginia) ou Europe (Frankfurt), e a inferência usa cross-region nas geografias US ou Europa (kiro.dev, páginas de regiões e de proteção de dados, consultadas em 20/10/2026). Para cliente regulado, isso pesa mais que o custo.

Os valores são estimativa a partir do preço público na data indicada e não substituem o AWS Pricing Calculator. Revalidar antes de qualquer proposta comercial; as linhas "não verificado" precisam ser preenchidas na calculadora com preço de South America (São Paulo).
