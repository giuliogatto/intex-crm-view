import os

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "OPENAI").strip().upper()


def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_APIKEY")
    if not api_key:
        raise ValueError("OPENAI_APIKEY environment variable is not set")

    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_APIKEY")
    if not api_key:
        raise ValueError("GEMINI_APIKEY environment variable is not set")

    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def send_prompt(prompt: str) -> str:
    """
    Send a prompt to the configured LLM provider and return the response text.

    Provider is selected via LLM_PROVIDER (default: OPENAI).
    Supported values: OPENAI, GEMINI.
    """
    provider = _get_provider()

    if provider == "OPENAI":
        return _call_openai(prompt)
    if provider == "GEMINI":
        return _call_gemini(prompt)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported: OPENAI, GEMINI")
