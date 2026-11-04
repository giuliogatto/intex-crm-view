"""Ricerca cicli compatibili con un ciclo di input (stesso cliente).

Uso:

    from cicli_compatibili import trova_cicli_compatibili

    risultati = trova_cicli_compatibili(
        cursor,
        {"codice_cliente": "1213", "codice_articolo": "00058", "codice_ciclo": "T100L",
         "codice_linea": ".", "codice_stagione": "AI 27", "codice_composizione": "00006"},
        cliente="1213",
        livello=3,
    )

Ogni risultato è un dict JSON-serializzabile:

    {
      "ciclo": {...chiave a 6 campi + descrizioni...},
      "compatibilita": 90.0,
      "simili": [{"campo": ..., "valore": ...}, ...],
      "differenze": [{"campo": ..., "input": ..., "candidato": ..., "penalita": ...}, ...]
    }

Punteggio: si parte da 100 e si sottraggono le penalità di PENALITA.
Articolo, stagione e codici ciclo non penalizzano (cambio solo articolo/stagione = 100%);
ogni fase aggiunta / mancante / sostituita / scambiata costa 10 punti (una fase = 90%).
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

KEY_FIELDS = (
    "codice_cliente",
    "codice_articolo",
    "codice_ciclo",
    "codice_linea",
    "codice_stagione",
    "codice_composizione",
)

# Punti sottratti a 100. I campi testuali sono scalati per (1 - similarità).
PENALITA: Dict[str, float] = {
    "fase": 10,
    "nota_fase": 3,
    "unita_misura_fase": 2,
    "macrofase": 2,
    "composizione": 5,
    "linea": 3,
    "ds_ciclo": 8,
    "ds_ciclo_bolle_fat": 4,
    "note": 5,
    "ds_applicazione": 4,
    "ds_ricamo": 4,
    "ds_stampa": 4,
    "codice_reparto": 3,
    "codice_gruppo": 2,
}

# Differenze riportate ma senza impatto sul punteggio.
CAMPI_NEUTRI = ("codice_articolo", "codice_stagione", "codice_ciclo", "codice_ciclo_cli")

# Senza nemmeno una fase in comune il ciclo non è davvero compatibile,
# anche se il resto della testata coincide.
MAX_SENZA_FASI_COMUNI = 40.0

# livello -> compatibilità minima (%). 1 = molto ampio, 5 = solo cicli equivalenti.
LIVELLI_SOGLIA: Dict[int, float] = {1: 30.0, 2: 50.0, 3: 70.0, 4: 90.0, 5: 100.0}

_TESTI_TESTATA = ("ds_ciclo", "ds_ciclo_bolle_fat", "note")
_CODICI_TESTATA = ("ds_applicazione", "ds_ricamo", "ds_stampa", "codice_reparto", "codice_gruppo")
_VALORI_VUOTI = {"", ".", "*", "-"}

_TESTATA_COLS = (
    "codice_cliente", "codice_articolo", "codice_ciclo", "codice_linea",
    "codice_stagione", "codice_composizione", "codice_ciclo_cli", "ds_ciclo",
    "ds_ciclo_bolle_fat", "ds_applicazione", "ds_ricamo", "ds_stampa", "note",
    "codice_reparto", "codice_gruppo", "st_record", "data_ins",
    "ragione_sociale", "ds_articolo", "ds_stagione", "ds_composizione", "ds_linea",
)

CicloInput = Union[Dict[str, Any], Sequence[str]]


# ---------------------------------------------------------------------------
# Normalizzazione / similarità testo
# ---------------------------------------------------------------------------
def _norm(value: Any) -> str:
    if value is None:
        return ""
    t = unicodedata.normalize("NFKD", str(value))
    t = "".join(c for c in t if not unicodedata.combining(c)).upper()
    t = re.sub(r"[+/().,;:'\"\-_]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return "" if t in _VALORI_VUOTI else t


def similarita_testo(a: Any, b: Any) -> float:
    """0..1: massimo fra rapporto caratteri e Jaccard sui token (ordine irrilevante)."""
    na, nb = _norm(a), _norm(b)
    if na == nb:
        return 1.0
    if not na or not nb:
        return 0.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    return max(ratio, jaccard)


# ---------------------------------------------------------------------------
# Fasi
# ---------------------------------------------------------------------------
def _fase_key(fase: Dict[str, Any]) -> str:
    return _norm(fase.get("codice_fase")) or _norm(fase.get("ds_fase")) or _norm(fase.get("note"))


def _fase_label(fase: Optional[Dict[str, Any]]) -> Optional[str]:
    if not fase:
        return None
    parts = [str(fase.get("codice_fase") or "").strip(), str(fase.get("ds_fase") or "").strip()]
    label = " ".join(p for p in parts if p)
    nota = str(fase.get("note") or "").strip()
    return f"{label} ({nota})" if nota else label


def _allinea_fasi(a: List[Dict[str, Any]], b: List[Dict[str, Any]]) -> List[Tuple[str, Any, Any]]:
    """Allineamento Damerau-Levenshtein (OSA) sulle sequenze di fasi.

    Ritorna operazioni: uguale | sostituita | mancante (solo input) | aggiunta (solo candidato)
    | scambio (due fasi adiacenti invertite, conta come una modifica).
    """
    ka, kb = [_fase_key(f) for f in a], [_fase_key(f) for f in b]
    n, m = len(ka), len(kb)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j

    def swap(i: int, j: int) -> bool:
        return (
            i > 1 and j > 1
            and ka[i - 1] == kb[j - 2] and ka[i - 2] == kb[j - 1]
            and ka[i - 1] != ka[i - 2]
        )

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ka[i - 1] == kb[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if swap(i, j):
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)

    ops: List[Tuple[str, Any, Any]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ka[i - 1] == kb[j - 1] and d[i][j] == d[i - 1][j - 1]:
            ops.append(("uguale", a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif swap(i, j) and d[i][j] == d[i - 2][j - 2] + 1:
            ops.append(("scambio", (a[i - 2], a[i - 1]), (b[j - 2], b[j - 1])))
            i, j = i - 2, j - 2
        elif i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + 1:
            ops.append(("sostituita", a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("mancante", a[i - 1], None))
            i -= 1
        else:
            ops.append(("aggiunta", None, b[j - 1]))
            j -= 1
    ops.reverse()
    return ops


def _confronta_fasi(
    fasi_in: List[Dict[str, Any]],
    fasi_cand: List[Dict[str, Any]],
    simili: List[Dict[str, Any]],
    differenze: List[Dict[str, Any]],
) -> Tuple[float, int]:
    """Ritorna (penalità totale, numero fasi uguali)."""
    penalita = 0.0
    uguali: List[str] = []
    for op, fin, fcand in _allinea_fasi(fasi_in, fasi_cand):
        if op == "uguale":
            uguali.append(_fase_label(fin))
            for campo, chiave, peso in (
                ("nota_fase", "note", PENALITA["nota_fase"]),
                ("unita_misura_fase", "codice_unita_mis", PENALITA["unita_misura_fase"]),
                ("macrofase", "codice_macrofase", PENALITA["macrofase"]),
            ):
                if _norm(fin.get(chiave)) != _norm(fcand.get(chiave)):
                    penalita += peso
                    differenze.append({
                        "campo": campo,
                        "fase": fin.get("codice_fase"),
                        "input": fin.get(chiave),
                        "candidato": fcand.get(chiave),
                        "penalita": peso,
                    })
            continue

        penalita += PENALITA["fase"]
        diff: Dict[str, Any] = {"campo": "fase", "tipo": op, "penalita": PENALITA["fase"]}
        if op == "scambio":
            diff["input"] = [_fase_label(f) for f in fin]
            diff["candidato"] = [_fase_label(f) for f in fcand]
        else:
            diff["input"] = _fase_label(fin)
            diff["candidato"] = _fase_label(fcand)
            if op == "sostituita":
                diff["similarita_descrizione"] = round(
                    similarita_testo(fin.get("ds_fase"), fcand.get("ds_fase")), 2
                )
        differenze.append(diff)

    if uguali:
        simili.append({
            "campo": "fasi",
            "valore": uguali,
            "dettaglio": f"{len(uguali)}/{max(len(fasi_in), len(fasi_cand))} fasi uguali",
        })
        if len(uguali) == len(fasi_in) == len(fasi_cand):
            simili.append({"campo": "sequenza_fasi", "valore": "identica"})
    return penalita, len(uguali)


# ---------------------------------------------------------------------------
# Confronto testata + fasi
# ---------------------------------------------------------------------------
def confronta_cicli(ciclo_input: Dict[str, Any], candidato: Dict[str, Any]) -> Dict[str, Any]:
    """Confronta due cicli già caricati (testata + chiave 'fasi'). Funzione pura."""
    simili: List[Dict[str, Any]] = []
    differenze: List[Dict[str, Any]] = []
    penalita = 0.0

    for campo in CAMPI_NEUTRI:
        a, b = ciclo_input.get(campo), candidato.get(campo)
        if _norm(a) == _norm(b):
            if _norm(a):
                simili.append({"campo": campo, "valore": a})
        else:
            differenze.append({"campo": campo, "input": a, "candidato": b, "penalita": 0})

    for campo, peso_key in (("codice_composizione", "composizione"), ("codice_linea", "linea")):
        a, b = ciclo_input.get(campo), candidato.get(campo)
        if _norm(a) == _norm(b):
            if _norm(a):
                simili.append({"campo": campo, "valore": a})
        else:
            peso = PENALITA[peso_key]
            penalita += peso
            ds_campo = "ds_composizione" if peso_key == "composizione" else "ds_linea"
            differenze.append({
                "campo": campo,
                "input": ciclo_input.get(ds_campo) or a,
                "candidato": candidato.get(ds_campo) or b,
                "penalita": peso,
            })

    for campo in _TESTI_TESTATA:
        a, b = ciclo_input.get(campo), candidato.get(campo)
        sim = similarita_testo(a, b)
        if sim >= 1.0:
            if _norm(a):
                simili.append({"campo": campo, "valore": a})
            continue
        peso = round(PENALITA[campo] * (1.0 - sim), 1)
        penalita += peso
        differenze.append({
            "campo": campo,
            "input": a,
            "candidato": b,
            "similarita": round(sim, 2),
            "penalita": peso,
        })
        if sim >= 0.6:
            simili.append({"campo": campo, "valore": b, "dettaglio": f"simile al {round(sim * 100)}%"})

    for campo in _CODICI_TESTATA:
        a, b = ciclo_input.get(campo), candidato.get(campo)
        if _norm(a) == _norm(b):
            if _norm(a):
                simili.append({"campo": campo, "valore": a})
        else:
            penalita += PENALITA[campo]
            differenze.append({"campo": campo, "input": a, "candidato": b, "penalita": PENALITA[campo]})

    fasi_in = list(ciclo_input.get("fasi") or [])
    fasi_cand = list(candidato.get("fasi") or [])
    pen_fasi, n_uguali = _confronta_fasi(fasi_in, fasi_cand, simili, differenze)
    penalita += pen_fasi

    compatibilita = max(0.0, 100.0 - penalita)
    if fasi_in and fasi_cand and n_uguali == 0:
        compatibilita = min(compatibilita, MAX_SENZA_FASI_COMUNI)

    return {
        "compatibilita": round(compatibilita, 1),
        "simili": simili,
        "differenze": differenze,
    }


# ---------------------------------------------------------------------------
# Accesso DB
# ---------------------------------------------------------------------------
def _key_of(ciclo: Dict[str, Any]) -> Tuple[str, ...]:
    return tuple(str(ciclo.get(f) or "") for f in KEY_FIELDS)


_C37_PREZZI_COLS = (
    "c37_pz_tot_capo", "c37_pz_tot_kg",
    *(f"c37_pz_fascia_{n}" for n in range(1, 10)),
    "c37_pz_fascia_c", "c37_pz_fascia_p",
)


def _chiavi_con_prezzi(cursor, codice_cliente: str) -> Set[Tuple[str, ...]]:
    """Chiavi a 6 campi del cliente con un'offerta C37 che ha almeno un prezzo > 0."""
    prezzi = " OR ".join(f"COALESCE({col}, 0) > 0" for col in _C37_PREZZI_COLS)
    cursor.execute(
        f"""
        SELECT DISTINCT c37_cd_cliente, c37_cd_articolo, c37_cd_ciclo, c37_cd_linea,
               c37_cd_stagione, c37_cd_composizione
        FROM c37_testata_listini
        WHERE c37_cd_cliente = %(c)s AND ({prezzi})
        """,
        {"c": codice_cliente},
    )
    return {tuple(str(v or "") for v in row) for row in cursor.fetchall()}


