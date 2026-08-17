import os
import re
import logging
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models import ProposalTemplateData, CommercialEvidence, slugify
from llm_provider import generate_proposal_with_fallback
from publisher import publish_to_r2
from config.archetypes import ARCHETYPES_CONFIG
from validate_evidence_integrity import EvidenceIntegrityValidator

# Carrega variáveis de ambiente do .env
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def _normalize_key(text: str) -> str:
    """Remove acentos e converte para lowercase para matching fuzzy de nicho."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9]', '', text.lower())
    return text


def resolve_archetype(niche: str) -> Optional[Tuple[str, dict]]:
    """
    Resolve o arquétipo para o nicho via matching fuzzy contra a chave do
    arquétipo e seus aliases (todos normalizados do mesmo jeito que o nicho,
    para que underscore/acento não quebrem o match — ex: "pet_shop" == "petshop").

    Retorna (archetype_key, config) ou None se o nicho não tiver arquétipo mapeado.

    NÃO cai de volta para um arquétipo genérico — publicar landing com
    imagem/prova social de outro nicho é pior do que não publicar.
    """
    key = _normalize_key(niche)
    if not key:
        return None

    for archetype_key, config in ARCHETYPES_CONFIG.items():
        candidates = [archetype_key] + config.get("aliases", [])
        for candidate in candidates:
            normalized_candidate = _normalize_key(candidate)
            if normalized_candidate and (normalized_candidate in key or key in normalized_candidate):
                return archetype_key, config
    return None


def get_archetype_or_fail(niche: str) -> Tuple[str, dict]:
    """Resolve o arquétipo ou levanta ValueError com código estável ARCHETYPE_NOT_SUPPORTED."""
    resolved = resolve_archetype(niche)
    if resolved is None:
        raise ValueError(
            f"ARCHETYPE_NOT_SUPPORTED: Nicho '{niche}' não possui arquétipo mapeado. "
            f"Suportados: {list(ARCHETYPES_CONFIG.keys())}"
        )
    return resolved


def synthetic_place_id(name: str, niche: str, city: str) -> str:
    """
    Gera um place_id sintético determinístico para leads sem place_id real do
    Google Places (ex: cadastro manual via API/formulário).

    Inclui nicho e cidade, não só o nome — dois leads com o mesmo nome
    (comum: "Estrela", "Central", "São José"...) em nichos ou cidades
    diferentes precisam de place_ids (e portanto slugs) diferentes, senão
    colidem no mesmo objeto no R2 e um sobrescreve o outro silenciosamente.

    Última linha de defesa (não garante unicidade absoluta): dois leads REAIS
    e diferentes com nome+nicho+cidade idênticos ainda colidiriam aqui — ver
    resolve_place_id(), que prioriza `lead_id` (garantidamente único, quando
    disponível) sobre este hash antes de cair nele.
    """
    return f"{slugify(name)}-{slugify(niche)}-{slugify(city)}-api"


def resolve_place_id(
    place_id: Optional[str],
    lead_id: Optional[str],
    name: str,
    niche: str,
    city: str
) -> str:
    """
    Contrato de identidade do lead, usado para derivar um place_id estável
    (e por consequência um slug único — ver models.BusinessData.generate_slug).

    Prioridade:
    1. place_id real (Google Places) — a fonte da verdade quando existe.
    2. lead_id (ID interno do registro, ex: api/app.py Lead.id) — não vem do
       Google, mas é garantidamente único dentro do sistema (cada lead
       cadastrado tem um id próprio), então é mais seguro que o fallback 3.
    3. Hash sintético de nome+nicho+cidade — reduz colisões (Fase 14.1) mas
       não as elimina: dois leads reais diferentes com nome, nicho e cidade
       idênticos ainda produziriam o mesmo resultado aqui. Sem um place_id
       real ou um lead_id, essa ambiguidade é inerente ao dado disponível.
    """
    if place_id:
        return place_id
    if lead_id:
        return f"lead-{slugify(str(lead_id))}"
    return synthetic_place_id(name, niche, city)


def _evidence_integrity_gate(proposal_data: ProposalTemplateData) -> None:
    """
    Gate obrigatório de integridade de evidências (Fase 17.1A), executado
    ANTES da publicação — e antes do arquétipo sobrescrever `proofs` (passo
    seguinte em process_lead/generate_landing), para validar exatamente o
    que o LLM gerou a partir da evidência, não o que o arquétipo
    determinístico (travado, fora de escopo aqui) coloca depois.

    Bloqueia (raises ValueError com prefixo "EVIDENCE_INTEGRITY_FAIL:",
    reconhecido por api/errors.py::extract_error_code) quando há violação
    crítica — ex: "1209 avaliações" virando "1209 alunos". Violações não
    críticas (severity medium/low) só são logadas.
    """
    evidence = proposal_data.business.evidence
    if not evidence.has_evidence:
        return

    copy = proposal_data.copywriting
    combined_text = " ".join([
        copy.headline,
        copy.subheadline,
        copy.cta_whatsapp,
        *copy.pain_points,
        *copy.proofs,
    ])

    result = EvidenceIntegrityValidator(evidence).validate(combined_text)

    for violation in result.violations:
        logging.warning(
            f"Evidence Integrity Violation [{violation.code.value}] ({violation.severity}): {violation.message}"
        )

    critical = result.critical_violations
    if critical:
        raise ValueError(
            f"EVIDENCE_INTEGRITY_FAIL: {len(critical)} violação(ões) crítica(s) de integridade "
            f"de evidência detectada(s): {'; '.join(v.message for v in critical)}"
        )


def process_lead(trusted_business: dict) -> str | None:
    place_id = trusted_business.get('place_id', 'UNKNOWN')
    logging.info(f"Iniciando processamento: {trusted_business.get('name')} ({place_id})")

    # 1. Resolução do Arquétipo (fail-fast: sem arquétipo mapeado, nem chama o LLM)
    try:
        archetype_key, config = get_archetype_or_fail(trusted_business.get('niche', ''))
    except ValueError as e:
        logging.error(f"Arquétipo não suportado, lead descartado: {e}")
        return None

    # 2. Geração de Proposta (LLM com fallback)
    try:
        proposal_data = generate_proposal_with_fallback(trusted_business)
    except ValueError as e:
        logging.error(f"Lead inválido, descartado: {e}")
        return None
    if not proposal_data:
        return None

    # 2.5. Gate de Integridade de Evidências (Fase 17.1A) — bloqueia
    # publicação se o LLM distorceu um fato verificável.
    try:
        _evidence_integrity_gate(proposal_data)
    except ValueError as e:
        logging.error(f"Gate de integridade de evidências reprovou o lead: {e}")
        return None

    # 3. Aplicação do Arquétipo Determinístico (Sobrescreve alucinações do LLM)
    proposal_data.copywriting.proofs = config["trust_signals"]
    proposal_data.assets.primary_color = config["primary_color"]
    hero_image_url = config["hero_image"]
    logging.info(f"Arquétipo '{archetype_key}' aplicado. Imagem e cores travadas.")

    # 4. Renderização do Template
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')

    data_dict = proposal_data.model_dump()
    data_dict['hero_image_url'] = hero_image_url

    html_final = template.render(data=data_dict)

    # 5. Publicação no R2
    try:
        final_url = publish_to_r2(proposal_data, html_final)
        logging.info(f"SUCESSO: {final_url}")
        return final_url
    except Exception as e:
        logging.error(f"FALHA NA PUBLICACAO: {e}")
        return None


async def generate_landing(
    lead_name: str,
    niche: str,
    city: str,
    phone: str,
    place_id: Optional[str] = None,
    lead_id: Optional[str] = None,
    evidence: Optional[CommercialEvidence] = None,
    on_progress: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Função de entrada principal do pipeline, exportável para a API.

    Encapsula toda a lógica de geração reutilizando os componentes existentes.
    Pode ser chamada pela CLI, por scripts ou pela API (via adaptador).

    Args:
        lead_name: Nome do negócio.
        niche: Nicho (ex: "padaria artesanal").
        city: Cidade do negócio.
        phone: Telefone (normalizado por BusinessData).
        place_id: ID do Google Places (opcional, usado para slug — prioridade máxima).
        lead_id: ID interno do lead (opcional; ex: api/app.py Lead.id). Usado
            para derivar o slug quando não há place_id real — ver
            resolve_place_id(). Garantidamente único dentro do sistema,
            então é preferido sobre o hash sintético de nome+nicho+cidade.
        evidence: Evidências comerciais (horário, ofertas, diferenciais, etc)
            usadas pelo LLM como única fonte de fatos específicos — ver
            models.CommercialEvidence. Opcional; sem evidência, o LLM é
            instruído a não inventar esses fatos (Fase 16).
        on_progress: Callback de progresso recebendo o estágio atual.

    Returns:
        Dict com os resultados finais (archetype_name, primary_color,
        hero_image, proofs, headline, subheadline, cta, url).

    Raises:
        ValueError: Se o nicho não tiver arquétipo mapeado (ARCHETYPE_NOT_SUPPORTED)
            ou se a geração de copy falhar após todas as tentativas.
        Exception: Se a publicação no R2 falhar.
    """
    trusted_business = {
        "name": lead_name,
        "niche": niche,
        "city": city,
        "place_id": resolve_place_id(place_id, lead_id, lead_name, niche, city),
        "phone": phone,
        "evidence": evidence or CommercialEvidence(),
    }

    # 1. Resolução do Arquétipo (fail-fast: sem arquétipo mapeado, nem chama o LLM)
    archetype_key, config = get_archetype_or_fail(niche)

    if on_progress:
        on_progress("generating")

    # 2. Geração de Proposta (LLM com fallback) — mesma lógica do process_lead
    proposal_data = generate_proposal_with_fallback(trusted_business)
    if not proposal_data:
        raise ValueError(
            f"Falha na geração de copy para '{lead_name}' após todas as tentativas."
        )

    # 2.5. Gate de Integridade de Evidências (Fase 17.1A) — bloqueia
    # publicação se o LLM distorceu um fato verificável. Levanta ValueError
    # estruturado ("EVIDENCE_INTEGRITY_FAIL: ...") reconhecido por
    # api/errors.py, propagado ao pipeline_adapter sem retry (não-transitório).
    _evidence_integrity_gate(proposal_data)

    # 3. Aplicação do Arquétipo Determinístico
    proposal_data.copywriting.proofs = config["trust_signals"]
    proposal_data.assets.primary_color = config["primary_color"]
    hero_image_url = config["hero_image"]

    if on_progress:
        on_progress("rendering")

    # 4. Renderização do Template
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / 'templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')

    data_dict = proposal_data.model_dump()
    data_dict['hero_image_url'] = hero_image_url

    html_final = template.render(data=data_dict)

    if on_progress:
        on_progress("publishing")

    # 5. Publicação no R2
    final_url = publish_to_r2(proposal_data, html_final)
    logging.info(f"Publicado pela API: {final_url}")

    return {
        "archetype_name": archetype_key,
        "primary_color": config["primary_color"],
        "hero_image": hero_image_url,
        "proofs": config["trust_signals"],
        "headline": proposal_data.copywriting.headline,
        "subheadline": proposal_data.copywriting.subheadline,
        "cta": proposal_data.copywriting.cta_whatsapp,
        "url": final_url,
    }


