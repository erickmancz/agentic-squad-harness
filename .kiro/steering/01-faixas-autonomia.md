---
inclusion: always
---

# Faixas de autonomia

Em toda faixa o agente gera a primeira versão do código. O que muda é a energia humana e a quantidade de gates.

| Faixa | Exemplos de mudança | Gate humano | Aprovações exigidas no merge |
|---|---|---|---|
| `autonoma` | Texto, cor, layout, configuração simples, ajuste de mensagem | FDE confere a diferença e o resultado do CI local | FDE |
| `semiautonoma` | Nova lógica de negócio, nova validação, novo endpoint sem dado sensível | FDE revisa a lógica contra a spec e aprova plano e merge | FDE |
| `critica` | Regra que calcula valor cobrado, pago, devido ou concedido; dado pessoal sensível; autenticação; autorização; regra regulatória do setor; migração; modernização de legado; mudança de arquitetura | Dev revisor lê linha a linha e reescreve onde precisar; FDE aprova; arquitetura do cliente aprova se mudar arquitetura | FDE e o `dev_revisor` nomeado na spec |

## Como escolher a faixa

1. Se a mudança toca qualquer item da linha `critica`, a faixa é `critica`, mesmo que o resto seja simples.
2. Na dúvida entre duas faixas, escolha a mais alta e registre a dúvida em "Perguntas em aberto".
3. O agente de intake **propõe** a faixa. Quem decide é o PO junto com o FDE, na aprovação da spec.
4. Cada lente de vertical ativa pode acrescentar exemplos à linha `critica` com o vocabulário do setor (a lente de serviços financeiros, por exemplo, acrescenta prêmio, juros, saldo e crédito). Uma lente nunca rebaixa uma faixa.

## Fidelidade do emulador por faixa

Vale para perfis de stack que declaram o bloco `emulador_aws` (projetos que chamam serviços AWS; o exemplo é `perfis/python-aws.json`). O perfil `python` padrão não declara o bloco, então nenhuma faixa exige emulador nem `homologacao` por causa dele. O AWS Emulator não replica a AWS por inteiro: cada serviço tem uma fidelidade (nota "k de n" publicada a cada release, registrada no perfil, com fonte e data) e o emulador não avalia políticas IAM. Por isso a evidência exigida cresce com a faixa:

| Faixa | O que o merge exige além das aprovações |
|---|---|
| `autonoma` | A etapa `integracao-aws` verde no emulador (o CI verde já a inclui) |
| `semiautonoma` | Emulador verde. Para os serviços do perfil com fidelidade **abaixo do corte** (`fidelidade_minima`), ou com fidelidade `null` (ainda não preenchida), exige também a execução em conta real de homologação |
| `critica` | Emulador verde **e** execução em conta real de homologação, sempre, com evidência |

Como a evidência fica registrada, sem criar etapa nova no núcleo do CI (o núcleo continua sendo só `spec-gate` e `rastreio`):
- **Emulador:** o evento `ci_executado` leva no detalhe `emulador` (`ok`, `falhou`, `pulado` ou `nao_aplicavel`), `emulador_versao` e `servicos_abaixo_do_corte`.
- **Conta real:** o papel `homologacao` em `.ash/approvals/<ID>.json`, registrado pelo portão `aprovar-homologacao` (`python ash.py aprovar ID --papel homologacao --nome NOME --branch feat/<id> --evidencia "<onde está o registro>"`). Guarda o commit, quem declarou, a frase literal do humano e a evidência. O `merge` recusa se a homologação não existir ou se foi registrada para outro commit.
- A execução em conta real é feita pelo humano ou pela esteira do cliente, fora do ASH. O ASH não a executa nem recebe credencial real: ele só registra a declaração e a evidência. Os agentes nunca tocam conta AWS real (`06-emulador-aws.md`).

Este catálogo é a versão inicial e será calibrado com os dados do piloto.
