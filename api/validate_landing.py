"""
Validação da landing publicada.
Verifica estrutura, assets e comportamento.
"""
import httpx
import asyncio
import re
import sys

async def validate_landing(url: str) -> dict:
    """
    Valida uma landing publicada.
    Retorna dicionário com resultados.
    """
    results = {
        "url": url,
        "accessible": False,
        "status_code": None,
        "content_type": None,
        "has_headline": False,
        "has_cta": False,
        "has_hero": False,
        "has_tailwind": False,
        "has_archetype_colors": False,
        "has_head_structure": False,
        "html_size": 0,
        "word_count": 0,
        "errors": []
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0, follow_redirects=True)

        results["status_code"] = response.status_code
        results["content_type"] = response.headers.get("content-type", "")

        if response.status_code != 200:
            results["errors"].append(f"HTTP {response.status_code}")
            return results

        results["accessible"] = True
        html = response.text

        # Verificações básicas
        if "<head>" in html and "<body>" in html:
            results["has_head_structure"] = True

        # Headline
        if re.search(r'<h1[^>]*>.*?<', html, re.IGNORECASE):
            results["has_headline"] = True

        # CTA
        if re.search(r'(Fale Conosco|WhatsApp|Contato|Saiba Mais|Comprar|Agendar)', html):
            results["has_cta"] = True

        # Hero (background-image)
        if 'background-image' in html:
            results["has_hero"] = True

        # Tailwind
        if 'tailwind' in html.lower():
            results["has_tailwind"] = True

        # Cores do arquétipo (âmbar #D97706 ou azul #1E40AF)
        if '#D97706' in html or '#1E40AF' in html:
            results["has_archetype_colors"] = True

        # Contagem de elementos
        results["html_size"] = len(html)
        results["word_count"] = len(re.findall(r'\w+', html))

    except Exception as e:
        results["errors"].append(str(e))

    return results

async def main():
    """Valida uma landing a partir da URL."""
    if len(sys.argv) < 2:
        print("Uso: python api/validate_landing.py <url>")
        print("Exemplo: python api/validate_landing.py https://propostas.api-plataforma.com/padaria-test")
        sys.exit(1)

    url = sys.argv[1]
    print(f"\nValidando landing: {url}\n")

    results = await validate_landing(url)

    print("Resultados:")
    for key, value in results.items():
        if key == "errors" and value:
            print(f"  Erros: {', '.join(value)}")
        elif key not in ["url", "errors"]:
            status = "OK" if value else "FALHA"
            label = key.replace('_', ' ').title()
            if isinstance(value, bool):
                print(f"  [{status}] {label}")
            else:
                print(f"  [{status}] {label}: {value}")

    if results["accessible"] and not results["errors"]:
        print("\nLanding validada com sucesso!")
        print(f"   Tamanho: {results['html_size']} caracteres")
        print(f"   Palavras: ~{results['word_count']}")
        sys.exit(0)
    else:
        print("\nValidação falhou.")
        if results["errors"]:
            print(f"   Erros: {', '.join(results['errors'])}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