def _carica_cicli(
    cursor, codice_cliente: str, chiave: Optional[Tuple[str, ...]] = None
) -> List[Dict[str, Any]]:
    """Testate + fasi del cliente (o del solo ciclo `chiave`)."""
    params: Dict[str, Any] = {"c": codice_cliente}
    where_t = "t.codice_cliente = %(c)s"
    where_f = "f.codice_cliente = %(c)s"
    if chiave:
        for i, f in enumerate(KEY_FIELDS):
            params[f"k{i}"] = chiave[i]
        where_t = " AND ".join(f"t.{f} = %(k{i})s" for i, f in enumerate(KEY_FIELDS))
        where_f = " AND ".join(f"f.{f} = %(k{i})s" for i, f in enumerate(KEY_FIELDS))

    cursor.execute(
        f"""
        SELECT t.codice_cliente, t.codice_articolo, t.codice_ciclo, t.codice_linea,
               t.codice_stagione, t.codice_composizione, t.codice_ciclo_cli, t.ds_ciclo,
               t.ds_ciclo_bolle_fat, t.ds_applicazione, t.ds_ricamo, t.ds_stampa, t.note,
               t.codice_reparto, t.codice_gruppo, t.st_record, t.data_ins,
               cl.ragione_sociale, ar.ds_articolo, st.ds_stagione, co.ds_composizione, li.ds_linea
        FROM cicli_testate t
        LEFT JOIN cicli_clienti cl ON cl.codice_cliente = t.codice_cliente
        LEFT JOIN articoli_cliente ar
          ON ar.codice_cliente = t.codice_cliente AND ar.codice_articolo = t.codice_articolo
        LEFT JOIN cicli_stagioni st ON st.codice_stagione = t.codice_stagione
        LEFT JOIN composizioni co ON co.codice_composizione = t.codice_composizione
        LEFT JOIN linee_tintoria li
          ON li.codice_cliente = t.codice_cliente AND li.codice_linea = t.codice_linea
        WHERE {where_t}
        """,
        params,
    )
    cicli: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for row in cursor.fetchall():
        item = dict(zip(_TESTATA_COLS, row))
        if item.get("data_ins") is not None:
            item["data_ins"] = item["data_ins"].isoformat()
        item["fasi"] = []
        cicli[_key_of(item)] = item

    cursor.execute(
        f"""
        SELECT f.codice_cliente, f.codice_articolo, f.codice_ciclo, f.codice_linea,
               f.codice_stagione, f.codice_composizione,
               f.sequenza, f.codice_fase, z.ds_fase, f.codice_macrofase,
               f.codice_unita_mis, f.note
        FROM cicli_fasi f
        LEFT JOIN fasi_lavoro z ON z.codice_fase = f.codice_fase
        WHERE {where_f}
        ORDER BY f.sequenza
        """,
        params,
    )
    for row in cursor.fetchall():
        ciclo = cicli.get(tuple(str(v or "") for v in row[0:6]))
        if ciclo is None:
            continue
        ciclo["fasi"].append({
            "sequenza": row[6],
            "codice_fase": row[7],
            "ds_fase": row[8],
            "codice_macrofase": row[9],
            "codice_unita_mis": row[10],
            "note": row[11],
        })
    return list(cicli.values())


