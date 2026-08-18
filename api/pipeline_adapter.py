"""
Adaptador entre a API e o pipeline Reframe existente.
Não modifica o código original - apenas o envolve.

Importa api.app de forma LAZY para evitar import circular
(app.py importa run_pipeline_task no topo).
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Tuple, Optional
from datetime import datetime

# Adiciona a raiz do projeto ao path para importar main.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main import generate_landing  # Função exportável do pipeline
from models import CommercialEvidence
import google_places
from api.errors import (
    ErrorCode,
    get_user_message,
    is_retryable_error,
    extract_error_code,
    classify_error_by_code,
)


class PipelineAdapter:
    """Adaptador que executa o pipeline e atualiza o status."""

    @staticmethod
    async def run(gen_id: str) -> Dict[str, Any]:
        """
        Executa o pipeline para uma geração específica.
        Atualiza o status no banco em memória.
        Classifica erros em códigos estáveis.

        Status: queued -> generating -> rendering -> publishing -> published|failed
        """
        # Import lazy para evitar import circular com app.py
        from api.app import generations_db, leads_db

        # Busca a geração
        gen = next((g for g in generations_db if g.id == gen_id), None)
        if not gen:
            raise ValueError(f"Generation {gen_id} not found")

        # Busca o lead
        lead = next((l for l in leads_db if l.id == gen.lead_id), None)
        if not lead:
            raise ValueError(f"Lead {gen.lead_id} not found")

        def progress(stage: str) -> None:
            gen.status = stage
            gen.updated_at = datetime.now()

        # Enriquecer com Google Places, uma única vez (não a cada retry) —
        # só faz sentido se o lead tiver um place_id real (não o sintético
        # que main.py::resolve_place_id gera internamente quando ausente).
        # Qualquer falha aqui (sem API key, erro de rede, place_id inválido)
        # já retorna CommercialEvidence() vazia — nunca propaga exceção.
        evidence = CommercialEvidence()
        if lead.place_id and google_places.is_available():
            enricher = google_places.GooglePlacesEnricher()
            evidence = await enricher.enrich(lead.place_id)
            if evidence.has_evidence:
                logging.info(f"Lead {lead.id} enriquecido com dados do Google Places")

        try:
            # Chama o pipeline com gerenciamento de retry inteligente
            result = await PipelineAdapter._run_with_retry(gen, lead, progress, evidence=evidence)

            # VS-0: o pipeline retorna {"status": "failed", "error": <ErrorCode>, ...}
            # em falhas determinísticas (posicionamento/tema/tokens/render). Traduz
            # para exceção estruturada para o mesmo caminho de classificação abaixo —
            # senão uma falha seria marcada como "published" com campos vazios.
            if result.get("status") == "failed":
                raise ValueError(
                    f"{result.get('error', 'PIPELINE_ERROR')}: {result.get('detail') or result.get('issues')}"
                )

            # Atualiza com os resultados
            gen.status = "published"
            gen.archetype_name = result.get("archetype_name")
            gen.personality = result.get("personality")
            gen.position = result.get("position")
            gen.primary_color = result.get("primary_color")
            gen.hero_image = result.get("hero_image")
            gen.proofs = result.get("proofs", [])
            gen.headline = result.get("headline")
            gen.subheadline = result.get("subheadline")
            gen.cta = result.get("cta")
            gen.url = result.get("url")
            gen.error = None
            gen.updated_at = datetime.now()

            return {"status": "published", "generation": gen}

        except Exception as e:
            # Classifica o erro
            error_code, detail = PipelineAdapter._classify_error(e)
            progress("failed")
            gen.error = {
                "code": error_code.value,
                "message": get_user_message(error_code),
                "detail": detail,
                "timestamp": datetime.now().isoformat()
            }
            gen.updated_at = datetime.now()

            return {"status": "failed", "error": detail}

    @staticmethod
    def _classify_error(error: Exception) -> Tuple[ErrorCode, str]:
        """Classifica exceções em códigos de erro estáveis."""
        detail = str(error)
        error_str = detail.lower()

        # 1. Erro estruturado levantado intencionalmente pelo próprio pipeline
        #    (prefixo "CODIGO: detalhe", ex: "INVALID_LEAD: ...",
        #    "ARCHETYPE_NOT_SUPPORTED: ..."). Determinístico — não depende do
        #    conteúdo da mensagem (nome do lead, etc), só do código.
        #    Fase 17.1A: o gate de integridade de evidências (ver
        #    main.py::_evidence_integrity_gate, chamado dentro de
        #    generate_landing antes da publicação) usa a mesma convenção —
        #    "EVIDENCE_INTEGRITY_FAIL: ..." — e por isso cai neste mesmo
        #    caminho, sem precisar de tratamento especial aqui. O código é
        #    não-retryable (ver api/errors.py::is_retryable_error), então
        #    _run_with_retry abaixo já propaga sem retentar.
        structured_code = extract_error_code(detail)
        if structured_code:
            return classify_error_by_code(structured_code), detail

        # 2. Heurísticas de string — para exceções que não carregam código
        #    (erros crus de boto3/requests/LLM SDKs).

        # R2 Errors (checar ANTES do 401 genérico - "R2 ... 401" é R2_AUTH_ERROR)
        if "r2" in error_str or "cloudflare" in error_str or "falha na publica" in error_str:
            if "auth" in error_str or "401" in error_str or "credenc" in error_str:
                return ErrorCode.R2_AUTH_ERROR, detail
            return ErrorCode.R2_UPLOAD_ERROR, detail

        # LLM Errors
        if "api_key_invalid" in error_str or "unauthorized" in error_str or "401" in error_str:
            return ErrorCode.LLM_AUTH_ERROR, detail
        if "quota" in error_str or "resource_exhausted" in error_str or "429" in error_str:
            return ErrorCode.LLM_QUOTA_EXCEEDED, detail
        if "ollama" in error_str or "connection refused" in error_str:
            return ErrorCode.OLLAMA_UNAVAILABLE, detail
        if "timeout" in error_str:
            return ErrorCode.LLM_TIMEOUT, detail

        # Validation Errors
        if "validation error" in error_str or "pydantic" in error_str or "validationerror" in error_str:
            return ErrorCode.VALIDATION_ERROR, detail
        if "businessdata" in error_str or "telefone" in error_str or "invalido" in error_str:
            return ErrorCode.INVALID_LEAD, detail

        return ErrorCode.PIPELINE_ERROR, detail

    @staticmethod
    async def _run_with_retry(
        gen: Any,
        lead: Any,
        progress: Any,
        evidence: Optional[CommercialEvidence] = None,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """Executa o pipeline com retry inteligente (não retenta erros não-retryable)."""
        last_error: Optional[Exception] = None
        evidence = evidence or CommercialEvidence()

        for attempt in range(max_attempts):
            try:
                return await generate_landing(
                    lead_name=lead.name,
                    niche=lead.niche,
                    city=lead.city,
                    phone=lead.phone,
                    place_id=lead.place_id,
                    lead_id=lead.id,
                    evidence=evidence,
                    on_progress=progress
                )
            except Exception as e:
                last_error = e
                error_code, _ = PipelineAdapter._classify_error(e)

                # Se não for retryable, falha imediatamente
                if not is_retryable_error(error_code):
                    raise e

                # Se for a última tentativa, propaga o erro
                if attempt >= max_attempts - 1:
                    raise last_error

                # Backoff exponencial entre tentativas
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                continue

        raise last_error if last_error else RuntimeError("Pipeline falhou sem erro")


async def run_pipeline_task(gen_id: str):
    """Wrapper para executar o pipeline em background."""
    adapter = PipelineAdapter()
    await adapter.run(gen_id)