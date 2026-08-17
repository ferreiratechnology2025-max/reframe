import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from models import ProposalTemplateData, BusinessData, CopyData, AssetsData, SeoData


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


def test_template_renders_successfully(mock_data):
    """Template deve renderizar sem erros."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')
    
    # Adiciona hero_image_url (gerado pelo image_provider)
    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    
    html = template.render(data=data_dict)
    
    assert html is not None
    assert len(html) > 0
    assert "<!DOCTYPE html>" in html


def test_all_copywriting_fields_rendered(mock_data):
    """Todos os campos de copywriting devem estar no HTML."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')
    
    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    html = template.render(data=data_dict)
    
    assert mock_data.copywriting.headline in html
    assert mock_data.copywriting.subheadline in html
    assert mock_data.copywriting.cta_whatsapp in html
    assert mock_data.copywriting.pain_points[0] in html
    assert mock_data.copywriting.proofs[0] in html


def test_seo_fields_rendered(mock_data):
    """Campos de SEO devem estar no HTML."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')
    
    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    html = template.render(data=data_dict)
    
    assert mock_data.seo.title in html
    assert mock_data.seo.description in html
    assert f'<title>{mock_data.seo.title}</title>' in html
    assert f'content="{mock_data.seo.description}"' in html


def test_primary_color_applied(mock_data):
    """Cor primária deve ser aplicada no template."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')
    
    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    html = template.render(data=data_dict)
    
    assert mock_data.assets.primary_color in html


def test_whatsapp_link_correctly_formatted(mock_data):
    """Link do WhatsApp deve estar formatado corretamente."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')
    
    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    html = template.render(data=data_dict)
    
    assert "wa.me/5562999999999" in html
    assert "?text=" in html
    assert "Pe%C3%A7a%20agora" in html  # URL encoded


def test_hero_image_rendered(mock_data):
    """Imagem hero deve estar no HTML. O template usa background-image inline
    (não <img src=...>) — ver publisher.py/main.py, hero é sempre CSS de fundo."""
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('premium.html')

    data_dict = mock_data.model_dump()
    data_dict['hero_image_url'] = "https://picsum.photos/seed/test/1200/600"
    html = template.render(data=data_dict)

    assert 'background-image' in html
    assert "https://picsum.photos/seed/test/1200/600" in html
