"""
EvidencePositioningEngine — refinamento determinístico do posicionamento por
evidência comercial (VS-1).

Contrato congelado VS-1:
- POSITIONING_MAP continua sendo a ÂNCORA (posição base por nicho).
- O refinamento só pode selecionar posições DENTRO do conjunto suportado
  pelo nicho (SUPPORTED_POSITIONS). Nenhuma posição fora do catálogo.
- Evidência ausente → posição base (comportamento VS-0.x preservado).
- Evidência presente → refina dentro do conjunto suportado.
- Precedência: 1) Especialidades (prioridade explícita, NÃO ordem da lista);
  2) Rating + Volume; 3) Base.
- Nenhum sinal fora do catálogo; rating < mínimo ou sem resolução → UNDETERMINED.
- UNDETERMINED → bloqueio (pipeline para). Sem fallback silencioso.
- LLM NUNCA participa da decisão de posicionamento.
- decision_reasons ordenadas e determinísticas (lista, sem set/dict iterado).

Determinismo: mesmo input + mesma evidência → mesmo Positioning,
decision_reasons e evidence_strength.
"""
from typing import Any, Dict, List, Optional

from design_system.positioning import MarketPosition, Positioning
from engines.positioning_engine import POSITIONING_MAP


# Posições suportadas por nicho (refinamento restrito a este conjunto).
SUPPORTED_POSITIONS: Dict[str, List[MarketPosition]] = {
    "estetica": [
        MarketPosition.PREMIUM,
        MarketPosition.NATURAL,
        MarketPosition.PERFORMANCE,
    ],
    "academia": [
        MarketPosition.PERFORMANCE,
        MarketPosition.MODERN,
        MarketPosition.NATURAL,
    ],
    "barbearia": [
        MarketPosition.LUXURY,
        MarketPosition.TRADITIONAL,
        MarketPosition.MODERN,
    ],
}

# Prioridade EXPLÍCITA entre posições disputadas por especialidades.
# Garante que permutações da mesma lista produzem a MESMA decisão.
SPECIALTY_PRIORITY: Dict[MarketPosition, int] = {
    MarketPosition.LUXURY: 300,
    MarketPosition.PREMIUM: 300,
    MarketPosition.PERFORMANCE: 200,
    MarketPosition.TRADITIONAL: 150,
    MarketPosition.NATURAL: 100,
    MarketPosition.MODERN: 50,
}

# Regras de refinamento por nicho (ordem determinística de avaliação).
REFINEMENT_RULES: Dict[str, Dict[str, Any]] = {
    "estetica": {
        "specialty": {
            "injetáveis": MarketPosition.PREMIUM,
            "botox": MarketPosition.PREMIUM,
            "preenchedor": MarketPosition.PREMIUM,
            "facial": MarketPosition.NATURAL,
            "limpeza": MarketPosition.NATURAL,
            "peeling": MarketPosition.NATURAL,
        },
        "rating": [
            {"min": 4.8, "volume_min": 200, "result": MarketPosition.PREMIUM},
            {"min": 4.0, "volume_min": 50, "result": MarketPosition.NATURAL},
            {"min": 0, "volume_min": 0, "result": MarketPosition.PERFORMANCE},  # fallback
        ],
        "rating_minimum": 3.0,  # abaixo disso → UNDETERMINED
    },
    "academia": {
        "specialty": {
            "crossfit": MarketPosition.PERFORMANCE,
            "hipertrofia": MarketPosition.PERFORMANCE,
            "pilates": MarketPosition.NATURAL,
            "yoga": MarketPosition.NATURAL,
        },
        "rating": [
            {"min": 4.5, "volume_min": 100, "result": MarketPosition.PERFORMANCE},
            {"min": 4.0, "volume_min": 30, "result": MarketPosition.MODERN},
            {"min": 0, "volume_min": 0, "result": MarketPosition.PERFORMANCE},
        ],
        "rating_minimum": 3.0,
    },
    "barbearia": {
        "specialty": {
            "barba": MarketPosition.LUXURY,
            "corte premium": MarketPosition.LUXURY,
            "corte tradicional": MarketPosition.TRADITIONAL,
        },
        "rating": [
            {"min": 4.5, "volume_min": 100, "result": MarketPosition.MODERN},
            {"min": 4.0, "volume_min": 30, "result": MarketPosition.TRADITIONAL},
            {"min": 0, "volume_min": 0, "result": MarketPosition.MODERN},
        ],
        "rating_minimum": 3.0,
    },
}

