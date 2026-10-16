"""Espansione sinonimi fasi: niente match per sottostringa su abbreviazioni corte."""

from cicli_routes import _FALLBACK_SINONIMI, _expand_fasi_keywords


def _expand(kw: str):
    sinonimi = {k: list(v) for k, v in _FALLBACK_SINONIMI.items()}
    _, meta = _expand_fasi_keywords([kw], sinonimi)
    return meta[kw]


def test_ammorbidente_non_espande_tintura():
    variants = _expand("ammorbidente")
    assert variants == ["AMMORBIDENTE"]
    for bad in ("T", "TI", "TINTO", "TINTURA"):
        assert bad not in variants


def test_tintura_e_abbreviazioni_restano_collegate():
    for kw in ("tintura", "tinto", "T", "TI"):
        variants = set(_expand(kw))
        assert {"T", "TI", "TINTO", "TINTURA"} <= variants


def test_altri_sinonimi_intatti():
    assert "ENZ" in _expand("enzima")
    assert "MANGIAPELO" in _expand("mpelo")
    assert "REATTIVO" in _expand("reattivo")
