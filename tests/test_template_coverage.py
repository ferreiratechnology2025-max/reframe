import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
DESIGN_SYSTEMS_DIR = Path(__file__).resolve().parent.parent / "design-systems"


@pytest.fixture
def jinja_env():
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


@pytest.fixture
def design_system():
    import json
    with open(DESIGN_SYSTEMS_DIR / "default.json") as f:
        return json.load(f)


def test_template_renders_successfully(jinja_env, design_system):
    template = jinja_env.get_template("premium.html")

    context = {
        "lead": {
            "business_info": {
                "name": "Empresa Exemplo Ltda",
            },
        },
        "value_proposition": {
            "headline": "Solução Premium para seu Negócio",
            "subheadline": "Transformamos sua presença digital",
            "key_benefits": ["Atendimento Personalizado", "Tecnologia de Ponta", "Resultados Garantidos"],
        },
        "seo": {
            "meta_title": "Empresa Exemplo - Soluções Premium",
            "meta_description": "Descrição para SEO",
            "keywords": ["exemplo", "premium"],
        },
        "design": design_system,
    }

    html = template.render(**context)
    assert "Solução Premium para seu Negócio" in html
    assert "Empresa Exemplo Ltda" in html
    assert "Atendimento Personalizado" in html
    assert "https://fonts.googleapis.com" in html
    assert len(html) > 500
