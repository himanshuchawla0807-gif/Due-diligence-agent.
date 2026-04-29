"""Command-line launcher for Due Diligence Agent Open."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from backend.model_catalog import MODEL_PRESETS, PROVIDER_ORDER

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"

LOGO = r"""
   ___       _       _
  / _ \ _ __(_)_ __ | | _____  __
 | | | | '__| | '_ \| |/ _ \ \/ /
 | |_| | |  | | |_) | |  __/>  <
  \___/|_|  |_| .__/|_|\___/_/\_\
              |_|
 Due Diligence Agent Open
"""


def choose_model(provider: str) -> dict:
    presets = MODEL_PRESETS.get(provider, [])
    if provider == "mock" or not presets:
        return presets[0] if presets else {"model": ""}

    print(f"\nChoose a {provider} model:")
    for index, preset in enumerate(presets, start=1):
        suffix = f" [{preset['model']}]" if preset.get("model") else ""
        print(f"{index}. {preset['label']}{suffix}")

    selected = input("Model [1]: ").strip() or "1"
    try:
        preset = presets[int(selected) - 1]
    except (ValueError, IndexError):
        preset = presets[0]

    if preset.get("custom"):
        model = input(f"OpenRouter model name ({preset['placeholder']}): ").strip()
        return {**preset, "model": model}
    return preset


def write_env(provider: str, api_key: str, model_choice: dict) -> None:
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    values = {
        "DUE_DILIGENCE_PROVIDER": provider,
        "DUE_DILIGENCE_MODEL": model_choice.get("model") or "mock-diligence",
    }
    if provider == "openai":
        values["OPENAI_API_KEY"] = api_key
        values["OPENAI_MODEL"] = model_choice.get("model", "gpt-5.5")
        values["OPENAI_REASONING_EFFORT"] = model_choice.get("reasoning_effort", "")
    elif provider == "anthropic":
        values["ANTHROPIC_API_KEY"] = api_key
        values["ANTHROPIC_MODEL"] = model_choice.get("model", "claude-3-5-haiku-latest")
    elif provider == "gemini":
        values["GEMINI_API_KEY"] = api_key
        values["GEMINI_MODEL"] = model_choice.get("model", "gemini-3.1-pro-preview")
    elif provider == "openrouter":
        values["OPENROUTER_API_KEY"] = api_key
        values["OPENROUTER_MODEL"] = model_choice.get("model", "")

    lines = []
    for line in template.splitlines():
        if "=" in line and not line.startswith("#"):
            key = line.split("=", 1)[0]
            if key in values:
                line = f"{key}={values[key]}"
        lines.append(line)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    print(LOGO)
    print("Choose an LLM provider:")
    for index, name in enumerate(PROVIDER_ORDER, start=1):
        suffix = " (no API key, recommended for first localhost test)" if name == "mock" else ""
        print(f"{index}. {name}{suffix}")
    choices = {str(index): name for index, name in enumerate(PROVIDER_ORDER, start=1)}
    provider = choices.get(input("Provider [1]: ").strip() or "1", "mock")

    api_key = ""
    if provider != "mock":
        api_key = input(f"Enter {provider} API key: ").strip()
        if not api_key:
            print("No API key entered. Falling back to mock provider.")
            provider = "mock"

    model_choice = choose_model(provider)
    write_env(provider, api_key, model_choice)

    print("Starting backend on http://localhost:8102")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8102", "--reload"],
        cwd=ROOT,
    )

    print("Session started. Press Ctrl+C to stop the server.")
    try:
        while process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        if process.poll() is None:
            process.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
