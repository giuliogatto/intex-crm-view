"""Estrazione strutturata da foto di bolla (DDT in ingresso) via OpenAI Vision.

Vedi documentation/ocr-analyses.md §2.1 / §6.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, List, Optional

from LLMservice import call_openai_vision_json

MAX_IMAGE_BYTES = 15 * 1024 * 1024

_INTEX_RE = re.compile(r"\bINTEX\b", re.IGNORECASE)
_CICLO_CODE_RE = re.compile(r"\bT\s?(\d{3}[A-Z]?)\b")


def sniff_image_mime(data: bytes) -> Optional[str]:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _nullable(type_name: str) -> Dict[str, Any]:
    return {"type": [type_name, "null"]}


_RIGA_PROPS: Dict[str, Any] = {
    "riga": {"type": "integer"},
    "testo_grezzo": {"type": "string"},
    "codice_articolo_cliente": _nullable("string"),
    "modello": _nullable("string"),
    "descrizione_articolo": _nullable("string"),
    "colore": _nullable("string"),
    "variante": _nullable("string"),
    "composizione_testo": _nullable("string"),
    "stagione": _nullable("string"),
    "quantita_capi": _nullable("number"),
    "quantita_kg": _nullable("number"),
    "um": _nullable("string"),
    "fonte_qty": _nullable("string"),
    "commessa": _nullable("string"),
    "tessuto": _nullable("string"),
    "fasi_testo": _nullable("string"),
    "note": _nullable("string"),
    "codice_ciclo_manoscritto": {"type": "array", "items": {"type": "string"}},
}

_DOC_PROPS: Dict[str, Any] = {
    "mittente_ragione_sociale": _nullable("string"),
    "mittente_partita_iva": _nullable("string"),
    "destinatario_ragione_sociale": _nullable("string"),
    "numero_bolla": _nullable("string"),
    "data_bolla": _nullable("string"),
    "causale": _nullable("string"),
    "codice_cliente_su_ddt": _nullable("string"),
    "annotazioni_manoscritte": {"type": "array", "items": {"type": "string"}},
    "codice_ciclo_manoscritto": {"type": "array", "items": {"type": "string"}},
    "riferimento_interno_manoscritto": _nullable("string"),
    "note_documento": _nullable("string"),
    "raw_text": {"type": "string"},
    "righe": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": _RIGA_PROPS,
            "required": list(_RIGA_PROPS.keys()),
            "additionalProperties": False,
        },
    },
}

BOLLA_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": _DOC_PROPS,
    "required": list(_DOC_PROPS.keys()),
    "additionalProperties": False,
}

OCR_INSTRUCTIONS = """Sei un sistema di estrazione dati da Documenti di Trasporto (DDT / bolle) italiani del settore tessile.
Le bolle sono inviate a INTEX SRL (tintoria/lavanderia industriale di Sarcedo, VI) da clienti che mandano capi o tessuti in conto lavorazione.

Regole fondamentali:
1. Il CLIENTE è il MITTENTE del DDT: l'azienda che emette il documento (logo/intestazione in alto, dati aziendali, P.IVA del mittente).
   INTEX SRL compare quasi sempre come DESTINATARIO ("Spett.le", "Destinatario", "Luogo di destinazione", talvolta etichettato "Fornitore" o "Cliente" nel modulo): NON va mai usato come mittente.
