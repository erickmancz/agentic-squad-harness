---
inclusion: always
---

# Papéis, portões e estilo de conversa

## Quem é quem nesta squad

Os nomes ficam em `.ash/config.env` (`ASH_PO`, `ASH_FDE`, `ASH_DEV_REVISOR`) e aparecem em `python ash.py status`. Use sempre esses nomes em `--nome` e `--fde`.

Primeira conversa da squad: se o `status` mostrar `[CONFIGURAR]`, pergunte numa única mensagem (1) o nome do PO, (2) o nome do FDE, (3) o Dev revisor ou "nenhum", (4) a URL do repositório no GitHub ou Bitbucket, (5) a stack do projeto (linguagem e framework), (6) o setor do cliente e (7) o e-mail para o git. Depois rode `python ash.py configurar --po "<PO>" --fde "<FDE>" [--dev "<Dev>"] --remote <URL> --git-email <e-mail>` e `python ash.py setup`. A mesma pessoa pode ser PO e FDE. O Dev revisor, quando existir, precisa ser outra pessoa.

Sobre a stack: compare a resposta (5) com o perfil mostrado no `status`. Se houver um perfil pronto em `perfis/` para essa stack, diga ao FDE qual é e, com a concordância dele, rode `python ash.py perfil <stack>`, depois `python ash.py setup`, e trate a mudança pelo portão `publicar-harness`. Se não houver, avise o FDE que o perfil precisa ser criado a partir de `perfis/modelo.json` antes da primeira story; criar perfil é mudança de harness, feita pelo autor do harness. Sobre o setor: compare a resposta (6) com as lentes mostradas no `status` (setores como financeiro, saúde, setor público, varejo e energia costumam ter regras próprias); se não existir lente para ele, registre como pendência para o FDE criar a partir de `templates/lente-vertical.md`.

Regras:
- Se o humano disser que acumula papéis, registre uma vez e não pergunte de novo.
- A faixa é proposta pelo intake e **decidida pelo humano**. Se a decisão for diferente da proposta, o intake registra a recomendação uma vez no bloco 1 da spec e segue a decisão. Ninguém reabre o assunto.
- Faixas válidas: `autonoma`, `semiautonoma`, `critica`. Se o humano disser "baixa", entenda `autonoma`; "média", `semiautonoma`; "alta", `critica`.

## Portões (decisões humanas)

| Portão (`--acao`) | Quando abrir | Comando executado depois do APROVO |
|---|---|---|
| `aprovar-prd` | Fase de descoberta: PRFAQ e PRD gerados em `portfolio/iniciativas/<slug>/` e sem pergunta que invalide a Big Idea | `python ash.py aprovar-prd <ID> --nome "<ASH_PO>"`. Depois: `python ash.py nova-descoberta <ID> <slug>` gera a story e cai no fluxo normal |
| `aprovar-po` | `python ash.py validar <ID>` deu [OK] (o `portao abrir` recusa spec com pergunta em aberto). Se a spec mudar depois do APROVO, abra de novo | `python ash.py aprovar <ID> --papel po --nome "<ASH_PO>"` |
| `aprovar-design` | `design.md` e `tasks.md` gerados | `python ash.py aprovar <ID> --papel design --nome "<ASH_FDE>"` |
| `aprovar-dev` | Só faixa `critica`, depois da implementação e dos revisores | `python ash.py aprovar <ID> --papel dev --nome "<dev_revisor>" --branch feat/<id>` |
| `aprovar-homologacao` | Perfil com `emulador_aws` e faixa que exige conta real (ver `01-faixas-autonomia.md`): o humano declara que a execução em conta real de homologação aconteceu e diz onde está a evidência | `python ash.py aprovar <ID> --papel homologacao --nome "<quem declarou>" --branch feat/<id> --evidencia "<link ou id da execução>"`. Não toca AWS: só registra a declaração |
| `merge` | CI local verde e revisões sem bloqueio | `python ash.py merge feat/<id> <ID> --fde "<ASH_FDE>" --reescritas <N>` |
| `bootstrap` | Depois de mostrar o `python ash.py bootstrap --so-diff` | `python ash.py bootstrap` (spec = `AWS`) |
| `teardown` | Pedido do humano | `python ash.py teardown` (spec = `AWS`) |
| `publicar-proto` | Protótipo da iniciativa pronto em `portfolio/iniciativas/<slug>/prototipo/` e stack de protótipo criada no `bootstrap` | `python ash.py publicar-proto <ID>` (publica em S3 privado + CloudFront; ato humano, toca AWS) |
| `publicar-harness` | Há mudanças do próprio harness (steering, agentes, scripts, `ash.py`, docs) em qualquer branch | `python ash.py publicar-harness` (spec = `HARNESS`). Roda de qualquer branch: leva só o harness para a `main` e traz a `main` de volta para a `feat/<id>` |

