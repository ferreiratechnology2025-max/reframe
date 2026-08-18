"""
Gera múltiplas landings para validação de produto.
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(Path(PROJECT_ROOT) / '.env')

from api.app import leads_db, generations_db, Lead, GenerationStatus
from api.pipeline_adapter import PipelineAdapter

BATCH_LEADS = [
    {"name": "Clínica Dra. Andrielle", "niche": "estetica", "city": "Goiânia", "phone": "+5562999999999"},
    {"name": "Academia Performance", "niche": "academia", "city": "Goiânia", "phone": "+5562888888888"},
    {"name": "Barbearia do Mário", "niche": "barbearia", "city": "Goiânia", "phone": "+5562777777777"},
]

async def generate_batch() -> List[Dict[str, Any]]:
    """Gera landings para todos os leads do lote."""
    results = []

    print("\n" + "="*70)
    print("GERANDO BATCH DE LANDINGS")
    print("="*70 + "\n")

    for idx, lead_data in enumerate(BATCH_LEADS, 1):
        print(f"\n[{idx}/{len(BATCH_LEADS)}] {lead_data['name']} ({lead_data['niche']})")
        print("-" * 50)

        try:
            # Criar lead
            lead = Lead(
                id=f"lead_batch_{idx}",
                name=lead_data["name"],
                niche=lead_data["niche"],
                city=lead_data["city"],
                phone=lead_data["phone"]
            )
            leads_db.append(lead)

            # Criar geração
            gen = GenerationStatus(
                id=f"gen_batch_{idx}",
                lead_id=lead.id,
                status="queued"
            )
            generations_db.append(gen)

            # Executar pipeline
            start = datetime.now()
            adapter = PipelineAdapter()
            result = await adapter.run(gen.id)
            elapsed = (datetime.now() - start).total_seconds()

            if result['status'] == 'published':
                gen = result['generation']
                print(f"   Publicado: {gen.url}")
                print(f"   {elapsed:.2f}s")

                results.append({
                    "lead": lead_data,
                    "generation_id": gen.id,
                    "status": "published",
                    "url": gen.url,
                    "archetype": gen.archetype_name,
                    "color": gen.primary_color,
                    "headline": gen.headline,
                    "duration": elapsed,
                    "proofs": len(gen.proofs),
                })
            else:
                print(f"   Falhou: {gen.error}")
                results.append({
                    "lead": lead_data,
                    "status": "failed",
                    "error": gen.error
                })

        except Exception as e:
            print(f"   Erro: {e}")
            results.append({
                "lead": lead_data,
                "status": "error",
                "error": str(e)
            })

    return results

async def main():
    results = await generate_batch()

    print("\n" + "="*70)
    print("RESUMO DO BATCH")
    print("="*70)

    published = [r for r in results if r.get('status') == 'published']
    failed = [r for r in results if r.get('status') != 'published']

    print(f"\nPublicados: {len(published)}/{len(BATCH_LEADS)}")
    print(f"Falhas: {len(failed)}/{len(BATCH_LEADS)}")

    if published:
        print("\nLandings publicadas:")
        for r in published:
            print(f"   - {r['lead']['name']} -> {r['url']}")

    if failed:
        print("\nFalhas:")
        for r in failed:
            print(f"   - {r['lead']['name']}: {r.get('error', 'unknown')}")

    # Salvar relatório
    report_path = PROJECT_ROOT / "batch_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": len(BATCH_LEADS),
            "published": len(published),
            "failed": len(failed),
            "results": results
        }, f, indent=2, default=str, ensure_ascii=False)

    print(f"\nRelatório salvo em: {report_path}")

if __name__ == "__main__":
    asyncio.run(main())
