"""
Fase 17.2 — A/B Test: Quality Gate B2C com e sem evidências do Google Places.

Compara o mesmo dataset e o mesmo LLM-judge da Fase 15.2
(api/quality_gate_b2c.py::QUALITY_LEADS, evaluate_deterministic,
evaluate_with_llm) em duas condições:
  - CONTROLE: place_id=None → CommercialEvidence() vazia (comportamento
    idêntico à Fase 15.2 — nenhum código de pipeline foi alterado para
    rodar este teste).
  - TRATAMENTO: place_id de um negócio REAL do mesmo nicho em Goiânia
    (obtido via Google Places Text Search — ver
    scratchpad/niche_place_ids.json para a busca original) → o pipeline
    chama google_places.GooglePlacesEnricher normalmente, como qualquer
    lead real com place_id seria enriquecido.

Os 20 leads sintéticos (nome/nicho/cidade/telefone) são idênticos à Fase
15.2 — só a presença/ausência de evidência varia entre os grupos.
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(Path(PROJECT_ROOT) / '.env')

from api.app import leads_db, generations_db, Lead, GenerationStatus
from api.pipeline_adapter import PipelineAdapter
from api.quality_gate_b2c import (
    QUALITY_LEADS,
    evaluate_deterministic,
    evaluate_with_llm,
)
from validate_evidence_integrity import EvidenceIntegrityValidator
import google_places

# Place_id de um negócio real por nicho em Goiânia (Google Places Text
# Search, ver scratchpad/niche_place_ids.json para a consulta original e
# os metadados — nome, endereço, rating — de cada um, para reprodutibilidade).
NICHE_PLACE_IDS = {
    "padaria": "ChIJI33ZNg7xXpMRFT9U8h7VFLs",       # Panificadora Mundial
    "restaurante": "ChIJjafAUmnxXpMRnCdaULqOSLo",   # Nord 23
    "mecânica": "ChIJCQsOf7zxXpMRtX6z0lCL7r0",       # Mecânica 86 Elétrica
    "barbearia": "ChIJ6RwFOp3xXpMR76Y--nzI2sU",      # Barbearia18k
    "salão": "ChIJL23FVFzxXpMRK1I2Cp2MxWM",          # Studio Nill Cabeleireiros
    "confeitaria": "ChIJbcT3yELxXpMRbF_j8pzeCTs",    # Richesse Confeitaria
    "academia": "ChIJi_9_0hTxXpMRiL_abKHwPHU",       # Bodytech
    "pet_shop": "ChIJL7DhkNb2XpMR-_l5YfoXaBI",       # Goiás Pet
    "moda": "ChIJ84pC1ZfzXpMRJRpDGvROfcI",           # W'CY Moda Feminina
    "farmácia": "ChIJU8zpvVTxXpMR5NunyM2aaTw",       # Drogasil
}


async def run_batch(use_evidence: bool) -> List[Dict[str, Any]]:
    """Executa o batch dos 20 leads da Fase 15.2, com ou sem evidência."""
    from main import get_archetype_or_fail

    tag = "t" if use_evidence else "c"
    batch_results = []

    for idx, lead_data in enumerate(QUALITY_LEADS, 1):
        print(f"\n[{idx}/{len(QUALITY_LEADS)}] {lead_data['name']} ({lead_data['niche']})")
        print("-" * 50)

        place_id = NICHE_PLACE_IDS.get(lead_data["niche"]) if use_evidence else None

        try:
            lead = Lead(
                id=f"lead_ab_{tag}_{idx}", name=lead_data["name"], niche=lead_data["niche"],
                city=lead_data["city"], phone=lead_data["phone"], place_id=place_id,
            )
            leads_db.append(lead)

            gen = GenerationStatus(id=f"gen_ab_{tag}_{idx}", lead_id=lead.id, status="queued")
            generations_db.append(gen)

            # Evidência real usada (para relatório de integridade) — mesma
            # lógica que PipelineAdapter.run já executa internamente.
            evidence = None
            if place_id and google_places.is_available():
                enricher = google_places.GooglePlacesEnricher()
                evidence = await enricher.enrich(place_id)

            start = datetime.now()
            adapter = PipelineAdapter()
            result = await adapter.run(gen.id)
            elapsed = (datetime.now() - start).total_seconds()

            if result["status"] != "published":
                error_code = gen.error.get("code", "unknown") if gen.error else "unknown"
                print(f"   Falhou: {error_code}")
                batch_results.append({
                    "lead": lead_data, "status": "failed", "error": gen.error,
                    "evidence_used": use_evidence,
                })
                continue

            gen = result["generation"]

            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(gen.url, timeout=10.0)

            if response.status_code != 200:
                print(f"   URL inacessível: HTTP {response.status_code}")
                batch_results.append({"lead": lead_data, "status": "inaccessible", "evidence_used": use_evidence})
                continue

            html = response.text
            archetype_key, archetype = get_archetype_or_fail(lead_data["niche"])

            det = evaluate_deterministic(html, lead_data, archetype)
            det_score = sum(det.values()) / len(det) * 5.0

            sem = await evaluate_with_llm(html, lead_data, archetype)
            sem_score = sum(sem.values()) / len(sem) if sem else None
            total_score = (det_score + sem_score) / 2 if sem_score is not None else None

            # Integridade de evidência — só faz sentido para o tratamento
            # (controle não tem evidência para distorcer).
            integrity = None
            if evidence is not None and evidence.has_evidence:
                combined_text = f"{gen.headline or ''} {gen.subheadline or ''} {' '.join(gen.proofs or [])}"
                integrity_result = EvidenceIntegrityValidator(evidence).validate(combined_text)
                integrity = integrity_result.to_dict()

            print(f"   Publicado: {gen.url}")
            print(f"   Arquétipo: {archetype_key}")
            print(f"   Evidência disponível: {evidence.has_evidence if evidence else False}")
            print(f"   Determinístico: {det_score:.2f}/5.0"
                  + (f" | Semântico: {sem_score:.2f}/5.0" if sem_score is not None else " | Semântico: N/A"))
            print(f"   {elapsed:.2f}s")

            batch_results.append({
                "lead": lead_data,
                "url": gen.url,
                "status": "published",
                "archetype": archetype_key,
                "deterministic": det,
                "deterministic_score": det_score,
                "semantic": sem,
                "semantic_score": sem_score,
                "total_score": total_score,
                "evidence_used": use_evidence,
                "evidence_available": bool(evidence.has_evidence) if evidence else False,
                "place_id": place_id,
                "integrity": integrity,
                "duration": elapsed,
            })

        except Exception as e:
            print(f"   Erro: {e}")
            batch_results.append({
                "lead": lead_data, "status": "error", "error": str(e), "evidence_used": use_evidence,
            })

    return batch_results


def _aggregate(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    published = [r for r in batch if r["status"] == "published"]
    with_semantic = [r for r in published if r.get("semantic_score") is not None]

    dims = ["headline_clarity", "niche_specificity", "cta_quality", "urgency",
            "b2c_orientation", "credibility", "differentiation", "conversion_potential"]
    dim_avgs = {}
    for d in dims:
        vals = [r["semantic"][d] for r in with_semantic if r.get("semantic")]
        dim_avgs[d] = sum(vals) / len(vals) if vals else None

    violations = sum(
        len(r["integrity"]["violations"]) for r in published if r.get("integrity")
    )
    evidence_available = sum(1 for r in published if r.get("evidence_available"))

    return {
        "total": len(batch),
        "published": len(published),
        "failed": len(batch) - len(published),
        "avg_deterministic": sum(r["deterministic_score"] for r in published) / len(published) if published else 0.0,
        "avg_semantic": sum(r["semantic_score"] for r in with_semantic) / len(with_semantic) if with_semantic else None,
        "avg_total": sum(r["total_score"] for r in with_semantic) / len(with_semantic) if with_semantic else None,
        "dimensions": dim_avgs,
        "evidence_available": evidence_available,
        "integrity_violations": violations,
    }


async def run_ab_test() -> Dict[str, Any]:
    print("\n" + "=" * 70)
    print("📊 A/B TEST - FASE 15.2 (sem evidências) vs FASE 17.2 (com evidências)")
    print("=" * 70 + "\n")

    print("🔬 CONTROLE (sem evidências)")
    print("-" * 50)
    control = await run_batch(use_evidence=False)

    # Reseta o estado em memória entre os grupos (evita colisão de ids/place_id).
    leads_db[:] = [l for l in leads_db if not l.id.startswith("lead_ab_")]
    generations_db[:] = [g for g in generations_db if not g.id.startswith("gen_ab_")]

    print("\n🧪 TRATAMENTO (com evidências reais do Google Places)")
    print("-" * 50)
    treatment = await run_batch(use_evidence=True)

    return {
        "control": control,
        "treatment": treatment,
        "control_summary": _aggregate(control),
        "treatment_summary": _aggregate(treatment),
        "niche_place_ids": NICHE_PLACE_IDS,
        "timestamp": datetime.now().isoformat(),
    }


def _print_comparison(report: Dict[str, Any]) -> None:
    c, t = report["control_summary"], report["treatment_summary"]

    def delta(a, b):
        if a is None or b is None:
            return "N/A"
        return f"{b - a:+.2f}"

    print("\n" + "=" * 70)
    print("📊 RESULTADOS DO A/B TEST")
    print("=" * 70)

    print(f"\n### Publicação")
    print(f"| Métrica | Controle | Tratamento | Delta |")
    print(f"|---|---|---|---|")
    print(f"| Publicados | {c['published']}/{c['total']} | {t['published']}/{t['total']} | {t['published']-c['published']:+d} |")
    print(f"| Falhas | {c['failed']} | {t['failed']} | {t['failed']-c['failed']:+d} |")

    print(f"\n### Qualidade (LLM-judge)")
    print(f"| Métrica | Controle | Tratamento | Delta |")
    print(f"|---|---|---|---|")
    for dim in ["urgency", "credibility", "differentiation", "b2c_orientation", "cta_quality"]:
        cv, tv = c["dimensions"].get(dim), t["dimensions"].get(dim)
        cv_s = f"{cv:.2f}" if cv is not None else "N/A"
        tv_s = f"{tv:.2f}" if tv is not None else "N/A"
        print(f"| {dim} | {cv_s} | {tv_s} | {delta(cv, tv)} |")
    cv_s = f"{c['avg_total']:.2f}" if c['avg_total'] is not None else "N/A"
    tv_s = f"{t['avg_total']:.2f}" if t['avg_total'] is not None else "N/A"
    print(f"| **Total** | **{cv_s}** | **{tv_s}** | **{delta(c['avg_total'], t['avg_total'])}** |")

    print(f"\n### Integridade")
    print(f"| Métrica | Controle | Tratamento |")
    print(f"|---|---|---|")
    print(f"| Violações | {c['integrity_violations']} | {t['integrity_violations']} |")
    print(f"| Evidências disponíveis | N/A | {t['evidence_available']}/{t['published']} |")


async def main():
    report = await run_ab_test()
    _print_comparison(report)

    report_path = PROJECT_ROOT / "ab_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str, ensure_ascii=False)

    print(f"\n📁 Relatório salvo em: {report_path}")

    # Limpa o estado em memória usado pelo teste.
    leads_db[:] = [l for l in leads_db if not l.id.startswith("lead_ab_")]
    generations_db[:] = [g for g in generations_db if not g.id.startswith("gen_ab_")]


if __name__ == "__main__":
    asyncio.run(main())
