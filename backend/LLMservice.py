import base64
import os
import sys
from typing import List, Optional, Tuple, Union

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OPENAI_OCR_MODEL = "gpt-5.4"
DEFAULT_OPENAI_OCR_DETAIL = "original"

# (connect, read): se api.openai.com non è raggiungibile dal container, fallire in pochi
# secondi invece di restare appesi fino al 502 di Cloudflare (senza header CORS).
OpenAITimeout = Union[float, Tuple[float, float]]
DEFAULT_OCR_TIMEOUT: OpenAITimeout = (10, 90)


def get_ocr_model_name() -> str:
    return os.getenv("OPENAI_OCR_MODEL") or DEFAULT_OPENAI_OCR_MODEL


def _get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "OPENAI").strip().upper()


def get_model_name() -> str:
    provider = _get_provider()
    if provider == "OPENAI":
        return os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    if provider == "GEMINI":
        return os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported: OPENAI, GEMINI")


def _extract_openai_response_text(data: dict) -> str:
    for item in data.get("output", []):
        if item.get("type") != "message" or item.get("role") != "assistant":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    raise ValueError("OpenAI response did not contain assistant text")


def _call_openai(
    input_text: str,
    instructions: Optional[str] = None,
    previous_response_id: Optional[str] = None,
) -> dict:
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


def call_openai_vision_json(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    instructions: str,
    json_schema: dict,
    schema_name: str = "estrazione",
    timeout: Optional[OpenAITimeout] = None,
) -> dict:
    """
    OCR / estrazione strutturata da immagine via Responses API.
    Returns {"text": str (JSON conforme a json_schema), "response_id": str, "model": str}.
    """
    api_key = os.getenv("OPENAI_APIKEY")
    if not api_key:
        raise ValueError("OPENAI_APIKEY environment variable is not set")

    model = get_ocr_model_name()
    detail = os.getenv("OPENAI_OCR_DETAIL") or DEFAULT_OPENAI_OCR_DETAIL
    data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    payload = {
        "model": model,
        "instructions": instructions,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": data_url, "detail": detail},
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": json_schema,
                "strict": True,
            }
        },
        "store": False,
    }

    if timeout is None:
        timeout = DEFAULT_OCR_TIMEOUT

    print(
        f"[ocr] OpenAI POST model={model} detail={detail} "
        f"image_bytes={len(image_bytes)} timeout={timeout}",
        file=sys.stderr,
        flush=True,
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except requests.exceptions.ConnectTimeout as e:
        raise RuntimeError(
            "Timeout di connessione verso api.openai.com "
            "(il container non raggiunge OpenAI entro 10s)."
        ) from e
    except requests.exceptions.ReadTimeout as e:
        raise RuntimeError(
            "Timeout in lettura dalla risposta OpenAI OCR (limite 90s)."
        ) from e
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            f"Connessione a api.openai.com fallita dal container: {e}"
        ) from e

    print(
        f"[ocr] OpenAI status={response.status_code} body_len={len(response.content)}",
        file=sys.stderr,
        flush=True,
    )
    if response.status_code >= 400:
        try:
            err = response.json().get("error") or {}
            detail_msg = err.get("message") or response.text
            err_code = (err.get("code") or err.get("type") or "").lower()
        except ValueError:
            detail_msg = response.text
            err_code = ""
        low = (detail_msg or "").lower()
        if response.status_code == 429 and (
            "credit" in low
            or "billing" in low
            or "quota" in low
            or err_code in ("insufficient_quota", "billing_not_active")
        ):
            raise RuntimeError(
                "OCR_NO_CREDITS: Il credito OpenAI per l'OCR è esaurito. "
                "Ricaricare il piano su platform.openai.com (Billing) e riprovare."
            )
        if response.status_code == 429:
            raise RuntimeError(
                "OCR_RATE_LIMIT: Troppe richieste OpenAI in questo momento. "
                "Attendere qualche secondo e riprovare."
            )
        raise RuntimeError(f"OpenAI {response.status_code}: {detail_msg[:500]}")
    data = response.json()
    return {
        "text": _extract_openai_response_text(data),
        "response_id": data.get("id"),
        "model": model,
    }


def _call_gemini(
    input_text: str,
    instructions: Optional[str] = None,
    history: Optional[List] = None,
) -> dict:
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
    instructions: Optional[str] = None,
    previous_response_id: Optional[str] = None,
    history: Optional[List] = None,
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
