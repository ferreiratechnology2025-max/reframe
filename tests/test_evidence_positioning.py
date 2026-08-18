"""
Testes do EvidencePositioningEngine (VS-1) — refinamento determinístico.

Matriz congelada VS-1:
- SUPPORTED_POSITIONS por nicho (refinamento restrito ao conjunto).
- Especialidades resolvidas por PRIORIDADE explícita, não por ordem da lista.
- Precedência: especialidade > rating+volume > base.
- Evidência ausente → posição base (comportamento VS-0.x).
- rating < minimum → UNDETERMINED → bloqueio.
- Nenhuma posição fora do catálogo do nicho.
"""
import pytest

from design_system.evidence_positioning import (
    EvidencePositioningEngine,
    SUPPORTED_POSITIONS,
)
from design_system.positioning import MarketPosition
from engines.theme_resolver import VisualThemeResolver


@pytest.fixture
def engine() -> EvidencePositioningEngine:
    return EvidencePositioningEngine()


class TestMarketPositionVs1:
    def test_luxury_exists(self):
        assert MarketPosition.LUXURY == "LUXURY"

    def test_traditional_exists(self):
        assert MarketPosition.TRADITIONAL == "TRADITIONAL"


class TestSupportedPositions:
    def test_estetica_supported_set(self):
        assert SUPPORTED_POSITIONS["estetica"] == [
            MarketPosition.PREMIUM,
            MarketPosition.NATURAL,
            MarketPosition.PERFORMANCE,
        ]

    def test_academia_supported_set(self):
        assert SUPPORTED_POSITIONS["academia"] == [
            MarketPosition.PERFORMANCE,
            MarketPosition.MODERN,
            MarketPosition.NATURAL,
        ]

    def test_barbearia_supported_set(self):
        assert SUPPORTED_POSITIONS["barbearia"] == [
            MarketPosition.LUXURY,
            MarketPosition.TRADITIONAL,
            MarketPosition.MODERN,
        ]


class TestEsteticaMatrix:
    @pytest.mark.parametrize(
        "specialty,expected",
        [
            ("injetáveis", MarketPosition.PREMIUM),
            ("botox", MarketPosition.PREMIUM),
            ("preenchedor", MarketPosition.PREMIUM),
            ("facial", MarketPosition.NATURAL),
            ("limpeza", MarketPosition.NATURAL),
            ("peeling", MarketPosition.NATURAL),
        ],
    )
    def test_specialty_refinement(self, engine, specialty, expected):
        pos = engine.determine("estetica", {
            "rating": 4.0,
            "total_ratings": 10,
            "specialties": [specialty],
        })
        assert pos.market_position == expected
        assert pos.decision_reasons == ["specialty"]

    @pytest.mark.parametrize(
        "rating,total,expected",
        [
            (4.8, 200, MarketPosition.PREMIUM),
            (4.0, 50, MarketPosition.NATURAL),
            (3.5, 0, MarketPosition.PERFORMANCE),
            (2.9, 500, MarketPosition.UNDETERMINED),
        ],
    )
    def test_rating_volume_refinement(self, engine, rating, total, expected):
        pos = engine.determine("estetica", {
            "rating": rating,
            "total_ratings": total,
            "specialties": [],
        })
        if expected is MarketPosition.UNDETERMINED:
            assert pos.is_undetermined
            assert pos.decision_reasons == ["rating_below_minimum"]
        else:
            assert pos.market_position == expected
            assert pos.decision_reasons == ["rating_volume"]

    def test_no_evidence_uses_base(self, engine):
        pos = engine.determine("estetica")
        assert pos.market_position == MarketPosition.PREMIUM
        assert pos.decision_reasons == ["base_position"]

    def test_empty_evidence_uses_base(self, engine):
        pos = engine.determine("estetica", {})
        assert pos.market_position == MarketPosition.PREMIUM


