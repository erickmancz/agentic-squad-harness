# Revisão de vulnerabilidades e proteção de dado pessoal: INS-017

- Spec: INS-017 · Resumo da apólice
- Faixa: semiautonoma (decisão humana)
- Branch: feat/ins-017
- Escopo revisado: `src/endosso/api.py` (trecho INS-017), `src/endosso/resumo.py`, `src/endosso/repositorio.py`, `tests/test_ins_017_resumo.py`
- Ferramentas: `python ash.py etapa sast` (Semgrep) e `python ash.py etapa dependencias` (pip-audit)

## Veredito

**Sem bloqueio. Nenhum achado de severidade alta.** Há 2 achados de severidade média (A-01, A-02) e 3 de baixa (A-03 a A-05). Todos são hardening e nenhum impede o merge na faixa semiautonoma. A ausência de controle de acesso está registrada pelo PO como fora de escopo (bloco 8) e não é tratada como achado.

## Resultado das ferramentas

| Ferramenta | Resultado |
|---|---|
| SAST (`etapa sast`) | Exit 0, sem achados reportados |
| Dependências (`etapa dependencias`) | No known vulnerabilities found. O aviso `venv ... may have moved` é ruído do caminho temporário do Windows |

## Achados

### A-01 · Auditoria em memória cresce sem limite
- Arquivo e linha: `src/endosso/repositorio.py`, `registrar_consulta_resumo` (`self.consultas_resumo.append`, final do arquivo); chamada em `src/endosso/api.py`, `resumo_apolice`.
- Severidade: média.
- Risco: cada consulta de número válido (inclusive inexistente) adiciona um registro e nada o remove. Sem autenticação nem limite de taxa, um chamador pode esgotar a memória do processo (negação de serviço). O descarte por 6 meses é fora de escopo (bloco 8), mas o teto de tamanho não está coberto por isso.
- Recomendação: limitar a lista (por exemplo `collections.deque(maxlen=N)`) ou gravar em armazenamento persistente com retenção. Aplicar limite de taxa na borda (API gateway). Registrar como pendência para a story de armazenamento persistente.

### A-02 · `X-Solicitante` sem validação de tamanho, caracteres nem formato
- Arquivo e linha: `src/endosso/api.py`, `resumo_apolice` (parâmetro `x_solicitante: str = Header(default="canal-app")`); gravado em `repositorio.py`, `registrar_consulta_resumo`, campo `usuario`.
- Severidade: média.
- Risco: o valor entra na auditoria como veio. Aceita string vazia, texto longo (limitado só pelo servidor HTTP, na casa de KB, multiplicado por A-01), caracteres de controle e texto livre, inclusive dado pessoal de terceiros. Hoje não há log nem sink externo, então não há injeção de log efetiva. Quando a auditoria for exportada para arquivo ou log, quebras de linha e controles permitem forjar registros.
- Recomendação: validar com `re.fullmatch` contra allowlist (ex.: `[A-Za-z0-9._-]{1,64}`), responder 422 genérico se fora do padrão e tratar vazio como inválido. Não usar `$` nem `match` (ver A-04). Os testes não cobrem tamanho, vazio nem controles; incluir.

### A-03 · Sem trilha para falha interna (HTTP 500) e sem log do erro
- Arquivo e linha: `src/endosso/api.py`, `resumo_apolice`, bloco `except ValorInvalido` (devolve `Erro interno.`).
- Severidade: baixa.
- Risco: a resposta é genérica e sem detalhe interno (conforme). Porém a causa não é registrada em lugar nenhum, o que dificulta detectar dado corrompido na base. Não é falha de segurança direta.
- Recomendação: registrar em log técnico apenas o número da apólice e o tipo do erro, sem valores nem `X-Solicitante`.

### A-04 · `FORMATO_APOLICE` usa `^...$` com `match` (código herdado, fora do resumo)
- Arquivo e linha: `src/endosso/api.py`, constante `FORMATO_APOLICE` e seus usos em `simular_aumento_cobertura` e `historico_endossos`.
- Severidade: baixa.
- Risco: `$` aceita `\n` final, então `AP-0001\n` passa na validação de formato. Na prática a busca no repositório não encontra a chave e devolve 404, então o efeito hoje é nulo. O resumo da INS-017 está correto (`fullmatch` em `resumo.py`). Os endpoints de INS-016 e INS-018 são de outras stories.
- Recomendação: unificar no `numero_valido` de `resumo.py` (`fullmatch`) em story própria, sem mexer nas outras stories nesta branch.

### A-05 · `aumentar_cobertura` (INS-014) grava `X-Solicitante` e usa `detail=str(e)`
- Arquivo e linha: `src/endosso/api.py`, `aumentar_cobertura`.
- Severidade: baixa.
- Risco: fora do escopo da INS-017. Registrado só porque compartilha o padrão do cabeçalho: o mesmo valor livre vai para a auditoria de endosso e as mensagens de exceção do domínio são devolvidas ao cliente.
- Recomendação: tratar junto com A-02 em hardening geral.

## Verificações conformes

| Ponto | Resultado |
|---|---|
| Validação do número | `fullmatch(r"AP-\d{4}")` em `resumo.py`; `AP-0001\n`, `AP-0001%0A`, vazio, minúscula e `AP-000a` rejeitados; há teste unitário e HTTP (CA-04) |
| Ordem das checagens | Formato validado antes de auditar e antes de consultar a base; número inválido não grava auditoria |
| Dado pessoal na resposta | Modelo com `extra="forbid"` e só 4 campos; `X-Solicitante` não aparece no corpo (teste CA-06) |
| Eco de entrada | 404 e 422 usam mensagem fixa e não repetem o número recebido, sem reflexão |
| Erro interno | `Erro interno.` fixo, sem stack, valor ou texto da exceção (teste CA-05) |
| Valores monetários | `Decimal`, sem arredondar, e `ValorInvalido` quando há mais de 2 casas |
| Registro de auditoria | Só `apolice`, `usuario`, `quando`; sem IP nem outros cabeçalhos (teste CA-08) |
| Somente leitura | O resumo não altera `apolices` (CA-07) |
| Segredos e injeção | Sem segredo no código, sem SQL, sem execução de comando, sem `eval` |

## Fora de escopo (registrado pelo PO)

- Controle de acesso (autenticação e perfis): bloco 8 da spec. Consequência conhecida: qualquer chamador consulta qualquer apólice, e `X-Solicitante` é declarado, não comprovado. A faixa sobe para `critica` se a story criar autenticação.
- Expiração da auditoria em 6 meses: bloco 8. O teto de tamanho (A-01) é tratado à parte.

## Observação sobre o emulador

A INS-017 não usa AWS. O resultado do emulador não entra nesta revisão e nada aqui é prova de segurança de políticas IAM.
