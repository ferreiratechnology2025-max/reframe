# Reframe — Pipeline de Geração de Landing Pages B2C

Pipeline automatizado que transforma leads de negócios locais em landing pages estáticas publicadas no Cloudflare R2, com perspectiva **B2C** (venda para o consumidor final, não para o dono do negócio).

---

## Status do Projeto

**Arquitetura pós-VS-2 (Reusable Visual Templates) — modo commercial validation.** O ciclo de engineering validation (VS-0 → VS-2) está encerrado: pipeline testado com **279 testes passando** (incluindo E2E 8/8 com credenciais reais). O próximo passo é um piloto comercial pequeno (10–20 negócios reais) para medir se dono de negócio paga pela landing.

| Área | Status |
|---|---|
| Design System Engine (evidence → positioning → tema → tokens) | ✅ |
| Visual Templates reutilizáveis (position → template desacoplado) | ✅ |
| Determinismo (mesmo lead → mesmo output) | ✅ |
| Identidade e publicação (slug, colisão, URL, R2) | ✅ |
| Integridade semântica (evidence integrity gate) | ✅ |
| Quality Gate visual (contrast + rendered visual gate) | ✅ |
| Classificação estruturada de erros | ✅ |
| UI React (leads, geração, tracker) | ✅ (build OK, local) |
| Enriquecimento com Google Places | ✅ (opcional, requer API key) |
| Validação comercial (conversão real) | ⏳ Pendente |

---

## Visão Geral

```
Lead (nome, nicho, cidade, telefone, place_id opcional)
    ↓
Evidence-Driven Positioning (determinístico, por nicho)
    ↓
Theme Resolver (MarketPosition → VisualTemplate via POSITION_TEMPLATE_MAP)
    ↓
Design Tokens Engine (template → tokens: cor, tipografia, raio, densidade)
    ↓
DesignTokenGate (bloqueia token que viola o template)
    ↓
LLM gera copy (somente copy; posicionamento/tema/tokens são determinísticos)
    ↓
Evidence Integrity Gate (bloqueia distorção de fatos)
    ↓
Render (template + tokens) → RenderedVisualGate
    ↓
Publicação Cloudflare R2
    ↓
https://propostas.api-plataforma.com/{slug}
```

**Princípio-chave (VS-2):** o LLM escreve **somente a copy**. Posicionamento, tema visual e tokens são decisões determinísticas do Design System Engine. O template visual é resolvido pela **posição de mercado** (não pelo nicho em si), permitindo que o mesmo template sirva negócios de nichos diferentes com a mesma posição.

---

## Arquitetura

```
UI (React + TypeScript, ai-ui-shell/)  ── CORS: localhost:5173/3000/4000
    ↓ HTTP (VITE_REFRAME_API_URL, default http://localhost:8000)
API (FastAPI, api/app.py)
    ↓
PipelineAdapter (api/pipeline_adapter.py)
    ↓
┌──────────────────────────────────────────────────────────────┐
│ generate_landing (main.py) — orquestração (VS-0)             │
│  1. EvidenceCollection  (evidência real, se houver place_id) │
│  2. EvidencePositioningEngine  (nicho → MarketPosition)      │
│  3. ThemeResolver  (POSITION_TEMPLATE_MAP → VisualTemplate)  │
│  4. DesignTokensEngine  (template → DesignTokens)            │
│  5. DesignTokenGate  (valida contraste/restrições)           │
│  6. LLM Copy  (Agnes → Gemini fallback)                      │
│  7. Evidence Integrity Gate  (bloqueia distorção)            │
│  8. Render (templates/) + RenderedVisualGate                 │
│  9. Publish (R2)                                             │
└──────────────────────────────────────────────────────────────┘
    ↓
Landing pública: https://propostas.api-plataforma.com/{slug}
```

`main.py::generate_landing` é o ponto de entrada único, reusado tanto pela API (via `pipeline_adapter.py`) quanto pelos batch scripts.

---

## Stack

