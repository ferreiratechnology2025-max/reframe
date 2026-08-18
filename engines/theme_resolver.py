"""
VisualThemeResolver — mapeia (nicho, posicionamento) -> personalidade (VS-0).

Generalization Slice (VS-0.1): o mapa cobre estetica, academia e
barbearia. Sem fallback silencioso: qualquer combinação não mapeada
levanta ThemeResolutionError com prefixo THEME_UNRESOLVED (contrato da API).
"""
from design_system.positioning import MarketPosition
from design_system.visual_policy import VisualPersonality


class ThemeResolutionError(Exception):
    """Combinação (nicho, posicionamento) não mapeada no catálogo."""


class VisualThemeResolver:
    """Resolve a personalidade visual para o par nicho+posicionamento.

    Catálogo fechado do VS-0. Qualquer posição fora do mapeamento
    é uma falha estruturada — NUNCA um fallback silencioso para
    evitar decisões de design arbitrárias.
    """

    # mapa (nicho, position) -> VisualPersonality
    PERSONALITY_MAP: dict[tuple[str, MarketPosition], VisualPersonality] = {
        ("estetica", MarketPosition.PREMIUM): VisualPersonality.PREMIUM_CLINICAL,
        ("academia", MarketPosition.PERFORMANCE): VisualPersonality.PERFORMANCE_RESULT,
        ("barbearia", MarketPosition.MODERN): VisualPersonality.BOLD_URBAN,
    }

    def resolve(self, niche: str, market_position: MarketPosition) -> VisualPersonality:
        key = ((niche or "").strip().lower(), market_position)
        personality = self.PERSONALITY_MAP.get(key)
        if personality is None:
            raise ThemeResolutionError(
                f"THEME_UNRESOLVED: (nicho='{niche}', position='{market_position.value}') "
                "fora do catálogo VS-0"
            )
        return personality