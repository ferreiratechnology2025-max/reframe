"""
PositioningEngine — decide o posicionamento de mercado (VS-0).

Regras 100% declarativas e determinísticas. Nenhuma chamada de LLM.
O resultado é auditável (decision_reasons).

Generalization Slice (VS-0.1): o mapeamento fixo cobre estetica,
academia e barbearia — SEM `if niche` por nicho. Nichos fora do mapa
retornam UNDETERMINED (falha estruturada).
"""
from typing import Any, Dict, Optional

from design_system.positioning import MarketPosition, Positioning


# VS-0: mapeamento fixo determinístico (sem LLM). Refinamento por
# evidência comercial entra em VS-1+.
POSITIONING_MAP: Dict[str, Dict[str, Any]] = {
    "estetica": {
        "default": MarketPosition.PREMIUM,
        "evidence_strength": 0.85,
        "value_proposition": "Excelência clínica com resultados naturais",
        "tone": "sofisticado",
        "target_audience": "mulheres e homens 25-60 anos, classes A/B",
    },
    "academia": {
        "default": MarketPosition.PERFORMANCE,
        "evidence_strength": 0.80,
        "value_proposition": "Transforme seu corpo com treinos de alta performance",
        "tone": "direto",
        "target_audience": "jovens e adultos 18-50 anos, todos os níveis",
    },
    "barbearia": {
        "default": MarketPosition.MODERN,
        "evidence_strength": 0.75,
        "value_proposition": "Estilo e tradição em cada corte",
        "tone": "confiável",
        "target_audience": "homens 18-60 anos",
    },
}


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

        entry = POSITIONING_MAP.get(niche)
        if entry is None:
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

        return Positioning(
            segment=niche,
            market_position=entry["default"],
            evidence_strength=entry["evidence_strength"],
            evidence_refs=[],  # mapping determinístico, não derivado de evidência
            decision_reasons=["vs0_fixed_mapping"],
            value_proposition=entry["value_proposition"],
            tone=entry["tone"],
            target_audience=entry["target_audience"],
        )