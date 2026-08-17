import os
import json
import hashlib
import logging
import requests
from filelock import FileLock

CACHE_FILE = "unsplash_cache.json"
LOCK_FILE = f"{CACHE_FILE}.lock"

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_hero_image(keywords: list[str], slug: str) -> str:
    """
    Retorna URL de imagem otimizada. Unsplash (primário) com fallback Picsum determinístico.
    
    Args:
        keywords: Lista de keywords para busca (ex: ["padaria", "pão artesanal"])
        slug: Slug único do lead (usado para gerar sufixo de cache)
    
    Returns:
        URL da imagem com sufixo único por lead
    """
    cache_key = "_".join(sorted(keywords)).lower().replace(" ", "-")
    
    with FileLock(LOCK_FILE):
        cache = {}
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}

        # Suporte a migração de cache antigo (string pura) e leitura de metadados
        if cache_key in cache:
            entry = cache[cache_key]
            if isinstance(entry, str):
                # Cache legado: retorna direto (sem sufixo único, mas funciona)
                return entry
            
            # Se já temos uma imagem válida (Unsplash ou Picsum), retorna a URL base
            base_url = entry.get("url", "")
            if not base_url:
                # Entry corrompido, remove e regenera
                del cache[cache_key]
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(cache, f, indent=2)
            else:
                # Adiciona sufixo único por lead para quebrar cache de navegador
                unique_sig = hashlib.md5(slug.encode()).hexdigest()[:6]
                separator = "&" if "?" in base_url else "?"
                return f"{base_url}{separator}v={unique_sig}"

        final_url = ""
        source = "picsum"
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")

        if unsplash_key:
            try:
                query = keywords[0] if keywords else "business"
                
                # Autenticação via Header (prática segura, sem vazamento em URL)
                headers = {"Authorization": f"Client-ID {unsplash_key}"}
                
                # orientation=landscape garante proporção adequada para hero 1200x600
                params = {"query": query, "orientation": "landscape"}
                
                resp = requests.get(
                    "https://api.unsplash.com/photos/random",
                    headers=headers,
                    params=params,
                    timeout=5
                )
                resp.raise_for_status()  # Lança HTTPError para 4xx/5xx
                
                final_url = resp.json()["urls"]["regular"]
                source = "unsplash"
                logging.info(f"Unsplash: imagem obtida para keyword '{query}'")
                
            except Exception as e:
                # Log explícito: operador saberá que o fallback foi acionado
                logging.warning(f"Unsplash falhou para keyword '{query}': {e}. Fallback Picsum ativado.")

        if not final_url:
            # Fallback determinístico: Picsum (Seed no PATH, não na query)
            seed_hash = hashlib.md5(f"{cache_key}-{slug}".encode()).hexdigest()[:8]
            final_url = f"https://picsum.photos/seed/{seed_hash}/1200/600"
            source = "picsum"

        # Cache armazena metadados para auditoria e invalidação seletiva
        cache[cache_key] = {"url": final_url, "source": source}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        
        # Retorna com sufixo único por lead
        unique_sig = hashlib.md5(slug.encode()).hexdigest()[:6]
        separator = "&" if "?" in final_url else "?"
        return f"{final_url}{separator}v={unique_sig}"
