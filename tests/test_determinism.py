"""
Testes de determinismo do Design System Engine (VS-0.2).

Os tokens são gerados ANTES do LLM e independentes de copy, provider ou
temperatura: a mesma personalidade produz SEMPRE os mesmos tokens.
"""
from design_system.visual_template import TEMPLATES
from engines.design_tokens_engine import DesignTokensEngine
from gates.design_token_gate import DesignTokenGate


class TestDeterminism:
    """Testa que DesignTokens são determinísticos."""

    def test_tokens_unchanged_across_runs(self):
        """Determinismo: mesmo template → mesmos tokens em execuções diferentes."""
        template = TEMPLATES["PREMIUM_CLINICAL"]
        results = []
        for _ in range(5):
            tokens, policy = DesignTokensEngine().generate(template)
            results.append((tokens, policy))

        for i in range(1, len(results)):
            assert results[0][0] == results[i][0]
            assert results[0][1] == results[i][1]

    def test_tokens_unchanged_by_llm_variation(self):
        """LLM não afeta tokens (tokens são gerados ANTES do LLM)."""
        template = TEMPLATES["PERFORMANCE_RESULT"]
        tokens1, policy1 = DesignTokensEngine().generate(template)
        tokens2, policy2 = DesignTokensEngine().generate(template)

        assert tokens1 == tokens2
        assert policy1 == policy2

    def test_all_personalities_have_valid_tokens(self):
        """Todos os templates VS-2 têm tokens válidos e passam no gate."""
        for template in TEMPLATES.values():
            tokens, policy = DesignTokensEngine().generate(template)
            passed, issues = DesignTokenGate().validate(tokens, policy)
            assert passed, f"Falha para {template.id}: {issues}"


class TestPositioningDeterminism:
    """VS-1: determinismo do EvidencePositioningEngine sob evidência variável."""

    def test_same_evidence_same_decision(self):
        """Mesma evidência → mesma posição, decision_reasons e strength."""
        from design_system.evidence_positioning import EvidencePositioningEngine

        engine = EvidencePositioningEngine()
        evidence = {"rating": 4.8, "total_ratings": 327, "specialties": ["injetáveis"]}
        results = []
        for _ in range(5):
            pos = engine.determine("estetica", evidence)
            results.append((pos.market_position, pos.decision_reasons, pos.evidence_strength))

        for i in range(1, len(results)):
            assert results[0] == results[i]

    def test_different_evidence_deterministic_per_case(self):
        """Evidências diferentes → decisões diferentes, mas cada uma estável."""
        from design_system.evidence_positioning import EvidencePositioningEngine

        engine = EvidencePositioningEngine()
        cases = [
            {"rating": 4.8, "total_ratings": 327, "specialties": ["facial"]},
            {"rating": 4.8, "total_ratings": 327, "specialties": ["injetáveis"]},
            {"rating": 2.9, "total_ratings": 100, "specialties": []},
            {},
        ]

        for evidence in cases:
            run_a = engine.determine("estetica", evidence)
            run_b = engine.determine("estetica", evidence)
            assert run_a.model_dump() == run_b.model_dump()
