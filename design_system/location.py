"""
BusinessLocation — localização determinística do negócio (VS-0).

100% determinística. O LLM NÃO toca em localização. Deriva de fonte
confiável (Google Places, cadastro verificado) e carrega status de
confiança auditável.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LocationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"


class BusinessLocation(BaseModel):
    """Endereço + georeferência de um negócio, com procedência auditável."""
    address_line: str = Field(..., min_length=3)
    neighborhood: Optional[str] = None
    city: str = Field(..., min_length=2)
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    google_maps_url: Optional[str] = None
    source: str = Field(..., min_length=1)
    source_ref: str = Field(..., min_length=1)
    confidence: float = Field(default=0.0, ge=0, le=1)
    status: LocationStatus = LocationStatus.UNVERIFIED
    observed_at: datetime = Field(default_factory=datetime.now)
    is_conflict: bool = False
    conflict_details: Optional[str] = None

    def format_microcopy(self, template: str = "{neighborhood} · {city}") -> str:
        """Formata a microcopy de localização segundo o template da policy."""
        return template.format(
            neighborhood=self.neighborhood or "",
            city=self.city,
            state=self.state or "",
        )