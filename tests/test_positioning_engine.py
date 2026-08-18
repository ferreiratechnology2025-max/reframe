"""
Testes da PositioningEngine (VS-0) — mapeamento determinístico.

Regra do slice VS-0: estetica -> PREMIUM (fixo). Nenhuma decisão vem de
LLM. Nichos fora do escopo retornam UNDETERMINED (falha estruturada).
"""
import pytest

from design_system.positioning import MarketPosition
from engines.positioning_engine import PositioningEngine


@pytest.fixture
def engine() -> PositioningEngine:
    return PositioningEngine()


class TestVs0FixedMapping:
    def test_estetica_maps_to_premium(self, engine):
        decision = engine.determine("estetica")
        assert decision.market_position == MarketPosition.PREMIUM
        assert not decision.is_undetermined

    def test_estetica_premium_has_expected_profile(self, engine):
        decision = engine.determine("estetica")
        assert decision.evidence_strength == 0.85
        assert decision.tone == "sofisticado"
        assert "vs0_fixed_mapping" in decision.decision_reasons
        assert decision.value_proposition

    def test_estetica_case_insensitive(self, engine):
        assert engine.determine("ESTETICA").market_position == MarketPosition.PREMIUM
        assert engine.determine("  Estetica  ").market_position == MarketPosition.PREMIUM

    def test_unknown_niche_is_undetermined(self, engine):
        decision = engine.determine("restaurante")
        assert decision.market_position == MarketPosition.UNDETERMINED
        assert decision.is_undetermined
        assert "nichos_fora_do_escopo_vs0" in decision.decision_reasons

    def test_empty_niche_is_undetermined(self, engine):
        assert engine.determine("").is_undetermined
        assert engine.determine(None).is_undetermined

    def test_determinism(self, engine):
        a = engine.determine("estetica")
        b = engine.determine("estetica")
        assert a.model_dump() == b.model_dump()

    def test_evidence_param_does_not_change_vs0_mapping(self, engine):
        """VS-0: mapping fixo — evidência não altera a decisão."""
        a = engine.determine("estetica", evidence={"rating": 4.8, "total_ratings": 327})
        b = engine.determine("estetica", evidence={})
        assert a.market_position == b.market_position == MarketPosition.PREMIUM

    def test_positioning_map_contains_all_niches(self, engine):
        """Todos os nichos do Generalization Slice têm mapeamento fixo."""
        for niche in ["estetica", "academia", "barbearia"]:
            pos = engine.determine(niche, {})
            assert pos.market_position != MarketPosition.UNDETERMINED, niche

    def test_academia_maps_to_performance(self, engine):
        decision = engine.determine("academia")
        assert decision.market_position == MarketPosition.PERFORMANCE
        assert not decision.is_undetermined
        assert decision.evidence_strength == 0.80
        assert decision.tone == "direto"
        assert decision.value_proposition == "Transforme seu corpo com treinos de alta performance"
        assert decision.target_audience == "jovens e adultos 18-50 anos, todos os níveis"
        assert "vs0_fixed_mapping" in decision.decision_reasons

    def test_barbearia_maps_to_modern(self, engine):
        decision = engine.determine("barbearia")
        assert decision.market_position == MarketPosition.MODERN
        assert not decision.is_undetermined
        assert decision.evidence_strength == 0.75
        assert decision.tone == "confiável"
        assert decision.value_proposition == "Estilo e tradição em cada corte"
        assert decision.target_audience == "homens 18-60 anos"

    def test_new_niches_are_case_insensitive(self, engine):
        assert engine.determine("ACADEMIA").market_position == MarketPosition.PERFORMANCE
        assert engine.determine("  Barbearia ").market_position == MarketPosition.MODERN

    def test_unknown_niche_reason_marker(self, engine):
        decision = engine.determine("restaurante")
        assert decision.market_position == MarketPosition.UNDETERMINED
        assert "nichos_fora_do_escopo_vs0" in decision.decision_reasons