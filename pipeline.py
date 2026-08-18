"""
pipeline — entrada de alto nível para o VS-0 (E2E / demos).

Decouples o chamador do fluxo assíncrono do main.generate_landing:
- DemoInput: dados mínimos de um negócio (determinísticos).
- generate_tokens: deriva (tokens, policy) sem LLM (determinístico).
- generate_demo: roda o pipeline completo e retorna o resultado publicado.

O LLM é usado APENAS para copy dentro de generate_demo; tokens,
posicionamento e tema são decisões do Design System Engine.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from design_system.design_tokens import DesignTokens
from design_system.evidence_positioning import EvidencePositioningEngine
from design_system.location import BusinessLocation
from design_system.visual_policy import VisualPolicy
from engines.theme_resolver import VisualThemeResolver
from engines.design_tokens_engine import DesignTokensEngine
from models import CommercialEvidence, EvidenceSource


@dataclass
class DemoInput:
    """Entrada mínima e determinística para o E2E do VS-0."""
    business_name: str
    niche: str
    city: str
    whatsapp: str
    place_id: str = "demo-place-id"
    evidence: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None


def _evidence_to_commercial(evidence: Optional[Dict[str, Any]]) -> CommercialEvidence:
    """Converte dict de evidência (rating/avaliações/especialidades) no
    contrato CommercialEvidence usado pelo pipeline.

    VS-1: rating/total_ratings/specialties ficam ESTRUTURADOS (fonte de
    decisão). As strings de copy são derivadas (contexto para o LLM), nunca
    fonte de decisão.
    """
    evidence = evidence or {}
    specialties = list(evidence.get("specialties") or [])
    services = [f"Especialidade: {s}" for s in specialties]
    rating = evidence.get("rating")
    total = evidence.get("total_ratings")

    if rating is not None and total is not None:
        services.append(f"Nota {rating} com {total} avaliações no Google")

    return CommercialEvidence(
        services=services,
        rating=rating,
        total_ratings=total,
        specialties=specialties,
        sources={
            "services": EvidenceSource(type="google_places", confidence=0.9, verified=True),
            "rating": EvidenceSource(type="google_places", confidence=0.9, verified=True),
            "total_ratings": EvidenceSource(type="google_places", confidence=0.9, verified=True),
            "specialties": EvidenceSource(type="google_places", confidence=0.9, verified=True),
        },
    )


def generate_tokens(demo: DemoInput) -> tuple[DesignTokens, VisualPolicy]:
    """Deriva (tokens, policy) da entrada — 100% determinístico, sem LLM."""
    positioning = EvidencePositioningEngine().determine(demo.niche, demo.evidence)
    if positioning.is_undetermined:
        raise ValueError(
            f"POSITIONING_UNDETERMINED: nicho '{demo.niche}' fora do escopo VS-1"
        )
    personality = VisualThemeResolver().resolve(demo.niche, positioning.market_position)
    return DesignTokensEngine().generate(personality)


async def generate_demo(demo: DemoInput) -> Dict[str, Any]:
    """Executa o pipeline completo (design system + LLM copy + gates + publish)."""
    from main import generate_landing

    location: Optional[BusinessLocation] = None
    if demo.location:
        location = BusinessLocation(**demo.location)

    evidence = _evidence_to_commercial(demo.evidence)

    return await generate_landing(
        lead_name=demo.business_name,
        niche=demo.niche,
        city=demo.city,
        phone=demo.whatsapp,
        place_id=demo.place_id,
        evidence=evidence,
        location=location,
    )