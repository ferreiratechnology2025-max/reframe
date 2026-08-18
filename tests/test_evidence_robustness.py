"""
Testes de robustez do pipeline sob variação de evidência (VS-0.2).

Contrato preservado: o posicionamento é FIXO por nicho (POSITIONING_MAP);
a evidência é contexto e NÃO refina a decisão no VS-0/VS-0.1. Refinamento
por evidência é VS-1+ (ver teste skip ao final).
"""
import pytest

from design_system.positioning import MarketPosition
from design_system.visual_policy import VisualPersonality
from engines.design_tokens_engine import DesignTokensEngine
from engines.positioning_engine import PositioningEngine
from engines.theme_resolver import ThemeResolutionError, VisualThemeResolver
from gates.design_token_gate import DesignTokenGate


class TestEvidenceRobustness:
    """Testa que o sistema é robusto sob diferentes condições de evidência."""

    def test_complete_evidence_does_not_break(self, complete_evidence):
        """Evidência completa → fluxo normal (posicionamento fixo por nicho)."""
        pos = PositioningEngine().determine("estetica", complete_evidence)
        # VS-0: estetica → PREMIUM (fixo, independente da evidência)
        assert pos.market_position == MarketPosition.PREMIUM

        personality = VisualThemeResolver().resolve("estetica", pos.market_position)
        assert personality == VisualPersonality.PREMIUM_CLINICAL

        tokens, policy = DesignTokensEngine().generate(personality)
        passed, issues = DesignTokenGate().validate(tokens, policy)
        assert passed, issues

    def test_minimal_evidence_does_not_break(self, minimal_evidence):
        """Evidência mínima → usa defaults, não quebra."""
        pos = PositioningEngine().determine("estetica", minimal_evidence)
        assert pos.market_position == MarketPosition.PREMIUM  # fixo por nicho

        personality = VisualThemeResolver().resolve("estetica", pos.market_position)
        assert personality == VisualPersonality.PREMIUM_CLINICAL

    def test_unmapped_niche_fails_regardless_of_evidence(self, complete_evidence):
        """Nicho não mapeado → UNDETERMINED → falha (evidência não salva)."""
        pos = PositioningEngine().determine("restaurante", complete_evidence)
        assert pos.market_position == MarketPosition.UNDETERMINED

        with pytest.raises(ThemeResolutionError):
            VisualThemeResolver().resolve("restaurante", pos.market_position)

    def test_location_absent_does_not_break_pipeline(self, minimal_evidence):
        """Localização ausente → pipeline não quebra (LocationPolicy gerencia)."""
        pos = PositioningEngine().determine("estetica", minimal_evidence)
        assert pos.market_position == MarketPosition.PREMIUM

        personality = VisualThemeResolver().resolve("estetica", pos.market_position)
        tokens, policy = DesignTokensEngine().generate(personality)

        passed, issues = DesignTokenGate().validate(tokens, policy)
        assert passed, issues

    @pytest.mark.skip(reason="VS-1: evidence-driven positioning refinement")
    def test_evidence_refines_positioning(self):
        """VS-1: evidência pode refinar posicionamento (NÃO implementado)."""
        pass
