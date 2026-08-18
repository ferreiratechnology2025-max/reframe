# EVIDENCE ROBUSTNESS + DETERMINISM SLICE — RELATÓRIO

Prova de robustez sob variação de evidência e determinismo do Design System, **preservando o contrato VS-0** (posicionamento fixo por nicho; evidência é contexto, não modificador). Data: 2026-08-17.

## 1. AJUSTES REALIZADOS

- [x] Fixtures usam os contratos reais (`design_system.location`, `design_system.positioning`, `design_system.visual_policy`) — não os módulos antigos citados no prompt original (`models.*`, `enums.*`).
- [x] Testes de refinamento por evidência **marcados como skip** com nota `VS-1: evidence-driven positioning refinement` — capability ainda não existe e exigiria mudança de pipeline (fora de escopo).
- [x] Determinismo comprovado: tokens gerados ANTES do LLM, independentes de copy/provider/temperatura.

**Resolução de conflito:** o prompt original esperava `rating 4.2 → NATURAL` e `especialidade não premium → NATURAL`. Isso contradiz o mapeamento fixo ratificado (VS-0/VS-0.1: `estetica → PREMIUM` independente de evidência, reforçado por `test_evidence_param_does_not_change_vs0_mapping`). Decidido: preservar o contrato e registrar o refinamento como VS-1.

## 2. TESTES

- Suíte completa: **194 passando** (1 falha transiente de LLM 503 durante a execução; passou no retry)
- Novos testes: **7 passando** (4 robustez + 3 determinismo)
- Skipped (VS-1): **1**

Arquivos novos:
- `tests/conftest.py` — fixtures `complete_evidence`, `minimal_evidence`, `location_unverified`
- `tests/test_evidence_robustness.py` — evidência completa/mínima não quebram; nicho não mapeado falha com/sem evidência; localização ausente não quebra o pipeline
- `tests/test_determinism.py` — mesmos tokens entre execuções; LLM não afeta tokens; todas as personalidades passam no gate

## 3. STATUS

- Robustez: **COMPROVADA** — evidência varia, decisão permanece determinística; falha estruturada para nicho não mapeado
- Determinismo: **COMPROVADO** — mesma personalidade → mesmos tokens, sempre
- Commit: `VS-0.2: Evidence Robustness + Determinism Slice (contrato VS-0 preservado)`
- Pronto para VS-1: **SIM** — o teste `test_evidence_refines_positioning` (skip) define o alvo; a arquitetura não muda, só o `POSITIONING_MAP` passa a considerar evidência
