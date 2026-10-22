"""API ricerca cicli di lavorazione + filtri storico disposizioni."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bottle import request, response

from audit import log_search

# ---------------------------------------------------------------------------
# Fallback sinonimi (usati se tabella ricerca_sinonimi assente / vuota)
# ---------------------------------------------------------------------------
_FALLBACK_SINONIMI: Dict[str, List[str]] = {
    "TINTURA": ["TINTURA", "TINTO", "TI", "T"],
    "REATTIVO": ["REATTIVO", "REATTIVA", "REATT", "TIR"],
    "MANGIAPELO": ["MANGIAPELO", "MPELO", "M PELO"],
    "ENZIMA": ["ENZIMA", "ENZIMI", "ENZ"],
    "POMICE": ["POMICE", "POM"],
    "PERLITE": ["PERLITE", "PERL"],
    "STONE WASH": ["STONE WASH", "STONE", "STW", "SW"],
    "SBOZZIMA": ["SBOZZIMA", "SBOZZ", "SBZ"],
    "CANDEGGIO": ["CANDEGGIO", "BLEACH", "BLEACHED", "SBIANCA"],
    "CARTEGGIO": ["CARTEGGIO", "CART"],
    "LAVAGGIO": ["LAVAGGIO", "LAV", "LAVATO"],
    "TRATTAMENTO": ["TRATTAMENTO", "TRATT", "TR"],
    "PIGMENTO": ["PIGMENTO", "PIG"],
    "SWEET": ["SWEET", "SWE"],
    "ROTTURE": ["ROTTURE", "ROTT"],
    "SPRUZZO": ["SPRUZZO", "SPR"],
    "DEGRADE": ["DEGRADE"],
    "STROPICCIO": ["STROPICCIO", "STROP"],
    "PURGA": ["PURGA"],
    "BAFFI": ["BAFFI"],
    "USED": ["USED", "DIRTY", "OLD"],
    "STRETCH": ["STRETCH", "STR"],
    "MARMO": ["MARMO"],
}


def _escape_like(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _broad_like_pattern(value: Optional[str]) -> Optional[str]:
    """Match allargato: 'tinto stretch' -> %tinto%stretch%."""
    if not value or not str(value).strip():
        return None
    parts = [_escape_like(p) for p in re.split(r"\s+", str(value).strip()) if p]
    if not parts:
        return None
    return "%" + "%".join(parts) + "%"


def _norm_token(value: str) -> str:
    t = value.upper().strip()
    t = re.sub(r"([0-9])\?", r"\1°", t)
    t = re.sub(r"[+/().,;:\-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    from datetime import datetime

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_pagination(default_limit=50, max_limit=200):
    try:
        page = int(request.query.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(request.query.get("limit", default_limit))
    except (TypeError, ValueError):
        limit = default_limit
    page = max(page, 1)
    limit = max(min(limit, max_limit), 1)
    offset = (page - 1) * limit
    return page, limit, offset


def _paginated(items, total, page, limit, extra=None):
    pages = max((total + limit - 1) // limit, 1) if total else 1
    result = {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "data": items,
    }
    if extra:
        result.update(extra)
    return result


def _query_getlist(name: str) -> List[str]:
    """Supporta ?fasi=a&fasi=b e ?fasi=a,b."""
    raw = request.query.getall(name) if hasattr(request.query, "getall") else []
    if not raw:
        single = (request.query.get(name) or "").strip()
        raw = [single] if single else []
    out: List[str] = []
    for item in raw:
        for part in re.split(r"[,|]", item):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


# Dizionario UI reparto → codice Z09_CD_REPARTO_STAT (cicli_testate.codice_reparto).
# Accetta anche i codici grezzi. "TUTTI" / vuoto = nessun filtro.
_REPARTO_TO_CODICE: Dict[str, str] = {
    "TINTO": "TINTO",
    "DENIM": "DENIM",
    "INTEX": "INTEX",
    "PROTOTIPI": "PROTOT",
    "PROTOT": "PROTOT",
    "EFFETTI SPECIALI": "EFFSPE",
    "EFFETTI SP": "EFFSPE",
    "EFFSPE": "EFFSPE",
}


def _normalize_reparto(raw: Optional[str]) -> Optional[str]:
    """Ritorna il codice_reparto DB, o None se Tutti / non valido."""
    if not raw:
        return None
    key = re.sub(r"\s+", " ", str(raw).strip().upper())
    if not key or key in ("TUTTI", "ALL", "*"):
        return None
    return _REPARTO_TO_CODICE.get(key)


def _cicli_filters() -> Dict[str, Any]:
    fasi = _query_getlist("fasi")
    descrizione = (request.query.get("descrizione") or "").strip() or None
    reparto_raw = (
        request.query.get("reparto")
        or request.query.get("codice_reparto")
        or ""
    )
    # Se c'è descrizione letterale e non è già in fasi, resta filtro letterale
    return {
        "codice_cliente": (request.query.get("codice_cliente") or "").strip() or None,
        "stagione": (request.query.get("stagione") or "").strip() or None,
        "articolo": (request.query.get("articolo") or "").strip() or None,
        "composizione": (request.query.get("composizione") or "").strip() or None,
        "descrizione": descrizione,
        "codice_ciclo": (request.query.get("codice_ciclo") or "").strip() or None,
        "reparto": _normalize_reparto(reparto_raw),
        "fasi": fasi,
        "fasi_mode": ((request.query.get("fasi_mode") or "all").strip().lower() or "all"),
        "fasi_note_storico": (request.query.get("fasi_note_storico") or "0").strip() in ("1", "true", "True"),
        "colore": (request.query.get("colore") or "").strip() or None,
        "tessuto": (request.query.get("tessuto") or "").strip() or None,
        "commessa": (request.query.get("commessa") or "").strip() or None,
        "modello": (request.query.get("modello") or "").strip() or None,
        "articolo_fiscale": (request.query.get("articolo_fiscale") or "").strip() or None,
        "data_bolla_da": _parse_date(request.query.get("data_bolla_da")),
        "data_bolla_a": _parse_date(request.query.get("data_bolla_a")),
        "vista": ((request.query.get("vista") or "cicli").strip().lower() or "cicli"),
    }


def _has_storico_filters(filters: Dict[str, Any]) -> bool:
    note_storico = bool(filters.get("fasi_note_storico") and filters.get("fasi"))
    return bool(
        filters.get("colore")
        or filters.get("tessuto")
        or filters.get("commessa")
        or filters.get("modello")
        or filters.get("articolo_fiscale")
        or filters.get("data_bolla_da")
        or filters.get("data_bolla_a")
        or note_storico
    )


def _load_sinonimi(cursor) -> Dict[str, List[str]]:
    try:
        cursor.execute("SELECT gruppo, termine FROM ricerca_sinonimi")
        rows = cursor.fetchall()
        if not rows:
            return {k: list(v) for k, v in _FALLBACK_SINONIMI.items()}
        out: Dict[str, List[str]] = {}
        for gruppo, termine in rows:
            g = (gruppo or "").upper().strip()
            t = (termine or "").upper().strip()
            if not g or not t:
                continue
            out.setdefault(g, []).append(t)
        return out or {k: list(v) for k, v in _FALLBACK_SINONIMI.items()}
    except Exception:
        cursor.connection.rollback()
        return {k: list(v) for k, v in _FALLBACK_SINONIMI.items()}


# Sotto questa lunghezza il match per contenimento (term in keyword) è troppo
# aggressivo: es. "T" ∈ "AMMORBIDENTE" agganciava tutto il gruppo TINTURA.
_MIN_SINONIMO_CONTAINMENT_LEN = 4


def _expand_fasi_keywords(
    keywords: Sequence[str], sinonimi: Dict[str, List[str]]
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """Espande ogni keyword in varianti (sinonimi + normalizzazione)."""
    expanded_meta: Dict[str, List[str]] = {}
    groups: List[Dict[str, Any]] = []

    # indice inverso termine -> gruppo
    term_to_group: Dict[str, str] = {}
    for gruppo, termini in sinonimi.items():
        for t in termini:
            term_to_group[t.upper()] = gruppo

    for kw in keywords:
        raw = kw.strip()
        if not raw:
            continue
        norm = _norm_token(raw)
        variants = {raw.upper(), norm}
        # match gruppo: uguaglianza sempre; contenimento solo per termini lunghi
        matched_groups = set()
        for term, gruppo in term_to_group.items():
            if norm == term:
                matched_groups.add(gruppo)
            elif (
                len(term) >= _MIN_SINONIMO_CONTAINMENT_LEN
                and term in norm
            ) or (
                len(norm) >= _MIN_SINONIMO_CONTAINMENT_LEN
                and norm in term
            ):
                matched_groups.add(gruppo)
        for gruppo in matched_groups:
            for t in sinonimi.get(gruppo, []):
                variants.add(t)
                variants.add(_norm_token(t))
        # parti multi-parola: solo lookup esatto sul token (già len >= 2)
        for part in norm.split():
            if len(part) >= 2:
                variants.add(part)
                g = term_to_group.get(part)
                if g:
                    for t in sinonimi.get(g, []):
                        variants.add(t)

        clean = sorted({v for v in variants if v and len(v) >= 1})
        expanded_meta[raw] = clean
        groups.append({"keyword": raw, "variants": clean})

    return groups, expanded_meta


def _fasi_match_sql(
    groups: List[Dict[str, Any]],
    mode: str,
    params: Dict[str, Any],
    alias: str = "cs",
) -> Optional[str]:
    """Costruisce condizione SQL su cicli_search.search_doc."""
    if not groups:
        return None

    group_clauses = []
    for gi, group in enumerate(groups):
        variant_clauses = []
        for vi, variant in enumerate(group["variants"]):
            key = f"fase_{gi}_{vi}"
            v = variant.strip()
            if not v:
                continue
            if len(v) <= 3:
                # confini di parola per abbreviazioni corte
                params[key] = rf"\m{_escape_like(v)}\M"
                variant_clauses.append(
                    f"{alias}.search_doc ~* %({key})s"
                )
            else:
                params[key] = f"%{_escape_like(v)}%"
                # ILIKE + word_similarity (soglia 0.45 se pg_trgm disponibile)
                params[f"{key}_sim"] = v
                variant_clauses.append(
                    f"("
                    f"{alias}.search_doc ILIKE %({key})s ESCAPE '\\'"
                    f" OR word_similarity(%({key}_sim)s, COALESCE({alias}.search_doc, '')) > 0.45"
                    f")"
                )
        if variant_clauses:
            group_clauses.append("(" + " OR ".join(variant_clauses) + ")")

    if not group_clauses:
        return None
    joiner = " OR " if mode == "any" else " AND "
    return joiner.join(group_clauses)


def _storico_where(
    filters: Dict[str, Any],
    params: Dict[str, Any],
    note_variants: Optional[List[str]] = None,
    ew2_alias: str = "r",
    ew1_alias: str = "t",
) -> str:
    """Condizioni su alias ew2 + ew1. Tutti AND sulla stessa riga.

    Usa alias espliciti (niente replace su 'r.'/'t.') per non corrompere
    placeholder tipo %(articolo_fiscale)s o nomi colonna.
    """
    r = ew2_alias
    t = ew1_alias
    clauses = ["1=1"]

    colore = filters.get("colore")
    if colore:
        params["colore"] = colore
        params["colore_like"] = f"%{_escape_like(colore)}%"
        params["colore_prefix"] = f"{_escape_like(colore)}%"
        clauses.append(
            "("
            f"{r}.ew2_cd_colore ILIKE %(colore_prefix)s ESCAPE '\\'"
            f" OR {r}.ew2_ds_colore ILIKE %(colore_like)s ESCAPE '\\'"
            f" OR word_similarity(%(colore)s, COALESCE({r}.ew2_ds_colore, '')) > 0.5"
            ")"
        )

    commessa = filters.get("commessa")
    if commessa:
        params["commessa"] = commessa.upper().strip()
        params["commessa_like"] = f"%{_escape_like(commessa)}%"
        clauses.append(
            "("
            f"UPPER(%(commessa)s) = ANY (COALESCE({r}.ew2_rif_tokens, ARRAY[]::text[]))"
            f" OR {r}.ew2_rif_disp_cliente ILIKE %(commessa_like)s ESCAPE '\\'"
            f" OR COALESCE({t}.ew1_rifer_cliente, '') ILIKE %(commessa_like)s ESCAPE '\\'"
            ")"
        )

    modello = filters.get("modello")
    if modello:
        params["modello"] = modello
        params["modello_like"] = f"%{_escape_like(modello)}%"
        clauses.append(
            "("
            f"{r}.ew2_modello ILIKE %(modello_like)s ESCAPE '\\'"
            f" OR {r}.ew2_ds_articolo ILIKE %(modello_like)s ESCAPE '\\'"
            f" OR word_similarity(%(modello)s, COALESCE({r}.ew2_modello, '')) > 0.5"
            ")"
        )

    tessuto = filters.get("tessuto")
    if tessuto:
        # Operativamente il "tessuto" è in ew2_ds_articolo (descrizione/articolo);
        # ew2_qualita + token restano per codici qualità (es. S3651).
        params["tessuto"] = tessuto.strip()
        params["tessuto_upper"] = tessuto.upper().strip()
        params["tessuto_like"] = f"%{_escape_like(tessuto)}%"
        clauses.append(
            "("
            f"COALESCE({r}.ew2_ds_articolo, '') ILIKE %(tessuto_like)s ESCAPE '\\'"
            f" OR word_similarity(%(tessuto)s, COALESCE({r}.ew2_ds_articolo, '')) > 0.5"
            f" OR COALESCE({r}.ew2_qualita, '') ILIKE %(tessuto_like)s ESCAPE '\\'"
            f" OR UPPER(%(tessuto_upper)s) = ANY (COALESCE({r}.ew2_tessuto_tokens, ARRAY[]::text[]))"
            f" OR COALESCE({r}.ew2_note, '') ILIKE %(tessuto_like)s ESCAPE '\\'"
            ")"
        )

    art_fisc = filters.get("articolo_fiscale")
    if art_fisc:
        # Case-insensitive + trim: i codici Oracle arrivano spesso upper e con padding
        params["articolo_fiscale"] = art_fisc.strip()
        params["articolo_fiscale_like"] = f"%{_escape_like(art_fisc.strip())}%"
        clauses.append(
            "("
            f"btrim(COALESCE({r}.ew2_cd_articolo_fiscale, '')) ILIKE %(articolo_fiscale)s ESCAPE '\\'"
            f" OR btrim(COALESCE({r}.ew2_cd_articolo_fiscale, '')) ILIKE %(articolo_fiscale_like)s ESCAPE '\\'"
            ")"
        )

    if filters.get("data_bolla_da"):
        params["data_bolla_da"] = filters["data_bolla_da"]
        clauses.append(f"{t}.ew1_data_bolla_cli >= %(data_bolla_da)s")
    if filters.get("data_bolla_a"):
        params["data_bolla_a"] = filters["data_bolla_a"]
        clauses.append(f"{t}.ew1_data_bolla_cli <= %(data_bolla_a)s")

    if filters.get("fasi_note_storico") and note_variants:
        note_parts = []
        for i, v in enumerate(note_variants):
            if len(v) < 2:
                continue
            key = f"note_storico_{i}"
            params[key] = f"%{_escape_like(v)}%"
            note_parts.append(
                f"(COALESCE({r}.ew2_note, '') ILIKE %({key})s ESCAPE '\\'"
                f" OR COALESCE({r}.ew2_note_ricetta, '') ILIKE %({key})s ESCAPE '\\')"
            )
        if note_parts:
            clauses.append("(" + " OR ".join(note_parts) + ")")

    return " AND ".join(clauses)


def _cicli_base_from(filters: Dict[str, Any], params: Dict[str, Any], join_search: bool) -> str:
    query = """
        FROM cicli_testate t
        LEFT JOIN cicli_clienti cl
          ON cl.codice_cliente = t.codice_cliente
        LEFT JOIN cicli_stagioni st
          ON st.codice_stagione = t.codice_stagione
        LEFT JOIN composizioni co
          ON co.codice_composizione = t.codice_composizione
        LEFT JOIN articoli_cliente ar
          ON ar.codice_cliente = t.codice_cliente
         AND ar.codice_articolo = t.codice_articolo
        LEFT JOIN linee_tintoria li
          ON li.codice_cliente = t.codice_cliente
         AND li.codice_linea = t.codice_linea
    """
    if join_search:
        query += """
        LEFT JOIN cicli_search cs
          ON cs.codice_cliente = t.codice_cliente
         AND cs.codice_articolo = t.codice_articolo
         AND cs.codice_ciclo = t.codice_ciclo
         AND cs.codice_linea = t.codice_linea
         AND cs.codice_stagione = t.codice_stagione
         AND cs.codice_composizione = t.codice_composizione
        """
    query += " WHERE 1=1"

    if filters.get("codice_cliente"):
        query += " AND t.codice_cliente = %(codice_cliente)s"
        params["codice_cliente"] = filters["codice_cliente"]

    if filters.get("stagione"):
        query += " AND t.codice_stagione = %(stagione)s"
        params["stagione"] = filters["stagione"]

    if filters.get("reparto"):
        query += " AND UPPER(TRIM(COALESCE(t.codice_reparto, ''))) = %(reparto)s"
        params["reparto"] = filters["reparto"]

    codice_ciclo_pat = _broad_like_pattern(filters.get("codice_ciclo"))
    if codice_ciclo_pat:
        query += """
          AND (
            t.codice_ciclo ILIKE %(codice_ciclo_pat)s ESCAPE '\\'
            OR COALESCE(t.codice_ciclo_cli, '') ILIKE %(codice_ciclo_pat)s ESCAPE '\\'
          )
        """
        params["codice_ciclo_pat"] = codice_ciclo_pat

    articolo_pat = _broad_like_pattern(filters.get("articolo"))
    if articolo_pat:
        query += """
          AND (
            COALESCE(ar.ds_articolo, '') ILIKE %(articolo_pat)s ESCAPE '\\'
            OR t.codice_articolo ILIKE %(articolo_pat)s ESCAPE '\\'
          )
        """
        params["articolo_pat"] = articolo_pat

    composizione_pat = _broad_like_pattern(filters.get("composizione"))
    if composizione_pat:
        query += """
          AND (
            COALESCE(co.ds_composizione, '') ILIKE %(composizione_pat)s ESCAPE '\\'
            OR t.codice_composizione ILIKE %(composizione_pat)s ESCAPE '\\'
          )
        """
        params["composizione_pat"] = composizione_pat

    descrizione_pat = _broad_like_pattern(filters.get("descrizione"))
    if descrizione_pat:
        query += """
          AND (
            COALESCE(t.ds_ciclo, '') ILIKE %(descrizione_pat)s ESCAPE '\\'
            OR COALESCE(t.ds_ciclo_bolle_fat, '') ILIKE %(descrizione_pat)s ESCAPE '\\'
          )
        """
        params["descrizione_pat"] = descrizione_pat

    return query


def _cicli_table_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %(name)s",
        {"name": name},
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %(table)s AND column_name = %(column)s
        """,
        {"table": table, "column": column},
    )
    return cursor.fetchone() is not None


