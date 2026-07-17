import os
import json
import logging
import hashlib
from typing import Optional

import requests
from filelock import FileLock

logger = logging.getLogger(__name__)

CACHE_FILE = "unsplash_cache.json"
LOCK_FILE = CACHE_FILE + ".lock"

UNSPLASH_BASE = "https://api.unsplash.com"
PICSUM_BASE = "https://picsum.photos"


def _load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_cache(cache: dict):
    with FileLock(LOCK_FILE):
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)


def _cache_key(prompt: str, width: int, height: int) -> str:
    raw = f"{prompt.lower().strip()}:{width}x{height}"
    return hashlib.md5(raw.encode()).hexdigest()


def fetch_image(prompt: str, width: int = 1200, height: int = 800) -> Optional[dict]:
    cache = _load_cache()
    key = _cache_key(prompt, width, height)

    if key in cache:
        logger.info("Image cache hit for '%s'", prompt)
        return cache[key]

    result = _search_fetch_picsum(prompt, width, height)
    if result:
        cache[key] = result
        _save_cache(cache)
        return result

    result = _search_fetch_unsplash(prompt, width, height)
    if result:
        cache[key] = result
        _save_cache(cache)
        return result

    logger.warning("No image found for prompt: %s", prompt)
    return None


def _search_fetch_unsplash(prompt: str, width: int, height: int) -> Optional[dict]:
    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        return None

    try:
        resp = requests.get(
            f"{UNSPLASH_BASE}/search/photos",
            params={"query": prompt, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {access_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            photo = data["results"][0]
            img_url = photo["urls"]["raw"] + f"&w={width}&h={height}&fit=crop"
            return {
                "url": img_url,
                "alt": photo.get("alt_description", prompt),
                "source": "unsplash",
                "prompt_used": prompt,
            }
    except Exception as e:
        logger.warning("Unsplash search failed: %s", e)
    return None


def _search_fetch_picsum(prompt: str, width: int, height: int) -> Optional[dict]:
    try:
        seed = hashlib.md5(prompt.encode()).hexdigest()[:8]
        url = f"{PICSUM_BASE}/seed/{seed}/{width}/{height}"
        resp = requests.get(url, timeout=10)
        if resp.status_code < 400:
            return {
                "url": str(resp.url),
                "alt": prompt,
                "source": "picsum",
                "prompt_used": prompt,
            }
    except Exception as e:
        logger.debug("Picsum fetch failed: %s", e)
    return None
