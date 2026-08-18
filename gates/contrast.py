"""
Contraste WCAG (a11y) — utilidade compartilhada pelos gates (VS-0).
"""
import re
from typing import Tuple

_HEX = re.compile(r'^#([0-9a-fA-F]{6})$')


def _rgb(hex_color: str) -> Tuple[float, float, float]:
    m = _HEX.match((hex_color or "").strip())
    if not m:
        raise ValueError(f"Cor não é hex válido: {hex_color!r}")
    value = m.group(1)
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _linearize(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = (_linearize(c) for c in _rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """Contraste WCAG 2.x entre duas cores hex (>= 1.0)."""
    l1, l2 = relative_luminance(hex_a), relative_luminance(hex_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)