class TestAcademiaMatrix:
    @pytest.mark.parametrize(
        "specialty,expected",
        [
            ("crossfit", MarketPosition.PERFORMANCE),
            ("hipertrofia", MarketPosition.PERFORMANCE),
            ("pilates", MarketPosition.NATURAL),
            ("yoga", MarketPosition.NATURAL),
        ],
    )
    def test_specialty_refinement(self, engine, specialty, expected):
        pos = engine.determine("academia", {
            "rating": 4.0,
            "total_ratings": 10,
            "specialties": [specialty],
        })
        assert pos.market_position == expected
        assert pos.decision_reasons == ["specialty"]

    @pytest.mark.parametrize(
        "rating,total,expected",
        [
            (4.5, 100, MarketPosition.PERFORMANCE),
            (4.0, 30, MarketPosition.MODERN),
            (3.5, 0, MarketPosition.PERFORMANCE),
            (2.9, 500, MarketPosition.UNDETERMINED),
        ],
    )
    def test_rating_volume_refinement(self, engine, rating, total, expected):
        pos = engine.determine("academia", {
            "rating": rating,
            "total_ratings": total,
            "specialties": [],
        })
        if expected is MarketPosition.UNDETERMINED:
            assert pos.is_undetermined
        else:
            assert pos.market_position == expected

    def test_no_evidence_uses_base(self, engine):
        pos = engine.determine("academia")
        assert pos.market_position == MarketPosition.PERFORMANCE
        assert pos.decision_reasons == ["base_position"]


class TestBarbeariaMatrix:
    @pytest.mark.parametrize(
        "specialty,expected",
        [
            ("barba", MarketPosition.LUXURY),
            ("corte premium", MarketPosition.LUXURY),
            ("corte tradicional", MarketPosition.TRADITIONAL),
        ],
    )
    def test_specialty_refinement(self, engine, specialty, expected):
        pos = engine.determine("barbearia", {
            "rating": 4.0,
            "total_ratings": 10,
            "specialties": [specialty],
        })
        assert pos.market_position == expected
        assert pos.decision_reasons == ["specialty"]

    @pytest.mark.parametrize(
        "rating,total,expected",
        [
            (4.5, 100, MarketPosition.MODERN),
            (4.0, 30, MarketPosition.TRADITIONAL),
            (3.5, 0, MarketPosition.MODERN),
            (2.9, 500, MarketPosition.UNDETERMINED),
        ],
    )
    def test_rating_volume_refinement(self, engine, rating, total, expected):
        pos = engine.determine("barbearia", {
            "rating": rating,
            "total_ratings": total,
            "specialties": [],
        })
        if expected is MarketPosition.UNDETERMINED:
            assert pos.is_undetermined
        else:
            assert pos.market_position == expected

    def test_no_evidence_uses_base(self, engine):
        pos = engine.determine("barbearia")
        assert pos.market_position == MarketPosition.MODERN
        assert pos.decision_reasons == ["base_position"]


class TestSpecialtyPriority:
    @pytest.mark.parametrize("specialties", [
        ["facial", "injetáveis"],
        ["injetáveis", "facial"],
        ["facial", "botox", "limpeza"],
        ["botox", "facial"],
    ])
    def test_specialty_resolution_order_independent(self, engine, specialties):
        """Especialidades resolvidas por PRIORIDADE, não por ordem da lista."""
        pos = engine.determine("estetica", {
            "rating": 4.2,
            "total_ratings": 327,
            "specialties": specialties,
        })
        assert pos.market_position == MarketPosition.PREMIUM
        assert pos.decision_reasons == ["specialty"]

    def test_barbearia_luxury_beats_traditional(self, engine):
        """Prioridade explícita também vale para barbearia (LUXURY > TRADITIONAL)."""
        a = engine.determine("barbearia", {
            "specialties": ["barba", "corte tradicional"],
        })
        b = engine.determine("barbearia", {
            "specialties": ["corte tradicional", "barba"],
        })
        assert a.market_position == MarketPosition.LUXURY
        assert b.market_position == a.market_position

    def test_specialty_beats_rating(self, engine):
        """Precedência: especialidade > rating+volume."""
        pos = engine.determine("estetica", {
            "rating": 4.8,
            "total_ratings": 327,
            "specialties": ["facial"],
        })
        # facial → NATURAL (especialidade vence; rating sozinho daria PREMIUM)
        assert pos.market_position == MarketPosition.NATURAL


