"""
Prompt regression cases taken from backend/prompts.txt examples and App.jsx shortcuts.

Each case defines the user message, the expected LLM JSON (structural fields), and
the UI/backend routing that App.jsx should apply after parsing the response.
"""

from dataclasses import dataclass
from datetime import date
from typing import List

from routing import RoutingExpectation, routing_from_case_definition

# Fixed reference date for {{OGGI}} substitution — keeps expectations stable.
REFERENCE_DATE = date(2026, 6, 30)
REFERENCE_DATE_STR = REFERENCE_DATE.isoformat()


@dataclass
class PromptCase:
    id: str
    user_message: str
    expected_area: str
    expected_filtri: dict
    expected_azione: dict
    routing: RoutingExpectation
    cliente_strict: bool = False


def _case(
    case_id: str,
    user_message: str,
    area: str,
    filtri: dict,
    azione: dict,
    *,
    cliente_strict: bool = False,
) -> PromptCase:
    return PromptCase(
        id=case_id,
        user_message=user_message,
        expected_area=area,
        expected_filtri=filtri,
        expected_azione=azione,
        routing=routing_from_case_definition(area, filtri, azione, today=REFERENCE_DATE),
        cliente_strict=cliente_strict,
    )


PROMPT_CASES: List[PromptCase] = [
    _case(
        "example_1_fatture_anno_cliente",
        "Voglio tutte le fatture del cliente TAM per il 2026",
        "fatture",
        {
            "data_inizio": "2026-01-01",
            "data_fine": REFERENCE_DATE_STR,
            "cliente": "TAM",
            "stagione": "",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "example_2_tutte_fatture_cliente",
        "Mostrami tutte le fatture del cliente TAM",
        "fatture",
        {
            "data_inizio": "",
            "data_fine": "",
            "cliente": "TAM",
            "stagione": "",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "example_3_totale_fatturato_trimestre",
        "Dammi il totale fatturato per cliente TAM nel primo trimestre 2026",
        "fatture",
        {
            "data_inizio": "2026-01-01",
            "data_fine": "2026-03-31",
            "cliente": "TAM",
            "stagione": "",
        },
        {"tipo": "esegui_somma", "numero_documento": ""},
    ),
    _case(
        "example_4_dettaglio_fattura",
        "Mostrami il dettaglio della fattura n. 1207",
        "fatture",
        {
            "data_inizio": "",
            "data_fine": "",
            "cliente": "",
            "stagione": "",
        },
        {"tipo": "dettaglio_fattura", "numero_documento": "1207"},
    ),
    _case(
        "example_4b_dettaglio_bolla",
        "Mostrami il dettaglio della bolla n. 4761",
        "bolle",
        {
            "data_inizio": "",
            "data_fine": "",
            "cliente": "",
            "stagione": "",
        },
        {"tipo": "dettaglio_bolla", "numero_documento": "4761"},
    ),
    _case(
        "example_4c_dettaglio_offerta",
        "Dammi ordine 2012-5234",
        "offerte",
        {
            "data_inizio": "",
            "data_fine": "",
            "cliente": "",
            "stagione": "",
        },
        {"tipo": "dettaglio_offerta", "numero_documento": "2012-5234"},
    ),
    _case(
        "example_5_bolle_marzo",
        "Quali bolle/DDT sono state emesse per TAM nel mese di marzo 2026?",
        "bolle",
        {
            "data_inizio": "2026-03-01",
            "data_fine": "2026-03-31",
            "cliente": "TAM",
            "stagione": "",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "example_7_ordini_stagione",
        "Cerca i cartellini di Maglificio Rossi per la stagione PE 2026",
        "offerte",
        {
            "data_inizio": "",
            "data_fine": "",
            "cliente": "MAGLIFICIO ROSSI",
            "stagione": "PE2026",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "example_10_discrepanze",
        "Confrontami ordine, bolla e fattura per TAM: ci sono differenze?",
        "discrepanze",
        {
            "data_inizio": "",
            "data_fine": "",
            "cliente": "TAM",
            "stagione": "",
        },
        {"tipo": "apri_discrepanze", "numero_documento": ""},
    ),
    _case(
        "example_11_export_csv",
        "Generami un riepilogo esportabile delle fatture di TAM a marzo 2026",
        "fatture",
        {
            "data_inizio": "2026-03-01",
            "data_fine": "2026-03-31",
            "cliente": "TAM",
            "stagione": "",
        },
        {"tipo": "esporta_csv", "numero_documento": ""},
    ),
    _case(
        "example_12_fatture_stagione",
        "Fatture emesse nella stagione PE 2026 per Serigrafia Rossi",
        "fatture",
        {
            "data_inizio": "",
            "data_fine": "",
            "cliente": "SERIGRAFIA ROSSI",
            "stagione": "PE2026",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "example_13_bolle_giorno_singolo",
        "Tutte le bolle del 10 marzo 2026",
        "bolle",
        {
            "data_inizio": "2026-03-10",
            "data_fine": "2026-03-10",
            "cliente": "",
            "stagione": "",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "example_17_fatture_q2",
        "Elenco fatture di Tessitura Rossi nel secondo trimestre 2026",
        "fatture",
        {
            "data_inizio": "2026-04-01",
            "data_fine": "2026-06-30",
            "cliente": "Tessitura Rossi",
            "stagione": "",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "example_18_ordini_ai_stagione_periodo",
        "Commesse fatte a TAM in autunno inverno 25-26 tra novembre e dicembre 2025",
        "offerte",
        {
            "data_inizio": "2025-11-01",
            "data_fine": "2025-12-31",
            "cliente": "TAM",
            "stagione": "AI25-26",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
    _case(
        "shortcut_prima_srl_gen_mar",
        "Mostrami tutte le fatture del cliente PRIMA SRL emesse tra gennaio e marzo.",
        "fatture",
        {
            "data_inizio": "2026-01-01",
            "data_fine": "2026-03-31",
            "cliente": "PRIMA SRL",
            "stagione": "",
        },
        {"tipo": "nessuna", "numero_documento": ""},
    ),
]
