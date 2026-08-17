"""
Códigos de erro estáveis para a API e pipeline.
Permite que a UI categorize erros sem depender de mensagens.
"""
import re
from enum import Enum
from typing import Dict, Optional

class ErrorCode(str, Enum):
    # LLM Errors
    LLM_AUTH_ERROR = "LLM_AUTH_ERROR"
    LLM_QUOTA_EXCEEDED = "LLM_QUOTA_EXCEEDED"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    OLLAMA_UNAVAILABLE = "OLLAMA_UNAVAILABLE"

    # R2 Errors
    R2_AUTH_ERROR = "R2_AUTH_ERROR"
    R2_UPLOAD_ERROR = "R2_UPLOAD_ERROR"
    R2_CONFIG_ERROR = "R2_CONFIG_ERROR"

    # Validation Errors
    INVALID_LEAD = "INVALID_LEAD"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ARCHETYPE_NOT_SUPPORTED = "ARCHETYPE_NOT_SUPPORTED"
    SLUG_COLLISION = "SLUG_COLLISION"

    # Pipeline Errors
    PIPELINE_ERROR = "PIPELINE_ERROR"
    GENERATION_FAILED = "GENERATION_FAILED"

    # Evidence Integrity Errors (Fase 17.1A) — o LLM distorceu um fato
    # verificável (CommercialEvidence) na copy gerada, ex: "1209 avaliações"
    # virando "1209 alunos". Ver validate_evidence_integrity.py.
    EVIDENCE_INTEGRITY_FAIL = "EVIDENCE_INTEGRITY_FAIL"
    EVIDENCE_NUMERIC_MISMATCH = "EVIDENCE_NUMERIC_MISMATCH"
    EVIDENCE_ENTITY_SUBSTITUTION = "EVIDENCE_ENTITY_SUBSTITUTION"
    EVIDENCE_UNSUPPORTED_INFERENCE = "EVIDENCE_UNSUPPORTED_INFERENCE"
    EVIDENCE_TIME_INTERPRETATION = "EVIDENCE_TIME_INTERPRETATION"
    EVIDENCE_GENERATION_ERROR = "EVIDENCE_GENERATION_ERROR"

# Mapeamento de mensagens amigáveis por código
USER_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.LLM_AUTH_ERROR: "Credenciais do provedor de IA inválidas. Verifique sua chave de API.",
    ErrorCode.LLM_QUOTA_EXCEEDED: "Cota do provedor de IA excedida. Verifique seu plano e faturamento.",
    ErrorCode.LLM_PROVIDER_ERROR: "Erro no provedor de IA. Tente novamente mais tarde.",
    ErrorCode.LLM_TIMEOUT: "Tempo limite excedido no provedor de IA.",
    ErrorCode.OLLAMA_UNAVAILABLE: "Ollama não está disponível. Verifique se o serviço está rodando.",
    ErrorCode.R2_AUTH_ERROR: "Credenciais do Cloudflare R2 inválidas. Verifique sua configuração.",
    ErrorCode.R2_UPLOAD_ERROR: "Falha ao publicar a landing no Cloudflare R2.",
    ErrorCode.R2_CONFIG_ERROR: "Configuração do Cloudflare R2 inválida.",
    ErrorCode.INVALID_LEAD: "Dados do lead inválidos. Verifique as informações.",
    ErrorCode.VALIDATION_ERROR: "Erro de validação nos dados gerados.",
    ErrorCode.ARCHETYPE_NOT_SUPPORTED: "Nicho não suportado pelo Reframe ainda. Nenhuma landing foi publicada.",
    ErrorCode.SLUG_COLLISION: "Já existe uma landing publicada com este identificador. Verifique se este lead já foi processado.",
    ErrorCode.PIPELINE_ERROR: "Erro interno no pipeline de geração.",
    ErrorCode.GENERATION_FAILED: "Falha na geração da landing.",
    ErrorCode.EVIDENCE_INTEGRITY_FAIL: "A copy gerada não preservou a integridade das evidências comerciais.",
    ErrorCode.EVIDENCE_NUMERIC_MISMATCH: "Números foram alterados ou arredondados indevidamente.",
    ErrorCode.EVIDENCE_ENTITY_SUBSTITUTION: "Entidades foram substituídas (ex: avaliações → clientes).",
    ErrorCode.EVIDENCE_UNSUPPORTED_INFERENCE: "Inferência não suportada pelas evidências.",
    ErrorCode.EVIDENCE_TIME_INTERPRETATION: "Horário foi interpretado de forma imprecisa.",
    ErrorCode.EVIDENCE_GENERATION_ERROR: "Erro ao validar integridade das evidências.",
}


