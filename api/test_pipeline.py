"""
Script para testar a integração com o pipeline.
"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.app import leads_db, generations_db, Lead, GenerationStatus
from api.pipeline_adapter import PipelineAdapter


async def test_pipeline():
    """Testa o adaptador com dados de exemplo."""

    # Criar lead de teste (phone válido exigido por BusinessData)
    lead = Lead(
        id="lead_test_123",
        name="Padaria do João",
        niche="padaria",
        city="Goiânia",
        phone="62 99999-9999"
    )
    leads_db.append(lead)

    # Criar geração
    gen = GenerationStatus(
        id="gen_test_456",
        lead_id=lead.id,
        status="queued"
    )
    generations_db.append(gen)

    print(f"Lead criado: {lead.name}")
    print(f"Generation criada: {gen.id}")

    # Executar pipeline
    adapter = PipelineAdapter()
    result = await adapter.run(gen.id)

    print(f"Resultado: {result['status']}")
    print(f"Status final do gen: {gen.status}")
    if gen.status == 'published':
        print(f"URL: {gen.url}")
        print(f"Arquétipo: {gen.archetype_name}")
        print(f"Cor: {gen.primary_color}")
        print(f"Headline: {gen.headline}")
        print(f"CTA: {gen.cta}")
    else:
        print(f"Erro: {gen.error}")

    # Limpar
    leads_db.clear()
    generations_db.clear()


if __name__ == "__main__":
    asyncio.run(test_pipeline())