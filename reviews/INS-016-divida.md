# Revisão de dívida técnica · INS-016 · Histórico de endossos

- Spec: INS-016 (front matter: `id: INS-016`, faixa `semiautonoma`, versão 2, status aprovada).
- Branch: `feat/ins-016`. Diff: `git diff main...HEAD`.
- Escopo: `src/endosso/api.py`, `src/endosso/regras.py`, `src/endosso/repositorio.py` e os testes `tests/test_ins_016_dominio.py`, `tests/test_ins_016_historico_endossos.py`.
- Convenções conferidas: `.kiro/steering/03-stack-cliente.md` (regra de negócio pura separada do HTTP; monetário em `decimal.Decimal`, nunca `float`), design em `.kiro/specs/ins-016-historico-endossos-v2/design.md`.
- Eu não corrijo código. O parecer é só diagnóstico; cada item traz arquivo, linha e esforço (P, M, G).

Esforço: P = pontual (poucos minutos, um ponto só). M = médio (um arquivo, alguns pontos). G = grande (vários arquivos ou decisão de design).

## Resumo

A mudança está limpa e bem separada em três camadas, como o design pede: `regras.py` concentra domínio puro (projeção, ordenação, montagem), `repositorio.py` guarda a massa sintética e `api.py` só valida formato, orquestra e serializa. Não há vazamento de regra de ordenação para o HTTP, não há `float` em dinheiro e a projeção de seis campos protege contra dado pessoal da trilha. Os achados abaixo são de higiene e manutenção futura; **nenhum é bloqueio**.

## Achados

### 1. Duplicação de `CENTAVOS` em dois módulos: melhoria não-bloqueante (M)
- `src/endosso/regras.py:9`, `CENTAVOS = Decimal("0.01")`.
- `src/endosso/api.py:22`, `CENTAVOS = Decimal("0.01")` (reintroduzido pela INS-016).
- A mesma constante monetária existe agora no domínio e na camada HTTP. A INS-014 já a tinha em `regras.py`; a INS-016 criou uma segunda cópia em `api.py` em vez de importar a existente. Duas fontes da mesma verdade monetária são exatamente o tipo de divergência silenciosa que a lente de serviços financeiros pede para evitar (a regra de arredondamento deve ser única e explícita). Risco baixo hoje (mesmo literal), mas se uma mudar e a outra não, a serialização e o cálculo passam a divergir. Sugestão de direção: importar a constante do domínio em `api.py`.

### 2. `CAMPOS_ITEM_ENDOSSO` é código morto: melhoria não-bloqueante (P)
- `src/endosso/regras.py:50-57`, a tupla `CAMPOS_ITEM_ENDOSSO` é definida com um comentário que diz ser a allowlist de campos, mas nada no código a usa. A proteção contra dado pessoal vem, na prática, da cópia explícita campo a campo em `project_endorsement` (`regras.py:72`) e em `_serializar_item` (`api.py:81`). A constante dá a falsa impressão de ser a fonte da projeção. Ou ela passa a dirigir a projeção, ou vira ruído que confunde quem mantém. Hoje é dívida de clareza, não de comportamento.

### 3. Lista de seis campos repetida em três lugares: melhoria não-bloqueante (M)
- `src/endosso/regras.py:50-57` (`CAMPOS_ITEM_ENDOSSO`), a dataclass `EndorsementItem` (`regras.py:61-69`), `project_endorsement` (`regras.py:72`) e `_serializar_item` em `src/endosso/api.py:81`.
- O contrato de saída (os seis campos) está escrito por extenso em quatro pontos: a dataclass, a tupla morta, a projeção e a serialização. Acrescentar ou renomear um campo do histórico obriga a tocar todos. Para a demo é aceitável; como padrão que outras specs vão copiar, é acoplamento por repetição. Sugestão de direção: derivar a serialização dos campos da dataclass (ex.: `dataclasses.asdict` ou iterar os `fields`) para ter uma fonte só.

