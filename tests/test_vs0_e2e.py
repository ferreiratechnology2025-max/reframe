"""
E2E do Vertical Slice VS-0 — pipeline completo REAL.

Cadeia: Evidence → Positioning (determinístico) → Theme → Tokens →
DesignTokenGate → LLM Copy → Evidence Integrity Gate → Render →
RenderedVisualGate (Playwright) → Publish (R2 de verdade).

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


NICHES_EXPECTED = [
    (
        "estetica",
        DemoInput(
            business_name="Clínica Dra. Andrielle Fernandes",
            niche="estetica",
            city="Goiânia",
            whatsapp="+5562999999999",
            place_id="ChIJN1t_tDeuEmsRUsoyN83rY4Q",
            evidence={"rating": 4.8, "total_ratings": 327, "specialties": ["facial", "injetáveis"]},
            location={
                "address_line": "Av. T-63, 1299 — Setor Bueno",
                "neighborhood": "Setor Bueno",
                "city": "Goiânia",
                "state": "GO",
                "latitude": -16.6869,
                "longitude": -49.2648,
                "google_maps_url": "https://www.google.com/maps/search/?api=1&query=-16.6869,-49.2648",
                "source": "google_places",
                "source_ref": "ChIJN1t_tDeuEmsRUsoyN83rY4Q",
                "status": "verified",
                "confidence": 0.95,
            },
        ),
        {
            "personality": "premium_clinical",
            "position": "PREMIUM",
            "primary_color": "#C6A87C",
            "bg": "#F5F3F0",
            "accent": "#C6A87C",
            "archetype": "prestigio_clinico",
        },
    ),
    (
        "academia",
        DemoInput(
            business_name="Academia Performance Prime",
            niche="academia",
            city="Goiânia",
            whatsapp="+5562999999999",
            place_id="demo-academia",
            evidence={"rating": 4.7, "total_ratings": 512, "specialties": ["musculação", "funcional"]},
            location={
                "address_line": "Av. Anhanguera, 450 — Centro",
                "neighborhood": "Centro",
                "city": "Goiânia",
                "state": "GO",
                "latitude": -16.6864,
                "longitude": -49.2643,
                "google_maps_url": "https://www.google.com/maps/search/?api=1&query=-16.6864,-49.2643",
                "source": "google_places",
                "source_ref": "demo-academia",
                "status": "verified",
                "confidence": 0.9,
            },
        ),
        {
            "personality": "performance_result",
            "position": "PERFORMANCE",
            "primary_color": "#E63946",
            "bg": "#FFFFFF",
            "accent": "#E63946",
            "archetype": "forca_disciplina",
        },
    ),
    (
        "barbearia",
        DemoInput(
            business_name="Barbearia Central",
            niche="barbearia",
            city="Goiânia",
            whatsapp="+5562999999999",
            place_id="demo-barbearia",
            # VS-1: "barba"/"corte premium" → LUXURY (sem personalidade → bloqueio).
            # Para publicar MODERN, evidência de especialidade fica vazia e o
            # rating/volume resolve MODERN (rating ≥4.5 E volume ≥100).
            evidence={"rating": 4.9, "total_ratings": 891, "specialties": []},
            location={
                "address_line": "Rua 3, 120 — Setor Central",
                "neighborhood": "Setor Central",
                "city": "Goiânia",
                "state": "GO",
                "latitude": -16.6799,
                "longitude": -49.2550,
                "google_maps_url": "https://www.google.com/maps/search/?api=1&query=-16.6799,-49.2550",
                "source": "google_places",
                "source_ref": "demo-barbearia",
                "status": "verified",
                "confidence": 0.9,
            },
        ),
        {
            "personality": "bold_urban",
            "position": "MODERN",
            "primary_color": "#D4AF37",
            "bg": "#1A1A1A",
            "accent": "#D4AF37",
            "archetype": "estilo_urbano",
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
    assert result["personality"] == expected["personality"], result
    assert result["position"] == expected["position"], result
    assert result["url"].startswith("https://"), result
    assert result["primary_color"] == expected["primary_color"], result
    assert result["tokens"]["colors"]["bg"] == expected["bg"], result
    assert result["tokens"]["colors"]["accent"] == expected["accent"], result
    assert result["archetype_name"] == expected["archetype"], result


@pytest.mark.asyncio
async def test_vs0_e2e_undetermined_niche_fails_without_publishing():
    """Nicho fora do VS-0 falha de forma estruturada, sem chamar LLM nem R2."""
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
async def test_vs0_e2e_luxury_barbearia_blocks_without_publishing():
    """VS-1: barbearia + 'barba' → LUXURY → THEME_UNRESOLVED → bloqueio.

    Não publica (posição sem personalidade no catálogo visual fechado VS-0).
    Falha ANTES do LLM/R2 — não depende de credenciais.
    """
    demo = DemoInput(
        business_name="Barbearia Central",
        niche="barbearia",
        city="Goiânia",
        whatsapp="+5562999999999",
        place_id="demo-barbearia-luxury",
        evidence={"rating": 4.9, "total_ratings": 891, "specialties": ["corte clássico", "barba"]},
    )
    result = await generate_demo(demo)
    assert result["status"] == "failed"
    assert result["error"] == "THEME_UNRESOLVED"


def test_generate_tokens_is_deterministic():
    """generate_tokens não depende de LLM e é determinístico."""
    from pipeline import generate_tokens

    demo = _demo_input()
    tokens_a, policy_a = generate_tokens(demo)
    tokens_b, policy_b = generate_tokens(demo)
    assert tokens_a.model_dump() == tokens_b.model_dump()
    assert policy_a.personality == policy_b.personality
    assert tokens_a.personality == "premium_clinical"