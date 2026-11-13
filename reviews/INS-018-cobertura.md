# Revisão de cobertura · INS-018

- Spec: `.kiro/specs/ins-018-simulacao-aumento-cobertura/requirements.md` (id INS-018, faixa critica, status aprovada)
- Branch: `feat/ins-018`
- Revisor de cobertura (só leitura; não escreve testes nem código)
- Comandos: `python scripts/rastrear_aceite.py` e `python -m pytest --cov=src --cov-report=term-missing`

## Resultado

| Item | Resultado |
|---|---|
| Rastreio de aceite (todas as specs aprovadas) | `[OK]` 18 critérios com teste |
| CA-01 a CA-07 da INS-018 com teste citando "INS-018 CA-NN" | 7 de 7 |
| Testes | 40 passaram, 0 falhas |
| Cobertura total de `src/` | 99% (mínimo do projeto: 80%) |
| Bloqueio | Nenhum |

## Rastreio dos critérios (CA-01 a CA-07)

Cada critério tem ao menos um teste que o cita na docstring/nome, em `tests/test_ins_018_simulacao.py`:

| CA | Teste(s) que citam o critério |
|---|---|
| CA-01 | `test_ins_018_ca_01_premio_proporcional` (domínio) e `test_ins_018_ca_01_endpoint_200` (endpoint 200, prêmio 1.800,00) |
| CA-02 | `test_ins_018_ca_02_half_up_centavos` (domínio, HALF_UP) e `test_ins_018_ca_02_endpoint_200` (endpoint, 1.166,67) |
| CA-03 | `test_ins_018_ca_03_regra_pura_inativa` (regra pura) e `test_ins_018_ca_03_inativa_409` (endpoint 409) |
| CA-04 | `test_ins_018_ca_04_limite_2x` (domínio, >2x e ==2x) e `test_ins_018_ca_04_acima_2x_422` (endpoint 422 e 200 em ==2x) |
| CA-05 | `test_ins_018_ca_05_inexistente_404` (endpoint 404 com mensagem genérica, sem dado pessoal) |
| CA-06 | `test_ins_018_ca_06_apolice_intacta` (parametrizado: sucesso, 409, 422, 404; apólice intacta e nenhum endosso) |
| CA-07 | `test_ins_018_ca_07_auditoria_sem_dado_pessoal` (registro de auditoria com os 6 campos, solicitante BRK-001, sem dado pessoal) |

Nenhum CA sem teste.

## Percentual de cobertura

```
Name                         Stmts   Miss  Cover   Missing
----------------------------------------------------------
src\__init__.py                  0      0   100%
src\endosso\__init__.py          0      0   100%
src\endosso\api.py              71      1    99%   93
src\endosso\regras.py           42      0   100%
src\endosso\repositorio.py      32      0   100%
----------------------------------------------------------
TOTAL                          145      1    99%
```

A cobertura total (99%) está acima do mínimo do projeto (80%). As regras de negócio puras
(`regras.py`) e o repositório (`repositorio.py`) estão em 100%.

## Trecho sem cobertura relevante para a spec

- `src/endosso/api.py` linha 93: o `raise HTTPException(status_code=404, detail="Apólice não encontrada.")`
  dentro do ramo `if not FORMATO_APOLICE.match(numero):` do endpoint de simulação da INS-018.
  - Esse ramo cobre o caso de **número com formato inválido** (ex.: `XYZ`, `AP-12`), que também responde 404.
  - O teste de CA-05 (`test_ins_018_ca_05_inexistente_404`) usa `AP-9999`, que **passa** no formato
    `AP-\d{4}` e cai no segundo 404 (apólice não encontrada), exercitando a linha 96-97, não a 93.
  - Consequência: o 404 por formato inválido existe no código mas não é exercitado por teste.

Observação (não bloqueio): CA-05 pede "apólice que não existe → 404", e isso está testado e passando.
A linha 93 é um caminho de borda adicional do próprio endpoint da INS-018 (formato inválido) que o
conjunto atual não cobre. Como não escrevo testes, registro aqui para decisão de quem implementa:
um caso extra com número malformado fecharia os 100% em `api.py` e cobriria explicitamente o ramo de
formato inválido do endpoint de simulação.

## Conclusão

Sem bloqueio de cobertura. Todos os critérios CA-01 a CA-07 têm teste que os cita, os 40 testes
passam e a cobertura total (99%) supera o mínimo do projeto (80%). Fica registrada como melhoria
opcional (não bloqueante) a falta de um teste para o ramo de número com formato inválido no endpoint
de simulação (`api.py` linha 93).