def _looks_like_code(query: str) -> bool:
    """Preferisci match su codici se la query è prevalentemente numerica/codice-like."""
    s = (query or "").strip()
    if not s:
        return False
    letters = sum(1 for c in s if c.isalpha())
    digits = sum(1 for c in s if c.isdigit())
    if digits > 0 and digits >= letters:
        return True
    if " " not in s and len(s) <= 12 and digits > 0:
        return True
    return False


def _suggest_limit(raw: Optional[str], default: int = 30, max_limit: int = 50) -> int:
    try:
        limit = int(raw or default)
    except (TypeError, ValueError):
        limit = default
    return max(1, min(limit, max_limit))


def _enrich_page(cursor, items: List[Dict[str, Any]], storico_available: bool) -> None:
    if not items or not storico_available:
        for it in items:
            it.setdefault("ultima_bolla", None)
            it.setdefault("n_righe_storico", 0)
            it.setdefault("commesse", [])
            it.setdefault("colori", [])
            it.setdefault("modelli", [])
        return

    # Costruisce VALUES per le chiavi della pagina
    tuples = []
    params: Dict[str, Any] = {}
    for i, it in enumerate(items):
        params[f"c{i}"] = it["codice_cliente"]
        params[f"a{i}"] = it["codice_articolo"]
        params[f"cic{i}"] = it["codice_ciclo"]
        params[f"l{i}"] = it["codice_linea"]
        params[f"s{i}"] = it["codice_stagione"]
        params[f"co{i}"] = it["codice_composizione"]
        tuples.append(
            f"(%(c{i})s, %(a{i})s, %(cic{i})s, %(l{i})s, %(s{i})s, %(co{i})s)"
        )

    sql = f"""
        SELECT
          r.ew2_cd_cliente,
          r.ew2_cd_articolo_fattura,
          r.ew2_cd_ciclo,
          r.ew2_cd_linea,
          r.ew2_cd_stagione,
          r.ew2_cd_composizione,
          MAX(t.ew1_data_bolla_cli) AS ultima_bolla,
          COUNT(*) AS n_righe,
          ARRAY_AGG(DISTINCT NULLIF(btrim(r.ew2_rif_disp_cliente), '') )
            FILTER (WHERE NULLIF(btrim(r.ew2_rif_disp_cliente), '') IS NOT NULL) AS commesse,
          ARRAY_AGG(DISTINCT NULLIF(btrim(r.ew2_ds_colore), '') )
            FILTER (WHERE NULLIF(btrim(r.ew2_ds_colore), '') IS NOT NULL) AS colori,
          ARRAY_AGG(DISTINCT NULLIF(btrim(r.ew2_modello), '') )
            FILTER (WHERE NULLIF(btrim(r.ew2_modello), '') IS NOT NULL) AS modelli
        FROM ew2_righe_disposizioni r
        JOIN ew1_testata_disposizioni t
          ON t.ew1_anno_disposizione = r.ew2_anno_disposizione
         AND t.ew1_nr_disposizione = r.ew2_nr_disposizione
        WHERE (r.ew2_cd_cliente, r.ew2_cd_articolo_fattura, r.ew2_cd_ciclo,
               r.ew2_cd_linea, r.ew2_cd_stagione, r.ew2_cd_composizione)
          IN ({', '.join(tuples)})
        GROUP BY 1, 2, 3, 4, 5, 6
    """
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    except Exception:
        cursor.connection.rollback()
        for it in items:
            it.setdefault("ultima_bolla", None)
            it.setdefault("n_righe_storico", 0)
            it.setdefault("commesse", [])
            it.setdefault("colori", [])
            it.setdefault("modelli", [])
        return

    by_key = {}
    for r in rows:
        key = (r[0], r[1], r[2], r[3], r[4], r[5])
        by_key[key] = {
            "ultima_bolla": r[6].isoformat() if r[6] else None,
            "n_righe_storico": int(r[7] or 0),
            "commesse": [c for c in (r[8] or []) if c][:5],
            "colori": [c for c in (r[9] or []) if c][:5],
            "modelli": [c for c in (r[10] or []) if c][:5],
        }

    for it in items:
        key = (
            it["codice_cliente"],
            it["codice_articolo"],
            it["codice_ciclo"],
            it["codice_linea"],
            it["codice_stagione"],
            it["codice_composizione"],
        )
        enrich = by_key.get(key) or {
            "ultima_bolla": None,
            "n_righe_storico": 0,
            "commesse": [],
            "colori": [],
            "modelli": [],
        }
        it.update(enrich)