def get_user_message(code: ErrorCode) -> str:
    """Retorna mensagem amigável para o usuário."""
    return USER_MESSAGES.get(code, "Erro desconhecido. Tente novamente mais tarde.")


def extract_error_code(error_str: str) -> Optional[str]:
    """
    Extrai um código de erro estruturado do início da mensagem, se presente.

    Convenção usada pelo próprio pipeline (não por exceções de bibliotecas
    externas como boto3/requests): exceções levantadas intencionalmente
    prefixam a mensagem com "CODIGO: detalhe" (ex: "INVALID_LEAD: Telefone
    é obrigatório...", "ARCHETYPE_NOT_SUPPORTED: Nicho 'x' não mapeado").

    Isso permite classificar por código em vez de depender de heurística de
    string sobre o conteúdo da mensagem — que pode colidir acidentalmente
    com o nome do lead ou outros dados variáveis.

    Retorna None se não houver prefixo reconhecível como ErrorCode válido.
    """
    m = re.match(r'^([A-Z][A-Z0-9_]*):\s', error_str)
    if not m:
        return None
    candidate = m.group(1)
    try:
        ErrorCode(candidate)
        return candidate
    except ValueError:
        return None


def classify_error_by_code(error_code: str) -> ErrorCode:
    """Classifica um código de erro estruturado (string) no ErrorCode correspondente."""
    try:
        return ErrorCode(error_code)
    except ValueError:
        return ErrorCode.PIPELINE_ERROR


def is_retryable_error(code: ErrorCode) -> bool:
    """Determina se um erro deve ser retentado."""
    # Erros de autenticação/configuração não melhoram com retry.
    # Erros de quota (429) são transitórios e devem ser retentados com backoff.
    NON_RETRYABLE = {
        ErrorCode.LLM_AUTH_ERROR,
        ErrorCode.R2_AUTH_ERROR,
        ErrorCode.R2_CONFIG_ERROR,
        ErrorCode.INVALID_LEAD,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.ARCHETYPE_NOT_SUPPORTED,
        ErrorCode.SLUG_COLLISION,
        # R2_UPLOAD_ERROR só é levantado DEPOIS que publish_to_r2 já esgotou
        # seus próprios 3 retries internos (com backoff). Deixar retryable
        # aqui faria o pipeline_adapter tentar de novo o fluxo inteiro
        # (LLM + render + publish), multiplicando o custo sem motivo — o
        # problema já foi dado como não-transitório na camada de baixo nível.
        ErrorCode.R2_UPLOAD_ERROR,
        # Violação de integridade de evidência é um problema de conteúdo
        # (LLM distorceu um fato), não uma falha transitória — retentar o
        # mesmo pipeline tende a reproduzir a mesma distorção. generate_
        # proposal_with_fallback já esgotou seus próprios retries/fallback
        # de provedor antes desse gate rodar (ver main.py).
        ErrorCode.EVIDENCE_INTEGRITY_FAIL,
        ErrorCode.EVIDENCE_NUMERIC_MISMATCH,
        ErrorCode.EVIDENCE_ENTITY_SUBSTITUTION,
        ErrorCode.EVIDENCE_UNSUPPORTED_INFERENCE,
        ErrorCode.EVIDENCE_TIME_INTERPRETATION,
    }
    return code not in NON_RETRYABLE