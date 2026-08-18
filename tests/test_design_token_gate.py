"""
Testes do DesignTokenGate (VS-0) — valida ANTES do LLM.

Regras (WCAG AA): contraste texto/fundo >= 4.5, accent/on_accent >= 3.0,
roles obrigatórios, coesão da política visual. Falha = STOP.
Contrato de saída: (passed, issues).
"""
import pytest

from design_system.design_tokens import ColorRole, DesignTokens, FontSpec, SemanticColor, TypographyPolicy
from design_system.visual_policy import CATALOG, VisualPersonality
from gates.contrast import contrast_ratio
from gates.design_token_gate import DesignTokenGate


def make_tokens(**overrides) -> DesignTokens:
    data = {
        "personality": VisualPersonality.PREMIUM_CLINICAL.value,
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
            heading=FontSpec(family="Playfair Display", source="google", weights=[400, 600]),
            body=FontSpec(family="Inter", source="google", weights=[400, 500]),
        ),
    }
    data.update(overrides)
    return DesignTokens(**data)


@pytest.fixture
def gate() -> DesignTokenGate:
    return DesignTokenGate()


@pytest.fixture
def tokens() -> DesignTokens:
    return make_tokens()


@pytest.fixture
def policy():
    return CATALOG[VisualPersonality.PREMIUM_CLINICAL]


class TestContrastUtility:
    def test_reference_black_on_white(self):
        assert abs(contrast_ratio("#FFFFFF", "#000000") - 21.0) < 0.01

    def test_premium_pair_passes_gate_minimum(self):
        """ON_ACCENT #1A1A1A sobre ACCENT #C6A87C = 7.70:1 (>= 3.0)."""
        ratio = contrast_ratio("#C6A87C", "#1A1A1A")
        assert ratio >= 3.0

    def test_spec_original_pair_would_fail(self):
        """A combinação original do spec (#FFFFFF sobre #C6A87C = 2.26:1) FALHA."""
        ratio = contrast_ratio("#C6A87C", "#FFFFFF")
        assert ratio < 3.0


class TestDesignTokenGateRules:
    def test_premium_clinical_tokens_pass(self, gate, tokens, policy):
        passed, issues = gate.validate(tokens, policy)
        assert passed, issues
        assert issues == []

    def test_text_bg_contrast_enforced(self, gate, tokens, policy):
        bad = make_tokens(colors={**tokens.colors, ColorRole.TEXT: "#B0A89C"})
        passed, issues = gate.validate(bad, policy)
        assert not passed
        assert any("contraste" in v.lower() for v in issues)

    def test_on_accent_contrast_enforced(self, gate, tokens, policy):
        bad = make_tokens(colors={**tokens.colors, ColorRole.ON_ACCENT: "#FFFFFF"})
        passed, issues = gate.validate(bad, policy)
        assert not passed
        assert any("on_accent" in v for v in issues)

    def test_accent_cannot_equal_background(self, gate, tokens, policy):
        bad = make_tokens(colors={**tokens.colors, ColorRole.ACCENT: tokens.colors[ColorRole.BG]})
        passed, issues = gate.validate(bad, policy)
        assert not passed
        assert any("accent" in v and "bg" in v for v in issues)

    def test_personality_mismatch_blocked(self, gate, tokens, policy):
        bad = make_tokens(personality="mainstream")
        passed, issues = gate.validate(bad, policy)
        assert not passed
        assert any("personality" in v.lower() for v in issues)

    def test_gate_is_deterministic(self, gate, tokens, policy):
        assert gate.validate(tokens, policy)[1] == gate.validate(tokens, policy)[1]

    def test_result_contract_is_tuple(self, gate, tokens, policy):
        result = gate.validate(tokens, policy)
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)