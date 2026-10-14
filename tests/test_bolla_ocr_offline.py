"""Offline checks: normalizzazione OCR bolle (regole da documentation/esempi-bolle, nessuna chiamata LLM/DB)."""

from bolla_ocr import BOLLA_JSON_SCHEMA, normalize_ciclo_codes, normalize_ocr, sniff_image_mime


def _raw(**overrides):
    base = {
        "mittente_ragione_sociale": "TRANSIT M & COMPANY s.p.a.",
        "mittente_partita_iva": "IT01839530241",
        "destinatario_ragione_sociale": "INTEX S.R.L.",
        "numero_bolla": "1409/L",
        "data_bolla": "2026-10-13",
        "causale": "MERCE CONTO LAVORAZIONE",
        "codice_cliente_su_ddt": "0001588",
        "annotazioni_manoscritte": ["T182 T242", "8702", "EMAIL 13/10"],
        "codice_ciclo_manoscritto": ["t 242"],
        "riferimento_interno_manoscritto": "8702",
        "note_documento": None,
        "raw_text": "...",
        "righe": [
            {
                "riga": 1,
                "testo_grezzo": "SS26 U S/C122 COL U02 RIENTRO+TINTURA COTONE+ENZIMA KG 4,200",
                "codice_articolo_cliente": "SS26 U S/C122 COL U02",
                "modello": None,
                "descrizione_articolo": "RIENTRO+TINTURA COTONE+ENZIMA",
                "colore": "U02",
                "variante": None,
                "composizione_testo": None,
                "stagione": "SS26",
                "quantita_capi": None,
                "quantita_kg": "4,200",
                "um": "KG",
                "fonte_qty": "stampata",
                "commessa": None,
                "tessuto": None,
                "fasi_testo": "RIENTRO+TINTURA COTONE+ENZIMA",
                "note": None,
                "codice_ciclo_manoscritto": [],
            }
        ],
    }
    base.update(overrides)
    return base


def test_mittente_is_client_and_codes_normalized():
    doc = normalize_ocr(_raw())
    assert doc["mittente_ragione_sociale"].startswith("TRANSIT")
    assert doc["codice_ciclo_manoscritto"] == ["T242", "T182"]
    riga = doc["righe"][0]
    assert riga["quantita_kg"] == 4.2
    assert riga["codice_ciclo_manoscritto"] == []
    assert riga["codice_ciclo_ereditato"] is True
    assert doc["warnings"] == []


def test_intex_as_mittente_is_swapped():
    doc = normalize_ocr(
        _raw(mittente_ragione_sociale="INTEX SRL", destinatario_ragione_sociale="Project S.r.l.")
    )
    assert doc["mittente_ragione_sociale"] == "Project S.r.l."
    assert doc["destinatario_ragione_sociale"] == "INTEX SRL"
    assert doc["warnings"]


def test_intex_only_clears_mittente():
    doc = normalize_ocr(_raw(mittente_ragione_sociale="INTEX SRL", destinatario_ragione_sociale="INTEX SRL"))
    assert doc["mittente_ragione_sociale"] is None
    assert doc["warnings"]


def test_printed_cycle_code_in_fasi_is_extracted():
    codes = normalize_ciclo_codes([], "T205 TINTO CAPO REATTIVO + RASAPELO + NO MORBIDO")
    assert codes == ["T205"]
    assert normalize_ciclo_codes(["T183B"]) == ["T183B"]
    assert normalize_ciclo_codes([], "22CMSS080A002246G RO190H6") == []


def test_sniff_mime():
    assert sniff_image_mime(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert sniff_image_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert sniff_image_mime(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff_image_mime(b"%PDF-1.7") is None


def _assert_strict(schema):
    if schema.get("type") == "object":
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        for sub in schema["properties"].values():
            _assert_strict(sub)
    if "items" in schema:
        _assert_strict(schema["items"])


def test_schema_is_strict_compatible():
    _assert_strict(BOLLA_JSON_SCHEMA)
