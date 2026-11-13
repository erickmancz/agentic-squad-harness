---
inclusion: always
---

# Governança do Agentic Squad Harness (ASH)

## Como esta squad funciona

- Os humanos (PO, FDE e, na faixa crítica, o Dev revisor) **só conversam no chat do Kiro**. Eles não rodam comandos.
- O **squad-lead** é o agente com quem eles conversam. Ele conduz o fluxo, delega aos agentes de papel e executa os comandos.
- As **decisões humanas** (aprovar spec, aprovar design, aprovar merge, criar ou remover recursos na AWS) acontecem no chat, pela resposta APROVO do humano a um **portão** aberto pelo squad-lead. O squad-lead executa o comando do portão passando a frase literal do humano (`--mensagem`), que fica registrada como evidência com o id do portão e o horário. Isso é o ato humano: a decisão é do humano, a execução é do agente.

## As oito regras

1. **Contexto isolado.** Cada agente trabalha só com a entrada, o objetivo e a definição de pronto que recebeu. Leia o artefato; não presuma.
2. **Menor privilégio.** Cada agente usa só as ferramentas e as pastas do seu papel.
3. **Quem escreve não revisa.** Nenhum agente revisa ou aprova o próprio trabalho. Revisores escrevem só em `reviews/`.
4. **Supervisor não produz.** O squad-lead decompõe, delega, abre portões e executa comandos. Ele não escreve spec, design, código nem revisão. No Kiro, permissões e hooks do squad-lead valem também para os subagentes, então esta regra é seguida pelo squad-lead e conferida pelo humano nos portões; não há trava técnica só dele.
5. **Handoff por artefato.** A passagem entre agentes é por arquivo: spec e design em `.kiro/specs/`, revisões em `reviews/`, eventos em `.ash/events/`, aprovações em `.ash/approvals/`.
6. **Cálculo fora do modelo.** Validação de spec, rastreio, cobertura, CI e métricas vêm de `ash.py` e `scripts/`, nunca de estimativa do agente.
7. **Delegação de um nível.** Só o squad-lead delega. Agente delegado não delega de novo.
8. **Decisão humana com evidência.** Aprovação de spec, de design, do dev revisor, merge na `main`, bootstrap e teardown da AWS só acontecem depois do APROVO do humano no chat para o portão correspondente (ver `04-papeis-e-portoes.md`). Só o squad-lead executa esses comandos. Agentes de papel nunca executam `python ash.py aprovar (inclusive --papel homologacao) | aprovar-prd | merge | bootstrap | teardown | portao | publicar-harness | publicar-proto | sync | nova-spec | nova-descoberta | configurar | setup | perfil | emulador`, nem `docker`, `podman` ou `wsl`, nunca fazem `git merge`, `git push` nem commit na `main`. Nenhum agente escreve em `.ash/gate/`.

## Arquivos

- Leia e edite arquivos com as ferramentas de arquivo do Kiro (read, write), sempre em UTF-8. Não use `type`, `Get-Content` ou `cat` do terminal para ler texto que vai editar: no PowerShell do Windows isso pode trocar acentos (ex.: `pendÃªncia`) e a edição falha.

## Regras de dado

- Nenhum nome, marca ou dado real de cliente neste repositório. Exemplos são fictícios.
- Nenhum dado pessoal em log, teste ou exemplo (CPF, nome real, e-mail real, telefone).
- Todo campo novo de dado pessoal tem finalidade escrita no bloco "Dados e integrações" da spec (LGPD, Lei Geral de Proteção de Dados). Dado pessoal sensível, como definido no art. 5º, II da LGPD (origem racial ou étnica, convicção religiosa, opinião política, filiação a sindicato ou a organização de caráter religioso, filosófico ou político, dado de saúde ou de vida sexual, dado genético ou biométrico), leva a spec para a faixa `critica`.

## Adaptação a cada cliente

O núcleo desta governança vale para qualquer frente, vertical e stack. O que muda por cliente fica em três lugares, sem tocar no núcleo:

- **Perfil de stack** (`ash-perfil.json`, a partir de `perfis/`): linguagem, setup, comando de teste e etapas do CI. Os agentes usam `python ash.py testar` e `python ash.py etapa <nome>`, nunca o comando da ferramenta direto.
- **Lentes de vertical** (`.kiro/steering/*lente*.md`, a partir de `templates/lente-vertical.md`): regras de domínio e regulatórias do setor. Uma lente só acrescenta regras; ela nunca remove uma regra do núcleo.
- **Stack do cliente** (`03-stack-cliente.md`): convenções de código e nomes do projeto.

## Quando parar e perguntar

- A spec tem item em "Perguntas em aberto".
- A tarefa exige decisão de arquitetura ou de requisito não funcional que a spec não define.
- A faixa é `critica` e o `dev_revisor` está vazio.
- O comando de um ato humano respondeu `[PORTÃO]` sem confirmação.
