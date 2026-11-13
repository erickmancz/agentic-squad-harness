# Revisão de documentação · INS-016 · Histórico de endossos

- Spec: `.kiro/specs/ins-016-historico-endossos-v2/` (id INS-016, versão 2, faixa semiautonoma, status aprovada).
- Branch: `feat/ins-016`.
- Escopo desta revisão: documentação (docstrings, coerência código x design.md, README). Não edito código nem README.
- Artefatos lidos: `src/endosso/api.py`, `src/endosso/regras.py`, `src/endosso/repositorio.py`, `design.md`, `README.md`, `03-stack-cliente`.

## Conclusão

**Sem bloqueio.** A documentação de código atende à convenção do steering: toda função pública nova tem docstring de uma linha, as docstrings citam os CA certos e descrevem o comportamento corretamente. Há, porém, **três apontamentos não bloqueantes** que recomendo tratar: uma divergência real entre o design (inglês, rota `/policies`, pasta `src/endorsements`) e a implementação (português, rota `/apolices`, pasta `src/endosso`) que **não está documentada nem justificada**, o módulo `api.py` com docstring de cabeçalho que cita só INS-014, e a ausência de qualquer menção no README à nova rota de consulta.

## 1. Funções públicas sem docstring

Nenhuma função pública nova ficou sem docstring. Todas têm docstring de uma linha, conforme `03-stack-cliente`. Levantamento:

| Arquivo | Símbolo público | Docstring de 1 linha | CA citado |
|---|---|---|---|
| `regras.py` | `EndorsementItem` (dataclass) | sim | CA-02 |
| `regras.py` | `project_endorsement` | sim | CA-02, CA-05 |
| `regras.py` | `sort_endorsements` | sim | CA-01, CA-06 |
| `regras.py` | `build_history` | sim | CA-01, CA-06 |
| `repositorio.py` | `existe` | sim | CA-04 |
| `repositorio.py` | `endossos_de` | sim | INS-016 (sem CA específico) |
| `repositorio.py` | `semear_historico` | sim | INS-016 |
| `api.py` | `historico_endossos` (rota) | sim | CA-01, CA-03, CA-04 |

Observações de detalhe (não bloqueantes):

- Os helpers de serialização em `api.py` (`_serializar_data`, `_serializar_valor`, `_serializar_item`) têm prefixo `_` (privados), logo a docstring de uma linha não é obrigatória pela convenção. Ainda assim todos têm docstring e citam CA (CA-02, CA-05). Bom sinal.
- `CAMPOS_ITEM_ENDOSSO` em `regras.py` é declarada mas não é usada por nenhuma função do histórico. É constante de módulo com comentário explicativo; não é "função pública sem docstring", mas é documentação de um artefato que o código não exercita. Vale confirmar com o revisor de dívida se fica como contrato declarativo ou se deve ser removida.

## 2. Docstrings: corretude e citação dos CA

As docstrings descrevem o comportamento real e citam os CA pertinentes. Pontos verificados:

- `sort_endorsements` / `build_history`: a docstring afirma "data decrescente e, em empate, por endorsement_id decrescente (CA-01, CA-06)". O código usa `sorted(..., key=lambda e: (e.date, e.endorsement_id), reverse=True)`, que é exatamente isso. Correto.
- `_serializar_data`: docstring diz "ISO-8601 em UTC com sufixo Z (CA-02)". O código faz `astimezone(timezone.utc).isoformat().replace("+00:00", "Z")`. Correto e coerente com o exemplo do bloco 9 (`2026-02-10T13:45:00Z`).
- `project_endorsement` / `_serializar_valor`: docstrings dizem "sem recálculo" (CA-05). O código preserva o valor da trilha e só aplica `quantize(CENTAVOS)` para 2 casas, sem aritmética que altere o valor. Correto.
- `historico_endossos`: docstring cita CA-01, CA-03, CA-04. O comportamento de 404 para formato inválido/inexistente com mensagem genérica está descrito num comentário inline que remete aos blocos 6 e 7. Correto.

Nenhuma docstring foi encontrada descrevendo comportamento diferente do código.

## 3. Coerência entre design.md e implementação

Aqui está o apontamento principal. O `design.md` define, de forma explícita e repetida:

- Rota `GET /policies/{policy_number}/endorsements` (bloco 4 "Contrato do endpoint" e bloco 7).
- Pastas em inglês: `src/endorsements/domain.py`, `src/endorsements/repository.py`, `src/endorsements/api.py` (bloco 2 "Arquitetura").
- Identificadores em inglês (segue `03-stack-cliente`).

