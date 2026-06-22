import re
from datetime import date
from pathlib import Path

_OGGI_PATTERN = re.compile(r'\{\{?\s*oggi\s*\}?\}', re.IGNORECASE)


def replace_oggi_placeholder(text, today=None):
    """Replace {oggi} / {{OGGI}} placeholders with today's date (YYYY-MM-DD)."""
    if not text:
        return text
    today_str = (today or date.today()).strftime('%Y-%m-%d')
    return _OGGI_PATTERN.sub(today_str, text)


def _load_generic_prompt():
    for path in (
        Path(__file__).resolve().parent / 'prompts.txt',
        Path(__file__).resolve().parent.parent / 'documentation' / 'prompts.txt',
    ):
        if path.is_file():
            return path.read_text(encoding='utf-8')
    raise FileNotFoundError('prompts.txt not found')


genericPrompt = _load_generic_prompt()
