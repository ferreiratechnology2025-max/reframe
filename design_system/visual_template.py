"""
VisualTemplate — template visual reutilizável, independente de nicho (VS-2).

VS-2 desacopla a seleção visual do nicho: uma posição de mercado resolve
para um VisualTemplate por meio do POSITION_TEMPLATE_MAP (position-only).
O template agrega a identidade completa (tokens + política visual) e pode
ser reutilizado por qualquer nicho que alcance a mesma posição.

7 templates no catálogo fechado:
  PREMIUM_CLINICAL, PERFORMANCE_RESULT, BOLD_URBAN (VS-0/VS-1)
  NATURAL_ELEGANT, LUXURY_MINIMAL, MODERN_TECH, ORGANIC_WARM (VS-2)

BOLD_URBAN permanece no catálogo como referência visual, mas NÃO está no
POSITION_TEMPLATE_MAP ativo (MODERN resolve para MODERN_TECH).
"""
from typing import Dict, List

from pydantic import BaseModel, Field

from design_system.design_tokens import (
    ColorRole,
    DesignTokens,
    FontSpec,
    SemanticColor,
    TypographyPolicy,
)
from design_system.visual_policy import Archetype, LocationPolicy, VisualPolicy


class VisualTemplate(BaseModel):
    """Identidade visual completa e reutilizável (tokens + política).

    Não conhece nichos: é um componente do Design System Engine selecionado
    por posição de mercado (ver engines.theme_resolver.POSITION_TEMPLATE_MAP).
    """
    id: str
    name: str
    description: str
    colors: Dict[ColorRole, str]
    semantic_colors: Dict[SemanticColor, str]
    typography: TypographyPolicy
    spacing: Dict[str, str] = Field(default_factory=dict)
    radius: Dict[str, str] = Field(default_factory=dict)
    shadows: Dict[str, str] = Field(default_factory=dict)
    policy: VisualPolicy
    font_links: List[str] = Field(default_factory=list)

    def build_tokens(self) -> DesignTokens:
        """Deriva os DesignTokens determinísticos do template."""
        return DesignTokens(
            personality=self.id,
            colors=self.colors,
            semantic_colors=self.semantic_colors,
            typography=self.typography,
            spacing=self.spacing,
            radius=self.radius,
            shadows=self.shadows,
        )


_BASE_SPACING = {
    "xs": "0.5rem",
    "sm": "1rem",
    "md": "1.5rem",
    "lg": "2.5rem",
    "xl": "4rem",
}

_BASE_RADIUS = {
    "sm": "0.375rem",
    "md": "0.625rem",
    "lg": "1rem",
    "pill": "9999px",
}

_SHADOWS_LIGHT = {
    "sm": "0 1px 2px rgba(26, 26, 26, 0.06)",
    "md": "0 6px 24px rgba(26, 26, 26, 0.08)",
    "lg": "0 12px 48px rgba(26, 26, 26, 0.12)",
}

_SHADOWS_DARK = {
    "sm": "0 1px 2px rgba(0, 0, 0, 0.25)",
    "md": "0 6px 24px rgba(0, 0, 0, 0.35)",
    "lg": "0 12px 48px rgba(0, 0, 0, 0.45)",
}

_SEMANTIC = {
    SemanticColor.SUCCESS: "#2E7D32",
    SemanticColor.WARNING: "#B26A00",
    SemanticColor.ERROR: "#C62828",
    SemanticColor.INFO: "#1565C0",
}

_POLICY_RULES = [
    "Personalidade é determinada por engine, nunca por LLM.",
    "O LLM escreve somente a copy; design vem dos tokens.",
]


