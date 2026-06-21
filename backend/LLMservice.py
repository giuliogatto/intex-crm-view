import os

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "OPENAI").strip().upper()


def get_model_name() -> str:
    provider = _get_provider()
    if provider == "OPENAI":
        return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if provider == "GEMINI":
        return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported: OPENAI, GEMINI")


def _extract_openai_response_text(data: dict) -> str:
    for item in data.get("output", []):
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    raise ValueError("OpenAI response did not contain assistant text")


def _call_openai(input_text: str, instructions: str | None = None, previous_response_id: str | None = None) -> dict:
    api_key = os.getenv("OPENAI_APIKEY")
    if not api_key:
        raise ValueError("OPENAI_APIKEY environment variable is not set")

    model = get_model_name()
    payload = {
        "model": model,
        "input": input_text,
        "store": True,
    }
    if instructions:
        payload["instructions"] = instructions
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "text": _extract_openai_response_text(data),
        "response_id": data["id"],
    }


def _call_gemini(input_text: str, instructions: str | None = None, history: list | None = None) -> dict:
    api_key = os.getenv("GEMINI_APIKEY")
    if not api_key:
        raise ValueError("GEMINI_APIKEY environment variable is not set")

    model = get_model_name()
    contents = []

    if instructions:
        contents.append({"role": "user", "parts": [{"text": instructions}]})
        contents.append({"role": "model", "parts": [{"text": "OK"}]})

    for msg in history or []:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    contents.append({"role": "user", "parts": [{"text": input_text}]})

    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": api_key},
        headers={"Content-Type": "application/json"},
        json={"contents": contents},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return {
        "text": text,
        "response_id": data.get("responseId") or f"gemini-{data['candidates'][0].get('index', 0)}",
    }


def send_prompt(
    input_text: str,
    instructions: str | None = None,
    previous_response_id: str | None = None,
    history: list | None = None,
) -> dict:
    """
    Send a prompt to the configured LLM provider.

    Returns {"text": str, "response_id": str}.
    OpenAI uses the Responses API with optional previous_response_id chaining.
    Gemini replays history from the database when provided.
    """
    provider = _get_provider()

    if provider == "OPENAI":
        return _call_openai(input_text, instructions, previous_response_id)
    if provider == "GEMINI":
        if previous_response_id and not history:
            raise ValueError("Gemini provider requires message history for existing chats")
        return _call_gemini(input_text, instructions, history)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported: OPENAI, GEMINI")
