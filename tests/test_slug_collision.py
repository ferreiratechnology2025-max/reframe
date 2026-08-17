"""
Testes de integridade de publicação (Fase 14.1).

A causa raiz do bug real (3 leads chamados "Estrela" em nichos diferentes
publicando na mesma URL) era o fallback de place_id em main.py::generate_landing,
que usava só o nome do lead — resolvido em main.py::synthetic_place_id,
que inclui nicho e cidade.

O collision guard em publisher.py::R2Publisher.upload_html é uma camada de
proteção adicional (testada em tests/test_publisher.py), não a causa raiz.
"""
import pytest
from main import synthetic_place_id
from models import BusinessData


def test_synthetic_place_id_differs_by_niche():
    """Mesmo nome, nichos diferentes → place_id (e portanto slug) diferentes."""
    id1 = synthetic_place_id("Estrela", "padaria", "Goiânia")
    id2 = synthetic_place_id("Estrela", "salão", "Goiânia")
    id3 = synthetic_place_id("Estrela", "pet_shop", "Goiânia")
    assert len({id1, id2, id3}) == 3


def test_synthetic_place_id_differs_by_city():
    """Mesmo nome e nicho, cidades diferentes → place_id diferentes."""
    id1 = synthetic_place_id("Estrela", "padaria", "Goiânia")
    id2 = synthetic_place_id("Estrela", "padaria", "Anápolis")
    assert id1 != id2


def test_synthetic_place_id_deterministic():
    """O mesmo lead (mesmo nome+nicho+cidade) deve gerar o mesmo place_id
    entre execuções — é isso que torna a regeneração da mesma landing idempotente."""
    id1 = synthetic_place_id("Padaria Central", "padaria", "Goiânia")
    id2 = synthetic_place_id("Padaria Central", "padaria", "Goiânia")
    assert id1 == id2


def test_synthetic_place_id_is_dns_safe():
    """O place_id sintético não deve conter underscore (quebraria o slug DNS-safe)."""
    place_id = synthetic_place_id("Pet Shop Amigo", "pet_shop", "São Paulo")
    assert '_' not in place_id


def test_business_slug_differs_for_same_name_different_niche():
    """
    Teste de integração: dois leads com o mesmo nome, nichos diferentes,
    sem place_id real — usando o place_id sintético, os slugs finais
    (BusinessData.slug) devem ser diferentes. Isso é o que impede a
    colisão de URL/sobrescrita no R2 reportada na Fase 14.
    """
    business1 = BusinessData(
        name="Estrela",
        niche="padaria",
        city="Goiânia",
        place_id=synthetic_place_id("Estrela", "padaria", "Goiânia"),
        phone="62999999999",
    )
    business2 = BusinessData(
        name="Estrela",
        niche="salão",
        city="Goiânia",
        place_id=synthetic_place_id("Estrela", "salão", "Goiânia"),
        phone="62999999999",
    )
    business3 = BusinessData(
        name="Estrela",
        niche="pet_shop",
        city="Goiânia",
        place_id=synthetic_place_id("Estrela", "pet_shop", "Goiânia"),
        phone="62999999999",
    )
    slugs = {business1.slug, business2.slug, business3.slug}
    assert len(slugs) == 3, f"Slugs deveriam ser únicos, obtidos: {slugs}"
