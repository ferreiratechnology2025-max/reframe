"""
Testes do fluxo VS-0 — posicionamento → tema → tokens → gate (determinístico).

Comprova a cadeia completa do Design System Engine SEM LLM:
estetica → PREMIUM → PREMIUM_CLINICAL → tokens corretos → gate passa.
E que nichos não mapeados falham com erro estruturado (sem fallback).
"""
import pytest

from design_system.design_tokens import ColorRole
from design_system.positioning import MarketPosition
from design_system.visual_policy import VisualPersonality
from engines.positioning_engine import PositioningEngine
from engines.theme_resolver import VisualThemeResolver, ThemeResolutionError
from engines.design_tokens_engine import DesignTokensEngine
from gates.design_token_gate import DesignTokenGate


def test_vs0_premium_clinical_deterministic():
    """VS-0: estetica → PREMIUM → PREMIUM_CLINICAL → tokens corretos."""
    # Positioning
    pos = PositioningEngine().determine("estetica")
    assert pos.market_position == MarketPosition.PREMIUM
    assert pos.evidence_strength == 0.85

    # Theme
    personality = VisualThemeResolver().resolve("estetica", MarketPosition.PREMIUM)
    assert personality == VisualPersonality.PREMIUM_CLINICAL

    # Tokens + policy
    tokens, policy = DesignTokensEngine().generate(personality)
    assert tokens.colors[ColorRole.BG] == "#F5F3F0"
    assert tokens.colors[ColorRole.ACCENT] == "#C6A87C"
    assert policy.personality == VisualPersonality.PREMIUM_CLINICAL

    # Gate (contraste AA)
    passed, issues = DesignTokenGate().validate(tokens, policy)
    assert passed, issues


def test_vs0_fails_unmapped_niche():
    """VS-0: nicho não mapeado → UNDETERMINED → falha estruturada."""
    pos = PositioningEngine().determine("restaurante")
    assert pos.market_position == MarketPosition.UNDETERMINED

    with pytest.raises(ThemeResolutionError):
        VisualThemeResolver().resolve("restaurante", MarketPosition.PREMIUM)


def test_vs0_engine_error_contracts():
    """Erros das engines carregam prefixo estável reconhecido pela API."""
    with pytest.raises(ThemeResolutionError) as exc:
        VisualThemeResolver().resolve("estetica", MarketPosition.PERFORMANCE)
    assert str(exc.value).startswith("THEME_UNRESOLVED:")

    with pytest.raises(Exception) as exc:
        DesignTokensEngine().generate("nao_existe")
    assert "DESIGN_TOKENS_UNRESOLVED" in str(exc.value)