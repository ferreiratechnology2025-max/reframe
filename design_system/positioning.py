"""
Positioning — posicionamento estratégico da marca (VS-0).

Determinístico. Regras declarativas (engine) decidem o posicionamento a
partir da evidência comercial. O LLM NUNCA decide posicionamento.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MarketPosition(str, Enum):
    """Posicionamento estratégico de mercado.

    VS-0 implementa apenas estetica/PREMIUM, mas o enum declarado cobre
    o espaço do produto — UNDETERMINED existe para falhas de evidência.
    """
    PERFORMANCE = "PERFORMANCE"
    MAINSTREAM = "MAINSTREAM"
    PRICE = "PRICE"
    INNOVATION = "INNOVATION"
    PREMIUM = "PREMIUM"
    EXPERT = "EXPERT"
    HERITAGE = "HERITAGE"
    COMMUNITY = "COMMUNITY"
    NATURAL = "NATURAL"
    MODERN = "MODERN"
    UNDETERMINED = "UNDETERMINED"


class Positioning(BaseModel):
    """Decisão de posicionamento completa — auditável e serializável."""
    segment: str = Field(..., min_length=1)
    market_position: MarketPosition
    evidence_strength: float = Field(default=0.0, ge=0, le=1)
    evidence_refs: List[str] = Field(default_factory=list)
    decision_reasons: List[str] = Field(default_factory=list)
    value_proposition: str = ""
    tone: str = "profissional"
    target_audience: str = ""

    @property
    def is_undetermined(self) -> bool:
        return self.market_position == MarketPosition.UNDETERMINED

    @property
    def rules_applied(self) -> List[str]:
        """Alias para decisão auditável (paridade com contratos de gate)."""
        return self.decision_reasons