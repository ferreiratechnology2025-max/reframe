"""
Testes dos contratos do Design Tokens (VS-0).

Validam que os modelos de tokens são deterministicos, validados e
serializáveis para CSS variables — a base do Design System Engine.
"""
import pytest
from pydantic import ValidationError

from design_system.design_tokens import (
    ColorRole,
    SemanticColor,
    FontSpec,
    TypographyPolicy,
    DesignTokens,
)


# ─── Fixtures ──────────────────────────────────────────────

def make_tokens(**overrides) -> DesignTokens:
    data = {
        "personality": "premium_clinical",
        "colors": {
            ColorRole.BG: "#F5F3F0",
            ColorRole.SURFACE: "#FFFFFF",
            ColorRole.TEXT: "#1A1A1A",
            ColorRole.TEXT_SECONDARY: "#4A4A4A",
            ColorRole.HEADING: "#1A1A1A",
            ColorRole.BORDER: "#E8E3DD",
            ColorRole.ACCENT: "#C6A87C",
            ColorRole.ACCENT_HOVER: "#B8976A",
            ColorRole.ON_ACCENT: "#1A1A1A",
        },
        "semantic_colors": {
            SemanticColor.SUCCESS: "#2E7D32",
            SemanticColor.WARNING: "#B26A00",
            SemanticColor.ERROR: "#C62828",
            SemanticColor.INFO: "#1565C0",
        },
        "typography": TypographyPolicy(
            heading=FontSpec(
                family="Playfair Display",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Georgia, serif",
            size_base="16px",
            line_height="1.6",
            line_height_heading="1.2",
        ),
    }
    data.update(overrides)
    return DesignTokens(**data)


class TestDesignTokensContract:
    def test_valid_tokens_construct(self):
        tokens = make_tokens()
        assert tokens.personality == "premium_clinical"
        assert tokens.colors[ColorRole.BG] == "#F5F3F0"
        assert tokens.colors[ColorRole.ACCENT] == "#C6A87C"

    def test_required_color_roles_enforced(self):
        """Modelo exige os roles obrigatorios (BG, SURFACE, TEXT, ACCENT, ON_ACCENT)."""
        with pytest.raises(ValidationError):
            make_tokens(colors={ColorRole.BG: "#F5F3F0"})

    def test_hex_color_format_validated(self):
        with pytest.raises(ValidationError):
            make_tokens(colors={
                **make_tokens().colors,
                ColorRole.ACCENT: "red",  # nao-hex
            })

    def test_font_source_literal(self):
        with pytest.raises(ValidationError):
            TypographyPolicy(
                heading=FontSpec(family="X", source="cdn", weights=[400]),
                body=FontSpec(family="Y", source="system", weights=[400]),
            )

    def test_weights_must_be_positive(self):
        with pytest.raises(ValidationError):
            FontSpec(family="X", source="system", weights=[0])

    def test_semantic_colors_present(self):
        tokens = make_tokens()
        assert tokens.semantic_colors[SemanticColor.SUCCESS] == "#2E7D32"


class TestCssVariables:
    def test_get_css_variables_emits_color_tokens(self):
        tokens = make_tokens()
        css = tokens.get_css_variables()
        assert "--color-bg: #F5F3F0;" in css
        assert "--color-accent: #C6A87C;" in css
        assert "--color-on-accent: #1A1A1A;" in css
        assert "--color-text-secondary: #4A4A4A;" in css

    def test_get_css_variables_emits_typography_tokens(self):
        tokens = make_tokens()
        css = tokens.get_css_variables()
        assert "--font-heading:" in css
        assert "--font-body:" in css

    def test_get_css_variables_is_deterministic(self):
        a = make_tokens().get_css_variables()
        b = make_tokens().get_css_variables()
        assert a == b

    def test_get_font_links_google(self):
        tokens = make_tokens()
        links = tokens.get_font_links()
        assert "fonts.googleapis.com" in links
        assert "Playfair+Display" in links
        assert "Inter" in links

    def test_get_font_links_empty_for_system_only(self):
        tokens = make_tokens(typography=TypographyPolicy(
            heading=FontSpec(family="Georgia", source="system", weights=[400]),
            body=FontSpec(family="Arial", source="system", weights=[400]),
        ))
        assert tokens.get_font_links() == ""
