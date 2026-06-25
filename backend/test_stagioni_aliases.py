from stagioni_aliases import (
    apply_stagione_filter,
    build_stagioni_api_list,
    resolve_stagione_filter,
    stagione_display_label,
)


def test_resolve_stagione_filter():
    assert resolve_stagione_filter("PE2026") == "PE 26"
    assert resolve_stagione_filter("AI25-26") == "AI 26"
    assert resolve_stagione_filter("PE 12") == "PE 12"
    assert resolve_stagione_filter("") is None


def test_stagione_display_label():
    assert stagione_display_label("PE 26") == "Primavera/Estate 2026"
    assert stagione_display_label("AI 26") == "Autunno/Inverno 2025-2026"
    assert stagione_display_label("PE 12", "Stagione PE 12") == "Stagione PE 12"


def test_build_stagioni_api_list_hides_oracle_alias_targets():
    rows = [
        ("PE 26", "Stagione PE 26"),
        ("PE2026", "Primavera/Estate 2026"),
        ("PE 12", "Stagione PE 12"),
        ("AI 26", "Stagione AI 26"),
    ]
    result = build_stagioni_api_list(rows)
    codes = [item["codice"] for item in result]
    assert "PE2026" in codes
    assert "PE 26" not in codes
    assert "AI25-26" in codes
    assert "AI 26" not in codes
    assert codes.count("PE2026") == 1


def test_apply_stagione_filter():
    query = "FROM t WHERE 1=1"
    params = {}
    query, params = apply_stagione_filter(query, params, {"stagione": "PE2026"}, "t.codice_stagione")
    assert "t.codice_stagione = %(stagione)s" in query
    assert params["stagione"] == "PE 26"