class TestUndetermined:
    def test_unknown_niche_is_undetermined(self, engine):
        pos = engine.determine("restaurante", {"rating": 4.8})
        assert pos.is_undetermined
        assert pos.decision_reasons == ["nichos_fora_do_escopo_vs1"]

    def test_empty_niche_is_undetermined(self, engine):
        assert engine.determine("").is_undetermined
        assert engine.determine(None).is_undetermined

    def test_rating_below_minimum_reason(self, engine):
        pos = engine.determine("estetica", {"rating": 2.0})
        assert pos.is_undetermined
        assert pos.decision_reasons == ["rating_below_minimum"]


class TestCommercialProfiles:
    def test_estetica_premium_profile(self, engine):
        pos = engine.determine("estetica")
        assert pos.value_proposition == "Excelência clínica com resultados naturais"
        assert pos.tone == "sofisticado"
        assert pos.target_audience == "mulheres e homens 25-60 anos, classes A/B"

    def test_barbearia_luxury_profile(self, engine):
        pos = engine.determine("barbearia", {"specialties": ["barba"]})
        assert pos.value_proposition == "Experiência premium em cuidados masculinos"
        assert pos.tone == "exclusivo"
        assert pos.target_audience == "homens 25-55 anos, classes A/B"

    def test_academia_modern_profile(self, engine):
        pos = engine.determine("academia", {"rating": 4.0, "total_ratings": 30})
        assert pos.value_proposition == "O futuro do treinamento já chegou"
        assert pos.tone == "inovador"
        assert pos.target_audience == "jovens e adultos 18-45 anos"


class TestThemeResolutionVs2:
    def test_luxury_barbearia_resolves_to_luxury_minimal(self):
        """Barbearia + 'barba' → LUXURY → LUXURY_MINIMAL (VS-2)."""
        pos = EvidencePositioningEngine().determine("barbearia", {
            "specialties": ["barba"],
            "rating": 4.8,
            "total_ratings": 150,
        })
        assert pos.market_position == MarketPosition.LUXURY

        template = VisualThemeResolver().resolve("barbearia", pos.market_position)
        assert template.id == "LUXURY_MINIMAL"

    def test_traditional_barbearia_resolves_to_organic_warm(self):
        pos = EvidencePositioningEngine().determine("barbearia", {
            "specialties": ["corte tradicional"],
        })
        assert pos.market_position == MarketPosition.TRADITIONAL

        template = VisualThemeResolver().resolve("barbearia", pos.market_position)
        assert template.id == "ORGANIC_WARM"

    def test_same_position_resolves_to_same_template_across_niches(self):
        """VS-2: posição igual → template igual, independente do nicho."""
        estetica = EvidencePositioningEngine().determine("estetica", {"specialties": ["facial"]})
        academia = EvidencePositioningEngine().determine("academia", {"specialties": ["pilates"]})
        assert estetica.market_position == MarketPosition.NATURAL
        assert academia.market_position == MarketPosition.NATURAL

        t_estetica = VisualThemeResolver().resolve("estetica", estetica.market_position)
        t_academia = VisualThemeResolver().resolve("academia", academia.market_position)
        assert t_estetica.id == t_academia.id == "NATURAL_ELEGANT"


class TestDeterminismWithVaryingEvidence:
    def test_same_evidence_same_decision(self, engine):
        """Mesma evidência → mesma posição, decision_reasons e strength."""
        evidence = {"rating": 4.8, "total_ratings": 327, "specialties": ["injetáveis"]}
        results = []
        for _ in range(5):
            pos = engine.determine("estetica", evidence)
            results.append((pos.market_position, pos.decision_reasons, pos.evidence_strength))

        for i in range(1, len(results)):
            assert results[0] == results[i]

    def test_different_evidence_different_strength(self, engine):
        """Especialidade tem strength maior que base (determinístico)."""
        specialty = engine.determine("estetica", {"specialties": ["injetáveis"]})
        base = engine.determine("estetica")
        assert specialty.evidence_strength > base.evidence_strength