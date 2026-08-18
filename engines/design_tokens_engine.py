"""
DesignTokensEngine — gera (DesignTokens, VisualPolicy) de uma personalidade (VS-0).

Determinístico e baseado em política: tokens NUNCA são gerados por LLM.
Catálogo fechado: apenas PREMIUM_CLINICAL.
"""
from design_system.design_tokens import (
    ColorRole,
    DesignTokens,
    FontSpec,
    SemanticColor,
    TypographyPolicy,
)
from design_system.visual_policy import CATALOG, VisualPersonality, VisualPolicy


class DesignTokensError(Exception):
    """Personalidade sem política de tokens registrada."""


class DesignTokensEngine:
    """Produz o par (tokens, policy) de uma personalidade visual."""

    def generate(self, personality: VisualPersonality) -> tuple[DesignTokens, VisualPolicy]:
        label = getattr(personality, "value", personality)
        policy = CATALOG.get(personality)
        if policy is None:
            raise DesignTokensError(
                f"DESIGN_TOKENS_UNRESOLVED: personalidade '{label}' "
                "fora do catálogo VS-0"
            )
        return self._tokens_for(personality), policy

    def tokens_for(self, personality: VisualPersonality) -> DesignTokens:
        tokens, _ = self.generate(personality)
        return tokens

    @staticmethod
    def _tokens_for(personality: VisualPersonality) -> DesignTokens:
        builder = DesignTokensEngine._BUILDERS.get(personality)
        if builder is None:
            label = getattr(personality, "value", personality)
            raise DesignTokensError(
                f"DESIGN_TOKENS_UNRESOLVED: personalidade '{label}' "
                "fora do catálogo VS-0"
            )
        return builder()

    @staticmethod
    def _premium_clinical() -> DesignTokens:
        return DesignTokens(
            personality=VisualPersonality.PREMIUM_CLINICAL.value,
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
            semantic_colors={
                SemanticColor.SUCCESS: "#2E7D32",
                SemanticColor.WARNING: "#B26A00",
                SemanticColor.ERROR: "#C62828",
                SemanticColor.INFO: "#1565C0",
            },
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
            spacing={
                "xs": "0.5rem",
                "sm": "1rem",
                "md": "1.5rem",
                "lg": "2.5rem",
                "xl": "4rem",
            },
            radius={
                "sm": "0.375rem",
                "md": "0.625rem",
                "lg": "1rem",
                "pill": "9999px",
            },
            shadows={
                "sm": "0 1px 2px rgba(26, 26, 26, 0.06)",
                "md": "0 6px 24px rgba(26, 26, 26, 0.08)",
                "lg": "0 12px 48px rgba(26, 26, 26, 0.12)",
            },
        )

    @staticmethod
    def _performance_result() -> DesignTokens:
        return DesignTokens(
            personality=VisualPersonality.PERFORMANCE_RESULT.value,
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
            semantic_colors={
                SemanticColor.SUCCESS: "#2E7D32",
                SemanticColor.WARNING: "#B26A00",
                SemanticColor.ERROR: "#C62828",
                SemanticColor.INFO: "#1565C0",
            },
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
            spacing={
                "xs": "0.5rem",
                "sm": "1rem",
                "md": "1.5rem",
                "lg": "2.5rem",
                "xl": "4rem",
            },
            radius={
                "sm": "0.375rem",
                "md": "0.625rem",
                "lg": "1rem",
                "pill": "9999px",
            },
            shadows={
                "sm": "0 1px 2px rgba(26, 26, 26, 0.06)",
                "md": "0 6px 24px rgba(26, 26, 26, 0.08)",
                "lg": "0 12px 48px rgba(26, 26, 26, 0.12)",
            },
        )

    @staticmethod
    def _bold_urban() -> DesignTokens:
        return DesignTokens(
            personality=VisualPersonality.BOLD_URBAN.value,
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
            semantic_colors={
                SemanticColor.SUCCESS: "#2E7D32",
                SemanticColor.WARNING: "#B26A00",
                SemanticColor.ERROR: "#C62828",
                SemanticColor.INFO: "#1565C0",
            },
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
            spacing={
                "xs": "0.5rem",
                "sm": "1rem",
                "md": "1.5rem",
                "lg": "2.5rem",
                "xl": "4rem",
            },
            radius={
                "sm": "0.375rem",
                "md": "0.625rem",
                "lg": "1rem",
                "pill": "9999px",
            },
            shadows={
                "sm": "0 1px 2px rgba(0, 0, 0, 0.25)",
                "md": "0 6px 24px rgba(0, 0, 0, 0.35)",
                "lg": "0 12px 48px rgba(0, 0, 0, 0.45)",
            },
        )

    _BUILDERS = {
        VisualPersonality.PREMIUM_CLINICAL: _premium_clinical,
        VisualPersonality.PERFORMANCE_RESULT: _performance_result,
        VisualPersonality.BOLD_URBAN: _bold_urban,
    }