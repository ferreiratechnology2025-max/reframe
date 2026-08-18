"""
VisualThemeResolver — position → VisualTemplate (VS-2).

VS-2 desacopla a seleção visual do nicho: o resolver conhece APENAS a
posição de mercado (MarketPosition). Nichos iguais alcançando a mesma
posição produzem o MESMO template. O nicho NÃO participa da decisão.

Sem fallback silencioso: posição fora do POSITION_TEMPLATE_MAP levanta
ThemeResolutionError com prefixo THEME_UNRESOLVED (contrato da API).
"""
from design_system.positioning import MarketPosition
from design_system.visual_template import TEMPLATES, VisualTemplate


class ThemeResolutionError(Exception):
    """Posição de mercado não mapeada no catálogo de templates."""


# Mapa POSITION-ONLY: posição de mercado -> template (VS-2).
# BOLD_URBAN permanece no catálogo como referência, mas NÃO está mapeado
# (MODERN resolve para MODERN_TECH — decisão congelada).
POSITION_TEMPLATE_MAP: dict[MarketPosition, VisualTemplate] = {
    MarketPosition.PREMIUM: TEMPLATES["PREMIUM_CLINICAL"],
    MarketPosition.PERFORMANCE: TEMPLATES["PERFORMANCE_RESULT"],
    MarketPosition.NATURAL: TEMPLATES["NATURAL_ELEGANT"],
    MarketPosition.LUXURY: TEMPLATES["LUXURY_MINIMAL"],
    MarketPosition.TRADITIONAL: TEMPLATES["ORGANIC_WARM"],
    MarketPosition.MODERN: TEMPLATES["MODERN_TECH"],
}


class VisualThemeResolver:
    """Resolve o VisualTemplate para uma posição de mercado.

    Position-only (VS-2): o nicho é recebido apenas por compatibilidade de
    assinatura, mas NÃO participa da resolução. Posições iguais produzem o
    mesmo template, independente do nicho.
    """

    def resolve(self, niche: str, market_position: MarketPosition) -> VisualTemplate:
        template = POSITION_TEMPLATE_MAP.get(market_position)
        if template is None:
            raise ThemeResolutionError(
                f"THEME_UNRESOLVED: position='{market_position.value}' "
                "fora do POSITION_TEMPLATE_MAP (VS-2)"
            )
        return template