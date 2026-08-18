import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from models import ProposalTemplateData, BusinessData, CopyData, AssetsData, SeoData

from design_system.design_tokens import ColorRole, FontSpec, SemanticColor, TypographyPolicy
from design_system.design_tokens import DesignTokens


def _premium_tokens_css() -> str:
    tokens = DesignTokens(
        personality="premium_clinical",
        colors={
            ColorRole.BG: "#F5F3F0",
            ColorRole.SURFACE: "#FFFFFF",
            ColorRole.TEXT: "#1A1A1A",
            ColorRole.TEXT_SECONDARY: "#4A4A4A",
            ColorRole.HEADING: "#1A1A1A",
            ColorRole.BORDER: "#E8E3DD",
            ColorRole.ACCENT: "#8B4513",
            ColorRole.ACCENT_HOVER: "#B8976A",
            ColorRole.ON_ACCENT: "#1A1A1A",
        },
        semantic_colors={
            SemanticColor.SUCCESS: "#2E7D32",
            SemanticColor.WARNING: "#B26A00",
            SemanticColor.ERROR: "#C62828",
            SemanticColor.INFO: "#1565C0",
        },
        typography=TypographyPolicy(
            heading=FontSpec(family="Playfair Display", source="system", weights=[400]),
            body=FontSpec(family="Inter", source="system", weights=[400]),
        ),
    )
    return tokens.get_css_variables()


@pytest.fixture
def mock_data():
    """Dados mock para teste de template."""
    return ProposalTemplateData(
        business=BusinessData(
            name="Padaria Teste",
            niche="padaria",
            city="Goiânia",
            place_id="ChIJ_teste_template",
            phone="62999999999"
        ),
        copywriting=CopyData(
            headline="Pão artesanal todo dia",
            subheadline="Tradição e qualidade desde 1990",
            cta_whatsapp="Peça agora",
            pain_points=["Pão velho", "Atendimento lento"],
            proofs=["4.8 no Google", "1000+ clientes satisfeitos"]
        ),
        assets=AssetsData(
            suggested_images_keywords=["padaria", "pão"],
            color_palette_hint="marrom e dourado",
            primary_color="#8B4513"
        ),
        seo=SeoData(
            title="Padaria Teste - Pão Artesanal em Goiânia",
            description="A melhor padaria de Goiânia com pão artesanal feito todo dia"
        )
    )


def _render(mock_data):
    """Renderiza o template com o contrato token-driven do VS-0."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')
    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    data_dict['tokens_css'] = _premium_tokens_css()
    data_dict['font_links'] = ""
    data_dict['location'] = None
    return template.render(data=data_dict)


def test_template_renders_successfully(mock_data):
    """Template deve renderizar sem erros."""
    html = _render(mock_data)
    assert html is not None
    assert len(html) > 0
    assert "<!DOCTYPE html>" in html


def test_all_copywriting_fields_rendered(mock_data):
    """Todos os campos de copywriting devem estar no HTML."""
    html = _render(mock_data)
    assert mock_data.copywriting.headline in html
    assert mock_data.copywriting.subheadline in html
    assert mock_data.copywriting.cta_whatsapp in html
    assert mock_data.copywriting.pain_points[0] in html
    assert mock_data.copywriting.proofs[0] in html


def test_seo_fields_rendered(mock_data):
    """Campos de SEO devem estar no HTML."""
    html = _render(mock_data)
    assert mock_data.seo.title in html
    assert mock_data.seo.description in html
    assert f'<title>{mock_data.seo.title}</title>' in html
    assert f'content="{mock_data.seo.description}"' in html


def test_primary_color_applied(mock_data):
    """A cor primária deve vir do bloco de tokens (:root), única fonte de hex."""
    html = _render(mock_data)
    assert "--color-accent: #8B4513;" in html
    # O hex NÃO pode vazar fora do bloco de tokens.
    assert html.index("#8B4513") < html.index("</style>")


def test_no_raw_hex_outside_token_block(mock_data):
    """Hex limpo: o único hex do template vive dentro de :root."""
    html = _render(mock_data)
    head = html[: html.index("</style>")]
    body = html[html.index("</style>"):]
    assert "{" in head
    assert body.count("#") == 0


def test_cta_class_present(mock_data):
    """CTA usa a classe token-driven (.cta-primary)."""
    html = _render(mock_data)
    assert 'class="cta-primary"' in html


def test_location_section_omitted_when_absent(mock_data):
    """Sem location, a seção de localização não é renderizada."""
    html = _render(mock_data)
    assert 'data-component="location"' not in html


def test_location_section_rendered_when_present(mock_data):
    """Com location, endereço + link 'Como chegar' aparecem (sem iframe)."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')
    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    data_dict['tokens_css'] = _premium_tokens_css()
    data_dict['font_links'] = ""
    data_dict['location'] = {
        "address_line": "Rua X, 100 — Setor Bueno",
        "neighborhood": "Setor Bueno",
        "city": "Goiânia",
        "google_maps_url": "https://www.google.com/maps/search/?api=1&query=-16.7,-49.2",
    }
    html = template.render(data=data_dict)
    assert 'data-component="location"' in html
    assert "Rua X, 100 — Setor Bueno" in html
    assert "Como chegar" in html
    assert "<iframe" not in html


def test_whatsapp_link_correctly_formatted(mock_data):
    """Link do WhatsApp deve estar formatado corretamente."""
    html = _render(mock_data)
    assert "wa.me/5562999999999" in html
    assert "?text=" in html
    assert "Pe%C3%A7a%20agora" in html  # URL encoded


def test_hero_image_rendered(mock_data):
    """Imagem hero deve estar no HTML. O template usa background-image inline
    (não <img src=...>) — ver publisher.py/main.py, hero é sempre CSS de fundo."""
    html = _render(mock_data)
    assert 'background-image' in html
    assert "https://picsum.photos/seed/test/1200/600" in html