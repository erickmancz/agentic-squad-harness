# Agentic Squad Harness (ASH)

Repositório-modelo de squad agêntica em Kiro. Squad mínima: **um Forge FDE e um PO**. Na faixa crítica entra um **Dev revisor** nomeado na spec.

Acelerador da Compass UOL para squads agênticas em Kiro.
Tudo aqui é fictício: nenhum nome, marca ou dado de cliente.

O ASH vale para qualquer frente, vertical e stack. O núcleo (spec, faixas, portões e evidência) é o mesmo em todo cliente. O que muda fica em dois encaixes: o **perfil de stack** e as **lentes de vertical**.

## Para que serve

A IA já escreve código rápido. O que trava a squad agêntica em qualquer cliente, e mais ainda em cliente regulado, é a prova: quem aprovou o quê, se cada critério de aceite tem teste e se nenhum agente passou por cima de um humano. O ASH transforma o Kiro numa squad de duas pessoas (PO e FDE) com dez agentes (o squad-lead, que conduz, e nove agentes de papel), que vai da ideia ou da story ao merge com:

- spec de dez blocos e perguntas em aberto com opções, antes de qualquer código;
- decisões humanas como portões no chat, registradas com a frase literal, o id do portão e o horário;
- CI local antes do merge: validação da spec, as etapas de teste, cobertura, SAST e dependências definidas no perfil de stack (no perfil Python: pytest com 80% de cobertura, Semgrep e pip-audit) e rastreio de cada critério de aceite até um teste;
- `main` alterada só pelo portão de merge, com push para o GitHub ou Bitbucket.

## Como o ASH se adapta a cada cliente

| Camada | O que é | Muda por cliente? | Onde fica |
|---|---|---|---|
| Núcleo | Governança, spec de dez blocos, faixas de autonomia, portões, papéis, descoberta, evidência, métricas, LGPD | Não | `.kiro/steering/00` a `05`, `ash.py`, `scripts/` |
| Perfil de stack | Setup do projeto, comando de teste, etapas do CI (testes com cobertura, SAST, dependências) e onde ficam os testes | Sim, uma vez por projeto | `ash-perfil.json`, a partir de `perfis/` |
| Lente de vertical | Regras de domínio e regulatórias do setor e exemplos que entram na faixa crítica | Sim, quando o setor tem regras próprias | `.kiro/steering/*lente*.md`, a partir de `templates/lente-vertical.md` |
| Stack do cliente | Convenções de código e nomes do projeto | Sim | `.kiro/steering/03-stack-cliente.md` |

O `python ash.py status` mostra o perfil ativo, se ele foi testado e as lentes carregadas.

**Criar um perfil de stack.** Copie `perfis/modelo.json` para `perfis/<stack>.json`, preencha os comandos (as instruções estão no próprio arquivo), rode `python ash.py perfil <stack>` e `python ash.py setup`, confira `python ash.py ci` e publique pelo portão `publicar-harness`. Os agentes nunca chamam a ferramenta de teste direto: usam `python ash.py testar` e `python ash.py etapa <nome>`, por isso servem para qualquer linguagem.

**Criar uma lente de vertical.** Copie `templates/lente-vertical.md` para `.kiro/steering/1N-lente-<setor>.md`, preencha as regras com fonte (norma, órgão e data de consulta) e publique pelo portão `publicar-harness`. A lente só acrescenta regras; nunca remove uma regra do núcleo. A lente de serviços financeiros já vem pronta e serve de exemplo.

Orientação inicial por frente, a validar com cada uma:

| Frente | O que costuma pedir do ASH |
|---|---|
| Agentic AI | Perfil da stack da aplicação; fronteira de IA e dados no PRD da descoberta; lente do setor do cliente |
| Migration | Faixa crítica para a migração; perfil da stack de destino |
| Modernization | Faixa crítica para modernização de legado; perfil da stack de destino; specs que descrevem o sistema atual antes da mudança |
| Data | Perfil próprio, criado do modelo, com testes de dados e de qualidade no lugar dos testes de aplicação |
| Customer Experience | Perfil da stack das integrações; lente do setor do cliente |

## Primeiros 10 minutos

1. Pré-requisitos na máquina: Python 3.12 (`python` no PATH, usado pelo harness em qualquer stack), Git, Kiro e as ferramentas da stack do projeto. AWS CLI, Node.js e CDK só se for ligar as métricas na AWS.
2. Crie um repositório vazio e privado no GitHub (ou Bitbucket).
3. Extraia o zip numa pasta e abra a pasta no Kiro.
4. No chat, escolha o agente `squad-lead` e diga: `Vamos começar`.
5. Ele pergunta o PO, o FDE, o Dev revisor (ou nenhum), a URL do repositório e a stack do projeto, e configura tudo sozinho. Se a stack não tiver perfil pronto ou o setor tiver regras sem lente, ele avisa o FDE antes da primeira story.
6. Cole a story do PO ou diga `rode a INS-017` para usar a story de exemplo (`stories/INS-017-resumo-apolice.md`).

