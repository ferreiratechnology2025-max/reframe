# VS-1 — RELATÓRIO DE IMPLEMENTAÇÃO (CORRIGIDO)

**Data:** 2026-08-18
**Contrato:** SPEC VS-1 FINAL — Evidence-Driven Positioning (congelada)
**Escopo:** Opção A — Engine fiel à matriz + catálogo visual fechado

## 1. ESPECIALIDADES COM PRIORIDADE

- [x] `SPECIALTY_PRIORITY` implementado (design_system/evidence_positioning.py)
- [x] `_resolve_by_specialty` usa prioridade, NÃO ordem da lista
- [x] Teste de invariância: permutações → mesma posição
  (`tests/test_evidence_positioning.py::TestSpecialtyPriority`)
- [x] Prioridade estendida para cobrir também LUXURY/TRADITIONAL/MODERN
  (barbearia), preservando determinismo em todo o conjunto suportado

## 2. MATRIZ IMPLEMENTADA

- [x] estetica: PREMIUM/NATURAL/PERFORMANCE (specialty + rating/volume)
- [x] academia: PERFORMANCE/MODERN/NATURAL (specialty + rating/volume)
- [x] barbearia: LUXURY/TRADITIONAL/MODERN (specialty + rating/volume)
- [x] `MarketPosition.LUXURY` e `MarketPosition.TRADITIONAL` adicionados
- [x] `CommercialEvidence` estruturado: `rating`, `total_ratings`, `specialties`
- [x] `COMMERCIAL_PROFILES` por (nicho, posição) — value/tone/audience

## 3. FIXTURES

- [x] estetica: `["facial", "injetáveis"]` → PREMIUM (prioridade PREMIUM > NATURAL)
- [x] barbearia: `["corte clássico", "barba"]` → LUXURY → THEME_UNRESOLVED (bloqueio)
- [x] barbearia E2E: `specialties=[]` → MODERN → publicado (rating 4.9/891)
- [x] academia: `["musculação", "funcional"]` → PERFORMANCE (sem specialty match → rating)

## 4. COMPORTAMENTO DE BLOQUEIO

- [x] `UNDETERMINED` → `POSITIONING_UNDETERMINED` (pipeline para)
- [x] Posição sem personalidade → `THEME_UNRESOLVED` (sem fallback silencioso)
- [x] E2E LUXURY barbearia → bloqueio documentado
  (`test_vs0_e2e_luxury_barbearia_blocks_without_publishing`)

## 5. TESTES

- [x] Refinamento por especialidade: passando
- [x] Refinamento por rating/volume: passando
- [x] Evidência ausente → base (robustez VS-0.2 preservada): passando
- [x] UNDETERMINED → bloqueio: passando
- [x] THEME_UNRESOLVED → bloqueio: passando
- [x] Determinismo com evidência variável: passando
- [x] Invariância de ordem de especialidades: passando
- [x] Skip de `test_evidence_refines_positioning` removido (VS-0.2 → VS-1)
- [x] Suíte completa (não-E2E): **242/242 passando**
- [x] E2E (LLM+R2 reais): 6/6 passando em retry (falhas transientes 503/timeout
  do provider `agnes-ai.com`, sem relação com o slice — ver VS-0.2)

## 6. NOTAS DE CONTRATO

- Localização/website: removidos do VS-1 (fora de escopo, como decidido).
- `UNDETERMINED` e `THEME_UNRESOLVED` são estados distintos e independentes.
- Nenhum `if niche` no engine — tudo via dados (SUPPORTED_POSITIONS,
  REFINEMENT_RULES, COMMERCIAL_PROFILES). `rg "if niche"` vazio.
- `engines/positioning_engine.py` (VS-0.x fixo) permanece como âncora
  (`POSITIONING_MAP` é consumido pelo novo engine) e os testes de contrato
  VS-0/VS-0.1/VS-0.2 seguem verdes.

## 7. STATUS

- VS-1: COMPLETO
- Commit: (ver hash abaixo)
- Pronto para VS-2 (expansão visual — 6 novas personalidades): SIM