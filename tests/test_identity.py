"""
Contrato de identidade do lead (Fase 14.2).

NOTA de implementação: a especificação original pedia uma propriedade
`BusinessData.identity` com reescrita do modelo (incluindo phone/slug).
Implementei o mesmo contrato de prioridade (place_id > lead_id > sintético)
em main.py::resolve_place_id() em vez disso — ver justificativa no relatório
da Fase 14.2. BusinessData continua com sua validação de telefone (DDD 55,
código de país) e geração de slug intactas, já cobertas por tests/test_models.py.
"""
import pytest
from main import resolve_place_id, synthetic_place_id
from models import BusinessData


class TestResolvePlaceId:
    def test_place_id_has_top_priority(self):
        """place_id real sempre vence, mesmo com lead_id também presente."""
        result = resolve_place_id(
            place_id="ChIJWzV_real_google_id",
            lead_id="lead_123",
            name="Estrela", niche="padaria", city="Goiânia"
        )
        assert result == "ChIJWzV_real_google_id"

    def test_lead_id_used_when_no_place_id(self):
        result = resolve_place_id(
            place_id=None,
            lead_id="lead_123",
            name="Estrela", niche="padaria", city="Goiânia"
        )
        assert result == "lead-lead-123"

    def test_synthetic_fallback_when_neither_available(self):
        result = resolve_place_id(
            place_id=None,
            lead_id=None,
            name="Estrela", niche="padaria", city="Goiânia"
        )
        assert result == synthetic_place_id("Estrela", "padaria", "Goiânia")

    def test_lead_id_is_stronger_guarantee_than_synthetic(self):
        """
        Dois leads com nome+nicho+cidade IDÊNTICOS (o caso que o hash
        sintético sozinho não resolve) ainda ficam com identidades
        diferentes se cada um tiver um lead_id interno distinto.
        """
        id1 = resolve_place_id(None, "lead_A", "Estrela", "padaria", "Goiânia")
        id2 = resolve_place_id(None, "lead_B", "Estrela", "padaria", "Goiânia")
        assert id1 != id2

    def test_result_is_dns_safe(self):
        """place_id resolvido vira sufixo de slug — não pode ter underscore
        sobrevivendo (dns_safe_suffix faz hash, mas o valor bruto também não
        deve introduzir caracteres inesperados na origem)."""
        result = resolve_place_id(None, "lead_123", "Estrela", "padaria", "Goiânia")
        assert '_' not in result


class TestSlugUniquenessWithLeadId:
    def test_same_name_niche_city_different_lead_id_yields_different_slug(self):
        """
        Cenário mais estrito que o da Fase 14.1: mesmo nome, MESMO nicho,
        MESMA cidade (o hash sintético sozinho colidiria aqui) — só o lead_id
        evita a colisão.
        """
        pid1 = resolve_place_id(None, "lead_A", "Estrela", "padaria", "Goiânia")
        pid2 = resolve_place_id(None, "lead_B", "Estrela", "padaria", "Goiânia")

        business1 = BusinessData(
            name="Estrela", niche="padaria", city="Goiânia",
            place_id=pid1, phone="62999999999"
        )
        business2 = BusinessData(
            name="Estrela", niche="padaria", city="Goiânia",
            place_id=pid2, phone="62999999999"
        )
        assert business1.slug != business2.slug

    def test_same_lead_id_reused_yields_same_slug(self):
        """Idempotência: reprocessar o mesmo lead (mesmo lead_id) deve
        produzir o mesmo slug — regeneração da própria landing, não colisão."""
        pid1 = resolve_place_id(None, "lead_123", "Estrela", "padaria", "Goiânia")
        pid2 = resolve_place_id(None, "lead_123", "Estrela", "padaria", "Goiânia")
        assert pid1 == pid2

        business1 = BusinessData(
            name="Estrela", niche="padaria", city="Goiânia",
            place_id=pid1, phone="62999999999"
        )
        business2 = BusinessData(
            name="Estrela", niche="padaria", city="Goiânia",
            place_id=pid2, phone="62999999999"
        )
        assert business1.slug == business2.slug
