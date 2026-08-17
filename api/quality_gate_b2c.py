"""
Quality Gate B2C - Avaliação comercial de landings.
Combina verificações determinísticas com LLM-judge para aspectos semânticos.

NOTA sobre correções em relação à especificação original da Fase 15:
- `evaluate_with_llm` estava com TODO e retornava valores mockados fixos —
  implementado de verdade aqui, usando o mesmo `llm_provider.call_llm` do
  pipeline (provider via env, com fallback e parsing tolerante a markdown).
  Sem isso, o "LLM-judge" não mediria nada real.
- `get_archetype_or_fail` retorna `Tuple[str, dict]` (archetype_key, config),
  não um dict solto — corrigido nas chamadas.
- `has_correct_archetype`: checar `archetype['name']` (ex: "Barbearia") como
  substring do HTML é ambíguo — o nome do lead às vezes já contém a palavra
  do nicho (ex: "Barbearia do Lago"), o que daria falso-positivo mesmo se o
  arquétipo errado tivesse sido aplicado. Trocado por checar a `primary_color`
  do arquétipo no HTML — é exatamente o dado travado (Fase 12) que prova que
  o arquétipo certo foi aplicado, sem ambiguidade textual.
- faltava `import sys` antes do `sys.path.insert`.
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(Path(PROJECT_ROOT) / '.env')

from api.app import leads_db, generations_db, Lead, GenerationStatus
from api.pipeline_adapter import PipelineAdapter


@dataclass
class QualityScore:
    """Avaliação de qualidade comercial de uma landing."""
    # Determinísticos (estrutura)
    has_phone: bool
    has_whatsapp: bool
    has_name: bool
    has_city: bool
    has_correct_archetype: bool
    has_hero: bool
    has_trust_signals: bool
    has_valid_html: bool

    # Semânticos (LLM-judge) — None quando o judge falhou para essa landing
    headline_clarity: Optional[float]
    niche_specificity: Optional[float]
    cta_quality: Optional[float]
    urgency: Optional[float]
    b2c_orientation: Optional[float]
    credibility: Optional[float]
    differentiation: Optional[float]
    conversion_potential: Optional[float]

    def deterministic_score(self) -> float:
        checks = [
            self.has_phone, self.has_whatsapp, self.has_name, self.has_city,
            self.has_correct_archetype, self.has_hero, self.has_trust_signals,
            self.has_valid_html,
        ]
        return sum(checks) / len(checks) * 5.0

    def semantic_score(self) -> Optional[float]:
        scores = [
            self.headline_clarity, self.niche_specificity, self.cta_quality,
            self.urgency, self.b2c_orientation, self.credibility,
            self.differentiation, self.conversion_potential,
        ]
        if any(s is None for s in scores):
            return None
        return sum(scores) / len(scores)

    def total(self) -> Optional[float]:
        sem = self.semantic_score()
        if sem is None:
            return None
        return (self.deterministic_score() + sem) / 2


SEMANTIC_DIMENSIONS = [
    "headline_clarity", "niche_specificity", "cta_quality", "urgency",
    "b2c_orientation", "credibility", "differentiation", "conversion_potential",
]


async def evaluate_with_llm(html: str, lead: dict, archetype: dict) -> Optional[Dict[str, float]]:
    """
    Avalia aspectos semânticos usando LLM-judge (mesmo mecanismo de llm_provider.py).
    Retorna None se o judge falhar (parsing inválido, LLM indisponível) — o
    chamador trata isso como score semântico indisponível, não como zero.
    """
    from llm_provider import call_llm, clean_json_payload
    import os

    prompt = f"""Você é um avaliador cético de qualidade de landing pages para negócios locais.

NEGÓCIO:
- Nome: {lead['name']}
- Nicho: {lead['niche']}
- Cidade: {lead['city']}
- Telefone: {lead['phone']}

ARQUÉTIPO APLICADO:
- Nome: {archetype.get('name', 'desconhecido')}
- Trust signals esperados: {archetype.get('trust_signals', [])}
- Cor: {archetype.get('primary_color', 'desconhecida')}

Avalie o HTML abaixo em 8 dimensões, cada uma de 0 a 5 (podem usar casas decimais):

1. headline_clarity: A headline comunica claramente o benefício para o consumidor final?
2. niche_specificity: O vocabulário e tom são específicos do nicho (não genéricos)?
3. cta_quality: O call-to-action é claro, acionável e apropriado ao nicho?
4. urgency: Existe um motivo concreto para o consumidor agir agora (não só a palavra "agora")?
5. b2c_orientation: A página vende para o consumidor final, sem linguagem de gestão/negócio?
6. credibility: Os claims (prova social) são específicos e críveis, não genéricos?
7. differentiation: A página se diferencia de um concorrente genérico do mesmo nicho?
8. conversion_potential: Um consumidor real clicaria no CTA depois de ler isso?

