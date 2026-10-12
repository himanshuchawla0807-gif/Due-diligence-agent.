"""Provider and model choices exposed by the local launcher/API."""

from __future__ import annotations

from typing import Any, Dict, List


PROVIDER_ORDER = ["gemini", "mock", "openai", "anthropic", "openrouter"]

MODEL_PRESETS: Dict[str, List[Dict[str, Any]]] = {
    "mock": [
        {"label": "Mock diligence reviewer", "model": "mock-diligence"},
    ],
    "openai": [
        {"label": "GPT-5.5 - X-High", "model": "gpt-5.5", "reasoning_effort": "xhigh"},
        {"label": "GPT-5.5 - High", "model": "gpt-5.5", "reasoning_effort": "high"},
        {"label": "GPT-5.5 - Medium", "model": "gpt-5.5", "reasoning_effort": "medium"},
        {"label": "GPT-5.5 - Low", "model": "gpt-5.5", "reasoning_effort": "low"},
        {"label": "GPT-5.5 - None", "model": "gpt-5.5", "reasoning_effort": "none"},
        {"label": "GPT-5.5 Pro - X-High", "model": "gpt-5.5-pro", "reasoning_effort": "xhigh"},
        {"label": "GPT-5.5 Pro - High", "model": "gpt-5.5-pro", "reasoning_effort": "high"},
        {"label": "GPT-5.5 Pro - Medium", "model": "gpt-5.5-pro", "reasoning_effort": "medium"},
        {"label": "GPT-5.5 Pro - Low", "model": "gpt-5.5-pro", "reasoning_effort": "low"},
    ],
    "anthropic": [
        {"label": "Claude 3.5 Haiku", "model": "claude-3-5-haiku-latest"},
        {"label": "Claude 3.5 Sonnet", "model": "claude-3-5-sonnet-latest"},
    ],
    "gemini": [
        {"label": "Gemini 3.8 Flash", "model": "gemini-3.8-flash"},
    ],
    "openrouter": [
        {
            "label": "Custom OpenRouter model",
            "model": "",
            "custom": True,
            "placeholder": "anthropic/claude-3.5-sonnet or openai/gpt-5.5",
        },
    ],
}


def provider_catalog() -> Dict[str, Any]:
    return {
        "providers": PROVIDER_ORDER,
        "default": "gemini",
        "models": MODEL_PRESETS,
    }
