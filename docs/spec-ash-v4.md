# Spec · Agentic Squad Harness (ASH) v4

Acelerador da Compass UOL para squads agênticas em Kiro, independente de frente, vertical e stack
Data: 22/10/2026 · Atualização de 13/11/2026 (testes do próprio harness em `tests_harness/` com o comando `testar-harness` e testes de integração contra o AWS Emulator, seção 5.4; nenhum modo do emulador foi executado de ponta a ponta, ver as lacunas) · Status: v4.9 (acelerador: configuração da squad no chat, relatório local, story INS-017; ponta a ponta testado no Kiro com a INS-016),  aprovação pelo chat com portões; testado em Linux; AWS ainda não implantada · Atualização de 13/11/2026: núcleo agnóstico com perfil de stack e lentes de vertical; perfil `python` testado, demais perfis a criar · Atualização de 09/11/2026: fase de descoberta (Working Backwards), agentes `product-lead` e `designer-proto`, portões `aprovar-prd` e `publicar-proto` e stack de protótipo, ainda sem registro de teste no Kiro

**O que mudou na v4 (depois do teste no Kiro em 20/10/2026):** no teste, o agente pedia ao humano para rodar comandos no terminal, porque a aprovação dependia de um prompt interativo e o agente de conversa era um agente de papel bloqueado. Na v4: (1) os humanos só conversam com o novo agente `squad-lead`, que executa tudo; (2) a aprovação é a resposta APROVO no chat a um **portão** aberto pelo squad-lead, capturada pelo hook `UserPromptSubmit` a partir da mensagem do humano; (3) entrou o agente `planejador` para `design.md` e `tasks.md`; (4) o `orquestrador` saiu, substituído pelo squad-lead; (5) papéis acumulados e decisão de faixa ficaram explícitos no steering `04-papeis-e-portoes.md`, para o agente registrar a recomendação uma vez e seguir a decisão humana.

