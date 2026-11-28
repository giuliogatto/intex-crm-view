"""Offline checks sul punteggio cicli compatibili (nessuna chiamata DB)."""

import copy

from cicli_compatibili import (
    MAX_SENZA_FASI_COMUNI,
    _anno_da_stagione,
    _chiave_ordinamento_compatibile,
    _codice_fase_canonico,
    _livello_soglia,
    confronta_cicli,
    fasi_ignorate_ranking,
)


def _fase(seq, cod, ds, note=None):
    return {
        "sequenza": seq,
        "codice_fase": cod,
        "ds_fase": ds,
        "codice_macrofase": None,
        "codice_unita_mis": "NR",
        "note": note,
    }


BASE = {
    "codice_cliente": "1213",
    "codice_articolo": "00058",
    "codice_ciclo": "T100L",
    "codice_ciclo_cli": "T100L-TELI",
    "codice_linea": ".",
    "codice_stagione": "AI 27",
    "codice_composizione": "00006",
    "ds_ciclo": "TINTO",
    "ds_ciclo_bolle_fat": "TINTO",
    "note": None,
    "codice_reparto": "TINTO",
    "codice_gruppo": ".",
    "fasi": [
        _fase(10, "000103", "TINTO OLANDESE"),
        _fase(20, "001127", "ASCIUGATURA SETA+MISTE 40°X15'"),
        _fase(30, "001049", "CONTROLLO QUALITA'"),
    ],
}


def _variante(**changes):
    c = copy.deepcopy(BASE)
    c.update(changes)
    return c


def test_cambio_solo_articolo_e_stagione_vale_100():
    cand = _variante(codice_articolo="CAPI", codice_stagione="PE 26")
    esito = confronta_cicli(BASE, cand)
    assert esito["compatibilita"] == 100.0
    campi_diff = {d["campo"] for d in esito["differenze"]}
    assert campi_diff == {"codice_articolo", "codice_stagione"}
    assert all(d["penalita"] == 0 for d in esito["differenze"])


def test_una_fase_sostituita_vale_90():
    cand = _variante()
    # 001130 non è in fasi-da-ignorare-in-ranking (001124 sì → non andrebbe in confronto)
    cand["fasi"][1] = _fase(20, "001130", "ASCIUGATURA LANA E MISTE 50°X25'")
    esito = confronta_cicli(BASE, cand)
    assert esito["compatibilita"] == 90.0
    diff = [d for d in esito["differenze"] if d["campo"] == "fase"]
    assert len(diff) == 1 and diff[0]["tipo"] == "sostituita"


def test_fase_aggiunta_e_mancante():
    cand = _variante()
    cand["fasi"].append(_fase(40, "000500", "STIRO"))
    assert confronta_cicli(BASE, cand)["compatibilita"] == 90.0

    cand = _variante()
    del cand["fasi"][0]
    esito = confronta_cicli(BASE, cand)
    assert esito["compatibilita"] == 90.0
    assert esito["differenze"][-1]["tipo"] == "mancante"


def test_scambio_adiacente_conta_una_modifica():
    cand = _variante()
    cand["fasi"][1], cand["fasi"][2] = cand["fasi"][2], cand["fasi"][1]
    esito = confronta_cicli(BASE, cand)
    assert esito["compatibilita"] == 90.0
    assert [d["tipo"] for d in esito["differenze"] if d["campo"] == "fase"] == ["scambio"]


def test_nota_fase_e_campi_testata_penalizzano_meno_di_una_fase():
    cand = _variante(codice_composizione="10002")
    cand["fasi"][0]["note"] = "BAGNO LUNGO"
    esito = confronta_cicli(BASE, cand)
    assert 90.0 < esito["compatibilita"] < 100.0


def test_descrizione_simile_penalita_parziale():
    cand = _variante(ds_ciclo="TINTO CAPO")
    esito = confronta_cicli(BASE, cand)
    diff = next(d for d in esito["differenze"] if d["campo"] == "ds_ciclo")
    assert 0 < diff["penalita"] < 8


def test_nessuna_fase_in_comune_e_limitata():
    cand = _variante()
    cand["fasi"] = [_fase(10, "009999", "LAVAGGIO ENZIMA")]
    esito = confronta_cicli(BASE, cand)
    assert esito["compatibilita"] <= MAX_SENZA_FASI_COMUNI


def test_simili_elenca_fasi_uguali():
    esito = confronta_cicli(BASE, _variante(codice_stagione="PE 26"))
    campi = {s["campo"] for s in esito["simili"]}
    assert {"fasi", "sequenza_fasi", "ds_ciclo", "codice_composizione"} <= campi