| Camada | Tecnologia |
|---|---|
| **LLM primário** | Agnes (`agnes-2.0-flash`, API OpenAI-compatible) |
| **LLM fallback** | Gemini (`gemini-flash-latest`) — Ollama local também suportado |
| **Evidências comerciais** | Google Places API (New) v1 — opcional |
| **Template** | Jinja2 + Tailwind CSS |
| **Storage** | Cloudflare R2 (S3-compatible, via boto3) |
| **Domínio** | `propostas.api-plataforma.com` |
| **API** | FastAPI (`api/`) |
| **UI** | React 19 + TypeScript + Vite 7 + Tailwind 4 (`ai-ui-shell/`) |
| **Validação** | Pydantic v2 |
| **Testes** | pytest (279 passando) |

---

## Capacidades

### Implementadas (por slice)

- **VS-0 — Design System Engine**: contrato `VisualPolicy`/`VisualTemplate`/`DesignTokens`, desacoplamento do legacy; `generate_landing` como orquestrador único; tokens CSS gerados deterministicamente.
- **VS-0.1 — Generalização**: cobertura para `academia` e `barbearia` além de `estetica`, via dados/mapeamentos (não hardcode).
- **VS-0.2 — Evidence Robustness + Determinism**: mesmo lead → mesmo output; falha estável e identificável para nicho/posição não mapeados.
- **VS-1 — Evidence-Driven Positioning**: `EvidencePositioningEngine` fiel à matriz de posicionamento (3 nichos comerciais: **estetica, academia, barbearia**); nicho fora do catálogo → `POSITIONING_UNDETERMINED`, nunca aproximado.
- **VS-2 — Reusable Visual Templates**: **position → template desacoplado**. `POSITION_TEMPLATE_MAP` (6 posições → 7 templates, em `engines/theme_resolver.py`). O mesmo template visual serve nichos diferentes; templates são independentes de nicho. Contraste validado por `DesignTokenGate` + `RenderedVisualGate` visual.

**Detalhes do VS-2:**
- 7 templates visuais em `design_system/visual_template.py`; 6 posições mapeadas em `POSITION_TEMPLATE_MAP` (`PREMIUM→PREMIUM_CLINICAL`, `PERFORMANCE→PERFORMANCE_RESULT`, `NATURAL→NATURAL_ELEGANT`, `LUXURY→LUXURY_MINIMAL`, `TRADITIONAL→ORGANIC_WARM`, `MODERN→MODERN_TECH`).
- Determinismo comprovado em E2E (mesmo lead → mesmo output).
- Reuso cross-nicho comprovado em E2E: posição `NATURAL` em estetica e academia → mesmo template `NATURAL_ELEGANT`.

### Adicionais (anteriores ao Design System)

- **Geração B2C**: copy focada no consumidor final; proibido vocabulário de gestão/negócio.
- **Fallback de LLM com retry**: até 3 tentativas, trocando de provedor e temperatura antes de desistir.
- **Normalização de output**: trunca campos que excedem limites mecânicos em vez de rejeitar a geração inteira.
- **Validação Pydantic**: schema rígido em toda a fronteira LLM → template.
- **Enriquecimento com Google Places**: horário, avaliação e site oficial viram `CommercialEvidence` real, injetada no prompt como única fonte de fatos específicos.
- **Evidence Integrity Gate**: bloqueia distorções da copy contra as evidências (troca de entidade, arredondamento, inferência não fundamentada).
- **Identidade de publicação**: slugs determinísticos (`nome-hash`), DNS-safe, com proteção contra colisão no R2.
- **Classificação estruturada de erros**: códigos estáveis (`api/errors.py`) distinguem retryable de não-retryable.
- **Alertas**: notificação via Telegram em falhas críticas.

### Pendentes (próximo ciclo)

- **Validação comercial**: ainda não medimos se as landings geram conversão real (cliques no WhatsApp, taxa de resposta).
- **Google Places em uso ativo por leads reais**: a integração funciona, mas depende do fluxo de captação real trazer `place_id`.
- **Cobertura de nichos**: apenas 3 nichos comerciais mapeados (estetica, academia, barbearia); qualquer outro é recusado com código estável, não aproximado.

