"""Parse LLM responses the same way the frontend does (utils/llm.js)."""

import json
import re
from datetime import date
from typing import Optional

_OGGI_PATTERN = re.compile(r"\{\{?\s*oggi\s*\}\}?", re.IGNORECASE)


def replace_oggi_placeholder(value, today: Optional[date] = None) -> str:
    if not isinstance(value, str) or not value:
        return value or ""
    today_str = (today or date.today()).strftime("%Y-%m-%d")
    return _OGGI_PATTERN.sub(today_str, value)


def parse_llm_json(raw: str, today: Optional[date] = None) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    text = replace_oggi_placeholder(text, today=today)
    return json.loads(text)
