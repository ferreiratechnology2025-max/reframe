"""
E2E do Vertical Slice VS-0/VS-2 — pipeline completo REAL.

Cadeia: Evidence → Positioning (determinístico) → Theme (position-only) →
Tokens → DesignTokenGate → LLM Copy → Evidence Integrity Gate → Render →
RenderedVisualGate (Playwright) → Publish (R2 de verdade).

VS-2: a seleção visual é por POSIÇÃO (POSITION_TEMPLATE_MAP), independente
de nicho. O mesmo template serve qualquer nicho na mesma posição.
E2E: 5 publicados + 1 bloqueio (UNDETERMINED).

É um teste de integração ponta-a-ponta: usa credenciais reais do .env
(LLM + R2). Pula com aviso se as credenciais não existirem.
"""
import asyncio
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from pipeline import DemoInput, generate_demo  # noqa: E402


def _env_ready() -> bool:
    llm = bool(os.getenv("AGNES_API_KEY") or os.getenv("GEMINI_API_KEY"))
    r2 = all([
        os.getenv("R2_ACCESS_KEY") or os.getenv("CLOUDFLARE_ACCESS_KEY"),
        os.getenv("R2_SECRET_KEY") or os.getenv("CLOUDFLARE_SECRET_KEY"),
        os.getenv("R2_ENDPOINT") or os.getenv("CLOUDFLARE_ENDPOINT"),
        os.getenv("CLOUDFLARE_ACCOUNT_ID") or os.getenv("R2_ACCOUNT_ID"),
    ])
    return llm and r2


def _demo_input() -> DemoInput:
    return DemoInput(
        business_name="Clínica Dra. Andrielle Fernandes",
        niche="estetica",
        city="Goiânia",
        whatsapp="+5562999999999",
        place_id="ChIJN1t_tDeuEmsRUsoyN83rY4Q",
        evidence={
            "rating": 4.8,
            "total_ratings": 327,
            "specialties": ["facial", "injetáveis"],
        },
        location={
            "address_line": "Av. T-63, 1299 — Setor Bueno",
            "neighborhood": "Setor Bueno",
            "city": "Goiânia",
            "state": "GO",
            "latitude": -16.6869,
            "longitude": -49.2648,
            "google_maps_url": (
                "https://www.google.com/maps/search/?api=1&query=-16.6869,-49.2648"
            ),
            "source": "google_places",
            "source_ref": "ChIJN1t_tDeuEmsRUsoyN83rY4Q",
            "status": "verified",
            "confidence": 0.95,
        },
    )


def _estetica_demo(specialties, name="Clínica Dra. Andrielle Fernandes",
                   place_id="ChIJN1t_tDeuEmsRUsoyN83rY4Q") -> DemoInput:
    return DemoInput(
        business_name=name,
        niche="estetica",
        city="Goiânia",
        whatsapp="+5562999999999",
        place_id=place_id,
        evidence={"rating": 4.8, "total_ratings": 327, "specialties": specialties},
        location={
            "address_line": "Av. T-63, 1299 — Setor Bueno",
            "neighborhood": "Setor Bueno",
            "city": "Goiânia",
            "state": "GO",
            "latitude": -16.6869,
            "longitude": -49.2648,
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=-16.6869,-49.2648",
            "source": "google_places",
            "source_ref": place_id,
            "status": "verified",
            "confidence": 0.95,
        },
    )


def _academia_demo(specialties, name="Academia Performance Prime",
                   place_id="demo-academia") -> DemoInput:
    return DemoInput(
        business_name=name,
        niche="academia",
        city="Goiânia",
        whatsapp="+5562999999999",
        place_id=place_id,
        evidence={"rating": 4.7, "total_ratings": 512, "specialties": specialties},
        location={
            "address_line": "Av. Anhanguera, 450 — Centro",
            "neighborhood": "Centro",
            "city": "Goiânia",
            "state": "GO",
            "latitude": -16.6864,
            "longitude": -49.2643,
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=-16.6864,-49.2643",
            "source": "google_places",
            "source_ref": place_id,
            "status": "verified",
            "confidence": 0.9,
        },
    )


def _barbearia_demo(specialties, name="Barbearia Central",
                    place_id="demo-barbearia") -> DemoInput:
    return DemoInput(
        business_name=name,
        niche="barbearia",
        city="Goiânia",
        whatsapp="+5562999999999",
        place_id=place_id,
        evidence={"rating": 4.9, "total_ratings": 891, "specialties": specialties},
        location={
            "address_line": "Rua 3, 120 — Setor Central",
            "neighborhood": "Setor Central",
            "city": "Goiânia",
            "state": "GO",
            "latitude": -16.6799,
            "longitude": -49.2550,
            "google_maps_url": "https://www.google.com/maps/search/?api=1&query=-16.6799,-49.2550",
            "source": "google_places",
            "source_ref": place_id,
            "status": "verified",
            "confidence": 0.9,
        },
    )


