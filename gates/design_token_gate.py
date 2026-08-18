"""
DesignTokenGate — portão de qualidade dos tokens ANTES do LLM (VS-0).

Verifica contraste (WCAG AA), roles obrigatórios e coesão com a política.
Falha = erro estruturado; NUNCA auto-repair (design não é negociável).

Contrato de saída: (passed: bool, issues: List[str]).
"""
from typing import List, Optional

from design_system.design_tokens import REQUIRED_COLOR_ROLES, ColorRole, DesignTokens
from design_system.visual_policy import VisualPolicy
from gates.contrast import contrast_ratio

# Limiares WCAG AA — são sobrescritos pelos valores da VisualPolicy.
DEFAULT_TEXT_CONTRAST_MIN = 4.5
DEFAULT_UI_CONTRAST_MIN = 3.0


class DesignTokenGate:
    """Valida que um conjunto de tokens é seguro para renderizar."""

    def validate(
        self,
        tokens: DesignTokens,
        policy: Optional[VisualPolicy] = None,
    ) -> tuple[bool, List[str]]:
        issues: List[str] = []

        text_min = (policy.minimum_text_contrast if policy else DEFAULT_TEXT_CONTRAST_MIN)
        ui_min = (policy.minimum_accent_contrast if policy else DEFAULT_UI_CONTRAST_MIN)

        # 1) Roles obrigatórios do contrato mínimo.
        missing = REQUIRED_COLOR_ROLES - {role.value for role in tokens.colors}
        if missing:
            issues.append(f"roles de cor obrigatórios ausentes: {sorted(missing)}")

        # 2) Contraste texto/fundo (WCAG AA: >= 4.5:1).
        text_bg = contrast_ratio(tokens.colors[ColorRole.TEXT], tokens.colors[ColorRole.BG])
        if text_bg < text_min:
            issues.append(
                f"contraste text/bg {text_bg:.2f}:1 < {text_min}:1"
                f" ({tokens.colors[ColorRole.TEXT]} sobre {tokens.colors[ColorRole.BG]})"
            )

        # 3) Contraste accent/on_accent (UI: >= 3.0:1).
        accent = tokens.colors[ColorRole.ACCENT]
        on_accent = tokens.colors[ColorRole.ON_ACCENT]
        accent_ratio = contrast_ratio(accent, on_accent)
        if accent_ratio < ui_min:
            issues.append(
                f"contraste on_accent/accent {accent_ratio:.2f}:1 < {ui_min}:1"
                f" ({on_accent} sobre {accent})"
            )

        # 4) Accent não pode colidir com o fundo.
        if accent == tokens.colors[ColorRole.BG]:
            issues.append("accent idêntico a bg — CTA invisível")

        # 5) Coesão da política visual.
        if policy is not None and tokens.personality != policy.personality.value:
            issues.append(
                f"personality do tokens ({tokens.personality}) diverge da política "
                f"({policy.personality.value})"
            )

        return (not issues, issues)