TEMPLATES: Dict[str, VisualTemplate] = {
    "PREMIUM_CLINICAL": VisualTemplate(
        id="PREMIUM_CLINICAL",
        name="Premium Clínico",
        description="Cuidado premium, sóbrio e confiante — estética e saúde.",
        colors={
            ColorRole.BG: "#F5F3F0",
            ColorRole.SURFACE: "#FFFFFF",
            ColorRole.TEXT: "#1A1A1A",
            ColorRole.TEXT_SECONDARY: "#4A4A4A",
            ColorRole.HEADING: "#1A1A1A",
            ColorRole.BORDER: "#E8E3DD",
            ColorRole.ACCENT: "#C6A87C",
            ColorRole.ACCENT_HOVER: "#B8976A",
            ColorRole.ON_ACCENT: "#1A1A1A",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors=_SEMANTIC,
        typography=TypographyPolicy(
            heading=FontSpec(
                family="Playfair Display",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Georgia, serif",
        ),
        spacing=_BASE_SPACING,
        radius=_BASE_RADIUS,
        shadows=_SHADOWS_LIGHT,
        policy=VisualPolicy(
            personality="PREMIUM_CLINICAL",
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
            rules=_POLICY_RULES,
        ),
        font_links=["Playfair Display", "Inter"],
    ),
    "PERFORMANCE_RESULT": VisualTemplate(
        id="PERFORMANCE_RESULT",
        name="Performance Resultado",
        description="Energia, disciplina e superação — treino e resultado.",
        colors={
            ColorRole.BG: "#FFFFFF",
            ColorRole.SURFACE: "#F8F9FA",
            ColorRole.TEXT: "#1A1A1A",
            ColorRole.TEXT_SECONDARY: "#4A4A4A",
            ColorRole.HEADING: "#1A1A1A",
            ColorRole.BORDER: "#E0E0E0",
            ColorRole.ACCENT: "#E63946",
            ColorRole.ACCENT_HOVER: "#C62828",
            ColorRole.ON_ACCENT: "#FFFFFF",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors=_SEMANTIC,
        typography=TypographyPolicy(
            heading=FontSpec(
                family="Montserrat",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Helvetica, Arial, sans-serif",
        ),
        spacing=_BASE_SPACING,
        radius=_BASE_RADIUS,
        shadows=_SHADOWS_LIGHT,
        policy=VisualPolicy(
            personality="PERFORMANCE_RESULT",
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
            rules=_POLICY_RULES,
        ),
        font_links=["Montserrat", "Inter"],
    ),
    "BOLD_URBAN": VisualTemplate(
        id="BOLD_URBAN",
        name="Urbano Ousado",
        description="Referência visual escura e marcante — identidade forte.",
        colors={
            ColorRole.BG: "#1A1A1A",
            ColorRole.SURFACE: "#2A2A2A",
            ColorRole.TEXT: "#FFFFFF",
            ColorRole.TEXT_SECONDARY: "#AAAAAA",
            ColorRole.HEADING: "#FFFFFF",
            ColorRole.BORDER: "#3A3A3A",
            ColorRole.ACCENT: "#D4AF37",
            ColorRole.ACCENT_HOVER: "#C49A2A",
            ColorRole.ON_ACCENT: "#1A1A1A",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors=_SEMANTIC,
        typography=TypographyPolicy(
            heading=FontSpec(
                family="Oswald",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Impact, sans-serif",
        ),
        spacing=_BASE_SPACING,
        radius=_BASE_RADIUS,
        shadows=_SHADOWS_DARK,
        policy=VisualPolicy(
            personality="BOLD_URBAN",
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
            rules=_POLICY_RULES,
        ),
        font_links=["Oswald", "Inter"],
    ),
    "NATURAL_ELEGANT": VisualTemplate(
        id="NATURAL_ELEGANT",
        name="Elegância Natural",
        description="Sage e quente, acolhedor e sofisticado — beleza natural.",
        colors={
            ColorRole.BG: "#F7F5F0",
            ColorRole.SURFACE: "#FFFFFF",
            ColorRole.TEXT: "#3A3A38",
            ColorRole.TEXT_SECONDARY: "#6A6A68",
            ColorRole.HEADING: "#3A3A38",
            ColorRole.BORDER: "#E8E4DC",
            ColorRole.ACCENT: "#7A8B6F",
            ColorRole.ACCENT_HOVER: "#6A7B5F",
            ColorRole.ON_ACCENT: "#FFFFFF",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors=_SEMANTIC,
        typography=TypographyPolicy(
            heading=FontSpec(
                family="Playfair Display",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Georgia, serif",
        ),
        spacing=_BASE_SPACING,
        radius=_BASE_RADIUS,
        shadows=_SHADOWS_LIGHT,
        policy=VisualPolicy(
            personality="NATURAL_ELEGANT",
            archetype=Archetype.BELEZA_NATURAL,
            position="natural",
            hero_image=(
                "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881"
                "?q=80&w=1600&auto=format&fit=crop"
            ),
            location_policy=LocationPolicy(required_for_niches=["estetica"]),
            tone_guidelines=[
                "Tom sereno, natural e sofisticado.",
                "Foco em bem-estar, equilíbrio e cuidado genuíno.",
                "Vocabulário: 'natural', 'equilíbrio', 'bem-estar', 'cuidado'.",
                "Evitar promessas absolutas e tom técnico-cirúrgico.",
            ],
            typography_heading="Playfair Display",
            typography_body="Inter",
            color_palette={
                "bg": "#F7F5F0",
                "surface": "#FFFFFF",
                "text": "#3A3A38",
                "accent": "#7A8B6F",
                "on_accent": "#FFFFFF",
            },
            forbidden=[
                "Hex fora do bloco de tokens (gate de hex limpo).",
                "Tons neon, alto contraste agressivo ou paleta fria.",
            ],
            rules=_POLICY_RULES,
        ),
        font_links=["Playfair Display", "Inter"],
    ),
    "LUXURY_MINIMAL": VisualTemplate(
        id="LUXURY_MINIMAL",
        name="Luxo Minimalista",
        description="Escuro e sóbrio, detalhes em dourado — exclusividade.",
        colors={
            ColorRole.BG: "#111111",
            ColorRole.SURFACE: "#1C1C1C",
            ColorRole.TEXT: "#F5F5F5",
            ColorRole.TEXT_SECONDARY: "#B5B3B0",
            ColorRole.HEADING: "#F5F5F5",
            ColorRole.BORDER: "#2A2A2A",
            ColorRole.ACCENT: "#C9A96A",
            ColorRole.ACCENT_HOVER: "#B8975A",
            ColorRole.ON_ACCENT: "#111111",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors=_SEMANTIC,
        typography=TypographyPolicy(
            heading=FontSpec(
                family="Cormorant Garamond",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Georgia, serif",
        ),
        spacing=_BASE_SPACING,
        radius=_BASE_RADIUS,
        shadows=_SHADOWS_DARK,
        policy=VisualPolicy(
            personality="LUXURY_MINIMAL",
            archetype=Archetype.LUXO_SOBRIO,
            position="luxury",
            hero_image=(
                "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6"
                "?q=80&w=1600&auto=format&fit=crop"
            ),
            location_policy=LocationPolicy(),
            tone_guidelines=[
                "Tom exclusivo, sóbrio e sofisticado.",
                "Foco em experiência premium, requinte e atenção ao detalhe.",
                "Vocabulário: 'exclusivo', 'experiência', 'requinte', 'detalhe'.",
                "Evitar linguagem promocional ou volume (preço/desconto).",
            ],
            typography_heading="Cormorant Garamond",
            typography_body="Inter",
            color_palette={
                "bg": "#111111",
                "surface": "#1C1C1C",
                "text": "#F5F5F5",
                "accent": "#C9A96A",
                "on_accent": "#111111",
            },
            forbidden=[
                "Hex fora do bloco de tokens (gate de hex limpo).",
                "Tons claros e clean, promos de preço ou paleta chamativa.",
            ],
            rules=_POLICY_RULES,
        ),
        font_links=["Cormorant Garamond", "Inter"],
    ),
    "MODERN_TECH": VisualTemplate(
        id="MODERN_TECH",
        name="Moderno Tecnológico",
        description="Limpo, nítido e tecnológico — inovação e precisão.",
        colors={
            ColorRole.BG: "#FFFFFF",
            ColorRole.SURFACE: "#F8F9FA",
            ColorRole.TEXT: "#0A1931",
            ColorRole.TEXT_SECONDARY: "#4A4A6A",
            ColorRole.HEADING: "#0A1931",
            ColorRole.BORDER: "#E0E4EA",
            ColorRole.ACCENT: "#00E5FF",
            ColorRole.ACCENT_HOVER: "#00B8D4",
            ColorRole.ON_ACCENT: "#0A1931",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors=_SEMANTIC,
        typography=TypographyPolicy(
            heading=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Helvetica, Arial, sans-serif",
        ),
        spacing=_BASE_SPACING,
        radius=_BASE_RADIUS,
        shadows=_SHADOWS_LIGHT,
        policy=VisualPolicy(
            personality="MODERN_TECH",
            archetype=Archetype.TECNOLOGIA_MODERNA,
            position="modern",
            hero_image=(
                "https://images.unsplash.com/photo-1518770660439-4636190af475"
                "?q=80&w=1600&auto=format&fit=crop"
            ),
            location_policy=LocationPolicy(),
            tone_guidelines=[
                "Tom direto, moderno e orientado a inovação.",
                "Foco em método, precisão e experiência atual.",
                "Vocabulário: 'método', 'precisão', 'inovação', 'experiência'.",
                "Evitar jargão tradicional ou tom antiquado.",
            ],
            typography_heading="Inter",
            typography_body="Inter",
            color_palette={
                "bg": "#FFFFFF",
                "surface": "#F8F9FA",
                "text": "#0A1931",
                "accent": "#00E5FF",
                "on_accent": "#0A1931",
            },
            forbidden=[
                "Hex fora do bloco de tokens (gate de hex limpo).",
                "Tons dourados clássicos ou estética retrô.",
            ],
            rules=_POLICY_RULES,
        ),
        font_links=["Inter"],
    ),
    "ORGANIC_WARM": VisualTemplate(
        id="ORGANIC_WARM",
        name="Orgânico Aconchegante",
        description="Tons quentes e terrosos — tradição, acolhimento e raízes.",
        colors={
            ColorRole.BG: "#E8E6D9",
            ColorRole.SURFACE: "#F5F3EC",
            ColorRole.TEXT: "#2D2A24",
            ColorRole.TEXT_SECONDARY: "#5A5448",
            ColorRole.HEADING: "#2D2A24",
            ColorRole.BORDER: "#D4CFC4",
            ColorRole.ACCENT: "#A97C50",
            ColorRole.ACCENT_HOVER: "#977048",
            ColorRole.ON_ACCENT: "#F5F3EC",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors=_SEMANTIC,
        typography=TypographyPolicy(
            heading=FontSpec(
                family="Cormorant Garamond",
                source="google",
                weights=[400, 600, 700],
            ),
            body=FontSpec(
                family="Inter",
                source="google",
                weights=[400, 500, 600],
            ),
            fallback_stack="Georgia, serif",
        ),
        spacing=_BASE_SPACING,
        radius=_BASE_RADIUS,
        shadows=_SHADOWS_LIGHT,
        policy=VisualPolicy(
            personality="ORGANIC_WARM",
            archetype=Archetype.TRADICAO_ACOLHEDORA,
            position="traditional",
            hero_image=(
                "https://images.unsplash.com/photo-1556910103-1c02745aae4d"
                "?q=80&w=1600&auto=format&fit=crop"
            ),
            location_policy=LocationPolicy(),
            tone_guidelines=[
                "Tom acolhedor, humano e de raízes.",
                "Foco em tradição, cuidado artesanal e comunidade.",
                "Vocabulário: 'tradição', 'artesanal', 'raízes', 'acolhimento'.",
                "Evitar tom tecnológico ou corporativo frio.",
            ],
            typography_heading="Cormorant Garamond",
            typography_body="Inter",
            color_palette={
                "bg": "#E8E6D9",
                "surface": "#F5F3EC",
                "text": "#2D2A24",
                "accent": "#A97C50",
                "on_accent": "#F5F3EC",
            },
            forbidden=[
                "Hex fora do bloco de tokens (gate de hex limpo).",
                "Tons neon ou estética fria e minimalista.",
            ],
            rules=_POLICY_RULES,
        ),
        font_links=["Cormorant Garamond", "Inter"],
    ),
}