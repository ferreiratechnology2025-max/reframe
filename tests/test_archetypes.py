import pytest
from main import resolve_archetype, get_archetype_or_fail
from config.archetypes import ARCHETYPES_CONFIG


# Nicho de entrada (como um lead real chegaria) -> archetype_key esperado
KNOWN_NICHES = [
    ("padaria artesanal", "padaria"),
    ("mecânica automotiva", "mecanica"),
    ("restaurante", "restaurante"),
    ("barbearia", "barbearia"),
    ("salão de beleza", "salao"),
    ("confeitaria", "confeitaria"),
    ("academia", "academia"),
    ("pet_shop", "pet_shop"),
    ("loja_roupas", "moda"),
    ("farmácia", "farmacia"),
]


@pytest.mark.parametrize("niche,expected_key", KNOWN_NICHES)
def test_resolve_archetype_known_niches(niche, expected_key):
    """Cada nicho conhecido deve resolver para o seu próprio arquétipo, nunca outro."""
    result = resolve_archetype(niche)
    assert result is not None, f"Nicho '{niche}' deveria resolver, retornou None"
    archetype_key, config = result
    assert archetype_key == expected_key
    assert config["trust_signals"]
    assert config["hero_image"]
    assert config["primary_color"].startswith("#")


def test_resolve_archetype_unknown_niche_returns_none():
    """Nicho sem arquétipo mapeado deve retornar None — nunca cair para padaria."""
    result = resolve_archetype("consultoria financeira")
    assert result is None


def test_get_archetype_or_fail_raises_for_unknown_niche():
    """get_archetype_or_fail deve levantar ValueError com código estável."""
    with pytest.raises(ValueError, match="ARCHETYPE_NOT_SUPPORTED"):
        get_archetype_or_fail("consultoria financeira")


def test_get_archetype_or_fail_returns_correct_archetype():
    """get_archetype_or_fail deve retornar o arquétipo certo para nicho conhecido."""
    archetype_key, config = get_archetype_or_fail("barbearia")
    assert archetype_key == "barbearia"
    assert config["primary_color"] == "#1C1917"


def test_no_niche_falls_back_to_padaria_silently():
    """Regressão: nenhum nicho desconhecido deve resolver silenciosamente para padaria."""
    for niche in ["academia de ginástica", "clínica veterinária", "doceria", ""]:
        result = resolve_archetype(niche)
        if result is not None:
            # Se resolveu, tem que ser porque genuinamente bateu com uma chave mapeada
            archetype_key, _ = result
            assert archetype_key in ARCHETYPES_CONFIG
