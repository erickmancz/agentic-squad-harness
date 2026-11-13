# INS-017 · Revisão de dívida técnica

Branch: `feat/ins-017` (diff contra `main`). Escopo: `src/endosso/resumo.py`, `src/endosso/repositorio.py`, `src/endosso/api.py` (trecho INS-017), `tests/test_ins_017_resumo.py`, contra `.kiro/specs/ins-017-resumo-apolice/design.md`. Revisão só de leitura: nada foi corrigido e os testes não foram executados por este revisor. Esforço: P (até 1 h), M (até 1 dia), G (mais de 1 dia).

## Veredito

**APROVADO COM RESSALVAS.** Nenhum item bloqueia o merge. Não há `float` para dinheiro, não há TODO sem dono e a regra de negócio está separada da camada HTTP. Há um código morto (`NumeroInvalido`), um acréscimo fora do design (tratamento de `InvalidOperation`, sem teste) e duplicações de constantes. Recomendo resolver os itens D-01 e D-02 antes do merge, porque tocam o desvio entre design e código. O restante pode virar dívida registrada.

## Itens

| # | Categoria | Arquivo:linha | Achado | Esforço | Gravidade |
|---|---|---|---|---|---|
| D-01 | Código morto / desvio do design | `src/endosso/resumo.py:14-15` | `NumeroInvalido` é declarada (design seção 2 e T-01 pedem) mas nada a levanta nem a captura. A rota usa `numero_valido` e devolve 422 direto (`api.py:164-165`). Nenhum teste a importa. Há duas formas de rejeitar número inválido, e só uma é usada. Decisão do FDE: remover a classe e ajustar design e tasks, ou usá-la. Não é erro de comportamento | P | Média |
| D-02 | Acréscimo fora do design | `src/endosso/resumo.py:30-33` | O `try/except InvalidOperation` trata NaN e infinito, que o design D2 não prevê (D2 só trata "mais de 2 casas"). Dois efeitos: (a) o ramo das linhas 31-33 não tem teste, pois os testes só cobrem 3 casas (`test_ins_017_resumo.py`, CA-05); (b) um NaN silencioso (`Decimal("NaN")`) passa por `quantize` sem erro, e é barrado pela comparação da linha 34 com a mensagem "mais de 2 casas", que não descreve o problema. Cobrir com teste e registrar no design, ou remover. A base atual é sintética e não tem esse valor | P | Média |
| D-03 | Duplicação | `src/endosso/resumo.py:11` | `_CENTAVOS = Decimal("0.01")` repete `CENTAVOS` de `src/endosso/regras.py` (importada em `repositorio.py:8`) e `CENTAVOS` de `api.py:25`. Três definições da mesma constante monetária. Reaproveitar a de `regras.py` | P | Baixa |
| D-04 | Duplicação e risco latente | `src/endosso/resumo.py:10-11` e `api.py:24` | Duas regexes para o mesmo formato de apólice. A de `api.py` (`^AP-\d{4}$` com `.match`) aceita `AP-0001\n`, o caso que a INS-017 CA-04 corrigiu. As rotas das INS-016 (`api.py:139`) e INS-018 (`api.py:94`) seguem com a versão frágil. Não é regressão desta story, mas passou a existir um validador correto ao lado do frágil. Unificar em `numero_valido` | M (toca rotas de outras stories e seus testes) | Média |
| D-05 | Duplicação | `src/endosso/api.py:161-181` | O padrão "valida formato, busca, 404 com `Apólice não encontrada.`, traduz erro de domínio" se repete em quatro rotas (`api.py:54`, `91`, `137`, `161`). Candidato a dependência do FastAPI ou função auxiliar. Não crítico com quatro rotas | M | Baixa |
| D-06 | Acoplamento regra e HTTP | `src/endosso/api.py:172-181` | A regra devolve um `dict` com `Decimal` e a rota converte para `str` e remonta o modelo campo a campo (`str(resumo["cobertura"])`). A formatação de saída ficou dividida entre `resumo.py` e `api.py`, e o `dict` sem tipo exige chaves repetidas nos dois lados. Não há `HTTPException` nem `Header` na regra, então o acoplamento é baixo. Um dataclass ou `TypedDict` de retorno tiraria as chaves em texto | P | Baixa |
| D-07 | Tratamento de erro | `src/endosso/api.py:173-174` | `ValorInvalido` vira 500 genérico sem log. Intencional pelo design (sem detalhe interno), mas sem registro interno a divergência de dados da base não é rastreável. Registrar em log o número da apólice (sem dado pessoal) | P | Baixa |
| D-08 | Função longa | `src/endosso/api.py:161-181` | `resumo_apolice` tem cerca de 20 linhas e quatro responsabilidades (formato, auditoria, busca, projeção). Dentro do aceitável; só acompanhar se crescer | P | Baixa |
| D-09 | Testes | `tests/test_ins_017_resumo.py` (CA-09, final do arquivo) | O teste de p95 mede tempo real (`time.perf_counter`) com limite de 2 s: sinal fraco, pode ficar instável em máquina lenta, e o design D8 já admite que não prova a base real. Aceito pelo design; manter a pendência da T-06 visível | P | Baixa |
| D-10 | Retenção | `src/endosso/repositorio.py:100` (`consultas_resumo`) | A lista de auditoria cresce sem limite e guarda `usuario` (dado pessoal comum do atendente). Já aceito pelo design D9 e pelo bloco 8 (descarte fora de escopo), mas a retenção de 6 meses do bloco 6 não tem dono nem story. Registrar como dívida com dono | G (persistência e descarte) | Média |

## Conferência pedida

| Ponto | Resultado |
|---|---|
| `NumeroInvalido` não usada pela rota | Confirmado, ver D-01 |
| NaN e infinito fora do design | Confirmado, ver D-02 |
| Duplicação | D-03, D-04, D-05 |
| Docstring de uma linha | Todas as funções e classes públicas da INS-017 têm docstring de uma linha. Sem desvio. Algumas passam de 110 caracteres (`api.py:163`, `repositorio.py:99`), no mesmo padrão do arquivo |
| `Decimal` e `float` | Sem `float` nos quatro arquivos. Valores monetários são `Decimal` e saem como `str` com 2 casas, sem arredondar (`resumo.py` não usa `ROUND_*`). Completar zeros é permitido por D2. Conforme |
| TODO sem dono | Nenhum encontrado |
| Regra de negócio fora da camada HTTP | Conforme: `resumo.py` não importa FastAPI. Ver D-06 para a divisão da formatação |
| Rastreio de aceite | Os testes citam `INS-017 CA-NN` no nome ou na docstring, CA-01 a CA-09 cobertos. CA-04 cobre `AP-0001\n` na regra e no HTTP |

## Limites desta revisão

Li os quatro arquivos e o `design.md`. Não executei `python ash.py testar` nem o CI, então cobertura e resultado dos testes não foram verificados por mim. Os números de linha vêm da leitura dos arquivos no estado atual da branch.
