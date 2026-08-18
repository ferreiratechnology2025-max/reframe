"""
Testes de robustez do pipeline sob variação de evidência (VS-0.2 → VS-1).

Contrato VS-1: o posicionamento tem ÂNCORA fixa por nicho (POSITIONING_MAP),
mas a evidência PODE refinar dentro das posições suportadas. Evidência
ausente → posição base. UNDETERMINED → bloqueio.
"""
import pytest

from design_system.evidence_positioning import EvidencePositioningEngine
from design_system.positioning import MarketPosition
from engines.design_tokens_engine import DesignTokensEngine
from engines.theme_resolver import ThemeResolutionError, VisualThemeResolver
from gates.design_token_gate import DesignTokenGate


class TestEvidenceRobustness:
    """Testa que o sistema é robusto sob diferentes condições de evidência."""

    def test_complete_evidence_does_not_break(self, complete_evidence):
        """Evidência completa → fluxo normal (estetica permanece PREMIUM)."""
        pos = EvidencePositioningEngine().determine("estetica", complete_evidence)
        # facial→NATURAL, injetáveis→PREMIUM → prioridade PREMIUM vence
        assert pos.market_position == MarketPosition.PREMIUM

        template = VisualThemeResolver().resolve("estetica", pos.market_position)
        assert template.id == "PREMIUM_CLINICAL"

        tokens, policy = DesignTokensEngine().generate(template)
        passed, issues = DesignTokenGate().validate(tokens, policy)
        assert passed, issues

    def test_minimal_evidence_does_not_break(self, minimal_evidence):
        """Evidência mínima → usa defaults, não quebra (base = PREMIUM)."""
        pos = EvidencePositioningEngine().determine("estetica", minimal_evidence)
        assert pos.market_position == MarketPosition.PREMIUM  # base por nicho

        template = VisualThemeResolver().resolve("estetica", pos.market_position)
        assert template.id == "PREMIUM_CLINICAL"

    def test_unmapped_niche_fails_regardless_of_evidence(self, complete_evidence):
        """Nicho não mapeado → UNDETERMINED → falha (evidência não salva)."""
        pos = EvidencePositioningEngine().determine("restaurante", complete_evidence)
        assert pos.market_position == MarketPosition.UNDETERMINED

        with pytest.raises(ThemeResolutionError):
            VisualThemeResolver().resolve("restaurante", pos.market_position)

    def test_location_absent_does_not_break_pipeline(self, minimal_evidence):
        """Localização ausente → pipeline não quebra (LocationPolicy gerencia)."""
        pos = EvidencePositioningEngine().determine("estetica", minimal_evidence)
        assert pos.market_position == MarketPosition.PREMIUM

        template = VisualThemeResolver().resolve("estetica", pos.market_position)
        tokens, policy = DesignTokensEngine().generate(template)

        passed, issues = DesignTokenGate().validate(tokens, policy)
        assert passed, issues

    def test_evidence_refines_positioning(self):
        """VS-1: evidência refina posicionamento dentro das posições suportadas."""
        # estetica: facial → NATURAL (refinamento da base PREMIUM)
        pos = EvidencePositioningEngine().determine("estetica", {
            "rating": 4.8,
            "total_ratings": 327,
            "specialties": ["facial"],
        })
        assert pos.market_position == MarketPosition.NATURAL
        assert pos.decision_reasons == ["specialty"]