Daí em diante você só responde às perguntas da spec e aos portões com APROVO.

## Fase opcional de descoberta (antes da story)

Quando o PO ainda não tem a story pronta, o ASH tem uma fase de descoberta e definição de produto, inspirada no Working Backwards (steering `05-descoberta-produto.md`). O agente `product-lead` conduz cinco etapas (intenção, estado atual, invenção, PRFAQ/PRD e handoff), cada uma gerando artefato em `portfolio/iniciativas/<slug>/` e terminando numa decisão humana. O PRFAQ/PRD passa pela crítica adversarial dos revisores e é aprovado no portão `aprovar-prd`. Depois, `python ash.py nova-descoberta <ID> <slug>` materializa a story e o fluxo segue normal. Protótipo navegável é opcional (`designer-proto`), publicado em S3+CloudFront pelo portão `publicar-proto`. A stack do protótipo tem um WAF com limite de requisições por IP, que cobra mensalidade fixa enquanto a stack existir (ver a estimativa de custo). Se o PO já tem a story, pule a descoberta e vá direto ao fluxo da spec.

## Como o trabalho flui

Os humanos **só conversam no chat do Kiro, com o agente `squad-lead`**. Ninguém digita comandos.

```
(descoberta opcional) ideia ─► product-lead ─► PRFAQ + PRD ─► PORTÃO aprovar-prd ─► story
                       │
PO cola a story ─► squad-lead ─► intake-spec gera a spec de 10 blocos
                       │            └─ perguntas em aberto com opções (1a 2b 3c)
                       │
PO responde no chat ─► intake-spec aplica ─► PORTÃO aprovar-po ─► humano: APROVO
                       │
planejador gera design.md + tasks.md ─► PORTÃO aprovar-design ─► humano: APROVO
                       │
implementador (código + testes) ─► 4 revisores (reviews/) ─► python ash.py ci
                       │
(faixa crítica: PORTÃO aprovar-dev ─► Dev revisor: APROVO)
                       │
PORTÃO merge ─► humano: APROVO ─► merge na main ─► métricas e backup no S3
```

## Portões: como o APROVO do chat vira evidência

1. O squad-lead abre o portão: `python ash.py portao abrir --acao <acao> --spec <ID> --resumo "..."`.
2. Ele mostra a decisão no chat e pede: "Responda APROVO para seguir".
3. Você responde APROVO.
4. Ele executa o comando do portão com `--mensagem "<sua frase literal>"`. O comando só aceita se houver portão aberto para a mesma ação e spec e se a frase for uma aprovação. Fica registrado em `.ash/approvals/<ID>.json` e nos eventos: canal `chat-declarado`, sua frase, id do portão e horário.

Por que não há captura automática: no Kiro IDE (Windows, 21/10/2026) o hook `UserPromptSubmit` dispara, mas recebe `"prompt": ""`, então o texto da mensagem não chega a scripts.

## Comandos que o squad-lead usa (`python ash.py ...`)

| Comando | Tipo |
|---|---|
| `status`, `configurar`, `setup`, `sync`, `validar ID`, `relatorio [--spec ID]`, `nova-spec ID SLUG`, `ci`, `pendencias`, `metricas`, `backup`, `restaurar` | Livres |
| `testar`, `etapa NOME` | Livres: testes rápidos e uma etapa isolada do CI, conforme o perfil de stack |
| `testar-harness` | Livre para o squad-lead: testes do próprio ASH, com a `.venv-tools`, em qualquer stack. Agentes de papel não precisam rodá-lo |
| `testar-harness --integracao` | Livre para o squad-lead e para o autor do harness: testes de integração do próprio ASH contra o AWS Emulator (`tests_harness_integracao/`). Fora do CI de qualquer projeto |
| `testar-harness --auditoria` | Livre para o squad-lead e para o autor do harness: audita o `requirements-tools.txt` com o `pip-audit` e os aceites de risco (ver "Riscos aceitos nas ferramentas do harness"). Precisa de rede; fora do CI de qualquer projeto |
| `emulador iniciar \| parar \| status \| reset` | Livres, só para o squad-lead: AWS Emulator local (ver "Testes contra o AWS Emulator"). `etapa integracao-aws` também roda com o emulador de pé |
| `aprovar ID --papel homologacao --nome NOME --branch feat/<id> --evidencia "..."` | Portão `aprovar-homologacao`: registra a declaração de que a execução em conta real de homologação aconteceu. Não toca AWS |
| `perfil` | Livre para o squad-lead: mostra o perfil ativo e os disponíveis (agentes de papel não rodam `perfil`) |
| `perfil NOME` | Mudança de harness: ativa `perfis/NOME.json`; publicar pelo portão `publicar-harness` |
| `nova-descoberta ID SLUG` | Livre, usado depois do portão `aprovar-prd` para gerar a story a partir do PRD |
| `aprovar-prd ID --nome NOME` | Portão `aprovar-prd` (fase de descoberta) |
| `publicar-proto ID` | Portão `publicar-proto` (toca AWS) |
| `publicar-harness` | Portão `publicar-harness` (mudanças do próprio harness) |
| `portao abrir --acao ... --spec ... --resumo ...`, `portao status` | Livres (só o squad-lead) |
| `aprovar ID --papel po --nome NOME` | Portão `aprovar-po` |
| `aprovar ID --papel design --nome NOME` | Portão `aprovar-design` |
| `aprovar ID --papel dev --nome NOME --branch feat/<id>` | Portão `aprovar-dev` (faixa crítica) |
| `merge feat/<id> ID --fde NOME --reescritas N` | Portão `merge` |
| `bootstrap --so-diff`, depois `bootstrap` | Portão `bootstrap` |
| `teardown` | Portão `teardown` |

