"""
VisualPolicy — política visual por personalidade (VS-0).

Mapeia (nicho, posicionamento) -> personalidade visual -> arquétipo.
Determinístico. Catálogo fechado: VS-0 contém apenas PREMIUM_CLINICAL.

Contratos de contraste seguem WCAG AA (nunca AAA): texto 4.5:1,
elementos de UI (accent) 3.0:1. AAA é exigência de conformidade
adicional, fora do escopo do VS-0.
"""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class VisualPersonality(str, Enum):
    """Personalidade visual derivada de (nicho + posicionamento)."""
    PREMIUM_CLINICAL = "premium_clinical"
    PERFORMANCE_RESULT = "performance_result"
    BOLD_URBAN = "bold_urban"


class Archetype(str, Enum):
    """Arquétipo visual — em VS-0, 1:1 com a personalidade."""

    # premium / estetica
    PRESTIGIO_CLINICO = "prestigio_clinico"

    # performance / academia
    FORCA_DISCIPLINA = "forca_disciplina"

    # modern / barbearia
    ESTILO_URBANO = "estilo_urbano"

    # -- posições declaradas mas fora do slice VS-0 (reserva de catálogo) --
    # mainstream, price, innovation, expert, heritage, community, natural


class LocationPolicy(BaseModel):
    """Política de localização da personalidade.

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
    """Política visual de uma personalidade: tokens, tom, restrições.

    Contraste — WCAG AA (não AAA):
      minimum_text_contrast: 4.5  (texto normal)
      minimum_large_text_contrast: 3.0
      minimum_accent_contrast: 3.0  (elementos de UI / CTA)
    """
    personality: VisualPersonality
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


CATALOG: dict[VisualPersonality, VisualPolicy] = {
    VisualPersonality.PREMIUM_CLINICAL: VisualPolicy(
        personality=VisualPersonality.PREMIUM_CLINICAL,
        archetype=Archetype.PRESTIGIO_CLINICO,
        position="premium",
        hero_image=(
            "https://images.unsplash.com/photo-1556228578-8c89e6adf883"
            "?q=80&w=1600&auto=format&fit=crop"
        ),
        location_policy=LocationPolicy(required_for_niches=["estetica"]),
        tone_guidelines=[
            "Tom sóbrio, confiante e empático.",
            "Foco em resultado, segurança e expertise clínica.",
            "Vocabulário: 'cuidado', 'protocolo', 'resultado', 'segurança'.",
            "Evitar promessas absolutas e jargão de venda.",
        ],
        typography_heading="Playfair Display",
        typography_body="Inter",
        color_palette={
            "bg": "#F5F3F0",
            "surface": "#FFFFFF",
            "text": "#1A1A1A",
            "accent": "#C6A87C",
            "on_accent": "#1A1A1A",
        },
        forbidden=[
            "Hex fora do bloco de tokens (gate de hex limpo).",
            "Tons neon, gradientes chamativos ou paleta infantil.",
        ],
        rules=[
            "Personalidade é determinada por engine, nunca por LLM.",
            "O LLM escreve somente a copy; design vem dos tokens.",
        ],
    ),
    VisualPersonality.PERFORMANCE_RESULT: VisualPolicy(
        personality=VisualPersonality.PERFORMANCE_RESULT,
        archetype=Archetype.FORCA_DISCIPLINA,
        position="performance",
        hero_image=(
            "https://images.unsplash.com/photo-1534438327276-14e5300c3a48"
            "?q=80&w=1600&auto=format&fit=crop"
        ),
        location_policy=LocationPolicy(),
        tone_guidelines=[
            "Tom direto, energético e orientado a resultado.",
            "Foco em evolução, disciplina e superação.",
            "Vocabulário: 'resultado', 'transformação', 'disciplina', 'superação'.",
            "Evitar promessas médicas ou tom clínico.",
        ],
        typography_heading="Montserrat",
        typography_body="Inter",
        color_palette={
            "bg": "#FFFFFF",
            "surface": "#F8F9FA",
            "text": "#1A1A1A",
            "accent": "#E63946",
            "on_accent": "#FFFFFF",
        },
        forbidden=[
            "Hex fora do bloco de tokens (gate de hex limpo).",
            "Paleta pastel, decoração delicada ou tom corporativo.",
        ],
        rules=[
            "Personalidade é determinada por engine, nunca por LLM.",
            "O LLM escreve somente a copy; design vem dos tokens.",
        ],
    ),
    VisualPersonality.BOLD_URBAN: VisualPolicy(
        personality=VisualPersonality.BOLD_URBAN,
        archetype=Archetype.ESTILO_URBANO,
        position="modern",
        hero_image=(
            "https://images.unsplash.com/photo-1503951914875-452162b0f3f1"
            "?q=80&w=1600&auto=format&fit=crop"
        ),
        location_policy=LocationPolicy(),
        tone_guidelines=[
            "Tom confiante, descontraído e de identidade forte.",
            "Foco em estilo, tradição e presença.",
            "Vocabulário: 'estilo', 'corte', 'identidade', 'tradição'.",
            "Evitar tom corporativo ou genérico.",
        ],
        typography_heading="Oswald",
        typography_body="Inter",
        color_palette={
            "bg": "#1A1A1A",
            "surface": "#2A2A2A",
            "text": "#FFFFFF",
            "accent": "#D4AF37",
            "on_accent": "#1A1A1A",
        },
        forbidden=[
            "Hex fora do bloco de tokens (gate de hex limpo).",
            "Tons claros e clean — o tema é escuro por definição.",
        ],
        rules=[
            "Personalidade é determinada por engine, nunca por LLM.",
            "O LLM escreve somente a copy; design vem dos tokens.",
        ],
    ),
}
