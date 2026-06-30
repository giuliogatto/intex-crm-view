"""
Live regression tests for backend/prompts.txt.

Each case sends a real LLM request (same shape as /llmrequest first turn), parses
the JSON response, and verifies:
  1. structural fields match the documented examples in prompts.txt
  2. derived UI tab + backend API path match App.jsx routing

Tests always run sequentially (one LLM call at a time).
"""

import json

import pytest

from cases import PROMPT_CASES
from llm_parse import parse_llm_json
from routing import routing_from_llm_json

REQUIRED_TOP_LEVEL = {"area", "filtri", "azione", "messaggio"}
REQUIRED_FILTRI = {"data_inizio", "data_fine", "cliente", "stagione"}
REQUIRED_AZIONE = {"tipo", "numero_documento"}
VALID_AREAS = {"bolle", "fatture", "offerte", "discrepanze"}
VALID_AZIONE_TIPI = {
    "nessuna",
    "dettaglio_fattura",
    "dettaglio_bolla",
    "dettaglio_offerta",
    "esporta_csv",
    "apri_discrepanze",
    "esegui_somma",
}


def _normalize(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _validate_schema(parsed: dict) -> list[str]:
    errors = []
    missing = REQUIRED_TOP_LEVEL - set(parsed)
    if missing:
        errors.append(f"missing top-level keys: {sorted(missing)}")

    filtri = parsed.get("filtri")
    if not isinstance(filtri, dict):
        errors.append("filtri must be an object")
    else:
        missing_filtri = REQUIRED_FILTRI - set(filtri)
        if missing_filtri:
            errors.append(f"missing filtri keys: {sorted(missing_filtri)}")

    azione = parsed.get("azione")
    if not isinstance(azione, dict):
        errors.append("azione must be an object")
    else:
        missing_azione = REQUIRED_AZIONE - set(azione)
        if missing_azione:
            errors.append(f"missing azione keys: {sorted(missing_azione)}")

    area = parsed.get("area")
    if area not in VALID_AREAS:
        errors.append(f"invalid area: {area!r}")

    tipo = (parsed.get("azione") or {}).get("tipo")
    if tipo not in VALID_AZIONE_TIPI:
        errors.append(f"invalid azione.tipo: {tipo!r}")

    messaggio = parsed.get("messaggio")
    if not isinstance(messaggio, str) or not messaggio.strip():
        errors.append("messaggio must be a non-empty string")

    return errors


def _compare_case(case, parsed: dict) -> list[str]:
    errors = _validate_schema(parsed)
    if errors:
        return errors

    if parsed["area"] != case.expected_area:
        errors.append(f"area: expected {case.expected_area!r}, got {parsed['area']!r}")

    filtri = parsed["filtri"]
    for key, expected in case.expected_filtri.items():
        actual = filtri.get(key, "")
        if key == "cliente" and not case.cliente_strict:
            if _normalize(expected) and _normalize(expected) not in _normalize(actual):
                if _normalize(actual) not in _normalize(expected):
                    errors.append(f"filtri.cliente: expected ~{expected!r}, got {actual!r}")
        elif actual != expected:
            errors.append(f"filtri.{key}: expected {expected!r}, got {actual!r}")

    azione = parsed["azione"]
    for key, expected in case.expected_azione.items():
        actual = azione.get(key, "")
        if actual != expected:
            errors.append(f"azione.{key}: expected {expected!r}, got {actual!r}")

    actual_routing = routing_from_llm_json(parsed)
    routing_errors = case.routing.matches(actual_routing)
    errors.extend(routing_errors)

    return errors


def _routing_summary(parsed: dict) -> str:
    routing = routing_from_llm_json(parsed)
    parts = [f"  tab: {routing.tab}"]
    if routing.list_api:
        parts.append(f"  list_api: {routing.list_api}")
    if routing.detail_api:
        parts.append(f"  detail_api: {routing.detail_api}")
    if routing.ui_actions:
        parts.append(f"  ui_actions: {routing.ui_actions}")
    return "\n".join(parts)


@pytest.mark.prompt_llm
@pytest.mark.parametrize(
    "case",
    PROMPT_CASES,
    ids=[case.id for case in PROMPT_CASES],
)
def test_prompt_case(case, llm_available, call_llm, reference_date, results_writer):
    result = call_llm(case.user_message)

    try:
        parsed = parse_llm_json(result.raw_response, today=reference_date)
    except json.JSONDecodeError as exc:
        results_writer.append_case(
            case.id,
            result,
            passed=False,
            errors=[f"JSON parse error: {exc}"],
        )
        print(results_writer.terminal_line(case.id, passed=False))
        pytest.fail(
            f"LLM did not return valid JSON for case {case.id!r}.\n"
            f"Parse error: {exc}\n"
            f"See: {results_writer.path}"
        )

    errors = _compare_case(case, parsed)
    routing = _routing_summary(parsed)

    results_writer.append_case(
        case.id,
        result,
        passed=not errors,
        errors=errors or None,
        routing_summary=routing,
    )
    print(results_writer.terminal_line(case.id, passed=not errors))

    if errors:
        pytest.fail(
            f"Case {case.id!r} failed.\n"
            f"Failures:\n" + "\n".join(f"  - {err}" for err in errors) + f"\n"
            f"See: {results_writer.path}"
        )