def _risolvi_input(cursor, ciclo: CicloInput, cliente: Optional[str]) -> Dict[str, Any]:
    if not isinstance(ciclo, dict):
        ciclo = dict(zip(KEY_FIELDS, ciclo))
    if "fasi" in ciclo:
        return ciclo
    codice_cliente = ciclo.get("codice_cliente") or cliente
    if not codice_cliente:
        raise ValueError("Ciclo di input senza codice_cliente")
    chiave = _key_of({**ciclo, "codice_cliente": codice_cliente})
    mancanti = [f for f, v in zip(KEY_FIELDS, chiave) if not v]
    if mancanti:
        raise ValueError(f"Chiave ciclo incompleta: {', '.join(mancanti)}")
    trovati = _carica_cicli(cursor, codice_cliente, chiave)
    if not trovati:
        raise LookupError(f"Ciclo non trovato: {chiave}")
    return trovati[0]


def _livello_soglia(livello: int) -> float:
    try:
        lv = int(livello)
    except (TypeError, ValueError):
        lv = 1
    lv = max(min(lv, max(LIVELLI_SOGLIA)), min(LIVELLI_SOGLIA))
    return LIVELLI_SOGLIA[lv]


def _ciclo_summary(ciclo: Dict[str, Any]) -> Dict[str, Any]:
    out = {f: ciclo.get(f) for f in KEY_FIELDS}
    for f in (
        "codice_ciclo_cli", "ds_ciclo", "ds_ciclo_bolle_fat", "ragione_sociale", "ds_articolo",
        "ds_stagione", "ds_composizione", "ds_linea", "codice_reparto", "st_record", "data_ins",
    ):
        out[f] = ciclo.get(f)
    out["fasi"] = [_fase_label(f) for f in ciclo.get("fasi") or []]
    return out


