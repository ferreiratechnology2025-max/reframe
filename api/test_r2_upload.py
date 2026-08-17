"""
Teste mínimo de upload para Cloudflare R2.
Usa o mesmo mecanismo (R2Publisher/boto3) que o pipeline real usa.
"""
import sys
from pathlib import Path
from datetime import datetime

# Adiciona raiz ao path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Carrega .env
from dotenv import load_dotenv
load_dotenv(Path(PROJECT_ROOT) / '.env')

from publisher import R2Publisher, diagnose_r2_config


def test_r2_upload():
    """Testa upload de um arquivo mínimo para R2, usando o mesmo mecanismo do pipeline."""

    diagnose_r2_config()

    slug = f"test-upload-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    html_content = f"""<!DOCTYPE html>
<html>
<head><title>R2 Healthcheck</title></head>
<body>
<h1>R2 Upload Test</h1>
<p>Teste realizado em {datetime.now().isoformat()}</p>
</body>
</html>"""

    try:
        publisher = R2Publisher()
        url = publisher.upload_html(slug=slug, html=html_content)

        print("\n[OK] Upload realizado com sucesso!")
        print(f"URL pública: {url}")
        return True

    except ValueError as e:
        print(f"\n[ERRO] Configuração inválida: {e}")
        return False

    except Exception as e:
        print(f"\n[ERRO] Falha no upload: {type(e).__name__}")
        print(f"   Mensagem: {e}")

        # Diagnóstico adicional
        error_str = str(e)
        if 'InvalidAccessKeyId' in error_str:
            print("\n[DIAGNOSTICO] Access Key ID invalida.")
            print("   Verifique se a chave esta correta e ativa.")
        elif 'SignatureDoesNotMatch' in error_str:
            print("\n[DIAGNOSTICO] Assinatura invalida.")
            print("   Verifique se Secret Access Key esta correta.")
        elif 'AccessDenied' in error_str:
            print("\n[DIAGNOSTICO] Acesso negado.")
            print("   Verifique permissoes da credencial (R2 API Token, Object Read & Write).")
        elif 'NoSuchBucket' in error_str:
            print("\n[DIAGNOSTICO] Bucket nao existe.")
        elif 'ConnectionError' in error_str or 'timeout' in error_str.lower():
            print("\n[DIAGNOSTICO] Falha de conexao.")
            print("   Verifique se o R2_ENDPOINT esta correto e acessivel.")
        elif 'Forbidden' in error_str:
            print("\n[DIAGNOSTICO] Acesso proibido.")
            print("   Verifique se o token R2 (nao API token da Cloudflare) esta sendo usado.")

        return False


if __name__ == "__main__":
    success = test_r2_upload()
    sys.exit(0 if success else 1)
