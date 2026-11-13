"""Camada HTTP do endosso de aumento de cobertura (INS-014)."""
from __future__ import annotations

import re
from datetime import timezone
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.endosso.regras import (
    ApoliceInativa,
    CoberturaInvalida,
    EndorsementItem,
    build_history,
    recalcular_premio,
    simular_premio,
)
from src.endosso.repositorio import Repositorio
from src.endosso.resumo import ValorInvalido, montar_resumo, numero_valido

# Número de apólice: AP seguido de hífen e 4 dígitos (ex.: AP-0001), conforme blocos 6 e 9 da INS-016.
FORMATO_APOLICE = re.compile(r"^AP-\d{4}$")
CENTAVOS = Decimal("0.01")

app = FastAPI(title="ASH demo · endosso (fictício)", version="1.0.0")
repo = Repositorio()


class PedidoAumento(BaseModel):
    """Corpo do pedido de aumento de cobertura."""

    nova_cobertura: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class RespostaAumento(BaseModel):
    """Resultado do endosso."""

    apolice: str
    cobertura_anterior: Decimal
    cobertura_nova: Decimal
    premio_anterior: Decimal
    premio_novo: Decimal


@app.get("/saude")
def saude() -> dict:
    """Verificação simples de vida."""
    return {"status": "ok"}


@app.post("/apolices/{numero}/endossos/aumento-cobertura", response_model=RespostaAumento)
def aumentar_cobertura(numero: str, pedido: PedidoAumento,
                       x_solicitante: str = Header(default="canal-app")) -> RespostaAumento:
    """Aplica o endosso de aumento de cobertura e devolve o prêmio recalculado."""
    apolice = repo.buscar(numero)
    if apolice is None:
        raise HTTPException(status_code=404, detail="Apólice não encontrada.")
    try:
        premio_novo = recalcular_premio(apolice, pedido.nova_cobertura)
    except ApoliceInativa as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except CoberturaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    nova = repo.aplicar_endosso(apolice, pedido.nova_cobertura, premio_novo, x_solicitante)
    return RespostaAumento(apolice=numero, cobertura_anterior=apolice.cobertura, cobertura_nova=nova.cobertura,
                           premio_anterior=apolice.premio, premio_novo=nova.premio)


# --- INS-018 · simulação de prêmio por aumento de cobertura (só consulta) ---


class SimulacaoPedido(BaseModel):
    """Corpo do pedido de simulação de aumento de cobertura."""

    cobertura_pedida: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class SimulacaoResposta(BaseModel):
    """Resultado da simulação; não altera a apólice (INS-018)."""

    apolice: str
    cobertura_atual: Decimal
    cobertura_pedida: Decimal
    premio_atual: Decimal
    premio_simulado: Decimal


@app.post("/apolices/{numero}/simulacoes/aumento-cobertura", response_model=SimulacaoResposta)
def simular_aumento_cobertura(numero: str, pedido: SimulacaoPedido,
                              x_corretor: str = Header(default="BRK-001")) -> SimulacaoResposta:
    """Simula o prêmio do aumento de cobertura sem alterar a apólice e registra auditoria sem dado pessoal (INS-018)."""
    if not FORMATO_APOLICE.match(numero):
        raise HTTPException(status_code=404, detail="Apólice não encontrada.")
    apolice = repo.buscar(numero)
    if apolice is None:
        raise HTTPException(status_code=404, detail="Apólice não encontrada.")
    try:
        premio_simulado = simular_premio(apolice, pedido.cobertura_pedida)
    except ApoliceInativa as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except CoberturaInvalida as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    repo.registrar_simulacao(apolice, pedido.cobertura_pedida, premio_simulado, x_corretor)
    return SimulacaoResposta(apolice=numero, cobertura_atual=apolice.cobertura,
                             cobertura_pedida=pedido.cobertura_pedida, premio_atual=apolice.premio,
                             premio_simulado=premio_simulado)


# --- INS-016 · consulta do histórico de endossos (somente leitura) ---


def _serializar_data(item: EndorsementItem) -> str:
    """Converte a data do endosso para ISO-8601 em UTC com sufixo Z (INS-016 CA-02)."""
    return item.date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _serializar_valor(valor: Decimal) -> str:
    """Serializa um valor monetário como string de duas casas, sem recálculo (INS-016 CA-05)."""
    return str(valor.quantize(CENTAVOS))


def _serializar_item(item: EndorsementItem) -> dict:
    """Projeta o item do histórico nos seis campos do contrato de saída (INS-016 CA-02)."""
    return {
        "endorsement_id": item.endorsement_id,
        "date": _serializar_data(item),
        "coverage_before": _serializar_valor(item.coverage_before),
        "coverage_after": _serializar_valor(item.coverage_after),
        "premium_before": _serializar_valor(item.premium_before),
        "premium_after": _serializar_valor(item.premium_after),
    }


@app.get("/apolices/{numero}/endossos")
def historico_endossos(numero: str, x_solicitante: str = Header(default="canal-app")) -> list[dict]:
    """Devolve o histórico de endossos da apólice, do mais recente para o mais antigo (INS-016 CA-01, CA-03, CA-04)."""
    if not FORMATO_APOLICE.match(numero) or not repo.existe(numero):
        # Mesma mensagem genérica para formato inválido e inexistente; sem dado pessoal (blocos 6 e 7).
        raise HTTPException(status_code=404, detail="Apólice não encontrada.")
    itens = build_history(repo.endossos_de(numero))
    return [_serializar_item(i) for i in itens]


# --- INS-017 · resumo da apólice (somente leitura) ---


class ResumoApoliceResposta(BaseModel):
    """Resumo da apólice com os quatro campos permitidos e nenhum dado pessoal (INS-017 CA-06)."""

    model_config = ConfigDict(extra="forbid")

    apolice: str
    situacao: Literal["ativa", "inativa"]
    cobertura: str
    premio: str


@app.get("/apolices/{numero}/resumo", response_model=ResumoApoliceResposta)
def resumo_apolice(numero: str, x_solicitante: str = Header(default="canal-app")) -> ResumoApoliceResposta:
    """Devolve número, situação, cobertura e prêmio da apólice e audita a consulta (INS-017 CA-01 a CA-08)."""
    if not numero_valido(numero):
        raise HTTPException(status_code=422, detail="Número de apólice inválido.")
    # Auditoria antes da busca, para haver trilha também de número válido inexistente (CA-08).
    repo.registrar_consulta_resumo(numero, x_solicitante)
    apolice = repo.buscar(numero)
    if apolice is None:
        raise HTTPException(status_code=404, detail="Apólice não encontrada.")
    try:
        resumo = montar_resumo(apolice)
    except ValorInvalido as e:
        raise HTTPException(status_code=500, detail="Erro interno.") from e
    return ResumoApoliceResposta(
        apolice=resumo["apolice"],
        situacao=resumo["situacao"],
        cobertura=str(resumo["cobertura"]),
        premio=str(resumo["premio"]),
    )
