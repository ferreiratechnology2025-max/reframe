# RELATÓRIO DE ACESSIBILIDADE — Reframe pós-VS-2

Data: 2026-08-18 · Base: `8f919df` (VS-2) + README atualizado (`0613868`)

---

## 1. UI React — /leads, /leads/new, /generation/new, /generation/:id

**Status: FUNCIONAL**

- `npm run build` (ai-ui-shell): **ok** — Vite 7, 1836 módulos, bundle único de 375 kB (gzip 108 kB) em `dist/index.html`.
- Rotas presentes e conectadas à API real (`src/projects/reframe/api/reframeApi.ts`): Leads, NewLead, GenerationTracker (3 fluxos: URL direta com generationId, novo fluxo com leadId, sem parâmetro → erro amigável).
- API alcançável a partir do front: CORS liberado para `http://localhost:5173` (dev), `localhost:3000` e `localhost:4000` (`api/app.py:15-25`).
- URL da API configurável via `VITE_REFRAME_API_URL` (default `http://localhost:8000`); `.env` do shell já aponta para a porta 8000.
- Teste real executado: `GET /api/health` e `POST /api/leads` responderam; o lead criado pelo mesmo contrato que a UI usa retornou com id normalizado.
- Observação: o `vite.config.ts` **não** tem proxy de dev configurado — o front chama a API diretamente na origem; funcionou porque a API tem CORS. Se um dia a UI subir em outra origem/porta, é preciso adicionar a origem no CORS da API.

## 2. CLI — python main.py

**Status: PARCIAL (não é um CLI com flags)**

- **O prompt assumia flags que não existem**: `main.py` NÃO tem `argparse`/`--name`/`--niche`/`--city`/`--place_id`/`--batch`. Busca por `argparse|add_argument|sys.argv` em `main.py` retorna vazio.
- Realidade: `main()` (main.py:441) executa **uma simulação fixa de 3 leads hardcoded** (Padaria Central, Oficina do João, Empresa Fantasma) através do caminho **legacy** `process_lead` (que ainda usa `get_archetype_or_fail`/10 arquétipos).
- O novo fluxo VS-0→VS-2 é acessado programaticamente por `main.py::generate_landing` (função assíncrona exportável), não por linha de comando.
- Scripts de lote existem como módulos, não como subcomando CLI: `python api/generate_batch.py` (10 leads) e `python api/generate_adversarial_batch.py` (variações linguísticas/casos extremos).
- ⚠️ Inconsistência detectada: os `BATCH_LEADS` desses scripts usam nichos do catálogo legacy (padaria, restaurante, mecânica, salão, confeitaria, pet shop, loja de roupas, farmácia). Após o VS-1/VS-2, o catálogo comercial fechou em **3 nichos** (`estetica`, `academia`, `barbearia` — `design_system/evidence_positioning.py:28`). Rodar esses batches hoje produzirá `POSITIONING_UNDETERMINED` para a maioria dos leads. Os scripts não foram atualizados para o catálogo VS-1/VS-2.

## 3. API — api/app.py (FastAPI, :8000)

**Status: FUNCIONAL**

- `GET /api/health` → `{"status": "ok"}` (verificado ao vivo).
- `GET /api/project` → info do projeto (verificado ao vivo).
- `POST /api/leads` → cria lead com id `lead_{hex}` (verificado ao vivo).
- Contrato real de geração: `POST /api/generations` recebe **`{"lead_id": ...}`** (não `business_name/niche/city/whatsapp/place_id` como o prompt sugeria). A UI já segue o contrato real: `createLead` → depois `createGeneration(lead_id)`.
- Geração roda em background (`run_pipeline_task`), com status `queued → generating → … → published/failed` e campos `archetype_name`, `primary_color`, `hero_image`, `url`, `error`.
- Erros estruturados: 404 para lead/geração inexistente; 400 com `ErrorCode.INVALID_LEAD` + campos inválidos.
- Observação: store in-memory (MVP) — reiniciar a API perde leads/gerações. Documentado como limitação conhecida no README.

## 4. Landing pages — publicação R2

**Status: FUNCIONAL (evidência E2E real)**

- E2E real (`tests/test_vs0_e2e.py`): **8/8 passando com credenciais reais** — 5 publicados em R2, 1 bloqueado por posição indeterminada, reuso cross-nicho (estetica/academia → NATURAL_ELEGANT), determinismo (mesmo lead → mesmo output).
- Validação visual: `DesignTokenGate` + `RenderedVisualGate` (gates/) verificam contraste e o render antes de publicar.
- Suíte completa: **279 testes passando** (confirmado em execução recente, 97s).

## 5. README.md

**Status: FUNCIONAL (atualizado e commitado)**

- Reescrito para o estado pós-VS-2 e commitado (`0613868`):
  - Diagrama de arquitetura novo: Evidence → Positioning → Theme Resolver (POSITION_TEMPLATE_MAP) → Design Tokens → Gates → LLM copy → Render → Publish.
  - Capacidades por slice (VS-0, VS-0.1, VS-0.2, VS-1, VS-2) com detalhes de templates e posições mapeadas.
  - CLI real documentado (simulação fixa, sem flags; `generate_landing` como interface programática).
  - Endpoints da API documentados com contratos reais (inclui `POST /api/generations {lead_id}`).
  - Estrutura de diretórios corrigida (`design_system/`, `engines/`, `gates/`, `api/`).
  - Encoding/acentuação corrigidos.
  - Limitações conhecidas atualizadas (catálogo de 3 nichos, store in-memory, CLI sem flags, batches desatualizados).

---

## Acessibilidade ao usuário — resumo executivo

| Área | Status | Nota |
|---|---|---|
| UI React (4 rotas) | ✅ FUNCIONAL | build ok, CORS ok, contrato real com API |
| CLI | ⚠️ PARCIAL | não há flags; simulação fixa; batches usam nichos fora do catálogo |
| API | ✅ FUNCIONAL | health/project/leads verificados ao vivo |
| Landing pages | ✅ FUNCIONAL | E2E real 8/8, 5 publicados, gates visuais ativos |
| README | ✅ FUNCIONAL | atualizado e commitado |

**Ações recomendadas (não bloqueantes):**
1. Atualizar `BATCH_LEADS`/`ADVERSARIAL_LEADS` para os 3 nichos comerciais do catálogo VS-1/VS-2 (ou remover o catálogo legacy de `config/archetypes.py`), senão os scripts de validação falham em massa.
2. Se quiser um CLI de verdade (`--name --niche --batch`), implementar `argparse` no `main.py` — hoje o único caminho programático é `generate_landing`/API.