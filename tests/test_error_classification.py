import pytest
from api.errors import ErrorCode, classify_error_by_code, extract_error_code, is_retryable_error
from api.pipeline_adapter import PipelineAdapter


class TestStructuredCodeExtraction:
    def test_extracts_known_code_prefix(self):
        assert extract_error_code("INVALID_LEAD: Telefone é obrigatório") == "INVALID_LEAD"
        assert extract_error_code("ARCHETYPE_NOT_SUPPORTED: Nicho 'x' não mapeado") == "ARCHETYPE_NOT_SUPPORTED"
        assert extract_error_code("R2_AUTH_ERROR: Access Denied") == "R2_AUTH_ERROR"

    def test_ignores_unknown_prefix(self):
        """Prefixo que não é um ErrorCode válido não deve ser extraído (evita falso-positivo)."""
        assert extract_error_code("SOME_RANDOM_THING: detalhe") is None

    def test_ignores_message_without_prefix(self):
        assert extract_error_code("Falha na geração de copy para 'Padaria X' após todas as tentativas.") is None

    def test_classify_error_by_code_known(self):
        assert classify_error_by_code("INVALID_LEAD") == ErrorCode.INVALID_LEAD
        assert classify_error_by_code("R2_UPLOAD_ERROR") == ErrorCode.R2_UPLOAD_ERROR

    def test_classify_error_by_code_unknown_falls_back_to_pipeline_error(self):
        assert classify_error_by_code("NOT_A_REAL_CODE") == ErrorCode.PIPELINE_ERROR


class TestErrorClassification:
    def test_invalid_lead_no_retry(self):
        """Telefone inválido (erro estruturado) → INVALID_LEAD → sem retry."""
        error = ValueError("INVALID_LEAD: Dados de negócio inválidos: Telefone é obrigatório")
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.INVALID_LEAD
        assert not is_retryable_error(code)

    def test_invalid_lead_independent_of_name(self):
        """Classificação não pode depender do nome do lead — só do código estruturado."""
        for name in ["Telefone Curto", "Doces da Maria", "Padaria Central", "Empresa Sem Nada A Ver"]:
            error = ValueError(f"INVALID_LEAD: Dados de negócio inválidos para '{name}': Telefone é obrigatório")
            code, _ = PipelineAdapter._classify_error(error)
            assert code == ErrorCode.INVALID_LEAD, f"Falhou para nome '{name}'"
            assert not is_retryable_error(code)

    def test_archetype_not_supported_no_retry(self):
        """Nicho desconhecido → ARCHETYPE_NOT_SUPPORTED → sem retry."""
        error = ValueError("ARCHETYPE_NOT_SUPPORTED: Nicho 'veterinária' não possui arquétipo mapeado.")
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.ARCHETYPE_NOT_SUPPORTED
        assert not is_retryable_error(code)

    def test_r2_auth_error_no_retry(self):
        """Erro de autenticação R2 (estruturado por publisher.py) → sem retry."""
        error = RuntimeError("R2_AUTH_ERROR: An error occurred (AccessDenied) when calling PutObject")
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.R2_AUTH_ERROR
        assert not is_retryable_error(code)

    def test_r2_upload_error_no_retry(self):
        """R2 com retries internos esgotados (estruturado por publisher.py) → sem retry
        na camada de cima (evita repetir LLM+render+publish sem necessidade)."""
        error = RuntimeError(
            "R2_UPLOAD_ERROR: Falha após 3 tentativas: An error occurred (InternalError) ..."
        )
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.R2_UPLOAD_ERROR
        assert not is_retryable_error(code)

    def test_slug_collision_no_retry(self):
        error = ValueError("SLUG_COLLISION: Slug 'estrela-padaria-goiania' já existe")
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.SLUG_COLLISION
        assert not is_retryable_error(code)

    def test_llm_quota_retryable_via_string_heuristic(self):
        """Erros crus de SDK (sem prefixo estruturado) ainda caem na heurística de string — e são retryable."""
        error = Exception("429 RESOURCE_EXHAUSTED: You exceeded your current quota")
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.LLM_QUOTA_EXCEEDED
        assert is_retryable_error(code)

    def test_llm_timeout_retryable(self):
        error = Exception("Request timeout after 30s")
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.LLM_TIMEOUT
        assert is_retryable_error(code)

    def test_generic_pipeline_error_retryable(self):
        """Erro sem código estruturado e sem match de heurística → PIPELINE_ERROR genérico → retryable."""
        error = Exception("Falha na geração de copy para 'Doces da Maria' após todas as tentativas.")
        code, _ = PipelineAdapter._classify_error(error)
        assert code == ErrorCode.PIPELINE_ERROR
        assert is_retryable_error(code)