---

## Como rodar

### Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # preencha as credenciais
```

### CLI — simulação de leads

```bash
python main.py
```

Roda a simulação de 3 leads hardcoded (Padaria Central, Oficina do João, Empresa Fantasma) através do pipeline legacy. **Não há CLI com flags** (`--name`, `--niche`, `--batch` não existem): a interface programática é a função `generate_landing` ou a API.

### API

```bash
python api/run.py      # http://localhost:8000
```

Endpoints (CORS liberado para localhost:5173/3000/4000):

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Info + lista de endpoints |
| GET | `/api/health` | Health check |
| GET | `/api/project` | Info do projeto |
| GET | `/api/r2/test` | Diagnóstico de conexão R2 |
| GET | `/api/leads` | Lista leads |
| POST | `/api/leads` | Cria lead — body `{name, niche, city, phone, place_id?}` |
| GET | `/api/leads/{id}` | Detalhe do lead |
| GET | `/api/generations` | Lista gerações |
| POST | `/api/generations` | Cria geração (background) — body `{lead_id}` |
| GET | `/api/generations/{id}` | Status da geração (`queued → generating → … → published/failed`) |

### UI

```bash
cd ai-ui-shell
npm install
npm run dev          # http://localhost:5173
```

Rotas: `/leads`, `/leads/new`, `/generation/new?lead={id}`, `/generation/{id}`. A URL da API é configurada em `ai-ui-shell/.env`:

```env
VITE_REFRAME_API_URL=http://localhost:8000
```

### Batch scripts (validação)

```bash
python api/generate_batch.py              # 10 leads de exemplo
python api/generate_adversarial_batch.py  # variações linguísticas, nichos similares e casos extremos
```

---

## Testes

```bash
pytest tests/ -v
```

**279 testes passando.** A suíte cobre:

- Design System Engine (evidence → positioning → tema → tokens → gates).
- Determinismo VS-0.2 (mesmo input → mesmo output).
- Generalização VS-0.1 (academia, barbearia).
- Evidence-Driven Positioning VS-1 (matriz, falha estável `POSITIONING_UNDETERMINED`).
- Reuso de templates VS-2 (position → template).
- Normalização/validação Pydantic, classificação de erros, identidade/slug, Google Places, integridade de evidência, publisher/R2.
- **E2E real** (`tests/test_vs0_e2e.py`): 8/8 com credenciais reais — 5 publicados, 1 bloqueio por posição indeterminada, reuso cross-nicho, determinismo.

> Dois testes em `api/` (`test_e2e_real.py`, `test_pipeline.py`) são `async def` e exigem `pytest-asyncio`; sem o plugin, o `pytest` os reporta como falha de coleta. `api/test_pipeline.py::test_pipeline` é falha **pré-existente** (async chamado sem `await`), confirmada também na base anterior ao VS-2 — não é regressão.

---

## Configuração

### Backend (`.env`, ver `.env.example`)

```env
# LLM
PRIMARY_LLM=agnes           # ollama | gemini | agnes
FALLBACK_LLM=gemini
AGNES_API_KEY=
AGNES_BASE_URL=https://apihub.agnes-ai.com/v1
AGNES_MODEL=agnes-2.0-flash
GEMINI_API_KEY=
GEMINI_MODEL=gemini-flash-latest
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# Cloudflare R2 (S3-compatible)
CLOUDFLARE_ACCOUNT_ID=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_ENDPOINT=https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com
R2_BUCKET=leads-sites
ROOT_DOMAIN=propostas.api-plataforma.com

# Google Places (opcional - sem ela, evidência fica vazia e o LLM
# é instruído a não inventar fatos comerciais)
GOOGLE_PLACES_API_KEY=

# Alertas (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### Frontend (`ai-ui-shell/.env`)

```env
VITE_REFRAME_API_URL=http://localhost:8000
```

---

## Estrutura

