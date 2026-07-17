# Reframe - Pipeline de Geração de Propostas

Pipeline automatizado para descoberta, qualificação e geração de propostas de sites personalizados.

## Setup

1. Copie `.env.example` para `.env` e preencha as credenciais
2. Instale dependências: `pip install -r requirements.txt`
3. Execute: `python main.py`

## Arquitetura

- **Descoberta**: Google Places API
- **LLM Primário**: Ollama (Qwen 2.5)
- **LLM Fallback**: Gemini 1.5 Flash
- **Publicação**: Cloudflare R2 + Worker
- **Imagens**: Unsplash (com fallback Picsum)

## Status

Em desenvolvimento.
