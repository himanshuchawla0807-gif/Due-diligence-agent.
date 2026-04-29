"""Provider adapters for diligence review."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .config import Settings


class ProviderError(RuntimeError):
    pass


class BaseProvider(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    async def analyze(self, documents: List[Dict[str, str]], focus: str = "") -> List[Dict[str, Any]]:
        raise NotImplementedError

    def _prompt(self, documents: List[Dict[str, str]], focus: str = "") -> str:
        docs = "\n\n".join(
            f"Document: {doc['file_name']}\n{doc.get('text') or '[No extractable text found]'}"
            for doc in documents
        )
        return (
            "Review these due diligence documents and return JSON only as an array of findings. "
            "Each finding must include category, severity, finding, evidence, and recommendation.\n\n"
            f"Focus: {focus or 'commercial, financial, legal, technical, and risk signals'}\n\n"
            f"{docs}"
        )

    def _parse_findings(self, raw: str, documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                data = data.get("findings") or data.get("data") or [data]
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
        except Exception:
            pass
        return MockProvider(self.settings).mock_findings(documents)


class MockProvider(BaseProvider):
    async def analyze(self, documents: List[Dict[str, str]], focus: str = "") -> List[Dict[str, Any]]:
        await asyncio.sleep(0.2)
        return self.mock_findings(documents)

    def mock_findings(self, documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        if not documents:
            documents = [{"file_name": "Sample Data Room", "text": ""}]
        return [
            {
                "category": "General",
                "severity": "medium",
                "finding": f"Initial diligence review completed for {doc['file_name']}.",
                "evidence": (doc.get("text") or "mock diligence review")[:180],
                "recommendation": "Validate this finding with the configured diligence provider.",
            }
            for doc in documents
        ]


class OpenAIProvider(BaseProvider):
    async def analyze(self, documents: List[Dict[str, str]], focus: str = "") -> List[Dict[str, Any]]:
        if not self.settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY is required for the OpenAI provider.")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        kwargs: Dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": [{"role": "user", "content": self._prompt(documents, focus)}],
            "response_format": {"type": "json_object"},
        }
        if self.settings.openai_reasoning_effort:
            kwargs["reasoning_effort"] = self.settings.openai_reasoning_effort
        response = await client.chat.completions.create(**kwargs)
        return self._parse_findings(response.choices[0].message.content or "[]", documents)


class OpenRouterProvider(BaseProvider):
    async def analyze(self, documents: List[Dict[str, str]], focus: str = "") -> List[Dict[str, Any]]:
        if not self.settings.openrouter_api_key:
            raise ProviderError("OPENROUTER_API_KEY is required for the OpenRouter provider.")
        if not self.settings.openrouter_model:
            raise ProviderError("OPENROUTER_MODEL is required for the OpenRouter provider.")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openrouter_api_key, base_url="https://openrouter.ai/api/v1")
        response = await client.chat.completions.create(
            model=self.settings.openrouter_model,
            messages=[{"role": "user", "content": self._prompt(documents, focus)}],
        )
        return self._parse_findings(response.choices[0].message.content or "[]", documents)


class AnthropicProvider(BaseProvider):
    async def analyze(self, documents: List[Dict[str, str]], focus: str = "") -> List[Dict[str, Any]]:
        if not self.settings.anthropic_api_key:
            raise ProviderError("ANTHROPIC_API_KEY is required for the Anthropic provider.")
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        response = await client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=3000,
            messages=[{"role": "user", "content": self._prompt(documents, focus)}],
        )
        raw = response.content[0].text if response.content else "[]"
        return self._parse_findings(raw, documents)


class GeminiProvider(BaseProvider):
    async def analyze(self, documents: List[Dict[str, str]], focus: str = "") -> List[Dict[str, Any]]:
        api_key = self.settings.gemini_api_key or self.settings.google_api_key
        if not api_key:
            raise ProviderError("GEMINI_API_KEY or GOOGLE_API_KEY is required for the Gemini provider.")
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = self._prompt(documents, focus)

        def call_model() -> str:
            response = client.models.generate_content(model=self.settings.gemini_model, contents=prompt)
            return getattr(response, "text", "") or "[]"

        return self._parse_findings(await asyncio.to_thread(call_model), documents)


def get_provider(settings: Settings) -> BaseProvider:
    provider = settings.due_diligence_provider.lower().strip()
    if provider == "mock":
        return MockProvider(settings)
    if provider == "openai":
        return OpenAIProvider(settings)
    if provider == "anthropic":
        return AnthropicProvider(settings)
    if provider in {"gemini", "google"}:
        return GeminiProvider(settings)
    if provider == "openrouter":
        return OpenRouterProvider(settings)
    raise ProviderError(f"Unsupported provider: {settings.due_diligence_provider}")
