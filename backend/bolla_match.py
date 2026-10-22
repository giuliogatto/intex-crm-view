"""Matching cliente + cicli di lavorazione a partire dall'OCR di una bolla.

Vedi documentation/ocr-analyses.md §7.1 / §7.2 / §2.1.4.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

from cicli_routes import (
    _cicli_search_ready,
    _cicli_table_exists,
    _column_exists,
    _enrich_page,
    _escape_like,
    _load_sinonimi,
)

KEY_FIELDS = (
    "codice_cliente",
    "codice_articolo",
    "codice_ciclo",
    "codice_linea",
    "codice_stagione",
    "codice_composizione",
)

CLIENTE_SOGLIA_AUTO = 0.55
CLIENTE_SOGLIA_MIN = 0.35

# Peso massimo di ciascuna evidenza nel noisy-OR (score = 1 - Π(1 - peso·valore)).
# Tessuto / descrizione alzati: bolle senza "TINTO" (Jacob/Canali) spesso
# portano il segnale utile solo in descrizione_articolo / tessuto OCR.
PESI_EVIDENZE = {
    "codice_ciclo_manoscritto": 0.9,
    "fasi": 0.6,
    "commessa": 0.6,
    "articolo": 0.45,
    "tessuto": 0.4,
    "descrizione": 0.4,
    "colore": 0.25,
    "composizione": 0.15,
}

SOGLIE_EVIDENZE = {
    "fasi": 0.5,
    "descrizione": 0.35,
    "tessuto": 0.35,
    "articolo": 0.5,
    "colore": 0.6,
    "composizione": 0.5,
}

_FASI_MARKERS = (
    "TINT", "TINTO", "LAVAGG", "ENZIM", "SBIANC", "PURGA", "RIENTRO",
    "AMMORB", "RASAPEL", "STONE", "MARMO", "CANDEGG", "STRIAT",
)

_FASI_STOPWORDS = {
    "DA", "DI", "DEL", "DELLA", "CON", "SU", "PER", "NO", "NON", "IL", "LA", "LE", "GLI",
    "EFFETTUARE", "TESS", "TESSUTO", "ART", "ARTICOLO", "PZ", "NR", "KG", "TOT",
}

_LEGAL_FORMS_RE = r"\m(SPA|SRL|SRLS|SAS|SNC|SOC|COOP|[A-Z])\M"


def _norm_text(value: Optional[str]) -> str:
    """Mirror Python di norm_search (UPPER, senza accenti, separatori -> spazio)."""
    if not value:
        return ""
    t = unicodedata.normalize("NFKD", str(value))
    t = "".join(c for c in t if not unicodedata.combining(c)).upper()
    t = re.sub(r"[+/().,;:\-]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _cliente_norm_sql(expr: str) -> str:
    return (
        "btrim(regexp_replace(regexp_replace("
        f"public.norm_search({expr}), '{_LEGAL_FORMS_RE}', ' ', 'g'), '\\s+', ' ', 'g'))"
    )


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------
def match_cliente(cursor, ocr: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
    mittente = (ocr.get("mittente_ragione_sociale") or "").strip()
    codice_su_ddt = (ocr.get("codice_cliente_su_ddt") or "").strip()
    if not mittente:
        return {"selezionato": None, "candidati": [], "livello": "nessuno", "query": None}

    params = {"q": mittente, "cod": codice_su_ddt, "limit": limit}
    n_col = _cliente_norm_sql("ragione_sociale")
    n_q = _cliente_norm_sql("%(q)s")
    cursor.execute(
        f"""
        SELECT codice_cliente, ragione_sociale,
               LEAST(1.0, 0.4 * s_trgm + 0.6 * s_word + bonus_cod) AS score,
               bonus_cod > 0 AS hit_cod
        FROM (
          SELECT codice_cliente, ragione_sociale,
                 similarity(n, q) AS s_trgm,
                 GREATEST(word_similarity(q, n), word_similarity(n, q)) AS s_word,
                 CASE WHEN %(cod)s <> ''
                       AND ltrim(codice_cliente, '0') = ltrim(%(cod)s, '0')
                      THEN 0.15 ELSE 0 END AS bonus_cod
          FROM (
            SELECT codice_cliente, ragione_sociale, {n_col} AS n, {n_q} AS q
            FROM cicli_clienti
            WHERE strpos(upper(ragione_sociale), 'INTEX') = 0
          ) c
        ) s
        ORDER BY score DESC, ragione_sociale
        LIMIT %(limit)s
        """,
        params,
    )
    candidati: List[Dict[str, Any]] = []
    for r in cursor.fetchall():
        evidenze = ["ragione_sociale"]
        if r[3]:
            evidenze.append("codice_cliente_su_ddt")
        candidati.append({
            "codice_cliente": r[0],
            "ragione_sociale": r[1],
            "score": round(float(r[2] or 0), 3),
            "evidenze": evidenze,
        })

    top = candidati[0] if candidati else None
    if top and top["score"] >= CLIENTE_SOGLIA_AUTO:
        livello = "alta"
    elif top and top["score"] >= CLIENTE_SOGLIA_MIN:
        livello = "media"
    else:
        livello = "bassa"
    return {
        "selezionato": top if livello in ("alta", "media") else None,
        "candidati": candidati,
        "livello": livello,
        "query": mittente,
    }


# ---------------------------------------------------------------------------
# Cicli per riga
# ---------------------------------------------------------------------------
def _fasi_keywords(text: Optional[str], limit: int = 12) -> List[str]:
    out: List[str] = []
    for tok in _norm_text(text).split():
        if len(tok) < 3 or tok in _FASI_STOPWORDS:
            continue
        if re.fullmatch(r"T\d{3}[A-Z]?", tok) or re.fullmatch(r"[\d°X]+", tok):
            continue
        if tok not in out:
            out.append(tok)
    return out[:limit]


def _keyword_variants(tok: str, sinonimi: Dict[str, List[str]]) -> List[str]:
    variants = {tok}
    for termini in sinonimi.values():
        norm_termini = [_norm_text(t) for t in termini]
        hit = tok in norm_termini or (
            len(tok) >= 5 and any(len(t) >= 5 and (t.startswith(tok[:5])) for t in norm_termini)
        )
        if hit:
            variants.update(t for t in norm_termini if t)
    return sorted(variants)


def _fasi_coverage_sql(
    keywords: Sequence[str], sinonimi: Dict[str, List[str]], doc_expr: str, params: Dict[str, Any]
) -> str:
    if not keywords:
        return "0::float"
    parts = []
    for ki, kw in enumerate(keywords):
        ors = []
        for vi, v in enumerate(_keyword_variants(kw, sinonimi)):
            key = f"kw_{ki}_{vi}"
            if len(v) <= 3:
                params[key] = rf"\m{re.escape(v)}\M"
                ors.append(f"{doc_expr} ~ %({key})s")
            else:
                params[key] = f"%{_escape_like(v)}%"
                ors.append(f"{doc_expr} LIKE %({key})s ESCAPE '\\'")
        parts.append("(" + " OR ".join(ors) + ")::int")
    return f"(({' + '.join(parts)})::float / {len(keywords)})"


def _commessa_tokens(commessa: Optional[str]) -> List[str]:
    out = []
    for tok in re.findall(r"[A-Z0-9]{4,}", (commessa or "").upper()):
        if not re.search(r"\d", tok) or re.fullmatch(r"(19|20)\d\d", tok):
            continue
        if tok not in out:
            out.append(tok)
    return out


def _looks_like_fasi(text: Optional[str]) -> bool:
    """True se il testo sembra una lavorazione (non solo tessuto/composizione).

    Evita falsi positivi tipo «CAPI/CAMICIA …» (slash in descrizione articolo).
    """
    raw = (text or "").strip()
    if not raw:
        return False
    norm = _norm_text(raw)
    if any(m in norm for m in _FASI_MARKERS):
        return True
    # Catene fasi tipiche: "A+B+C" o "A / B / C" con più segmenti lavorazione.
    if "+" in raw:
        return True
    if raw.count("/") >= 2:
        return True
    return False


def _fasi_source(riga: Dict[str, Any]) -> str:
    """Usa fasi_testo; fallback a descrizione solo se sembra davvero una catena fasi."""
    fasi = (riga.get("fasi_testo") or "").strip()
    if fasi:
        return fasi
    desc = (riga.get("descrizione_articolo") or "").strip()
    return desc if _looks_like_fasi(desc) else ""


def _riga_signals(riga: Dict[str, Any], doc_codes: List[str]) -> Dict[str, Any]:
    codes = list(riga.get("codice_ciclo_manoscritto") or []) or list(doc_codes)
    desc = (riga.get("descrizione_articolo") or "").strip()
    tessuto = (riga.get("tessuto") or "").strip()
    modello = (riga.get("modello") or "").strip()
    return {
        "codes": [c.upper() for c in codes],
        "fasi_text": _fasi_source(riga),
        # descrizione (+ modello) → ar.ds_articolo / ew2_ds_articolo
        "desc": desc or modello,
        # tessuto OCR dedicato → ew2_ds_articolo / ew2_qualita / token
        "tessuto": tessuto,
        "art": (riga.get("codice_articolo_cliente") or "").upper(),
        "modello": modello.upper(),
        "colore": (riga.get("colore") or riga.get("variante") or "").upper(),
        "composizione": riga.get("composizione_testo") or "",
        "commessa_tokens": _commessa_tokens(riga.get("commessa")),
    }


def _query_cicli(cursor, codice_cliente: str, sig: Dict[str, Any], sinonimi, search_ok: bool) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "c": codice_cliente,
        "codes": sig["codes"],
        "desc": sig["desc"],
        "tessuto": sig["tessuto"],
        "art": sig["art"],
        "comp": sig["composizione"],
    }
    if search_ok:
        doc_expr = "COALESCE(cs.search_doc, '')"
        join_search = """
          LEFT JOIN cicli_search cs
            ON cs.codice_cliente = t.codice_cliente
           AND cs.codice_articolo = t.codice_articolo
           AND cs.codice_ciclo = t.codice_ciclo
           AND cs.codice_linea = t.codice_linea
           AND cs.codice_stagione = t.codice_stagione
           AND cs.codice_composizione = t.codice_composizione
        """
    else:
        doc_expr = (
            "public.norm_search(COALESCE(t.ds_ciclo, '') || ' ' || "
            "COALESCE(t.ds_ciclo_bolle_fat, '') || ' ' || COALESCE(t.note, ''))"
        )
        join_search = ""

    coverage = _fasi_coverage_sql(_fasi_keywords(sig["fasi_text"]), sinonimi, doc_expr, params)
    sql = f"""
        SELECT * FROM (
          SELECT
            t.codice_cliente, t.codice_articolo, t.codice_ciclo,
            t.codice_linea, t.codice_stagione, t.codice_composizione,
            (upper(t.codice_ciclo) = ANY(%(codes)s::text[])
             OR upper(COALESCE(t.codice_ciclo_cli, '')) = ANY(%(codes)s::text[])) AS hit_code,
            {coverage} AS s_fasi,
            CASE WHEN %(desc)s = '' THEN 0 ELSE GREATEST(
              word_similarity(public.norm_search(%(desc)s), public.norm_search(COALESCE(ar.ds_articolo, ''))),
              similarity(public.norm_search(%(desc)s), public.norm_search(COALESCE(ar.ds_articolo, ''))),
              word_similarity(public.norm_search(%(desc)s), {doc_expr})
            ) END AS s_desc,
            CASE WHEN %(tessuto)s = '' THEN 0 ELSE GREATEST(
              word_similarity(public.norm_search(%(tessuto)s), public.norm_search(COALESCE(ar.ds_articolo, ''))),
              similarity(public.norm_search(%(tessuto)s), public.norm_search(COALESCE(ar.ds_articolo, '')))
            ) END AS s_tessuto,
            CASE WHEN %(art)s = '' THEN 0 ELSE GREATEST(
              similarity(%(art)s, upper(t.codice_articolo)),
              word_similarity(upper(t.codice_articolo), %(art)s)
            ) END AS s_art,
            CASE WHEN %(comp)s = '' THEN 0 ELSE
              word_similarity(public.norm_search(%(comp)s), public.norm_search(COALESCE(co.ds_composizione, '')))
            END AS s_comp,
            t.data_ins
          FROM cicli_testate t
          LEFT JOIN articoli_cliente ar
            ON ar.codice_cliente = t.codice_cliente
           AND ar.codice_articolo = t.codice_articolo
          LEFT JOIN composizioni co
            ON co.codice_composizione = t.codice_composizione
          {join_search}
          WHERE t.codice_cliente = %(c)s
        ) x
        WHERE hit_code
           OR s_fasi >= {SOGLIE_EVIDENZE['fasi']}
           OR s_desc >= {SOGLIE_EVIDENZE['descrizione']}
           OR s_tessuto >= {SOGLIE_EVIDENZE['tessuto']}
           OR s_art >= {SOGLIE_EVIDENZE['articolo']}
        ORDER BY hit_code DESC,
                 (s_fasi + s_desc + s_tessuto + s_art) DESC,
                 data_ins DESC NULLS LAST
        LIMIT 60
    """
    cursor.execute(sql, params)
    out = []
    for r in cursor.fetchall():
        out.append({
            "key": tuple(r[0:6]),
            "hit_code": bool(r[6]),
            "fasi": float(r[7] or 0),
            "descrizione": float(r[8] or 0),
            "tessuto": float(r[9] or 0),
            "articolo": float(r[10] or 0),
            "composizione": float(r[11] or 0),
        })
    return out


def _query_storico(cursor, codice_cliente: str, sig: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not (
        sig["commessa_tokens"]
        or sig["colore"]
        or sig["art"]
        or sig["modello"]
        or sig["desc"]
        or sig["tessuto"]
    ):
        return []
    params = {
        "c": codice_cliente,
        "comm": sig["commessa_tokens"],
        "col": sig["colore"],
        "art": sig["art"],
        "mod": sig["modello"] or sig["art"],
        "desc": (sig["desc"] or "").upper(),
        "tessuto": (sig["tessuto"] or "").upper(),
        "tessuto_like": f"%{_escape_like(sig['tessuto'] or '')}%",
    }
    # Token exact match solo se la colonna generata esiste.
    if _column_exists(cursor, "ew2_righe_disposizioni", "ew2_tessuto_tokens"):
        token_expr = (
            "CASE WHEN %(tessuto)s <> '' "
            "AND UPPER(%(tessuto)s) = ANY (COALESCE(r.ew2_tessuto_tokens, ARRAY[]::text[])) "
            "THEN 1.0 ELSE 0 END"
        )
    else:
        token_expr = "0"

    sql = f"""
        SELECT cd_cliente, cd_articolo, cd_ciclo, cd_linea, cd_stagione, cd_composizione,
               BOOL_OR(hit_comm), MAX(s_col), MAX(s_art), MAX(s_desc), MAX(s_tessuto),
               COUNT(*), MAX(data_bolla)
        FROM (
          SELECT
            r.ew2_cd_cliente AS cd_cliente,
            r.ew2_cd_articolo_fattura AS cd_articolo,
            r.ew2_cd_ciclo AS cd_ciclo,
            r.ew2_cd_linea AS cd_linea,
            r.ew2_cd_stagione AS cd_stagione,
            r.ew2_cd_composizione AS cd_composizione,
            t.ew1_data_bolla_cli AS data_bolla,
            (cardinality(%(comm)s::text[]) > 0 AND EXISTS (
              SELECT 1 FROM unnest(%(comm)s::text[]) tok
              WHERE strpos(upper(COALESCE(r.ew2_rif_disp_cliente, '') || ' ' ||
                                 COALESCE(t.ew1_rifer_cliente, '')), tok) > 0
            )) AS hit_comm,
            CASE WHEN %(col)s = '' THEN 0 ELSE GREATEST(
              CASE WHEN upper(COALESCE(r.ew2_cd_colore, '')) = %(col)s THEN 1 ELSE 0 END,
              word_similarity(%(col)s, upper(COALESCE(r.ew2_ds_colore, '')))
            ) END AS s_col,
            GREATEST(
              CASE WHEN %(art)s = '' THEN 0
                   ELSE similarity(%(art)s, upper(COALESCE(r.ew2_cd_articolo_fattura, ''))) END,
              CASE WHEN %(mod)s = '' OR COALESCE(r.ew2_modello, '') = '' THEN 0
                   ELSE word_similarity(upper(r.ew2_modello), %(mod)s) END
            ) AS s_art,
            CASE WHEN %(desc)s = '' THEN 0 ELSE GREATEST(
              word_similarity(%(desc)s, upper(COALESCE(r.ew2_ds_articolo, ''))),
              similarity(%(desc)s, upper(COALESCE(r.ew2_ds_articolo, '')))
            ) END AS s_desc,
            CASE WHEN %(tessuto)s = '' THEN 0 ELSE GREATEST(
              word_similarity(%(tessuto)s, upper(COALESCE(r.ew2_ds_articolo, ''))),
              similarity(%(tessuto)s, upper(COALESCE(r.ew2_ds_articolo, ''))),
              word_similarity(%(tessuto)s, upper(COALESCE(r.ew2_qualita, ''))),
              CASE WHEN COALESCE(r.ew2_qualita, '') ILIKE %(tessuto_like)s ESCAPE '\\'
                   THEN 1.0 ELSE 0 END,
              CASE WHEN COALESCE(r.ew2_ds_articolo, '') ILIKE %(tessuto_like)s ESCAPE '\\'
                   THEN 0.95 ELSE 0 END,
              {token_expr}
            ) END AS s_tessuto
          FROM ew2_righe_disposizioni r
          JOIN ew1_testata_disposizioni t
            ON t.ew1_anno_disposizione = r.ew2_anno_disposizione
           AND t.ew1_nr_disposizione = r.ew2_nr_disposizione
          WHERE r.ew2_cd_cliente = %(c)s
        ) x
        WHERE hit_comm
           OR s_col >= {SOGLIE_EVIDENZE['colore']}
           OR s_art >= {SOGLIE_EVIDENZE['articolo']}
           OR s_desc >= {SOGLIE_EVIDENZE['descrizione']}
           OR s_tessuto >= {SOGLIE_EVIDENZE['tessuto']}
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY BOOL_OR(hit_comm) DESC,
                 MAX(s_tessuto) + MAX(s_desc) + MAX(s_art) + MAX(s_col) DESC,
                 MAX(data_bolla) DESC NULLS LAST
        LIMIT 60
    """
    cursor.execute(sql, params)
    out = []
    for r in cursor.fetchall():
        out.append({
            "key": tuple(r[0:6]),
            "commessa": bool(r[6]),
            "colore": float(r[7] or 0),
            "articolo": float(r[8] or 0),
            "descrizione": float(r[9] or 0),
            "tessuto": float(r[10] or 0),
        })
    return out


def _score(ev: Dict[str, float]) -> float:
    residuo = 1.0
    for name, peso in PESI_EVIDENZE.items():
        residuo *= 1.0 - peso * max(0.0, min(1.0, ev.get(name, 0.0)))
    return 1.0 - residuo


def _evidenze_list(ev: Dict[str, float]) -> List[str]:
    out = []
    if ev.get("codice_ciclo_manoscritto"):
        out.append("codice_ciclo_manoscritto")
    for name in (
        "fasi",
        "commessa",
        "articolo",
        "tessuto",
        "descrizione",
        "colore",
        "composizione",
    ):
        soglia = SOGLIE_EVIDENZE.get(name, 0.5)
        if ev.get(name, 0) >= soglia:
            out.append(name)
    return out


def _fetch_cicli_details(cursor, keys: List[Tuple]) -> Dict[Tuple, Dict[str, Any]]:
    if not keys:
        return {}
    params: Dict[str, Any] = {}
    tuples = []
    for i, k in enumerate(keys):
        for j, val in enumerate(k):
            params[f"k{i}_{j}"] = val
        tuples.append("(" + ", ".join(f"%(k{i}_{j})s" for j in range(6)) + ")")
    cursor.execute(
        f"""
        SELECT t.codice_cliente, t.codice_articolo, t.codice_ciclo, t.codice_linea,
               t.codice_stagione, t.codice_composizione,
               t.codice_ciclo_cli, t.ds_ciclo, t.ds_ciclo_bolle_fat, ar.ds_articolo,
               st.ds_stagione, co.ds_composizione, li.ds_linea, t.data_ins
        FROM cicli_testate t
        LEFT JOIN articoli_cliente ar
          ON ar.codice_cliente = t.codice_cliente AND ar.codice_articolo = t.codice_articolo
        LEFT JOIN cicli_stagioni st ON st.codice_stagione = t.codice_stagione
        LEFT JOIN composizioni co ON co.codice_composizione = t.codice_composizione
        LEFT JOIN linee_tintoria li
          ON li.codice_cliente = t.codice_cliente AND li.codice_linea = t.codice_linea
        WHERE (t.codice_cliente, t.codice_articolo, t.codice_ciclo, t.codice_linea,
               t.codice_stagione, t.codice_composizione) IN ({', '.join(tuples)})
        """,
        params,
    )
    out = {}
    for r in cursor.fetchall():
        out[tuple(r[0:6])] = {
            "codice_ciclo_cli": r[6],
            "ds_ciclo": r[7],
            "ds_ciclo_bolle_fat": r[8],
            "ds_articolo": r[9],
            "ds_stagione": r[10],
            "ds_composizione": r[11],
            "ds_linea": r[12],
            "data_ins": r[13].isoformat() if r[13] else None,
            "in_anagrafica": True,
        }
    return out


def match_righe(
    cursor, codice_cliente: str, ocr: Dict[str, Any], max_per_riga: int = 5
) -> Dict[str, Any]:
    search_ok = _cicli_search_ready(cursor)
    storico_ok = _cicli_table_exists(cursor, "ew2_righe_disposizioni") and _cicli_table_exists(
        cursor, "ew1_testata_disposizioni"
    )
    sinonimi = _load_sinonimi(cursor)
    doc_codes = list(ocr.get("codice_ciclo_manoscritto") or [])

    per_riga: List[Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]] = []
    all_keys: List[Tuple] = []
    for riga in ocr.get("righe") or []:
        sig = _riga_signals(riga, doc_codes)
        merged: Dict[Tuple, Dict[str, Any]] = {}

        for hit in _query_cicli(cursor, codice_cliente, sig, sinonimi, search_ok):
            ev = merged.setdefault(hit["key"], {"fonti": set()})
            ev["fonti"].add("manoscritto" if hit["hit_code"] else "cicli")
            ev["codice_ciclo_manoscritto"] = 1.0 if hit["hit_code"] else 0.0
            for name in ("fasi", "descrizione", "tessuto", "articolo", "composizione"):
                ev[name] = max(ev.get(name, 0.0), hit.get(name, 0.0))

        if storico_ok:
            for hit in _query_storico(cursor, codice_cliente, sig):
                ev = merged.setdefault(hit["key"], {"fonti": set()})
                ev["fonti"].add("storico")
                ev["commessa"] = 1.0 if hit["commessa"] else ev.get("commessa", 0.0)
                ev["colore"] = max(ev.get("colore", 0.0), hit["colore"])
                ev["articolo"] = max(ev.get("articolo", 0.0), hit["articolo"])
                ev["descrizione"] = max(ev.get("descrizione", 0.0), hit.get("descrizione", 0.0))
                ev["tessuto"] = max(ev.get("tessuto", 0.0), hit.get("tessuto", 0.0))
            # Codice manoscritto vale anche per candidati emersi solo dallo storico
            for key, ev in merged.items():
                if key[2].upper() in sig["codes"]:
                    ev["codice_ciclo_manoscritto"] = 1.0
                    ev["fonti"].add("manoscritto")

        ranked = sorted(merged.items(), key=lambda kv: _score(kv[1]), reverse=True)[:max_per_riga]
        candidati = []
        for key, ev in ranked:
            item = dict(zip(KEY_FIELDS, key))
            item["score"] = round(_score(ev), 3)
            item["evidenze"] = _evidenze_list(ev)
            item["dettaglio_score"] = {
                k: round(float(ev.get(k, 0.0)), 3) for k in PESI_EVIDENZE
            }
            item["fonte"] = "+".join(sorted(ev["fonti"]))
            candidati.append(item)
            all_keys.append(key)
        per_riga.append((riga, sig, candidati))

    details = _fetch_cicli_details(cursor, list(dict.fromkeys(all_keys)))
    flat = [c for _, _, cands in per_riga for c in cands]
    for c in flat:
        key = tuple(c[f] for f in KEY_FIELDS)
        c.update(details.get(key) or {"in_anagrafica": False})
    _enrich_page(cursor, flat, storico_ok)

    righe_match = []
    for riga, sig, candidati in per_riga:
        candidati.sort(
            key=lambda c: (c["score"], c.get("ultima_bolla") or "", c.get("data_ins") or ""),
            reverse=True,
        )
        righe_match.append({
            "riga": riga.get("riga"),
            "codici_cercati": sig["codes"],
            "candidati_ciclo": candidati,
        })
    return {
        "codice_cliente": codice_cliente,
        "righe_match": righe_match,
        "capabilities": {"cicli_search": search_ok, "storico": storico_ok},
    }