def _storico_range(cursor) -> Optional[Dict[str, Optional[str]]]:
    """MIN/MAX data bolla storico, escludendo date anomale del gestionale (es. anno 2202)."""
    try:
        cursor.execute(
            """
            SELECT MIN(ew1_data_bolla_cli), MAX(ew1_data_bolla_cli)
            FROM ew1_testata_disposizioni
            WHERE ew1_data_bolla_cli BETWEEN '1990-01-01'
                  AND (CURRENT_DATE + INTERVAL '30 days')
            """
        )
        row = cursor.fetchone()
        if not row or (row[0] is None and row[1] is None):
            return None
        return {
            "da": row[0].isoformat() if row[0] else None,
            "a": row[1].isoformat() if row[1] else None,
        }
    except Exception:
        cursor.connection.rollback()
        return None


def _cicli_search_ready(cursor) -> bool:
    """True se cicli_search esiste e ha almeno una riga (refresh via POST /api/cicli/refresh-search)."""
    if not _cicli_table_exists(cursor, "cicli_search"):
        return False
    try:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM cicli_search LIMIT 1)")
        return bool(cursor.fetchone()[0])
    except Exception:
        cursor.connection.rollback()
        return False


def register_cicli_routes(app, db_pool, parse_pagination=None, paginated_list_response=None):
    """Registra /api/cicli* sull'app Bottle."""

    @app.route("/api/cicli/clienti", method="GET")
    def get_cicli_clienti():
        try:
            conn = db_pool.get_conn()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT codice_cliente, ragione_sociale
                FROM cicli_clienti
                ORDER BY ragione_sociale
                """
            )
            rows = cursor.fetchall()
            cursor.close()
            db_pool.release_conn(conn)
            data = [{"codice": r[0], "ragione_sociale": r[1]} for r in rows]
            return {"total": len(data), "data": data}
        except Exception as e:
            response.status = 500
            return {"error": str(e)}

    @app.route("/api/cicli/stagioni", method="GET")
    def get_cicli_stagioni():
        try:
            conn = db_pool.get_conn()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT codice_stagione, ds_stagione
                FROM cicli_stagioni
                ORDER BY codice_stagione DESC
                """
            )
            rows = cursor.fetchall()
            cursor.close()
            db_pool.release_conn(conn)
            data = [{"codice": r[0], "descrizione": r[1] or r[0]} for r in rows]
            return {"total": len(data), "data": data}
        except Exception as e:
            response.status = 500
            return {"error": str(e)}

    @app.route("/api/cicli/suggest/<field>", method="GET")
    def get_cicli_suggest(field):
        """Autocomplete case-insensitive con testo libero (valore = stringa digitata/selezionata).

        Campi: codice_ciclo, articolo, colore, modello, tessuto, commessa,
        articolo_fiscale, fasi.
        Ranking: prefisso prima di contains; per query codice-like priorità ai codici.
        """
        field = (field or "").strip().lower().replace("-", "_")
        allowed = {
            "codice_ciclo",
            "articolo",
            "colore",
            "modello",
            "tessuto",
            "commessa",
            "articolo_fiscale",
            "fasi",
        }
        if field not in allowed:
            response.status = 400
            return {"error": f"Campo suggest non supportato: {field}"}

        q = (request.query.get("q") or "").strip()
        min_chars = 3 if field == "commessa" else (1 if field == "articolo_fiscale" else 2)
        if len(q) < min_chars:
            return {"total": 0, "data": [], "min_chars": min_chars}

        limit = _suggest_limit(request.query.get("limit"))
        codice_cliente = (request.query.get("codice_cliente") or "").strip() or None
        code_like = _looks_like_code(q)
        escaped = _escape_like(q)
        params: Dict[str, Any] = {
            "prefix": f"{escaped}%",
            "contains": f"%{escaped}%",
            "limit": limit,
        }

        conn = None
        cursor = None
        try:
            conn = db_pool.get_conn()
            cursor = conn.cursor()
            data: List[Dict[str, Any]] = []

            if field == "fasi":
                # Dizionario sinonimi (piccolo): termine + gruppo, case-insensitive
                sinonimi = _load_sinonimi(cursor)
                q_upper = q.upper()
                exclude = {
                    x.strip().upper()
                    for x in _query_getlist("exclude")
                    if x and x.strip()
                }
                scored: List[Tuple[int, str, str, Optional[str]]] = []
                seen = set()
                for gruppo, termini in sinonimi.items():
                    g = (gruppo or "").strip()
                    if not g:
                        continue
                    candidates = [(g, None)] + [
                        (t.strip(), g) for t in termini if t and t.strip()
                    ]
                    for value, secondary in candidates:
                        key = value.upper()
                        if key in seen or key in exclude:
                            continue
                        if q_upper not in key:
                            continue
                        seen.add(key)
                        rank = 0 if key.startswith(q_upper) else 1
                        # Se value == gruppo, niente secondary ridondante
                        sec = None if not secondary or secondary.upper() == key else secondary
                        scored.append((rank, value, value, sec))
                scored.sort(key=lambda row: (row[0], row[1].upper()))
                data = [
                    {"value": v, "label": label, "secondary": sec}
                    for _, v, label, sec in scored[:limit]
                ]

            elif field == "codice_ciclo":
                if codice_cliente:
                    params["codice_cliente"] = codice_cliente
                cli_filter = "AND t.codice_cliente = %(codice_cliente)s" if codice_cliente else ""
                # Unisce codice ciclo e codice ciclo cliente; prefisso prima
                cursor.execute(
                    f"""
                    SELECT value, label, secondary FROM (
                      SELECT DISTINCT
                        t.codice_ciclo AS value,
                        t.codice_ciclo AS label,
                        NULLIF(btrim(t.codice_ciclo_cli), '') AS secondary,
                        CASE
                          WHEN t.codice_ciclo ILIKE %(prefix)s ESCAPE '\\' THEN 0
                          WHEN COALESCE(t.codice_ciclo_cli, '') ILIKE %(prefix)s ESCAPE '\\' THEN 1
                          ELSE 2
                        END AS rank_pref,
                        t.codice_ciclo AS sort_key
                      FROM cicli_testate t
                      WHERE (
                        t.codice_ciclo ILIKE %(contains)s ESCAPE '\\'
                        OR COALESCE(t.codice_ciclo_cli, '') ILIKE %(contains)s ESCAPE '\\'
                      )
                      {cli_filter}
                    ) x
                    ORDER BY rank_pref, sort_key
                    LIMIT %(limit)s
                    """,
                    params,
                )
                data = [
                    {"value": r[0], "label": r[1], "secondary": r[2]}
                    for r in cursor.fetchall()
                    if r[0]
                ]

            elif field == "articolo":
                if codice_cliente:
                    params["codice_cliente"] = codice_cliente
                cli_filter = "AND a.codice_cliente = %(codice_cliente)s" if codice_cliente else ""
                # Query codice-like → codice prima; altrimenti descrizione prima
                order_sql = (
                    "rank_code, rank_pref, sort_key"
                    if code_like
                    else "rank_desc, rank_pref, sort_key"
                )
                cursor.execute(
                    f"""
                    SELECT value, label, secondary FROM (
                      SELECT DISTINCT
                        a.codice_articolo AS value,
                        COALESCE(NULLIF(btrim(a.ds_articolo), ''), a.codice_articolo) AS label,
                        a.codice_articolo AS secondary,
                        CASE WHEN a.codice_articolo ILIKE %(prefix)s ESCAPE '\\' THEN 0
                             WHEN a.codice_articolo ILIKE %(contains)s ESCAPE '\\' THEN 1
                             ELSE 2 END AS rank_code,
                        CASE WHEN COALESCE(a.ds_articolo, '') ILIKE %(prefix)s ESCAPE '\\' THEN 0
                             WHEN COALESCE(a.ds_articolo, '') ILIKE %(contains)s ESCAPE '\\' THEN 1
                             ELSE 2 END AS rank_desc,
                        CASE WHEN a.codice_articolo ILIKE %(prefix)s ESCAPE '\\'
                               OR COALESCE(a.ds_articolo, '') ILIKE %(prefix)s ESCAPE '\\'
                             THEN 0 ELSE 1 END AS rank_pref,
                        COALESCE(a.ds_articolo, a.codice_articolo) AS sort_key
                      FROM articoli_cliente a
                      WHERE (
                        a.codice_articolo ILIKE %(contains)s ESCAPE '\\'
                        OR COALESCE(a.ds_articolo, '') ILIKE %(contains)s ESCAPE '\\'
                      )
                      {cli_filter}
                    ) x
                    ORDER BY {order_sql}
                    LIMIT %(limit)s
                    """,
                    params,
                )
                rows = cursor.fetchall()
                data = []
                for r in rows:
                    if not r[0]:
                        continue
                    # Se la query sembra descrizione, il value inviabile può essere la label
                    value = r[0] if code_like else (r[1] or r[0])
                    data.append({"value": value, "label": r[1], "secondary": r[2]})

            elif field == "articolo_fiscale":
                if not _cicli_table_exists(cursor, "ew2_righe_disposizioni"):
                    return {"total": 0, "data": [], "storico_disponibile": False}
                cursor.execute(
                    """
                    SELECT value, label, secondary FROM (
                      SELECT DISTINCT
                        btrim(r.ew2_cd_articolo_fiscale) AS value,
                        btrim(r.ew2_cd_articolo_fiscale) AS label,
                        NULL::text AS secondary,
                        CASE
                          WHEN btrim(r.ew2_cd_articolo_fiscale) ILIKE %(prefix)s ESCAPE '\\' THEN 0
                          ELSE 1
                        END AS rank_pref,
                        btrim(r.ew2_cd_articolo_fiscale) AS sort_key
                      FROM ew2_righe_disposizioni r
                      WHERE NULLIF(btrim(r.ew2_cd_articolo_fiscale), '') IS NOT NULL
                        AND btrim(r.ew2_cd_articolo_fiscale) ILIKE %(contains)s ESCAPE '\\'
                    ) x
                    ORDER BY rank_pref, sort_key
                    LIMIT %(limit)s
                    """,
                    params,
                )
                data = [
                    {"value": r[0], "label": r[1], "secondary": r[2]}
                    for r in cursor.fetchall()
                    if r[0]
                ]

            elif field in ("colore", "modello", "tessuto", "commessa"):
                if not _cicli_table_exists(cursor, "ew2_righe_disposizioni"):
                    return {"total": 0, "data": [], "storico_disponibile": False}

                if field == "colore":
                    order_sql = (
                        "rank_code, rank_pref, sort_key"
                        if code_like
                        else "rank_desc, rank_pref, sort_key"
                    )
                    cursor.execute(
                        f"""
                        SELECT cd_colore, ds_colore FROM (
                          SELECT DISTINCT
                            NULLIF(btrim(r.ew2_cd_colore), '') AS cd_colore,
                            NULLIF(btrim(r.ew2_ds_colore), '') AS ds_colore,
                            CASE WHEN COALESCE(r.ew2_cd_colore, '') ILIKE %(prefix)s ESCAPE '\\' THEN 0
                                 WHEN COALESCE(r.ew2_cd_colore, '') ILIKE %(contains)s ESCAPE '\\' THEN 1
                                 ELSE 2 END AS rank_code,
                            CASE WHEN COALESCE(r.ew2_ds_colore, '') ILIKE %(prefix)s ESCAPE '\\' THEN 0
                                 WHEN COALESCE(r.ew2_ds_colore, '') ILIKE %(contains)s ESCAPE '\\' THEN 1
                                 ELSE 2 END AS rank_desc,
                            CASE WHEN COALESCE(r.ew2_cd_colore, '') ILIKE %(prefix)s ESCAPE '\\'
                                   OR COALESCE(r.ew2_ds_colore, '') ILIKE %(prefix)s ESCAPE '\\'
                                 THEN 0 ELSE 1 END AS rank_pref,
                            COALESCE(r.ew2_ds_colore, r.ew2_cd_colore) AS sort_key
                          FROM ew2_righe_disposizioni r
                          WHERE (
                            COALESCE(r.ew2_cd_colore, '') ILIKE %(contains)s ESCAPE '\\'
                            OR COALESCE(r.ew2_ds_colore, '') ILIKE %(contains)s ESCAPE '\\'
                          )
                        ) x
                        WHERE cd_colore IS NOT NULL OR ds_colore IS NOT NULL
                        ORDER BY {order_sql}
                        LIMIT %(limit)s
                        """,
                        params,
                    )
                    data = []
                    for cd, ds in cursor.fetchall():
                        if code_like:
                            value = cd or ds
                            label = cd or ds
                            secondary = ds if cd and ds else None
                        else:
                            value = ds or cd
                            label = ds or cd
                            secondary = cd if cd and ds else None
                        if value:
                            data.append(
                                {"value": value, "label": label, "secondary": secondary}
                            )

                elif field == "modello":
                    cursor.execute(
                        """
                        SELECT value, label, secondary FROM (
                          SELECT DISTINCT
                            NULLIF(btrim(r.ew2_modello), '') AS value,
                            NULLIF(btrim(r.ew2_modello), '') AS label,
                            NULLIF(btrim(r.ew2_ds_articolo), '') AS secondary,
                            CASE WHEN r.ew2_modello ILIKE %(prefix)s ESCAPE '\\' THEN 0 ELSE 1 END AS rank_pref,
                            r.ew2_modello AS sort_key
                          FROM ew2_righe_disposizioni r
                          WHERE NULLIF(btrim(r.ew2_modello), '') IS NOT NULL
                            AND (
                              r.ew2_modello ILIKE %(contains)s ESCAPE '\\'
                              OR COALESCE(r.ew2_ds_articolo, '') ILIKE %(contains)s ESCAPE '\\'
                            )
                        ) x
                        ORDER BY rank_pref, sort_key
                        LIMIT %(limit)s
                        """,
                        params,
                    )
                    data = [
                        {"value": r[0], "label": r[1], "secondary": r[2]}
                        for r in cursor.fetchall()
                        if r[0]
                    ]

                elif field == "tessuto":
                    # Priorità: descrizione/articolo (uso operativo), poi qualità, poi token.
                    token_union = ""
                    if _column_exists(cursor, "ew2_righe_disposizioni", "ew2_tessuto_tokens"):
                        token_union = """
                          UNION ALL
                          SELECT
                            tok AS value,
                            tok AS label,
                            NULL::text AS secondary,
                            2 AS rank_src,
                            CASE WHEN tok ILIKE %(prefix)s ESCAPE '\\' THEN 0 ELSE 1 END AS rank_pref,
                            tok AS sort_key
                          FROM ew2_righe_disposizioni r
                          CROSS JOIN LATERAL unnest(COALESCE(r.ew2_tessuto_tokens, ARRAY[]::text[])) AS tok
                          WHERE NULLIF(btrim(tok), '') IS NOT NULL
                            AND length(tok) >= 2
                            AND tok ILIKE %(contains)s ESCAPE '\\'
                        """
                    cursor.execute(
                        f"""
                        SELECT value, label, secondary FROM (
                          SELECT DISTINCT ON (upper(btrim(value)))
                            value, label, secondary, rank_src, rank_pref, sort_key
                          FROM (
                            SELECT
                              NULLIF(btrim(r.ew2_ds_articolo), '') AS value,
                              NULLIF(btrim(r.ew2_ds_articolo), '') AS label,
                              NULLIF(btrim(r.ew2_qualita), '') AS secondary,
                              0 AS rank_src,
                              CASE WHEN r.ew2_ds_articolo ILIKE %(prefix)s ESCAPE '\\' THEN 0 ELSE 1 END AS rank_pref,
                              r.ew2_ds_articolo AS sort_key
                            FROM ew2_righe_disposizioni r
                            WHERE NULLIF(btrim(r.ew2_ds_articolo), '') IS NOT NULL
                              AND r.ew2_ds_articolo ILIKE %(contains)s ESCAPE '\\'

                            UNION ALL

                            SELECT
                              NULLIF(btrim(r.ew2_qualita), '') AS value,
                              NULLIF(btrim(r.ew2_qualita), '') AS label,
                              NULLIF(btrim(r.ew2_ds_articolo), '') AS secondary,
                              1 AS rank_src,
                              CASE WHEN r.ew2_qualita ILIKE %(prefix)s ESCAPE '\\' THEN 0 ELSE 1 END AS rank_pref,
                              r.ew2_qualita AS sort_key
                            FROM ew2_righe_disposizioni r
                            WHERE NULLIF(btrim(r.ew2_qualita), '') IS NOT NULL
                              AND r.ew2_qualita ILIKE %(contains)s ESCAPE '\\'
                            {token_union}
                          ) u
                          WHERE value IS NOT NULL
                          ORDER BY upper(btrim(value)), rank_src, rank_pref, sort_key
                        ) x
                        ORDER BY rank_src, rank_pref, sort_key
                        LIMIT %(limit)s
                        """,
                        params,
                    )
                    data = [
                        {"value": r[0], "label": r[1], "secondary": r[2]}
                        for r in cursor.fetchall()
                        if r[0]
                    ]

                elif field == "commessa":
                    if _column_exists(cursor, "ew2_righe_disposizioni", "ew2_rif_tokens"):
                        cursor.execute(
                            """
                            SELECT value, label, secondary FROM (
                              SELECT DISTINCT
                                tok AS value,
                                tok AS label,
                                NULL::text AS secondary,
                                CASE WHEN tok ILIKE %(prefix)s ESCAPE '\\' THEN 0 ELSE 1 END AS rank_pref,
                                tok AS sort_key
                              FROM ew2_righe_disposizioni r
                              CROSS JOIN LATERAL unnest(COALESCE(r.ew2_rif_tokens, ARRAY[]::text[])) AS tok
                              WHERE NULLIF(btrim(tok), '') IS NOT NULL
                                AND length(tok) >= 2
                                AND tok ILIKE %(contains)s ESCAPE '\\'
                            ) x
                            ORDER BY rank_pref, sort_key
                            LIMIT %(limit)s
                            """,
                            params,
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT value, label, secondary FROM (
                              SELECT DISTINCT
                                NULLIF(btrim(r.ew2_rif_disp_cliente), '') AS value,
                                NULLIF(btrim(r.ew2_rif_disp_cliente), '') AS label,
                                NULL::text AS secondary,
                                CASE WHEN r.ew2_rif_disp_cliente ILIKE %(prefix)s ESCAPE '\\' THEN 0 ELSE 1 END AS rank_pref,
                                r.ew2_rif_disp_cliente AS sort_key
                              FROM ew2_righe_disposizioni r
                              WHERE NULLIF(btrim(r.ew2_rif_disp_cliente), '') IS NOT NULL
                                AND r.ew2_rif_disp_cliente ILIKE %(contains)s ESCAPE '\\'
                            ) x
                            ORDER BY rank_pref, sort_key
                            LIMIT %(limit)s
                            """,
                            params,
                        )
                    data = [
                        {"value": r[0], "label": r[1], "secondary": r[2]}
                        for r in cursor.fetchall()
                        if r[0]
                    ]

            return {"total": len(data), "data": data, "min_chars": min_chars}
        except Exception as e:
            response.status = 500
            return {"error": str(e)}
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn is not None:
                try:
                    db_pool.release_conn(conn)
                except Exception:
                    pass

    @app.route("/api/cicli/refresh-search", method="POST")
    def refresh_cicli_search_endpoint():
        try:
            conn = db_pool.get_conn()
            cursor = conn.cursor()
            if not _cicli_table_exists(cursor, "cicli_search"):
                cursor.close()
                db_pool.release_conn(conn)
                response.status = 400
                return {"error": "cicli_search non esiste: applicare migration cicli-storico-search.sql"}
            cursor.execute("SELECT public.refresh_cicli_search()")
            n = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            db_pool.release_conn(conn)
            return {"status": "ok", "rows": n}
        except Exception as e:
            response.status = 500
            return {"error": str(e)}

    @app.route("/api/cicli", method="GET")
    def get_cicli():
        try:
            page, limit, offset = _parse_pagination(default_limit=50, max_limit=200)
            filters = _cicli_filters()
            vista = filters.get("vista") or "cicli"

            conn = db_pool.get_conn()
            cursor = conn.cursor()

            storico_ok = _cicli_table_exists(cursor, "ew2_righe_disposizioni") and _cicli_table_exists(
                cursor, "ew1_testata_disposizioni"
            )
            search_ok = _cicli_search_ready(cursor)
            storico_range = _storico_range(cursor) if storico_ok else None

            sinonimi = _load_sinonimi(cursor)
            fasi_groups, fasi_espanse = _expand_fasi_keywords(filters.get("fasi") or [], sinonimi)
            note_variants: List[str] = []
            for g in fasi_groups:
                note_variants.extend(g["variants"])

            if vista == "utilizzi":
                result = _fetch_utilizzi_list(
                    cursor, filters, fasi_groups, note_variants, page, limit, offset, storico_ok
                )
                cursor.close()
                db_pool.release_conn(conn)
                if isinstance(result, dict) and result.get("error"):
                    response.status = 400
                    return result
                result["fasi_espanse"] = fasi_espanse
                result["storico_disponibile"] = storico_range
                user = request.environ.get("intex.user") or {}
                log_search(
                    db_pool,
                    user_id=user.get("id"),
                    username=user.get("username"),
                    filters=filters,
                    page=page,
                    limit=limit,
                    result_total=result.get("total") if isinstance(result, dict) else None,
                )
                return result

            params: Dict[str, Any] = {}
            need_search = bool(fasi_groups) and search_ok
            from_where = _cicli_base_from(filters, params, join_search=need_search)

            # Filtro fasi su cicli_search (con fallback EXISTS su fasi se search assente)
            if fasi_groups:
                if need_search:
                    fasi_sql = _fasi_match_sql(
                        fasi_groups, filters.get("fasi_mode") or "all", params, alias="cs"
                    )
                    if fasi_sql:
                        from_where += f" AND ({fasi_sql})"
                else:
                    # fallback: EXISTS su fasi_lavoro / note
                    fb = _fasi_fallback_exists(fasi_groups, filters.get("fasi_mode") or "all", params)
                    if fb:
                        from_where += f" AND ({fb})"

            # Filtro storico: EXISTS o JOIN aggregata
            use_storico = storico_ok and _has_storico_filters(filters)
            if use_storico:
                # Alias ew1/ew2 per non collidere con cicli_testate t
                storico_cond = _storico_where(
                    filters,
                    params,
                    note_variants if filters.get("fasi_note_storico") else None,
                    ew2_alias="ew2",
                    ew1_alias="ew1",
                )
                from_where += f"""
                  AND EXISTS (
                    SELECT 1
                    FROM ew2_righe_disposizioni ew2
                    JOIN ew1_testata_disposizioni ew1
                      ON ew1.ew1_anno_disposizione = ew2.ew2_anno_disposizione
                     AND ew1.ew1_nr_disposizione = ew2.ew2_nr_disposizione
                    WHERE ew2.ew2_cd_cliente = t.codice_cliente
                      AND ew2.ew2_cd_articolo_fattura = t.codice_articolo
                      AND ew2.ew2_cd_ciclo = t.codice_ciclo
                      AND ew2.ew2_cd_linea = t.codice_linea
                      AND ew2.ew2_cd_stagione = t.codice_stagione
                      AND ew2.ew2_cd_composizione = t.codice_composizione
                      AND {storico_cond}
                  )
                """

            # Count
            try:
                cursor.execute(f"SELECT COUNT(*) {from_where}", params)
                total = cursor.fetchone()[0]
            except Exception as e:
                # word_similarity / colonne generate potrebbero mancare: riprova senza similarity
                cursor.connection.rollback()
                if "word_similarity" in str(e).lower() or "ew2_rif_tokens" in str(e).lower():
                    params2 = dict(params)
                    from_where2 = _rebuild_without_advanced(filters, fasi_groups, search_ok, storico_ok, params2, note_variants)
                    cursor.execute(f"SELECT COUNT(*) {from_where2}", params2)
                    total = cursor.fetchone()[0]
                    from_where, params = from_where2, params2
                else:
                    raise

            params_page = dict(params)
            params_page["limit"] = limit
            params_page["offset"] = offset

            cursor.execute(
                f"""
                SELECT
                  t.codice_cliente,
                  cl.ragione_sociale,
                  t.codice_articolo,
                  ar.ds_articolo,
                  t.codice_ciclo,
                  t.codice_ciclo_cli,
                  t.ds_ciclo,
                  t.ds_ciclo_bolle_fat,
                  t.codice_linea,
                  li.ds_linea,
                  t.codice_stagione,
                  st.ds_stagione,
                  t.codice_composizione,
                  co.ds_composizione,
                  t.codice_reparto,
                  t.codice_gruppo,
                  t.st_record,
                  t.nr_revisione,
                  t.data_ins
                  {', cs.search_doc' if need_search else ', NULL AS search_doc'}
                {from_where}
                ORDER BY t.data_ins DESC NULLS LAST, t.nr_revisione DESC NULLS LAST, t.codice_ciclo
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                params_page,
            )
            rows = cursor.fetchall()

            items = []
            for r in rows:
                item = {
                    "codice_cliente": r[0],
                    "ragione_sociale": r[1],
                    "codice_articolo": r[2],
                    "ds_articolo": r[3],
                    "codice_ciclo": r[4],
                    "codice_ciclo_cli": r[5],
                    "ds_ciclo": r[6],
                    "ds_ciclo_bolle_fat": r[7],
                    "codice_linea": r[8],
                    "ds_linea": r[9],
                    "codice_stagione": r[10],
                    "ds_stagione": r[11],
                    "codice_composizione": r[12],
                    "ds_composizione": r[13],
                    "codice_reparto": r[14],
                    "codice_gruppo": r[15],
                    "st_record": r[16],
                    "nr_revisione": r[17],
                    "data_ins": r[18].isoformat() if r[18] else None,
                    "match_fasi": _match_fasi_terms(r[19] if len(r) > 19 else None, fasi_groups),
                }
                items.append(item)

            _enrich_page(cursor, items, storico_ok)

            cursor.close()
            db_pool.release_conn(conn)

            user = request.environ.get("intex.user") or {}
            log_search(
                db_pool,
                user_id=user.get("id"),
                username=user.get("username"),
                filters=filters,
                page=page,
                limit=limit,
                result_total=total,
            )

            return _paginated(
                items,
                total,
                page,
                limit,
                extra={
                    "fasi_espanse": fasi_espanse,
                    "storico_disponibile": storico_range,
                },
            )
        except Exception as e:
            response.status = 500
            return {"error": str(e)}

    def _rebuild_without_advanced(filters, fasi_groups, search_ok, storico_ok, params, note_variants):
        """Fallback senza word_similarity / colonne generate."""
        need_search = bool(fasi_groups) and search_ok
        from_where = _cicli_base_from(filters, params, join_search=need_search)
        if fasi_groups:
            if need_search:
                # solo ILIKE
                group_clauses = []
                for gi, group in enumerate(fasi_groups):
                    ors = []
                    for vi, variant in enumerate(group["variants"]):
                        if len(variant) < 2:
                            continue
                        key = f"fb_fase_{gi}_{vi}"
                        params[key] = f"%{_escape_like(variant)}%"
                        ors.append(f"cs.search_doc ILIKE %({key})s ESCAPE '\\'")
                    if ors:
                        group_clauses.append("(" + " OR ".join(ors) + ")")
                if group_clauses:
                    joiner = " OR " if (filters.get("fasi_mode") or "all") == "any" else " AND "
                    from_where += " AND (" + joiner.join(group_clauses) + ")"
            else:
                fb = _fasi_fallback_exists(fasi_groups, filters.get("fasi_mode") or "all", params)
                if fb:
                    from_where += f" AND ({fb})"

        if storico_ok and _has_storico_filters(filters):
            # storico without word_similarity / tokens
            clauses = ["1=1"]
            if filters.get("colore"):
                params["colore_like"] = f"%{_escape_like(filters['colore'])}%"
                params["colore_prefix"] = f"{_escape_like(filters['colore'])}%"
                clauses.append(
                    "(ew2.ew2_cd_colore ILIKE %(colore_prefix)s ESCAPE '\\'"
                    " OR ew2.ew2_ds_colore ILIKE %(colore_like)s ESCAPE '\\')"
                )
            if filters.get("commessa"):
                params["commessa_like"] = f"%{_escape_like(filters['commessa'])}%"
                clauses.append(
                    "(ew2.ew2_rif_disp_cliente ILIKE %(commessa_like)s ESCAPE '\\'"
                    " OR COALESCE(ew1.ew1_rifer_cliente, '') ILIKE %(commessa_like)s ESCAPE '\\')"
                )
            if filters.get("modello"):
                params["modello_like"] = f"%{_escape_like(filters['modello'])}%"
                clauses.append(
                    "(ew2.ew2_modello ILIKE %(modello_like)s ESCAPE '\\'"
                    " OR ew2.ew2_ds_articolo ILIKE %(modello_like)s ESCAPE '\\')"
                )
            if filters.get("tessuto"):
                params["tessuto_like"] = f"%{_escape_like(filters['tessuto'])}%"
                clauses.append(
                    "(COALESCE(ew2.ew2_ds_articolo, '') ILIKE %(tessuto_like)s ESCAPE '\\'"
                    " OR COALESCE(ew2.ew2_qualita, '') ILIKE %(tessuto_like)s ESCAPE '\\'"
                    " OR COALESCE(ew2.ew2_note, '') ILIKE %(tessuto_like)s ESCAPE '\\')"
                )
            if filters.get("articolo_fiscale"):
                art = (filters["articolo_fiscale"] or "").strip()
                params["articolo_fiscale"] = art
                params["articolo_fiscale_like"] = f"%{_escape_like(art)}%"
                clauses.append(
                    "(btrim(COALESCE(ew2.ew2_cd_articolo_fiscale, '')) ILIKE %(articolo_fiscale)s ESCAPE '\\'"
                    " OR btrim(COALESCE(ew2.ew2_cd_articolo_fiscale, '')) ILIKE %(articolo_fiscale_like)s ESCAPE '\\')"
                )
            if filters.get("data_bolla_da"):
                params["data_bolla_da"] = filters["data_bolla_da"]
                clauses.append("ew1.ew1_data_bolla_cli >= %(data_bolla_da)s")
            if filters.get("data_bolla_a"):
                params["data_bolla_a"] = filters["data_bolla_a"]
                clauses.append("ew1.ew1_data_bolla_cli <= %(data_bolla_a)s")
            storico_cond = " AND ".join(clauses)
            from_where += f"""
              AND EXISTS (
                SELECT 1
                FROM ew2_righe_disposizioni ew2
                JOIN ew1_testata_disposizioni ew1
                  ON ew1.ew1_anno_disposizione = ew2.ew2_anno_disposizione
                 AND ew1.ew1_nr_disposizione = ew2.ew2_nr_disposizione
                WHERE ew2.ew2_cd_cliente = t.codice_cliente
                  AND ew2.ew2_cd_articolo_fattura = t.codice_articolo
                  AND ew2.ew2_cd_ciclo = t.codice_ciclo
                  AND ew2.ew2_cd_linea = t.codice_linea
                  AND ew2.ew2_cd_stagione = t.codice_stagione
                  AND ew2.ew2_cd_composizione = t.codice_composizione
                  AND {storico_cond}
              )
            """
        return from_where

    def _fasi_fallback_exists(groups, mode, params):
        group_clauses = []
        for gi, group in enumerate(groups):
            ors = []
            for vi, variant in enumerate(group["variants"]):
                if len(variant) < 2:
                    continue
                key = f"fase_fb_{gi}_{vi}"
                params[key] = f"%{_escape_like(variant)}%"
                ors.append(
                    f"""EXISTS (
                      SELECT 1 FROM cicli_fasi f
                      LEFT JOIN fasi_lavoro z ON z.codice_fase = f.codice_fase
                      WHERE f.codice_cliente = t.codice_cliente
                        AND f.codice_articolo = t.codice_articolo
                        AND f.codice_ciclo = t.codice_ciclo
                        AND f.codice_linea = t.codice_linea
                        AND f.codice_stagione = t.codice_stagione
                        AND f.codice_composizione = t.codice_composizione
                        AND (
                          COALESCE(z.ds_fase, '') ILIKE %({key})s ESCAPE '\\'
                          OR COALESCE(f.note, '') ILIKE %({key})s ESCAPE '\\'
                          OR COALESCE(t.ds_ciclo, '') ILIKE %({key})s ESCAPE '\\'
                          OR COALESCE(t.note, '') ILIKE %({key})s ESCAPE '\\'
                        )
                    )"""
                )
            if ors:
                group_clauses.append("(" + " OR ".join(ors) + ")")
        if not group_clauses:
            return None
        joiner = " OR " if mode == "any" else " AND "
        return joiner.join(group_clauses)

    def _match_fasi_terms(search_doc, groups):
        if not search_doc or not groups:
            return []
        doc = search_doc.upper()
        hits = []
        for g in groups:
            for v in g["variants"]:
                if v and v.upper() in doc:
                    hits.append(v)
                    break
            else:
                hits.append(g["keyword"])
        return hits

    def _fetch_utilizzi_list(cursor, filters, fasi_groups, note_variants, page, limit, offset, storico_ok):
        if not storico_ok:
            return {"error": "Tabelle storico non disponibili"}

        params: Dict[str, Any] = {}
        storico_cond = _storico_where(
            filters, params, note_variants if filters.get("fasi_note_storico") else None
        )

        # Filtri cicli via EXISTS su cicli_testate
        cicli_exists = """
          EXISTS (
            SELECT 1 FROM cicli_testate ct
            LEFT JOIN articoli_cliente ar
              ON ar.codice_cliente = ct.codice_cliente
             AND ar.codice_articolo = ct.codice_articolo
            LEFT JOIN composizioni co
              ON co.codice_composizione = ct.codice_composizione
            WHERE ct.codice_cliente = r.ew2_cd_cliente
              AND ct.codice_articolo = r.ew2_cd_articolo_fattura
              AND ct.codice_ciclo = r.ew2_cd_ciclo
              AND ct.codice_linea = r.ew2_cd_linea
              AND ct.codice_stagione = r.ew2_cd_stagione
              AND ct.codice_composizione = r.ew2_cd_composizione
        """
        if filters.get("codice_cliente"):
            cicli_exists += " AND ct.codice_cliente = %(codice_cliente)s"
            params["codice_cliente"] = filters["codice_cliente"]
        if filters.get("stagione"):
            cicli_exists += " AND ct.codice_stagione = %(stagione)s"
            params["stagione"] = filters["stagione"]
        codice_ciclo_pat = _broad_like_pattern(filters.get("codice_ciclo"))
        if codice_ciclo_pat:
            cicli_exists += """
              AND (
                ct.codice_ciclo ILIKE %(codice_ciclo_pat)s ESCAPE '\\'
                OR COALESCE(ct.codice_ciclo_cli, '') ILIKE %(codice_ciclo_pat)s ESCAPE '\\'
              )
            """
            params["codice_ciclo_pat"] = codice_ciclo_pat
        articolo_pat = _broad_like_pattern(filters.get("articolo"))
        if articolo_pat:
            cicli_exists += """
              AND (
                COALESCE(ar.ds_articolo, '') ILIKE %(articolo_pat)s ESCAPE '\\'
                OR ct.codice_articolo ILIKE %(articolo_pat)s ESCAPE '\\'
              )
            """
            params["articolo_pat"] = articolo_pat
        composizione_pat = _broad_like_pattern(filters.get("composizione"))
        if composizione_pat:
            cicli_exists += """
              AND (
                COALESCE(co.ds_composizione, '') ILIKE %(composizione_pat)s ESCAPE '\\'
                OR ct.codice_composizione ILIKE %(composizione_pat)s ESCAPE '\\'
              )
            """
            params["composizione_pat"] = composizione_pat
        descrizione_pat = _broad_like_pattern(filters.get("descrizione"))
        if descrizione_pat:
            cicli_exists += """
              AND (
                COALESCE(ct.ds_ciclo, '') ILIKE %(descrizione_pat)s ESCAPE '\\'
                OR COALESCE(ct.ds_ciclo_bolle_fat, '') ILIKE %(descrizione_pat)s ESCAPE '\\'
              )
            """
            params["descrizione_pat"] = descrizione_pat

        if fasi_groups:
            # join a cicli_search via chiave
            cicli_exists += """
              AND EXISTS (
                SELECT 1 FROM cicli_search cs
                WHERE cs.codice_cliente = ct.codice_cliente
                  AND cs.codice_articolo = ct.codice_articolo
                  AND cs.codice_ciclo = ct.codice_ciclo
                  AND cs.codice_linea = ct.codice_linea
                  AND cs.codice_stagione = ct.codice_stagione
                  AND cs.codice_composizione = ct.codice_composizione
            """
            fasi_sql = _fasi_match_sql(fasi_groups, filters.get("fasi_mode") or "all", params, alias="cs")
            if fasi_sql:
                cicli_exists += f" AND ({fasi_sql})"
            cicli_exists += ")"

        cicli_exists += ")"

        from_where = f"""
            FROM ew2_righe_disposizioni r
            JOIN ew1_testata_disposizioni t
              ON t.ew1_anno_disposizione = r.ew2_anno_disposizione
             AND t.ew1_nr_disposizione = r.ew2_nr_disposizione
            LEFT JOIN cicli_clienti cl ON cl.codice_cliente = r.ew2_cd_cliente
            WHERE {storico_cond}
              AND {cicli_exists}
        """

        try:
            cursor.execute(f"SELECT COUNT(*) {from_where}", params)
            total = cursor.fetchone()[0]
        except Exception:
            cursor.connection.rollback()
            # semplifica: senza fasi_search avanzata
            return {"error": "Errore query utilizzi: verificare migration cicli-storico-search.sql"}

        params_page = dict(params)
        params_page["limit"] = limit
        params_page["offset"] = offset
        cursor.execute(
            f"""
            SELECT
              TO_CHAR(t.ew1_data_bolla_cli, 'DD/MM/YYYY'),
              t.ew1_nr_bolla_cli,
              r.ew2_cd_cliente,
              cl.ragione_sociale,
              r.ew2_cd_ciclo,
              r.ew2_cd_ciclo_cli,
              r.ew2_cd_articolo_fattura,
              r.ew2_cd_articolo_fiscale,
              r.ew2_ds_articolo,
              r.ew2_cd_colore,
              r.ew2_ds_colore,
              r.ew2_modello,
              r.ew2_qualita,
              r.ew2_rif_disp_cliente,
              r.ew2_cd_composizione,
              r.ew2_cd_stagione,
              r.ew2_cd_linea,
              r.ew2_nr_capi_caricati,
              r.ew2_kg_caricati,
              r.ew2_note,
              r.ew2_anno_disposizione,
              r.ew2_nr_disposizione,
              r.ew2_riga_disposizione
            {from_where}
            ORDER BY t.ew1_data_bolla_cli DESC NULLS LAST,
                     r.ew2_nr_disposizione DESC,
                     r.ew2_riga_disposizione
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params_page,
        )
        rows = cursor.fetchall()
        items = []
        for r in rows:
            items.append(
                {
                    "data_bolla": r[0],
                    "nr_bolla": r[1],
                    "codice_cliente": r[2],
                    "ragione_sociale": r[3],
                    "codice_ciclo": r[4],
                    "codice_ciclo_cli": r[5],
                    "codice_articolo": r[6],
                    "articolo_fiscale": r[7],
                    "ds_articolo": r[8],
                    "cd_colore": r[9],
                    "ds_colore": r[10],
                    "modello": r[11],
                    "tessuto": r[12],
                    "commessa": r[13],
                    "codice_composizione": r[14],
                    "codice_stagione": r[15],
                    "codice_linea": r[16],
                    "capi_caricati": float(r[17]) if r[17] is not None else None,
                    "kg_caricati": float(r[18]) if r[18] is not None else None,
                    "note": r[19],
                    "anno_disposizione": r[20],
                    "nr_disposizione": r[21],
                    "riga_disposizione": r[22],
                }
            )
        return _paginated(items, total, page, limit)

    @app.route("/api/cicli/fasi", method="GET")
    def get_cicli_fasi():
        try:
            codice_cliente = (request.query.get("codice_cliente") or "").strip()
            codice_articolo = (request.query.get("codice_articolo") or "").strip()
            codice_ciclo = (request.query.get("codice_ciclo") or "").strip()
            codice_linea = (request.query.get("codice_linea") or "").strip()
            codice_stagione = (request.query.get("codice_stagione") or "").strip()
            codice_composizione = (request.query.get("codice_composizione") or "").strip()

            missing = [
                name
                for name, val in [
                    ("codice_cliente", codice_cliente),
                    ("codice_articolo", codice_articolo),
                    ("codice_ciclo", codice_ciclo),
                    ("codice_linea", codice_linea),
                    ("codice_stagione", codice_stagione),
                    ("codice_composizione", codice_composizione),
                ]
                if not val
            ]
            if missing:
                response.status = 400
                return {"error": f"Missing required params: {', '.join(missing)}"}

            conn = db_pool.get_conn()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                  f.sequenza,
                  f.codice_fase,
                  z.ds_fase,
                  f.codice_macrofase,
                  f.codice_unita_mis,
                  f.note,
                  f.st_record
                FROM cicli_fasi f
                LEFT JOIN fasi_lavoro z ON z.codice_fase = f.codice_fase
                WHERE f.codice_cliente = %(codice_cliente)s
                  AND f.codice_articolo = %(codice_articolo)s
                  AND f.codice_ciclo = %(codice_ciclo)s
                  AND f.codice_linea = %(codice_linea)s
                  AND f.codice_stagione = %(codice_stagione)s
                  AND f.codice_composizione = %(codice_composizione)s
                ORDER BY f.sequenza
                """,
                {
                    "codice_cliente": codice_cliente,
                    "codice_articolo": codice_articolo,
                    "codice_ciclo": codice_ciclo,
                    "codice_linea": codice_linea,
                    "codice_stagione": codice_stagione,
                    "codice_composizione": codice_composizione,
                },
            )
            rows = cursor.fetchall()
            cursor.close()
            db_pool.release_conn(conn)

            data = [
                {
                    "sequenza": r[0],
                    "codice_fase": r[1],
                    "ds_fase": r[2],
                    "codice_macrofase": r[3],
                    "codice_unita_mis": r[4],
                    "note": r[5],
                    "st_record": r[6],
                }
                for r in rows
            ]
            return {"total": len(data), "data": data}
        except Exception as e:
            response.status = 500
            return {"error": str(e)}

    @app.route("/api/cicli/utilizzi", method="GET")
    def get_cicli_utilizzi():
        """Espansione utilizzi per un singolo ciclo (chiave a 6 campi)."""
        try:
            codice_cliente = (request.query.get("codice_cliente") or "").strip()
            codice_articolo = (request.query.get("codice_articolo") or "").strip()
            codice_ciclo = (request.query.get("codice_ciclo") or "").strip()
            codice_linea = (request.query.get("codice_linea") or "").strip()
            codice_stagione = (request.query.get("codice_stagione") or "").strip()
            codice_composizione = (request.query.get("codice_composizione") or "").strip()

            missing = [
                name
                for name, val in [
                    ("codice_cliente", codice_cliente),
                    ("codice_articolo", codice_articolo),
                    ("codice_ciclo", codice_ciclo),
                    ("codice_linea", codice_linea),
                    ("codice_stagione", codice_stagione),
                    ("codice_composizione", codice_composizione),
                ]
                if not val
            ]
            if missing:
                response.status = 400
                return {"error": f"Missing required params: {', '.join(missing)}"}

            page, limit, offset = _parse_pagination(default_limit=50, max_limit=200)
            filters = _cicli_filters()
            # forza chiave ciclo
            filters["codice_cliente"] = codice_cliente

            conn = db_pool.get_conn()
            cursor = conn.cursor()
            if not (
                _cicli_table_exists(cursor, "ew2_righe_disposizioni")
                and _cicli_table_exists(cursor, "ew1_testata_disposizioni")
            ):
                cursor.close()
                db_pool.release_conn(conn)
                return {"total": 0, "page": 1, "limit": limit, "pages": 1, "data": []}

            params: Dict[str, Any] = {
                "codice_cliente": codice_cliente,
                "codice_articolo": codice_articolo,
                "codice_ciclo": codice_ciclo,
                "codice_linea": codice_linea,
                "codice_stagione": codice_stagione,
                "codice_composizione": codice_composizione,
            }
            storico_cond = _storico_where(filters, params)

            from_where = f"""
                FROM ew2_righe_disposizioni r
                JOIN ew1_testata_disposizioni t
                  ON t.ew1_anno_disposizione = r.ew2_anno_disposizione
                 AND t.ew1_nr_disposizione = r.ew2_nr_disposizione
                WHERE r.ew2_cd_cliente = %(codice_cliente)s
                  AND r.ew2_cd_articolo_fattura = %(codice_articolo)s
                  AND r.ew2_cd_ciclo = %(codice_ciclo)s
                  AND r.ew2_cd_linea = %(codice_linea)s
                  AND r.ew2_cd_stagione = %(codice_stagione)s
                  AND r.ew2_cd_composizione = %(codice_composizione)s
                  AND {storico_cond}
            """

            try:
                cursor.execute(f"SELECT COUNT(*) {from_where}", params)
                total = cursor.fetchone()[0]
            except Exception:
                cursor.connection.rollback()
                # senza colonne generate
                params_fb = {
                    "codice_cliente": codice_cliente,
                    "codice_articolo": codice_articolo,
                    "codice_ciclo": codice_ciclo,
                    "codice_linea": codice_linea,
                    "codice_stagione": codice_stagione,
                    "codice_composizione": codice_composizione,
                }
                from_where = """
                    FROM ew2_righe_disposizioni r
                    JOIN ew1_testata_disposizioni t
                      ON t.ew1_anno_disposizione = r.ew2_anno_disposizione
                     AND t.ew1_nr_disposizione = r.ew2_nr_disposizione
                    WHERE r.ew2_cd_cliente = %(codice_cliente)s
                      AND r.ew2_cd_articolo_fattura = %(codice_articolo)s
                      AND r.ew2_cd_ciclo = %(codice_ciclo)s
                      AND r.ew2_cd_linea = %(codice_linea)s
                      AND r.ew2_cd_stagione = %(codice_stagione)s
                      AND r.ew2_cd_composizione = %(codice_composizione)s
                """
                cursor.execute(f"SELECT COUNT(*) {from_where}", params_fb)
                total = cursor.fetchone()[0]
                params = params_fb

            params_page = dict(params)
            params_page["limit"] = limit
            params_page["offset"] = offset
            cursor.execute(
                f"""
                SELECT
                  TO_CHAR(t.ew1_data_bolla_cli, 'DD/MM/YYYY'),
                  t.ew1_nr_bolla_cli,
                  r.ew2_rif_disp_cliente,
                  r.ew2_cd_colore,
                  r.ew2_ds_colore,
                  r.ew2_modello,
                  r.ew2_qualita,
                  r.ew2_cd_articolo_fiscale,
                  r.ew2_ds_articolo,
                  r.ew2_nr_capi_caricati,
                  r.ew2_kg_caricati,
                  r.ew2_note,
                  r.ew2_anno_disposizione,
                  r.ew2_nr_disposizione,
                  r.ew2_riga_disposizione
                {from_where}
                ORDER BY t.ew1_data_bolla_cli DESC NULLS LAST,
                         r.ew2_nr_disposizione DESC,
                         r.ew2_riga_disposizione
                LIMIT %(limit)s OFFSET %(offset)s
                """,
                params_page,
            )
            rows = cursor.fetchall()
            cursor.close()
            db_pool.release_conn(conn)

            data = [
                {
                    "data_bolla": r[0],
                    "nr_bolla": r[1],
                    "commessa": r[2],
                    "cd_colore": r[3],
                    "ds_colore": r[4],
                    "modello": r[5],
                    "tessuto": r[6],
                    "articolo_fiscale": r[7],
                    "ds_articolo": r[8],
                    "capi_caricati": float(r[9]) if r[9] is not None else None,
                    "kg_caricati": float(r[10]) if r[10] is not None else None,
                    "note": r[11],
                    "anno_disposizione": r[12],
                    "nr_disposizione": r[13],
                    "riga_disposizione": r[14],
                }
                for r in rows
            ]
            return _paginated(data, total, page, limit)
        except Exception as e:
            response.status = 500
            return {"error": str(e)}