def test_livelli_crescenti_restringono():
    soglie = [_livello_soglia(lv) for lv in range(1, 6)]
    assert soglie == sorted(soglie)
    assert _livello_soglia(0) == soglie[0]
    assert _livello_soglia(99) == soglie[-1] == 100.0


def test_anno_da_stagione():
    assert _anno_da_stagione("AI 27") == 2027
    assert _anno_da_stagione("AI 27/28") == 2027
    assert _anno_da_stagione("PE 26") == 2026
    assert _anno_da_stagione("PE 2027") == 2027
    assert _anno_da_stagione("AI 99") == 1999
    assert _anno_da_stagione("*") is None
    assert _anno_da_stagione("pe/ai") is None
    assert _anno_da_stagione("") is None
    assert _anno_da_stagione(None) is None


def test_ordinamento_stagione_poi_ranking():
    """Anno stagione DESC, poi compatibilità; senza anno in fondo."""

    def item(stagione, compat, data_ins=""):
        return {
            "compatibilita": compat,
            "ciclo": {"codice_stagione": stagione, "data_ins": data_ins},
        }

    rows = [
        item("AI 26/27", 100.0),
        item("*", 100.0),
        item("PE 27", 90.0),
        item("AI 27/28", 90.0),
        item("pe/ai", 95.0),
        item("PE 27", 100.0),
    ]
    ordered = sorted(rows, key=_chiave_ordinamento_compatibile, reverse=True)
    assert [(r["ciclo"]["codice_stagione"], r["compatibilita"]) for r in ordered] == [
        ("PE 27", 100.0),     # 2027, ranking alto
        ("PE 27", 90.0),      # 2027, ranking più basso (stabile rispetto ad AI 27/28)
        ("AI 27/28", 90.0),   # 2027
        ("AI 26/27", 100.0),  # 2026
        ("*", 100.0),         # senza anno, ranking alto
        ("pe/ai", 95.0),      # senza anno
    ]


def test_fasi_ignorate_ranking_normalizza_leading_zero():
    ignore = fasi_ignorate_ranking()
    assert ignore  # file documentation caricato
    assert _codice_fase_canonico("000068") == "68"
    assert _codice_fase_canonico("69") == "69"
    assert "68" in ignore and "69" in ignore
    assert "1124" in ignore and "1148" in ignore


def test_fasi_generiche_non_pesano_sul_ranking():
    """Fasi in fasi-da-ignorare-in-ranking.txt non contano su input né candidato."""
    assert "125" in fasi_ignorate_ranking()
    assert "1124" in fasi_ignorate_ranking()

    # Stesse fasi di lavorazione; sul candidato ci sono in più fasi generiche.
    cand = _variante()
    cand["fasi"] = list(cand["fasi"]) + [
        _fase(40, "000125", "CONTROLLO GENERICO"),
        _fase(50, "001124", "FASE SEMPRE PRESENTE"),
    ]
    assert confronta_cicli(BASE, cand)["compatibilita"] == 100.0

    # Solo differenze su fasi ignorate → ancora 100%.
    solo_ignore_in = _variante(fasi=[
        _fase(10, "000069", "GENERICA A"),
        _fase(20, "000103", "TINTO OLANDESE"),
        _fase(30, "001127", "ASCIUGATURA SETA+MISTE 40°X15'"),
        _fase(40, "001049", "CONTROLLO QUALITA'"),
        _fase(50, "000207", "GENERICA B"),
    ])
    solo_ignore_cand = _variante(fasi=[
        _fase(10, "000103", "TINTO OLANDESE"),
        _fase(20, "001127", "ASCIUGATURA SETA+MISTE 40°X15'"),
        _fase(30, "001049", "CONTROLLO QUALITA'"),
        _fase(40, "001148", "ALTRA GENERICA"),
    ])
    assert confronta_cicli(solo_ignore_in, solo_ignore_cand)["compatibilita"] == 100.0

    # Una fase di lavorazione diversa continua a pesare 10 punti.
    cand_bad = _variante()
    cand_bad["fasi"] = [
        _fase(10, "000125", "IGNORATA"),
        _fase(20, "000103", "TINTO OLANDESE"),
        _fase(30, "009999", "ALTRO LAVAGGIO"),
        _fase(40, "001049", "CONTROLLO QUALITA'"),
        _fase(50, "001124", "IGNORATA 2"),
    ]
    esito = confronta_cicli(BASE, cand_bad)
    assert esito["compatibilita"] == 90.0
    assert any(d.get("tipo") == "sostituita" for d in esito["differenze"] if d["campo"] == "fase")