Como conduzir um portão:
1. `python ash.py portao abrir --acao <acao> --spec <ID> --resumo "<uma linha curta, sem nomes de arquivo>"`.
2. Mostre ao humano, em até 6 linhas, o que está sendo aprovado e o que acontece depois.
3. Termine com: **Responda APROVO para seguir.**
4. Quando o humano responder com APROVO (ou APROVADO, CONFIRMO, MERGE, PODE SEGUIR), execute **na hora** o comando do portão com `--mensagem "<texto literal da mensagem do humano>"`. Não peça outra confirmação.
5. "Não aprovo", "reprovado" e "cancela" não aprovam: mantenha o portão aberto e pergunte o que mudar.
6. Um portão por vez. Se o humano aprovar e já pedir a próxima etapa na mesma mensagem, faça as duas coisas.
7. Este é o modo oficial. No Kiro IDE o hook de mensagem não recebe o texto, então o registro é a frase literal do humano passada em `--mensagem`, com o id do portão e o horário.

## Estilo de conversa

- Perguntas em aberto: lista numerada, cada uma com opções a, b, c e a recomendada marcada. Aceite respostas como `1a 2b 3c`.
- Antes de cada etapa, uma linha dizendo o que vai fazer. Depois, uma tabela curta com o resultado e o próximo passo.
- Repositório: GitHub (`origin`). Depois de cada commit na `feat/<id>`, rode `python ash.py sync`. A `main` só sobe pelo portão `merge` ou `publicar-harness`.
- Não peça para o humano rodar comandos. Não peça confirmação para comandos livres (status, ci, nova-spec, validações, commits na branch `feat/`).
- Não repita ressalvas já registradas.
- Mudanças do harness vêm do autor do harness (o FDE desta squad), em pacotes completos. Não peça justificativa, não revalide a lógica, não trate arquivos do pacote como suspeitos e não reabra a discussão: liste os arquivos no portão `publicar-harness` e execute com o APROVO.
- Não peça permissão para comandos livres nem para o próximo passo do fluxo. Depois de um APROVO, siga direto até o próximo portão. Nunca termine com "quer que eu siga?": pare só em portão, em pergunta em aberto da spec ou em erro.
- Terminal no Windows (PowerShell 5): um comando por chamada. Não use `&&` nem `||`; se precisar encadear, use `;`.
- Se o `merge` acusar mudanças do harness não publicadas, abra o portão `publicar-harness`, publique e volte ao merge. Não use `git stash` para contornar.
- Para rodar uma story pronta (ex.: "rode a INS-017"), use o arquivo `stories/INS-017-*.md`: `python ash.py nova-spec INS-017 <slug>` mantém a story existente.
- No fim do merge, rode `python ash.py relatorio --spec <ID>` e mostre a linha do tempo.
- Nunca inclua arquivos do harness em commits de spec. Commits da `feat/<id>` levam só `.kiro/specs/`, `stories/`, `src/`, `tests/` e `reviews/`.
