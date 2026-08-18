"""
VisualPolicy — política visual por template (VS-2).

VS-2: a política vive dentro do VisualTemplate (design_system.visual_template),
selecionado por posição de mercado via POSITION_TEMPLATE_MAP. Não há mais
enum de personalidade visual nem CATALOG — o catálogo fechado é TEMPLATES.

Contratos de contraste seguem WCAG AA (nunca AAA): texto 4.5:1,
elementos de UI (accent) 3.0:1. AAA é exigência de conformidade
adicional, fora do escopo.
"""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Archetype(str, Enum):
    """Arquétipo visual do template (1:1 com o template)."""

    # premium
    PRESTIGIO_CLINICO = "prestigio_clinico"

    # performance
    FORCA_DISCIPLINA = "forca_disciplina"

    # modern
    ESTILO_URBANO = "estilo_urbano"

    # natural
    BELEZA_NATURAL = "beleza_natural"

    # luxury
    LUXO_SOBRIO = "luxo_sobrio"

    # modern (tech)
    TECNOLOGIA_MODERNA = "tecnologia_moderna"

    # traditional
    TRADICAO_ACOLHEDORA = "tradicao_acolhedora"


class LocationPolicy(BaseModel):
    """Política de localização do template.

    is_required é MÉTODO (não property) — recebe o nicho e decide.
    """
    required_for_niches: List[str] = Field(default_factory=list)
    hidden_for_niches: List[str] = Field(default_factory=list)

    def is_required(self, niche: str) -> bool:
        """Determina se a localização é obrigatória para o nicho."""
        return (niche or "").strip().lower() in self.required_for_niches

    def is_hidden(self, niche: str) -> bool:
        return (niche or "").strip().lower() in self.hidden_for_niches


class VisualPolicy(BaseModel):
    """Política visual de um template: tom, restrições e contratos.

    Contraste — WCAG AA (não AAA):
      minimum_text_contrast: 4.5  (texto normal)
      minimum_large_text_contrast: 3.0
      minimum_accent_contrast: 3.0  (elementos de UI / CTA)
    """
    personality: str
    archetype: Archetype
    position: str
    hero_image: str = ""
    location_policy: LocationPolicy = Field(default_factory=LocationPolicy)
    tone_guidelines: List[str] = Field(default_factory=list)
    typography_heading: str = "Inter"
    typography_body: str = "Inter"
    color_palette: dict = Field(default_factory=dict)
    forbidden: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)

    # WCAG AA (não AAA)
    minimum_text_contrast: float = 4.5
    minimum_large_text_contrast: float = 3.0
    minimum_accent_contrast: float = 3.0