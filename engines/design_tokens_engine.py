"""
DesignTokensEngine — gera (DesignTokens, VisualPolicy) de um VisualTemplate (VS-2).

Determinístico e baseado em política: tokens NUNCA são gerados por LLM.
Catálogo fechado em TEMPLATES (design_system.visual_template).
"""
from design_system.design_tokens import DesignTokens
from design_system.visual_policy import VisualPolicy
from design_system.visual_template import TEMPLATES, VisualTemplate


class DesignTokensError(Exception):
    """Template sem tokens registrados (fora do catálogo)."""


class DesignTokensEngine:
    """Produz o par (tokens, policy) de um VisualTemplate."""

    def generate(self, template: VisualTemplate) -> tuple[DesignTokens, VisualPolicy]:
        label = getattr(template, "id", template)
        if not isinstance(template, VisualTemplate):
            raise DesignTokensError(
                f"DESIGN_TOKENS_UNRESOLVED: template '{label}' "
                "fora do catálogo VS-2"
            )
        return template.build_tokens(), template.policy

    def tokens_for(self, template: VisualTemplate) -> DesignTokens:
        tokens, _ = self.generate(template)
        return tokens