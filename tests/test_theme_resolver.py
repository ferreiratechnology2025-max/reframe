"""
Testes do VisualThemeResolver (VS-0).

Mapeia (nicho, posicionamento) -> personalidade visual. Sem fallback
silencioso: combinação não mapeada levanta ThemeResolutionError.
"""
import pytest

from design_system.positioning import MarketPosition
from design_system.visual_policy import VisualPersonality
from engines.theme_resolver import VisualThemeResolver, ThemeResolutionError


@pytest.fixture
def resolver() -> VisualThemeResolver:
    return VisualThemeResolver()


class TestThemeResolution:
    def test_estetica_premium_maps_to_premium_clinical(self, resolver):
        personality = resolver.resolve("estetica", MarketPosition.PREMIUM)
        assert personality == VisualPersonality.PREMIUM_CLINICAL

    def test_unmapped_position_raises(self, resolver):
        """Sem fallback silencioso: posição não suportada -> erro estruturado."""
        with pytest.raises(ThemeResolutionError) as exc:
            resolver.resolve("estetica", MarketPosition.PERFORMANCE)
        assert str(exc.value).startswith("THEME_UNRESOLVED:")
        assert "PERFORMANCE" in str(exc.value)

    def test_undetermined_raises(self, resolver):
        with pytest.raises(ThemeResolutionError):
            resolver.resolve("estetica", MarketPosition.UNDETERMINED)

    def test_unknown_niche_raises(self, resolver):
        with pytest.raises(ThemeResolutionError):
            resolver.resolve("dentista", MarketPosition.PREMIUM)

    def test_estetica_other_positions_raise(self, resolver):
        for pos in (MarketPosition.NATURAL, MarketPosition.MAINSTREAM, MarketPosition.PERFORMANCE):
            with pytest.raises(ThemeResolutionError):
                resolver.resolve("estetica", pos)

    def test_determinism(self, resolver):
        assert (
            resolver.resolve("estetica", MarketPosition.PREMIUM)
            == resolver.resolve("estetica", MarketPosition.PREMIUM)
        )

    def test_academia_performance_maps_to_performance_result(self, resolver):
        personality = resolver.resolve("academia", MarketPosition.PERFORMANCE)
        assert personality == VisualPersonality.PERFORMANCE_RESULT

    def test_barbearia_modern_maps_to_bold_urban(self, resolver):
        personality = resolver.resolve("barbearia", MarketPosition.MODERN)
        assert personality == VisualPersonality.BOLD_URBAN

    def test_academia_wrong_position_raises(self, resolver):
        """academia com posição errada não mapeia (sem fallback)."""
        with pytest.raises(ThemeResolutionError):
            resolver.resolve("academia", MarketPosition.PREMIUM)

    def test_barbearia_wrong_position_raises(self, resolver):
        with pytest.raises(ThemeResolutionError):
            resolver.resolve("barbearia", MarketPosition.PERFORMANCE)