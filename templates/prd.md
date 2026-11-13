---
id: ABC-000
iniciativa: slug-da-iniciativa
dono_po: Nome do PO
status: rascunho
---

# PRD · Título da iniciativa

Gerado a partir do PRFAQ aprovado. Composição por raciocínio: use as seções que servem a ESTA iniciativa, pule ou junte com uma linha de justificativa. Todo PRD responde às sete perguntas abaixo. Tudo fictício.

## Sumário executivo
(O produto em um parágrafo: o que é, para quem, por que agora, como é o sucesso.)

## Contexto e problema
(Abre com o Retrato do Cliente. Prefira "Hoje [cliente] tem que [problema] quando [situação]".)

## Objetivos e KPIs
(3 a 5 indicadores, cada um com linha de base (ou "medir primeiro") e alvo.)

## Personas
(Personas nomeadas da descoberta, com atributos [D]/[W]/[I] e confiança.)

## Visão da solução
(Conceito geral + grupos de funcionalidades nomeados, da Big Idea.)

## Escopo
(Dentro e fora, explícito. Restrições de prazo, time, orçamento.)

## Jornadas do usuário
(As jornadas principais, por persona.)

## Funcionalidades
(Em profundidade, grupo a grupo, com a mecânica visível.)

## Requisitos funcionais e não-funcionais
(Funcionais priorizados Must/Should/Nice; não-funcionais: desempenho, disponibilidade, escala.)

## Arquitetura e tecnologia
(Como se constrói, como digest DENTRO do documento. "Está em outro arquivo" não vale. Para iniciativa que vira software no ASH, aponte a stack do cliente (steering 03).)

## Dados, IA e segurança
(Fontes de dado, fronteira de IA se houver, classificação de dado, LGPD, medidas de segurança.)

## Métricas e telemetria
(Cada KPI aponta seu evento e dono.)

## Riscos
(Nomeados, com probabilidade, impacto e mitigação.)

## Validação e perguntas em aberto
(Herdadas do PRFAQ. Cada uma com teste pré-registrado: limiar, dono, quando. Trilha paralela, nunca bloqueio do build.)

## Próximos passos (handoff para o ASH)
(As stories que este PRD gera, uma por capacidade entregável. O squad-lead materializa com python ash.py nova-descoberta <ID> <slug>, e cada story entra no fluxo normal: intake, spec de dez blocos, design, implementação, merge.)
