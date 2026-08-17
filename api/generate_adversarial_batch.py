"""
Batch adversarial para testar robustez do sistema.
Inclui variações linguísticas, nichos similares, casos extremos.
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

ADVERSARIAL_LEADS = [
    # Variações de nichos mapeados
    {"name": "Barbearia do Zé", "niche": "barbearia", "city": "Goiânia", "phone": "(62) 9999-0101"},
    {"name": "Barber Shop Moderno", "niche": "barber shop", "city": "Goiânia", "phone": "(62) 9999-0102"},
    {"name": "Barbearia Masculina", "niche": "barbearia masculina", "city": "Goiânia", "phone": "(62) 9999-0103"},
    {"name": "Salão Bella Vista", "niche": "salão de beleza", "city": "Goiânia", "phone": "(62) 9999-0104"},
    {"name": "Beauty Salon", "niche": "beauty salon", "city": "Goiânia", "phone": "(62) 9999-0105"},
    {"name": "Padaria do Pão", "niche": "padaria", "city": "Goiânia", "phone": "(62) 9999-0106"},
    {"name": "Panificadora Central", "niche": "panificadora", "city": "Goiânia", "phone": "(62) 9999-0107"},

    # Nichos similares (teste de desambiguação)
    {"name": "Confeitaria Doce", "niche": "confeitaria", "city": "Goiânia", "phone": "(62) 9999-0108"},
    {"name": "Padaria e Confeitaria", "niche": "padaria e confeitaria", "city": "Goiânia", "phone": "(62) 9999-0109"},
    {"name": "Restaurante Gourmet", "niche": "restaurante", "city": "Goiânia", "phone": "(62) 9999-0110"},
    {"name": "Lanchonete do Bairro", "niche": "lanchonete", "city": "Goiânia", "phone": "(62) 9999-0111"},
    {"name": "Academia Power", "niche": "academia", "city": "Goiânia", "phone": "(62) 9999-0112"},
    {"name": "Centro de Treinamento", "niche": "centro de treinamento", "city": "Goiânia", "phone": "(62) 9999-0113"},

    # Nichos não mapeados (devem falhar com ARCHETYPE_NOT_SUPPORTED)
    {"name": "Clínica Veterinária", "niche": "veterinária", "city": "Goiânia", "phone": "(62) 9999-0114"},
    {"name": "Escola de Idiomas", "niche": "escola de idiomas", "city": "Goiânia", "phone": "(62) 9999-0115"},
    {"name": "Consultório Dentário", "niche": "dentista", "city": "Goiânia", "phone": "(62) 9999-0116"},

    # Casos extremos
    {"name": "Oficina Mecânica", "niche": "mecânica", "city": "Goiânia", "phone": "(62) 9999-0117"},
    {"name": "Mecânica de Motos", "niche": "mecânica de motos", "city": "Goiânia", "phone": "(62) 9999-0118"},
    {"name": "Farmácia Popular", "niche": "farmácia", "city": "Goiânia", "phone": "(62) 9999-0119"},
    {"name": "Drogaria Central", "niche": "drogaria", "city": "Goiânia", "phone": "(62) 9999-0120"},
    {"name": "Pet Shop Amigo", "niche": "pet shop", "city": "Goiânia", "phone": "(62) 9999-0121"},
    {"name": "Loja de Roupas", "niche": "moda", "city": "Goiânia", "phone": "(62) 9999-0122"},
    {"name": "Moda Infantil", "niche": "moda infantil", "city": "Goiânia", "phone": "(62) 9999-0123"},

    # Telefone inválido
    {"name": "Sem Telefone", "niche": "padaria", "city": "Goiânia", "phone": ""},
    {"name": "Telefone Curto", "niche": "padaria", "city": "Goiânia", "phone": "123"},
]

# Mapeamento esperado (niche -> archetype_key REAL, conforme config/archetypes.py).
# None = esperamos ARCHETYPE_NOT_SUPPORTED (nicho intencionalmente fora de escopo,
# ou variação/sinônimo que o matching fuzzy atual não cobre — o objetivo deste
# batch é justamente revelar esses buracos, não presumir que fecham).
EXPECTED_ARCHETYPE = {
    "barbearia": "barbearia",
    "barber shop": None,               # sinônimo em inglês, sem alias mapeado
    "barbearia masculina": "barbearia",
    "salão de beleza": "salao",
    "beauty salon": None,              # sinônimo em inglês, sem alias mapeado
    "padaria": "padaria",
    "panificadora": "padaria",
    "confeitaria": "confeitaria",
    "padaria e confeitaria": "padaria",  # ambíguo; primeiro match na ordem do dict vence
    "restaurante": "restaurante",
    "lanchonete": None,                # sinônimo próximo, sem alias mapeado
    "academia": "academia",
    "centro de treinamento": None,     # sinônimo, sem alias mapeado
    "veterinária": None,               # fora de escopo (não mapeado)
    "escola de idiomas": None,         # fora de escopo (não mapeado)
    "dentista": None,                  # fora de escopo (não mapeado)
    "mecânica": "mecanica",
    "mecânica de motos": "mecanica",
    "farmácia": "farmacia",
    "drogaria": "farmacia",
    "pet shop": "pet_shop",
    "moda": "moda",
    "moda infantil": "moda",
}


async def run_adversarial_batch() -> Dict[str, Any]:
    """Executa o batch adversarial e coleta métricas."""

    print("\n" + "="*70)
    print("BATCH ADVERSARIAL - REFRAME")
    print("="*70 + "\n")

    results = []
    metrics = {
        "total": len(ADVERSARIAL_LEADS),
        "published": 0,
        "failed": 0,
        "archetype_correct": 0,
        "archetype_evaluated": 0,
        "unknown_niche_handled": 0,
        "unknown_niche_expected": 0,
        "durations": [],
        "total_duration": 0,
        "errors": []
    }

    for idx, lead_data in enumerate(ADVERSARIAL_LEADS, 1):
        print(f"\n[{idx}/{len(ADVERSARIAL_LEADS)}] {lead_data['name']} ({lead_data['niche']})")
        print("-" * 50)

        try:
            lead = Lead(
                id=f"lead_adv_{idx}",
                name=lead_data["name"],
                niche=lead_data["niche"],
                city=lead_data["city"],
                phone=lead_data["phone"]
            )
            leads_db.append(lead)

            gen = GenerationStatus(
                id=f"gen_adv_{idx}",
                lead_id=lead.id,
                status="queued"
            )
            generations_db.append(gen)

            start = datetime.now()
            adapter = PipelineAdapter()
            result = await adapter.run(gen.id)
            elapsed = (datetime.now() - start).total_seconds()
            metrics["total_duration"] += elapsed
            metrics["durations"].append(elapsed)

            expected_key = EXPECTED_ARCHETYPE.get(lead_data["niche"])

            if result['status'] == 'published':
                gen = result['generation']
                metrics["published"] += 1

                if expected_key is not None:
                    metrics["archetype_evaluated"] += 1
                    is_correct = (gen.archetype_name == expected_key)
                    if is_correct:
                        metrics["archetype_correct"] += 1
                else:
                    # Publicou algo que esperávamos que NÃO tivesse arquétipo mapeado.
                    is_correct = False

                print(f"   Publicado: {gen.url}")
                print(f"   Arquétipo: {gen.archetype_name} (esperado: {expected_key}) {'OK' if is_correct else ('N/A' if expected_key is None else 'DIVERGENTE')}")
                print(f"   {elapsed:.2f}s")

                results.append({
                    "lead": lead_data,
                    "generation_id": gen.id,
                    "status": "published",
                    "url": gen.url,
                    "archetype": gen.archetype_name,
                    "expected_archetype": expected_key,
                    "archetype_correct": is_correct,
                    "duration": elapsed,
                })
            else:
                metrics["failed"] += 1
                error_code = gen.error.get('code', 'unknown') if gen.error else 'unknown'

                if expected_key is None:
                    metrics["unknown_niche_expected"] += 1
                if error_code == "ARCHETYPE_NOT_SUPPORTED":
                    metrics["unknown_niche_handled"] += 1
                    print(f"   Nicho não suportado (bloqueado antes de publicar)")
                else:
                    print(f"   Falhou: {error_code}")

                results.append({
                    "lead": lead_data,
                    "status": "failed",
                    "expected_archetype": expected_key,
                    "error": gen.error if gen.error else {"code": "unknown"}
                })

        except Exception as e:
            metrics["failed"] += 1
            metrics["errors"].append({
                "lead": lead_data["name"],
                "error": str(e)
            })
            print(f"   Erro: {e}")

    return {
        "metrics": metrics,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


async def main():
    report = await run_adversarial_batch()

    print("\n" + "="*70)
    print("RELATÓRIO DO BATCH ADVERSARIAL")
    print("="*70)

    m = report["metrics"]
    durations = sorted(m["durations"])
    p95 = durations[int(len(durations) * 0.95) - 1] if durations else 0

    print(f"\nMétricas:")
    print(f"   Total: {m['total']}")
    print(f"   Publicados: {m['published']}")
    print(f"   Falhas: {m['failed']}")
    print(f"   Arquétipo correto (dos que tinham expectativa): {m['archetype_correct']}/{m['archetype_evaluated']}")
    print(f"   Nichos não mapeados bloqueados corretamente: {m['unknown_niche_handled']}/{m['unknown_niche_expected']}")
    print(f"   Tempo médio: {m['total_duration']/m['total']:.2f}s")
    print(f"   Tempo p95: {p95:.2f}s")

    report_path = PROJECT_ROOT / "adversarial_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str, ensure_ascii=False)

    print(f"\nRelatório salvo em: {report_path}")

    # Limpar dados de teste
    global leads_db, generations_db
    leads_db[:] = [l for l in leads_db if not l.id.startswith("lead_adv")]
    generations_db[:] = [g for g in generations_db if not g.id.startswith("gen_adv")]

if __name__ == "__main__":
    asyncio.run(main())
