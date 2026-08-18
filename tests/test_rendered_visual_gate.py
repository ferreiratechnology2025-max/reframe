"""
Testes do RenderedVisualGate (VS-0) — Playwright sobre HTML renderizado.

O gate comprova o que o token promete: contraste executado, CTA com o
accent real, sem overflow em 3 viewports, viewport meta, location (via
DOM data-component="location") e HTML fonte sem hex fora do bloco de tokens.
"""
import pytest
from playwright.sync_api import sync_playwright

from design_system.design_tokens import (
    ColorRole,
    DesignTokens,
    FontSpec,
    SemanticColor,
    TypographyPolicy,
)
from design_system.visual_policy import CATALOG, VisualPersonality, LocationPolicy, VisualPolicy
from gates.rendered_visual_gate import RenderedVisualGate

# HTML autocontido que MIMA a saída do template premium (mesma estrutura
# de tokens: :root + .cta-primary + seção de localização).
SAMPLE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clínica Dra. Andrielle Fernandes</title>
<style>
:root {
  {tokens}
}
body { margin: 0; background: var(--color-bg); color: var(--color-text); font-family: var(--font-body); }
.cta-primary {
  display: inline-block; padding: 0.9rem 2rem; border-radius: var(--radius-pill);
  background-color: var(--color-accent); color: var(--color-on-accent);
  font-weight: 600; text-decoration: none;
}
.section { padding: 4rem 1.5rem; }
[data-component="location"] { border-top: 1px solid var(--color-border); }
</style>
</head>
<body>
  <header class="section">
    <h1 style="font-family: var(--font-heading);">Clínica Dra. Andrielle Fernandes</h1>
    <a class="cta-primary" href="https://wa.me/5562999999999">Agendar avaliação</a>
  </header>
  <section class="section" data-component="location">
    <p>Setor Bueno · Goiânia</p>
    <a href="https://maps.google.com/?q=-16.7,-49.2">Como chegar</a>
  </section>
</body>
</html>"""


def build_tokens() -> DesignTokens:
    return DesignTokens(
        personality="premium_clinical",
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
        },
        semantic_colors={
            SemanticColor.SUCCESS: "#2E7D32",
            SemanticColor.WARNING: "#B26A00",
            SemanticColor.ERROR: "#C62828",
            SemanticColor.INFO: "#1565C0",
        },
        typography=TypographyPolicy(
            heading=FontSpec(family="Playfair Display", source="system", weights=[400]),
            body=FontSpec(family="Inter", source="system", weights=[400]),
        ),
    )


@pytest.fixture(scope="module")
def chromium_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def policy() -> VisualPolicy:
    return CATALOG[VisualPersonality.PREMIUM_CLINICAL]


@pytest.fixture
def html() -> str:
    return SAMPLE_HTML.replace("{tokens}", build_tokens().get_css_variables())


@pytest.fixture
def gate() -> RenderedVisualGate:
    return RenderedVisualGate()


class TestRenderedVisualGate:
    def test_clean_html_passes_all_viewports(self, gate, html, policy, chromium_browser):
        passed, issues = gate.validate(html, chromium_browser, policy, niche="estetica")
        assert passed, issues

    def test_location_not_required_outside_required_niche(self, gate, html, policy, chromium_browser):
        """Nicho fora da lista required_for_niches não exige location."""
        no_location = html.replace(
            '<section class="section" data-component="location">',
            "<section class=\"section\">",
        ).replace("Setor Bueno · Goiânia", "")
        passed, issues = gate.validate(no_location, chromium_browser, policy, niche="padaria")
        assert passed, issues

    def test_overflow_at_390_detected(self, gate, html, policy, chromium_browser):
        bad = html.replace("</head>", "<style>body { min-width: 1200px; }</style></head>")
        passed, issues = gate.validate(bad, chromium_browser, policy, niche="estetica")
        assert not passed
        assert any("overflow" in v.lower() for v in issues)

    def test_missing_viewport_meta_detected(self, gate, html, policy, chromium_browser):
        bad = html.replace(
            '<meta name="viewport" content="width=device-width, initial-scale=1">', ""
        )
        passed, issues = gate.validate(bad, chromium_browser, policy, niche="estetica")
        assert not passed
        assert any("viewport" in v.lower() for v in issues)

    def test_cta_not_using_accent_detected(self, gate, html, policy, chromium_browser):
        bad = html.replace("var(--color-accent)", "#CC0000")
        passed, issues = gate.validate(bad, chromium_browser, policy, niche="estetica")
        assert not passed
        assert any("cta" in v.lower() for v in issues)

    def test_missing_location_detected_when_required(self, gate, html, policy, chromium_browser):
        bad = html.replace(
            '<section class="section" data-component="location">', '<section class="section">'
        ).replace("Setor Bueno · Goiânia", "Conteúdo sem localização")
        passed, issues = gate.validate(bad, chromium_browser, policy, niche="estetica")
        assert not passed
        assert any("location" in v.lower() for v in issues)

    def test_raw_hex_in_source_detected(self, gate, html):
        bad = html.replace(
            "body { margin: 0; background: var(--color-bg);",
            "body { margin: 0; background: #FF0000;",
        )
        issues = gate.check_source_hex(bad)
        assert any("hex" in v.lower() for v in issues)

    def test_hex_inside_token_block_allowed(self, gate, html):
        assert gate.check_source_hex(html) == []

    def test_result_contract_is_tuple(self, gate, html, policy, chromium_browser):
        result = gate.validate(html, chromium_browser, policy, niche="estetica")
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], bool) and isinstance(result[1], list)