HTML (truncado):
{html[:3000]}

Responda APENAS com JSON puro, sem markdown, no formato exato:
{{"headline_clarity": 0.0, "niche_specificity": 0.0, "cta_quality": 0.0, "urgency": 0.0, "b2c_orientation": 0.0, "credibility": 0.0, "differentiation": 0.0, "conversion_potential": 0.0}}"""

    provider = os.getenv('PRIMARY_LLM', 'ollama')

    try:
        raw = call_llm(provider, prompt, 0.0)
        clean = clean_json_payload(raw)
        data = json.loads(clean)

        scores = {}
        for dim in SEMANTIC_DIMENSIONS:
            value = float(data.get(dim, 0.0))
            scores[dim] = max(0.0, min(5.0, value))  # clamp defensivo
        return scores

    except Exception as e:
        print(f"   [AVISO] LLM-judge falhou: {e}")
        return None


def evaluate_deterministic(html: str, lead: dict, archetype: dict) -> Dict[str, bool]:
    """Avalia aspectos estruturais de forma determinística."""
    html_lower = html.lower()
    return {
        "has_phone": bool(lead['phone']) and len(re.sub(r'\D', '', lead['phone'])) >= 8,
        "has_whatsapp": 'whatsapp' in html_lower or 'wa.me' in html_lower,
        "has_name": lead['name'].lower() in html_lower,
        "has_city": lead['city'].lower() in html_lower,
        "has_correct_archetype": archetype.get('primary_color', '\x00').lower() in html_lower,
        "has_hero": 'background-image' in html_lower,
        "has_trust_signals": any(s.lower() in html_lower for s in archetype.get('trust_signals', [])),
        "has_valid_html": '<html' in html_lower and '<body' in html_lower,
    }


QUALITY_LEADS = [
    {"name": "Padaria do Centro", "niche": "padaria", "city": "Goiânia", "phone": "(62) 9999-2001"},
    {"name": "Café & Pão", "niche": "padaria", "city": "Goiânia", "phone": "(62) 9999-2002"},
    {"name": "Restaurante do Mercado", "niche": "restaurante", "city": "Goiânia", "phone": "(62) 9999-2003"},
    {"name": "Cantina Italiana", "niche": "restaurante", "city": "Goiânia", "phone": "(62) 9999-2004"},
    {"name": "Oficina do Motor", "niche": "mecânica", "city": "Goiânia", "phone": "(62) 9999-2005"},
    {"name": "Auto Center", "niche": "mecânica", "city": "Goiânia", "phone": "(62) 9999-2006"},
    {"name": "Barbearia do Lago", "niche": "barbearia", "city": "Goiânia", "phone": "(62) 9999-2007"},
    {"name": "Barbearia Elite", "niche": "barbearia", "city": "Goiânia", "phone": "(62) 9999-2008"},
    {"name": "Salão da Ana", "niche": "salão", "city": "Goiânia", "phone": "(62) 9999-2009"},
    {"name": "Studio Hair", "niche": "salão", "city": "Goiânia", "phone": "(62) 9999-2010"},
    {"name": "Doces e Sabores", "niche": "confeitaria", "city": "Goiânia", "phone": "(62) 9999-2011"},
    {"name": "Bolo Caseiro", "niche": "confeitaria", "city": "Goiânia", "phone": "(62) 9999-2012"},
    {"name": "Academia Power", "niche": "academia", "city": "Goiânia", "phone": "(62) 9999-2013"},
    {"name": "CrossBox Goiânia", "niche": "academia", "city": "Goiânia", "phone": "(62) 9999-2014"},
    {"name": "Pet Shop do Bairro", "niche": "pet_shop", "city": "Goiânia", "phone": "(62) 9999-2015"},
    {"name": "Amigo Fiel Pet", "niche": "pet_shop", "city": "Goiânia", "phone": "(62) 9999-2016"},
    {"name": "Moda Feminina", "niche": "moda", "city": "Goiânia", "phone": "(62) 9999-2017"},
    {"name": "Boutique Elegance", "niche": "moda", "city": "Goiânia", "phone": "(62) 9999-2018"},
    {"name": "Farmácia do Povo", "niche": "farmácia", "city": "Goiânia", "phone": "(62) 9999-2019"},
    {"name": "Drogaria Saúde", "niche": "farmácia", "city": "Goiânia", "phone": "(62) 9999-2020"},
]


async def run_quality_gate() -> Dict[str, Any]:
    """Executa o Quality Gate B2C."""

    print("\n" + "="*70)
    print("QUALITY GATE B2C (LLM-JUDGE) - REFRAME")
    print("="*70 + "\n")

    from main import get_archetype_or_fail

    results = []
    metrics = {
        "total": len(QUALITY_LEADS),
        "published": 0,
        "failed": 0,
        "judge_failures": 0,
        "average_deterministic": 0.0,
        "average_semantic": 0.0,
        "average_total": 0.0,
        "deterministic_passes": 0,
        "semantic_passes": 0,
        "total_passes": 0,
    }

    semantic_count = 0

    for idx, lead_data in enumerate(QUALITY_LEADS, 1):
        print(f"\n[{idx}/{len(QUALITY_LEADS)}] {lead_data['name']} ({lead_data['niche']})")
        print("-" * 50)

        try:
            lead = Lead(
                id=f"lead_qg_{idx}", name=lead_data["name"], niche=lead_data["niche"],
                city=lead_data["city"], phone=lead_data["phone"]
            )
            leads_db.append(lead)

            gen = GenerationStatus(id=f"gen_qg_{idx}", lead_id=lead.id, status="queued")
            generations_db.append(gen)

            start = datetime.now()
            adapter = PipelineAdapter()
            result = await adapter.run(gen.id)
            elapsed = (datetime.now() - start).total_seconds()

            if result['status'] != 'published':
                metrics["failed"] += 1
                error_code = gen.error.get('code', 'unknown') if gen.error else 'unknown'
                print(f"   Falhou: {error_code}")
                results.append({"lead": lead_data, "status": "failed", "error": gen.error})
                continue

            gen = result['generation']
            metrics["published"] += 1

            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(gen.url, timeout=10.0)

            if response.status_code != 200:
                print(f"   URL inacessível: HTTP {response.status_code}")
                results.append({"lead": lead_data, "status": "inaccessible"})
                continue

            html = response.text
            archetype_key, archetype = get_archetype_or_fail(lead_data["niche"])

            det = evaluate_deterministic(html, lead_data, archetype)
            det_score = sum(det.values()) / len(det) * 5.0

            sem = await evaluate_with_llm(html, lead_data, archetype)
            sem_score = sum(sem.values()) / len(sem) if sem else None
            if sem_score is None:
                metrics["judge_failures"] += 1

            total_score = (det_score + sem_score) / 2 if sem_score is not None else None

            metrics["average_deterministic"] += det_score
            if det_score >= 4.0:
                metrics["deterministic_passes"] += 1

            if sem_score is not None:
                semantic_count += 1
                metrics["average_semantic"] += sem_score
                metrics["average_total"] += total_score
                if sem_score >= 4.0:
                    metrics["semantic_passes"] += 1
                if total_score >= 4.0:
                    metrics["total_passes"] += 1

            print(f"   Publicado: {gen.url}")
            print(f"   Arquétipo: {archetype_key}")
            print(f"   Determinístico: {det_score:.2f}/5.0"
                  + (f" | Semântico: {sem_score:.2f}/5.0" if sem_score is not None else " | Semântico: N/A"))
            print(f"   {elapsed:.2f}s")

            results.append({
                "lead": lead_data,
                "url": gen.url,
                "status": "published",
                "archetype": archetype_key,
                "deterministic": det,
                "deterministic_score": det_score,
                "semantic": sem,
                "semantic_score": sem_score,
                "total_score": total_score,
            })

        except Exception as e:
            metrics["failed"] += 1
            print(f"   Erro: {e}")
            results.append({"lead": lead_data, "status": "error", "error": str(e)})

    if metrics["published"] > 0:
        metrics["average_deterministic"] /= metrics["published"]
    if semantic_count > 0:
        metrics["average_semantic"] /= semantic_count
        metrics["average_total"] /= semantic_count

    return {"metrics": metrics, "results": results, "timestamp": datetime.now().isoformat()}


async def main():
    report = await run_quality_gate()

    print("\n" + "="*70)
    print("RELATÓRIO DO QUALITY GATE B2C")
    print("="*70)

    m = report["metrics"]
    print(f"\nMétricas:")
    print(f"   Total: {m['total']}")
    print(f"   Publicados: {m['published']}")
    print(f"   Falhas: {m['failed']}")
    print(f"   Falhas do LLM-judge: {m['judge_failures']}")
    print(f"   Determinístico médio: {m['average_deterministic']:.2f}/5.0")
    print(f"   Semântico médio: {m['average_semantic']:.2f}/5.0")
    print(f"   Total médio: {m['average_total']:.2f}/5.0")
    print(f"\n   Deterministic PASS (>=4.0): {m['deterministic_passes']}/{m['published']}")
    print(f"   Semantic PASS (>=4.0): {m['semantic_passes']}/{m['published']}")
    print(f"   Total PASS (>=4.0): {m['total_passes']}/{m['published']}")

    report_path = PROJECT_ROOT / "quality_gate_b2c_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str, ensure_ascii=False)

    print(f"\nRelatório salvo em: {report_path}")

    global leads_db, generations_db
    leads_db[:] = [l for l in leads_db if not l.id.startswith("lead_qg")]
    generations_db[:] = [g for g in generations_db if not g.id.startswith("gen_qg")]

if __name__ == "__main__":
    asyncio.run(main())
