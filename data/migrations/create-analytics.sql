-- Analytics layer: materialized views, views, and support tables.
-- Idempotent: drops and recreates analytics objects (safe on local dev DB).
-- Apply on existing DB: python backend/apply_migrations.py create-analytics.sql
-- Fresh Docker init: mounted as docker-entrypoint-initdb.d/03-analytics.sql

CREATE SCHEMA IF NOT EXISTS analytics;

-- ---------------------------------------------------------------------------
-- Materialized views (refreshed after each sync)
-- ---------------------------------------------------------------------------

DROP MATERIALIZED VIEW IF EXISTS analytics.clienti_fatturato_mensile CASCADE;
CREATE MATERIALIZED VIEW analytics.clienti_fatturato_mensile AS
WITH testate AS (
    SELECT
        codice_cliente,
        numero_disposizione,
        data_fattura,
        importo_totale,
        EXTRACT(YEAR FROM data_fattura)::INTEGER AS anno,
        EXTRACT(MONTH FROM data_fattura)::INTEGER AS mese
    FROM fatture_testate
),
righe AS (
    SELECT
        codice_cliente,
        numero_disposizione,
        SUM(capi_fatturati) AS capi,
        SUM(kg_fatturati) AS kg
    FROM fatture_righe
    GROUP BY codice_cliente, numero_disposizione
)
SELECT
    t.codice_cliente,
    t.anno,
    t.mese,
    SUM(t.importo_totale) AS totale_fatturato,
    COUNT(DISTINCT t.numero_disposizione)::INTEGER AS numero_fatture,
    COALESCE(SUM(r.capi), 0)::BIGINT AS capi_fatturati,
    COALESCE(SUM(r.kg), 0) AS kg_fatturati
FROM testate t
LEFT JOIN righe r
    ON r.codice_cliente = t.codice_cliente
   AND r.numero_disposizione = t.numero_disposizione
GROUP BY t.codice_cliente, t.anno, t.mese;

CREATE UNIQUE INDEX idx_mv_fatt_mensile_pk
    ON analytics.clienti_fatturato_mensile (codice_cliente, anno, mese);
CREATE INDEX idx_mv_fatt_mensile_data
    ON analytics.clienti_fatturato_mensile (anno, mese);

DROP MATERIALIZED VIEW IF EXISTS analytics.clienti_fatturato_stagionale CASCADE;
CREATE MATERIALIZED VIEW analytics.clienti_fatturato_stagionale AS
WITH testate AS (
    SELECT
        codice_cliente,
        numero_disposizione,
        codice_stagione,
        importo_totale
    FROM fatture_testate
    WHERE codice_stagione IS NOT NULL
),
righe AS (
    SELECT
        codice_cliente,
        numero_disposizione,
        SUM(capi_fatturati) AS capi,
        SUM(kg_fatturati) AS kg
    FROM fatture_righe
    GROUP BY codice_cliente, numero_disposizione
)
SELECT
    t.codice_cliente,
    t.codice_stagione,
    SUM(t.importo_totale) AS totale_fatturato,
    COUNT(DISTINCT t.numero_disposizione)::INTEGER AS numero_fatture,
    COALESCE(SUM(r.capi), 0)::BIGINT AS capi_fatturati,
    COALESCE(SUM(r.kg), 0) AS kg_fatturati
FROM testate t
LEFT JOIN righe r
    ON r.codice_cliente = t.codice_cliente
   AND r.numero_disposizione = t.numero_disposizione
GROUP BY t.codice_cliente, t.codice_stagione;

CREATE UNIQUE INDEX idx_mv_fatt_stag_pk
    ON analytics.clienti_fatturato_stagionale (codice_cliente, codice_stagione);

DROP MATERIALIZED VIEW IF EXISTS analytics.volume_giornaliero CASCADE;
CREATE MATERIALIZED VIEW analytics.volume_giornaliero AS
SELECT
    dt.codice_cliente,
    dt.data_bolla AS giorno,
    EXTRACT(ISOYEAR FROM dt.data_bolla)::INTEGER AS anno,
    EXTRACT(WEEK FROM dt.data_bolla)::INTEGER AS settimana_iso,
    SUM(dr.kg_consegnati) AS kg_consegnati,
    SUM(dr.capi_consegnati)::BIGINT AS capi_consegnati
