"""
Publicador Cloudflare R2 (S3-compatible via boto3).

Variáveis de ambiente esperadas:
- R2_ACCESS_KEY / R2_SECRET_KEY: Credenciais S3-compatible do R2
  (aceita fallback CLOUDFLARE_ACCESS_KEY / CLOUDFLARE_SECRET_KEY)
- CLOUDFLARE_ACCOUNT_ID: ID da conta Cloudflare (aceita fallback R2_ACCOUNT_ID)
- R2_ENDPOINT: Endpoint S3-compatible (https://{account_id}.r2.cloudflarestorage.com)
  (aceita fallback CLOUDFLARE_ENDPOINT)
- R2_BUCKET: Nome do bucket R2 (aceita fallback CLOUDFLARE_BUCKET, default: leads-sites)
- ROOT_DOMAIN: Domínio público/custom para a URL final
- TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID: Alerta em caso de falha final de upload

URL pública gerada:
- https://{ROOT_DOMAIN}/{slug} (custom domain conectado ao bucket)

NOTA: o upload usa exclusivamente boto3/S3-compatible (R2_ACCESS_KEY/R2_SECRET_KEY).
CLOUDFLARE_API_TOKEN NÃO é usado por este módulo.
"""
import os
import time
import logging

import boto3
import requests
from botocore.config import Config
from botocore.exceptions import ClientError

from models import ProposalTemplateData

logger = logging.getLogger(__name__)

# Códigos de erro do R2/S3 que não melhoram com retry (autenticação/config).
_NON_RETRYABLE_CODES = {'AccessDenied', 'InvalidAccessKeyId', 'SignatureDoesNotMatch'}


class R2Publisher:
    """Publicador R2 usando boto3/S3-compatible."""

    def __init__(self):
        self.access_key = os.getenv('R2_ACCESS_KEY') or os.getenv('CLOUDFLARE_ACCESS_KEY')
        self.secret_key = os.getenv('R2_SECRET_KEY') or os.getenv('CLOUDFLARE_SECRET_KEY')
        self.account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID') or os.getenv('R2_ACCOUNT_ID')
        self.endpoint = os.getenv('R2_ENDPOINT') or os.getenv('CLOUDFLARE_ENDPOINT')
        self.bucket = os.getenv('R2_BUCKET') or os.getenv('CLOUDFLARE_BUCKET') or 'leads-sites'
        self.root_domain = os.getenv('ROOT_DOMAIN', 'propostas.api-plataforma.com')

        self._validate_config()
        self._init_client()

    def _validate_config(self):
        """Valida que todas as credenciais estão presentes."""
        missing = []
        if not self.access_key:
            missing.append('R2_ACCESS_KEY/CLOUDFLARE_ACCESS_KEY')
        if not self.secret_key:
            missing.append('R2_SECRET_KEY/CLOUDFLARE_SECRET_KEY')
        if not self.account_id:
            missing.append('CLOUDFLARE_ACCOUNT_ID/R2_ACCOUNT_ID')
        if not self.endpoint:
            missing.append('R2_ENDPOINT/CLOUDFLARE_ENDPOINT')
        if not self.bucket:
            missing.append('R2_BUCKET/CLOUDFLARE_BUCKET')

        if missing:
            raise ValueError(f"Credenciais R2 faltando: {', '.join(missing)}")

    def _init_client(self):
        """Inicializa o cliente boto3 S3."""
        endpoint = self.endpoint
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f'https://{endpoint}'

        self.session = boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

        self.client = self.session.client(
            's3',
            endpoint_url=endpoint,
            config=Config(
                signature_version='s3v4',
                region_name='auto',
            ),
        )
        logger.info(f"R2 Publisher inicializado: bucket={self.bucket}, endpoint={endpoint}")

    def upload_html(self, slug: str, html: str, force: bool = False) -> str:
        """
        Publica HTML no R2.
        Grava diretamente na key = {slug} (sem /index.html) para URL limpa,
        já que o custom domain do R2 não resolve index document automaticamente.
        Retorna a URL pública.

        Args:
            force: se False (default), levanta SLUG_COLLISION quando já existe
                um objeto nessa key — protege contra dois leads diferentes
                colidindo na mesma URL e se sobrescrevendo silenciosamente.
                Passe True para republicar/atualizar deliberadamente uma key
                já existente (ex: regenerar a landing do mesmo lead).

        Raises:
            ValueError: "SLUG_COLLISION: ..." se force=False e a key já existir.
        """
        if not force and self.exists(slug):
            raise ValueError(
                f"SLUG_COLLISION: Slug '{slug}' já existe no bucket '{self.bucket}'. "
                f"Verifique se este lead já foi publicado ou use force=True para sobrescrever."
            )

        key = slug

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=html.encode('utf-8'),
                ContentType='text/html',
                CacheControl='public, max-age=3600',
            )

            url = f"https://{self.root_domain}/{slug}"
            logger.info(f"HTML publicado: {url}")
            return url

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"Falha ao publicar HTML: {error_code} - {e}")
            raise

    def upload_asset(self, slug: str, filename: str, content: bytes, content_type: str) -> str:
        """
        Publica um asset (imagem, CSS, etc) no R2.
        Retorna a URL pública.
        """
        key = f"{slug}/{filename}"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                CacheControl='public, max-age=86400',
            )

            url = f"https://{self.root_domain}/{slug}/{filename}"
            logger.info(f"Asset publicado: {url}")
            return url

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"Falha ao publicar asset: {error_code} - {e}")
            raise

    def exists(self, slug: str) -> bool:
        """Verifica se um site já existe no bucket."""
        key = slug
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                return False
            raise


