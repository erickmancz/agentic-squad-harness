---
inclusion: always
---

# Stack do projeto

A stack vem do **perfil de stack ativo**, em `ash-perfil.json`. Rode `python ash.py perfil` para ver qual está ativo e quais existem em `perfis/`. O template vem com o perfil `python`, testado de ponta a ponta. Para outra stack, o FDE cria `perfis/<stack>.json` a partir de `perfis/modelo.json`, ativa com `python ash.py perfil <stack>` e publica pelo portão `publicar-harness`.

Preencha a tabela abaixo por cliente. Os valores são o padrão do template, que corresponde ao perfil `python`.

| Item | Valor padrão |
|---|---|
| Perfil de stack | `python` (Python 3.12, FastAPI, pytest com cobertura, Semgrep, pip-audit) |
| Cobertura mínima | 80%, definida no perfil (`cobertura_minima`) |
| Versionamento | Repositório da squad em `ASH_GIT_REMOTE` (origin, GitHub ou Bitbucket); backup opcional por `git bundle` em S3 |
| Plataforma Git do cliente | Definir no início do projeto (GitHub ou Bitbucket) |
| Padrão de nomes | Código e variáveis em inglês; textos de spec e revisão em português |
| Pasta de código | `src/` (campo `pasta_codigo` do perfil) |
| Pasta de testes | `tests/` (campos `pasta_testes` e `arquivos_teste` do perfil) |

## Convenções de código (valem para qualquer stack)

- Regra de negócio fica em funções ou classes sem efeito colateral, separadas da camada de entrada (HTTP, fila, tela, job).
- Valor monetário nunca usa ponto flutuante binário: `decimal.Decimal` em Python, `BigDecimal` em Java, `decimal` em C#, biblioteca decimal ou inteiro em centavos em JavaScript e TypeScript.
- Toda função ou método público tem documentação de uma linha.
- Os testes citam `<ID da spec> CA-NN` no nome, na docstring ou em comentário, para o rastreio de aceite.
- Rode os testes com `python ash.py testar` e as etapas isoladas com `python ash.py etapa <nome>`. Não chame a ferramenta de teste direto: assim o mesmo agente serve para qualquer stack.
- O perfil `python` padrão não usa o AWS Emulator: o `ci` dele sai com código 0 sem emulador. Projetos que chamam serviços AWS usam o perfil `python-aws` (`python ash.py perfil python-aws`), que declara o bloco `emulador_aws` e a etapa `integracao-aws` (campo `requer: emulador_aws`) com testes em `tests/integracao_aws/` (esqueleto em `templates/tests-integracao-aws/`) que usam só o SDK, e declaram o `boto3` com versão exata no `requirements.txt` do projeto (a etapa `dependencias` só audita esse arquivo; o `perfil` e o `ci` avisam se faltar). Os testes de integração do próprio ASH (Lambdas de `infra/` e backup) ficam em `tests_harness_integracao/` e rodam por `python ash.py testar-harness --integracao`, fora do CI. O emulador sobe por `python ash.py emulador iniciar` (modos `linux`, `wsl` e `container`, escolhidos por `ASH_EMULADOR_MODO` em `.ash/config.env`); regras em `06-emulador-aws.md`, passo a passo no `README.md` e fontes na spec (seção 5.4). Docker Desktop é opcional: o ASH funciona sem ele pelos modos `linux` e `wsl`, ou com Podman. Licenciar e instalar um runtime de contêiner é decisão de cada cliente ou usuário (o Docker Desktop é gratuito só para uso pessoal, educação, open source não comercial e empresas com menos de 250 funcionários e menos de US$ 10 milhões de receita anual; fonte e data na spec). O template não leva dado de pessoa nem de conta: credenciais do emulador, login de runtime, nomes e e-mails da squad ficam em `.ash/config.env` e `.ash/emulador/`, fora do git.
- **Checklist do autor do harness antes do `publicar-harness`:** `python ash.py testar-harness`; `python ash.py testar-harness --integracao` se a mudança tocar o emulador, o CI por etapas, o backup, as Lambdas de `infra/` ou a versão do emulador; `python ash.py testar-harness --auditoria` se tocar `requirements-tools.txt`, o arquivo de aceites ou as ferramentas do harness. As duas variantes ficam fora do CI de qualquer projeto. CVE novo ou aceite vencido nas ferramentas do harness exige decisão do autor do harness: nenhum agente cria, edita nem prorroga aceite em `tests_harness/auditoria_ferramentas.json`, e nenhum agente troca versão de ferramenta do harness para "limpar" a auditoria. O aceite vale para o template; cada cliente revalida com o seu time de segurança (README, "Riscos aceitos nas ferramentas do harness").
- Os testes do próprio ASH ficam em `tests_harness/` e rodam por `python ash.py testar-harness` (pytest da `.venv-tools`), em qualquer stack. Todo perfil leva a etapa `harness` com esse comando. Só o squad-lead o roda; o implementador não edita `tests_harness/`.
