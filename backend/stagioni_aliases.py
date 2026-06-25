"""
Canonical season codes (UI / LLM) map to Oracle ERP codes stored on documents.

Oracle uses legacy short codes (e.g. PE 26, AI 26). Friendly codes (PE2026,
AI25-26) are resolved at query time so filters and the dropdown stay consistent.
"""

# Canonical UI/LLM code -> Oracle ERP code on document headers
STAGIONE_ALIASES = {
    "PE2026": "PE 26",
    "AI25-26": "AI 26",
}

ORACLE_TO_CANONICAL = {oracle: canonical for canonical, oracle in STAGIONE_ALIASES.items()}

CANONICAL_DESCRIPTIONS = {
    "PE2026": "Primavera/Estate 2026",
    "AI25-26": "Autunno/Inverno 2025-2026",
}


def resolve_stagione_filter(codice):
    """Map a filter value from the UI or LLM to the Oracle document code."""
    if not codice:
        return None
    value = str(codice).strip()
    if not value:
        return None
    return STAGIONE_ALIASES.get(value, value)


def stagione_display_label(oracle_codice, db_descrizione=None):
    """Prefer a friendly canonical label when the document uses an aliased code."""
    if not oracle_codice:
        return db_descrizione or ""
    canonical = ORACLE_TO_CANONICAL.get(oracle_codice)
    if canonical:
        return CANONICAL_DESCRIPTIONS.get(canonical, db_descrizione or oracle_codice)
    return db_descrizione or oracle_codice


def apply_stagione_filter(query, params, filters, column):
    """Append an exact-match season predicate using alias resolution."""
    raw = (filters.get("stagione") or "").strip()
    if not raw:
        return query, params
    oracle_code = resolve_stagione_filter(raw)
    query += f" AND {column} = %(stagione)s"
    params["stagione"] = oracle_code
    return query, params


def build_stagioni_api_list(db_rows):
    """
    Build the dropdown list: show canonical aliases with friendly names and hide
    Oracle codes that are superseded by an alias (e.g. hide PE 26 when PE2026 exists).
    """
    hidden_oracle = set(STAGIONE_ALIASES.values())
    merged = {}

    for codice, descrizione in db_rows:
        if codice in hidden_oracle:
            continue
        if codice in CANONICAL_DESCRIPTIONS:
            merged[codice] = CANONICAL_DESCRIPTIONS[codice]
        else:
            merged[codice] = descrizione

    for canonical, descrizione in CANONICAL_DESCRIPTIONS.items():
        merged.setdefault(canonical, descrizione)

    return [
        {"codice": codice, "descrizione": merged[codice]}
        for codice in sorted(merged.keys(), reverse=True)
    ]
