import pytest
import os
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from models import ProposalTemplateData, BusinessData, CopyData, AssetsData, SeoData
from publisher import publish_to_r2, R2Publisher


# Variáveis de ambiente mínimas exigidas por R2Publisher._validate_config
R2_ENV = {
    "R2_ACCESS_KEY": "test_access_key",
    "R2_SECRET_KEY": "test_secret_key",
    "CLOUDFLARE_ACCOUNT_ID": "test_account",
    "R2_ENDPOINT": "https://testaccount.r2.cloudflarestorage.com",
    "R2_BUCKET": "test-bucket",
    "ROOT_DOMAIN": "test.com",
}


@pytest.fixture
def sample_data():
    """Dados de exemplo para teste."""
    return ProposalTemplateData(
        business=BusinessData(
            name="Padaria Central",
            niche="padaria",
            city="Goiânia",
            place_id="ChIJ_teste_publisher",
            phone="62999999999"
        ),
        copywriting=CopyData(
            headline="Pão artesanal todo dia",
            subheadline="Tradição e qualidade desde 1990",
            cta_whatsapp="Peça agora",
            pain_points=["Pão velho", "Atendimento lento"],
            proofs=["4.8 no Google", "1000+ clientes"]
        ),
        assets=AssetsData(
            suggested_images_keywords=["padaria", "pão"],
            color_palette_hint="marrom e dourado"
        ),
        seo=SeoData(
            title="Padaria Central - Pão Artesanal em Goiânia",
            description="A melhor padaria de Goiânia com pão artesanal feito todo dia"
        )
    )


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "PutObject")


@patch('publisher.R2Publisher.upload_html')
@patch.dict(os.environ, R2_ENV)
def test_publish_success(mock_upload, sample_data):
    """Upload bem-sucedido deve retornar URL correta."""
    html = "<html><body>Teste</body></html>"
    expected_url = f"https://test.com/{sample_data.business.slug}"
    mock_upload.return_value = expected_url

    url = publish_to_r2(sample_data, html)

    assert url == expected_url
    assert mock_upload.call_count == 1

    call_args = mock_upload.call_args[0]
    assert call_args[0] == sample_data.business.slug
    assert call_args[1] == html


@patch('publisher.trigger_telegram_alert')
@patch('publisher.R2Publisher.upload_html')
@patch.dict(os.environ, R2_ENV)
def test_publish_retry_on_failure(mock_upload, mock_alert, sample_data):
    """Falha (retryable) deve tentar novamente com backoff."""
    expected_url = f"https://test.com/{sample_data.business.slug}"
    mock_upload.side_effect = [
        _client_error("InternalError"),
        _client_error("InternalError"),
        expected_url,  # Sucesso na terceira tentativa
    ]

    html = "<html><body>Teste</body></html>"
    url = publish_to_r2(sample_data, html, retries=3)

    assert url == expected_url
    assert mock_upload.call_count == 3
    assert mock_alert.call_count == 0


@patch('publisher.trigger_telegram_alert')
@patch('publisher.R2Publisher.upload_html')
@patch.dict(os.environ, R2_ENV)
def test_publish_all_retries_fail(mock_upload, mock_alert, sample_data):
    """Todas as tentativas falhando (erro retryable) deve alertar e levantar
    RuntimeError estruturado com prefixo R2_UPLOAD_ERROR (não o ClientError cru)."""
    mock_upload.side_effect = _client_error("InternalError")

    html = "<html><body>Teste</body></html>"

    with pytest.raises(RuntimeError, match="R2_UPLOAD_ERROR"):
        publish_to_r2(sample_data, html, retries=2)

    assert mock_upload.call_count == 2
    assert mock_alert.call_count == 1


@patch('publisher.trigger_telegram_alert')
@patch('publisher.R2Publisher.upload_html')
@patch.dict(os.environ, R2_ENV)
def test_publish_auth_error_not_retried(mock_upload, mock_alert, sample_data):
    """Erro de autenticação (AccessDenied) não deve ser retentado."""
    mock_upload.side_effect = _client_error("AccessDenied")

    html = "<html><body>Teste</body></html>"

    with pytest.raises(RuntimeError, match="R2_AUTH_ERROR"):
        publish_to_r2(sample_data, html, retries=3)

    assert mock_upload.call_count == 1
    assert mock_alert.call_count == 1


def test_publish_invalid_slug_raises_error(sample_data):
    """Slug com underscore deve levantar ValueError."""
    sample_data.business.slug = "slug_invalido_com_underscore"

    html = "<html><body>Teste</body></html>"

    with pytest.raises(ValueError, match="DNS inseguro"):
        publish_to_r2(sample_data, html)


def _not_found_error() -> ClientError:
    return ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")