A implementação real diverge na rota e na pasta/módulo:

| Item | design.md | Implementação | Divergência |
|---|---|---|---|
| Rota | `/policies/{policy_number}/endorsements` | `/apolices/{numero}/endossos` | sim (inglês -> português) |
| Pasta/módulo | `src/endorsements/{domain,repository,api}.py` | `src/endosso/{regras,repositorio,api}.py` | sim (inglês -> português) |
| Nomes de função/variável | inglês | mistos: tipos/campos de contrato em inglês (`EndorsementItem`, `endorsement_id`, `coverage_before`), funções/rota de aplicação em português (`buscar`, `existe`, `aumentar_cobertura`, `/apolices`) | parcial |
| Regex do caminho | `^AP-\d{4}$` | `^AP-\d{4}$` | sem divergência |
| Contrato de saída (6 campos, nomes em inglês) | 6 campos | 6 campos idênticos | sem divergência |
| Ordenação, UTC/ISO-8601, Decimal sem recálculo, 404 genérico | definidos | implementados conforme | sem divergência |

Avaliação:

- A divergência de **pasta e rota** é real e **não está documentada nem justificada** em nenhum artefato: nem no `design.md`, nem num cabeçalho de módulo, nem numa seção de notas. O design chega a abrir uma "Dúvida para o FDE" sobre o hífen do número da apólice, mas **não registra a decisão de usar português na rota e na estrutura de pastas**. Para quem lê o design e depois o código, a rota e o caminho do módulo não batem, o que confunde operação e manutenção.
- O comportamento funcional (contrato de saída, ordenação, desempate, UTC, Decimal, 404) está **coerente** com o design; os nomes dos 6 campos de resposta seguem o inglês do contrato. A divergência é de nomenclatura de superfície (rota e pasta), não de regra.
- A escolha em si (rota/pasta em português) é consistente com o restante do repositório, que já usa `src/endosso`, `/apolices`, `/saude`, `aumentar_cobertura` desde a INS-014. Ou seja: a implementação seguiu o padrão existente no código, e **o design é que destoou** ao propor inglês/`/policies`/`src/endorsements`.

Recomendação (não bloqueante, mas deve ser resolvida antes do merge para não deixar o design mentindo):

1. Atualizar o `design.md` para refletir a rota real `/apolices/{numero}/endossos`, a pasta `src/endosso` e os módulos `regras.py`/`repositorio.py`/`api.py`; **ou**
2. Registrar explicitamente no design/spec a decisão de nomenclatura (código de aplicação em português acompanhando a INS-014, campos de contrato em inglês) para que a divergência fique justificada e rastreável.

Como a faixa é semiautonoma e isso é documentação, não trava a lógica: mas o `design.md` desatualizado é um débito de documentação que o FDE deveria endereçar no portão de merge.

## 4. O que falta no README para operar a mudança

O `README.md` descreve o fluxo da squad e os comandos do harness, mas **não documenta a aplicação de exemplo** (nem a rota da INS-014 nem a nova rota da INS-016). Para outra pessoa operar a consulta de histórico, hoje faltam no README:

- A existência da nova rota `GET /apolices/{numero}/endossos` e o que ela devolve (lista de endossos, do mais recente para o mais antigo).
- O contrato de saída (os 6 campos) e o formato de data (UTC ISO-8601 com `Z`).
- Os códigos de resposta (200 com lista, 200 com `[]` para apólice sem endosso, 404 para inexistente/formato inválido).
- A massa sintética disponível para teste manual (AP-0001 com 2 endossos, AP-0003 sem endosso, AP-9999 inexistente) e o header `x-solicitante`.
- Como subir a API localmente (uvicorn já está no `.venv-tools`), já que o README não cita o app FastAPI.

Ressalva: o README atual é o do harness, não um README de produto; pode ser decisão consciente não documentar a app de demo ali. Se for o caso, registrar essa decisão. Caso contrário, a lacuna acima impede alguém de operar a mudança só com o README.

## Resumo para o portão

- Docstrings: conformes. Sem função pública nova sem docstring. **OK.**
- Corretude/CA nas docstrings: conformes. **OK.**
- Coerência design x código: **divergência de rota e pasta não documentada** (design em inglês/`/policies`/`src/endorsements` x código em português/`/apolices`/`src/endosso`). Comportamento coerente. Recomendo atualizar o design ou registrar a decisão.
- README: não cobre a nova rota; lacuna de documentação operacional (ou decisão a registrar).
- **Veredito: sem bloqueio.** Apontamentos de documentação a tratar antes do merge, a critério do FDE.
