"""
Fase 17.1 — Testes de integridade de evidências.

Cobrem duas camadas:
1. O prompt gerado por generate_proposal_with_fallback contém as instruções
   EVIDENCE_INTEGRITY (garantia de que o LLM recebe a regra).
2. EvidenceIntegrityValidator detecta corretamente as distorções descritas
   no relatório da Fase 17 (avaliações viradas em alunos, horário fixo
   virado em "flexível", números arredondados/generalizados).
"""
import json
import os
from unittest.mock import patch

from llm_provider import EVIDENCE_INTEGRITY, generate_proposal_with_fallback
from models import CommercialEvidence
from validate_evidence_integrity import (
    EvidenceIntegrityValidator,
    validate_copy_against_evidence,
)


VALID_LLM_JSON = json.dumps({
    "copywriting": {
        "headline": "A Melhor Academia de Goiânia",
        "subheadline": "Avaliação 4.1/5 no Google, com 1.209 avaliações",
        "cta_whatsapp": "Chamar no Whats",
        "pain_points": ["Falta de tempo para treinar", "Medo de se machucar"],
        "proofs": ["Avaliação 4.1/5 no Google, com 1.209 avaliações"],
    },
    "assets": {
        "suggested_images_keywords": ["academia", "treino", "goiania"],
        "color_palette_hint": "Tons de azul e cinza",
        "primary_color": "#111827",
    },
    "seo": {
        "title": "Academia Teste - Goiânia",
        "description": "A melhor academia de Goiânia com avaliação 4.1/5 no Google.",
    },
})


class TestEvidenceIntegrityPrompt:
    """Garante que a instrução de integridade chega até o LLM."""

    def test_evidence_integrity_constant_has_key_rules(self):
        """A constante deve conter as regras essenciais anti-distorção."""
        assert "NUNCA mude a ENTIDADE" in EVIDENCE_INTEGRITY
        assert "NUNCA infira FATOS NÃO DECLARADOS" in EVIDENCE_INTEGRITY
        assert "1209" in EVIDENCE_INTEGRITY or "1.209" in EVIDENCE_INTEGRITY
        assert "alunos" in EVIDENCE_INTEGRITY

    @patch.dict(os.environ, {"PRIMARY_LLM": "ollama"})
    @patch('llm_provider.call_ollama')
    def test_prompt_sent_to_llm_contains_evidence_integrity(self, mock_ollama):
        """O prompt efetivamente montado e enviado ao LLM deve conter as
        regras de integridade de evidência quando há evidências disponíveis.

        PRIMARY_LLM é fixado explicitamente porque outros módulos (ex:
        api/test_e2e_real.py) chamam load_dotenv() na coleção do pytest,
        o que pode sobrescrever a env var globalmente na sessão de testes.
        """
        mock_ollama.return_value = VALID_LLM_JSON

        trusted_business = {
            "name": "Academia Teste",
            "niche": "academia",
            "city": "Goiânia",
            "place_id": "ChIJ_teste_evidence_integrity",
            "phone": "62999999999",
            "evidence": {
                "credentials": ["Avaliação 4.1/5 no Google (1209 avaliações)"],
            },
        }

        result = generate_proposal_with_fallback(trusted_business)

        assert result is not None
        sent_prompt = mock_ollama.call_args[0][0]
        assert "INTEGRIDADE DA EVIDÊNCIA" in sent_prompt
        assert "NUNCA mude a ENTIDADE" in sent_prompt
        assert "1209 avaliações" in sent_prompt  # evidência original presente


class TestEvidenceIntegrityValidator:
    """Testes de regressão para o EvidenceIntegrityValidator."""

    def test_review_count_not_converted_to_students(self):
        """'1209 avaliações' preservado corretamente não gera violação."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        copy = "Avaliação 4.1/5 no Google, com 1.209 avaliações de clientes reais."

        result = validate_copy_against_evidence(evidence, copy)
        assert result["has_violations"] is False

    def test_review_count_converted_to_students_is_flagged(self):
        """'1209 avaliações' virando '1209 alunos' DEVE ser detectado."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        copy = "Mais de 1.209 alunos satisfeitos confiam em nós."

        result = validate_copy_against_evidence(evidence, copy)
        assert result["has_violations"] is True
        assert any("alunos" in v for v in result["violations"])

    def test_review_count_rounded_and_generalized_is_flagged(self):
        """'1209' virando 'mais de 1200' (perda de precisão) DEVE ser detectado."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        copy = "Mais de 1.200 alunos satisfeitos já treinaram aqui."

        result = validate_copy_against_evidence(evidence, copy)
        assert result["has_violations"] is True

    def test_rating_unused_in_copy_is_not_flagged(self):
        """Se a copy simplesmente não usar o rating (sem distorcê-lo), não é
        violação — a evidência pode legitimamente não ter sido citada
        (Fase 17.1A: só distorção é violação, omissão não)."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        copy = "Uma academia excelente e muito bem avaliada por todos."

        result = validate_copy_against_evidence(evidence, copy)
        assert result["has_violations"] is False

    def test_opening_hours_not_converted_to_flexible(self):
        """Horário fixo preservado corretamente não gera violação."""
        evidence = CommercialEvidence(opening_hours="Seg-Sex 08:00-18:00")
        copy = "Atendimento de Segunda a Sexta, das 08:00 às 18:00."

        result = validate_copy_against_evidence(evidence, copy)
        assert result["has_violations"] is False

    def test_opening_hours_converted_to_flexible_is_flagged(self):
        """Horário fixo virando 'horário flexível' sem evidência DEVE ser detectado."""
        evidence = CommercialEvidence(opening_hours="Seg-Sex 08:00-18:00")
        copy = "Conte com horário flexível para treinar quando quiser."

        result = validate_copy_against_evidence(evidence, copy)
        assert result["has_violations"] is True
        assert any("flexível" in v for v in result["violations"])

    def test_no_evidence_no_violations_possible(self):
        """Sem evidências configuradas, o validador não levanta falsas violações."""
        evidence = CommercialEvidence()
        copy = "Qualquer copy genérica, sem números nem horários específicos."

        result = validate_copy_against_evidence(evidence, copy)
        assert result["has_violations"] is False
        assert result["violations"] == []

    def test_validator_instance_reset_between_calls(self):
        """Chamadas sucessivas de validate() não acumulam violações antigas.

        validate() retorna um EvidenceIntegrityResult estruturado (Fase
        17.1A) — não mais o dict legado, que segue disponível via
        validate_copy_against_evidence()."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        validator = EvidenceIntegrityValidator(evidence)

        first = validator.validate("Mais de 1.209 alunos satisfeitos.")
        assert first.passed is False

        second = validator.validate("Avaliação 4.1/5 no Google, com 1.209 avaliações.")
        assert second.passed is True