@patch.dict(os.environ, R2_ENV)
def test_upload_html_key_format():
    """Verifica que upload_html usa key = slug (URL limpa, sem /index.html)."""
    publisher = R2Publisher()
    with patch.object(publisher.client, 'head_object', side_effect=_not_found_error()):
        with patch.object(publisher.client, 'put_object') as mock_put:
            publisher.upload_html("test-slug", "<html>")
            mock_put.assert_called_once()
            call_kwargs = mock_put.call_args[1]
            assert call_kwargs['Key'] == "test-slug"


@patch.dict(os.environ, R2_ENV)
def test_upload_asset_key_format():
    """Verifica que upload_asset mantém key = {slug}/{filename}."""
    publisher = R2Publisher()
    with patch.object(publisher.client, 'put_object') as mock_put:
        publisher.upload_asset("test-slug", "style.css", b"body{}", "text/css")
        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args[1]
        assert call_kwargs['Key'] == "test-slug/style.css"


@patch.dict(os.environ, R2_ENV)
def test_url_format():
    """Verifica que a URL retornada por upload_html está no formato {root_domain}/{slug}."""
    publisher = R2Publisher()
    with patch.object(publisher.client, 'head_object', side_effect=_not_found_error()):
        with patch.object(publisher.client, 'put_object'):
            url = publisher.upload_html("test-slug", "<html>")
            assert url == f"https://{publisher.root_domain}/test-slug"


@patch.dict(os.environ, R2_ENV)
def test_collision_guard_blocks_overwrite_by_default():
    """upload_html deve levantar SLUG_COLLISION se a key já existe e force=False."""
    publisher = R2Publisher()
    with patch.object(publisher.client, 'head_object', return_value={}):  # existe
        with patch.object(publisher.client, 'put_object') as mock_put:
            with pytest.raises(ValueError, match="SLUG_COLLISION"):
                publisher.upload_html("estrela-padaria-goiania", "<html>")
            mock_put.assert_not_called()


@patch.dict(os.environ, R2_ENV)
def test_collision_guard_force_overwrites():
    """upload_html com force=True deve sobrescrever mesmo se a key já existir."""
    publisher = R2Publisher()
    with patch.object(publisher.client, 'head_object', return_value={}):  # existe
        with patch.object(publisher.client, 'put_object') as mock_put:
            url = publisher.upload_html("estrela-padaria-goiania", "<html>", force=True)
            mock_put.assert_called_once()
            assert url.startswith("https://")


@patch.dict(os.environ, R2_ENV)
def test_collision_guard_allows_new_slug():
    """upload_html não deve bloquear quando a key ainda não existe (404)."""
    publisher = R2Publisher()
    with patch.object(publisher.client, 'head_object', side_effect=_not_found_error()):
        with patch.object(publisher.client, 'put_object') as mock_put:
            publisher.upload_html("slug-novo", "<html>")
            mock_put.assert_called_once()


@patch('publisher.trigger_telegram_alert')
@patch('publisher.R2Publisher.upload_html')
@patch.dict(os.environ, R2_ENV)
def test_publish_to_r2_slug_collision_not_retried(mock_upload, mock_alert, sample_data):
    """publish_to_r2 com force=False não deve retentar SLUG_COLLISION."""
    mock_upload.side_effect = ValueError("SLUG_COLLISION: Slug já existe")

    html = "<html><body>Teste</body></html>"

    with pytest.raises(ValueError, match="SLUG_COLLISION"):
        publish_to_r2(sample_data, html, retries=3, force=False)

    assert mock_upload.call_count == 1  # sem retry
    assert mock_alert.call_count == 0  # não é uma falha de infraestrutura


@patch('publisher.R2Publisher.upload_html')
@patch.dict(os.environ, R2_ENV)
def test_publish_to_r2_defaults_to_force_true(mock_upload, sample_data):
    """
    publish_to_r2 usa force=True por padrão — regenerar a landing do mesmo
    lead é o fluxo normal, não uma colisão.
    """
    expected_url = f"https://test.com/{sample_data.business.slug}"
    mock_upload.return_value = expected_url

    publish_to_r2(sample_data, "<html>")

    call_kwargs = mock_upload.call_args[1]
    assert call_kwargs['force'] is True


@patch.dict(os.environ, R2_ENV)
def test_exists_uses_slug_as_key():
    """Verifica que exists() checa a key = slug (consistente com upload_html)."""
    publisher = R2Publisher()
    with patch.object(publisher.client, 'head_object') as mock_head:
        publisher.exists("test-slug")
        mock_head.assert_called_once()
        call_kwargs = mock_head.call_args[1]
        assert call_kwargs['Key'] == "test-slug"