### 4. `quantize` monetário mora na camada HTTP: melhoria não-bloqueante (M)
- `src/endosso/api.py:76-78`, `_serializar_valor` faz `valor.quantize(CENTAVOS)` (linha 78).
- Formatar `Decimal` como string de duas casas é, em parte, apresentação (cabe no HTTP). Mas `quantize` é uma decisão de representação monetária, e o CA-05 exige preservar o valor gravado "sem recálculo". Hoje os valores da massa já têm duas casas, então o `quantize` não muda nada; se um dia a trilha trouxer um valor com mais casas, quem decide o arredondamento é a camada HTTP, longe da regra monetária do domínio. A convenção do projeto manda a regra monetária ficar no domínio puro. Risco baixo hoje, mas é um ponto onde a fronteira domínio/HTTP fica borrada. Sugestão de direção: a quantização/normalização monetária nascer no domínio (em `project_endorsement` ou num helper de `regras.py`), deixando o HTTP só com `str(...)`.

### 5. Acoplamento à forma em `dict` do registro bruto da trilha: melhoria não-bloqueante (M)
- `src/endosso/regras.py:72` (`project_endorsement`) lê chaves literais do `dict` (`registro["endorsement_id"]`, `registro["date"]`, ...); `src/endosso/repositorio.py:31-55` (`semear_historico`) produz esses `dict`; `endossos_de` devolve `list[dict]`.
- O domínio conhece o layout exato do `dict` bruto da trilha. Se o formato da trilha de auditoria mudar (renomear chave, aninhar), quebra dentro do domínio por `KeyError`, sem mensagem de contexto. Não há validação de chave ausente nem de tipo. Para massa sintética controlada é tolerável; num adaptador real de trilha de auditoria, essa fronteira pediria um tradutor explícito ou um `.get` com erro claro. Classifico como acoplamento aceitável na demo, a vigiar quando a trilha deixar de ser em memória.

### 6. Consistência de tipos da data depende de disciplina da massa: melhoria não-bloqueante (P)
- `src/endosso/regras.py:72` (`project_endorsement`) copia `registro["date"]` sem garantir que seja `datetime` tz-aware; `src/endosso/api.py:73` (`_serializar_data`) faz `item.date.astimezone(timezone.utc)`.
- O contrato depende de a data chegar como `datetime` tz-aware em UTC. A massa sintética cumpre isso (`repositorio.py:32`, `tzinfo=timezone.utc`), então o `.astimezone` funciona. Mas uma data naive (sem fuso) passaria pela projeção e só falharia na serialização, ou pior, produziria um deslocamento silencioso. Não há ponto único que afirme "a data é UTC tz-aware". Como `date` é a única exigência de fuso do contrato (CA-02), vale uma guarda explícita no domínio no futuro. Hoje, sem bug, porque a única fonte é a massa controlada.

### 7. `x_solicitante` recebido e descartado no endpoint de leitura: melhoria não-bloqueante (P)
- `src/endosso/api.py:94`, `historico_endossos(..., x_solicitante: str = Header(default="canal-app"))` declara o header mas nunca o usa.
- A consulta é somente leitura e a spec (bloco 6) não pede trilha de quem consultou, então não é falta funcional. Mas um parâmetro recebido e ignorado é um gancho sem dono: ou sinaliza intenção futura de auditar a consulta (e aí falta o registro), ou é cópia do endpoint de escrita que não serve aqui. Vale decidir e documentar a intenção, para não virar um `TODO` implícito.

## Observações que não são dívida

- Não encontrei `float` em caminho monetário: tudo em `Decimal` no domínio e string na saída. Alinhado à convenção e ao CA-05.
- Não encontrei `TODO`/`FIXME` sem dono no código tocado.
- A regra de ordenação com desempate está inteira no domínio (`sort_endorsements`, `regras.py:84`); o HTTP não reordena. Separação domínio/HTTP preservada nesse ponto.
- Não há função longa demais: a maior é `semear_historico` (`repositorio.py:31-55`), que é só dados, sem ramificação.
- A trilha de auditoria de escrita (`aplicar_endosso`, `repositorio.py`) registra quem/quando/antes/depois, atendendo a lente de serviços financeiros; a INS-016 não a alterou.

## Conclusão

Nenhum bloqueio de dívida técnica. Os sete achados são melhorias não-bloqueantes: as de maior retorno são a **duplicação de `CENTAVOS`** (item 1) e o **`quantize` monetário fora do domínio** (item 4), por tocarem a regra monetária, que a lente de serviços financeiros pede manter única e no domínio. Os demais são higiene (código morto, repetição do contrato, acoplamento ao `dict`, guarda de fuso e header ocioso) e podem ser endereçados quando a trilha deixar de ser uma demo em memória. A entrega pode seguir no fluxo da faixa `semiautonoma`.
