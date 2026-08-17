import pytest
from unittest.mock import patch, MagicMock
import llm_provider
from llm_provider import (
    clean_json_payload,
    generate_proposal_with_fallback,
)


def test_clean_json_payload_with_markdown():
    """Remove blocos de markdown do output do LLM."""
    raw = '''```json
{
  "copywriting": {"headline": "Teste"},
  "assets": {},
  "seo": {}
}
```'''
    clean = clean_json_payload(raw)
    assert clean.startswith('{')
    assert clean.endswith('}')
    assert '```' not in clean


def test_clean_json_payload_without_markdown():
    """JSON puro deve passar sem alteração."""
    raw = '{"copywriting": {"headline": "Teste"}, "assets": {}, "seo": {}}'
    clean = clean_json_payload(raw)
    assert clean == raw


@patch('llm_provider.call_ollama')
@patch('llm_provider.trigger_telegram_alert')
def test_generate_proposal_invalid_phone(mock_alert, mock_ollama):
    """Telefone inválido deve falhar rápido sem chamar LLM, com erro estruturado."""
    trusted_business = {
        "name": "Empresa Teste",
        "niche": "teste",
        "city": "Cidade",
        "place_id": "ChIJ_teste_invalid_phone",
        "phone": ""  # vazio
    }

    with pytest.raises(ValueError, match="INVALID_LEAD"):
        generate_proposal_with_fallback(trusted_business)

    assert mock_ollama.call_count == 0  # LLM não foi chamado
    assert mock_alert.call_count == 1  # Alerta foi disparado


@patch('llm_provider.call_ollama', return_value="response from ollama")
@patch('llm_provider.call_gemini', return_value="response from gemini")
def test_call_llm_dispatch(mock_gemini, mock_ollama):
    """call_llm deve dispatchar para o provedor correto."""
    from llm_provider import call_llm

    result_ollama = call_llm('ollama', 'prompt', 0.5)
    assert result_ollama == "response from ollama"
    mock_ollama.assert_called_once_with('prompt', 0.5)

    result_gemini = call_llm('gemini', 'prompt', 0.5)
    assert result_gemini == "response from gemini"
    mock_gemini.assert_called_once_with('prompt', 0.5)

    with pytest.raises(ValueError, match="Provedor LLM desconhecido"):
        call_llm('unknown', 'prompt', 0.5)