def _filtra_compatibili(
    ciclo_in: Dict[str, Any],
    candidati: Sequence[Dict[str, Any]],
    soglia: float,
    limite: Optional[int],
    chiavi_ammesse: Optional[Set[Tuple[str, ...]]] = None,
) -> List[Dict[str, Any]]:
    key_in = _key_of(ciclo_in)
    risultati: List[Dict[str, Any]] = []
    for cand in candidati:
        key = _key_of(cand)
        if key == key_in or (chiavi_ammesse is not None and key not in chiavi_ammesse):
            continue
        esito = confronta_cicli(ciclo_in, cand)
        if esito["compatibilita"] < soglia:
            continue
        risultati.append({"ciclo": _ciclo_summary(cand), **esito})

    risultati.sort(
        key=lambda r: (r["compatibilita"], r["ciclo"].get("data_ins") or ""),
        reverse=True,
    )
    return risultati[:limite] if limite else risultati


def trova_cicli_compatibili(
    cursor,
    ciclo: CicloInput,
    cliente: Optional[str] = None,
    livello: int = 1,
    *,
    limite: Optional[int] = 100,
    soglia_minima: Optional[float] = None,
    prezzi_presenti: bool = True,
) -> List[Dict[str, Any]]:
    """Cicli del `cliente` compatibili con `ciclo`, ordinati per compatibilità decrescente.

    ciclo: dict con la chiave a 6 campi (caricato da DB), oppure dict già completo con
           chiave "fasi" (lista di dict codice_fase/ds_fase/note/...), oppure tupla in
           ordine KEY_FIELDS.
    cliente: codice cliente su cui cercare; default = cliente del ciclo di input.
    livello: 1 (molto ampio) .. 5 (solo cicli equivalenti), vedi LIVELLI_SOGLIA.
    soglia_minima: sovrascrive la soglia del livello (0..100).
    prezzi_presenti: se True, solo candidati con un'offerta C37 (stessa chiave a 6 campi)
                     che ha almeno un prezzo > 0 (totale capo/kg o fasce).
    """
    ciclo_in = _risolvi_input(cursor, ciclo, cliente)
    codice_cliente = cliente or ciclo_in.get("codice_cliente")
    if not codice_cliente:
        raise ValueError("Cliente non specificato")
    soglia = float(soglia_minima) if soglia_minima is not None else _livello_soglia(livello)
    return _filtra_compatibili(
        ciclo_in,
        _carica_cicli(cursor, codice_cliente),
        soglia,
        limite,
        _chiavi_con_prezzi(cursor, codice_cliente) if prezzi_presenti else None,
    )


