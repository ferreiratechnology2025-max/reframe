import os
import json
import logging
from typing import Optional
from abc import ABC, abstractmethod

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        ...


class OllamaProvider(LLMProvider):
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": kwargs.get("max_tokens", 2048)},
        }
        if system_prompt:
            payload["system"] = system_prompt

        resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip()


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        import google.generativeai as genai

        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        resp = self.model.generate_content(full_prompt)
        return resp.text.strip()


def get_llm_provider() -> LLMProvider:
    primary = os.getenv("PRIMARY_LLM", "ollama").lower()
    if primary == "ollama":
        try:
            provider = OllamaProvider()
            logger.info("Using Ollama as primary LLM")
            return provider
        except Exception as e:
            logger.warning(f"Ollama failed, falling back to Gemini: {e}")

    fallback = os.getenv("FALLBACK_LLM", "gemini").lower()
    if fallback == "gemini":
        logger.info("Using Gemini as LLM")
        return GeminiProvider()

    raise RuntimeError("No LLM provider available")
