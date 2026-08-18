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


@pytest.mark.asyncio
async def test_vs0_e2e_published():
    if not _env_ready():
        pytest.skip("Credenciais LLM/R2 ausentes — E2E real pulado")

    result = await generate_demo(_demo_input())

    assert result["status"] == "published", f"Falhou: {result}"
    assert result["personality"] == "premium_clinical"
    assert result["position"] == "PREMIUM"
    assert result["url"].startswith("https://")
    assert result["primary_color"] == "#C6A87C"
    assert result["tokens"]["colors"]["bg"] == "#F5F3F0"
    assert result["tokens"]["colors"]["accent"] == "#C6A87C"
    assert result["archetype_name"] == "prestigio_clinico"


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


def test_generate_tokens_is_deterministic():
    """generate_tokens não depende de LLM e é determinístico."""
    from pipeline import generate_tokens

    demo = _demo_input()
    tokens_a, policy_a = generate_tokens(demo)
    tokens_b, policy_b = generate_tokens(demo)
    assert tokens_a.model_dump() == tokens_b.model_dump()
    assert policy_a.personality == policy_b.personality
    assert tokens_a.personality == "premium_clinical"