import pytest
import os
import json
from unittest.mock import patch, MagicMock
from image_provider import get_hero_image, CACHE_FILE


@pytest.fixture(autouse=True)
def clean_cache():
    """Remove cache antes e depois de cada teste."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    yield
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)


@patch('image_provider.requests.get')
@patch.dict(os.environ, {"UNSPLASH_ACCESS_KEY": "test_key"})
def test_unsplash_success(mock_get):
    """Unsplash deve retornar URL real quando API responde com sucesso."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "urls": {"regular": "https://images.unsplash.com/photo-123"}
    }
    mock_get.return_value = mock_response
    
    url = get_hero_image(["padaria", "pão"], "padaria-central-abc123")
    
    assert "images.unsplash.com" in url
    assert "?v=" in url or "&v=" in url  # Sufixo único por lead
    assert mock_get.call_count == 1
    
    # Verifica autenticação via Header
    call_kwargs = mock_get.call_args[1]
    assert "Authorization" in call_kwargs["headers"]
    assert call_kwargs["headers"]["Authorization"] == "Client-ID test_key"


@patch('image_provider.requests.get')
@patch.dict(os.environ, {"UNSPLASH_ACCESS_KEY": "test_key"})
def test_unsplash_failure_fallback_picsum(mock_get):
    """Quando Unsplash falha, deve usar Picsum com seed determinístico."""
    mock_get.side_effect = Exception("API Error")
    
    url = get_hero_image(["padaria"], "padaria-central-abc123")
    
    assert "picsum.photos/seed/" in url
    assert "1200/600" in url
    assert "?v=" in url or "&v=" in url


@patch.dict(os.environ, {}, clear=True)
def test_no_unsplash_key_uses_picsum():
    """Sem UNSPLASH_ACCESS_KEY, deve usar Picsum diretamente."""
    url = get_hero_image(["oficina"], "oficina-mecanica-xyz789")
    
    assert "picsum.photos/seed/" in url
    assert "1200/600" in url


def test_cache_persistence():
    """Segunda chamada deve usar cache (sem chamar API novamente)."""
    with patch.dict(os.environ, {"UNSPLASH_ACCESS_KEY": "test_key"}):
        with patch('image_provider.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "urls": {"regular": "https://images.unsplash.com/photo-test"}
            }
            mock_get.return_value = mock_response

            # Primeira chamada: deve chamar API
            url1 = get_hero_image(["teste"], "lead-1")
            assert mock_get.call_count == 1

            # Segunda chamada (mesmo keyword): deve usar cache
            url2 = get_hero_image(["teste"], "lead-2")
            assert mock_get.call_count == 1  # API não foi chamada novamente

            # URLs devem ser diferentes (sufixo único por lead)
            assert url1 != url2
            assert "v=" in url1 and "v=" in url2


def test_cache_metadata():
    """Cache deve armazenar metadados de origem (unsplash vs picsum)."""
    with patch.dict(os.environ, {}, clear=True):
        get_hero_image(["teste"], "lead-test")
        
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        
        assert "teste" in cache
        assert "url" in cache["teste"]
        assert "source" in cache["teste"]
        assert cache["teste"]["source"] == "picsum"
