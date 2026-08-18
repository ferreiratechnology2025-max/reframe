"""
PositioningEngine — decide o posicionamento de mercado (VS-0).

Regras 100% declarativas e determinísticas. Nenhuma chamada de LLM.
O resultado é auditável (decision_reasons).

VS-0: apenas estetica -> PREMIUM (mapeamento fixo determinístico).
Qualquer outro nicho retorna UNDETERMINED (fora do escopo VS-0).
"""
from typing import Any, Dict, Optional

from design_system.positioning import MarketPosition, Positioning


class PositioningEngine:
    """Resolve o posicionamento para um (nicho, evidência, localização)."""

    def determine(
        self,
        niche: str,
        evidence: Optional[Dict[str, Any]] = None,
        location=None,
    ) -> Positioning:
        niche = (niche or "").strip().lower()
        segment = niche or "unknown"

        # VS-0: apenas estetica possui regra de posicionamento.
        if niche != "estetica":
            return Positioning(
                segment=segment,
                market_position=MarketPosition.UNDETERMINED,
                evidence_strength=0.0,
                evidence_refs=[],
                decision_reasons=["nichos_fora_do_escopo_vs0"],
                value_proposition="",
                tone="profissional",
                target_audience="",
            )

        # VS-0: estetica -> PREMIUM (fixo e determinístico). Refinamento
        # por evidência comercial entra em VS-1+.
        return Positioning(
            segment=niche,
            market_position=MarketPosition.PREMIUM,
            evidence_strength=0.85,
            evidence_refs=[],  # mapping determinístico, não derivado de evidência
            decision_reasons=["vs0_fixed_mapping"],
            value_proposition="Excelência clínica com resultados naturais",
            tone="sofisticado",
            target_audience="mulheres e homens 25-60 anos, classes A/B",
        )