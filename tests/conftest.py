"""
Fixtures compartilhadas dos testes VS-0.x — cenários de evidência.

Usam os contratos REAIS do Design System (design_system.*), nunca os
módulos antigos. Evidência é CONTEXTO, não modificador de posicionamento
no VS-0/VS-0.1 (refinamento por evidência é VS-1+).
"""
import pytest

from design_system.location import BusinessLocation, LocationStatus


@pytest.fixture
def complete_evidence():
    """Evidência completa — contexto, não modificador de posicionamento."""
    return {
        "rating": 4.8,
        "total_ratings": 327,
        "specialties": ["facial", "injetáveis"],
        "location": BusinessLocation(
            address_line="Av. T-10, 1234",
            neighborhood="Setor Bueno",
            city="Goiânia",
            state="GO",
            source="google_places",
            source_ref="ChIJN1t_tDeuEmsRUsoyN83rY4Q",
            confidence=0.95,
            status=LocationStatus.VERIFIED,
            google_maps_url="https://maps.google.com/...",
        ),
    }


@pytest.fixture
def minimal_evidence():
    """Evidência mínima — apenas o essencial para não quebrar."""
    return {
        "rating": None,
        "total_ratings": 0,
        "specialties": [],
        "location": None,
    }


@pytest.fixture
def location_unverified():
    """Localização não verificada — deve ser tratada como tal."""
    return BusinessLocation(
        address_line="Rua X, 456",
        neighborhood="Setor Marista",
        city="Goiânia",
        state="GO",
        source="lead_input",
        source_ref="manual",
        confidence=0.4,
        status=LocationStatus.UNVERIFIED,
        google_maps_url=None,
    )
