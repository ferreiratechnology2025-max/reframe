"""
Arquétipos suportados pelo Reframe.

Cada arquétipo define o conjunto travado (não gerado pelo LLM) de:
hero_image, primary_color, trust_signals, image_keywords.

Nichos sem entrada aqui NÃO devem ser publicados com um arquétipo genérico —
ver main.py::get_archetype_or_fail.
"""

ARCHETYPES_CONFIG = {
    "padaria": {
        "name": "Padaria",
        "hero_image": "https://images.unsplash.com/photo-1509440159596-0249088772ff?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#D97706",
        "trust_signals": [
            "Pães artesanais assados na hora",
            "Confeitaria fina e salgados para festas",
            "Café da manhã completo todos os dias"
        ],
        "image_keywords": ["pão", "padaria", "artesanal", "forno", "café"],
        "aliases": ["panificadora"]
    },
    "mecanica": {
        "name": "Mecânica",
        "hero_image": "https://images.unsplash.com/photo-1486006920555-c77dce18193b?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#1E40AF",
        "trust_signals": [
            "Diagnóstico computadorizado de precisão",
            "Profissionais qualificados e peças com garantia",
            "Transparência total no orçamento antes do serviço"
        ],
        "image_keywords": ["oficina", "ferramentas", "diagnóstico", "garantia"],
        "aliases": ["oficina"]
    },
    "restaurante": {
        "name": "Restaurante",
        "hero_image": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#B91C1C",
        "trust_signals": [
            "Comida caseira feita na hora",
            "Ingredientes frescos e selecionados",
            "Ambiente familiar e acolhedor"
        ],
        "image_keywords": ["restaurante", "comida", "prato", "caseiro"],
        "aliases": []
    },
    "barbearia": {
        "name": "Barbearia",
        "hero_image": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#1C1917",
        "trust_signals": [
            "Atendimento personalizado",
            "Profissionais experientes",
            "Ambiente vintage e exclusivo"
        ],
        "image_keywords": ["barbearia", "corte", "barba", "estilo"],
        "aliases": ["barbeiro"]
    },
    "salao": {
        "name": "Salão de Beleza",
        "hero_image": "https://images.unsplash.com/photo-1560066984-24fe9b05eb6a?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#BE185D",
        "trust_signals": [
            "Produtos de qualidade profissional",
            "Profissionais especializados",
            "Atendimento personalizado"
        ],
        "image_keywords": ["salão", "beleza", "cabelo", "estética"],
        "aliases": ["cabeleireiro"]
    },
    "confeitaria": {
        "name": "Confeitaria",
        "hero_image": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#D97706",
        "trust_signals": [
            "Doces artesanais feitos na hora",
            "Ingredientes selecionados",
            "Decoração personalizada para festas"
        ],
        "image_keywords": ["confeitaria", "doce", "bolo", "artesanal"],
        "aliases": ["doceria", "doces"]
    },
    "academia": {
        "name": "Academia",
        "hero_image": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#16A34A",
        "trust_signals": [
            "Equipamentos modernos",
            "Profissionais qualificados",
            "Horário flexível"
        ],
        "image_keywords": ["academia", "musculação", "treino", "saúde"],
        "aliases": ["fitness", "musculacao"]
    },
    "pet_shop": {
        "name": "Pet Shop",
        "hero_image": "https://images.unsplash.com/photo-1450778869180-41d0601e046e?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#0891B2",
        "trust_signals": [
            "Atendimento especializado",
            "Produtos de qualidade",
            "Banho e tosa com carinho"
        ],
        "image_keywords": ["pet", "animal", "cuidado", "banho"],
        "aliases": []
    },
    "moda": {
        "name": "Loja de Roupas",
        "hero_image": "https://images.unsplash.com/photo-1445205170230-053b83016050?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#7C3AED",
        "trust_signals": [
            "Moda atual e exclusiva",
            "Qualidade e estilo",
            "Atendimento personalizado"
        ],
        "image_keywords": ["moda", "roupa", "estilo", "vitrine"],
        "aliases": ["roupa", "vestuario", "boutique"]
    },
    "farmacia": {
        "name": "Farmácia",
        "hero_image": "https://images.unsplash.com/photo-1585435557343-3b092031a831?q=80&w=1200&auto=format&fit=crop",
        "primary_color": "#059669",
        "trust_signals": [
            "Profissionais habilitados",
            "Medicamentos de qualidade",
            "Atendimento humano e atencioso"
        ],
        "image_keywords": ["farmácia", "medicamento", "saúde", "atendimento"],
        "aliases": ["drogaria"]
    }
}
