---
inclusion: fileMatch
fileMatchPattern: "portfolio/**"
---

# Fase de descoberta e definição de produto

Esta fase é opcional e vem ANTES da story. Ela existe para quando o PO ainda não tem a story pronta: parte de uma ideia ou de um problema de negócio e produz, com método, a story que entra no fluxo normal do ASH (intake → spec de dez blocos → design → implementação → merge).

Inspirada no Working Backwards da Amazon. Ela não substitui nenhuma regra da governança (`00-governanca.md`), das faixas (`01-faixas-autonomia.md`) nem dos portões (`04-papeis-e-portoes.md`). Só acrescenta uma etapa na frente.

## Quando usar

- Use quando o humano disser "tenho uma ideia, não sei por onde começar", "me ajuda a criar o produto", "quero descobrir o que construir".
- Não use quando o PO já tem a story clara: nesse caso vá direto ao `nova-spec` e ao intake, como sempre.
- A descoberta é conduzida pelo agente `product-lead`, delegado pelo squad-lead. Como todo agente de papel, ele escreve só na sua pasta (`portfolio/`), nunca em código, spec, `ash.py` ou harness.

## Princípio: pessoas no centro

A diferenciação vem das pessoas: criatividade, diversidade de perspectiva e conhecimento do cliente. O agente acelera a coleta de evidência, a redação e o rascunho; ele não substitui o julgamento humano na descoberta, na definição do problema nem na invenção. Por isso cada fase é **travada por participação humana**: o fluxo não avança sem a decisão do humano no portão.

## As cinco etapas (cada uma termina numa decisão humana no chat)

Cada etapa gera um artefato em `portfolio/iniciativas/<slug>/` e termina numa decisão humana (Aprovar / Pedir mudança). O squad-lead mostra o artefato no chat e pede Aprovar ou Pedir mudança. Só a definição (PRFAQ/PRD) e a publicação do protótipo têm portão registrado (`aprovar-prd` e `publicar-proto`); a decisão das etapas 1 a 3 fica registrada pelo evento `descoberta_etapa`.

1. **Intenção.** O que o humano quer, o que já existe de material, qual a data-alvo. Artefato: `intencao.md`.
2. **Estado atual (Escutar e Definir o problema).** Quem é o cliente, como ele vive e decide, quais as dores. Antes de pesquisar na web, o `product-lead` pergunta ao humano: você tem dados/materiais, prefere que a gente pesquise online, ou começamos por uma reflexão guiada? Respostas do humano entram como evidência declarada `[D]` (percepção de quem conhece o cliente, ainda não validada). Artefatos: `retrato-cliente.md`, `problema.md`.
3. **Invenção (ideação).** Diverge a partir do problema, converge para a Big Idea. O humano inventa; o agente provoca e facilita. Nunca começa pelas ideias do agente: pergunte se o humano ideia, o agente propõe, ou híbrido. Artefato: `big-idea.md`.
4. **Definição (PRFAQ/PRD).** O `product-lead` escreve o PRFAQ (Working Backwards) e o PRD a partir da Big Idea decidida, passa por uma rodada de crítica adversarial (os revisores do ASH atacam o documento) e registra divergências abertas. Artefatos: `prfaq.md`, `prd.md`.
5. **Handoff para o ASH.** O PRD aprovado vira uma ou mais stories em `stories/`. A partir daí o fluxo é o normal: `nova-spec`, intake, spec de dez blocos, portões, merge.

## Portão novo: `aprovar-prd`

A definição (PRFAQ/PRD) é uma decisão humana e tem portão próprio, no mesmo modelo dos demais:

| Portão (`--acao`) | Quando abrir | Comando depois do APROVO |
|---|---|---|
| `aprovar-prd` | PRFAQ e PRD gerados e sem pergunta que invalide a Big Idea | `python ash.py aprovar-prd <ID> --nome "<ASH_PO>"` |

Depois do APROVO do PRD, o squad-lead gera a story com `python ash.py nova-descoberta <ID> <slug>` (que materializa a story a partir do PRD) e segue o fluxo normal da spec.

## Regras de evidência (herdadas do método, adaptadas ao ASH)

- Toda afirmação apresentada como fato atual carrega a fonte (URL + data de acesso). Sem fonte, é inferência e vai marcada como tal.
- Número-chave relevante é corroborado por duas fontes independentes ou marcado `[fonte-única]`.
- Persona é compressão de evidência, nunca invenção: cada atributo é `[D] declarado`, `[W] web` ou `[I] inferido`. Persona majoritariamente `[I]` é hipótese, e é rotulada assim.
- Nenhum dado pessoal real em persona, exemplo ou pesquisa. Tudo fictício, como manda a governança.
- "Não sabemos ainda" é uma entrega válida: registre a pergunta em aberto com o teste que a resolve, em vez de preencher com achismo.

## Protótipo (fase de design, opcional)

Quando a iniciativa precisa de um protótipo navegável, o agente `designer-proto` o constrói em `portfolio/iniciativas/<slug>/prototipo/` (HTML/CSS/JS autocontido). O protótipo só é publicado na AWS (S3 privado + CloudFront) pelo portão `publicar-proto`, que é ato humano e toca AWS, no mesmo modelo do `bootstrap`. Nada de protótipo com dado pessoal; segue a base de segurança da infra (S3 privado via OAC, sem segredo no bundle).

## Artefatos em pasta visível

Tudo o que o humano precisa ler ou decidir fica em `portfolio/` (pasta visível na raiz), nunca só em pasta oculta. `.kiro/` é estado de máquina. A decisão humana aparece no chat, formatada para leitura; o arquivo em `portfolio/` é o registro.
