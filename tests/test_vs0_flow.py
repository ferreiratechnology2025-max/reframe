"""
Testes do fluxo VS-0 — posicionamento → tema → tokens → gate (determinístico).

Comprova a cadeia completa do Design System Engine SEM LLM:
estetica → PREMIUM → PREMIUM_CLINICAL → tokens corretos → gate passa.
E que nichos não mapeados falham com erro estruturado (sem fallback).
"""
import pytest

from design_system.design_tokens import ColorRole
from design_system.positioning import MarketPosition
from engines.positioning_engine import PositioningEngine
from engines.theme_resolver import VisualThemeResolver, ThemeResolutionError
from engines.design_tokens_engine import DesignTokensEngine
from gates.design_token_gate import DesignTokenGate


def test_vs0_premium_clinical_deterministic():
    """VS-2: estetica → PREMIUM → PREMIUM_CLINICAL → tokens corretos."""
    # Positioning
    pos = PositioningEngine().determine("estetica")
    assert pos.market_position == MarketPosition.PREMIUM
    assert pos.evidence_strength == 0.85

    # Theme (position-only)
    template = VisualThemeResolver().resolve("estetica", MarketPosition.PREMIUM)
    assert template.id == "PREMIUM_CLINICAL"

    # Tokens + policy
    tokens, policy = DesignTokensEngine().generate(template)
    assert tokens.colors[ColorRole.BG] == "#F5F3F0"
    assert tokens.colors[ColorRole.ACCENT] == "#C6A87C"
    assert policy.personality == "PREMIUM_CLINICAL"

    # Gate (contraste AA)
    passed, issues = DesignTokenGate().validate(tokens, policy)
    assert passed, issues


def test_vs0_fails_unmapped_position():
    """VS-2: posição não mapeada → UNDETERMINED → falha estruturada."""
    pos = PositioningEngine().determine("restaurante")
    assert pos.market_position == MarketPosition.UNDETERMINED

    with pytest.raises(ThemeResolutionError):
        VisualThemeResolver().resolve("restaurante", MarketPosition.UNDETERMINED)


def test_vs0_engine_error_contracts():
    """Erros das engines carregam prefixo estável reconhecido pela API."""
    with pytest.raises(ThemeResolutionError) as exc:
        VisualThemeResolver().resolve("estetica", MarketPosition.UNDETERMINED)
    assert str(exc.value).startswith("THEME_UNRESOLVED:")

    with pytest.raises(Exception) as exc:
        DesignTokensEngine().generate("nao_existe")
    assert "DESIGN_TOKENS_UNRESOLVED" in str(exc.value)


@pytest.mark.parametrize(
    "niche,position_name,bg,accent,template_name",
    [
        ("estetica", "PREMIUM", "#F5F3F0", "#C6A87C", "PREMIUM_CLINICAL"),
        ("academia", "PERFORMANCE", "#FFFFFF", "#E63946", "PERFORMANCE_RESULT"),
        ("barbearia", "MODERN", "#FFFFFF", "#00E5FF", "MODERN_TECH"),
    ],
)
def test_vs0_generalization_flow(niche, position_name, bg, accent, template_name):
    """VS-2: a mesma cadeia determinística serve os 3 nichos (position-only)."""
    position = MarketPosition[position_name]

    pos = PositioningEngine().determine(niche)
    assert pos.market_position == position

    resolved = VisualThemeResolver().resolve(niche, pos.market_position)
    assert resolved.id == template_name

    tokens, policy = DesignTokensEngine().generate(resolved)
    assert tokens.colors[ColorRole.BG] == bg
    assert tokens.colors[ColorRole.ACCENT] == accent
    assert policy.personality == template_name

    passed, issues = DesignTokenGate().validate(tokens, policy)
    assert passed, issues