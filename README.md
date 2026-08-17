# Reframe — Pipeline de Geração de Landing Pages B2C

Pipeline automatizado que transforma leads de negócios locais em landing pages estáticas publicadas no Cloudflare R2, com perspectiva **B2C** (venda para o consumidor final, não para o dono do negócio).

---

## Status do Projeto

**Arquitetura congelada — modo commercial validation.** O MVP (engineering validation) está encerrado: pipeline funcional, testado, com gate de integridade de conteúdo, e o A/B test da Fase 17.2 confirmou que evidências reais melhoram a qualidade percebida da copy (ver seção abaixo). Isso é sinal suficiente para não abrir mais fases de otimização técnica agora — o próximo passo é um piloto comercial pequeno (10–20 negócios reais) para medir se dono de negócio paga pela landing, não mais score de LLM-judge.

| Área | Status |
|---|---|
| Pipeline (LLM → Render → Publish) | ✅ |
| Identidade e publicação (slug, colisão, URL) | ✅ |
| Integridade semântica (evidence integrity gate) | ✅ |
| Classificação estruturada de erros | ✅ |
| Enriquecimento com Google Places | ✅ (opcional, requer API key) |
| Validação comercial (conversão real) | ⏳ Pendente |

---

## Visão Geral

```
Lead (nome, nicho, cidade, telefone, place_id opcional)
    ↓
Arquétipo determinístico (resolve nicho → trust signals, cor, imagem)
    ↓
Google Places (se houver place_id) → evidências comerciais reais
    ↓
LLM gera copy (com instruções B2C + integridade de evidência)
    ↓
Normalização + validação (Pydantic)
    ↓
Evidence Integrity Gate (bloqueia distorção de fatos)
    ↓
Arquétipo sobrescreve proofs/cor (elimina alucinação restante)
    ↓
Render Jinja2 + Tailwind
    ↓
Publicação Cloudflare R2
    ↓
https://propostas.api-plataforma.com/{slug}
```

---

## Arquitetura

```
UI (React + TypeScript, ai-ui-shell/)
    ↓ HTTP
API (FastAPI, api/app.py)
    ↓
PipelineAdapter (api/pipeline_adapter.py)
    ↓
┌────────────────────────────────────────────────────────┐
│ 1. Archetype Resolution   (10 nichos mapeados)          │
│ 2. Google Places Enrichment  (opcional, por place_id)   │
│ 3. LLM Generation  (Agnes → Gemini fallback)            │
│ 4. Normalização + Validação  (Pydantic)                 │
│ 5. Evidence Integrity Gate  (bloqueia distorção)        │
│ 6. Arquétipo sobrescreve proofs/cor  (determinístico)   │
│ 7. Render (Jinja2) + Publish (R2)                       │
└────────────────────────────────────────────────────────┘
    ↓
Landing pública: https://propostas.api-plataforma.com/{slug}
```

`main.py::generate_landing` é o ponto de entrada único, reusado tanto pela API (via `pipeline_adapter.py`) quanto por scripts/CLI.

---

## Stack

| Camada | Tecnologia |
|---|---|
| **LLM primário** | Agnes (`agnes-2.0-flash`, API OpenAI-compatible) |
| **LLM fallback** | Gemini (`gemini-flash-latest`) — Ollama local também suportado |
| **Evidências comerciais** | Google Places API (New) v1 — opcional |
| **Imagens** | Unsplash (arquétipo fixo por nicho) |
| **Template** | Jinja2 + Tailwind CSS (CDN) |
| **Storage** | Cloudflare R2 (S3-compatible, via boto3) |
| **Domínio** | `propostas.api-plataforma.com` |
| **API** | FastAPI (`api/`) |
| **UI** | React + TypeScript + Vite (`ai-ui-shell/`) |
| **Validação** | Pydantic v2 |
| **Testes** | pytest |

---

## Capacidades

### Implementadas

