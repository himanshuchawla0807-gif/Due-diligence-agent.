"""Provider adapters for diligence review."""

from __future__ import annotations

import asyncio
import json
import re
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
        docs = "\n\n".join(self._source_block(index, doc) for index, doc in enumerate(documents, start=1))
        return (
            "You are a senior VC/PE due diligence analyst reviewing a local uploaded data room. "
            "Return JSON only in this exact shape: "
            '{"findings":[{"category":"","severity":"","finding":"","evidence":"","recommendation":"",'
            '"source_file":"","source_path":"","text_snippet":""}]}. '
            "Produce 12 to 20 findings when enough evidence exists. Every finding must be grounded in one "
            "specific source file. Do not make a claim unless the evidence is present in the provided source "
            "blocks. Use the source_file exactly as provided. Prefer concrete fraud, data integrity, financial, "
            "legal, security, compliance, product, commercial, HR, and operations risks over generic summaries. "
            "Act like an investment committee diligence lead: triangulate contradictions across files, identify "
            "deal blockers, quantify where numbers exist, and separate evidence from inference. Use severity "
            "values Critical, High, Medium, or Low. Evidence must name the relevant source file and cite the exact "
            "fact or contradiction. Recommendations must be actionable next diligence steps.\n\n"
            f"Focus: {focus or 'commercial, financial, legal, technical, and risk signals'}\n\n"
            f"{docs}"
        )

    def _parse_findings(self, raw: str, documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        raw = self._strip_code_fences(raw)
        raw = self._extract_json(raw)
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                data = data.get("findings") or data.get("data") or [data]
            if isinstance(data, list):
                normalized = [self._normalize_finding(item, documents) for item in data if isinstance(item, dict)]
                return [item for item in normalized if item.get("finding")]
        except Exception as exc:
            raise ProviderError(
                "The selected provider returned a response that could not be parsed as due diligence JSON. "
                "Try again, select a stronger model, or switch to mock mode for localhost UI testing."
            ) from exc
        raise ProviderError("The selected provider returned no findings in the expected JSON format.")

    def _source_block(self, index: int, doc: Dict[str, str]) -> str:
        text = (doc.get("text") or "[No extractable text found]").strip()
        if len(text) > 2400:
            text = f"{text[:2400]}\n[Excerpt truncated for prompt size]"
        return (
            f"[SOURCE {index}]\n"
            f"file_name: {doc.get('file_name') or 'Source Document'}\n"
            f"source_path: {doc.get('source_path') or 'local upload'}\n"
            f"chunk_index: {doc.get('chunk_index', '')}\n"
            f"excerpt:\n{text}"
        )

    def _strip_code_fences(self, raw: str) -> str:
        cleaned = (raw or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        return cleaned.strip()

    def _extract_json(self, raw: str) -> str:
        cleaned = raw.strip()
        if cleaned.startswith("{") or cleaned.startswith("["):
            return cleaned
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if match:
            return match.group(1)
        return cleaned

    def _normalize_finding(self, item: Dict[str, Any], documents: List[Dict[str, str]]) -> Dict[str, Any]:
        source_file = item.get("source_file") or item.get("file_name") or item.get("document")
        if not source_file and documents:
            source_file = documents[0].get("file_name")
        source_path = item.get("source_path")
        if not source_path and source_file:
            for document in documents:
                if document.get("file_name") == source_file:
                    source_path = document.get("source_path")
                    break
        return {
            "category": item.get("category") or "General",
            "severity": item.get("severity") or "Medium",
            "finding": item.get("finding") or item.get("summary") or "",
            "evidence": item.get("evidence") or "",
            "recommendation": item.get("recommendation") or "",
            "source_file": source_file,
            "source_path": source_path,
            "text_snippet": item.get("text_snippet") or item.get("snippet") or item.get("evidence") or "",
        }


class MockProvider(BaseProvider):
    async def analyze(self, documents: List[Dict[str, str]], focus: str = "") -> List[Dict[str, Any]]:
        await asyncio.sleep(0.2)
        return self.mock_findings(documents)

    def mock_findings(self, documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        if not documents:
            documents = [{"file_name": "Sample Data Room", "text": ""}]
        categories = [
            "Data Integrity",
            "Financial",
            "Legal",
            "Security & Compliance",
            "Commercial",
            "Operations",
            "Human Resources",
            "Product",
        ]
        findings: List[Dict[str, Any]] = []
        for index, doc in enumerate(documents[:12]):
            text = (doc.get("text") or "mock diligence review").strip()
            snippet = text[:260]
            category = categories[index % len(categories)]
            severity = "High" if any(term in text.lower() for term in ("fraud", "fake", "risk", "mismatch")) else "Medium"
            findings.append(
                {
                    "category": category,
                    "severity": severity,
                    "finding": f"File-directed diligence review identified a {category.lower()} issue in {doc['file_name']}.",
                    "evidence": f"{doc['file_name']}: {snippet}",
                    "recommendation": "Validate the source file against primary records and request management clarification.",
                    "source_file": doc.get("file_name"),
                    "source_path": doc.get("source_path"),
                    "text_snippet": snippet,
                }
            )
        return findings


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
            "temperature": 0.2,
            "max_completion_tokens": 8192,
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
            max_tokens=8192,
            temperature=0.2,
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
            max_tokens=8192,
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
            from google.genai import types

            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    candidate_count=1,
                    max_output_tokens=8192,
                ),
            )
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
