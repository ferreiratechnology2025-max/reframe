import pytest
from pydantic import ValidationError
from models import BusinessData, ProposalTemplateData, CopyData, AssetsData, SeoData, LLMOutput, normalize_llm_output


def test_slug_dns_safe():
    """Slug não pode conter underscore nem caracteres não-DNS."""
    b = BusinessData(
        name="Padaria Central",
        niche="padaria",
        city="Goiânia",
        place_id="ChIJ_N1t_123",
        phone="62999999999"
    )
    assert '_' not in b.slug
    assert b.slug.startswith("padaria-central-")
    assert len(b.slug.split('-')[-1]) == 6  # sufixo do place_id


def test_phone_normalization_ddd_55():
    """DDD 55 (Santa Maria/RS) não deve ser confundido com código de país."""
    # Telefone sem código de país, DDD 55
    b = BusinessData(
        name="Empresa RS",
        niche="teste",
        city="Santa Maria",
        place_id="ChIJ_teste_55",
        phone="55991234567"  # DDD 55 + número
    )
    assert b.phone == "5555991234567"  # 55 (país) + 55 (DDD) + número


def test_phone_normalization_with_country_code():
    """Telefone já com código de país deve ser aceito."""
    b = BusinessData(
        name="Empresa SP",
        niche="teste",
        city="São Paulo",
        place_id="ChIJ_teste_sp",
        phone="+5511999999999"
    )
    assert b.phone == "5511999999999"


def test_phone_empty_raises_error():
    """Telefone vazio deve levantar ValueError."""
    with pytest.raises(ValidationError) as exc_info:
        BusinessData(
            name="Empresa",
            niche="teste",
            city="Cidade",
            place_id="ChIJ_teste_empty",
            phone=""
        )
    assert "Telefone é obrigatório" in str(exc_info.value)


def test_whatsapp_link_generation():
    """Link do WhatsApp deve conter ?text= com CTA."""
    data = ProposalTemplateData(
        business=BusinessData(
            name="Teste",
            niche="teste",
            city="Cidade",
            place_id="ChIJ_teste_wa",
            phone="62999999999"
        ),
        copywriting=CopyData(
            headline="Headline Teste",
            subheadline="Subheadline Teste",
            cta_whatsapp="Quero saber mais",
            pain_points=["Dor 1"],
            proofs=["Prova 1"]
        ),
        assets=AssetsData(
            suggested_images_keywords=["teste"],
            color_palette_hint="blue"
        ),
        seo=SeoData(
            title="Teste SEO",
            description="Descrição de teste para SEO"
        )
    )
    assert "wa.me/5562999999999" in data.whatsapp_link
    assert "?text=" in data.whatsapp_link
    assert "Quero%20saber%20mais" in data.whatsapp_link


def test_slug_validation_not_assert():
    """Validação de slug deve usar ValueError, não assert (sobrevive a -O)."""
    # Força um slug inválido manualmente
    b = BusinessData(
        name="Teste",
        niche="teste",
        city="Cidade",
        place_id="ChIJ_teste_slug",
        phone="62999999999",
        slug="slug_invalido_com_underscore"
    )
    # O validator deve levantar ValueError, não AssertionError
    with pytest.raises(ValidationError) as exc_info:
        b.model_validate(b.model_dump())
    assert "DNS-safe" in str(exc_info.value)


def _valid_llm_payload(**overrides) -> dict:
    """Payload mínimo válido de LLMOutput, para testes de normalização."""
    payload = {
        "copywriting": {
            "headline": "Headline Teste",
            "subheadline": "Subheadline Teste",
            "cta_whatsapp": "Quero saber mais",
            "pain_points": ["Dor 1"],
            "proofs": ["Prova 1"],
        },
        "assets": {
            "suggested_images_keywords": ["a", "b", "c"],
            "color_palette_hint": "azul e branco",
        },
        "seo": {
            "title": "Título SEO",
            "description": "Descrição de teste para SEO com tamanho razoável",
        },
    }
    for section, fields in overrides.items():
        payload[section].update(fields)
    return payload


def test_normalize_truncates_excess_keywords():
    """LLM devolvendo mais de 3 keywords deve ser truncado para 3, não rejeitado."""
    raw = _valid_llm_payload(assets={"suggested_images_keywords": ["a", "b", "c", "d", "e"]})
    normalized = normalize_llm_output(raw)
    assert normalized["assets"]["suggested_images_keywords"] == ["a", "b", "c"]
    # Deve validar sem erro após normalização
    LLMOutput.model_validate(normalized)


def test_normalize_truncates_long_seo_title():
    """seo.title acima do limite deve ser truncado, não rejeitado."""
    raw = _valid_llm_payload(seo={"title": "T" * 100})
    normalized = normalize_llm_output(raw)
    assert len(normalized["seo"]["title"]) <= 70
    LLMOutput.model_validate(normalized)


def test_normalize_truncates_long_subheadline():
    """copywriting.subheadline acima do limite deve ser truncado, não rejeitado."""
    raw = _valid_llm_payload(copywriting={"subheadline": "S" * 200})
    normalized = normalize_llm_output(raw)
    assert len(normalized["copywriting"]["subheadline"]) <= 140
    LLMOutput.model_validate(normalized)


def test_normalize_leaves_valid_payload_unchanged():
    """Payload já dentro dos limites não deve ser alterado."""
    raw = _valid_llm_payload()
    normalized = normalize_llm_output(raw)
    assert normalized == raw
