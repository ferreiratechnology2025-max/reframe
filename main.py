import os
import re
import asyncio
import logging
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models import ProposalTemplateData, CommercialEvidence, slugify, BusinessData
from llm_provider import generate_proposal_with_fallback
from publisher import publish_to_r2
from config.archetypes import ARCHETYPES_CONFIG
from validate_evidence_integrity import EvidenceIntegrityValidator

# ─── Design System Engine (VS-0) ─────────────────────────────────────
from design_system.design_tokens import ColorRole, DesignTokens, FontSpec, SemanticColor, TypographyPolicy
from design_system.evidence_positioning import EvidencePositioningEngine
from design_system.location import BusinessLocation
from engines.theme_resolver import VisualThemeResolver, ThemeResolutionError
from engines.design_tokens_engine import DesignTokensEngine
from gates.design_token_gate import DesignTokenGate
from gates.rendered_visual_gate import RenderedVisualGate

from api.errors import extract_error_code

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


def _run_visual_gate_sync(html: str, policy, niche: str) -> tuple[bool, list]:
    """Executa o RenderedVisualGate (Playwright + Chromium headless)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            return RenderedVisualGate().validate(html, browser, policy, niche=niche)
        finally:
            browser.close()


async def _run_visual_gate(html: str, policy, niche: str) -> tuple[bool, list]:
    """Wrapper async: roda o gate síncrono em thread (Playwright Sync não pode
    rodar dentro do loop asyncio)."""
    return await asyncio.to_thread(_run_visual_gate_sync, html, policy, niche)


def _archetype_tokens_css(primary_color: str) -> str:
    """Tokens mínimos para o caminho LEGACY (process_lead/CLI).

    O legacy usa a cor primária do arquétipo como accent. Não passa pelo
    DesignTokenGate (é caminho antigo); o novo fluxo (generate_landing)
    usa o DesignTokensEngine e passa por todos os gates.
    """
    tokens = DesignTokens(
        personality="legacy",
        colors={
            ColorRole.BG: "#FAFAF7",
            ColorRole.SURFACE: "#FFFFFF",
            ColorRole.TEXT: "#1A1A1A",
            ColorRole.TEXT_SECONDARY: "#4A4A4A",
            ColorRole.HEADING: "#1A1A1A",
            ColorRole.BORDER: "#E5E7EB",
            ColorRole.ACCENT: primary_color,
            ColorRole.ACCENT_HOVER: primary_color,
            ColorRole.ON_ACCENT: "#FFFFFF",
            ColorRole.ON_OVERLAY: "#FFFFFF",
        },
        semantic_colors={
            SemanticColor.SUCCESS: "#2E7D32",
            SemanticColor.WARNING: "#B26A00",
            SemanticColor.ERROR: "#C62828",
            SemanticColor.INFO: "#1565C0",
        },
        typography=TypographyPolicy(
            heading=FontSpec(family="Inter", source="system", weights=[400, 600]),
            body=FontSpec(family="Inter", source="system", weights=[400, 500]),
        ),
    )
    return tokens.get_css_variables()


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
    data_dict['tokens_css'] = _archetype_tokens_css(config["primary_color"])
    data_dict['font_links'] = ""
    data_dict['location'] = trusted_business.get("location")

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
    location: Optional[BusinessLocation] = None,
    on_progress: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Função de entrada principal do pipeline — ORQUESTRAÇÃO (VS-0).

    O novo fluxo NÃO depende do legacy (resolve_archetype/get_archetype_or_fail):
    nicho não mapeado no Design System simplesmente falha com código estável
    (POSITIONING_UNDETERMINED/THEME_UNRESOLVED) em vez de ser barrado antes
    de chegar ao sistema de design.

    Fluxo:
      Evidence → Positioning (determinístico) → Theme Resolver → Design Tokens
      → DesignTokenGate → LLM Copy → Evidence Integrity Gate → Render
      → RenderedVisualGate → Publish.

    O LLM escreve SOMENTE a copy; posicionamento, tema e tokens são decisões
    determinísticas do Design System Engine.

    Args:
        lead_name: Nome do negócio.
        niche: Nicho (ex: "estetica").
        city: Cidade do negócio.
        phone: Telefone (normalizado por BusinessData).
        place_id: ID do Google Places (opcional, usado para slug).
        lead_id: ID interno do lead (opcional).
        evidence: Evidências comerciais (única fonte de fatos para o LLM).
        location: Localização determinística (VS-0).
        on_progress: Callback de progresso recebendo o estágio atual.

    Returns:
        Dict com status ("published" ou "failed") + dados. Em falha de
        posicionamento/tema/tokens/render, retorna {"status": "failed",
        "error": <ErrorCode>, ...} — o pipeline_adapter traduz para o status
        correto da geração (ver api/pipeline_adapter.py::run).
    """
    trusted_business = {
        "name": lead_name,
        "niche": niche,
        "city": city,
        "place_id": resolve_place_id(place_id, lead_id, lead_name, niche, city),
        "phone": phone,
        "evidence": evidence or CommercialEvidence(),
    }
    if location is not None:
        trusted_business["location"] = location

    # ── 1. POSITIONING (determinístico — nunca LLM) ──────────────────
    commercial = trusted_business["evidence"]
    positioning = EvidencePositioningEngine().determine(
        niche=niche,
        evidence={
            "rating": commercial.rating,
            "total_ratings": commercial.total_ratings,
            "specialties": commercial.specialties,
        },
    )
    if positioning.is_undetermined:
        return {
            "status": "failed",
            "error": "POSITIONING_UNDETERMINED",
            "detail": "; ".join(positioning.decision_reasons),
            "segment": positioning.segment,
        }

    # ── 2. THEME RESOLVER (position-only, sem fallback silencioso) ─────
    try:
        visual_template = VisualThemeResolver().resolve(niche, positioning.market_position)
    except ThemeResolutionError as e:
        return {"status": "failed", "error": "THEME_UNRESOLVED", "detail": str(e)}

    # ── 3. DESIGN TOKENS + POLICY (determinísticos) ──────────────────
    tokens, policy = DesignTokensEngine().generate(visual_template)

    # ── 4. DESIGN TOKEN GATE (ANTES do LLM) ──────────────────────────
    passed, issues = DesignTokenGate().validate(tokens, policy)
    if not passed:
        return {
            "status": "failed",
            "error": "DESIGN_TOKEN_GATE_FAILED",
            "issues": issues,
            "personality": visual_template.id,
        }

    if on_progress:
        on_progress("generating")

    # ── 5. LLM COPY (o LLM só escreve copy) ──────────────────────────
    proposal_data = generate_proposal_with_fallback(trusted_business)
    if not proposal_data:
        return {
            "status": "failed",
            "error": "GENERATION_FAILED",
            "detail": f"Falha na geração de copy para '{lead_name}' após todas as tentativas.",
        }

    # ── 6. EVIDENCE INTEGRITY GATE (a copy não pode distorcer fatos) ─
    try:
        _evidence_integrity_gate(proposal_data)
    except ValueError as e:
        code = extract_error_code(str(e)) or "EVIDENCE_INTEGRITY_FAIL"
        return {"status": "failed", "error": code, "detail": str(e)}

    if on_progress:
        on_progress("rendering")

    # ── 7. RENDER com tokens (hex vive só no bloco :root) ────────────
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / 'templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')

    data_dict = proposal_data.model_dump()
    data_dict['hero_image_url'] = policy.hero_image
    data_dict['tokens_css'] = tokens.get_css_variables()
    data_dict['font_links'] = tokens.get_font_links()
    data_dict['location'] = location.model_dump() if location is not None else None

    html_final = template.render(data=data_dict)

    # ── 8. RENDERED VISUAL GATE (Playwright, 3 viewports) ────────────
    passed, issues = await _run_visual_gate(html_final, policy, niche)
    if not passed:
        return {
            "status": "failed",
            "error": "RENDERED_VISUAL_GATE_FAILED",
            "issues": issues,
            "personality": visual_template.id,
        }

    if on_progress:
        on_progress("publishing")

    # ── 9. PUBLISH (R2) ──────────────────────────────────────────────
    final_url = publish_to_r2(proposal_data, html_final)
    logging.info(f"Publicado pela API: {final_url}")

    return {
        "status": "published",
        "url": final_url,
        "personality": visual_template.id,
        "archetype_name": policy.archetype.value,
        "position": positioning.market_position.value,
        "primary_color": tokens.colors[ColorRole.ACCENT],
        "hero_image": policy.hero_image,
        "proofs": proposal_data.copywriting.proofs,
        "headline": proposal_data.copywriting.headline,
        "subheadline": proposal_data.copywriting.subheadline,
        "cta": proposal_data.copywriting.cta_whatsapp,
        "tokens": tokens.model_dump(mode="json"),
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