def main():
    """Ponto de entrada principal. Simula o processamento de leads."""
    logging.info("Iniciando Pipeline Reframe...")
    
    # Simulação de leads vindos da etapa de Descoberta (Places API)
    # Teste 1: Lead válido e completo
    lead_1 = {
        "name": "Padaria Central",
        "niche": "padaria artesanal",
        "city": "Goiânia",
        "place_id": "ChIJ_teste_padaria_123",
        "phone": "62999998888"
    }
    
    # Teste 2: Lead com DDD 55 (Santa Maria/RS) para validar a correção
    lead_2 = {
        "name": "Oficina do João",
        "niche": "mecânica automotiva",
        "city": "Santa Maria",
        "place_id": "ChIJ_teste_oficina_55",
        "phone": "55991234567"  # DDD 55 sem código de país
    }
    
    # Teste 3: Lead inválido (telefone vazio) para validar o fail-fast
    lead_3 = {
        "name": "Empresa Fantasma",
        "niche": "consultoria",
        "city": "São Paulo",
        "place_id": "ChIJ_teste_fantasma",
        "phone": ""
    }
    
    leads_to_process = [lead_1, lead_2, lead_3]
    
    for i, lead in enumerate(leads_to_process, 1):
        logging.info(f"\n{'='*50}")
        logging.info(f"PROCESSANDO LEAD {i}/{len(leads_to_process)}")
        logging.info(f"{'='*50}")
        
        url = process_lead(lead)
        
        if url:
            logging.info(f"URL Final: {url}")
        else:
            logging.warning(f"Lead {i} ({lead.get('name')}) foi descartado ou falhou.")
            
    logging.info("\nPipeline concluído.")


if __name__ == "__main__":
    main()
