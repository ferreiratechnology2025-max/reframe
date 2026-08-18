"""
Testes do VisualThemeResolver (VS-2).

VS-2: a resolução visual é 100% POSITION-DRIVEN. O nicho NÃO participa:
posições iguais produzem o MESMO template, para qualquer nicho (inclusive
nichos fora do mapa comercial). Sem fallback silencioso: posição fora do
POSITION_TEMPLATE_MAP levanta ThemeResolutionError (prefixo THEME_UNRESOLVED).
"""
import pytest

from design_system.positioning import MarketPosition
from design_system.visual_template import TEMPLATES
from engines.theme_resolver import VisualThemeResolver, ThemeResolutionError


@pytest.fixture
def resolver() -> VisualThemeResolver:
    return VisualThemeResolver()


class TestPositionOnlyResolution:
    @pytest.mark.parametrize("position,expected_id", [
        (MarketPosition.PREMIUM, "PREMIUM_CLINICAL"),
        (MarketPosition.PERFORMANCE, "PERFORMANCE_RESULT"),
        (MarketPosition.NATURAL, "NATURAL_ELEGANT"),
        (MarketPosition.LUXURY, "LUXURY_MINIMAL"),
        (MarketPosition.TRADITIONAL, "ORGANIC_WARM"),
        (MarketPosition.MODERN, "MODERN_TECH"),
    ])
    def test_position_resolves_to_template(self, resolver, position, expected_id):
        template = resolver.resolve("estetica", position)
        assert template.id == expected_id

    @pytest.mark.parametrize("position", [
        MarketPosition.UNDETERMINED,
        MarketPosition.MAINSTREAM,
        MarketPosition.PRICE,
        MarketPosition.INNOVATION,
        MarketPosition.EXPERT,
        MarketPosition.HERITAGE,
        MarketPosition.COMMUNITY,
    ])
    def test_unmapped_position_raises(self, resolver, position):
        with pytest.raises(ThemeResolutionError) as exc:
            resolver.resolve("estetica", position)
        assert str(exc.value).startswith("THEME_UNRESOLVED:")

    def test_undetermined_raises(self, resolver):
        with pytest.raises(ThemeResolutionError):
            resolver.resolve("estetica", MarketPosition.UNDETERMINED)

    def test_niche_does_not_change_resolution(self, resolver):
        """Mesma posição -> mesmo template, independente do nicho."""
        for pos in [MarketPosition.PREMIUM, MarketPosition.NATURAL, MarketPosition.MODERN]:
            ids = {
                resolver.resolve(n, pos).id
                for n in ["estetica", "academia", "barbearia", "novo_nicho"]
            }
            assert len(ids) == 1

    def test_new_niche_resolves_any_position(self, resolver):
        for pos in [MarketPosition.NATURAL, MarketPosition.LUXURY, MarketPosition.TRADITIONAL]:
            template = resolver.resolve("qualquer_coisa", pos)
            assert template in TEMPLATES.values()

    def test_determinism(self, resolver):
        assert (
            resolver.resolve("estetica", MarketPosition.PREMIUM)
            is resolver.resolve("estetica", MarketPosition.PREMIUM)
        )