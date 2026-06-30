"""
API routes for /api/analisi/* — deterministic analytics endpoints for UI and LLM.
"""

from datetime import date
from decimal import Decimal

from bottle import request, response


def _decimal_to_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_to_dict(columns, row):
    if not row:
        return None
    out = {}
    for i, col in enumerate(columns):
        val = row[i]
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        elif isinstance(val, list):
            val = list(val)
        else:
            val = _decimal_to_float(val)
        out[col] = val
    return out


def _rows_to_list(cursor):
    columns = [desc[0] for desc in cursor.description]
    return [_row_to_dict(columns, row) for row in cursor.fetchall()]


def _parse_int(name, default, minimum=1, maximum=100):
    try:
        value = int(request.query.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(min(value, maximum), minimum)


def register_analisi_routes(app, db_pool):
    @app.route("/api/analisi/meta", method="GET")
    def analisi_meta():
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_name, last_success, last_error, elapsed_seconds
                FROM analytics.sync_meta
                WHERE job_name = 'rebuild_analytics'
                """
            )
            row = cursor.fetchone()
            if not row:
                return {"data": None}
            return {
                "data": {
                    "job_name": row[0],
                    "last_success": row[1].isoformat() if row[1] else None,
                    "last_error": row[2],
                    "elapsed_seconds": _decimal_to_float(row[3]),
                }
            }
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/fatturato/mensile", method="GET")
    def analisi_fatturato_mensile():
        mesi = _parse_int("mesi", 24, minimum=1, maximum=60)
        codice_cliente = request.query.get("codice_cliente") or None

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            params = {"mesi": mesi}
            client_filter = ""
            if codice_cliente:
                client_filter = "AND codice_cliente = %(codice_cliente)s"
                params["codice_cliente"] = codice_cliente

            cursor.execute(
                f"""
                SELECT anno, mese, SUM(totale_fatturato) AS fatturato_mensile,
                       SUM(numero_fatture) AS numero_fatture
                FROM analytics.clienti_fatturato_mensile
                WHERE make_date(anno, mese, 1) >= date_trunc('month', CURRENT_DATE) - (%(mesi)s || ' months')::INTERVAL
                {client_filter}
                GROUP BY anno, mese
                ORDER BY anno DESC, mese DESC
                LIMIT %(mesi)s
                """,
                params,
            )
            return {"total": cursor.rowcount, "data": _rows_to_list(cursor)}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/ranking", method="GET")
    def analisi_clienti_ranking():
        limit = _parse_int("limit", 10, minimum=1, maximum=100)
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.codice AS codice_cliente, c.ragione_sociale,
                       s.fatturato_rolling_12m AS fatturato,
                       s.percentuale_sul_totale_12m AS percentuale,
                       s.rank_fatturato_12m AS rank
                FROM analytics.clienti_snapshot s
                JOIN clienti c ON c.codice = s.codice_cliente
                WHERE s.fatturato_rolling_12m > 0
                ORDER BY s.fatturato_rolling_12m DESC
                LIMIT %(limit)s
                """,
                {"limit": limit},
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/concentrazione", method="GET")
    def analisi_clienti_concentrazione():
        top_n = _parse_int("top_n", 5, minimum=1, maximum=50)
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                WITH periodi AS (
                    SELECT codice_cliente,
                        SUM(totale_fatturato) FILTER (
                            WHERE make_date(anno, mese, 1) >= date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
                        ) AS fat_corrente,
                        SUM(totale_fatturato) FILTER (
                            WHERE make_date(anno, mese, 1) >= date_trunc('month', CURRENT_DATE) - INTERVAL '24 months'
                              AND make_date(anno, mese, 1) < date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
                        ) AS fat_precedente
                    FROM analytics.clienti_fatturato_mensile
                    GROUP BY codice_cliente
                ),
                totali AS (
                    SELECT COALESCE(SUM(fat_corrente), 0) AS tot_corrente,
                           COALESCE(SUM(fat_precedente), 0) AS tot_precedente
                    FROM periodi
                ),
                rank_corrente AS (
                    SELECT fat_corrente,
                           ROW_NUMBER() OVER (ORDER BY fat_corrente DESC) AS rn
                    FROM periodi WHERE fat_corrente > 0
                ),
                rank_precedente AS (
                    SELECT fat_precedente,
                           ROW_NUMBER() OVER (ORDER BY fat_precedente DESC) AS rn
                    FROM periodi WHERE fat_precedente > 0
                )
                SELECT
                    ROUND(100.0 * (SELECT COALESCE(SUM(fat_corrente), 0) FROM rank_corrente WHERE rn <= %(top_n)s)
                          / NULLIF((SELECT tot_corrente FROM totali), 0), 2) AS quota_top_n_ultimi_12m,
                    ROUND(100.0 * (SELECT COALESCE(SUM(fat_precedente), 0) FROM rank_precedente WHERE rn <= %(top_n)s)
                          / NULLIF((SELECT tot_precedente FROM totali), 0), 2) AS quota_top_n_periodo_precedente,
                    (SELECT tot_corrente FROM totali) AS fatturato_totale_12m,
                    (SELECT tot_precedente FROM totali) AS fatturato_totale_periodo_precedente
                """,
                {"top_n": top_n},
            )
            row = cursor.fetchone()
            columns = [d[0] for d in cursor.description]
            return {"data": _row_to_dict(columns, row)}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/erosione", method="GET")
    def analisi_clienti_erosione():
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.codice AS codice_cliente, c.ragione_sociale,
                       s.fatturato_semestre_yoy AS semestre_anno_scorso,
                       s.fatturato_semestre_corrente AS semestre_attuale,
                       (s.fatturato_semestre_yoy - s.fatturato_semestre_corrente) AS calo_assoluto,
                       ROUND(100.0 * (s.fatturato_semestre_yoy - s.fatturato_semestre_corrente)
                             / NULLIF(s.fatturato_semestre_yoy, 0), 2) AS calo_percentuale,
                       s.intervallo_medio_giorni_prec AS giorni_medio_anno_scorso,
                       s.intervallo_medio_giorni_corrente AS giorni_medio_quest_anno,
                       (s.intervallo_medio_giorni_corrente - s.intervallo_medio_giorni_prec) AS allungamento_giorni
                FROM analytics.clienti_snapshot s
                JOIN clienti c ON c.codice = s.codice_cliente
                WHERE s.fatturato_semestre_corrente < s.fatturato_semestre_yoy
                   OR s.intervallo_medio_giorni_corrente > s.intervallo_medio_giorni_prec
                ORDER BY calo_assoluto DESC NULLS LAST
                """
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/dormienti", method="GET")
    def analisi_clienti_dormienti():
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.codice AS codice_cliente, c.ragione_sociale,
                       s.data_ultimo_ordine, s.giorni_dall_ultimo_ordine,
                       s.fatturato_rolling_12m
                FROM analytics.clienti_snapshot s
                JOIN clienti c ON c.codice = s.codice_cliente
                WHERE s.is_dormiente = TRUE
                ORDER BY s.giorni_dall_ultimo_ordine DESC NULLS LAST
                """
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/nuovi", method="GET")
    def analisi_clienti_nuovi():
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.codice AS codice_cliente, c.ragione_sociale,
                       s.data_primo_ordine, s.fatturato_rolling_12m
                FROM analytics.clienti_snapshot s
                JOIN clienti c ON c.codice = s.codice_cliente
                WHERE s.is_nuovo_12m = TRUE
                ORDER BY s.data_primo_ordine DESC
                """
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/stagione", method="GET")
    def analisi_clienti_stagione():
        stagione_attuale = request.query.get("stagione_attuale")
        stagione_precedente = request.query.get("stagione_precedente")
        if not stagione_attuale or not stagione_precedente:
            response.status = 400
            return {"error": "stagione_attuale and stagione_precedente are required"}

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.codice AS codice_cliente, c.ragione_sociale,
                       SUM(CASE WHEN f.codice_stagione = %(attuale)s THEN f.totale_fatturato ELSE 0 END) AS fatturato_attuale,
                       SUM(CASE WHEN f.codice_stagione = %(precedente)s THEN f.totale_fatturato ELSE 0 END) AS fatturato_precedente
                FROM analytics.clienti_fatturato_stagionale f
                JOIN clienti c ON c.codice = f.codice_cliente
                WHERE f.codice_stagione IN (%(attuale)s, %(precedente)s)
                GROUP BY c.codice, c.ragione_sociale
                HAVING SUM(CASE WHEN f.codice_stagione = %(attuale)s THEN f.totale_fatturato ELSE 0 END) > 0
                    OR SUM(CASE WHEN f.codice_stagione = %(precedente)s THEN f.totale_fatturato ELSE 0 END) > 0
                ORDER BY fatturato_attuale DESC
                """,
                {"attuale": stagione_attuale, "precedente": stagione_precedente},
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/articoli-top", method="GET")
    def analisi_clienti_articoli_top():
        codice_cliente = request.query.get("codice_cliente")
        if not codice_cliente:
            response.status = 400
            return {"error": "codice_cliente is required"}
        limit = _parse_int("limit", 5, minimum=1, maximum=20)

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(a.descrizione, fr.codice_articolo, '—') AS capo,
                       SUM(fr.capi_fatturati)::BIGINT AS capi,
                       SUM(fr.kg_fatturati) AS kg,
                       SUM(fr.importo_riga) AS importo
                FROM fatture_righe fr
                LEFT JOIN articoli a ON a.codice = fr.codice_articolo
                WHERE fr.codice_cliente = %(codice_cliente)s
                GROUP BY COALESCE(a.descrizione, fr.codice_articolo, '—')
                ORDER BY capi DESC
                LIMIT %(limit)s
                """,
                {"codice_cliente": codice_cliente, "limit": limit},
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/mono-stagione", method="GET")
    def analisi_clienti_mono_stagione():
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.codice AS codice_cliente, c.ragione_sociale,
                       s.stagioni_attive, s.fatturato_rolling_12m
                FROM analytics.clienti_snapshot s
                JOIN clienti c ON c.codice = s.codice_cliente
                WHERE cardinality(s.stagioni_attive) = 1
                ORDER BY s.fatturato_rolling_12m DESC
                """
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/produzione/lead-time", method="GET")
    def analisi_produzione_lead_time():
        tipo = request.query.get("tipo", "trend")
        codice_cliente = request.query.get("codice_cliente") or None
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            if tipo == "top":
                params = {}
                client_filter = ""
                if codice_cliente:
                    client_filter = "AND ld.codice_cliente = %(codice_cliente)s"
                    params["codice_cliente"] = codice_cliente
                cursor.execute(
                    f"""
                    SELECT ld.numero_offerta, c.ragione_sociale,
                           ld.data_entrata, ld.data_uscita, ld.lead_time_giorni
                    FROM analytics.lead_time_documenti ld
                    JOIN clienti c ON c.codice = ld.codice_cliente
                    WHERE ld.data_uscita >= CURRENT_DATE - INTERVAL '90 days'
                    {client_filter}
                    ORDER BY ld.lead_time_giorni DESC
                    LIMIT 10
                    """,
                    params,
                )
            else:
                mesi = _parse_int("mesi", 24, minimum=1, maximum=60)
                params = {"mesi": mesi}
                client_filter = ""
                if codice_cliente:
                    client_filter = "AND codice_cliente = %(codice_cliente)s"
                    params["codice_cliente"] = codice_cliente
                cursor.execute(
                    f"""
                    SELECT anno, mese,
                           ROUND(AVG(lead_time_medio), 1) AS lead_time_medio_aziendale,
                           SUM(numero_ordini) AS numero_ordini
                    FROM analytics.lead_time_mensile
                    WHERE make_date(anno, mese, 1) >= date_trunc('month', CURRENT_DATE) - (%(mesi)s || ' months')::INTERVAL
                    {client_filter}
                    GROUP BY anno, mese
                    ORDER BY anno ASC, mese ASC
                    """,
                    params,
                )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/produzione/volumi", method="GET")
    def analisi_produzione_volumi():
        granularita = request.query.get("granularita", "mensile")
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            if granularita == "settimanale":
                cursor.execute(
                    """
                    SELECT settimana_iso AS settimana, anno,
                           SUM(kg_consegnati) FILTER (WHERE anno = EXTRACT(ISOYEAR FROM CURRENT_DATE)::INTEGER) AS kg_quest_anno,
                           SUM(kg_consegnati) FILTER (WHERE anno = EXTRACT(ISOYEAR FROM CURRENT_DATE)::INTEGER - 1) AS kg_anno_scorso,
                           SUM(capi_consegnati) FILTER (WHERE anno = EXTRACT(ISOYEAR FROM CURRENT_DATE)::INTEGER) AS capi_quest_anno,
                           SUM(capi_consegnati) FILTER (WHERE anno = EXTRACT(ISOYEAR FROM CURRENT_DATE)::INTEGER - 1) AS capi_anno_scorso
                    FROM analytics.volume_giornaliero
                    WHERE anno >= EXTRACT(ISOYEAR FROM CURRENT_DATE)::INTEGER - 1
                    GROUP BY settimana_iso, anno
                    ORDER BY settimana_iso
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT EXTRACT(YEAR FROM giorno)::INTEGER AS anno,
                           EXTRACT(MONTH FROM giorno)::INTEGER AS mese,
                           SUM(kg_consegnati) AS kg_totali,
                           SUM(capi_consegnati) AS capi_totali
                    FROM analytics.volume_giornaliero
                    WHERE giorno >= CURRENT_DATE - INTERVAL '2 years'
                    GROUP BY EXTRACT(YEAR FROM giorno), EXTRACT(MONTH FROM giorno)
                    ORDER BY kg_totali DESC
                    LIMIT 12
                    """
                )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/controllo/anomalie", method="GET")
    def analisi_controllo_anomalie():
        tipo = request.query.get("tipo", "tutte")
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            data = {}

            if tipo in ("tutte", "ddt_non_fatturati"):
                cursor.execute(
                    """
                    SELECT d.codice_documento AS numero_bolla, d.codice_cliente,
                           c.ragione_sociale, d.data_bolla, d.giorni_ritardo, d.valore_stimato
                    FROM analytics.v_anomalie_ddt_non_fatturati d
                    JOIN clienti c ON c.codice = d.codice_cliente
                    ORDER BY d.giorni_ritardo DESC
                    """
                )
                data["ddt_non_fatturati"] = _rows_to_list(cursor)

            if tipo in ("tutte", "consegne_non_fatturate"):
                cursor.execute(
                    """
                    SELECT v.codice_cliente, c.ragione_sociale,
                           v.valore_stimato_non_fatturato
                    FROM analytics.v_consegne_non_fatturate_cliente v
                    JOIN clienti c ON c.codice = v.codice_cliente
                    ORDER BY v.valore_stimato_non_fatturato DESC
                    """
                )
                data["consegne_non_fatturate"] = _rows_to_list(cursor)

            if tipo in ("tutte", "fatture_senza_ddt"):
                cursor.execute(
                    """
                    SELECT f.codice_documento AS numero_disposizione, f.codice_cliente,
                           c.ragione_sociale, f.data_fattura, f.valore_stimato
                    FROM analytics.v_anomalie_fatture_senza_ddt f
                    JOIN clienti c ON c.codice = f.codice_cliente
                    ORDER BY f.valore_stimato DESC
                    """
                )
                data["fatture_senza_ddt"] = _rows_to_list(cursor)

            if tipo in ("tutte", "non_fatturato_totale"):
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(valore_stimato), 0) AS totale_sospeso
                    FROM analytics.v_anomalie_ddt_non_fatturati
                    """
                )
                row = cursor.fetchone()
                data["totale_sospeso"] = _decimal_to_float(row[0]) if row else 0

            return {"data": data}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/clienti/qualita", method="GET")
    def analisi_clienti_qualita():
        limit = _parse_int("limit", 20, minimum=1, maximum=100)
        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                WITH lt AS (
                    SELECT codice_cliente, AVG(lead_time_giorni) AS lead_time_medio
                    FROM analytics.lead_time_documenti
                    GROUP BY codice_cliente
                )
                SELECT c.codice AS codice_cliente, c.ragione_sociale,
                       s.fatturato_rolling_12m,
                       ROUND(COALESCE(lt.lead_time_medio, 0), 1) AS lead_time_medio_giorni,
                       s.intervallo_medio_giorni_corrente
                FROM analytics.clienti_snapshot s
                JOIN clienti c ON c.codice = s.codice_cliente
                LEFT JOIN lt ON lt.codice_cliente = s.codice_cliente
                WHERE s.fatturato_rolling_12m > 0
                ORDER BY s.fatturato_rolling_12m DESC, COALESCE(lt.lead_time_medio, 9999) ASC
                LIMIT %(limit)s
                """,
                {"limit": limit},
            )
            rows = _rows_to_list(cursor)
            return {"total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/opportunita/trimestre", method="GET")
    def analisi_opportunita_trimestre():
        today = date.today()
        trimestre = request.query.get("trimestre") or f"{today.year}-Q{(today.month - 1) // 3 + 1}"
        limit = _parse_int("limit", 3, minimum=1, maximum=20)

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT tipo_anomalia, codice_cliente, codice_documento,
                       valore_stimato, descrizione, giorni_ritardo, severita
                FROM analytics.anomalie_rilevate
                WHERE trimestre = %(trimestre)s
                ORDER BY severita DESC, valore_stimato DESC NULLS LAST
                LIMIT %(limit)s
                """,
                {"trimestre": trimestre, "limit": limit},
            )
            rows = _rows_to_list(cursor)
            return {"trimestre": trimestre, "total": len(rows), "data": rows}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/simulazioni/stress-test", method="POST")
    def analisi_stress_test():
        try:
            body = request.json or {}
        except Exception:
            body = {}

        top_n = int(body.get("top_n", 3))
        riduzione_pct = float(body.get("riduzione_pct", 20))
        top_n = max(min(top_n, 20), 1)
        riduzione_pct = max(min(riduzione_pct, 100), 0)
        fattore = riduzione_pct / 100.0

        conn = db_pool.get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT codice_cliente FROM analytics.clienti_snapshot
                WHERE fatturato_rolling_12m > 0
                ORDER BY fatturato_rolling_12m DESC
                LIMIT %(top_n)s
                """,
                {"top_n": top_n},
            )
            top_clienti = [row[0] for row in cursor.fetchall()]
            if not top_clienti:
                return {"data": {"perdita_totale": 0, "per_mese": [], "clienti": []}}

            cursor.execute(
                """
                SELECT anno, mese, SUM(totale_fatturato) AS fatturato
                FROM analytics.clienti_fatturato_mensile
                WHERE codice_cliente = ANY(%(clienti)s)
                  AND make_date(anno, mese, 1) >= date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
                GROUP BY anno, mese
                ORDER BY anno, mese
                """,
                {"clienti": top_clienti},
            )
            per_mese = []
            perdita_totale = 0.0
            for row in cursor.fetchall():
                fatturato = float(row[2] or 0)
                perdita = fatturato * fattore
                perdita_totale += perdita
                per_mese.append({
                    "anno": row[0],
                    "mese": row[1],
                    "fatturato_base": fatturato,
                    "perdita_stimata": round(perdita, 2),
                })

            per_mese.sort(key=lambda x: x["perdita_stimata"], reverse=True)

            cursor.execute(
                """
                SELECT c.codice, c.ragione_sociale, s.fatturato_rolling_12m
                FROM analytics.clienti_snapshot s
                JOIN clienti c ON c.codice = s.codice_cliente
                WHERE s.codice_cliente = ANY(%(clienti)s)
                ORDER BY s.fatturato_rolling_12m DESC
                """,
                {"clienti": top_clienti},
            )
            clienti = _rows_to_list(cursor)

            return {
                "data": {
                    "top_n": top_n,
                    "riduzione_pct": riduzione_pct,
                    "perdita_totale": round(perdita_totale, 2),
                    "clienti": clienti,
                    "per_mese": per_mese,
                    "mesi_piu_colpiti": per_mese[:3],
                }
            }
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
        finally:
            cursor.close()
            db_pool.release_conn(conn)

    @app.route("/api/analisi/refresh", method="POST")
    def analisi_refresh():
        """Manual analytics refresh (admin/debug). Normally run via oracle-sync."""
        from analytics import refresh_analytics_layer

        try:
            elapsed = refresh_analytics_layer(db_pool)
            return {"status": "ok", "elapsed_seconds": elapsed}
        except Exception as exc:
            response.status = 500
            return {"error": str(exc)}
