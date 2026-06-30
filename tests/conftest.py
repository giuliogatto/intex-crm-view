"""Shared fixtures for prompt regression tests."""

import os
import sys
from datetime import date
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent


def _resolve_backend_dir() -> Path:
    local = REPO_ROOT / "backend"
    if local.is_dir() and (local / "app.py").is_file():
        return local
    docker_app = Path("/app")
    if docker_app.is_dir() and (docker_app / "app.py").is_file():
        return docker_app
    return local


BACKEND_DIR = _resolve_backend_dir()

sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from cases import REFERENCE_DATE  # noqa: E402


def _llm_configured() -> bool:
    provider = os.getenv("LLM_PROVIDER", "OPENAI").strip().upper()
    if provider == "OPENAI":
        return bool(os.getenv("OPENAI_APIKEY"))
    if provider == "GEMINI":
        return bool(os.getenv("GEMINI_APIKEY"))
    return False


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "prompt_llm: live LLM regression test using backend/prompts.txt",
    )


def pytest_collection_modifyitems(config, items):
    """Run prompt tests in case definition order, never in parallel groups."""
    prompt_items = [item for item in items if "prompt_llm" in item.keywords]
    other_items = [item for item in items if item not in prompt_items]
    items[:] = other_items + prompt_items


@pytest.fixture(scope="session")
def reference_date() -> date:
    raw = os.getenv("PROMPT_TEST_REFERENCE_DATE", REFERENCE_DATE.isoformat())
    return date.fromisoformat(raw)


@pytest.fixture(scope="session")
def results_writer():
    from reporting import ResultsWriter

    writer = ResultsWriter(TESTS_DIR / "results")
    yield writer
    if writer.path is not None:
        print(f"\nReport written to: {writer.path}")


@pytest.fixture(scope="session")
def llm_available():
    if not _llm_configured():
        pytest.skip("LLM API key not configured (OPENAI_APIKEY or GEMINI_APIKEY)")
    return True


@pytest.fixture(scope="session")
def call_llm(reference_date):
    from prompts import genericPrompt, replace_oggi_placeholder
    from LLMservice import send_prompt
    from reporting import LlmCallResult

    def _call(user_message: str) -> LlmCallResult:
        prompt_body = replace_oggi_placeholder(genericPrompt, today=reference_date)
        full_input = f"{prompt_body}\n{user_message}"
        prompt_sent = replace_oggi_placeholder(full_input, today=reference_date)
        result = send_prompt(prompt_sent)
        raw_response = replace_oggi_placeholder(result["text"], today=reference_date)
        return LlmCallResult(
            user_message=user_message,
            prompt=prompt_sent,
            raw_response=raw_response,
        )

    return _call
