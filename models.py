import re
import hashlib
import unicodedata
from typing import Dict, List, Literal, Optional
from urllib.parse import quote
from pydantic import BaseModel, Field, model_validator, computed_field, field_validator, ValidationError

from design_system.location import BusinessLocation


def dns_safe_suffix(place_id: str) -> str:
    """Hash hex só com [a-f0-9], DNS seguro. Resolve _ do place_id."""
    return hashlib.sha256(place_id.encode('utf-8')).hexdigest()[:6]


def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return text or "site"


class _SlugValidator(BaseModel):
    slug: str

    @field_validator('slug')
    @classmethod
    def check_dns_safe(cls, v):
        if '_' in v or not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError(f"Slug gerado não é DNS-safe: {v}")
        return v


class EvidenceSource(BaseModel):
    """Fonte de uma evidência comercial (de onde ela veio, quão confiável é)."""
    type: Literal["google_places", "lead_input", "system", "verified"]
    confidence: float = Field(ge=0, le=1, description="0-1, confiança na evidência")
    verified: bool = False
    timestamp: Optional[str] = None
    reference: Optional[str] = Field(
        default=None, description="Identificador de origem, ex: place_id (Fase 17)"
    )


class CommercialEvidence(BaseModel):
    """
    Evidências comerciais do negócio — fatos verificáveis (ou pelo menos
    fornecidos por uma fonte real) que o LLM pode usar para gerar claims
    específicos (urgência, credibilidade, diferenciação) sem inventar.

    Fase 16: só a estrutura. Todos os campos ficam vazios por padrão — não há
    fonte de dados real (Google Places, CRM) conectada ainda. Preencher isso
    é o próximo passo natural para atacar os gargalos de Urgency/Credibility/
    Differentiation identificados nas Fases 15/15.2, mas está fora do escopo
    desta fase (ver critério "Foco: criar estrutura, não preencher dados").
    """
    opening_hours: Optional[str] = Field(
        default=None,
        description="Ex: 'Seg-Sex 08:00-18:00, Sáb 08:00-12:00'"
    )
    services: List[str] = Field(
        default_factory=list,
        description="Lista de serviços ou produtos oferecidos"
    )
    differentiators: List[str] = Field(
        default_factory=list,
        description="O que torna o negócio único"
    )
    credentials: List[str] = Field(
        default_factory=list,
        description="Certificações, anos de experiência, prêmios"
    )
    offers: List[str] = Field(
        default_factory=list,
        description="Ofertas válidas, descontos, combos"
    )
    availability: Optional[str] = Field(
        default=None,
        description="Disponibilidade atual (ex: 'Atende hoje até 18h')"
    )
    sources: Dict[str, EvidenceSource] = Field(
        default_factory=dict,
        description="Fonte/confiança de cada campo de evidência, por nome do campo"
    )

    @property
    def has_evidence(self) -> bool:
        """Verifica se há alguma evidência disponível."""
        return any([
            self.opening_hours,
            self.services,
            self.differentiators,
            self.credentials,
            self.offers,
            self.availability,
        ])

    @property
    def evidence_summary(self) -> str:
        """Resumo estruturado das evidências, pronto para injetar no prompt do LLM."""
        parts = []

        if self.opening_hours:
            parts.append(f"Horário de funcionamento: {self.opening_hours}")
        if self.services:
            parts.append(f"Serviços oferecidos: {', '.join(self.services)}")
        if self.differentiators:
            parts.append(f"Diferenciais: {', '.join(self.differentiators)}")
        if self.credentials:
            parts.append(f"Credenciais: {', '.join(self.credentials)}")
        if self.offers:
            parts.append(f"Ofertas: {', '.join(self.offers)}")
        if self.availability:
            parts.append(f"Disponibilidade: {self.availability}")

        return "\n".join(parts) if parts else "Nenhuma evidência comercial disponível."