FROM ddt_testate dt
JOIN ddt_righe dr ON dr.numero_bolla = dt.numero_bolla
GROUP BY dt.codice_cliente, dt.data_bolla;

CREATE UNIQUE INDEX idx_mv_volume_giorno_pk
    ON analytics.volume_giornaliero (codice_cliente, giorno);
CREATE INDEX idx_mv_volume_anno_settimana
    ON analytics.volume_giornaliero (anno, settimana_iso);

DROP MATERIALIZED VIEW IF EXISTS analytics.lead_time_documenti CASCADE;
CREATE MATERIALIZED VIEW analytics.lead_time_documenti AS
SELECT
    o.numero_offerta,
    o.codice_cliente,
    o.data_offerta AS data_entrata,
    MAX(dt.data_bolla) AS data_uscita,
    (MAX(dt.data_bolla) - o.data_offerta)::INTEGER AS lead_time_giorni,
    o.codice_stagione
FROM offerte_testate o
JOIN ddt_righe dr ON dr.numero_offerta = o.numero_offerta
JOIN ddt_testate dt ON dt.numero_bolla = dr.numero_bolla
WHERE dt.data_bolla >= o.data_offerta
GROUP BY o.numero_offerta, o.codice_cliente, o.data_offerta, o.codice_stagione;

CREATE UNIQUE INDEX idx_mv_lead_time_doc_pk
    ON analytics.lead_time_documenti (numero_offerta);
CREATE INDEX idx_mv_lead_time_doc_cliente
    ON analytics.lead_time_documenti (codice_cliente);

-- Initial populate (empty tables on first init are fine)
REFRESH MATERIALIZED VIEW analytics.clienti_fatturato_mensile;
REFRESH MATERIALIZED VIEW analytics.clienti_fatturato_stagionale;
REFRESH MATERIALIZED VIEW analytics.volume_giornaliero;
REFRESH MATERIALIZED VIEW analytics.lead_time_documenti;

-- ---------------------------------------------------------------------------
-- Views (always current, read from MVs + transactional tables)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW analytics.lead_time_mensile AS
SELECT
    codice_cliente,
    EXTRACT(YEAR FROM data_uscita)::INTEGER AS anno,
    EXTRACT(MONTH FROM data_uscita)::INTEGER AS mese,
    ROUND(AVG(lead_time_giorni), 2) AS lead_time_medio,
    COUNT(*)::INTEGER AS numero_ordini
FROM analytics.lead_time_documenti
GROUP BY codice_cliente, EXTRACT(YEAR FROM data_uscita), EXTRACT(MONTH FROM data_uscita);

