"""Offline checks: case definitions and routing logic (no LLM calls)."""

import pytest

from cases import PROMPT_CASES, REFERENCE_DATE
from routing import routing_from_case_definition, routing_from_llm_json


@pytest.mark.parametrize("case", PROMPT_CASES, ids=[c.id for c in PROMPT_CASES])
def test_case_definition_is_self_consistent(case):
    expected_json = {
        "area": case.expected_area,
        "filtri": case.expected_filtri,
        "azione": case.expected_azione,
        "messaggio": "placeholder",
    }
    derived = routing_from_llm_json(expected_json, today=REFERENCE_DATE)
    errors = case.routing.matches(derived)
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("case", PROMPT_CASES, ids=[c.id for c in PROMPT_CASES])
def test_expected_json_round_trips_routing(case):
    routing = routing_from_case_definition(
        case.expected_area,
        case.expected_filtri,
        case.expected_azione,
        today=REFERENCE_DATE,
    )
    assert routing.tab == case.routing.tab
    assert routing.list_api == case.routing.list_api
    assert routing.detail_api == case.routing.detail_api
    assert routing.ui_actions == case.routing.ui_actions


def test_detail_routes_use_correct_api_paths():
    case = next(c for c in PROMPT_CASES if c.id == "example_4_dettaglio_fattura")
    routing = routing_from_llm_json(
        {
            "area": case.expected_area,
            "filtri": case.expected_filtri,
            "azione": case.expected_azione,
        },
        today=REFERENCE_DATE,
    )
    assert routing.detail_api == "GET /api/fatture/1207"
    assert routing.tab == "fatture"


def test_discrepanze_has_no_list_api():
    case = next(c for c in PROMPT_CASES if c.id == "example_10_discrepanze")
    routing = routing_from_llm_json(
        {
            "area": case.expected_area,
            "filtri": case.expected_filtri,
            "azione": case.expected_azione,
        },
        today=REFERENCE_DATE,
    )
    assert routing.tab == "discrepanze"
    assert routing.list_api is None
    assert routing.detail_api is None