class BusinessData(BaseModel):
    name: str = Field(..., min_length=2)
    niche: str = Field(..., min_length=2)
    city: str = Field(..., min_length=2)
    place_id: str = Field(..., min_length=6)
    phone: str = Field(default="")
    slug: str = Field(default="")
    evidence: CommercialEvidence = Field(default_factory=CommercialEvidence)
    location: Optional["BusinessLocation"] = Field(
        default=None,
        description="Localização determinística (VS-0). O LLM NÃO toca nela.",
    )

    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Telefone é obrigatório para geração de proposta com CTA WhatsApp.")
        digits = re.sub(r'\D', '', v)

        # Decide pelo COMPRIMENTO, não pelo prefixo — DDD 55 (Santa Maria/RS)
        # colide com o prefixo de país e torna o prefixo ambíguo como sinal.
        if len(digits) in (10, 11):
            digits = '55' + digits
        elif len(digits) in (12, 13) and digits.startswith('55'):
            pass
        # outros comprimentos caem direto na validação abaixo e falham com erro claro

        if not re.match(r'^55\d{10,11}$', digits):
            raise ValueError(f"Telefone inválido: {v}. Esperado 55 + DDD + 8-9 dígitos.")
        return digits

    @model_validator(mode='after')
    def generate_slug(self):
        if not self.slug:
            base = slugify(self.name)
            self.slug = f"{base}-{dns_safe_suffix(self.place_id)}"
        return self

    @classmethod
    def model_validate(cls, obj, **kwargs):
        instance = super().model_validate(obj, **kwargs)
        _SlugValidator(slug=instance.slug)
        return instance


class CopyData(BaseModel):
    headline: str = Field(..., min_length=5, max_length=80)
    subheadline: str = Field(..., min_length=5, max_length=140)
    cta_whatsapp: str = Field(..., min_length=2, max_length=30)
    pain_points: list[str] = Field(..., min_length=1, max_length=4)
    proofs: list[str] = Field(..., min_length=1, max_length=4)


class AssetsData(BaseModel):
    suggested_images_keywords: list[str] = Field(..., min_length=1, max_length=3)
    color_palette_hint: str = Field(..., min_length=3)
    primary_color: str = Field(default="#111827", pattern=r'^#[0-9a-fA-F]{6}$')


class SeoData(BaseModel):
    title: str = Field(..., min_length=5, max_length=70)
    description: str = Field(..., min_length=20, max_length=160)


class LLMOutput(BaseModel):
    """Trust boundary: LLM só pode retornar isso."""
    copywriting: CopyData
    assets: AssetsData
    seo: SeoData


def normalize_llm_output(raw: dict) -> dict:
    """
    Normaliza campos mecânicos do output do LLM antes da validação Pydantic.

    O LLM tende a exceder levemente os limites de tamanho (ex: 4-5 keywords
    em vez de 3, subheadline com 145 chars em vez de 140). Truncar aqui evita
    gastar tentativas de retry inteiras com um output que já está 90% correto.
    Não corrige problemas estruturais (JSON inválido, campos faltando) — só
    os limites de tamanho/quantidade que são responsabilidade nossa, não do LLM.
    """
    normalized = raw.copy()

    assets = normalized.get("assets")
    if isinstance(assets, dict):
        assets = assets.copy()
        keywords = assets.get("suggested_images_keywords")
        if isinstance(keywords, list) and len(keywords) > 3:
            assets["suggested_images_keywords"] = keywords[:3]
        normalized["assets"] = assets

    seo = normalized.get("seo")
    if isinstance(seo, dict):
        seo = seo.copy()
        title = seo.get("title")
        if isinstance(title, str) and len(title) > 70:
            seo["title"] = title[:67].rstrip() + "..."
        description = seo.get("description")
        if isinstance(description, str) and len(description) > 160:
            seo["description"] = description[:157].rstrip() + "..."
        normalized["seo"] = seo

    copywriting = normalized.get("copywriting")
    if isinstance(copywriting, dict):
        copywriting = copywriting.copy()
        subheadline = copywriting.get("subheadline")
        if isinstance(subheadline, str) and len(subheadline) > 140:
            copywriting["subheadline"] = subheadline[:137].rstrip() + "..."
        headline = copywriting.get("headline")
        if isinstance(headline, str) and len(headline) > 80:
            copywriting["headline"] = headline[:77].rstrip() + "..."
        cta = copywriting.get("cta_whatsapp")
        if isinstance(cta, str) and len(cta) > 30:
            copywriting["cta_whatsapp"] = cta[:30].rstrip()
        normalized["copywriting"] = copywriting

    return normalized


class ProposalTemplateData(BaseModel):
    business: BusinessData
    copywriting: CopyData
    assets: AssetsData
    seo: SeoData

    @computed_field
    @property
    def whatsapp_link(self) -> str:
        digits = re.sub(r'\D', '', self.business.phone)
        if not digits:
            return ""
        text = quote(self.copywriting.cta_whatsapp)
        return f"https://wa.me/{digits}?text={text}"