Variáveis do CI: `ASH_COBERTURA_MIN` sobrescreve a cobertura mínima do perfil numa execução. `ASH_PULAR` pula etapas do perfil (o CI sai com código 3 e o merge recusa); `spec-gate` e `rastreio` são do núcleo e não podem ser pulados. `ASH_ATOR` define o ator do evento `ci_executado`: o padrão é `agente` (o squad-lead roda o CI) e `humano` serve para execução manual.

Testes do próprio harness: `tests_harness/` (perfil, certificados, `ASH_PULAR` do núcleo, ator do CI e rastreio com testes de outra linguagem). Rodam por `python ash.py testar-harness`, com o pytest da `.venv-tools`, e por isso valem para qualquer stack. Todo perfil leva a etapa `harness` (`{python} ash.py testar-harness`), então os testes do ASH entram no CI de qualquer projeto. Ficam fora da cobertura da app de exemplo e do rastreio, que só varre `tests/`.

## Versionamento

- Repositório da squad em `ASH_GIT_REMOTE` (`.ash/config.env`), preenchido pelo `configurar`. Recomendado: repositório **privado**.
- Quem roda git é o Kiro: o squad-lead faz commit na `feat/<id>` e envia com `python ash.py sync`. A `main` só sobe pelo portão `merge` (merge local + push) ou pelo portão `publicar-harness` (mudanças do próprio harness).
- Nenhum agente roda `git push` direto: o push passa pelo `ash.py`, que recusa enviar a `main` fora dos portões.
- Proteção local: hooks em `.githooks/` bloqueiam commit e merge na `main` fora do `ash.py`. Limite honesto: hook local pode ser contornado com `--no-verify`, e a `main` do GitHub ainda aceita push direto de quem tem acesso. Uma regra de proteção no GitHub exigindo PR travaria o fluxo atual, que faz push direto da `main` pelo portão. Em macOS e Linux o Git só executa hook com permissão de execução; por isso o índice guarda os dois hooks como `100755`, o `python ash.py setup` soma os bits de execução a todo arquivo de `.githooks/` (e os registra assim no commit inicial), e o `python ash.py status` avisa quando algum hook estiver sem permissão. No Windows nada disso muda.
- Backup opcional em S3 (`git bundle`), ativo quando `ASH_CODE_BUCKET` estiver preenchido. Para trocar de plataforma (GitHub ou Bitbucket), troque o `ASH_GIT_REMOTE` e rode `python ash.py setup`.
- Login no GitHub: o Git da máquina usa o login já salvo (no Windows, Git Credential Manager). No primeiro push pode abrir o navegador para entrar.

## Pré-requisitos

Para os testes de integração contra o AWS Emulator (só projetos que chamam AWS): Linux com o pacote nativo, Windows com WSL2 (sem Docker) ou com um runtime de contêiner, ou macOS com um runtime de contêiner (ver "Testes contra o AWS Emulator"). Windows, macOS ou Linux; Python 3.12 no PATH como `python` (o harness roda em Python em qualquer stack) (no Windows, instalador do python.org com "Add python.exe to PATH" e os atalhos da Microsoft Store desligados); Git; AWS CLI v2 com credenciais da conta AWS da squad; Node.js e `npm install -g aws-cdk` (só para o bootstrap); Kiro; e as ferramentas que o perfil de stack ativo chama (no perfil Python, nada além do próprio Python).

Tudo roda com `python`, sem bash: funciona no PowerShell, no Git Bash, no macOS e no Linux.

## Métricas

`python ash.py relatorio` mostra, sem AWS, a linha do tempo de cada spec (criada, aprovada pelo PO, design aprovado, merge), o tempo da spec ao merge, as execuções do CI e o canal das decisões. Com o portão `bootstrap`, os mesmos eventos vão para o S3 e um relatório semanal é gerado na AWS. O `bootstrap` cria três stacks: código (backup), métricas e protótipo. O `teardown` remove as stacks de métricas e de protótipo e mantém os buckets de código e de protótipo. Créditos do Kiro só aparecem na tela do chat ("Est. Credits Used" por turno).