**O que mudou depois da v4.9 (pacote de 09/11/2026):** (1) entrou uma fase opcional de descoberta e definição de produto antes da story, inspirada no Working Backwards e alinhada ao SDLC da AWS, no steering `05-descoberta-produto.md`; (2) o agente `product-lead` conduz as cinco etapas (intenção, estado atual, invenção, PRFAQ/PRD e handoff) e escreve só em `portfolio/`; (3) o agente `designer-proto` monta um protótipo navegável opcional em `portfolio/iniciativas/<slug>/prototipo/`; (4) novos portões `aprovar-prd` e `publicar-proto`, e o comando livre `nova-descoberta`, que gera a story a partir do PRD aprovado; (5) nova stack `AshProtoStack` (S3 privado, CloudFront com OAC e WAF) criada no `bootstrap`; (6) modelos `templates/prfaq.md` e `templates/prd.md`; (7) o `teardown` passa a remover também a `AshProtoStack`, porque o WAF cobra mensalidade fixa; (8) o `ash.py` ignora, só no próprio processo e nos filhos, as variáveis de certificado TLS (`REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `AWS_CA_BUNDLE`, `NODE_EXTRA_CA_CERTS`, `CURL_CA_BUNDLE`, `PIP_CERT`) que apontam para arquivo inexistente, e mostra quais ignorou no `status`. Motivo: em notebook Windows com gerenciamento corporativo (12/11/2026), essas variáveis estavam no escopo de máquina apontando para um `.pem` que não existia, e o pip-audit falhava no CI **[TESTADO]** em Linux com variável simulada. A faixa crítica rodou no Kiro na INS-018 (23/10/2026); a separação de funções com duas pessoas reais ainda não foi testada.

Legenda:
- **[DOC]** confirmado na documentação oficial do Kiro em 20/10/2026 (fontes na seção 14)
- **[TESTADO]** executado e verificado no ambiente de construção em 20/10/2026
- **[DECISÃO]** escolha de desenho desta spec
- **[LACUNA]** não confirmado; depende de verificação ou de alguém

---

**O que mudou em 13/11/2026 (núcleo agnóstico):** o ASH deixou de assumir uma stack e um setor. (1) O que muda por stack saiu do código do `ash.py` e foi para o **perfil de stack**, `ash-perfil.json`, ativado a partir de `perfis/`: setup do projeto, comando rápido de teste, etapas do CI e padrão dos arquivos de teste. O template traz `perfis/python.json`, que reproduz o comportamento anterior, e `perfis/modelo.json`, com instruções para criar outro. (2) O CI passou a ser `spec-gate` (núcleo) + etapas do perfil + `rastreio` (núcleo); o rastreio lê os arquivos de teste do perfil e aceita a citação `<ID> CA-NN` em nome, docstring ou comentário. (3) Comandos novos: `testar`, `etapa <nome>` e `perfil [nome]`. Implementador e revisores usam esses comandos em vez de chamar pytest, Semgrep ou pip-audit direto; agentes de papel não trocam o perfil (bloqueio por permissão e pelo hook). (4) O que é de setor saiu do núcleo: a faixa crítica usa critérios neutros, a regra de finalidade de dado pessoal (LGPD) e a de dado sensível (art. 5º, II) subiram para a governança, a regra de Semgrep para valor monetário ficou com vocabulário neutro, e a lente de serviços financeiros virou exemplo pronto ao lado de `templates/lente-vertical.md`. (5) A primeira conversa pergunta a stack e o setor e avisa o FDE quando falta perfil ou lente.

## 1. Objetivo

Um repositório-modelo para o Kiro, com uma camada pequena na AWS. Com ele, uma squad agêntica começa com duas pessoas (um Forge FDE e um PO) e entrega código com governança, gates por faixa de autonomia, versionamento seguro e medição pronta para o Value Realization Plan (VRP). O mesmo repositório-modelo serve a qualquer frente (Agentic AI, Migration, Modernization, Data, Customer Experience), vertical e stack: o núcleo é fixo e a adaptação acontece no perfil de stack e nas lentes de vertical.

## 2. Problema e critério de sucesso

| Dor | Como o ASH responde |
|---|---|
| Clientes pedem mais produtividade com o mesmo custo | Squad mínima de duas pessoas, com agentes por papel |
| Cada squad monta o harness do zero | Repositório-modelo pronto: `git clone` (ou restauração do S3) e `python ash.py setup` |
| O Forge FDE completo é raro | O FDE orquestra e aprova; o trabalho é dividido entre agentes e scripts |
| O PO é gargalo na escrita de spec | O PO escreve a story em linguagem de negócio; o intake gera a spec de dez blocos |
| Governança só em slide | As oito regras viram permissões de agente, hooks, CI local e scripts de ato humano |
| Não há baseline | Eventos registrados desde a primeira spec; relatório semanal automático |

Critério de sucesso do piloto: os critérios de aceite da seção 12, todos verdes.

## 3. Composição humana

| Papel | Quem | Faz | Não faz |
|---|---|---|---|
| Forge FDE | Compass | Opera o harness, aprova design e tasks, aprova merge | Escrever a spec pelo PO |
| PO | Cliente, por padrão **[DECISÃO]** | Escreve a story, responde as perguntas, aprova a spec | Revisar código |
| Dev revisor | Cliente ou Compass, só na faixa crítica | Revisa linha a linha e aprova o merge junto com o FDE | Entrar nas outras faixas |

Na faixa `critica`, o merge exige aprovação do FDE e do `dev_revisor` nomeado na spec, e os dois precisam ser pessoas diferentes (separação de funções) **[TESTADO]**. A checagem compara os nomes como texto, então dois nomes diferentes da mesma pessoa passariam. A separação real depende da configuração da squad e da conferência humana no portão **[LACUNA]**.

## 4. Ambiente

| Item | Valor |
|---|---|
| Conta AWS | Conta da squad, conferida pelo `bootstrap` contra `ASH_CONTA_ESPERADA` |
| Região de build | us-east-1 **[DECISÃO]** |
| Região da estimativa | sa-east-1 |
| Região do perfil Kiro enterprise | US East (N. Virginia) ou Europe (Frankfurt) **[DOC]** |
| Versionamento | Repositório privado da squad (GitHub ou Bitbucket) como `origin`, operado pelo Kiro (`ash.py sync`, portões `merge` e `publicar-harness`) **[TESTADO]** com remoto local; backup opcional em S3 |
| Tags | `accelerator=agentic-squad-harness`, `owner`, `cost-center`, `env`. **[LACUNA]** Confirmar a lista canônica de tags e o centro de custo com o cliente |
| Sistema operacional | Windows (PowerShell), macOS ou Linux. `ash.py` detecta `.venv\\Scripts` ou `.venv/bin`. `.gitattributes` força LF |

## 5. Arquitetura

### 5.1 Repositório

```
ash-template/
├── AGENTS.md  README.md  pytest.ini  .gitignore
├── ash-perfil.json           # perfil de stack ativo (cópia de um arquivo de perfis/)
├── perfis/                   # python.json (testado) e modelo.json (instruções para outra stack)
├── requirements.txt          # app (FastAPI)
├── requirements-dev.txt      # testes
├── requirements-tools.txt    # semgrep e pip-audit, em .venv-tools separado
├── .kiro/
│   ├── steering/  00-governanca · 01-faixas-autonomia · 02-spec-dez-blocos · 03-stack-cliente · 04-papeis-e-portoes · 05-descoberta-produto · 10-lente-servicos-financeiros
│   ├── agents/    squad-lead · product-lead · designer-proto · intake-spec · planejador · implementador · revisor-vulnerabilidade · revisor-cobertura · revisor-documentacao · revisor-divida
│   ├── hooks/     ash-hooks.json
│   └── specs/     ins-014-aumento-cobertura/ (exemplo aprovado: requirements, design, tasks) · ins-016 · ins-018 (rodadas de teste)
├── .githooks/     pre-commit · pre-merge-commit
├── .semgrep/      regras-ash.yml
├── .ash/          config.env.example (config.env, events/ e approvals/ ficam fora do git)
├── stories/       INS-017-resumo-apolice.md (story de exemplo para a primeira demonstração, não implementada) · INS-015 (story original do histórico, base da INS-016) · INS-016 · INS-018
├── templates/     story-po.md · requirements-dez-blocos.md · prfaq.md · prd.md · lente-vertical.md
├── portfolio/     backlog.md e iniciativas/<slug>/ (artefatos da fase de descoberta e protótipo)
├── scripts/       ver seção 6; emulador.py é o ciclo de vida do AWS Emulator (seção 5.4)
├── tests_harness/ testes do próprio ASH (`python ash.py testar-harness`)
├── tests_harness_integracao/  testes de integração do PRÓPRIO ASH contra o AWS Emulator (`python ash.py testar-harness --integracao`; fora do CI de qualquer projeto)
├── templates/tests-integracao-aws/  esqueleto dos testes de integração de um PROJETO que usa AWS (copiado para tests/integracao_aws/ no perfil `python-aws`)
├── reviews/       saída dos revisores
├── src/endosso/   app de demonstração (regras puras, repositório em memória, API)
├── tests/         testes citando "<ID> CA-NN"
├── infra/         CDK Python: AshCodeStack, AshMetricsStack e AshProtoStack, Lambdas e testes
└── docs/          esta spec e a estimativa
```

### 5.1.1 Adaptação: perfil de stack e lentes de vertical

| Camada | Conteúdo | Mecanismo | Status |
|---|---|---|---|
| Núcleo | Governança, faixas, spec de dez blocos, portões, papéis, descoberta, evidência, métricas, LGPD | Steering `00` a `05`, `ash.py`, `scripts/` | **[TESTADO]** com o perfil `python` |
| Perfil de stack | `pasta_codigo`, `pasta_testes`, `arquivos_teste`, `cobertura_minima`, `setup`, `testar`, `etapas` | `ash-perfil.json`, lido por `setup`, `ci`, `testar`, `etapa` e pelo rastreio; sem o arquivo, vale o perfil Python embutido no `ash.py` | `python` **[TESTADO]** em Linux em 13/11/2026; outros **[A CRIAR]** |
| Lente de vertical | Exemplos de faixa crítica, regras do setor com fonte, dados do setor | Steering com `inclusion: auto` e nome contendo `lente` | Serviços financeiros pronta; modelo em `templates/lente-vertical.md` |

Comandos do perfil são listas (programa e argumentos), sem operadores de shell. Marcadores: `{python}`, `{py}`, `{semgrep}`, `{pip-audit}`, `{cobertura}`, `{codigo}`, `{testes}`. O programa é resolvido no PATH com `shutil.which`, o que cobre `npm.cmd` e similares no Windows. As etapas `spec-gate` e `rastreio` são do núcleo e um perfil não pode redefinir. Perfil marcado como modelo é recusado por `perfil` e pelo `ci`. Ativar ou criar perfil e lente é mudança de harness e passa pelo portão `publicar-harness`. A etapa de integração contra o AWS Emulator (`integracao-aws`, com o campo `requer: emulador_aws` e o bloco `emulador_aws`) é declarada no perfil como qualquer outra etapa; desenho, fontes e lacunas na seção 5.4. Todo perfil leva também a etapa `harness` (`{python} ash.py testar-harness`).

### 5.2 Regras de governança e o mecanismo de cada uma

| Regra | Mecanismo | Status |
|---|---|---|
| Contexto isolado | Um custom agent por papel; subagentes com contexto de conversa isolado | **[DOC]** |
| Menor privilégio | `tools` e `permissions.rules` por agente, `fs_write` restrito a pastas | **[DOC]** campos |
| Quem escreve não revisa | Revisores escrevem só em `reviews/**`; implementador com `deny` em `reviews/**` | **[DOC]** campos |
| Supervisor não produz | Prompt do squad-lead e conferência humana nos portões (permissões e hooks do squad-lead valem para os subagentes) | **[TESTADO]** no Kiro em 22/10/2026 |
| Handoff por artefato | Spec, `reviews/*.md`, eventos em `.ash/events/` | **[DECISÃO]** |
| Cálculo fora do modelo | Validação, rastreio, cobertura e métricas em scripts e Lambdas | **[TESTADO]** |
| Delegação de um nível | Só o squad-lead tem a ferramenta `subagent` | **[DOC]** |
| Decisão humana com evidência | (1) `deny` de shell nos agentes de papel; (2) hook `PreToolUse` (código 2) no perfil de cada agente de papel; (3) hooks do Git na `main`; (4) portões: portão aberto pelo squad-lead e frase literal do humano no chat passada em `--mensagem` (o hook `UserPromptSubmit` não entrega o texto no Kiro IDE) | (1) e (2) **[DOC]** e observado no teste; (3) e (4) **[TESTADO]** |

### 5.3 AWS

| Stack | Recurso | Papel |
|---|---|---|
| AshCodeStack | S3 `CodeBucket` | Backup do repositório (`git bundle`). Privado, versionado, SSE-S3, só TLS, versões antigas expiram em 180 dias, **mantido se a stack for apagada** |
| AshMetricsStack | S3 `EventsBucket` | Recebe JSONL em `raw/`, expira em 90 dias |
| AshMetricsStack | S3 `ReportsBucket` | Relatório semanal CSV + HTML |
| AshMetricsStack | Lambda `ash-ingest` (Python 3.12, arm64) | Evento S3 → DynamoDB; idempotente; retry assíncrono 0; X-Ray ativo; métrica `ASH/EventosIngeridos` via Embedded Metric Format |
| AshMetricsStack | Lambda `ash-report` | Agrega e grava o relatório |
| AshMetricsStack | DynamoDB `ash-metrics` on-demand | Eventos |
| AshMetricsStack | EventBridge Scheduler | Segunda 08h, America/Sao_Paulo |
| AshMetricsStack | CloudWatch Logs | Retenção de 30 dias |
| AshProtoStack | S3 `ProtoBucket` | Protótipo da fase de descoberta. Privado (Block Public Access total), SSE-S3, só TLS, **mantido se a stack for apagada** |
| AshProtoStack | CloudFront `ProtoDist` | Serve o bucket por OAC, redireciona para HTTPS, TLS mínimo 1.2 (2021), cabeçalhos de segurança (nosniff, DENY de frame, no-referrer, HSTS de 365 dias) |
| AshProtoStack | WAF `ProtoWebAcl` (escopo CLOUDFRONT) | Uma regra de limite por IP: 2.000 requisições em 5 minutos, ação de bloqueio |

`cdk synth` da `AshCodeStack` e da `AshMetricsStack` executado sem erro **[TESTADO]** (a `AshProtoStack` ainda não, ver abaixo). Única política com `Resource: "*"`: `xray:PutTraceSegments` e `xray:PutTelemetryRecords`, gerada pelo CDK ao ativar o X-Ray; essas ações não aceitam restrição por recurso **[DECISÃO justificada]**. O CDK também cria as funções auxiliares de notificação de bucket e de auto-delete, padrão da biblioteca.

Nenhum LLM, Bedrock, VPC, NAT, API Gateway ou ferramenta de BI. Disponibilidade dos serviços em sa-east-1: **[LACUNA]** confirmar na lista regional oficial.

`cdk synth` da `AshProtoStack`: sem registro de execução neste pacote **[LACUNA]**. O WAF de escopo CLOUDFRONT precisa ser criado em us-east-1 **[DOC]** (guia do AWS WAF e referência do `CfnWebACL`, consultados em 12/11/2026). Como as três stacks usam a mesma região (padrão us-east-1), trocar `AWS_REGION` para sa-east-1 quebra o deploy da `AshProtoStack` até ela ser separada e mantida em us-east-1. O WAF cobra mensalidade fixa por web ACL e por regra enquanto existir; por isso o `teardown` remove a `AshProtoStack` junto com a de métricas.

### 5.4 Testes de integração contra o AWS Emulator

Esta seção descreve o que o ASH faz para rodar testes de integração de projetos que chamam serviços AWS sem tocar conta real, por que cada decisão foi tomada, o que a documentação oficial afirma (com fonte e data de consulta) e o que **não** foi testado. O passo a passo de uso está no `README.md` (seção "Testes contra o AWS Emulator") e as regras dos agentes em `.kiro/steering/06-emulador-aws.md`. Os critérios de aceite AC-28 a AC-38 estão na seção 12, com o status real. A auditoria das ferramentas do harness (D19, AC-38 e L12) vive nesta seção porque nasceu da adição do `boto3` ao `requirements-tools.txt`, mas não depende do emulador.

O emulador tem dois usos que não se misturam (decisão D15): (1) os testes de integração **do próprio ASH** (as Lambdas de `infra/lambdas/` e o backup), em `tests_harness_integracao/`, rodados pelo autor do harness com `python ash.py testar-harness --integracao`, **fora do CI de qualquer projeto**; (2) os testes de integração **da aplicação do cliente**, em `tests/integracao_aws/`, etapa `integracao-aws`, **só no perfil `python-aws`**. O perfil `python` padrão não declara o emulador: o `ci` dele sai com código 0 numa máquina sem emulador, Docker ou WSL, e nenhuma faixa exige `homologacao` por causa do emulador.

#### 5.4.1 Fontes (todas consultadas em 13/11/2026)

| Código | Fonte | O que sustenta |
|---|---|---|
| UG-visão | https://docs.aws.amazon.com/emulator/latest/userguide/what-is-service.html | O que é; sem taxa adicional; macOS e Windows só por Docker; limites: não avalia políticas IAM nem as baseadas em recurso, uma conta e uma região por emulador, verificado em `us-west-2` (serviços globais em `us-east-1`), recursos só em memória, não testado para uso longo nem teste de carga (usar `--idle-timeout`) |
| UG-req | https://docs.aws.amazon.com/emulator/latest/userguide/setting-up.html | Pacote nativo: Linux 64 bits (x86_64 ou aarch64) com glibc 2.17 ou superior, capaz de instalar RPM ou DEB; Docker: qualquer sistema que rode Docker, e no macOS e no Windows é o caminho a usar; skill `aws-emulator`: AWS CLI 2.35.0 ou superior; licença CC0 1.0 (diretório `vendor/` sob Apache 2.0) |
| UG-linux | https://docs.aws.amazon.com/emulator/latest/userguide/getting-started-linux.html | Instalação do pacote em `/opt/aws-emulator/` com o comando `aws-emulator` em `/usr/bin/`; `-p` escolhe a porta; parar com Ctrl+C ou SIGTERM apaga os arquivos de `~/.aws/emulator/<porta>/`; o emulador usa cerca de 160 MiB parado |
| UG-docker | https://docs.aws.amazon.com/emulator/latest/userguide/getting-started-docker.html | Sem imagem pronta; Dockerfile da documentação; `docker run` publicando em `127.0.0.1` (nunca `-p PORTA:PORTA`), `--memory=2g`, volume de `.aws/emulator`; não usar `-p 0` em contêiner |
| UG-sdk | https://docs.aws.amazon.com/emulator/latest/userguide/point-sdk-to-emulator.html | Variáveis de ambiente para CLI e SDK; remover as variáveis de credencial real; `AWS_CA_BUNDLE` para CLI v2, boto3 e SDK Go; S3 só funciona com endpoint por IP (`127.0.0.1`); S3 Control não alcança o emulador; conta `000000000000` e ARN `arn:aws:iam::000000000000:user/emulator` |
| UG-cli | https://docs.aws.amazon.com/emulator/latest/userguide/cli-reference.html | Opções (`-b`, `-p`, `-a`, `-t`, `--idle-timeout`); health check `GET /__admin/health` (200 e `ok`); arquivos `emulator_credentials`, `config`, `ca.pem`, `truststore.p12` em modo 0600; chaves novas a cada início, ID começando com `EMULATOR` (o formato pode mudar); sem rota de reset; porta em uso devolve erro e código 1 |
| UG-fidelidade | https://docs.aws.amazon.com/emulator/latest/userguide/fidelity.html | Fidelidade por serviço (nota "k de n" por release); operação não implementada devolve HTTP 501 `NotImplemented`; fidelidade maior no plano de controle; suporte a CloudFormation, Terraform e CDK "varia por serviço" |
| UG-versão | https://docs.aws.amazon.com/emulator/latest/userguide/versioning.html | Versionamento `MAJOR.MINOR.PATCH`; canal LTS em `https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/`; `versions.json`; recomendação de fixar a versão; correções de segurança só na última release |
| UG-segurança | https://docs.aws.amazon.com/emulator/latest/userguide/security.html | Não testar segurança; manter privado; manter credenciais reais e dados reais fora; manter a autenticação ligada; código executado pelo emulador não é isolado |
| AWS-repo | https://github.com/aws/aws-emulator (README) e https://github.com/aws/aws-emulator/releases | Telemetria ligada por padrão (desliga com `--telemetry off`, `EMULATOR_TELEMETRY=off` ou `config.toml`); notas de fidelidade por release; última release observada: v1.0.343 |
| AWS-anúncio | https://aws.amazon.com/blogs/aws/test-your-applications-against-aws-locally-with-aws-emulator/ e https://aws.amazon.com/about-aws/whats-new/2026/11/aws-emulator-now-available/ | Lançamento em 11/11/2026; instalação por RPM ou DEB no Linux e Docker no macOS e no Windows; embutido só para Rust |
| AWS-pacotes | HEAD de leitura em `downloads.aws.com` | `LTS/aws-emulator-1.0.343-1-x86_64.rpm`, `LTS/aws-emulator-1.0.343-1-aarch64.rpm`, `LTS/aws-emulator_1.0.343-1_amd64.deb` e `LTS/aws-emulator_1.0.343-1_arm64.deb` responderam 200. Com o sufixo `.1` do `versions.json` (`1.0.343.1`) a resposta é 403, então o perfil usa `versao: "1.0.343"` |
| MS-comandos | https://learn.microsoft.com/en-us/windows/wsl/basic-commands | `wsl --distribution <nome>` roda uma distribuição específica; `wsl --list --verbose` (com `--running`); `wsl --terminate`; `wsl --shutdown` |
| MS-arquivos | https://learn.microsoft.com/en-us/windows/wsl/filesystems | `wsl <comando>` roda binários Linux a partir do PowerShell; `\\wsl$` expõe as distribuições no Windows; discos do Windows aparecem em `/mnt/c` |
| MS-config | https://learn.microsoft.com/en-us/windows/wsl/wsl-config | `localhostForwarding` (padrão `true`): portas ligadas a localhost ou wildcard na VM do WSL2 ficam acessíveis do Windows por `localhost:porta`; `vmIdleTimeout` padrão 60000 ms; `instanceIdleTimeout` padrão 15000 ms (`-1` desliga o encerramento automático) |
| MS-rede | https://learn.microsoft.com/en-us/windows/wsl/networking | No modo NAT (padrão), um app Linux é acessível do Windows por `localhost`; no modo `mirrored`, a página documenta só o sentido Linux para Windows |
| DOCKER-licença | https://docs.docker.com/subscription/desktop-license/ | Docker Desktop é gratuito para pequenas empresas (menos de 250 funcionários **e** menos de US$ 10 milhões de receita anual), uso pessoal, educação e open source não comercial; exige assinatura paga para uso profissional em organizações maiores, entidades governamentais e uso comercial além disso; o Docker Engine e outros projetos open source não mudam |

#### 5.4.2 Decisões e motivos

| # | Decisão | Motivo |
|---|---|---|
| D1 | Três modos, escolhidos por `ASH_EMULADOR_MODO` (vazio: detecção na ordem `linux`, `wsl`, `container`): pacote nativo em Linux; pacote nativo dentro de uma distribuição WSL2 no Windows; contêiner (CLI em `ASH_CONTAINER_CLI`, `docker` ou `podman`) | O ASH não pode depender do Docker Desktop: a licença dele (DOCKER-licença) depende do uso, e quem avalia e contrata é cada cliente ou usuário. O pacote nativo é o caminho principal da AWS (UG-linux); contêiner é o caminho da AWS para macOS e Windows (UG-docker). O modo `wsl` e o uso de Podman são extensões do ASH (ver L1 e L7) |
| D2 | Só `python ash.py emulador iniciar` sobe o emulador (ou o `ci`, com `ASH_EMULADOR_AUTO=sim`). Nunca serviço, tarefa agendada ou início automático com o Windows ou com o WSL; nunca alterar o `.wslconfig` | O emulador guarda estado em memória e não foi testado para uso longo (UG-visão); iniciar sozinho sem o usuário saber consumiria memória e abriria uma porta local sem necessidade |
| D3 | Toda subida usa `--idle-timeout` (padrão 1800 s, `ASH_EMULADOR_IDLE`) e `--telemetry off` | O `--idle-timeout` é a forma documentada de não deixar um emulador esquecido (UG-visão, UG-cli); a telemetria vem ligada por padrão (AWS-repo) e o ASH não envia dado de uso a terceiros sem pedido |
| D4 | O comando que subiu o emulador o para ao final; o que já estava de pé fica como estava | Evita deixar processo ou contêiner para trás sem derrubar o que outra pessoa ou sessão estava usando |
| D5 | Chaves, certificado e estado ficam em `.ash/emulador/` (modos `linux` e `container`) ou dentro da distribuição WSL (modo `wsl`); o `estado.json` nunca contém chaves; a pasta é gitignorada (`.gitignore` e `GITIGNORE_PADRAO`) | O `git add -A` do fluxo da squad não pode versionar chaves. Fora do `~/.aws/emulator` do usuário, o ASH não interfere em uso manual do emulador |
| D6 | O ambiente do emulador existe só no processo filho (cópia do ambiente), com as variáveis de UG-sdk. Além do que a documentação manda, o ASH remove do filho `AWS_SECURITY_TOKEN`, `AWS_DEFAULT_PROFILE`, as variáveis de web identity e de role, `AWS_CONTAINER_CREDENTIALS_*`, `AWS_ENDPOINT_URL_*`, `AWS_SSO*` e as de FIPS e dualstack, e acrescenta `127.0.0.1` ao `NO_PROXY` | Garante que nenhuma credencial real nem endpoint por serviço desvie uma chamada de teste para a AWS (endurecimento do ASH, não exigência da documentação). O `NO_PROXY` evita que um proxy corporativo capture a chamada local |
| D7 | Provas antes de qualquer chamada: endpoint `https://127.0.0.1:<porta>`; `ca.pem` presente e health check respondendo com ele; ID da chave começando com `EMULATOR`, conferido em memória; no `conftest.py`, `sts get-caller-identity` com conta `000000000000` e usuário `emulator` | UG-cli e UG-sdk descrevem esses sinais. A documentação avisa que o formato das chaves pode mudar, por isso só se confere o prefixo. Se uma prova falha, a execução aborta antes de criar recurso |
| D8 | Convivência com a limpeza de certificados do `ash.py`: ela roda uma vez, sobre o ambiente real; o ambiente do emulador é montado depois, na cópia do filho, com `AWS_CA_BUNDLE` apontando para o `ca.pem` provado como existente | O certificado do emulador existe e não pode ser removido pela regra de "variável apontando para arquivo inexistente". Certificados corporativos válidos continuam como estão |
| D9 | Bloco `emulador_aws` no perfil (versão fixada, URL base do pacote, serviços com fidelidade, `fidelidade_minima`) e campo `requer: emulador_aws` na etapa `integracao-aws`, que roda `tests/integracao_aws/` no perfil `python-aws` (não no `python` padrão; D15) | A documentação recomenda fixar a versão (UG-versão), e a fidelidade varia por serviço (UG-fidelidade). O campo `requer` é genérico: outra stack usa o mesmo mecanismo com o seu comando de testes. `spec-gate` e `rastreio` continuam as únicas etapas do núcleo |
| D10 | Sem emulador, a etapa `integracao-aws` (perfil `python-aws`) falha com mensagem clara. `ASH_PULAR=integracao-aws` é possível, com código 3 e merge recusado | Pular em silêncio esconderia que a integração não foi testada |
| D11 | Os testes chamam os handlers das Lambdas em processo, nunca `lambda invoke` | O emulador executa código de função sem isolamento, com as permissões do usuário (UG-segurança) |
| D12 | Fidelidade por faixa (steering 01) e papel `homologacao` no merge, registrado pelo portão `aprovar-homologacao`, sem tocar AWS; vale só para perfis que declaram `emulador_aws` (o `python-aws`), nunca para o `python` padrão | O emulador não avalia IAM e a fidelidade varia (UG-visão, UG-segurança). Sem um jeito de registrar a execução em conta real, a faixa crítica nunca passaria pelo merge |
| D13 | Sem `bootstrap --emulador` | A documentação só diz que o suporte a CloudFormation e CDK "varia por serviço" (UG-fidelidade). Ver L3 |
| D14 | Permissões: agentes de papel nunca rodam `emulador`, `docker`, `podman` ou `wsl`; o `implementador` escreve em `tests/integracao_aws/` (coberto por `tests/**`), não escreve em `tests_harness/` nem em `tests_harness_integracao/` e roda `etapa integracao-aws`; ninguém entre os agentes de papel roda `testar-harness --integracao`; o hook de bloqueio ganhou esses padrões | Os runtimes são chamados por dentro do `ash.py`; nenhum agente deve iniciar processo ou abrir porta fora do fluxo |
| D15 | Separação entre a integração do harness e a da aplicação: os testes do próprio ASH (Lambdas de `infra/` e backup) ficam em `tests_harness_integracao/`, com a configuração do emulador em `tests_harness_integracao/emulador.json`, e rodam por `python ash.py testar-harness --integracao`, fora do CI. Os testes da aplicação ficam em `tests/integracao_aws/` e só o perfil `python-aws` os roda (etapa `integracao-aws`). O perfil `python` padrão não declara `emulador_aws` nem a etapa | Os testes das Lambdas e do backup verificam o ASH, não a aplicação do cliente. Como etapa obrigatória do perfil padrão, qualquer cliente Python sem emulador ficaria com o `ci` em código 1 e sem merge, mesmo sem usar AWS, e a faixa crítica exigiria `homologacao` num projeto sem AWS |
| D16 | `boto3`: o dos testes do harness vai para o `requirements-tools.txt` (`.venv-tools`), com a mesma versão do `infra/requirements.txt`. O de um projeto que usa AWS fica no `requirements.txt` dele, com versão exata. O `setup` do `python-aws` **não** instala `boto3` por fora. O `python ash.py perfil` e o `ci` avisam quando o perfil tem `emulador_aws` e o `requirements.txt` não declara o `boto3` com versão exata | A etapa `dependencias` só audita o `requirements.txt`: um `boto3` instalado por fora ficaria sem `pip-audit`. A versão exata faz o `pip-audit` e o emulador testarem sempre a mesma coisa |
| D17 | O aviso não bloqueante do `publicar-harness`: quando os arquivos mudados incluem `ash.py`, `scripts/emulador.py`, `infra/lambdas/`, `infra/emulador/` ou `tests_harness_integracao/`, ele sugere rodar `testar-harness --integracao` antes. Quem mantém o ASH roda também ao trocar a versão do emulador | Exigir a execução bloquearia um autor sem emulador disponível (L5). O aviso lembra sem travar |
| D18 | Os testes de `tests_harness/` não dependem de qual perfil está ativo: o `ash-perfil.json` é conferido como cópia de algum perfil pronto de `perfis/`, e as afirmações sobre o perfil padrão olham `perfis/python.json` | Achado ao ativar o `python-aws` de verdade: dois testes assumiam que o perfil ativo era o `python`, e a etapa `harness` do CI falhava no `python-aws`. Como a etapa `harness` roda em qualquer perfil, os testes dela não podem depender do perfil ativo |
| D19 | Vulnerabilidades conhecidas nas ferramentas do harness (`requirements-tools.txt`) viram **risco aceito explícito e revisável**, não ficam em silêncio nem são "corrigidas" à força. O arquivo `tests_harness/auditoria_ferramentas.json` guarda, por vulnerabilidade: id, pacote, versão afetada, motivo, fonte com data, data da decisão, data de revisão (no máximo 90 dias depois), o papel de quem aceitou (`autor do harness`, nunca nome de pessoa), a frase "aceite válido para o template; cada cliente revalida com o seu time de segurança" e a condição de saída (qual versão que o Semgrep teria de admitir). `python ash.py testar-harness --auditoria` roda o `pip-audit -r requirements-tools.txt` **sem ignorar nada** e mostra três listas: CVEs novos, aceites vencidos e aceites que podem sair; sai com código 1 se houver CVE novo ou aceite vencido e com 2 se não conseguiu auditar. O `publicar-harness` avisa, sem bloquear, quando o `requirements-tools.txt` ou o arquivo de aceites mudam ou há aceite vencido. O comando nunca roda no CI de um projeto | Nenhuma versão do Semgrep até a 1.185.0 declara faixas que admitam as versões corrigidas de `mcp` e `opentelemetry-api`, e forçá-las faz o `pip check` falhar (L12). Auditar dentro do `testar-harness` do CI quebraria o CI de todo cliente por CVE de ferramenta do harness, e um teste que falha numa data faria o mesmo; por isso é um comando à parte, do autor do harness, com lembrete no `publicar-harness`. Um aceite com prazo máximo de 90 dias impede aceite eterno. O arquivo vive em `tests_harness/`, onde o `implementador` não escreve: nenhum agente cria nem prorroga aceite |

#### 5.4.3 Pré-requisitos por sistema

Linux: pacote nativo da AWS, RPM ou DEB (UG-linux), glibc 2.17 ou superior (UG-req). Windows com WSL2, sem Docker: WSL2 com uma distribuição própria e o pacote nativo instalado dentro dela (MS-comandos; ver L1 e L2). Windows ou macOS com contêiner: Docker ou Podman rodando, e o ASH constrói a imagem com `infra/emulador/Dockerfile` (UG-docker). macOS só tem o modo `container` (UG-req). Só projetos que usam AWS (perfil `python-aws`) e o autor do harness (`testar-harness --integracao`) precisam de um desses modos; o perfil `python` padrão não precisa. Detalhes e comandos: README.

#### 5.4.4 Lacunas e o que não foi testado

| # | Lacuna ou não testado | Motivo |
|---|---|---|
| L1 | A documentação da AWS só cita Linux (RPM ou DEB, glibc 2.17 ou superior) e Docker; não cita WSL. Rodar o pacote nativo numa distribuição WSL2 decorre da descrição de requisitos, não é suporte declarado | UG-req, UG-visão |
| L2 | A documentação da Microsoft não define "ocioso" em `vmIdleTimeout` e `instanceIdleTimeout`, então não há prova oficial de que um processo iniciado por `wsl.exe` mantém a distribuição de pé durante o uso. O encaminhamento de `localhost` está documentado para o modo NAT; para o modo `mirrored` a documentação só cita o sentido Linux para Windows. O ASH usa `--idle-timeout` e o health check | MS-config, MS-rede |
| L3 | Notas de fidelidade por serviço (k de n): publicadas a cada release, mas a página de releases consultada devolveu só a lista de correções, então os percentuais não foram obtidos e começam `null` no perfil. Suporte a CloudFormation e CDK não confirmado. SNS e EventBridge Scheduler não apareceram na documentação nem nas notas consultadas | UG-fidelidade, AWS-repo |
| L4 | O nome do pacote com versão fixada (`aws-emulator-<versao>-1-<arq>.rpm`) foi confirmado só por HEAD de leitura, não por exemplo da documentação | AWS-pacotes |
| L5 | Nenhum dos três modos foi executado de ponta a ponta: o ciclo iniciar, usar, parar e a conferência de que não sobra processo (`wsl --list --running`, `docker ps`, `pgrep`) dependem de um ambiente com modo disponível. No ambiente em que o pacote foi preparado (Windows) não havia modo utilizável: o modo `linux` só existe em Linux, não havia distribuição WSL2 própria e o daemon do runtime de contêiner estava parado | Ver AC-28 |
| L6 | Não testados contra um emulador real: a leitura das credenciais e do `ca.pem` pelo caminho `\\wsl$`, a criação de arquivos com modo 0600 dentro do WSL, o `pkill` pelo `wsl.exe`, o build da imagem e o `docker run`, a ingestão, o relatório e o backup de `tests_harness_integracao/` | Ver AC-28, AC-31, AC-32, AC-33 |
| L7 | Podman não foi testado, e a documentação da AWS não o cita: o ASH usa o mesmo `run` e `build` que a documentação descreve para Docker | UG-docker |
| L8 | O gatilho S3 para Lambda, o EventBridge Scheduler, o `ash.py metricas` e a execução do CDK continuam exigindo conta real: AC-08, AC-09, AC-10 e AC-21 ficam só parcialmente cobertos | Seção 12 |
| L9 | O ASH não executa a homologação em conta real e não recebe credencial real: o portão `aprovar-homologacao` só registra a declaração do humano e a evidência que ele informa | D12 |
| L10 | A licença e a instalação de qualquer runtime de contêiner são decisão do cliente ou do usuário de cada máquina; o ASH não instala WSL, Docker nem Podman | DOCKER-licença |
| L11 | O perfil `python-aws`, o esqueleto `templates/tests-integracao-aws/` e a integração de um projeto com AWS nunca rodaram contra um emulador real nem contra uma aplicação que use AWS (a app de exemplo `src/endosso/` não usa). O perfil está marcado `testado: false`. Foram verificados: a ativação e a volta do perfil (byte a byte), o `ci` sem emulador (código 1 na etapa `integracao-aws`), o `ASH_PULAR` (código 3), o aviso do `boto3` e que a etapa `testes` ignora `tests/integracao_aws/` | D15, AC-30, AC-37 |
| L12 | `pip-audit -r requirements-tools.txt` (13/11/2026) encontrou 6 vulnerabilidades conhecidas em 2 dependências **transitivas do Semgrep 1.181.0**, não do `boto3` nem do `pytest`: `mcp` 1.29.0 (CVE-2026-59951, CVE-2026-116684, CVE-2026-116685, CVE-2026-116686; correção em 1.30.0 ou 2.2.0) e `opentelemetry-api` 1.37.0 (CVE-2026-114603 e CVE-2026-126360; correção em 1.45.1 e 1.45.2). **Investigação de 13/11/2026 (nada foi alterado no `requirements-tools.txt`):** (a) *atualizar o Semgrep não corrige*: as versões 1.181.0, 1.181.1, 1.182.1, 1.183.0, 1.184.0 e 1.185.0 (a mais recente; a 1.183.0, de 29/10/2026, é a mais nova com mais de 14 dias) declaram as mesmas faixas, `mcp==1.29.0`, `opentelemetry-api`, `-sdk` e `-exporter-otlp-proto-http` em `~=1.37.0` e as instrumentações em `~=0.58b0`; (b) *fixar as versões corrigidas contraria as faixas do Semgrep*, e o `pip check` falha. Num ensaio em venv temporária fora do repositório, forçar `mcp` 1.30.0 e `opentelemetry-*` 1.45.2 funcionou (scan do repositório com 0 achados e os mesmos 5 arquivos; alvo sintético com os mesmos 3 achados das regras; `pip-audit` do ambiente sem vulnerabilidades), mas o `pip check` acusou 4 conflitos com o Semgrep 1.181.0, então a opção foi descartada; (c) o Semgrep acompanha o `mcp` no issue semgrep/semgrep#11992 ("Update the Python MCP SDK pin to 1.30.0", aberto em 17/10/2026; o estado atual não foi conferido); não achei issue equivalente para o `opentelemetry`; (d) as descrições dos CVEs (OSV, 13/11/2026) tratam de caminhos de servidor e de cliente HTTP do MCP e da leitura de cabeçalhos de contexto de trace; o ASH só roda `semgrep scan` em arquivos locais com `--metrics=off`; não verifiquei os caminhos internos do Semgrep, então isto é indício de baixa exposição, não prova. A etapa `dependencias` do CI audita só o `requirements.txt` do projeto, então o CI não é afetado. **Decisão do autor do harness em 13/11/2026 (D19): risco aceito de forma explícita e revisável, não corrigido.** Os 6 aceites estão em `tests_harness/auditoria_ferramentas.json`, cada um com fonte, data da decisão (13/11/2026), data de revisão (11/02/2027, 90 dias) e o papel de quem aceitou; `python ash.py testar-harness --auditoria` lista CVEs novos, aceites vencidos e aceites que podem sair, e o `publicar-harness` avisa quando o `requirements-tools.txt` ou o arquivo de aceites mudam ou há aceite vencido. **Esta lacuna fica aberta** até o Semgrep publicar versão que declare faixas admitindo `mcp` 1.30.0 ou superior e `opentelemetry-api` 1.45.2 ou superior; nesse dia o `--auditoria` passa a listar os aceites como "podem sair". O aceite vale para o template: cada cliente revalida com o seu time de segurança e pode trocar a ferramenta da etapa `sast` (README, "Riscos aceitos nas ferramentas do harness"). `pip-audit -r requirements-dev.txt -r infra/requirements.txt` não encontrou vulnerabilidades | D16 |

## 6. Interação pelo chat e portões

| Portão | Abertura | Comando depois do APROVO |
|---|---|---|
| `aprovar-po` | Spec validada, sem perguntas em aberto | `ash.py aprovar ID --papel po` |
| `aprovar-design` | `design.md` e `tasks.md` gerados | `ash.py aprovar ID --papel design` |
| `aprovar-dev` | Só faixa crítica | `ash.py aprovar ID --papel dev --branch feat/<id>` |
| `aprovar-homologacao` | Perfil com `emulador_aws` e faixa que exige conta real (seção 5.4 e steering 01) | `ash.py aprovar ID --papel homologacao --nome NOME --branch feat/<id> --evidencia "..."` (só registra a declaração; não toca AWS) |
| `merge` | CI verde, revisões sem bloqueio | `ash.py merge feat/<id> ID --fde NOME` |
| `bootstrap` / `teardown` | Pedido do humano, depois do diff | `ash.py bootstrap` / `ash.py teardown` |
| `aprovar-prd` | Fase de descoberta: PRFAQ e PRD gerados em `portfolio/iniciativas/<slug>/`, sem pergunta que invalide a Big Idea | `ash.py aprovar-prd ID --nome NOME`; depois, `ash.py nova-descoberta ID SLUG` gera a story |
| `publicar-proto` | Protótipo pronto em `portfolio/iniciativas/<slug>/prototipo/` e `AshProtoStack` criada no `bootstrap` | `ash.py publicar-proto ID` (S3 sync e invalidação no CloudFront) |
| `publicar-harness` | Mudanças do próprio harness (steering, agentes, scripts, `ash.py`, docs) | `ash.py publicar-harness` |

Mecanismo em uso (modo declarado): `portao abrir` grava `.ash/gate/pendente.json` com ação, spec e resumo; o squad-lead mostra a decisão no chat; o humano responde APROVO; o squad-lead executa o comando do ato humano com a frase literal em `--mensagem`. O comando só aceita se houver portão aberto para a mesma ação e spec e se a frase for uma aprovação, e registra canal `chat-declarado`, frase, id do portão e horário em `.ash/approvals/<ID>.json` e nos eventos. Motivo: no Kiro IDE (Windows, 21/10/2026) o hook `UserPromptSubmit` dispara mas recebe o texto vazio **[TESTADO]**. O código de captura pelo hook (canal `chat-hook`) continua em `scripts/portao.py` e passa a valer se o Kiro um dia entregar o texto; hoje ele não é acionado. Desenho original, que esse código implementa: `portao abrir` grava `.ash/gate/pendente.json`; a mensagem do humano dispara o hook `UserPromptSubmit` (`scripts/portao.py`), que lê o texto em `USER_PROMPT` **[DOC]** (ou no JSON do STDIN) e, se for aprovação, grava `.ash/gate/confirmacao.json` com o texto literal; o comando do ato humano consome a confirmação uma vez, para aquela ação e spec, em até 30 minutos, e registra canal e texto em `.ash/approvals/<ID>.json` e nos eventos. Negações ("não aprovo", "reprovado", "cancela") não aprovam. Observado no Kiro (Windows) em 21/10/2026: o hook `UserPromptSubmit` dispara, mas não recebeu o texto da mensagem por `USER_PROMPT` nem por STDIN nas chaves esperadas. Aprendizado de 22/10/2026: no Kiro, as regras de `shell` com curinga no início (`*portao.py*`) casam com o texto inteiro do comando, inclusive argumentos livres como `--resumo`; por isso o squad-lead não usa mais negações com curinga inicial. O diagnóstico da v4.5 mostrou `"prompt": ""` no STDIN. Na v4.6 o hook de mensagem saiu e o modo declarado virou o modo oficial: portão aberto + frase literal do humano em `--mensagem` (`--mensagem`, canal `chat-declarado`), sempre com portão aberto. Agentes de papel são bloqueados de abrir portão e de tocar em `.ash/gate/` (permissões e hook). Observado no Kiro em 21/10/2026: as regras de `fs_write` do perfil que delega também valem para os subagentes; por isso o squad-lead só nega caminhos que nenhum agente pode escrever. Na v4.4, a regra "supervisor não produz" volta a ter trava dura: um hook `PreToolUse` só no perfil do squad-lead (`scripts/supervisor_nao_produz.py`) bloqueia a escrita dele nas pastas de trabalho. Observado no Kiro (Windows) em 22/10/2026: o hook do perfil do squad-lead também disparou na subagente intake-spec e barrou a edição da spec; o payload não traz o nome do agente. Na v4.8 o hook saiu do perfil e a regra 4 voltou a depender do prompt do squad-lead e da conferência humana nos portões. Também na v4.8: `ash.py validar <ID>` faz a checagem completa (inclusive perguntas em aberto), o `portao abrir --acao aprovar-po` recusa spec que não passa nela, e o bloco de perguntas aceita frases como "Nenhuma pendência". Na v4.9: nomes da squad em `.ash/config.env` via `ash.py configurar` (o squad-lead pergunta na primeira conversa), `ash.py relatorio` com a linha do tempo local de cada spec, merge que aponta mudanças do harness pendentes em vez de exigir stash, remoção do `spec-kiro-v1.md` solto na raiz pelo publicar-harness, e regras de conversa para o squad-lead seguir sem pedir licença e usar um comando por chamada no PowerShell 5. **[TESTADO]** em Linux: aprovação, recusa de "ok", confirmação para ação errada, reuso, merge sem portão, modo declarado.

Comandos livres do `ash.py` (squad-lead): `status`, `configurar`, `setup`, `sync`, `validar`, `relatorio`, `nova-spec`, `nova-descoberta`, `ci`, `testar`, `testar-harness` (com `--integracao`: os testes de integração do próprio ASH contra o emulador, fora do CI), `etapa`, `emulador iniciar|parar|status|reset`, `perfil` (sem argumento), `pendencias`, `metricas`, `backup`, `restaurar`, `portao`. `perfil NOME` é mudança de harness. Agentes de papel rodam só o que a permissão de cada um libera (implementador: `testar` e `etapa testes`; revisor de cobertura: `etapa testes`; revisor de vulnerabilidade: `etapa sast` e `etapa dependencias`). `ASH_COBERTURA_MIN` sobrescreve a cobertura mínima do perfil; `ASH_PULAR` pula etapas do perfil (o CI sai com código 3 e o merge recusa) e nunca aceita `spec-gate` nem `rastreio`.

## 7. Formato da spec

Front matter `id`, `dono_po`, `faixa` (`autonoma`, `semiautonoma`, `critica`), `dev_revisor`, `versao`, `status` (`rascunho`, `em_revisao`, `aprovada`). Dez blocos com títulos exatos (ver `.kiro/steering/02-spec-dez-blocos.md`) e a seção "Perguntas em aberto", que precisa estar vazia ou com "Nenhuma" para aprovar. Kiro gera `requirements.md`, `design.md` e `tasks.md` por spec **[DOC]**.

## 8. Eventos e métricas

Evento: `{"ts","squad","spec_id","tipo","faixa","ator","usuario","detalhe"}`. Tipos: `spec_criada`, `spec_aprovada`, `task_concluida`, `reescrita_humana`, `ci_executado`, `aprovacao_merge`, `merge`, `defeito_aberto`. Na fase de descoberta, com faixa `descoberta`: `descoberta_etapa`, `prd_aprovado` e `proto_publicado`. O evento `ci_executado` grava `ator: agente` por padrão, porque o squad-lead roda o CI (inclusive dentro do `merge`); `ASH_ATOR=humano` marca execução manual. Entre as métricas, só `proporcao_tasks_agente_sem_reescrita` usa o ator (de `task_concluida`); a taxa de CI verde não depende dele.

| Métrica | Cálculo |
|---|---|
| Cycle time (mediana, horas, por faixa) | `merge` − `spec_aprovada` |
| Tempo até spec aprovada (mediana, horas) | `spec_aprovada` − `spec_criada` |
| Defect density (30 dias) | `defeito_aberto` ÷ specs com merge |
| Proporção de tasks do agente sem reescrita | (`task_concluida` do agente − `reescrita_humana`) ÷ `task_concluida` do agente |
| Taxa de CI local verde | `ci_executado` com status ok ÷ total |

Cálculo testado com dados sintéticos **[TESTADO]**. As definições são a versão inicial e serão calibradas no piloto.

## 9. Agentes e hooks

Agentes em JSON: `squad-lead` (conversa, delega, abre portões, executa; `fs_write` negado), `product-lead` e `designer-proto` (fase de descoberta, escrita só em `portfolio/`), `intake-spec`, `planejador`, `implementador` e quatro revisores. São dez agentes no total. Implementador e revisores de cobertura e de vulnerabilidade rodam testes e verificações só por `python ash.py testar` e `python ash.py etapa <nome>`; nenhum agente de papel pode rodar `ash.py perfil`. Campos `name`, `description`, `prompt`, `tools`, `resources`, `permissions.rules`, `hooks`, `includeMcpJson: false` e, no squad-lead, `toolsSettings.subagent.availableAgents` e `trustedAgents` **[DOC]**.

Hooks do workspace em `.kiro/hooks/ash-hooks.json`, `version: "v1"`: `PostFileSave` com matcher em `requirements.md` (validação) e `Stop` (pendências). O `PreToolUse` de bloqueio fica no campo `hooks` de cada agente de papel, para não travar a sessão principal do FDE. Nomes de gatilho e campo `hooks` do perfil aparecem na documentação **[DOC]**. Código de saída 2 bloqueia o `PreToolUse` **[DOC]** (página de migração de hooks) e foi observado no teste de 20/10/2026, quando o hook barrou o `aprovar.py` **[TESTADO]**. Hook de bloqueio dos agentes de papel com `matcher: "shell"`.

**[LACUNA]** O comportamento padrão de uma operação que não casa com nenhuma regra de `permissions` (provavelmente pedir confirmação) precisa ser observado no Kiro.

## 10. Guardrails

Pago por uso; retry assíncrono 0 com ingestão idempotente; nenhuma escrita em sistema de terceiro; least privilege; logs JSON; buckets com Block Public Access, SSE-S3 e TLS obrigatório; nenhum nome, marca ou dado de cliente.

## 11. Fora de escopo

Front-end de produto ou dashboard (exceção: o protótipo navegável e fictício da fase de descoberta, publicado só pelo portão `publicar-proto`); Bedrock, AgentCore ou LLM na AWS; escrita em Jira ou ferramenta do cliente; overage de créditos Kiro sem limite definido; compatibilidade com outros IDEs; perfis de stack além de `python` e lentes além de serviços financeiros prontos de fábrica (o template entrega o mecanismo e os modelos).

## 12. Critérios de aceite

| ID | Verificação | Esperado | Status em 20/10 |
|---|---|---|---|
| AC-01 | `validar_spec.py` numa spec sem "Limites do agente" | exit 1 nomeando o bloco | **[TESTADO]** |
| AC-02 | Spec `critica` sem `dev_revisor` | Validação falha; merge recusa | **[TESTADO]** |
| AC-03 | Pedir ao `implementador` "faça git push" ou "faça merge na main" | Negado pelo Kiro | No Kiro |
| AC-04 | Pedir ao `squad-lead` para editar `src/` | Escrita negada | No Kiro |
| AC-05 | Pedir a um revisor para corrigir `src/` | Só `reviews/` muda | No Kiro |
| AC-06 | Remover o teste de um CA | `rastreio` falha apontando o CA | **[TESTADO]** |
| AC-07 | INS-015 de ponta a ponta com FDE + PO | Spec aprovada → código → CI verde → merge humano | **[TESTADO]** fora do Kiro; repetir no Kiro |
| AC-08 | Após o merge, `python ash.py metricas` | Itens na tabela `ash-metrics` | Após o bootstrap. Cobertura local parcial: o handler de ingestão com S3 e DynamoDB (AC-31, **[A TESTAR]**); o gatilho S3 para Lambda e o `metricas` real exigem conta real |
| AC-09 | Invocar `ash-report` | CSV + HTML em `reports/semana=AAAA-Www/` | Após o bootstrap. Cobertura local parcial: o cálculo e a gravação do CSV e do HTML (AC-32, **[A TESTAR]**); o EventBridge Scheduler e a invocação real exigem conta real |
| AC-10 | `python ash.py backup` e `python ash.py restaurar` em pasta nova | Repositório restaurado com todas as branches | Bundle **[TESTADO]**; S3 após o bootstrap. Cobertura local parcial: o envio do bundle a um S3 local (AC-33, **[A TESTAR]**); o S3 real exige conta real |
| AC-11 | Commit direto na `main` | Bloqueado pelo hook do Git | **[TESTADO]** |
| AC-12 | `aprovar.py` sem terminal | Recusado | **[TESTADO]** |
| AC-14 | Humano responde "ok" a um portão aberto | Portão continua aberto; nada é aprovado | **[TESTADO]** |
| AC-15 | Comando de ato humano sem APROVO no chat | `[PORTÃO]` recusa | **[TESTADO]** |
| AC-16 | Agente de papel tenta abrir portão ou escrever em `.ash/gate/` | Bloqueado | **[TESTADO]** hook |
| AC-17 | Fluxo INS-015 inteiro só pelo chat no Kiro | Nenhum comando digitado pelo humano | No Kiro |
| AC-13 | Semgrep com float em dinheiro, eval e CPF em log | Três achados, exit 1 | **[TESTADO]** |
| AC-18 | Pedir ao `product-lead` para escrever fora de `portfolio/` | Escrita negada | **[A TESTAR]** no Kiro |
| AC-19 | `aprovar-prd` sem APROVO no chat | `[PORTÃO]` recusa | **[A TESTAR]** |
| AC-20 | `publicar-proto` antes do `bootstrap` | Erro pedindo o `bootstrap` da stack de protótipo | **[TESTADO]** em 13/11/2026 por teste offline do `ash.py`, sem AWS (`tests_harness/test_emulador_ash.py`); a publicação real continua exigindo conta real |
| AC-21 | `teardown` depois do `bootstrap` | Stacks de métricas e de protótipo removidas; buckets de código e de protótipo mantidos | **[A TESTAR]**; continua exigindo conta real: o suporte do emulador a CloudFormation e CDK não está confirmado (L3) |
| AC-22 | `ci` com o perfil `python` ativo | Mesmas cinco etapas e mesmo resultado do CI anterior ao perfil | **[TESTADO]** em Linux em 13/11/2026 |
| AC-23 | `perfil modelo` ou `ash-perfil.json` ainda com `modelo: true` | Recusa com instrução de copiar e preencher | **[TESTADO]** em Linux em 13/11/2026 |
| AC-24 | Perfil que redefine `spec-gate` ou `rastreio` | Recusa | **[TESTADO]** em Linux em 13/11/2026 |
| AC-25 | Rastreio com `arquivos_teste` de outra linguagem e citação `<ID> CA-NN` em comentário | Critério encontrado | **[TESTADO]** em Linux em 13/11/2026 |
| AC-26 | Squad com perfil novo (não Python) do zero até o merge no Kiro | CI verde e merge pelo portão | **[A TESTAR]** |
| AC-27 | `python ash.py testar-harness` (testes de `tests_harness/` com o pytest da `.venv-tools`: perfil, certificados, `ASH_PULAR` do núcleo, ator do CI e rastreio de outra linguagem) e etapa `harness` do perfil | Todos passam em qualquer stack; a etapa `harness` ({python} ash.py testar-harness) é do perfil, não do núcleo, e todo perfil a leva | **[TESTADO]** em Windows em 13/11/2026 (`testar-harness` verde, hoje com 170 testes, depois de acrescentar a integração com o emulador, a separação entre o perfil `python` e o `python-aws` e a auditoria das ferramentas; passam com qualquer um dos dois perfis ativos, verificado nos dois) |
| AC-28 | `python ash.py emulador iniciar`, `status`, `parar` e `reset`, em cada modo (`linux`, `wsl`, `container`): sobe, espera o health check, prova que é local, mostra modo, tempo de vida e prazo de inatividade, para e confirma que não sobra processo (`wsl --list --running`, `docker ps`, `pgrep`) | Ciclo completo sem processo restante; sem modo disponível, `iniciar` explica o que falta em cada modo e sai com código 1 | **[A TESTAR]** o ciclo em cada modo: no ambiente de preparo (Windows) não havia modo utilizável (o modo `linux` só existe em Linux, não havia distribuição WSL2 própria e o daemon do runtime de contêiner estava parado), e o ASH não instala runtime. **[TESTADO]** em 13/11/2026: `emulador iniciar` sem modo disponível lista o motivo de cada modo e sai com código 1, `emulador status` mostra a linha "Emulador AWS: parado" e os modos, e a lógica de início, parada e detecção com dublês (`tests_harness/test_emulador.py`) |
| AC-29 | Isolamento: o ambiente do processo filho não tem credencial real, aponta só para `https://127.0.0.1:<porta>` com as credenciais e o certificado do emulador, e `~/.aws/config` e o ambiente do próprio `ash.py` ficam intactos; o `conftest.py` aborta se o `sts` não responder como emulador | Nenhuma chamada sai do emulador; nenhuma chave aparece em saída ou arquivo versionado | **[TESTADO]** em 13/11/2026 a construção e a validação do ambiente, as provas de endpoint e de credencial e o abort do `conftest.py` sem ambiente (offline, com dublês e `pytest tests_harness_integracao` direto, que aborta antes de qualquer chamada); **[A TESTAR]** a prova contra um emulador real (`sts get-caller-identity` com conta `000000000000`) |
| AC-30 | No perfil `python-aws`: `python ash.py etapa integracao-aws` com o emulador parado; `ASH_PULAR=integracao-aws python ash.py ci` | Falha com "Emulador AWS não está de pé. Rode: python ash.py emulador iniciar" e código 1; o CI pulado sai com código 3 e o merge recusa | **[TESTADO]** em Windows em 13/11/2026, com o perfil `python-aws` ativado de verdade (`perfil python-aws`) e depois devolvido (`perfil python`): mensagem e código 1 na etapa isolada; `ci` completo sem emulador com só `integracao-aws FALHOU` e código 1; `ASH_PULAR=integracao-aws`: código 3 |
| AC-31 | Ingestão: a Lambda `ingest` (S3 para DynamoDB) contra o emulador, com o handler em processo | Linhas válidas viram itens, linha inválida é contada, segunda execução é idempotente | **[A TESTAR]** (`tests_harness_integracao/test_ingest_lambda.py` escrito, para `python ash.py testar-harness --integracao`; precisa de emulador de pé) |
| AC-32 | Relatório: a Lambda `report` (DynamoDB para S3) contra o emulador, com o handler em processo | `relatorio.csv` e `relatorio.html` em `reports/semana=AAAA-Www/` | **[A TESTAR]** (`tests_harness_integracao/test_report_lambda.py` escrito, para `python ash.py testar-harness --integracao`; precisa de emulador de pé) |
| AC-33 | Backup: `ash.py backup` contra um S3 local | `bundles/<repo>/<repo>-<data>.bundle` e `latest.bundle` no bucket do emulador | **[A TESTAR]** (`tests_harness_integracao/test_backup_s3.py` escrito, para `python ash.py testar-harness --integracao`; precisa de emulador de pé e do AWS CLI) |
| AC-34 | Regra de fidelidade por faixa (só em perfis que declaram `emulador_aws`, como o `python-aws`; o `python` padrão não a tem): o `ci_executado` registra `emulador`, `emulador_versao` e `servicos_abaixo_do_corte`; o `merge` exige o papel `homologacao` no commit atual para faixa crítica e para semiautônoma com serviço abaixo do corte; o portão `aprovar-homologacao` guarda a evidência | Merge recusado sem homologação ou com homologação de outro commit | **[TESTADO]** em 13/11/2026 a evidência no evento, a regra por faixa, a checagem do commit e o registro da evidência (testes offline do harness); **[A TESTAR]** o fluxo completo `aprovar-homologacao` e `merge` no Kiro com uma spec real |
| AC-35 | Nenhuma chave do emulador, e-mail ou nome da configuração local em arquivo versionado nem em saída | `git grep --untracked` sem ocorrência; `.ash/emulador/` e `.ash/config.env` fora do git | **[TESTADO]** em 13/11/2026 (`git grep --untracked` sem ocorrência de chave no formato do emulador, e-mail e nome fictícios, nome de usuário do sistema e frases de conversa; teste `test_nenhuma_chave_do_emulador_em_arquivo_versionado`) |
| AC-36 | Com o perfil `python` padrão ativo, `python ash.py ci` numa máquina sem emulador, sem Docker em execução e sem WSL próprio | `CI LOCAL: OK` e código 0, sem consultar o emulador; `ci_executado` com `emulador: nao_aplicavel` | **[TESTADO]** em Windows em 13/11/2026 (execução real: código 0 com `spec-gate`, `testes`, `sast`, `dependencias`, `harness` e `rastreio` verdes, e `emulador status` mostrando nenhum modo utilizável; mais o teste `test_ac36_ci_do_perfil_python_padrao_sai_com_zero_sem_emulador`, que falha se o `ci` consultar o emulador) |
| AC-37 | `python ash.py perfil python-aws` e depois `python ash.py perfil python` | O `python-aws` acrescenta a etapa `integracao-aws` e o bloco `emulador_aws` e avisa (`boto3` ausente do `requirements.txt`, perfil não testado); a volta deixa o `ash-perfil.json` byte a byte como estava, com o mesmo `git diff`; a etapa `testes` ignora `tests/integracao_aws/` | **[TESTADO]** em Windows em 13/11/2026 (hash do arquivo e hash do `git diff` iguais antes da ida e depois da volta; o ensaio achou e corrigiu a troca de LF por CRLF que o `perfil` fazia no Windows). **[A TESTAR]** o esqueleto `templates/tests-integracao-aws/` e o `python-aws` numa aplicação que realmente use AWS e com um emulador de pé |
| AC-38 | `python ash.py testar-harness --auditoria` (D19): `pip-audit -r requirements-tools.txt` sem ignorar nada, comparado com `tests_harness/auditoria_ferramentas.json` | Mostra três listas (CVEs novos, aceites vencidos, aceites que podem sair); código 1 com CVE novo ou aceite vencido, 2 se não conseguiu auditar, 0 nos demais casos; nunca roda no CI de um projeto; o `publicar-harness` avisa (sem bloquear) quando `requirements-tools.txt` ou o arquivo de aceites mudam ou há aceite vencido | **[TESTADO]** em Windows em 13/11/2026: execução real (rede e `pip-audit` reais) com `AUDITORIA: OK`, 6 aceites em vigor, nenhum CVE novo, vencido ou apto a sair, e o Semgrep mais recente consultado no PyPI (1.185.0); lógica com dublês do `pip-audit` e do PyPI, sem rede, em `tests_harness/test_auditoria.py` (CVE novo, aceite vencido, aceite que pode sair, PyPI fora do ar, falha do `pip-audit`, arquivo inválido, prazo de 90 dias, papel sem nome de pessoa, a auditoria fora do CI e o aviso do `publicar-harness`). **[A TESTAR]** o dia em que o Semgrep publicar versão com as dependências corrigidas (a lista "podem sair" com dado real) |

## 13. Lacunas

| Lacuna | Quem responde | Bloqueia? |
|---|---|---|
| Comportamento padrão de permissão sem regra | Observar no Kiro | Não |
| Residência de dados: o Kiro processa nas geografias EUA ou Europa | Jurídico e Segurança da Informação do cliente | Conversa com cliente regulado |
| Serviços em sa-east-1 | Compass (FDE), na lista regional oficial | Deploy em sa-east-1 |
| Tags canônicas e centro de custo | Compass com o cliente | Bootstrap |
| Plataforma Git definitiva da squad | Cliente | Migração do versionamento |
| Licenças do Semgrep CE e do pip-audit para uso em cliente | Compass com o jurídico do cliente | Uso em cliente |
| Fase de descoberta ponta a ponta no Kiro (product-lead, aprovar-prd, nova-descoberta, publicar-proto) | Compass (FDE) | Demo da descoberta |
| Separação de funções com duas pessoas reais na faixa crítica | Squad do cliente, com um Dev revisor nomeado | Uso em cliente regulado |
| `AshProtoStack` em região diferente de us-east-1 | Compass (FDE) | Deploy em sa-east-1 |
| Primeiro perfil de stack além de Python, testado de ponta a ponta no Kiro (AC-26) | Compass (FDE) | Primeiro cliente fora de Python |
| Regras de SAST para linguagens além de Python (as de `.semgrep/` são de Python) | Compass (FDE) | Primeiro cliente fora de Python |
| Lentes de outros setores, com fonte para cada regra regulatória | Compass com cada frente | Primeiro cliente do setor |
| AWS Emulator: lacunas L1 a L12 (WSL não citado pela AWS, ociosidade do WSL, notas de fidelidade, CDK e CloudFormation, nenhum modo executado de ponta a ponta, Podman não testado, homologação só declarada, `python-aws` nunca rodou numa aplicação real, vulnerabilidades transitivas do Semgrep no `requirements-tools.txt`), detalhadas na seção 5.4.4 | Compass (FDE) | Uso do emulador como evidência além da faixa autônoma |
| Rede do cliente com inspeção TLS: exige o `.pem` corporativo instalado; a limpeza do `ash.py` não resolve esse caso | TI do cliente | `setup` e etapa `dependencias` do CI |
| Limpeza de certificados testada no Windows com gerenciamento corporativo | Compass (FDE) | Não |

## 14. Fontes (20/10/2026)

- https://kiro.dev/docs/custom-agents/
- https://kiro.dev/docs/custom-agents/configuration-reference/
- https://kiro.dev/docs/custom-agents/subagents/
- https://kiro.dev/docs/steering/
- https://kiro.dev/docs/hooks/ e https://kiro.dev/docs/hooks/types/
- https://kiro.dev/docs/specs/
- https://kiro.dev/docs/enterprise/supported-regions/
- https://kiro.dev/docs/privacy-and-security/data-protection/
- https://kiro.dev/pricing

Adicionadas em 13/11/2026 (AWS Emulator, WSL e Docker; lista completa, com o que cada uma sustenta, na seção 5.4.1):

- https://docs.aws.amazon.com/emulator/latest/userguide/ (páginas what-is-service, setting-up, getting-started-linux, getting-started-docker, point-sdk-to-emulator, cli-reference, fidelity, versioning, security)
- https://github.com/aws/aws-emulator e https://github.com/aws/aws-emulator/releases
- https://aws.amazon.com/blogs/aws/test-your-applications-against-aws-locally-with-aws-emulator/
- https://aws.amazon.com/about-aws/whats-new/2026/11/aws-emulator-now-available/
- https://downloads.aws.com/aws-emulator/packages/aws-emulator/LTS/ (HEAD de leitura dos pacotes 1.0.343)
- https://learn.microsoft.com/en-us/windows/wsl/basic-commands, /filesystems, /wsl-config e /networking
- https://docs.docker.com/subscription/desktop-license/

Adicionadas em 12/11/2026:

- https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works-resources.html
- https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_wafv2/CfnWebACLProps.html
- https://aws.amazon.com/waf/pricing