def diagnose_r2_config() -> dict:
    """Diagnostica a configuração do R2 (para endpoints de diagnóstico)."""
    vars_to_check = [
        'R2_ACCESS_KEY',
        'R2_SECRET_KEY',
        'CLOUDFLARE_ACCOUNT_ID',
        'R2_ENDPOINT',
        'R2_BUCKET',
        'ROOT_DOMAIN',
    ]

    config = {}
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'SECRET' in var:
                config[var] = f"{value[:8]}...{value[-4:]}"
            else:
                config[var] = value
        else:
            config[var] = "MISSING"

    print("Configuração R2:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    endpoint = os.getenv('R2_ENDPOINT')
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    if not endpoint and account_id:
        default_endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        print(f"\nEndpoint inferido: {default_endpoint}")
        config['_inferred_endpoint'] = default_endpoint

    return config


def trigger_telegram_alert(slug: str, message: str):
    """Envia alerta para Telegram (implementação placeholder)."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        logger.warning(f"[ALERTA TELEGRAM] {slug}: {message}")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": f"R2 Upload Falhou\nSlug: {slug}\n{message}"
        }, timeout=5)
    except Exception as e:
        logger.error(f"Falha ao enviar alerta Telegram: {e}")


def publish_to_r2(
    validated_data: ProposalTemplateData,
    html_final: str,
    retries: int = 3,
    force: bool = True
) -> str:
    """
    Publica HTML no Cloudflare R2 (boto3/S3-compatible) com retry e backoff exponencial.

    Args:
        validated_data: Dados validados do proposal (contém slug único)
        html_final: HTML renderizado pronto para publicação
        retries: Número máximo de tentativas
        force: Repassado para R2Publisher.upload_html. Default True porque,
            na arquitetura atual, publicar É o caminho de atualização de um
            lead — não existe um fluxo separado de "criar" vs "regenerar".
            Bloquear por padrão quebraria a regeneração normal da landing do
            mesmo lead (ex: rodar o pipeline de novo após um ajuste). O
            collision guard (force=False) fica disponível para quem
            deliberadamente quer proteção contra reuso acidental de slug —
            ex: uma futura rota administrativa de "publicar só se for novo".
            A causa raiz do bug de colisão real (leads com nomes iguais e
            nichos/cidades diferentes gerando o mesmo slug) é resolvida em
            main.py::synthetic_place_id, não aqui.

    Returns:
        URL pública do site publicado

    Raises:
        ValueError: Se slug não for DNS-safe, credenciais R2 estiverem
            faltando, ou (com force=False) "SLUG_COLLISION: ..." se a key
            já existir — nunca é retentado, o resultado não muda com retry.
        Exception: Se todas as tentativas de upload falharem
    """
    slug = validated_data.business.slug

    # Validação explícita de slug (defesa em profundidade)
    if '_' in slug or not slug.replace('-', '').isalnum():
        raise ValueError(f"Slug DNS inseguro detectado: {slug}")

    publisher = R2Publisher()

    last_error: Exception = RuntimeError("R2_UPLOAD_ERROR: erro desconhecido")

    for attempt in range(retries):
        try:
            return publisher.upload_html(slug, html_final, force=force)

        except ValueError as e:
            if "SLUG_COLLISION" in str(e):
                # Determinístico — tentar de novo não muda o resultado.
                logger.error(f"Colisão de slug (não-retryable): {slug}")
                raise
            last_error = e

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')

            if error_code in _NON_RETRYABLE_CODES:
                logger.error(f"Erro de autenticação R2 (não-retryable): {error_code}")
                trigger_telegram_alert(slug, f"Falha de autenticação R2: {error_code} - {e}")
                raise RuntimeError(f"R2_AUTH_ERROR: {e}") from e

            last_error = e

        except Exception as e:
            last_error = e

        if attempt < retries - 1:
            wait_time = 2 ** attempt
            logger.warning(
                f"R2 tentativa {attempt + 1}/{retries} falhou para {slug}, "
                f"retry em {wait_time}s: {last_error}"
            )
            time.sleep(wait_time)
        else:
            logger.error(f"R2 upload falhou após {retries} tentativas: {last_error}")
            trigger_telegram_alert(slug, f"Falha R2 final após {retries} tentativas: {last_error}")
            # Erro estruturado (prefixo "R2_UPLOAD_ERROR:") em vez de propagar o
            # ClientError/Exception cru — sem isso, a mensagem não contém "r2"
            # nem "cloudflare" (ex: "An error occurred (InternalError)..."),
            # então o pipeline_adapter classificava como PIPELINE_ERROR genérico
            # em vez de R2_UPLOAD_ERROR (achado da Fase 13.2).
            raise RuntimeError(
                f"R2_UPLOAD_ERROR: Falha após {retries} tentativas: {last_error}"
            ) from last_error