CREATE OR REPLACE VIEW analytics.clienti_snapshot AS
WITH mensile_12m AS (
    SELECT codice_cliente, SUM(totale_fatturato) AS fatturato_rolling_12m
    FROM analytics.clienti_fatturato_mensile
    WHERE make_date(anno, mese, 1) >= date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
    GROUP BY codice_cliente
),
totale_12m AS (
    SELECT COALESCE(SUM(fatturato_rolling_12m), 0) AS tot FROM mensile_12m
),
ordini AS (
    SELECT
        codice_cliente,
        MIN(data_offerta) AS data_primo_ordine,
        MAX(data_offerta) AS data_ultimo_ordine,
        COUNT(*) FILTER (WHERE data_offerta >= date_trunc('year', CURRENT_DATE)::date)::INTEGER AS ordini_ytd,
        AVG(importo_totale) FILTER (WHERE data_offerta >= date_trunc('year', CURRENT_DATE)::date) AS valore_medio_ordine_ytd
    FROM offerte_testate
    GROUP BY codice_cliente
),
gaps AS (
    SELECT
        codice_cliente,
        AVG(giorni) FILTER (
            WHERE data_offerta >= CURRENT_DATE - INTERVAL '12 months'
        ) AS intervallo_medio_giorni_corrente,
        AVG(giorni) FILTER (
            WHERE data_offerta >= CURRENT_DATE - INTERVAL '24 months'
              AND data_offerta < CURRENT_DATE - INTERVAL '12 months'
        ) AS intervallo_medio_giorni_prec
    FROM (
        SELECT
            codice_cliente,
            data_offerta,
            (data_offerta - LAG(data_offerta) OVER (
                PARTITION BY codice_cliente ORDER BY data_offerta
            ))::INTEGER AS giorni
        FROM offerte_testate
    ) sub
    WHERE giorni IS NOT NULL
    GROUP BY codice_cliente
),
semestre AS (
    SELECT
        codice_cliente,
        SUM(totale_fatturato) FILTER (
            WHERE anno = EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
              AND mese BETWEEN
                  CASE WHEN EXTRACT(MONTH FROM CURRENT_DATE) <= 6 THEN 1 ELSE 7 END
                  AND CASE WHEN EXTRACT(MONTH FROM CURRENT_DATE) <= 6 THEN 6 ELSE 12 END
        ) AS fatturato_semestre_corrente,
        SUM(totale_fatturato) FILTER (
            WHERE anno = EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER - 1
              AND mese BETWEEN
                  CASE WHEN EXTRACT(MONTH FROM CURRENT_DATE) <= 6 THEN 1 ELSE 7 END
                  AND CASE WHEN EXTRACT(MONTH FROM CURRENT_DATE) <= 6 THEN 6 ELSE 12 END
        ) AS fatturato_semestre_yoy
    FROM analytics.clienti_fatturato_mensile
    GROUP BY codice_cliente
),
stagioni AS (
    SELECT codice_cliente, array_agg(DISTINCT codice_stagione ORDER BY codice_stagione) AS stagioni_attive
    FROM analytics.clienti_fatturato_stagionale
    WHERE totale_fatturato > 0
    GROUP BY codice_cliente
),
ranked AS (
    SELECT
        m.codice_cliente,
        m.fatturato_rolling_12m,
        ROW_NUMBER() OVER (ORDER BY m.fatturato_rolling_12m DESC NULLS LAST) AS rank_fatturato_12m,
        CASE
            WHEN t.tot > 0 THEN ROUND(100.0 * m.fatturato_rolling_12m / t.tot, 2)
            ELSE 0
        END AS percentuale_sul_totale_12m
    FROM mensile_12m m
    CROSS JOIN totale_12m t
),
prev_12m AS (
    SELECT codice_cliente, SUM(totale_fatturato) AS fatturato_anno_precedente
    FROM analytics.clienti_fatturato_mensile
    WHERE make_date(anno, mese, 1) >= date_trunc('month', CURRENT_DATE) - INTERVAL '24 months'
      AND make_date(anno, mese, 1) < date_trunc('month', CURRENT_DATE) - INTERVAL '12 months'
    GROUP BY codice_cliente
)
SELECT
    c.codice AS codice_cliente,
    o.data_primo_ordine,
    o.data_ultimo_ordine,
    CASE WHEN o.data_ultimo_ordine IS NOT NULL
        THEN (CURRENT_DATE - o.data_ultimo_ordine)::INTEGER
        ELSE NULL
    END AS giorni_dall_ultimo_ordine,
    COALESCE(o.ordini_ytd, 0) AS ordini_ytd,
    ROUND(COALESCE(o.valore_medio_ordine_ytd, 0), 2) AS valore_medio_ordine_ytd,
    ROUND(COALESCE(g.intervallo_medio_giorni_corrente, 0), 1) AS intervallo_medio_giorni_corrente,
    ROUND(COALESCE(g.intervallo_medio_giorni_prec, 0), 1) AS intervallo_medio_giorni_prec,
    COALESCE(r.fatturato_rolling_12m, 0) AS fatturato_rolling_12m,
    COALESCE(p.fatturato_anno_precedente, 0) AS fatturato_anno_precedente,
    COALESCE(s.fatturato_semestre_corrente, 0) AS fatturato_semestre_corrente,
    COALESCE(s.fatturato_semestre_yoy, 0) AS fatturato_semestre_yoy,
    r.rank_fatturato_12m::INTEGER,
    r.percentuale_sul_totale_12m,
    (
        o.data_ultimo_ordine IS NOT NULL
        AND o.data_ultimo_ordine < CURRENT_DATE - INTERVAL '90 days'
        AND EXISTS (
            SELECT 1 FROM offerte_testate ox
            WHERE ox.codice_cliente = c.codice
              AND ox.data_offerta >= CURRENT_DATE - INTERVAL '12 months'
              AND ox.data_offerta < CURRENT_DATE - INTERVAL '90 days'
        )
    ) AS is_dormiente,
    (o.data_primo_ordine IS NOT NULL AND o.data_primo_ordine >= CURRENT_DATE - INTERVAL '12 months') AS is_nuovo_12m,
    COALESCE(st.stagioni_attive, ARRAY[]::VARCHAR[]) AS stagioni_attive
