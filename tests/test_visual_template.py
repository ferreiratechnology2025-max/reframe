"""
Testes do VS-2 — Reusable Visual Templates (contrato congelado).

VS-2 desacopla a seleção visual do nicho:
- VisualTemplate é entidade reutilizável, independente de nicho.
- POSITION_TEMPLATE_MAP: MarketPosition -> VisualTemplate (position-only).
- Resolver NÃO conhece nichos: posições iguais => templates iguais,
  para qualquer nicho (inclusive nichos fora do mapa comercial).
- 7 templates no catálogo; BOLD_URBAN fora do mapa ativo (MODERN -> MODERN_TECH).
- Teste mandatório: resolve(niche, NATURAL).id == "NATURAL_ELEGANT" para
  ["estetica","academia","barbearia","novo_nicho","qualquer_coisa"].
"""
import pytest

from design_system.design_tokens import ColorRole
from design_system.positioning import MarketPosition
from design_system.visual_template import TEMPLATES, VisualTemplate
from engines.design_tokens_engine import DesignTokensEngine
from engines.theme_resolver import (
    POSITION_TEMPLATE_MAP,
    ThemeResolutionError,
    VisualThemeResolver,
)
from gates.design_token_gate import DesignTokenGate


ALL_NICHES = ["estetica", "academia", "barbearia", "novo_nicho", "qualquer_coisa"]


class TestTemplateCatalog:
    def test_catalog_has_seven_templates(self):
        assert set(TEMPLATES) == {
            "PREMIUM_CLINICAL",
            "PERFORMANCE_RESULT",
            "BOLD_URBAN",
            "NATURAL_ELEGANT",
            "LUXURY_MINIMAL",
            "MODERN_TECH",
            "ORGANIC_WARM",
        }

    def test_each_template_builds_coherent_tokens(self):
        for template in TEMPLATES.values():
            tokens, policy = DesignTokensEngine().generate(template)
            assert tokens.personality == template.id
            assert policy.personality == template.id

    def test_all_templates_pass_design_token_gate(self):
        for template in TEMPLATES.values():
            tokens, policy = DesignTokensEngine().generate(template)
            passed, issues = DesignTokenGate().validate(tokens, policy)
            assert passed, f"{template.id}: {issues}"


class TestPositionTemplateMap:
    def test_position_map_has_six_entries(self):
        assert set(POSITION_TEMPLATE_MAP) == {
            MarketPosition.PREMIUM,
            MarketPosition.PERFORMANCE,
            MarketPosition.NATURAL,
            MarketPosition.LUXURY,
            MarketPosition.TRADITIONAL,
            MarketPosition.MODERN,
        }

    @pytest.mark.parametrize("position,expected_id", [
        (MarketPosition.PREMIUM, "PREMIUM_CLINICAL"),
        (MarketPosition.PERFORMANCE, "PERFORMANCE_RESULT"),
        (MarketPosition.NATURAL, "NATURAL_ELEGANT"),
        (MarketPosition.LUXURY, "LUXURY_MINIMAL"),
        (MarketPosition.TRADITIONAL, "ORGANIC_WARM"),
        (MarketPosition.MODERN, "MODERN_TECH"),
    ])
    def test_each_position_resolves_to_expected_template(self, position, expected_id):
        template = VisualThemeResolver().resolve("qualquer_nicho", position)
        assert isinstance(template, VisualTemplate)
        assert template.id == expected_id


class TestPositionOnlyResolution:
    def test_mandatory_natural_mapping_for_all_niches(self):
        """Teste mandatório congelado: NATURAL -> NATURAL_ELEGANT p/ qualquer nicho."""
        resolver = VisualThemeResolver()
        for niche in ALL_NICHES:
            assert resolver.resolve(niche, MarketPosition.NATURAL).id == "NATURAL_ELEGANT"

    def test_central_property_same_position_same_template(self):
        """∀ niche1, niche2: position(niche1)=position(niche2) => template(niche1)=template(niche2)."""
        resolver = VisualThemeResolver()
        for position in POSITION_TEMPLATE_MAP:
            ids = {resolver.resolve(n, position).id for n in ALL_NICHES}
            assert len(ids) == 1, position

    def test_new_niche_reuses_existing_template(self):
        template = VisualThemeResolver().resolve("novo_nicho", MarketPosition.NATURAL)
        assert template.id == "NATURAL_ELEGANT"
        assert template is TEMPLATES["NATURAL_ELEGANT"]

    def test_unmapped_position_raises(self):
        with pytest.raises(ThemeResolutionError) as exc:
            VisualThemeResolver().resolve("estetica", MarketPosition.UNDETERMINED)
        assert str(exc.value).startswith("THEME_UNRESOLVED:")

    def test_determinism_same_object(self):
        resolver = VisualThemeResolver()
        assert (
            resolver.resolve("estetica", MarketPosition.PREMIUM)
            is resolver.resolve("academia", MarketPosition.PREMIUM)
        )


class TestTemplateTokens:
    @pytest.mark.parametrize("template_id,bg,accent", [
        ("PREMIUM_CLINICAL", "#F5F3F0", "#C6A87C"),
        ("PERFORMANCE_RESULT", "#FFFFFF", "#E63946"),
        ("NATURAL_ELEGANT", "#F7F5F0", "#7A8B6F"),
        ("LUXURY_MINIMAL", "#111111", "#C9A96A"),
        ("MODERN_TECH", "#FFFFFF", "#00E5FF"),
        ("ORGANIC_WARM", "#E8E6D9", "#A97C50"),
    ])
    def test_mapped_templates_token_values(self, template_id, bg, accent):
        tokens, _ = DesignTokensEngine().generate(TEMPLATES[template_id])
        assert tokens.colors[ColorRole.BG] == bg
        assert tokens.colors[ColorRole.ACCENT] == accent