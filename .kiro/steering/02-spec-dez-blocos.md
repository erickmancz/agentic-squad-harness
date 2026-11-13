---
inclusion: fileMatch
fileMatchPattern: ".kiro/specs/**"
---

# Spec de dez blocos

Uma história pronta para pessoas não está pronta para agentes. Sem aceite testável, dados e limites, o agente adivinha.

Todo `requirements.md` em `.kiro/specs/<nome>/` segue o template abaixo, com estes títulos exatos e nesta ordem. O script `scripts/validar_spec.py` procura os títulos literalmente.

```markdown
---
id: ABC-000
dono_po: Nome do PO
faixa: semiautonoma
dev_revisor:
versao: 1
status: rascunho
---

# ABC-000 · Título curto

## 1. Cabeçalho
## 2. Objetivo e métrica
## 3. História e contexto
## 4. Aceite testável
## 5. Referências de UX
## 6. Dados e integrações
## 7. Não funcionais
## 8. Limites do agente
## 9. Testes e exemplos
## 10. Compatibilidade
## Perguntas em aberto
```

## Regras

- `faixa` aceita `autonoma`, `semiautonoma` ou `critica`.
- `faixa: critica` exige `dev_revisor` preenchido.
- `status` aceita `rascunho`, `em_revisao` ou `aprovada`.
- "Aceite testável" tem um item por critério, com ID `CA-01`, `CA-02`..., no formato Dado / Quando / Então.
- Nenhum dos dez blocos fica vazio. Se não se aplica, escreva "Não se aplica" e o motivo.
- "Perguntas em aberto" lista o que falta decidir. Spec com pergunta em aberto não pode ter `status: aprovada`.
- Todo teste que cobre um critério cita `<ID da spec> CA-NN` no nome ou na docstring, por exemplo `INS-014 CA-01`. O script `scripts/rastrear_aceite.py` usa isso.
- `design.md` e `tasks.md` são gerados a partir do `requirements.md` aprovado e aprovados pelo FDE antes da implementação.