## Testes contra o AWS Emulator

O AWS Emulator é um emulador local das APIs da AWS (código aberto da própria AWS, sem taxa adicional e sem conta AWS). O ASH o usa em dois lugares, sem nunca tocar conta real:

| Uso | Para quem | Como roda | Faz parte do CI? |
|---|---|---|---|
| Testes de integração **do próprio ASH** (as Lambdas de `infra/lambdas/` e o backup em S3), em `tests_harness_integracao/` | O autor do harness | `python ash.py testar-harness --integracao` | **Não.** Nenhum projeto precisa de emulador por causa disso |
| Testes de integração **da aplicação do cliente**, em `tests/integracao_aws/`, quando o projeto usa serviços AWS | A squad do projeto | `python ash.py etapa integracao-aws` (ou `python ash.py ci`), só no perfil `python-aws` | Sim, **só** no perfil `python-aws` |

### Você precisa do emulador?

- **Seu projeto não usa AWS:** não. Fique no perfil `python` (o padrão): o `ci` completo sai com código 0 sem emulador, Docker ou WSL, e nenhuma faixa exige o papel `homologacao` por causa do emulador. Nada nesta seção é necessário.
- **Seu projeto usa serviços AWS:** sim, para a etapa `integracao-aws`. Ative o perfil `python-aws` (próxima seção).
- **Você mantém o ASH (autor do harness):** rode `python ash.py testar-harness --integracao` antes do `publicar-harness` quando a mudança tocar o emulador (`scripts/emulador.py`, o comando `emulador`), o CI por etapas, o backup, as Lambdas de `infra/` ou a versão do emulador. O `publicar-harness` avisa quando os arquivos mudados estão nessa lista; o aviso não bloqueia. Não é preciso rodar em mudanças só de documentação.

### Se o seu projeto usa AWS: perfil `python-aws`

1. Ative: `python ash.py perfil python-aws`, `python ash.py setup` e publique a mudança pelo portão `publicar-harness` (trocar de perfil é mudança de harness). O perfil nasce marcado como não testado; depois de rodar o `ci` com o emulador de pé no projeto, mude `testado` para `true`.
2. Declare o `boto3`, com versão exata (`boto3==X.Y.Z`), no **`requirements.txt` do próprio projeto**. É nele que a etapa `dependencias` (pip-audit) olha; o `setup` do perfil não instala `boto3` por fora. O `python ash.py perfil python-aws` e o `ci` avisam se o perfil tem `emulador_aws` e o `requirements.txt` não declara o `boto3` com versão exata.
3. Copie `templates/tests-integracao-aws/` para `tests/integracao_aws/` e troque o teste de exemplo pelos do projeto, que chamam o código do projeto. Eles citam `<ID da spec> CA-NN` como os demais, e o rastreio os conta. A etapa `testes` ignora essa pasta (`--ignore=tests/integracao_aws`), para não rodar sem emulador.
4. Em `perfis/python-aws.json`, ajuste `emulador_aws.servicos` para os serviços que o projeto usa e preencha a fidelidade de cada um (nota "k de n" da página de releases da versão fixada, com fonte e data).
5. A regra de fidelidade por faixa e o papel `homologacao` (seção "Regra de fidelidade por faixa", abaixo) valem para esse perfil, e só para ele.

Todas as afirmações sobre o emulador, o WSL e o Docker, com fonte e data de consulta, e o que ainda não foi testado, estão em `docs/spec-ash-v4.md`, seção 5.4. Regras para os agentes: `.kiro/steering/06-emulador-aws.md`.

### Pré-requisitos por sistema

| Sistema | O que você precisa | Modo |
|---|---|---|
| Linux (x86_64 ou aarch64, glibc 2.17 ou superior) | O pacote nativo da AWS, RPM ou DEB. Exemplo para DEB: `curl -fsSLo aws-emulator.deb https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/<latest ou a versão do perfil>/aws-emulator_amd64.deb` e `sudo apt-get install -y ./aws-emulator.deb` (o nome exato por versão está no bloco `emulador_aws` do perfil). Quem instala é você; o ASH nunca roda `sudo` | `linux` |
| Windows com WSL2, sem Docker | O WSL2 com uma distribuição própria (`wsl --list --online` mostra as disponíveis; `wsl --install <distribuição>` instala) e o pacote nativo da AWS instalado dentro dela, como na linha do Linux. As distribuições internas de runtimes de contêiner (por exemplo, a do Docker Desktop) não valem. Usa o encaminhamento de `localhost` do WSL2, que vem ligado por padrão | `wsl` |
| Windows ou macOS com runtime de contêiner | Docker ou Podman instalado e **rodando** (a AWS não publica imagem pronta: o ASH constrói a imagem na primeira vez, com `infra/emulador/Dockerfile`, que baixa o pacote RPM, cerca de 170 MB). Se o CLI for o Podman, defina `ASH_CONTAINER_CLI=podman` | `container` |
| macOS | Só o modo `container`: o emulador roda nativamente apenas em Linux | `container` |

