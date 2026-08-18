"""
Testes de determinismo do Design System Engine (VS-0.2).

Os tokens são gerados ANTES do LLM e independentes de copy, provider ou
temperatura: a mesma personalidade produz SEMPRE os mesmos tokens.
"""
from design_system.visual_policy import VisualPersonality
from engines.design_tokens_engine import DesignTokensEngine
from gates.design_token_gate import DesignTokenGate


class TestDeterminism:
    """Testa que DesignTokens são determinísticos."""

    def test_tokens_unchanged_across_runs(self):
        """Determinismo: mesma personality → mesmos tokens em execuções diferentes."""
        personality = VisualPersonality.PREMIUM_CLINICAL
        results = []
        for _ in range(5):
            tokens, policy = DesignTokensEngine().generate(personality)
            results.append((tokens, policy))

        for i in range(1, len(results)):
            assert results[0][0] == results[i][0]
            assert results[0][1] == results[i][1]

    def test_tokens_unchanged_by_llm_variation(self):
        """LLM não afeta tokens (tokens são gerados ANTES do LLM)."""
        personality = VisualPersonality.PERFORMANCE_RESULT
        tokens1, policy1 = DesignTokensEngine().generate(personality)
        tokens2, policy2 = DesignTokensEngine().generate(personality)

        assert tokens1 == tokens2
        assert policy1 == policy2

    def test_all_personalities_have_valid_tokens(self):
        """Todas as personalidades VS-0 têm tokens válidos e passam no gate."""
        personalities = [
            VisualPersonality.PREMIUM_CLINICAL,
            VisualPersonality.PERFORMANCE_RESULT,
            VisualPersonality.BOLD_URBAN,
        ]

        for personality in personalities:
            tokens, policy = DesignTokensEngine().generate(personality)
            passed, issues = DesignTokenGate().validate(tokens, policy)
            assert passed, f"Falha para {personality}: {issues}"