def trova_cicli_compatibili_batch(
    cursor,
    cicli: Sequence[CicloInput],
    livello: int = 4,
    *,
    limite: Optional[int] = 50,
    soglia_minima: Optional[float] = None,
    prezzi_presenti: bool = True,
) -> List[Dict[str, Any]]:
    """Come ``trova_cicli_compatibili`` per N cicli, riusando i candidati per cliente.

    Ritorna una lista parallela a ``cicli``. Ogni elemento:

        {"ok": True, "compatibili": [...]}
        oppure
        {"ok": False, "error": "...", "compatibili": []}
    """
    soglia = float(soglia_minima) if soglia_minima is not None else _livello_soglia(livello)
    cache_cliente: Dict[str, List[Dict[str, Any]]] = {}
    cache_prezzi: Dict[str, Set[Tuple[str, ...]]] = {}
    out: List[Dict[str, Any]] = []

    for raw in cicli:
        try:
            if isinstance(raw, dict) and "fasi" in raw:
                ciclo_in = raw
                codice_cliente = str(ciclo_in.get("codice_cliente") or "")
            else:
                if not isinstance(raw, dict):
                    raw = dict(zip(KEY_FIELDS, raw))
                codice_cliente = str(raw.get("codice_cliente") or "")
                if not codice_cliente:
                    raise ValueError("Ciclo di input senza codice_cliente")
                chiave = _key_of({**raw, "codice_cliente": codice_cliente})
                mancanti = [f for f, v in zip(KEY_FIELDS, chiave) if not v]
                if mancanti:
                    raise ValueError(f"Chiave ciclo incompleta: {', '.join(mancanti)}")
                if codice_cliente not in cache_cliente:
                    cache_cliente[codice_cliente] = _carica_cicli(cursor, codice_cliente)
                trovati = [
                    c for c in cache_cliente[codice_cliente] if _key_of(c) == chiave
                ]
                if not trovati:
                    raise LookupError(f"Ciclo non trovato: {chiave}")
                ciclo_in = trovati[0]

            if not codice_cliente:
                codice_cliente = str(ciclo_in.get("codice_cliente") or "")
            if not codice_cliente:
                raise ValueError("Cliente non specificato")
            if codice_cliente not in cache_cliente:
                cache_cliente[codice_cliente] = _carica_cicli(cursor, codice_cliente)
            if prezzi_presenti and codice_cliente not in cache_prezzi:
                cache_prezzi[codice_cliente] = _chiavi_con_prezzi(cursor, codice_cliente)

            compatibili = _filtra_compatibili(
                ciclo_in,
                cache_cliente[codice_cliente],
                soglia,
                limite,
                cache_prezzi.get(codice_cliente) if prezzi_presenti else None,
            )
            out.append({"ok": True, "compatibili": compatibili})
        except (ValueError, LookupError) as exc:
            out.append({"ok": False, "error": str(exc), "compatibili": []})
        except Exception as exc:  # noqa: BLE001 — una riga non deve far fallire il batch
            out.append({"ok": False, "error": str(exc), "compatibili": []})

    return out