- **Geração B2C**: copy focada no consumidor final; proibido vocabulário de gestão/negócio ("empresa", "transformar", etc.)
- **Arquétipos determinísticos**: 10 nichos mapeados — padaria, mecânica, restaurante, barbearia, salão, confeitaria, academia, pet shop, moda, farmácia. `proofs`, cor e imagem hero são travados pelo arquétipo, não pelo LLM.
- **Nichos não mapeados são bloqueados, não aproximados**: sem fallback genérico — `ARCHETYPE_NOT_SUPPORTED` impede publicar um nicho com prova social de outro segmento.
- **Fallback de LLM com retry**: até 3 tentativas, trocando de provedor e temperatura antes de desistir.
- **Normalização de output**: trunca campos que excedem limites mecânicos (ex: título SEO longo) em vez de rejeitar a geração inteira.
- **Validação Pydantic**: schema rígido em toda a fronteira LLM → template (`LLMOutput`, `ProposalTemplateData`).
- **Enriquecimento com Google Places**: quando o lead tem `place_id`, horário, avaliação e site oficial viram `CommercialEvidence` real, injetada no prompt como única fonte de fatos específicos.
- **Evidence Integrity Gate**: valida a copy gerada contra as evidências fornecidas antes da publicação — bloqueia distorções como "1209 avaliações" virando "mais de 1200 alunos" (troca de entidade, arredondamento, inferência não fundamentada). Ver `validate_evidence_integrity.py` e `main.py::_evidence_integrity_gate`.
- **Identidade de publicação**: slugs determinísticos (`nome-hash`), DNS-safe, com proteção contra colisão silenciosa no R2.
- **Classificação estruturada de erros**: códigos estáveis (`api/errors.py`) distinguem erros retryable (timeout, quota) de não-retryable (credenciais inválidas, nicho não suportado, violação de integridade).
- **Alertas**: notificação via Telegram em falhas críticas do pipeline.

### Pendentes (próximo ciclo)

- **Validação comercial**: ainda não medimos se as landings geram conversão real (cliques no WhatsApp, taxa de resposta).
- **Google Places em uso ativo por leads reais**: a integração funciona (testada em batch via A/B — ver seção abaixo), mas depende do fluxo de captação real trazer `place_id`.
- **Diferenciação por lead**: dois negócios do mesmo nicho ainda recebem os mesmos `trust signals` — só a evidência (quando disponível) varia por lead.
- **Cobertura de nichos**: 10 nichos mapeados; qualquer outro é recusado, não aproximado.

---

## Medição de impacto — Google Places (Fase 17.2)

Foi rodado um A/B test com os mesmos 20 leads do Quality Gate B2C (`api/quality_gate_b2c.py::QUALITY_LEADS`), variando apenas a presença de evidência real do Google Places (um negócio real por nicho em Goiânia) — ver `api/ab_test_quality_gate.py`. Métricas de publicação, LLM-judge (mesmas 8 dimensões da Fase 15.2) e violações de integridade de evidência, com relatório salvo em `ab_test_report.json`.

**Resultado:** 20/20 publicados em ambos os grupos. Ganho no LLM-judge com evidência real, concentrado exatamente nos eixos que eram gargalo — Credibility +1,08, Urgency +0,48, Differentiation +0,45 (total 3,75 → 3,97). Duas violações de integridade (severidade `medium`, não bloqueante) — o LLM inseriu "horário flexível" sem essa palavra estar na evidência real de uma academia; publicado mesmo assim, registrado para observabilidade.

**Leitura:** isso prova que o produto melhora com dados reais — não prova que ele converte. LLM-judge é proxy, não substituto de validação comercial. Conclusão registrada como dívida explícita (não corrigida agora): violação `medium` hoje publica e só loga; comercialmente, uma afirmação derivada de evidência não deveria ser "embelezada" pelo LLM mesmo em severidade baixa — candidato a promover para bloqueante numa fase futura, se o piloto comercial justificar o investimento.

