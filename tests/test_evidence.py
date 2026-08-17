import pytest
from pydantic import ValidationError
from models import CommercialEvidence, EvidenceSource, BusinessData


class TestCommercialEvidence:
    def test_evidence_summary_empty(self):
        evidence = CommercialEvidence()
        assert evidence.evidence_summary == "Nenhuma evidência comercial disponível."
        assert not evidence.has_evidence

    def test_evidence_summary_with_data(self):
        evidence = CommercialEvidence(
            opening_hours="Seg-Sex 08:00-18:00",
            services=["Diagnóstico", "Troca de óleo"],
            differentiators=["Atendimento rápido"],
            credentials=["10 anos de experiência"]
        )
        assert "Horário de funcionamento" in evidence.evidence_summary
        assert "Serviços oferecidos" in evidence.evidence_summary
        assert "Diferenciais" in evidence.evidence_summary
        assert "Credenciais" in evidence.evidence_summary
        assert evidence.has_evidence

    def test_evidence_summary_only_includes_populated_fields(self):
        """Campos vazios não devem aparecer no resumo (evita instruir o LLM
        com listas vazias tipo 'Ofertas: ')."""
        evidence = CommercialEvidence(opening_hours="08:00-18:00")
        summary = evidence.evidence_summary
        assert "Horário de funcionamento" in summary
        assert "Ofertas" not in summary
        assert "Serviços oferecidos" not in summary

    def test_evidence_with_sources(self):
        evidence = CommercialEvidence(
            opening_hours="08:00-18:00",
            sources={
                "opening_hours": EvidenceSource(type="google_places", confidence=0.9, verified=True)
            }
        )
        assert evidence.sources["opening_hours"].type == "google_places"
        assert evidence.sources["opening_hours"].confidence == 0.9

    def test_evidence_source_confidence_bounds(self):
        with pytest.raises(ValidationError):
            EvidenceSource(type="lead_input", confidence=1.5)  # > 1, inválido
        with pytest.raises(ValidationError):
            EvidenceSource(type="lead_input", confidence=-0.1)  # < 0, inválido

    def test_business_data_with_evidence(self):
        evidence = CommercialEvidence(opening_hours="08:00-18:00")
        business = BusinessData(
            name="Teste",
            niche="padaria",
            city="Goiânia",
            place_id="ChIJ_teste_evidence",
            phone="62999999999",
            evidence=evidence
        )
        assert business.evidence.opening_hours == "08:00-18:00"

    def test_business_data_default_evidence_is_empty(self):
        """BusinessData sem evidence explícita deve continuar funcionando
        (backward compatible com todo o código que já existia antes da Fase 16)."""
        business = BusinessData(
            name="Teste",
            niche="padaria",
            city="Goiânia",
            place_id="ChIJ_teste_no_evidence",
            phone="62999999999",
        )
        assert business.evidence.has_evidence is False
        assert business.evidence.evidence_summary == "Nenhuma evidência comercial disponível."
