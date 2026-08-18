"""
Design Tokens — contratos do Design System Engine (VS-0).

Tokens sao a FONTE DE VERDADE da identidade visual. Sao deterministicos,
derivados da personalidade visual (nicho + posicionamento), e NUNCA sao
alterados pelo LLM. O LLM apenas escreve copy.

Regra do slice VS-0: apenas a personalidade PREMIUM_CLINICAL esta mapeada.
"""
import re
from enum import Enum
from typing import Dict, List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_HEX_COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')

# Roles de cor que a identidade visual DEVE definir (contrato minimo).
REQUIRED_COLOR_ROLES = frozenset({
    "bg", "surface", "text", "accent", "on_accent",
})


class ColorRole(str, Enum):
    """Papel funcional de cada cor na identidade visual (nao "nomes")."""
    BG = "bg"
    SURFACE = "surface"
    TEXT = "text"
    TEXT_SECONDARY = "text_secondary"
    HEADING = "heading"
    BORDER = "border"
    ACCENT = "accent"
    ACCENT_HOVER = "accent_hover"
    ON_ACCENT = "on_accent"

    @property
    def css_name(self) -> str:
        """Nome CSS: --color-{role} (underscore -> hifen)."""
        return self.value.replace("_", "-")


class SemanticColor(str, Enum):
    """Cores semânticas (feedback/estado), independentes da marca."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class FontSpec(BaseModel):
    """Especificação de uma fonte."""
    family: str = Field(..., min_length=1)
    source: Literal["system", "google", "self_hosted"]
    weights: List[int] = Field(default_factory=list)

    @field_validator("weights")
    @classmethod
    def _weights_positive(cls, v: List[int]) -> List[int]:
        for w in v:
            if w <= 0:
                raise ValueError(f"Peso de fonte inválido: {w}")
        return v


class TypographyPolicy(BaseModel):
    """Política tipográfica: heading + body, com stack de fallback."""
    heading: FontSpec
    body: FontSpec
    fallback_stack: str = "sans-serif"
    size_base: str = "16px"
    line_height: str = "1.6"
    line_height_heading: str = "1.2"


class DesignTokens(BaseModel):
    """Conjunto completo de tokens de design para uma personalidade visual.

    Determinismo: a mesma personalidade produz sempre os mesmos tokens.
    O LLM não tem acesso a este objeto.
    """
    personality: str
    version: str = "1.0.0"
    colors: Dict[ColorRole, str] = Field(default_factory=dict)
    semantic_colors: Dict[SemanticColor, str] = Field(default_factory=dict)
    typography: TypographyPolicy
    spacing: Dict[str, str] = Field(default_factory=dict)
    radius: Dict[str, str] = Field(default_factory=dict)
    shadows: Dict[str, str] = Field(default_factory=dict)

    @field_validator("colors")
    @classmethod
    def _validate_colors(cls, v: Dict[ColorRole, str]) -> Dict[ColorRole, str]:
        for role, value in v.items():
            if not isinstance(value, str) or not _HEX_COLOR.match(value):
                raise ValueError(f"Cor do role {role.value} não é hex válido: {value!r}")
        return v

    @field_validator("semantic_colors")
    @classmethod
    def _validate_semantic_colors(cls, v: Dict[SemanticColor, str]) -> Dict[SemanticColor, str]:
        for name, value in v.items():
            if not isinstance(value, str) or not _HEX_COLOR.match(value):
                raise ValueError(f"Cor semântica {name.value} não é hex válido: {value!r}")
        return v

    @model_validator(mode="after")
    def _check_required_roles(self):
        present = {role.value for role in self.colors}
        missing = REQUIRED_COLOR_ROLES - present
        if missing:
            raise ValueError(f"Roles de cor obrigatórios ausentes: {sorted(missing)}")
        return self

    def get_css_variables(self) -> str:
        """Gera o bloco de declarações CSS (sem o wrapper :root).

        Todo hex do template vive AQUI — fora deste bloco, hex é proibido
        (ver gates.rendered_visual_gate: disallow_raw_colors).
        """
        lines: List[str] = []
        for role, value in self.colors.items():
            lines.append(f"--color-{role.css_name}: {value};")
        for name, value in self.semantic_colors.items():
            lines.append(f"--color-{name.value}: {value};")
        lines.append(
            f"--font-heading: '{self.typography.heading.family}', {self.typography.fallback_stack};"
        )
        lines.append(
            f"--font-body: '{self.typography.body.family}', -apple-system, 'Segoe UI', sans-serif;"
        )
        for key, value in self.spacing.items():
            lines.append(f"--space-{key}: {value};")
        for key, value in self.radius.items():
            lines.append(f"--radius-{key}: {value};")
        for key, value in self.shadows.items():
            lines.append(f"--shadow-{key}: {value};")
        return "\n".join(lines)

    def get_font_links(self) -> str:
        """Retorna tags <link> do Google Fonts quando alguma fonte usa source=google.

        Vazio quando todas as fontes são locais (system/self_hosted).
        """
        google_fonts = []
        if self.typography.heading.source == "google":
            google_fonts.append(self.typography.heading)
        if self.typography.body.source == "google":
            google_fonts.append(self.typography.body)

        if not google_fonts:
            return ""

        families = []
        for spec in google_fonts:
            weights = ";".join(str(w) for w in sorted(set(spec.weights)))
            family = spec.family.replace(" ", "+")
            if weights:
                families.append(f"family={family}:wght@{weights}")
            else:
                families.append(f"family={family}")
        query = "&".join(families)
        return (
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link href="https://fonts.googleapis.com/css2?{query}&display=swap" rel="stylesheet">'
        )