---

## Testes

```bash
pytest tests/ -v
```

A suíte cobre normalização/validação Pydantic, arquétipos, classificação de erros, identidade/slug, integração com Google Places, integridade de evidência (validador + gate de pipeline) e publisher/R2 — ver `tests/`. Dois testes em `api/` (`test_e2e_real.py`, `test_pipeline.py`) são `async def` e exigem `pytest-asyncio` instalado para rodar; sem o plugin, o `pytest` os reporta como falha de coleta, não como bug do pipeline.

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

# Google Places (opcional — sem ela, evidência fica vazia e o LLM
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

### Setup

```bash
# Pipeline / CLI
pip install -r requirements.txt
cp .env.example .env   # preencha as credenciais
python main.py

# API
pip install -r api/requirements.txt
python api/run.py      # http://localhost:8000

# UI
cd ai-ui-shell
npm install
npm run dev
```

---

## Estrutura

```
Reframe/
├── main.py                       # Orquestrador do pipeline + arquétipos + evidence gate
├── models.py                     # Schemas Pydantic (BusinessData, CommercialEvidence, CopyData...)
├── llm_provider.py                # Dispatch Agnes/Gemini/Ollama + prompt B2C + evidence integrity
├── validate_evidence_integrity.py # Validador estruturado de integridade de evidências
├── google_places.py               # Enriquecimento via Google Places API (New) v1
├── publisher.py                   # Upload para R2 (boto3)
├── config/archetypes.py           # 10 arquétipos determinísticos (nicho → cor/imagem/trust signals)
├── templates/premium.html         # Template Jinja2 (Tailwind, hero via inline style)
├── api/
│   ├── app.py                     # FastAPI (leads, generations)
│   ├── pipeline_adapter.py        # Adapta main.generate_landing à API + classificação de erro
│   ├── errors.py                  # Códigos de erro estáveis, retryable/não-retryable
│   ├── quality_gate_b2c.py        # Quality Gate com LLM-judge (Fase 15.2)
│   └── ab_test_quality_gate.py    # A/B test controle vs Google Places (Fase 17.2)
├── ai-ui-shell/                   # UI React + TypeScript
├── tests/                         # Testes unitários (pytest)
└── .env                           # Credenciais (não versionado)
```

---

## URLs publicadas

`https://propostas.api-plataforma.com/{slug-do-negocio}-{hash}`

---

## Limitações conhecidas

1. **Validação comercial não realizada** — não sabemos ainda se as landings geradas convertem melhor do que uma página genérica; a métrica que importa (WhatsApp click-through) ainda não foi medida no mundo real.
2. **Trust signals fixos por nicho** — dois negócios do mesmo nicho recebem a mesma prova social; só a evidência do Google Places (quando disponível) diferencia o texto entre leads.
3. **Urgência depende de dados reais** — sem evidência de horário/disponibilidade, o sistema deliberadamente não inventa urgência.
4. **Cobertura de nichos limitada** — 10 nichos mapeados; qualquer outro nicho é recusado (`ARCHETYPE_NOT_SUPPORTED`), nunca aproximado.
5. **Google Places depende de captação trazer `place_id`** — a integração está testada e funcional, mas seu impacto em produção depende do fluxo de leads real alimentar esse campo.

---

## Próximos passos

**Imediato**
1. Validação comercial — medir conversão real (cliques no WhatsApp) em leads publicados.
2. Conectar `place_id` real ao fluxo de captação de leads em produção.
3. Iterar copy/arquétipos com base em dados de mercado, não só em métricas de LLM-judge.

**Depois da validação**
1. Diferenciação por lead além do que a evidência já cobre.
2. Expansão de nichos conforme demanda real.
3. Otimização de conversão com testes A/B baseados em CTR real (não só qualidade percebida por LLM-judge).
