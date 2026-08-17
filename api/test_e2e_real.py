"""
Teste End-to-End completo com pipeline real.
Requer credenciais LLM e R2 válidas.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(Path(PROJECT_ROOT) / '.env')

# Importações da API
from api.app import leads_db, generations_db, Lead, GenerationStatus
from api.pipeline_adapter import PipelineAdapter

async def test_e2e_real():
    """Testa o fluxo completo: Lead → Generation → Published → URL."""

    print("\n" + "="*60)
    print("TESTE E2E REAL - REFRAME")
    print("="*60 + "\n")

    # 1. Criar lead de teste
    print("1. Criando lead de teste...")
    lead = Lead(
        id="lead_e2e_test",
        name="Padaria E2E Test",
        niche="padaria",
        city="Goiânia",
        phone="(62) 99999-9999",
        place_id="test_place_id"
    )
    leads_db.append(lead)
    print(f"   Lead criado: {lead.name} ({lead.id})")

    # 2. Criar geração
    print("\n2. Criando geração...")
    gen = GenerationStatus(
        id="gen_e2e_test",
        lead_id=lead.id,
        status="queued"
    )
    generations_db.append(gen)
    print(f"   Geração criada: {gen.id}")

    # 3. Executar pipeline
    print("\n3. Executando pipeline...")
    print("   (Isso pode levar alguns segundos...)\n")

    start_time = datetime.now()
    adapter = PipelineAdapter()
    result = await adapter.run(gen.id)
    elapsed = (datetime.now() - start_time).total_seconds()

    # 4. Verificar resultado
    print(f"\n4. Resultado (em {elapsed:.2f}s):")
    print(f"   Status: {result['status']}")

    if result['status'] == 'published':
        gen = result['generation']

        print("\n   Dados da landing:")
        print(f"   URL: {gen.url}")
        print(f"   Arquétipo: {gen.archetype_name}")
        print(f"   Cor primária: {gen.primary_color}")
        print(f"   Headline: {gen.headline}")
        print(f"   Subheadline: {gen.subheadline}")
        print(f"   CTA: {gen.cta}")
        print(f"   Trust signals: {len(gen.proofs)}")

        # 5. Verificar URL
        print("\n5. Verificando URL publicada...")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(gen.url, timeout=15.0, follow_redirects=True)

            if response.status_code == 200:
                print(f"   URL acessível (HTTP {response.status_code})")
                print(f"   HTML: {len(response.text)} caracteres")

                # Verificar conteúdo básico
                if lead.name in response.text:
                    print(f"   Nome do lead encontrado no HTML")
                if gen.headline and gen.headline in response.text:
                    print(f"   Headline encontrada no HTML")
                if 'background-image' in response.text:
                    print(f"   Hero image (background-image) encontrada")
                if 'tailwind' in response.text.lower():
                    print(f"   Tailwind CSS encontrado")

            else:
                print(f"   URL retornou HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"   Falha ao acessar URL: {e}")
            return False

        print("\n" + "="*60)
        print("E2E REAL - COMPLETO COM SUCESSO!")
        print("="*60)
        print(f"\nLanding publicada em: {gen.url}")
        print("   Abra no navegador para visualizar.")
        print("\nDetalhes:")
        print(f"   Lead: {lead.name} ({lead.id})")
        print(f"   Generation: {gen.id}")
        print(f"   Tempo total: {elapsed:.2f}s")

        return True

    else:
        # Falha
        print(f"\n   Falha na geração:")
        if gen.error:
            print(f"   Código: {gen.error.get('code', 'unknown')}")
            print(f"   Mensagem: {gen.error.get('message', 'unknown')}")
            if gen.error.get('detail'):
                print(f"   Detalhe: {gen.error.get('detail')[:200]}...")
        else:
            print(f"   Erro desconhecido")

        print("\nE2E REAL - FALHOU")
        return False

async def main():
    """Executa o teste e limpa os dados."""
    success = await test_e2e_real()

    # Limpar dados de teste
    global leads_db, generations_db
    leads_db = [l for l in leads_db if not l.id.startswith("lead_e2e")]
    generations_db = [g for g in generations_db if not g.id.startswith("gen_e2e")]

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