Fora do emulador, o `ash.py` só precisa do Python 3.12 e do Git. O AWS CLI é usado só pelo teste de backup (`test_backup_s3.py`), que é pulado se ele não existir.

### Nota de licença do Docker

O Docker Desktop é gratuito para uso pessoal, educação, projetos open source não comerciais e empresas com menos de 250 funcionários e menos de US$ 10 milhões de receita anual. Fora disso (uso profissional em organizações maiores, entidades governamentais e uso comercial além desses limites), exige assinatura paga. Fonte: https://docs.docker.com/subscription/desktop-license/, consultada em 13/11/2026; o Docker Engine e outros projetos open source não mudam. Avaliar o enquadramento e contratar é responsabilidade de cada cliente ou usuário. O ASH funciona sem Docker Desktop, pelos modos `linux` e `wsl`, ou com Podman, e não instala nenhum runtime.

### Primeira execução

1. Prepare o ambiente: `python ash.py setup`. (O `boto3` dos testes do harness vem na `.venv-tools`; o do projeto, se ele usa AWS, vem do `requirements.txt` dele.)
2. Veja o que sua máquina consegue usar: `python ash.py emulador status`. A linha "Emulador AWS" mostra se está de pé ou parado; a lista de modos diz, para cada um, se está disponível e o que falta.
3. Se nenhum modo estiver disponível, instale um da tabela acima (a decisão e a licença são suas) e repita o passo 2. Se a detecção automática escolher um modo que você não quer, defina `ASH_EMULADOR_MODO` em `.ash/config.env`.
4. Suba o emulador: `python ash.py emulador iniciar`. No modo `container`, a primeira vez constrói a imagem.
5. Rode a integração: no perfil `python-aws`, `python ash.py etapa integracao-aws` (ou `python ash.py ci`); para os testes do próprio ASH, `python ash.py testar-harness --integracao`. Se o perfil ativo não declara `emulador_aws`, o `emulador iniciar` usa a versão fixada dos testes do harness (`tests_harness_integracao/emulador.json`) e avisa.
6. Quando terminar: `python ash.py emulador parar`.

### Modos e variáveis (`.ash/config.env`; cada uma também pode vir do ambiente do processo)

| Variável | O que faz | Padrão |
|---|---|---|
| `ASH_EMULADOR_MODO` | `linux`, `wsl` ou `container` | vazio: detecção automática, nesta ordem: linux, wsl, container |
| `ASH_EMULADOR_WSL_DISTRO` | Distribuição WSL2 que hospeda o emulador no modo `wsl` | vazio: a primeira distribuição WSL2 própria |
| `ASH_CONTAINER_CLI` | `docker` ou `podman` | vazio: o primeiro que responder |
| `ASH_EMULADOR_PORTA` | Porta HTTPS em `127.0.0.1` | `9297` |
| `ASH_EMULADOR_IDLE` | Segundos sem chamadas de API até o emulador se encerrar sozinho | `1800` |
| `ASH_EMULADOR_AUTO` | `sim`: o `ci` e a etapa `integracao-aws` sobem o emulador e o param ao final | vazio: a etapa falha com mensagem clara se o emulador não estiver de pé |

