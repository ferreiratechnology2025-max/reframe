# VS-2 — RELATÓRIO DE IMPLEMENTAÇÃO

**Data:** 2026-08-18
**Slice:** VS-2 — Reusable Visual Templates (Expansão Visual desacoplada)
**Base:** VS-1 (`b153801`)

## Resumo

VS-2 desacopla a seleção visual do nicho. O fluxo passa a ser:

`Evidence → EvidencePositioningEngine → MarketPosition → VisualThemeResolver (POSITION_TEMPLATE_MAP, position-only) → VisualTemplate → DesignTokensEngine → DesignTokenGate`

**Propriedade central:** ∀ nicho₁, nicho₂: position(nicho₁) = position(nicho₂) ⇒ template(nicho₁) = template(nicho₂).

O nicho NÃO participa da resolução visual: o resolver conhece apenas `MarketPosition`. Nichos novos (`novo_nicho`, `qualquer_coisa`) reutilizam templates existentes sem código novo.

## NOVAS PERSONALIDADES (templates)

O catálogo fechado passou de 3 para **7 templates**:

| Template | Posição | Novos (VS-2) |
|---|---|---|
| PREMIUM_CLINICAL | PREMIUM | — |
| PERFORMANCE_RESULT | PERFORMANCE | — |
| BOLD_URBAN | (referência) | — |
| **NATURAL_ELEGANT** | NATURAL | sim |
| **LUXURY_MINIMAL** | LUXURY | sim |
| **MODERN_TECH** | MODERN | sim |
| **ORGANIC_WARM** | TRADITIONAL | sim |

BOLD_URBAN permanece no catálogo como referência visual, mas **não** está no
mapa ativo: MODERN resolve para MODERN_TECH (decisão congelada).

## TOKENS ADICIONADOS

| Template | bg | accent | on_accent | contraste accent |
|---|---|---|---|---|
| NATURAL_ELEGANT | `#F7F5F0` | `#7A8B6F` | `#FFFFFF` | 3.65:1 ✓ |
| LUXURY_MINIMAL | `#111111` | `#C9A96A` | `#111111` | 8.42:1 ✓ |
| MODERN_TECH | `#FFFFFF` | `#00E5FF` | `#0A1931` | 11.41:1 ✓ |
| ORGANIC_WARM | `#E8E6D9` | `#A97C50` | `#F5F3EC` | 3.33:1 ✓ |

Todos os 7 templates passam no DesignTokenGate (WCAG AA: texto ≥4.5:1,
accent/on_accent ≥3.0:1). Tipografia: Playfair/Cormorant Garamond + Inter
(sage/orgânico/luxo) e Inter + Inter (tech).

## MAPEAMENTOS

`POSITION_TEMPLATE_MAP` (position-only, em `engines/theme_resolver.py`):

| Posição | Template |
|---|---|
| PREMIUM | PREMIUM_CLINICAL |
| PERFORMANCE | PERFORMANCE_RESULT |
| NATURAL | NATURAL_ELEGANT |
| LUXURY | LUXURY_MINIMAL |
| TRADITIONAL | ORGANIC_WARM |
| MODERN | MODERN_TECH |

Arquivos novos: `design_system/visual_template.py` (VisualTemplate + 7
templates), `tests/test_visual_template.py` (contrato congelado).
`design_system/visual_policy.py` perdeu `VisualPersonality`/`CATALOG`
(`personality` virou `str`); `DesignTokensEngine.generate(template)`.

## TESTES

- **279 testes passando** (antes 242 + 6 E2E). Inclui novo contrato:
  - teste mandatório: `resolve(niche, NATURAL).id == "NATURAL_ELEGANT"` para
    `["estetica","academia","barbearia","novo_nicho","qualquer_coisa"]`;
  - propriedade central (posição igual → template igual, qualquer nicho);
  - reuso: `novo_nicho`/`qualquer_coisa` resolvem sem código novo;
  - gate: 7 templates passam no DesignTokenGate.
- **E2E (credenciais reais): 8/8 passando** — 5 publicados (estetica PREMIUM,
  estetica NATURAL, academia PERFORMANCE, academia NATURAL, barbearia LUXURY),
  1 bloqueio (UNDETERMINED), 1 reuso cross-nicho (estetica NATURAL == academia
  NATURAL → NATURAL_ELEGANT) + determinismo de tokens.
- `rg "if niche"` no código de resolução: vazio (resolver não conhece nicho).
- `api/test_pipeline.py::test_pipeline` falha pré-existente (async sem await),
  presente também na base — não é regressão.

## STATUS

**Concluído.** Commit proposto: `VS-2: Reusable Visual Templates - position → template desacoplado`.
