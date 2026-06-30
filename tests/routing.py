"""
Derive frontend tab + backend API expectations from LLM JSON.

Mirrors the routing decisions in frontend/app/src/App.jsx (applyLlmResponse).
Cliente codice resolution is done in the browser against /api/clienti; tests only
carry the LLM cliente string in filter hints.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
from urllib.parse import urlencode

from llm_parse import replace_oggi_placeholder

LIST_PAGE_SIZE = 50

DETAIL_ACTION_TABS = {
    "dettaglio_fattura": "fatture",
    "dettaglio_bolla": "bolle",
    "dettaglio_offerta": "offerte",
}


@dataclass
class RoutingExpectation:
    tab: str
    list_api: Optional[str] = None
    detail_api: Optional[str] = None
    ui_actions: List[str] = field(default_factory=list)
    filter_hints: dict = field(default_factory=dict)

    def matches(self, other: "RoutingExpectation") -> List[str]:
        errors = []
        if self.tab != other.tab:
            errors.append(f"tab: expected {self.tab!r}, got {other.tab!r}")
        if self.list_api != other.list_api:
            errors.append(f"list_api: expected {self.list_api!r}, got {other.list_api!r}")
        if self.detail_api != other.detail_api:
            errors.append(f"detail_api: expected {self.detail_api!r}, got {other.detail_api!r}")
        if self.ui_actions != other.ui_actions:
            errors.append(f"ui_actions: expected {self.ui_actions!r}, got {other.ui_actions!r}")
        for key, expected in self.filter_hints.items():
            actual = other.filter_hints.get(key, "")
            if _normalize(expected) != _normalize(actual):
                errors.append(
                    f"filter_hints[{key!r}]: expected {expected!r}, got {actual!r}"
                )
        return errors


def _normalize(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _build_list_api(tab: str, filters: dict) -> Optional[str]:
    if tab == "discrepanze":
        return None

    params = {"page": "1", "limit": str(LIST_PAGE_SIZE)}
    for key in ("data_inizio", "data_fine", "stagione"):
        value = filters.get(key, "")
        if value:
            params[key] = value
    codice = filters.get("codice_cliente", "")
    if codice:
        params["codice_cliente"] = codice

    query = urlencode(params)
    return f"GET /api/{tab}?{query}"


def routing_from_llm_json(llm_json: dict, today: Optional[date] = None) -> RoutingExpectation:
    area = llm_json.get("area") or "bolle"
    filtri = llm_json.get("filtri") or {}
    azione = llm_json.get("azione") or {}
    tipo = azione.get("tipo") or "nessuna"
    numero = str(azione.get("numero_documento") or "").strip()

    filter_hints = {
        "data_inizio": replace_oggi_placeholder(filtri.get("data_inizio") or "", today=today),
        "data_fine": replace_oggi_placeholder(filtri.get("data_fine") or "", today=today),
        "stagione": filtri.get("stagione") or "",
        "cliente": filtri.get("cliente") or "",
    }

    ui_actions: List[str] = []
    if tipo == "esporta_csv":
        ui_actions.append("export_csv")

    if numero and tipo in DETAIL_ACTION_TABS:
        tab = DETAIL_ACTION_TABS[tipo]
        detail_path = {
            "dettaglio_fattura": f"/api/fatture/{numero}",
            "dettaglio_bolla": f"/api/bolle/{numero}",
            "dettaglio_offerta": f"/api/offerte/{numero}",
        }[tipo]
        return RoutingExpectation(
            tab=tab,
            detail_api=f"GET {detail_path}",
            filter_hints=filter_hints,
        )

    if area == "discrepanze" or tipo == "apri_discrepanze":
        return RoutingExpectation(
            tab="discrepanze",
            filter_hints=filter_hints,
        )

    tab = area
    list_filters = {
        "data_inizio": filter_hints["data_inizio"],
        "data_fine": filter_hints["data_fine"],
        "stagione": filter_hints["stagione"],
    }
    return RoutingExpectation(
        tab=tab,
        list_api=_build_list_api(tab, list_filters),
        ui_actions=ui_actions,
        filter_hints=filter_hints,
    )


def routing_from_case_definition(
    area: str,
    filtri: dict,
    azione: dict,
    today: Optional[date] = None,
) -> RoutingExpectation:
    return routing_from_llm_json(
        {"area": area, "filtri": filtri, "azione": azione},
        today=today,
    )
