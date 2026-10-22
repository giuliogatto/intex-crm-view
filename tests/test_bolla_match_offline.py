"""Offline checks sul ranking OCR bolle (nessuna chiamata LLM/DB).

Copre il gap golden set «solo TINTO»: bolle tipo Jacob/Canali senza fasi/codici T…
che portano il segnale in descrizione_articolo / tessuto.
"""

from bolla_match import (
    PESI_EVIDENZE,
    SOGLIE_EVIDENZE,
    _evidenze_list,
    _fasi_source,
    _looks_like_fasi,
    _riga_signals,
    _score,
)


def test_pesi_includono_tessuto_e_descrizione_rafforzata():
    assert "tessuto" in PESI_EVIDENZE
    assert PESI_EVIDENZE["tessuto"] >= 0.35
    assert PESI_EVIDENZE["descrizione"] >= 0.35
    assert SOGLIE_EVIDENZE["tessuto"] <= 0.4
    assert SOGLIE_EVIDENZE["descrizione"] <= 0.4


def test_looks_like_fasi_vs_tessuto():
    assert _looks_like_fasi("RIENTRO+TINTURA COTONE+ENZIMA")
    assert _looks_like_fasi("TINTO CAPO REATTIVO")
    assert _looks_like_fasi("SBIANCA/PURGA + TINTURA DIRETTA")
    assert not _looks_like_fasi("JERSEY 100% CO STRETCH")
    assert not _looks_like_fasi("CAPI/CAMICIA 2829 BUBACO")
    assert not _looks_like_fasi("CAMICIA BUBACO")
    assert not _looks_like_fasi("")


def test_fasi_source_non_usa_descrizione_tessuto():
    """Jacob/Canali: descrizione = tessuto, non deve diventare fasi_text."""
    riga = {
        "fasi_testo": None,
        "descrizione_articolo": "JERSEY 95CO 5EA",
    }
    assert _fasi_source(riga) == ""


def test_fasi_source_fallback_quando_descrizione_e_lavorazione():
    riga = {
        "fasi_testo": None,
        "descrizione_articolo": "SBIANCA/PURGA + TINTURA DIRETTA",
    }
    assert "TINTURA" in _fasi_source(riga).upper()


def test_signals_tinto_layout():
    riga = {
        "fasi_testo": "TINTO CAPO",
        "descrizione_articolo": "BLUSA MISTO SETA",
        "tessuto": None,
        "codice_articolo_cliente": "D6262400009",
        "codice_ciclo_manoscritto": ["T200"],
        "commessa": "PROT/2026/90280",
        "colore": "10009",
        "modello": None,
        "composizione_testo": "CO 72% SE 28%",
    }
    sig = _riga_signals(riga, [])
    assert sig["codes"] == ["T200"]
    assert "TINTO" in sig["fasi_text"].upper()
    assert sig["desc"] == "BLUSA MISTO SETA"
    assert sig["tessuto"] == ""


def test_signals_jacob_canali_like_senza_tinto():
    """Profilo tipico bolle senza fasi/T…: tessuto + descrizione articolo."""
    riga = {
        "fasi_testo": None,
        "descrizione_articolo": "CAPI/CAMICIA 2829 BUBACO 100%CO",
        "tessuto": "2829",
        "codice_articolo_cliente": "SS26 JACOB 01",
        "codice_ciclo_manoscritto": [],
        "commessa": None,
        "colore": "125/2829",
        "modello": None,
        "composizione_testo": None,
        "variante": None,
    }
    sig = _riga_signals(riga, [])
    assert sig["codes"] == []
    assert sig["fasi_text"] == ""
    assert "BUBACO" in sig["desc"].upper()
    assert sig["tessuto"] == "2829"
    assert sig["colore"] == "125/2829"


def test_ranking_senza_fasi_con_tessuto_e_descrizione():
    """Senza TINTO/fasi, tessuto+descrizione devono alzare lo score sopra lo zero utile."""
    ev_vuoto = {"fasi": 0.0, "descrizione": 0.0, "tessuto": 0.0, "articolo": 0.0}
    ev_soft = {
        "fasi": 0.0,
        "descrizione": 0.8,
        "tessuto": 0.9,
        "articolo": 0.0,
        "commessa": 0.0,
        "colore": 0.0,
        "composizione": 0.0,
    }
    assert _score(ev_vuoto) == 0.0
    assert _score(ev_soft) > 0.45
    evidenze = _evidenze_list(ev_soft)
    assert "tessuto" in evidenze
    assert "descrizione" in evidenze
    assert "fasi" not in evidenze


def test_evidenze_list_ordine_include_tessuto():
    ev = {
        "codice_ciclo_manoscritto": 0.0,
        "fasi": 0.0,
        "commessa": 0.0,
        "articolo": 0.0,
        "tessuto": 0.9,
        "descrizione": 0.8,
        "colore": 0.0,
        "composizione": 0.0,
    }
    assert _evidenze_list(ev) == ["tessuto", "descrizione"]