Outros pontos de uso:
- **Reiniciar com estado limpo:** `python ash.py emulador reset` (parar e iniciar). O emulador guarda tudo em memória e não tem rota de reset, então reiniciar é o reset; as chaves e o certificado mudam a cada início (os caminhos dos arquivos não mudam).
- **Log do emulador:** `.ash/emulador/emulador.log` (modos `linux` e `wsl`; no modo `container`, `docker logs ash-emulador-<porta>` ou `podman logs ...`). Não contém as chaves.
- **Trocar a versão do emulador:** altere `versao` no bloco `emulador_aws` do perfil do projeto (`perfis/python-aws.json` e `ash-perfil.json`) e, para os testes do harness, em `tests_harness_integracao/emulador.json`. A documentação da AWS recomenda fixar a versão porque correções de fidelidade podem mudar o resultado de testes. No modo `container` o ASH constrói uma imagem nova para a nova versão; nos modos `linux` e `wsl`, reinstale o pacote da versão escolhida. A lista de versões publicadas está em `https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/versions.json`.
- **Preencher a fidelidade dos serviços:** use a nota "k de n" de cada serviço na página de releases da versão fixada (https://github.com/aws/aws-emulator/releases) e registre no perfil, com a fonte e a data de consulta; até lá a fidelidade fica `null` e conta como abaixo do corte.

### Ciclo de vida: nada inicia sozinho

- O emulador só sobe por `python ash.py emulador iniciar` (ou pelo `ci` quando `ASH_EMULADOR_AUTO=sim`). O ASH nunca o instala como serviço (systemd, init ou serviço do Windows), nunca cria tarefa agendada, atalho de inicialização ou início automático com o Windows ou com o WSL, e nunca altera o seu `.wslconfig` (em especial, nunca define `vmIdleTimeout=-1`).
- Todo início usa `--idle-timeout` (`ASH_EMULADOR_IDLE`): sem chamadas de API, o emulador se encerra sozinho. No modo `wsl`, o WSL2 desliga a distribuição e a VM depois do próprio tempo de inatividade (padrões documentados: 15 s para a distribuição e 60 s para a VM).
- Se foi o `ci` ou a etapa que subiu o emulador, o próprio comando o para ao final, com sucesso ou falha. Se o emulador já estava de pé antes, ele fica como estava.
- `python ash.py status` mostra a linha "Emulador AWS": de pé ou parado, o modo, há quanto tempo e depois de quanto tempo sem uso ele se encerra.

Conferir e encerrar tudo manualmente:
1. `python ash.py emulador parar` (para o emulador do ASH e apaga o estado local).
2. Modo `container`: `docker ps` (ou `podman ps`) não deve listar `ash-emulador-<porta>`.
3. Modo `wsl`: `wsl --list --running` mostra se o WSL ficou ligado; `wsl --terminate <distribuição>` encerra só ela; `wsl --shutdown` encerra todas as distribuições e a VM, como último recurso.
4. Modo `linux`: nenhum processo `aws-emulator` deve restar.

### Como saber que você não está na conta real

- Os testes só recebem o endpoint e as credenciais no ambiente do processo filho que o `ash.py` monta; nada vai para o seu ambiente, para `~/.aws/config` nem para suas credenciais reais. As variáveis de credencial real (`AWS_ACCESS_KEY_ID`, `AWS_PROFILE`, token de sessão e semelhantes) são removidas desse ambiente.
- Antes de qualquer chamada, o `ash.py` prova que o endpoint é `https://127.0.0.1:<porta>`, que o certificado do emulador responde ao health check e que o ID da chave começa com `EMULATOR` (sem imprimi-la). O `conftest.py` de `tests/integracao_aws/` (cópia do esqueleto) e o de `tests_harness_integracao/` conferem de novo, com o `sts get-caller-identity`: a conta tem de ser `000000000000` e o usuário `emulator`. Se algo falhar, a execução aborta antes de criar recurso.
- As chaves mudam a cada início e ficam só em `.ash/emulador/` (modos `linux` e `container`) ou dentro da distribuição WSL (modo `wsl`), nunca no git.

### Se a etapa `integracao-aws` falhar

| Mensagem ou sintoma | O que fazer |
|---|---|
| "Emulador AWS não está de pé" | `python ash.py emulador iniciar` (ou `ASH_EMULADOR_AUTO=sim`) e repetir |
| "Nenhum modo do emulador está disponível" | Instale um modo da tabela de pré-requisitos; `python ash.py emulador status` explica o que falta em cada um |
| "docker instalado, mas o daemon ou a máquina virtual não responde" | Inicie o runtime de contêiner (ou use outro modo) |
| "A porta 9297 já está em uso" | Defina outra `ASH_EMULADOR_PORTA` |
| Abort "endpoint não local" ou "credenciais não são as do emulador" | É a proteção funcionando: não force. Rode por `python ash.py etapa integracao-aws` (ou `testar-harness --integracao`) e confira se há emulador de outra origem na porta |
| Teste falha com HTTP 501 `NotImplemented` | O emulador ainda não implementa a operação. É lacuna do emulador, não motivo para usar a AWS: registre na spec |
| Sem emulador possível e o CI precisa seguir | `ASH_PULAR=integracao-aws` pula a etapa, mas o CI sai com código 3 e o merge recusa |

### Regra de fidelidade por faixa

O emulador não replica a AWS por inteiro (cada serviço tem uma nota de fidelidade) e não avalia políticas IAM. Por isso, quando o perfil declara `emulador_aws` (o `python-aws`; o `python` padrão não declara e não tem essa exigência): faixa `autonoma` exige a etapa `integracao-aws` verde; `semiautonoma` exige o emulador verde e, para serviços do perfil abaixo do corte de fidelidade (ou com fidelidade ainda `null`), também a execução em conta real; `critica` exige emulador verde e execução em conta real de homologação, sempre. A homologação em conta real é feita fora do ASH e registrada pelo portão `aprovar-homologacao` (`python ash.py aprovar ID --papel homologacao --nome NOME --branch feat/<id> --evidencia "..."`), que só guarda a declaração e a evidência. O `merge` recusa sem ela. Detalhes: `.kiro/steering/01-faixas-autonomia.md`.

### Limites do emulador (resumo; fontes na spec)

Não avalia políticas IAM nem as baseadas em recurso e nunca serve para testar segurança; uma conta (`000000000000`) e uma região por emulador; recursos só em memória (parar ou reiniciar apaga tudo, e não existe rota de reset); fidelidade varia por serviço e operação não implementada devolve HTTP 501; não foi testado pela AWS para uso longo nem para teste de carga; código de função Lambda executado pelo emulador roda sem isolamento (por isso os testes chamam os handlers em processo e nunca usam `lambda invoke`); suporte a CloudFormation e a CDK não está confirmado, então não há `bootstrap` contra o emulador; telemetria anônima vem ligada por padrão e o ASH a desliga em todo início.

### Dados por máquina

O template não leva dado de nenhuma pessoa nem de conta. Credenciais do emulador, login de runtime de contêiner, nomes e e-mails da squad são configurados em cada máquina, na replicação para o cliente, e ficam fora do git (`.ash/config.env` e `.ash/emulador/`).

## Riscos aceitos nas ferramentas do harness

O harness tem ferramentas próprias (Semgrep, pip-audit, pytest e boto3), instaladas na `.venv-tools` a partir do `requirements-tools.txt`. A etapa `dependencias` do CI audita só o `requirements.txt` **do projeto**; as ferramentas do harness são auditadas à parte, por `python ash.py testar-harness --auditoria`. Esse comando precisa de rede, é do autor do harness e **nunca roda no CI de um projeto**.

**O que está aceito hoje (decisão de 13/11/2026).** Seis vulnerabilidades conhecidas em duas dependências transitivas do Semgrep 1.181.0: `mcp` 1.29.0 (CVE-2026-59951, CVE-2026-116684, CVE-2026-116685 e CVE-2026-116686) e `opentelemetry-api` 1.37.0 (CVE-2026-114603 e CVE-2026-126360).

**Por quê.** Nenhuma versão do Semgrep até a 1.185.0 (10/11/2026) declara faixas que admitam as versões corrigidas (`mcp` 1.30.0 ou superior; `opentelemetry-api` 1.45.2 ou superior), então atualizar o Semgrep não corrige. Forçar as versões corrigidas funciona, mas deixa o `pip check` falhando, e foi descartado. O ASH só roda `semgrep scan` em arquivos locais, com `--metrics=off`, sem iniciar servidor MCP nem ler cabeçalhos de trace de terceiros; isso é indício de baixa exposição, não prova (os caminhos internos do Semgrep não foram verificados). Fontes, ensaio e limites: `docs/spec-ash-v4.md`, decisão D19 e lacuna L12. Cada aceite cita a sua fonte em `tests_harness/auditoria_ferramentas.json`.

**Até quando.** Cada aceite tem data da decisão e data de revisão, no máximo 90 dias depois (esta, até 11/02/2027). Prorrogar exige uma nova decisão do autor do harness, com nova data; o arquivo recusa prazo maior. Depois da data de revisão, `testar-harness --auditoria` sai com código 1 e o `publicar-harness` avisa.

**O que o `--auditoria` mostra.** Três listas: CVEs novos (sem aceite), aceites vencidos (data de revisão passada) e aceites que podem sair (a vulnerabilidade não aparece mais, ou o Semgrep mais recente já declara faixas que admitem a versão corrigida). Sai com código 1 se houver CVE novo ou aceite vencido, 2 se não conseguiu auditar (por exemplo, sem rede) e 0 nos demais casos.

**Quem decide.** O autor do harness (o arquivo guarda o papel, nunca nome de pessoa). Nenhum agente cria nem prorroga aceite. O aceite é válido para o template; **cada cliente revalida com o seu time de segurança**.

**O que o cliente pode fazer.** Substituir a etapa `sast` do perfil por outra ferramenta de SAST aprovada pelo time de segurança dele: troque o comando da etapa `sast` em `perfis/<stack>.json` e `ash-perfil.json`, mantendo o nome `sast`, porque o revisor de vulnerabilidades chama `python ash.py etapa sast`. Quem deixar de usar o Semgrep pode removê-lo do `requirements-tools.txt` e apagar os aceites dele do arquivo.

**Checklist do autor do harness antes do `publicar-harness`.**
1. `python ash.py testar-harness` (sempre).
2. `python ash.py testar-harness --integracao`, se a mudança tocar o emulador, o CI por etapas, o backup, as Lambdas de `infra/` ou a versão do emulador (precisa de um modo do emulador disponível).
3. `python ash.py testar-harness --auditoria`, se a mudança tocar `requirements-tools.txt`, o arquivo de aceites ou as ferramentas do harness, ou se o `publicar-harness` avisar de aceite vencido.

## Redes corporativas e certificados

Notebooks corporativos às vezes trazem `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `AWS_CA_BUNDLE` ou `NODE_EXTRA_CA_CERTS` definidas no escopo de máquina, apontando para um arquivo `.pem` que ainda não foi instalado. Nesse caso pip, pip-audit, AWS CLI e Node falham por TLS, e o CI quebra na etapa `dependencias`.

O `ash.py` trata isso sozinho: ao iniciar, ignora no próprio processo (e nos comandos que ele chama) as variáveis de certificado que apontam para arquivo inexistente, e mostra quais foram ignoradas no `python ash.py status`. Variável que aponta para arquivo existente é tratada como certificado corporativo legítimo e não é tocada. Nada muda no registro do sistema.

Se a rede do cliente faz inspeção TLS, o caminho certo é instalar o `.pem` corporativo no caminho que as variáveis indicam. Sem ele, nenhuma ferramenta consegue sair para a internet, com ou sem o ASH.

No PowerShell 5, não use `2>&1` ao rodar o CI: o redirecionamento transforma a saída de erro em falha e devolve código 1 mesmo com "CI LOCAL: OK".

## Limites conhecidos

- No Kiro, permissões e hooks do squad-lead valem também para os subagentes. Por isso a regra "supervisor não produz" depende do prompt do squad-lead e da conferência humana nos portões; não há trava técnica só dele.
- O hook de mensagem do Kiro não entrega o texto ao script. O registro do APROVO é a frase literal passada pelo squad-lead em `--mensagem`, sempre com portão aberto.
- O Kiro processa as requisições fora do Brasil (perfil enterprise em us-east-1 ou Frankfurt). Para qualquer cliente com exigência de residência de dado (serviços financeiros, saúde, setor público e outros), isso é tema de LGPD a tratar antes do piloto.
- Só o perfil de stack `python` foi testado de ponta a ponta. Outros perfis saem do `perfis/modelo.json` e precisam do CI verde antes da primeira story. As regras locais de `.semgrep/` são de Python; outra linguagem precisa de regras próprias ou de outra ferramenta na etapa `sast`.
- Só a lente de serviços financeiros vem pronta. Outros setores usam o modelo de lente, com fonte para cada regra regulatória.
- Testado de ponta a ponta no Kiro IDE no Windows (story INS-016, 22/10/2026).
- A faixa crítica rodou no Kiro na INS-018 (23/10/2026), com o portão `aprovar-dev` e o merge. A separação de funções com duas pessoas reais ainda não foi testada.
- A checagem de separação de funções compara o texto dos nomes. Dois nomes diferentes da mesma pessoa passam; quem garante a separação de verdade é a configuração da squad e a conferência humana.
- Métricas na AWS ainda não foram testadas no Kiro. A fase de descoberta (`product-lead`, `aprovar-prd`, `nova-descoberta`, `publicar-proto`) não tem registro de execução neste pacote.
- O WAF do protótipo tem escopo CloudFront, e a AWS exige criar esse tipo de WAF em us-east-1. As stacks rodam em us-east-1 por padrão. Se a squad trocar a região para sa-east-1, a `AshProtoStack` falha no deploy até ser separada e mantida em us-east-1.

## Exemplos incluídos

O repositório traz uma app fictícia de seguros (`src/endosso/`) com três rodadas completas como referência. O setor e a linguagem da app são só ilustração do fluxo; o ASH não depende deles. As rodadas: INS-014 (aumento de cobertura, faixa crítica), INS-016 (histórico de endossos, faixa semiautônoma) e INS-018 (simulação de aumento, faixa crítica). As três têm spec de dez blocos, design, tasks e testes. A INS-016 e a INS-018 também têm as quatro revisões em `reviews/`; a INS-014 é anterior aos revisores e não tem revisão. Os registros de aprovação e os eventos dessas rodadas não vêm no pacote: a squad começa com `.ash/` limpo. A INS-017 é uma story de demonstração, não implementada no pacote: serve para a primeira rodada da squad.

## Documentos

- Spec do acelerador: `docs/spec-ash-v4.md`
- Perfis de stack: `perfis/` (`python.json` pronto e `modelo.json` com instruções); perfil ativo em `ash-perfil.json`
- Modelo de lente de vertical: `templates/lente-vertical.md`; exemplo pronto em `.kiro/steering/10-lente-servicos-financeiros.md`
- Estimativa de custo: `docs/estimativa-custo-sa-east-1.md`
- Fase de descoberta: `.kiro/steering/05-descoberta-produto.md`, com os modelos `templates/prfaq.md` e `templates/prd.md`
- Portões e estilo de conversa: `.kiro/steering/04-papeis-e-portoes.md`
- Testes contra o AWS Emulator: seção "Testes contra o AWS Emulator" deste README, regras dos agentes em `.kiro/steering/06-emulador-aws.md` e fontes, decisões, AC e lacunas em `docs/spec-ash-v4.md`, seção 5.4