# Perfil comercial por (nicho, posição) — contrato VS-1 #12.
COMMERCIAL_PROFILES: Dict[tuple[str, MarketPosition], Dict[str, str]] = {
    ("estetica", MarketPosition.PREMIUM): {
        "value_proposition": "Excelência clínica com resultados naturais",
        "tone": "sofisticado",
        "target_audience": "mulheres e homens 25-60 anos, classes A/B",
    },
    ("estetica", MarketPosition.NATURAL): {
        "value_proposition": "Cuidado estético que realça sua beleza natural",
        "tone": "acolhedor",
        "target_audience": "mulheres 25-55 anos, classes A/B",
    },
    ("estetica", MarketPosition.PERFORMANCE): {
        "value_proposition": "Resultados comprovados com tecnologia de ponta",
        "tone": "direto",
        "target_audience": "homens e mulheres 30-60 anos, classes A/B",
    },
    ("academia", MarketPosition.PERFORMANCE): {
        "value_proposition": "Transforme seu corpo com treinos de alta performance",
        "tone": "direto",
        "target_audience": "jovens e adultos 18-50 anos",
    },
    ("academia", MarketPosition.MODERN): {
        "value_proposition": "O futuro do treinamento já chegou",
        "tone": "inovador",
        "target_audience": "jovens e adultos 18-45 anos",
    },
    ("academia", MarketPosition.NATURAL): {
        "value_proposition": "Equilíbrio entre corpo e mente",
        "tone": "acolhedor",
        "target_audience": "adultos 25-55 anos",
    },
    ("barbearia", MarketPosition.LUXURY): {
        "value_proposition": "Experiência premium em cuidados masculinos",
        "tone": "exclusivo",
        "target_audience": "homens 25-55 anos, classes A/B",
    },
    ("barbearia", MarketPosition.TRADITIONAL): {
        "value_proposition": "Estilo e tradição em cada corte",
        "tone": "confiável",
        "target_audience": "homens 18-60 anos",
    },
    ("barbearia", MarketPosition.MODERN): {
        "value_proposition": "O novo padrão em barbearia",
        "tone": "inovador",
        "target_audience": "homens 18-40 anos",
    },
}

# Strength determinística por tipo de resolução.
SPECIALTY_STRENGTH = 0.9
RATING_VOLUME_STRENGTH = 0.85


class EvidencePositioningEngine:
    """Decide o posicionamento a partir da evidência — 100% determinístico.

    Regras declarativas (dados). Nenhuma chamada de LLM. O resultado é
    auditável via decision_reasons (lista ordenada).
    """

    def determine(
        self,
        niche: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Positioning:
        niche = (niche or "").strip().lower()
        segment = niche or "unknown"
        evidence = evidence or {}

        # 1. Nicho suportado?
        allowed = SUPPORTED_POSITIONS.get(niche)
        if allowed is None:
            return self._undetermined(segment, ["nichos_fora_do_escopo_vs1"])

        # 2.1 Especialidade (prioridade explícita, não ordem da lista)
        candidate = self._resolve_by_specialty(niche, evidence.get("specialties") or [])
        if candidate is not None and candidate in allowed:
            return self._build_positioning(segment, candidate, ["specialty"])

        # 2.2 Rating < mínimo → UNDETERMINED
        rating = evidence.get("rating")
        if rating is not None:
            min_rating = REFINEMENT_RULES.get(niche, {}).get("rating_minimum", 3.0)
            if rating < min_rating:
                return self._undetermined(segment, ["rating_below_minimum"])

        # 2.3 Rating + Volume
        total = evidence.get("total_ratings") or 0
        candidate = self._resolve_by_rating(niche, rating, total)
        if candidate is not None and candidate in allowed:
            return self._build_positioning(segment, candidate, ["rating_volume"])

        # 2.4 Base do nicho (âncora VS-0.x)
        base = POSITIONING_MAP.get(niche, {}).get("default")
        if base is not None and base in allowed:
            return self._build_positioning(segment, base, ["base_position"])

        # 2.5 Sem posição resolvida
        return self._undetermined(segment, ["no_position_resolved"])

    def _resolve_by_specialty(
        self, niche: str, specialties: List[str]
    ) -> Optional[MarketPosition]:
        """Resolve especialidades por PRIORIDADE, NÃO por ordem da lista."""
        mapping = REFINEMENT_RULES.get(niche, {}).get("specialty", {})
        candidates = []
        for specialty in specialties:
            key = (specialty or "").strip().lower()
            pos = mapping.get(key)
            if pos is not None:
                candidates.append(pos)

        if not candidates:
            return None

        return max(candidates, key=lambda p: SPECIALTY_PRIORITY.get(p, 0))

    def _resolve_by_rating(
        self, niche: str, rating: Optional[float], total: int
    ) -> Optional[MarketPosition]:
        if rating is None:
            return None
        for rule in REFINEMENT_RULES.get(niche, {}).get("rating", []):
            if rating >= rule["min"] and total >= rule["volume_min"]:
                return rule["result"]
        return None

    def _build_positioning(
        self,
        niche: str,
        position: MarketPosition,
        reasons: List[str],
    ) -> Positioning:
        profile = COMMERCIAL_PROFILES.get((niche, position))
        if profile is None:
            raise ValueError(
                f"COMMERCIAL_PROFILE_UNRESOLVED: perfil ausente para "
                f"(nicho='{niche}', position='{position.value}')"
            )

        if reasons == ["specialty"]:
            strength = SPECIALTY_STRENGTH
        elif reasons == ["rating_volume"]:
            strength = RATING_VOLUME_STRENGTH
        else:  # base_position — âncora VS-0.x
            strength = POSITIONING_MAP.get(niche, {}).get("evidence_strength", 0.0)

        return Positioning(
            segment=niche,
            market_position=position,
            evidence_strength=strength,
            evidence_refs=[],
            decision_reasons=reasons,
            value_proposition=profile["value_proposition"],
            tone=profile["tone"],
            target_audience=profile["target_audience"],
        )

    def _undetermined(self, segment: str, reasons: List[str]) -> Positioning:
        return Positioning(
            segment=segment,
            market_position=MarketPosition.UNDETERMINED,
            evidence_strength=0.0,
            evidence_refs=[],
            decision_reasons=reasons,
            value_proposition="",
            tone="profissional",
            target_audience="",
        )