NICHES_EXPECTED = [
    (
        "estetica_premium",
        _estetica_demo(["facial", "injetáveis"]),
        {
            "template_id": "PREMIUM_CLINICAL",
            "position": "PREMIUM",
            "primary_color": "#C6A87C",
            "bg": "#F5F3F0",
            "accent": "#C6A87C",
            "archetype": "prestigio_clinico",
        },
    ),
    (
        "estetica_natural",
        _estetica_demo(["facial"], place_id="demo-estetica-natural"),
        {
            "template_id": "NATURAL_ELEGANT",
            "position": "NATURAL",
            "primary_color": "#7A8B6F",
            "bg": "#F7F5F0",
            "accent": "#7A8B6F",
            "archetype": "beleza_natural",
        },
    ),
    (
        "academia_performance",
        _academia_demo(["musculação", "funcional"]),
        {
            "template_id": "PERFORMANCE_RESULT",
            "position": "PERFORMANCE",
            "primary_color": "#E63946",
            "bg": "#FFFFFF",
            "accent": "#E63946",
            "archetype": "forca_disciplina",
        },
    ),
    (
        "academia_natural",
        _academia_demo(["pilates"], place_id="demo-academia-natural"),
        {
            "template_id": "NATURAL_ELEGANT",
            "position": "NATURAL",
            "primary_color": "#7A8B6F",
            "bg": "#F7F5F0",
            "accent": "#7A8B6F",
            "archetype": "beleza_natural",
        },
    ),
    (
        "barbearia_luxury",
        _barbearia_demo(["barba"]),
        {
            "template_id": "LUXURY_MINIMAL",
            "position": "LUXURY",
            "primary_color": "#C9A96A",
            "bg": "#111111",
            "accent": "#C9A96A",
            "archetype": "luxo_sobrio",
        },
    ),
]


@pytest.mark.parametrize(
    "niche,demo,expected",
    NICHES_EXPECTED,
    ids=[n for n, _, _ in NICHES_EXPECTED],
)
@pytest.mark.asyncio
async def test_vs0_e2e_published(niche, demo, expected):
    if not _env_ready():
        pytest.skip("Credenciais LLM/R2 ausentes — E2E real pulado")

    result = await generate_demo(demo)

    assert result["status"] == "published", f"[{niche}] Falhou: {result}"
    assert result["personality"] == expected["template_id"], result
    assert result["position"] == expected["position"], result
    assert result["url"].startswith("https://"), result
    assert result["primary_color"] == expected["primary_color"], result
    assert result["tokens"]["colors"]["bg"] == expected["bg"], result
    assert result["tokens"]["colors"]["accent"] == expected["accent"], result
    assert result["archetype_name"] == expected["archetype"], result


@pytest.mark.asyncio
async def test_vs0_e2e_undetermined_niche_fails_without_publishing():
    """Nicho fora do escopo VS-1 falha de forma estruturada, sem chamar LLM nem R2."""
    demo = DemoInput(
        business_name="Restaurante Central",
        niche="restaurante",
        city="Goiânia",
        whatsapp="+5562999999999",
    )
    result = await generate_demo(demo)
    assert result["status"] == "failed"
    assert result["error"] == "POSITIONING_UNDETERMINED"


@pytest.mark.asyncio
async def test_vs0_e2e_same_position_reuses_same_template_across_niches():
    """VS-2: estetica NATURAL e academia NATURAL publicam o MESMO template.

    Comprova a propriedade central do VS-2: posição igual ⇒ template igual,
    independente do nicho. Requer credenciais reais (publish em R2).
    """
    if not _env_ready():
        pytest.skip("Credenciais LLM/R2 ausentes — E2E real pulado")

    estetica = await generate_demo(
        _estetica_demo(["facial"], place_id="demo-estetica-natural-e2e")
    )
    academia = await generate_demo(
        _academia_demo(["pilates"], place_id="demo-academia-natural-e2e")
    )

    assert estetica["status"] == "published", estetica
    assert academia["status"] == "published", academia
    assert estetica["personality"] == "NATURAL_ELEGANT"
    assert academia["personality"] == "NATURAL_ELEGANT"


def test_generate_tokens_is_deterministic():
    """generate_tokens não depende de LLM e é determinístico."""
    from pipeline import generate_tokens

    demo = _demo_input()
    tokens_a, policy_a = generate_tokens(demo)
    tokens_b, policy_b = generate_tokens(demo)
    assert tokens_a.model_dump() == tokens_b.model_dump()
    assert policy_a.personality == policy_b.personality
    assert tokens_a.personality == "PREMIUM_CLINICAL"