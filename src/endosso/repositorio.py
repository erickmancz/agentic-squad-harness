"""Repositório em memória com apólices fictícias e trilha de auditoria (INS-014 CA-05, INS-016)."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from src.endosso.regras import CENTAVOS, Apolice


class Repositorio:
    """Guarda apólices fictícias e a trilha de auditoria das alterações de prêmio."""

    def __init__(self) -> None:
        self.apolices: dict[str, Apolice] = {}
        self.auditoria: list[dict] = []
        self.simulacoes: list[dict] = []
        self.historico_endossos: dict[str, list[dict]] = {}
        self.semear()

    def semear(self) -> None:
        """Carrega a massa sintética da demonstração."""
        for ap in (
            Apolice("AP-0001", Decimal("100000.00"), Decimal("1200.00"), True),
            Apolice("AP-0002", Decimal("80000.00"), Decimal("950.00"), False),
            Apolice("AP-0003", Decimal("33333.00"), Decimal("777.77"), True),
        ):
            self.apolices[ap.numero] = ap
        self.semear_historico()

    def semear_historico(self) -> None:
        """Carrega a trilha de auditoria sintética de endossos para a consulta de histórico (INS-016)."""
        mesma_data = datetime(2026, 2, 10, 13, 45, 0, tzinfo=timezone.utc)
        # AP-0001: dois endossos na MESMA data e identificadores distintos (11 e 12) para cobrir
        # ordenação (CA-01) e desempate por id decrescente (CA-06). Sem dado pessoal.
        self.historico_endossos["AP-0001"] = [
            {
                "endorsement_id": 11,
                "date": mesma_data,
                "coverage_before": "80000.00",
                "coverage_after": "100000.00",
                "premium_before": "960.00",
                "premium_after": "1200.00",
            },
            {
                "endorsement_id": 12,
                "date": mesma_data,
                "coverage_before": "100000.00",
                "coverage_after": "150000.00",
                "premium_before": "1200.00",
                "premium_after": "1500.00",
            },
        ]
        # AP-0003 existe mas não tem endosso (CA-03). AP-9999 não existe (CA-04).

    def buscar(self, numero: str) -> Apolice | None:
        """Retorna a apólice ou None."""
        return self.apolices.get(numero)

    def existe(self, numero: str) -> bool:
        """Informa se a apólice existe (INS-016 CA-04)."""
        return numero in self.apolices

    def endossos_de(self, numero: str) -> list[dict]:
        """Retorna os registros brutos de endosso da apólice, sem ordem garantida (INS-016)."""
        return list(self.historico_endossos.get(numero, []))

    def aplicar_endosso(self, apolice: Apolice, nova_cobertura: Decimal, novo_premio: Decimal,
                        solicitante: str) -> Apolice:
        """Grava a nova cobertura e o novo prêmio e registra a trilha de auditoria."""
        nova = replace(apolice, cobertura=nova_cobertura, premio=novo_premio)
        self.apolices[apolice.numero] = nova
        self.auditoria.append({
            "apolice": apolice.numero,
            "solicitante": solicitante,
            "quando": datetime.now(timezone.utc).isoformat(),
            "premio_anterior": str(apolice.premio),
            "premio_novo": str(novo_premio),
            "cobertura_anterior": str(apolice.cobertura),
            "cobertura_nova": str(nova_cobertura),
        })
        return nova

    def registrar_simulacao(self, apolice: Apolice, cobertura_pedida: Decimal, premio_simulado: Decimal,
                            solicitante: str) -> None:
        """Registra a trilha de auditoria da simulação sem alterar a apólice e sem dado pessoal (INS-018 CA-06, CA-07)."""
        self.simulacoes.append({
            "apolice": apolice.numero,
            "cobertura_atual": str(apolice.cobertura.quantize(CENTAVOS)),
            "cobertura_pedida": str(cobertura_pedida.quantize(CENTAVOS)),
            "premio_simulado": str(premio_simulado.quantize(CENTAVOS)),
            "solicitante": solicitante,
            "quando": datetime.now(timezone.utc).isoformat(),
        })