FROM clienti c
LEFT JOIN ordini o ON o.codice_cliente = c.codice
LEFT JOIN gaps g ON g.codice_cliente = c.codice
LEFT JOIN semestre s ON s.codice_cliente = c.codice
LEFT JOIN ranked r ON r.codice_cliente = c.codice
LEFT JOIN prev_12m p ON p.codice_cliente = c.codice
LEFT JOIN stagioni st ON st.codice_cliente = c.codice;

-- Structural anomalies (live views)
CREATE OR REPLACE VIEW analytics.v_anomalie_ddt_non_fatturati AS
SELECT
    d.numero_bolla AS codice_documento,
    d.codice_cliente,
    d.data_bolla,
    (CURRENT_DATE - d.data_bolla)::INTEGER AS giorni_ritardo,
    COALESCE(SUM(dr.importo_riga), 0) AS valore_stimato
FROM ddt_testate d
JOIN ddt_righe dr ON dr.numero_bolla = d.numero_bolla
WHERE CURRENT_DATE - d.data_bolla > 60
  AND NOT EXISTS (
      SELECT 1 FROM ddt_righe dr2
      WHERE dr2.numero_bolla = d.numero_bolla
        AND dr2.numero_disposizione IS NOT NULL
        AND TRIM(dr2.numero_disposizione) <> ''
  )
GROUP BY d.numero_bolla, d.codice_cliente, d.data_bolla;

CREATE OR REPLACE VIEW analytics.v_consegne_non_fatturate_cliente AS
SELECT
    dt.codice_cliente,
    SUM(dr.importo_riga) AS valore_stimato_non_fatturato
FROM ddt_righe dr
JOIN ddt_testate dt ON dt.numero_bolla = dr.numero_bolla
WHERE dr.numero_disposizione IS NULL OR TRIM(dr.numero_disposizione) = ''
GROUP BY dt.codice_cliente;

CREATE OR REPLACE VIEW analytics.v_anomalie_fatture_senza_ddt AS
SELECT
    f.codice_cliente,
    f.numero_disposizione AS codice_documento,
    f.data_fattura,
    f.importo_totale AS valore_stimato
FROM fatture_testate f
WHERE NOT EXISTS (
    SELECT 1 FROM fatture_righe fr
    WHERE fr.codice_cliente = f.codice_cliente
      AND fr.numero_disposizione = f.numero_disposizione
      AND fr.numero_bolla IS NOT NULL
      AND TRIM(fr.numero_bolla) <> ''
);

-- ---------------------------------------------------------------------------
-- Persisted table: quarterly insight summary (Q32) + price alerts (Q25)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS analytics.anomalie_rilevate (
    id                 SERIAL PRIMARY KEY,
    tipo_anomalia      VARCHAR(100) NOT NULL,
    codice_cliente     VARCHAR(50) REFERENCES clienti(codice) ON DELETE CASCADE,
    codice_documento   VARCHAR(100),
    valore_stimato     NUMERIC(12, 2) DEFAULT 0.00,
    descrizione        TEXT,
    giorni_ritardo     INTEGER,
    rilevata_il        DATE DEFAULT CURRENT_DATE,
    trimestre          VARCHAR(7) NOT NULL,
    severita           INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_anomalie_trimestre
    ON analytics.anomalie_rilevate (trimestre, severita DESC);

CREATE TABLE IF NOT EXISTS analytics.sync_meta (
    job_name           VARCHAR(100) PRIMARY KEY,
    last_success       TIMESTAMP WITH TIME ZONE,
    last_error         TEXT,
    rows_affected      INTEGER,
    elapsed_seconds    NUMERIC(8, 2)
);

INSERT INTO analytics.sync_meta (job_name)
VALUES ('rebuild_analytics')
ON CONFLICT (job_name) DO NOTHING;