2. Il campo stampato "Codice cliente" del modulo DDT va in codice_cliente_su_ddt (è il codice di Intex nell'anagrafica del mittente, non il codice cliente Intex).
3. Estrai TUTTE le righe articolo. Una riga = un articolo o una variante/colore distinta con propria quantità. Per righe con griglia taglie, somma le taglie in quantita_capi se il totale non è indicato. Se istruzioni di lavorazione stampate sotto più varianti valgono per tutte, ripetile in fasi_testo di ogni riga.
4. fasi_testo: testo della lavorazione richiesta (es. "TINTO CAPO", "RIENTRO+TINTURA COTONE+ENZIMA", "SBIANCA/PURGA + TINTURA DIRETTA + ..."). Mantieni separatori originali (+, /). Se la descrizione beni è di fatto la lavorazione, copiala anche in fasi_testo.
5. Annotazioni scritte A MANO: esamina con attenzione l'intero foglio (margini, intestazione, spazi sopra/sotto la tabella, zone vicino alle righe) e trascrivi OGNI scritta a mano, una per elemento, in annotazioni_manoscritte (es. "T182 T242", "8702", "EMAIL 13/10", "SALDO", "Kg. 33,50"). I codici del tipo T seguito da 3 cifre ed eventuale lettera (es. T200, T182, T242, T183B, T205) sono codici ciclo Intex: mettili TUTTI in codice_ciclo_manoscritto (della riga se scritti accanto a una riga, altrimenti a livello documento; possono essercene più di uno, es. "T182 T242"). Codici T stampati dentro la descrizione lavorazione vanno anche essi in codice_ciclo_manoscritto della riga.
   Numeri di 4 cifre cerchiati a mano (es. 8686, 8701) vanno in riferimento_interno_manoscritto.
   Quantità scritte a mano con virgola decimale (es. "40,5", "Kg. 33,50") sono di norma CHILOGRAMMI: vanno in quantita_kg (40.5), non in quantita_capi; imposta fonte_qty="manoscritta".
6. commessa: riferimenti ordine/commessa/disposizione/ODP del mittente (es. "PROT/2026/90280", "45855").
7. data_bolla in formato YYYY-MM-DD. Le bolle sono recenti: l'anno è quello corrente o il precedente rispetto alla data odierna indicata nel messaggio; un anno a 2 cifre "26" significa 2026. Numeri con virgola decimale italiana vanno convertiti (4,200 KG -> 4.2).
   Codici stagione come SS26, SS27, AI26, FW26 sono comuni nei codici articolo: "S" e "5" sono spesso confusi, preferisci la lettura come stagione.
8. Non inventare: usa null per i campi assenti o illeggibili. testo_grezzo contiene il testo completo della riga così come appare.
9. raw_text: trascrizione completa del documento (stampato + manoscritto), righe separate da \\n.
Rispondi solo con JSON conforme allo schema."""

def _ocr_prompt() -> str:
    return (
        f"Data odierna: {date.today().isoformat()}. "
        "Estrai i dati di questa bolla (DDT) in JSON secondo lo schema."
    )


def _clean_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s or None


def is_intex(name: Optional[str]) -> bool:
    return bool(name and _INTEX_RE.search(name))


def normalize_ciclo_codes(values: Any, *texts: Optional[str]) -> List[str]:
    """Codici ciclo manoscritti normalizzati (T 205 -> T205), deduplicati, ordine stabile."""
    out: List[str] = []
    candidates: List[str] = []
    for v in values or []:
        candidates.append(str(v))
    for t in texts:
        if t:
            candidates.extend(m.group(0) for m in _CICLO_CODE_RE.finditer(t.upper()))
    for raw in candidates:
        code = re.sub(r"[^A-Z0-9]", "", raw.upper())
        if code and code not in out:
            out.append(code)
    return out


def _to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def normalize_ocr(data: Dict[str, Any]) -> Dict[str, Any]:
    """Applica le regole di dominio (§2.0) sull'output del modello. Ritorna una copia con `warnings`."""
    warnings: List[str] = []
    doc: Dict[str, Any] = {k: _clean_str(data.get(k)) for k in (
        "mittente_ragione_sociale",
        "mittente_partita_iva",
        "destinatario_ragione_sociale",
        "numero_bolla",
        "data_bolla",
        "causale",
        "codice_cliente_su_ddt",
        "riferimento_interno_manoscritto",
        "note_documento",
    )}
    doc["raw_text"] = (data.get("raw_text") or "").strip()
    doc["annotazioni_manoscritte"] = [
        s for s in (_clean_str(a) for a in data.get("annotazioni_manoscritte") or []) if s
    ]

    mitt, dest = doc["mittente_ragione_sociale"], doc["destinatario_ragione_sociale"]
    if is_intex(mitt):
        if dest and not is_intex(dest):
            doc["mittente_ragione_sociale"], doc["destinatario_ragione_sociale"] = dest, mitt
            warnings.append("Mittente e destinatario invertiti: INTEX è il destinatario.")
        else:
            doc["mittente_ragione_sociale"] = None
            warnings.append("Mittente non riconosciuto (estratto INTEX): selezionare il cliente manualmente.")
    if not doc["mittente_ragione_sociale"]:
        if not warnings:
            warnings.append("Mittente non leggibile: selezionare il cliente manualmente.")

    doc_codes = normalize_ciclo_codes(
        data.get("codice_ciclo_manoscritto"), doc.get("note_documento"), *doc["annotazioni_manoscritte"]
    )

    righe: List[Dict[str, Any]] = []
    for idx, r in enumerate(data.get("righe") or [], start=1):
        riga: Dict[str, Any] = {
            k: _clean_str(r.get(k))
            for k in _RIGA_PROPS
            if k not in ("riga", "quantita_capi", "quantita_kg", "codice_ciclo_manoscritto")
        }
        riga["riga"] = idx
        riga["testo_grezzo"] = riga.get("testo_grezzo") or ""
        riga["quantita_capi"] = _to_number(r.get("quantita_capi"))
        riga["quantita_kg"] = _to_number(r.get("quantita_kg"))
        if riga.get("fonte_qty") not in ("stampata", "manoscritta"):
            riga["fonte_qty"] = None
        own_codes = normalize_ciclo_codes(
            r.get("codice_ciclo_manoscritto"), riga.get("fasi_testo"), riga.get("note")
        )
        riga["codice_ciclo_manoscritto"] = own_codes
        righe.append(riga)

    doc["codice_ciclo_manoscritto"] = doc_codes
    for riga in righe:
        riga["codice_ciclo_ereditato"] = not riga["codice_ciclo_manoscritto"] and bool(doc_codes)
    doc["righe"] = righe
    if not righe:
        warnings.append("Nessuna riga articolo estratta dalla bolla.")

    doc["warnings"] = warnings
    return doc


def extract_bolla(image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    """Chiama OpenAI Vision e ritorna {ocr, response_id, model}."""
    result = call_openai_vision_json(
        image_bytes,
        mime_type,
        prompt=_ocr_prompt(),
        instructions=OCR_INSTRUCTIONS,
        json_schema=BOLLA_JSON_SCHEMA,
        schema_name="bolla_ddt",
    )
    try:
        raw = json.loads(result["text"])
    except (TypeError, ValueError) as e:
        raise RuntimeError(f"Risposta OCR non è JSON valido: {e}") from e
    return {
        "ocr": normalize_ocr(raw),
        "response_id": result.get("response_id"),
        "model": result.get("model"),
    }
