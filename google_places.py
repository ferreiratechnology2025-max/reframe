"""
Integração com Google Places API (New, v1) para enriquecimento de leads
com evidências comerciais reais (models.CommercialEvidence).

NOTA: sem GOOGLE_PLACES_API_KEY configurada neste ambiente, este módulo
nunca foi exercitado contra a API real — apenas com mocks (tests/test_google_places.py).
Os nomes de campo usados no parsing seguem o schema documentado da Places
API (New) v1 (camelCase: regularOpeningHours, websiteUri, etc), consistente
com o FieldMask pedido na requisição. Confirmar contra uma chamada real
assim que houver uma API key disponível.
"""
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import httpx

from models import CommercialEvidence, EvidenceSource

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Verifica se a integração com Google Places está configurada."""
    return bool(os.getenv('GOOGLE_PLACES_API_KEY'))


class GooglePlacesEnricher:
    """Enriquece leads com dados do Google Places (New API v1)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        self.base_url = "https://places.googleapis.com/v1"

        if not self.api_key:
            logger.warning("Google Places API key não configurada.")

    async def enrich(self, place_id: str) -> CommercialEvidence:
        """
        Busca dados do Google Places e retorna CommercialEvidence.
        Nunca levanta exceção — qualquer falha (sem API key, erro de rede,
        place_id inválido/sintético) resulta em CommercialEvidence() vazia,
        preservando o comportamento "sem invenção" do prompt (Fase 16).
        """
        if not self.api_key:
            return CommercialEvidence()

        try:
            details = await self._get_place_details(place_id)
            if not details:
                return CommercialEvidence()

            return self._to_evidence(details, place_id)

        except Exception as e:
            logger.error(f"Erro ao enriquecer place_id {place_id}: {e}")
            return CommercialEvidence()

    def _to_evidence(self, details: Dict[str, Any], place_id: str) -> CommercialEvidence:
        """Mapeia a resposta da Places API v1 para CommercialEvidence."""
        evidence = CommercialEvidence()
        now = datetime.now().isoformat()

        # Horários de funcionamento
        hours = details.get('regularOpeningHours')
        if hours and hours.get('weekdayDescriptions'):
            evidence.opening_hours = '\n'.join(hours['weekdayDescriptions'])
            evidence.sources['opening_hours'] = EvidenceSource(
                type='google_places', confidence=0.95, verified=True,
                timestamp=now, reference=place_id
            )

        # Avaliação — só usamos como credencial se for realmente boa (>=4.0),
        # senão vira um claim contra o negócio, não a favor.
        rating = details.get('rating')
        if rating is not None and rating >= 4.0:
            count = details.get('userRatingCount')
            text = f"Avaliação {rating}/5 no Google"
            if count:
                text += f" ({count} avaliações)"
            evidence.credentials.append(text)
            evidence.sources['rating'] = EvidenceSource(
                type='google_places', confidence=0.9, verified=True,
                timestamp=now, reference=place_id
            )

        # Site oficial
        website = details.get('websiteUri')
        if website:
            evidence.services.append(f"Site oficial: {website}")
            evidence.sources['website'] = EvidenceSource(
                type='google_places', confidence=0.95, verified=True,
                timestamp=now, reference=place_id
            )

        # NOTA: 'types', 'editorialSummary' e 'formattedAddress' vêm na
        # resposta mas não são mapeados para evidência ainda — confiança
        # baixa demais para virar claim específico sem revisão humana.
        # Candidatos naturais para uma próxima iteração.

        return evidence

    async def _get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Busca detalhes do lugar via Google Places API (New) v1."""
        url = f"{self.base_url}/places/{place_id}"

        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,types,rating,userRatingCount,"
                "regularOpeningHours,websiteUri,internationalPhoneNumber,"
                "editorialSummary,googleMapsUri,priceLevel,primaryType"
            ),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    return response.json()
                logger.error(
                    f"Google Places API error: HTTP {response.status_code} para place_id={place_id}"
                )
                return None
        except Exception as e:
            logger.error(f"Erro na requisição Google Places: {e}")
            return None
