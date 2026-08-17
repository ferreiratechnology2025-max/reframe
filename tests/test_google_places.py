import os
import pytest
from unittest.mock import patch, AsyncMock
from google_places import GooglePlacesEnricher, is_available


class TestIsAvailable:
    @patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "fake_key"})
    def test_available_when_key_set(self):
        assert is_available() is True

    @patch.dict(os.environ, {}, clear=True)
    def test_not_available_without_key(self):
        assert is_available() is False


class TestGooglePlacesEnricher:
    @pytest.mark.asyncio
    async def test_enrich_without_api_key_returns_empty(self):
        enricher = GooglePlacesEnricher(api_key=None)
        evidence = await enricher.enrich("test_place_id")
        assert not evidence.has_evidence

    @pytest.mark.asyncio
    async def test_enrich_success_maps_opening_hours_rating_website(self):
        mock_response = {
            "rating": 4.5,
            "userRatingCount": 128,
            "regularOpeningHours": {
                "weekdayDescriptions": [
                    "Monday: 8:00 AM – 6:00 PM",
                    "Tuesday: 8:00 AM – 6:00 PM",
                ]
            },
            "websiteUri": "https://example.com",
        }

        enricher = GooglePlacesEnricher(api_key="fake_key")

        with patch.object(enricher, '_get_place_details', AsyncMock(return_value=mock_response)):
            evidence = await enricher.enrich("test_place_id")

        assert evidence.opening_hours is not None
        assert "8:00 AM" in evidence.opening_hours
        assert any("4.5/5" in c for c in evidence.credentials)
        assert any("128 avaliações" in c for c in evidence.credentials)
        assert any("example.com" in s for s in evidence.services)
        assert evidence.sources['opening_hours'].type == 'google_places'
        assert evidence.sources['opening_hours'].reference == 'test_place_id'
        assert evidence.has_evidence

    @pytest.mark.asyncio
    async def test_enrich_low_rating_not_used_as_credential(self):
        """Avaliação abaixo de 4.0 não deve virar um claim (seria contraproducente)."""
        mock_response = {"rating": 3.2}
        enricher = GooglePlacesEnricher(api_key="fake_key")

        with patch.object(enricher, '_get_place_details', AsyncMock(return_value=mock_response)):
            evidence = await enricher.enrich("test_place_id")

        assert evidence.credentials == []
        assert not evidence.has_evidence

    @pytest.mark.asyncio
    async def test_enrich_missing_place_returns_empty(self):
        """place_id inexistente/sintético — API retorna None, sem quebrar o pipeline."""
        enricher = GooglePlacesEnricher(api_key="fake_key")

        with patch.object(enricher, '_get_place_details', AsyncMock(return_value=None)):
            evidence = await enricher.enrich("padaria-sintetico-api")

        assert not evidence.has_evidence

    @pytest.mark.asyncio
    async def test_enrich_swallows_exceptions(self):
        """Qualquer erro inesperado durante o enriquecimento não deve propagar —
        enriquecimento é um "nice to have", nunca pode derrubar o pipeline."""
        enricher = GooglePlacesEnricher(api_key="fake_key")

        with patch.object(enricher, '_get_place_details', AsyncMock(side_effect=RuntimeError("boom"))):
            evidence = await enricher.enrich("test_place_id")

        assert not evidence.has_evidence

    @pytest.mark.asyncio
    async def test_get_place_details_http_error_returns_none(self):
        enricher = GooglePlacesEnricher(api_key="fake_key")

        class FakeResponse:
            status_code = 404

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, *a, **kw):
                return FakeResponse()

        with patch('google_places.httpx.AsyncClient', return_value=FakeClient()):
            details = await enricher._get_place_details("nonexistent_place_id")

        assert details is None
