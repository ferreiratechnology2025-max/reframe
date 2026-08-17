"""
Fase 17.1A — Testes do contrato estruturado de integridade de evidências e
do gate obrigatório de publicação.
"""
import pytest

from validate_evidence_integrity import EvidenceIntegrityValidator, IntegrityViolationCode
from models import CommercialEvidence
from api.errors import ErrorCode, is_retryable_error, get_user_message, extract_error_code


class TestEvidenceIntegrityGate:
    def test_validator_passes_without_evidence(self):
        """Sem evidência → passa automaticamente."""
        evidence = CommercialEvidence()
        validator = EvidenceIntegrityValidator(evidence)
        result = validator.validate("Qualquer copy")
        assert result.passed
        assert len(result.violations) == 0

    def test_validator_blocks_entity_substitution(self):
        """Avaliação → alunos → BLOQUEIA."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        validator = EvidenceIntegrityValidator(evidence)
        result = validator.validate("Mais de 1.200 alunos satisfeitos")
        assert not result.passed
        assert any(v.code == IntegrityViolationCode.ENTITY_SUBSTITUTION for v in result.violations)
        # Substituição de entidade é sempre crítica → deve estar em critical_violations.
        assert any(v.code == IntegrityViolationCode.ENTITY_SUBSTITUTION for v in result.critical_violations)

    def test_validator_blocks_numeric_mismatch(self):
        """Arredondamento indevido → BLOQUEIA."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        validator = EvidenceIntegrityValidator(evidence)
        result = validator.validate("Mais de 1200 avaliações")
        assert not result.passed
        assert any(v.code == IntegrityViolationCode.NUMERIC_MISMATCH for v in result.violations)

    def test_validator_allows_correct_usage(self):
        """Uso correto da evidência → PASSA."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        validator = EvidenceIntegrityValidator(evidence)
        result = validator.validate("Avaliação 4.1/5 no Google, com 1.209 avaliações")
        assert result.passed
        assert len(result.violations) == 0

    def test_validator_blocks_unsupported_inference(self):
        """Horário fixo → 'flexível' → BLOQUEIA."""
        evidence = CommercialEvidence(
            opening_hours="Monday: 08:00-18:00, Tuesday: 08:00-18:00"
        )
        validator = EvidenceIntegrityValidator(evidence)
        result = validator.validate("Horário flexível para atendimento")
        assert not result.passed
        assert any(v.code == IntegrityViolationCode.TIME_INTERPRETATION for v in result.violations)

    def test_result_to_dict_structure(self):
        """to_dict() expõe o contrato estruturado (código, severidade, evidência, snippet)."""
        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        result = EvidenceIntegrityValidator(evidence).validate("Mais de 1.200 alunos satisfeitos")
        d = result.to_dict()

        assert d["passed"] is False
        assert len(d["violations"]) >= 1
        v = d["violations"][0]
        assert set(["code", "message", "evidence", "copy_snippet", "severity"]).issubset(v.keys())
        assert v["code"] == IntegrityViolationCode.ENTITY_SUBSTITUTION.value


class TestEvidenceIntegrityErrorCodes:
    """Contrato de erro (api/errors.py) para violações de integridade."""

    def test_evidence_error_codes_exist(self):
        assert ErrorCode.EVIDENCE_INTEGRITY_FAIL == "EVIDENCE_INTEGRITY_FAIL"
        assert ErrorCode.EVIDENCE_NUMERIC_MISMATCH == "EVIDENCE_NUMERIC_MISMATCH"
        assert ErrorCode.EVIDENCE_ENTITY_SUBSTITUTION == "EVIDENCE_ENTITY_SUBSTITUTION"
        assert ErrorCode.EVIDENCE_UNSUPPORTED_INFERENCE == "EVIDENCE_UNSUPPORTED_INFERENCE"
        assert ErrorCode.EVIDENCE_TIME_INTERPRETATION == "EVIDENCE_TIME_INTERPRETATION"

    def test_evidence_error_codes_are_not_retryable(self):
        """Violação de integridade é um problema de conteúdo — retry não resolve."""
        assert is_retryable_error(ErrorCode.EVIDENCE_INTEGRITY_FAIL) is False
        assert is_retryable_error(ErrorCode.EVIDENCE_NUMERIC_MISMATCH) is False
        assert is_retryable_error(ErrorCode.EVIDENCE_ENTITY_SUBSTITUTION) is False
        assert is_retryable_error(ErrorCode.EVIDENCE_UNSUPPORTED_INFERENCE) is False
        assert is_retryable_error(ErrorCode.EVIDENCE_TIME_INTERPRETATION) is False

    def test_evidence_error_codes_have_user_messages(self):
        msg = get_user_message(ErrorCode.EVIDENCE_INTEGRITY_FAIL)
        assert msg and msg != "Erro desconhecido. Tente novamente mais tarde."

    def test_extract_error_code_recognizes_evidence_integrity_fail(self):
        """O gate levanta ValueError com prefixo 'EVIDENCE_INTEGRITY_FAIL: ...' —
        a mesma convenção usada por INVALID_LEAD/ARCHETYPE_NOT_SUPPORTED — e o
        classificador genérico de erro do pipeline_adapter já reconhece isso
        sem heurística adicional."""
        code = extract_error_code("EVIDENCE_INTEGRITY_FAIL: 1 violação(ões) crítica(s) encontrada(s)")
        assert code == "EVIDENCE_INTEGRITY_FAIL"


class TestEvidenceIntegrityPipelineGate:
    """Integração com main.py::_evidence_integrity_gate — bloqueia a
    publicação antes do R2 quando há violação crítica."""

    def test_gate_raises_structured_error_on_critical_violation(self):
        from main import _evidence_integrity_gate
        from models import BusinessData, CopyData, AssetsData, SeoData, ProposalTemplateData

        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        business = BusinessData(
            name="Academia Teste",
            niche="academia",
            city="Goiânia",
            place_id="ChIJ_teste_gate",
            phone="62999999999",
            evidence=evidence,
        )
        proposal = ProposalTemplateData(
            business=business,
            copywriting=CopyData(
                headline="A Melhor Academia",
                subheadline="Confie em quem já ajudou muita gente",
                cta_whatsapp="Chamar no Whats",
                pain_points=["Falta de tempo", "Medo de se machucar"],
                proofs=["Mais de 1.200 alunos satisfeitos"],
            ),
            assets=AssetsData(
                suggested_images_keywords=["academia", "treino"],
                color_palette_hint="Azul",
            ),
            seo=SeoData(
                title="Academia Teste",
                description="A melhor academia de Goiânia para você treinar com segurança.",
            ),
        )

        with pytest.raises(ValueError, match="EVIDENCE_INTEGRITY_FAIL"):
            _evidence_integrity_gate(proposal)

    def test_gate_passes_on_correct_usage(self):
        from main import _evidence_integrity_gate
        from models import BusinessData, CopyData, AssetsData, SeoData, ProposalTemplateData

        evidence = CommercialEvidence(
            credentials=["Avaliação 4.1/5 no Google (1209 avaliações)"]
        )
        business = BusinessData(
            name="Academia Teste",
            niche="academia",
            city="Goiânia",
            place_id="ChIJ_teste_gate_ok",
            phone="62999999999",
            evidence=evidence,
        )
        proposal = ProposalTemplateData(
            business=business,
            copywriting=CopyData(
                headline="A Melhor Academia",
                subheadline="Avaliação 4.1/5 no Google, com 1.209 avaliações",
                cta_whatsapp="Chamar no Whats",
                pain_points=["Falta de tempo", "Medo de se machucar"],
                proofs=["Avaliação 4.1/5 no Google, com 1.209 avaliações"],
            ),
            assets=AssetsData(
                suggested_images_keywords=["academia", "treino"],
                color_palette_hint="Azul",
            ),
            seo=SeoData(
                title="Academia Teste",
                description="A melhor academia de Goiânia para você treinar com segurança.",
            ),
        )

        _evidence_integrity_gate(proposal)  # não deve levantar
