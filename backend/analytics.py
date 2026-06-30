"""
Post-sync analytics layer: refresh materialized views and rebuild anomalie_rilevate.
"""

import time
from datetime import date

MATERIALIZED_VIEWS = (
    "analytics.clienti_fatturato_mensile",
    "analytics.clienti_fatturato_stagionale",
    "analytics.volume_giornaliero",
    "analytics.lead_time_documenti",
)


def _current_trimestre():
    today = date.today()
    quarter = (today.month - 1) // 3 + 1
    return f"{today.year}-Q{quarter}"


def _rebuild_anomalie_rilevate(cursor):
    """Populate anomalie_rilevate from structural views + article price heuristic (Q25)."""
    trimestre = _current_trimestre()
    cursor.execute("DELETE FROM analytics.anomalie_rilevate WHERE trimestre = %s", (trimestre,))

    cursor.execute(
        """
        INSERT INTO analytics.anomalie_rilevate (
            tipo_anomalia, codice_cliente, codice_documento, valore_stimato,
            descrizione, giorni_ritardo, trimestre, severita
        )
        SELECT
            'ddt_non_fatturato_60g',
            a.codice_cliente,
            a.codice_documento,
            a.valore_stimato,
            'DDT in uscita senza fattura da più di 60 giorni',
            a.giorni_ritardo,
            %s,
            CASE
                WHEN a.giorni_ritardo > 120 THEN 5
                WHEN a.giorni_ritardo > 90 THEN 4
                ELSE 3
            END
        FROM analytics.v_anomalie_ddt_non_fatturati a
        """,
        (trimestre,),
    )

    cursor.execute(
        """
        INSERT INTO analytics.anomalie_rilevate (
            tipo_anomalia, codice_cliente, codice_documento, valore_stimato,
            descrizione, trimestre, severita
        )
        SELECT
            'fattura_senza_ddt',
            a.codice_cliente,
            a.codice_documento,
            a.valore_stimato,
            'Fattura emessa senza DDT collegato',
            %s,
            3
        FROM analytics.v_anomalie_fatture_senza_ddt a
        """,
        (trimestre,),
    )

    cursor.execute(
        """
        INSERT INTO analytics.anomalie_rilevate (
            tipo_anomalia, codice_cliente, valore_stimato,
            descrizione, trimestre, severita
        )
        SELECT
            'consegne_non_fatturate',
            v.codice_cliente,
            v.valore_stimato_non_fatturato,
            'Valore stimato consegne non ancora fatturate',
            %s,
            CASE
                WHEN v.valore_stimato_non_fatturato > 10000 THEN 5
                WHEN v.valore_stimato_non_fatturato > 5000 THEN 4
                ELSE 3
            END
        FROM analytics.v_consegne_non_fatturate_cliente v
        WHERE v.valore_stimato_non_fatturato > 0
        """,
        (trimestre,),
    )

    # Q25 reduced: article price deviation >10% vs client historical average
    cursor.execute(
        """
        INSERT INTO analytics.anomalie_rilevate (
            tipo_anomalia, codice_cliente, codice_documento, valore_stimato,
            descrizione, trimestre, severita
        )
        WITH prezzi AS (
            SELECT
                fr.codice_cliente,
                fr.codice_articolo,
                f.data_fattura,
                CASE
                    WHEN fr.capi_fatturati > 0
                    THEN fr.importo_riga / fr.capi_fatturati
                    ELSE NULL
                END AS prezzo_unitario
            FROM fatture_righe fr
            JOIN fatture_testate f
                ON f.codice_cliente = fr.codice_cliente
               AND f.numero_disposizione = fr.numero_disposizione
            WHERE fr.capi_fatturati > 0
              AND fr.importo_riga > 0
        ),
        storico AS (
            SELECT
                codice_cliente,
                codice_articolo,
                AVG(prezzo_unitario) AS prezzo_medio_storico
            FROM prezzi
            WHERE data_fattura < CURRENT_DATE - INTERVAL '3 months'
            GROUP BY codice_cliente, codice_articolo
            HAVING COUNT(*) >= 2
        ),
        recenti AS (
            SELECT
                p.codice_cliente,
                p.codice_articolo,
                AVG(p.prezzo_unitario) AS prezzo_medio_recente
            FROM prezzi p
            WHERE p.data_fattura >= CURRENT_DATE - INTERVAL '3 months'
            GROUP BY p.codice_cliente, p.codice_articolo
        )
        SELECT
            'prezzo_articolo_spostamento',
            r.codice_cliente,
            r.codice_articolo,
            ABS(r.prezzo_medio_recente - s.prezzo_medio_storico),
            'Variazione prezzo articolo >10%% rispetto allo storico cliente',
            %s,
            2
        FROM recenti r
        JOIN storico s
            ON s.codice_cliente = r.codice_cliente
           AND s.codice_articolo = r.codice_articolo
        WHERE s.prezzo_medio_storico > 0
          AND ABS(r.prezzo_medio_recente - s.prezzo_medio_storico) / s.prezzo_medio_storico > 0.10
        """,
        (trimestre,),
    )


def refresh_analytics_layer(db_pool, concurrent=False):
    """
    Refresh all analytics materialized views and rebuild anomalie_rilevate.
    REFRESH CONCURRENTLY cannot run inside a transaction; default uses
    non-concurrent refresh inside a single transaction (fine at this scale).
    """
    print("\n--- Ricostruzione Layer Analytics ---")
    start_time = time.time()
    conn = db_pool.get_conn()
    cursor = conn.cursor()

    try:
        for mv in MATERIALIZED_VIEWS:
            print(f"  Refreshing {mv}...")
            if concurrent:
                conn.commit()
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
            else:
                cursor.execute(f"REFRESH MATERIALIZED VIEW {mv}")

        print("  Rebuilding anomalie_rilevate...")
        _rebuild_anomalie_rilevate(cursor)

        elapsed = time.time() - start_time
        cursor.execute(
            """
            INSERT INTO analytics.sync_meta (job_name, last_success, last_error, elapsed_seconds)
            VALUES ('rebuild_analytics', NOW(), NULL, %s)
            ON CONFLICT (job_name) DO UPDATE SET
                last_success = EXCLUDED.last_success,
                last_error = NULL,
                elapsed_seconds = EXCLUDED.elapsed_seconds
            """,
            (elapsed,),
        )
        conn.commit()
        print(f"  Analytics refresh completed in {elapsed:.2f}s.")
        return elapsed
    except Exception as exc:
        conn.rollback()
        try:
            cursor.execute(
                """
                INSERT INTO analytics.sync_meta (job_name, last_error)
                VALUES ('rebuild_analytics', %s)
                ON CONFLICT (job_name) DO UPDATE SET last_error = EXCLUDED.last_error
                """,
                (str(exc),),
            )
            conn.commit()
        except Exception:
            conn.rollback()
        print(f"  Analytics refresh failed: {exc}")
        raise
    finally:
        cursor.close()
        db_pool.release_conn(conn)
