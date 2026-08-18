"""
RenderedVisualGate — prova visual do que os tokens prometem (VS-0).

Renderiza o HTML no Chromium e verifica, de verdade:
  - 3 viewports (1440 / 768 / 390) sem overflow horizontal;
  - meta viewport presente;
  - CTA com computed background == accent (contraste executado);
  - localização presente quando a política visual EXIGE (via DOM
    `[data-component="location"]` — nunca por objeto externo);
  - HTML fonte com hex SOMENTE dentro do bloco de tokens (hex limpo).

BeautifulSoup é usado apenas como validação estrutural auxiliar (nunca
como gate visual). Falha de gate = STOP; sem auto-repair.

Contrato de saída: (passed: bool, issues: List[str]).
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup

from design_system.design_tokens import DesignTokens
from design_system.visual_policy import VisualPolicy

DEFAULT_VIEWPORTS = [(1440, 900), (768, 1024), (390, 844)]

# Hex permitido APENAS dentro de declaração de variável: `--name: #hex;`
_CUSTOM_PROP_HEX = re.compile(
    r'--[a-zA-Z0-9-]+\s*:\s*#[0-9a-fA-F]{3,8}\s*;'
)
_ANY_HEX = re.compile(r'#[0-9a-fA-F]{3,8}')


class RenderedVisualGate:
    """Valida o HTML renderizado contra a promessa dos tokens."""

    def __init__(self, viewports: Optional[List[tuple[int, int]]] = None):
        self.viewports = viewports or DEFAULT_VIEWPORTS

    def validate(
        self,
        html: str,
        browser,
        policy: VisualPolicy,
        niche: Optional[str] = None,
        screenshot_dir: Optional[Path] = None,
    ) -> tuple[bool, List[str]]:
        """Valida o HTML renderizado.

        Localização é validada pelo DOM (data-component="location"),
        não por objeto externo.
        """
        issues: List[str] = []

        issues.extend(self.check_source_hex(html))
        issues.extend(self._check_structure(html))
        issues.extend(self._check_rendered(html, browser, policy, niche, screenshot_dir))

        return (not issues, issues)

    # ─── fonte (sem render) ─────────────────────────────────────────

    def check_source_hex(self, html: str) -> List[str]:
        """Hex no fonte é permitido apenas em declarações de variável."""
        issues: List[str] = []

        allowed = list(_CUSTOM_PROP_HEX.finditer(html))

        def _is_allowed(pos: int) -> bool:
            return any(m.start() <= pos < m.end() for m in allowed)

        for m in _ANY_HEX.finditer(html):
            if not _is_allowed(m.start()):
                snippet = html[max(0, m.start() - 30): m.end() + 10].replace("\n", " ")
                issues.append(f"hex fora do bloco de tokens: {m.group()} em '...{snippet}...'")
        return issues

    # ─── estrutura (BeautifulSoup — auxiliar) ───────────────────────

    def _check_structure(self, html: str) -> List[str]:
        issues: List[str] = []
        soup = BeautifulSoup(html, "html.parser")

        if soup.find("html") is None or soup.find("body") is None:
            issues.append("HTML sem estrutura html/body completa")

        if not soup.find("meta", attrs={"name": "viewport"}):
            issues.append("meta viewport ausente no <head>")

        if not soup.select(".cta-primary"):
            issues.append("elemento .cta-primary ausente no template")

        return issues

    # ─── render (Playwright) ────────────────────────────────────────

    def _check_rendered(
        self,
        html: str,
        browser,
        policy: VisualPolicy,
        niche: Optional[str],
        screenshot_dir: Optional[Path],
    ) -> List[str]:
        issues: List[str] = []
        page = browser.new_page()

        try:
            page.set_content(html, wait_until="networkidle")

            # 1) overflow horizontal por viewport
            for width, height in self.viewports:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(80)
                has_overflow = page.evaluate(
                    "() => document.documentElement.scrollWidth > window.innerWidth"
                )
                if has_overflow:
                    issues.append(f"overflow horizontal no viewport {width}x{height}")

            # 2) CTA com computed background == accent
            page.set_viewport_size({"width": 1440, "height": 900})
            bg = page.evaluate(
                """() => {
                    const el = document.querySelector('.cta-primary');
                    if (!el) return null;
                    return getComputedStyle(el).backgroundColor;
                }"""
            )
            if bg is None:
                issues.append("CTA não encontrado para leitura de cor")
            else:
                accent_rgb = self._token_value(html, "--color-accent")
                if accent_rgb is None:
                    issues.append("token --color-accent não encontrado no <style>")
                elif bg != accent_rgb:
                    issues.append(
                        f"CTA computado como {bg}, esperado {accent_rgb} (accent real)"
                    )

            # 3) localização exigida pela política visual (via DOM)
            if policy.location_policy.is_required(niche or ""):
                count = page.locator('[data-component="location"]').count()
                text = ""
                if count:
                    text = (page.locator('[data-component="location"]').inner_text() or "").strip()
                if count == 0 or not text:
                    issues.append(
                        "location exigida pela política visual mas ausente/vazia no DOM "
                        "(data-component=\"location\")"
                    )

            # 4) screenshots de evidência (opcional)
            if screenshot_dir:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                for width, height in self.viewports:
                    page.set_viewport_size({"width": width, "height": height})
                    page.wait_for_timeout(60)
                    page.screenshot(
                        path=str(screenshot_dir / f"viewport-{width}x{height}.png"),
                        full_page=True,
                    )

        finally:
            page.close()

        return issues

    @staticmethod
    def _token_value(html: str, var_name: str) -> Optional[str]:
        m = re.search(
            rf'{re.escape(var_name)}\s*:\s*(#[0-9a-fA-F]{{6}})',
            html.replace("\n", " "),
        )
        if not m:
            return None
        h = m.group(1)
        r = int(h[1:3], 16)
        g = int(h[3:5], 16)
        b = int(h[5:7], 16)
        return f"rgb({r}, {g}, {b})"