```
Reframe/
├── main.py                       # Orquestrador generate_landing (VS-0) + legacy process_lead
├── models.py                     # Schemas Pydantic (BusinessData, CommercialEvidence, CopyData...)
├── llm_provider.py               # Dispatch Agnes/Gemini/Ollama + prompt B2C + evidence integrity
├── validate_evidence_integrity.py # Validador estruturado de integridade de evidências
├── google_places.py               # Enriquecimento via Google Places API (New) v1
├── publisher.py                   # Upload para R2 (boto3)
├── design_system/                 # Contratos do Design System Engine (VS-0 → VS-2)
│   ├── positioning.py             #   MarketPosition
│   ├── evidence_positioning.py    #   Evidência → posição (matriz VS-1, 3 nichos)
│   ├── visual_template.py         #   VisualTemplate (7 templates, VS-2)
│   ├── visual_policy.py           #   VisualPolicy (personality = template id)
│   ├── design_tokens.py           #   DesignTokens (cor, tipografia, raio, densidade)
│   └── location.py                #   BusinessLocation
├── engines/                       # Lógica determinística do Design System
│   ├── positioning_engine.py      #   Posicionamento por evidência/nicho
│   ├── theme_resolver.py          #   POSITION_TEMPLATE_MAP (position → template, VS-2)
│   └── design_tokens_engine.py    #   Template → tokens
├── gates/                         # Gates de qualidade
│   ├── contrast.py                #   Contraste de cores
│   ├── design_token_gate.py       #   Bloqueia token que viola o template
│   └── rendered_visual_gate.py    #   Valida o visual renderizado
├── config/archetypes.py           # Arquétipos legacy (10 nichos, caminho process_lead)
├── templates/premium.html         # Template Jinja2 (Tailwind, hero via inline style)
├── api/
│   ├── app.py                     # FastAPI (leads, generations, health, r2/test)
│   ├── pipeline_adapter.py        # Adapta main.generate_landing à API + classificação de erro
│   ├── errors.py                  # Códigos de erro estáveis, retryable/não-retryable
│   ├── run.py                     # uvicorn (porta 8000)
│   ├── generate_batch.py          # Batch de validação (10 leads)
│   └── generate_adversarial_batch.py # Batch adversarial (variações e casos extremos)
├── ai-ui-shell/                   # UI React + TypeScript + Vite + Tailwind 4
└── tests/                         # Testes unitários (pytest) + E2E real
```

---

## URLs publicadas

`https://propostas.api-plataforma.com/{slug-do-negocio}-{hash}`

---

## Limitações conhecidas

1. **Validação comercial não realizada** — não sabemos ainda se as landings geradas convertem melhor do que uma página genérica; a métrica que importa (WhatsApp click-through) ainda não foi medida no mundo real.
2. **Cobertura de nichos limitada** — 3 nichos comerciais (estetica, academia, barbearia); nicho fora do catálogo → `POSITIONING_UNDETERMINED`, nunca aproximado.
3. **Trust signals compartilhados por posição** — negócios do mesmo nicho/posição recebem a mesma base de prova social; só a evidência do Google Places (quando disponível) diferencia o texto entre leads.
4. **Urgência depende de dados reais** — sem evidência de horário/disponibilidade, o sistema deliberadamente não inventa urgência.
5. **Google Places depende de captação trazer `place_id`** — a integração está testada, mas seu impacto em produção depende do fluxo de leads real alimentar esse campo.
6. **CLI sem flags** — `python main.py` é uma simulação fixa; para automação real, use a API ou `generate_landing`.
7. **Estado em memória na API** — leads/gerações são in-memory (MVP); reiniciar a API perde o histórico. Substituição por banco planejada.

---

## Próximos passos

**Imediato**
1. Validação comercial — medir conversão real (cliques no WhatsApp) em leads publicados.
2. Conectar `place_id` real ao fluxo de captação de leads em produção.
3. Iterar copy/posicionamento com base em dados de mercado, não só em métricas de LLM-judge.

**Depois da validação**
1. Diferenciação por lead além do que a evidência já cobre.
2. Expansão de nichos conforme demanda real.
3. Otimização de conversão com testes A/B baseados em CTR real.
4. Persistência (banco de dados) para leads/gerações na API.
