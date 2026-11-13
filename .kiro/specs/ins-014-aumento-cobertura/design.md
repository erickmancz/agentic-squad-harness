# Design · INS-014 (exemplo fictício)

## Visão geral
Regra de negócio pura em `src/endosso/regras.py`, separada da camada HTTP em `src/endosso/api.py`. Estado e trilha de auditoria em `src/endosso/repositorio.py` (memória, só para a demo).

## Componentes
| Componente | Responsabilidade |
|---|---|
| `regras.recalcular_premio` | Valida apólice ativa e nova cobertura; calcula prêmio proporcional com `Decimal` e HALF_UP em centavos |
| `regras.validar_nova_cobertura` | Maior que a atual e no máximo 2 vezes a atual |
| `repositorio.Repositorio.aplicar_endosso` | Grava nova cobertura e prêmio; registra auditoria sem dado pessoal |
| `api.aumentar_cobertura` | Traduz exceções em 404, 409 e 422 |

## Fluxo
1. API busca a apólice (404 se não existir).
2. `recalcular_premio` valida e calcula (409 se inativa, 422 se cobertura inválida).
3. Repositório aplica o endosso e grava a auditoria.
4. API devolve valores anteriores e novos.

## Decisões
- Dinheiro sempre em `Decimal`.
- Limite de 2 vezes é constante `LIMITE_MULTIPLICADOR` (mudança exige aprovação humana, bloco 8 da spec).
