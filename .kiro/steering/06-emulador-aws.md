---
inclusion: always
---

# AWS Emulator: regras para os agentes

O AWS Emulator é um emulador local das APIs da AWS. O ASH o usa para rodar testes de integração sem conta AWS, em dois lugares que não se misturam: (1) os testes de integração **do próprio ASH** (`tests_harness_integracao/`, por `python ash.py testar-harness --integracao`), fora do CI de qualquer projeto; (2) os testes de integração **da aplicação do cliente** (`tests/integracao_aws/`, etapa `integracao-aws`), só no perfil `python-aws`. O perfil `python` padrão não usa o emulador: o `ci` dele sai com código 0 sem emulador, e nenhum agente deve criar etapa, teste ou dependência que o torne obrigatório num projeto sem AWS. Desenho, decisões, fontes com data de consulta, testes e lacunas: `docs/spec-ash-v4.md`, seção 5.4. Passo a passo de instalação e de primeira execução: `README.md`, seção "Testes contra o AWS Emulator".

## Regras que valem sempre

1. **Nunca toque conta AWS real.** Nenhum agente roda `aws`, `cdk`, `bootstrap`, `teardown` nem `publicar-proto` para fins de teste. Os testes de integração usam só o SDK (boto3), apontado para o emulador. Um projeto que usa AWS declara o `boto3` com versão exata no `requirements.txt` dele (a etapa `dependencias` só audita esse arquivo).
2. **Nunca imprima, copie nem versione chaves.** O emulador gera chaves novas a cada início e as grava só em `.ash/emulador/` (fora do git). Nenhum comando, teste, log, mensagem ou documento mostra o conteúdo de `emulator_credentials`. O `ash.py` confere só o prefixo `EMULATOR` do ID da chave, em memória.
3. **Só o `ash.py` inicia o emulador, e só quando alguém manda.** O emulador sobe por `python ash.py emulador iniciar` (ou pelo `ci`, se `ASH_EMULADOR_AUTO=sim`). Nunca instale como serviço (systemd, init, serviço do Windows), nunca crie tarefa agendada, atalho de inicialização nem qualquer início automático com o Windows ou com o WSL, e nunca altere o `.wslconfig` do usuário (em especial, nunca `vmIdleTimeout=-1`).
4. **Todo emulador tem prazo de inatividade.** O `ash.py` sempre usa `--idle-timeout` (padrão 1800 s, `ASH_EMULADOR_IDLE`).
5. **Pare o que você subiu.** Quando o `ci` ou a etapa `integracao-aws` sobe o emulador, o próprio comando o para ao final, com sucesso ou falha. Se o emulador já estava de pé, deixe como estava. Ao terminar uma sessão de trabalho em que você o iniciou à mão, rode `python ash.py emulador parar`.
6. **O emulador não valida segurança.** Ele não avalia políticas IAM nem as baseadas em recurso. Nunca use o resultado dele como prova de segurança. Para isso vale a regra de fidelidade por faixa (`01-faixas-autonomia.md`).

## Quem pode rodar o quê

| Comando | Quem |
|---|---|
| `python ash.py emulador iniciar \| parar \| status \| reset` | Só o squad-lead (ou o agente que conduz a sessão). Comando livre, sem portão, porque não toca conta real |
| `python ash.py etapa integracao-aws` e `python ash.py ci` | squad-lead; o `implementador` também roda `etapa integracao-aws` (só existe no perfil `python-aws`), com o emulador já de pé |
| `python ash.py testar-harness --integracao` | Só o squad-lead ou o autor do harness, antes do `publicar-harness` quando a mudança toca o emulador, o CI por etapas, o backup ou as Lambdas de `infra/`. Agentes de papel não rodam. O `publicar-harness` avisa (sem bloquear) quando os arquivos mudados pedem essa execução |
| `docker`, `podman`, `wsl` no shell do agente | Ninguém. Os runtimes são chamados por dentro do `ash.py`; o hook e as listas de negação dos agentes bloqueiam |
| `python ash.py aprovar ID --papel homologacao ...` | Só o squad-lead, depois do APROVO do humano no portão `aprovar-homologacao` |
| Escrever em `tests/integracao_aws/` (testes de integração do projeto) | `implementador`, como em qualquer pasta de `tests/` |
| Escrever em `tests_harness/` e `tests_harness_integracao/` (testes do próprio ASH) | Ninguém entre os agentes de papel; são do autor do harness |

Os agentes de papel (intake-spec, planejador, implementador, revisores, product-lead, designer-proto) nunca iniciam, param nem reiniciam o emulador.

## Quando o emulador não está de pé

A etapa `integracao-aws` (perfil `python-aws`) e o `testar-harness --integracao` falham com a mensagem "Emulador AWS não está de pé. Rode: python ash.py emulador iniciar". Isso é o comportamento esperado, não um defeito. Com o perfil `python` padrão, nada disso se aplica: o `ci` não consulta o emulador.

1. O squad-lead roda `python ash.py emulador status`: a linha "Emulador AWS" diz o modo e, se não há modo utilizável, `emulador status` lista o motivo de cada um (por exemplo, Docker instalado mas parado, nenhuma distribuição WSL2 própria, pacote nativo ausente).
2. Se há um modo disponível, `python ash.py emulador iniciar` e repetir.
3. Se não há nenhum modo e o humano não puder instalar um, o squad-lead avisa e **não** finge sucesso: `ASH_PULAR=integracao-aws` é possível, mas o CI sai com código 3 e o merge recusa. Nunca contorne trocando o endpoint por uma conta real.
4. Não instale WSL, Docker nem Podman por conta própria: licenciar e instalar o runtime é decisão do cliente ou do usuário da máquina (nota de licença no README).

## Quando a etapa `integracao-aws` falha com o emulador de pé

Leia a mensagem do `pytest`. Uma operação que o emulador ainda não implementa devolve HTTP 501 (`NotImplemented`): é uma lacuna do emulador, registrada na spec, e não motivo para chamar a AWS. Abortos do tipo "endpoint não local" ou "credenciais não são as do emulador" são proteção: pare e avise o humano.

## Dados e configuração por máquina

O template não leva dado de pessoa nem de conta. Credenciais do emulador, login de runtime de contêiner, nomes e e-mails da squad são configurados em cada máquina e ficam fora do git (`.ash/config.env` e `.ash/emulador/`). Nunca escreva esses valores em arquivo versionado, em spec, em revisão ou em teste.
