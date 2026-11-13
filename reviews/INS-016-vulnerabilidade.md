# Revisão de vulnerabilidades · INS-016

Spec: `.kiro/specs/ins-016-historico-endossos-v2/requirements.md` (faixa `semiautonoma`; recomendação de intake `critica` por ler prêmio e trilha).
Branch: `feat/ins-016`.
Escopo revisado: `src/endosso/api.py`, `src/endosso/regras.py`, `src/endosso/repositorio.py` e os testes `tests/test_ins_016_dominio.py`, `tests/test_ins_016_historico_endossos.py`.

## Veredito

**NÃO BLOQUEIA MERGE.** Nenhum achado de severidade alta. As ferramentas não apontaram vulnerabilidade e a revisão manual dos quatro focos (injeção/validação de entrada, vazamento de dado pessoal, enumeração por mensagem de erro e tratamento monetário) não encontrou bloqueio.

## Ferramentas

| Ferramenta | Comando | Resultado |
|---|---|---|
| Semgrep CE | `semgrep --config .semgrep/ --metrics=off src/` | 0 findings (5 regras, 5 arquivos), 0 blocking |
| pip-audit | `pip-audit -r requirements.txt` | No known vulnerabilities found |

## Achados

### 1. Validação do parâmetro de rota (formato AP+4 dígitos): sem achado
- Arquivo/linha: `src/endosso/api.py:112-118` (`historico_endossos`), regex em `api.py:22` (`FORMATO_APOLICE = re.compile(r"^AP-\d{4}$")`).
- Severidade: informativo.
- Risco: nenhum. O regex é ancorado em `^...$`, a validação roda antes de qualquer acesso ao repositório e o repositório é um `dict` em memória: não há concatenação em SQL, shell ou template, logo não há superfície de injeção. Caso `re.fullmatch` fosse desejável, `match` com âncoras `^$` é equivalente aqui.
- Recomendação: manter. Ao migrar o repositório para um backend real (SQL/NoSQL), garantir consulta parametrizada; não é mudança desta spec.

### 2. Vazamento de dado pessoal em resposta/log/erro: sem achado
- Arquivo/linha: projeção em `src/endosso/regras.py:60-79` (`project_endorsement` / `EndorsementItem`), serialização em `src/endosso/api.py:88-99` (`_serializar_item`).
- Severidade: informativo.
- Risco: nenhum identificado. `project_endorsement` copia apenas os seis campos do contrato para um dataclass `frozen`; qualquer campo pessoal presente no registro bruto da trilha (ex.: `nome_segurado`, `cpf`) é descartado por construção, comportamento coberto por `test_ins_016_ca_02_item_sem_dado_pessoal`. No caminho de leitura não há `logging`/`print` de parâmetros nem do corpo. Atende os blocos 6 e 7 (nenhum PII em resposta, log ou erro).
- Recomendação: manter. Observação (não-bloqueio): o header `x_solicitante` é aceito em `historico_endossos` mas não é usado nem registrado; se futuramente for logado, tratar como dado potencialmente sensível e nunca registrar valor livre sem sanitização: a regra `ash-sem-dado-pessoal-em-log` cobre esse caso.

### 3. Enumeração via mensagem de erro (404 genérico): sem achado
- Arquivo/linha: `src/endosso/api.py:114-117`.
- Severidade: informativo.
- Risco: nenhum. Formato inválido e apólice inexistente retornam a mesma resposta `404` com detalhe fixo `"Apólice não encontrada."`, sem distinguir os casos e sem PII. Isso remove o canal de enumeração por diferença de mensagem/status e atende CA-04. Coberto por `test_ins_016_ca_04_ap9999_nao_encontrada` e `test_ins_016_ca_04_formato_invalido_tambem_404`.
- Recomendação: manter.

### 4. Tratamento monetário (decimal.Decimal, sem float): sem achado
- Arquivo/linha: `src/endosso/regras.py:70-78` (campos `Decimal`), `src/endosso/api.py:85-86` (`_serializar_valor` com `quantize(CENTAVOS)`).
- Severidade: informativo.
- Risco: nenhum. Todos os valores de cobertura e prêmio são `decimal.Decimal`; a serialização usa `quantize` para duas casas e devolve string, sem conversão por `float` em nenhum ponto do caminho de leitura. A regra `ash-sem-float-para-dinheiro` do Semgrep não disparou. Atende CA-05 e a convenção do steering 03; coberto por `test_ins_016_ca_05_*`.
- Recomendação: manter.

## Observações fora de escopo de bloqueio
- A spec (bloco 6) permite que qualquer atendente autenticado consulte qualquer apólice, sem segregação por carteira. É uma decisão humana registrada na spec, não um defeito da implementação; não é bloqueio. Caso a segregação por carteira entre no escopo futuro, revisar autorização a nível de recurso.
- A autenticação em si não é exercida nesta demo (API fictícia em memória); o controle de acesso real fica para o ambiente de produção, conforme a spec.

## Conclusão
Não há bloqueio de merge pela ótica de vulnerabilidades: os quatro focos estão endereçados, Semgrep e pip-audit estão limpos e os critérios de aceite relacionados à segurança (CA-02, CA-04, CA-05) têm teste correspondente.
