-- ============================================================
-- Migration: create-ddt-prezzi-003w.sql
-- Scopo: snapshot giornaliero della view Oracle
--        INTEX2.DDT_PREZZI_003W (DDT non fatturati + prezzi calcolati)
-- CSV: {timestamp}_ddt_prezzi_003w.csv  (SELECT *, header lowercase)
-- Pipeline: extract_upload_tables_storico_365.py
--           → import_storico_disposizioni.sh
--
-- Nota: non è una tabella Oracle; è una view non materializzata.
--       Candidata del report Wash "Lista Controllo Prezzi Mancanti"
--       (ha stagione listino + stagione produzione). Filtrare i
--       prezzi a 0 lato applicazione, non in export.
-- ============================================================

CREATE TABLE IF NOT EXISTS ddt_prezzi_003w (
    d02_key                          TEXT,
    d02_cd_tipo_bolla                TEXT,
    i01_cd_tipo_documento            TEXT,
    d02_anno_bolla                   NUMERIC,
    d02_nr_bolla                     NUMERIC,
    d02_dt_bolla                     DATE,
    d02_cd_cliente_fatt              TEXT,
    r07_ragione_soc                  TEXT,
    r07_cd_pagamento                 TEXT,
    r06_ds_pagamento                 TEXT,
    r07_cd_abi                       TEXT,
    r07_cd_cab                       TEXT,
    c06_denominazione_banca          TEXT,
    c06_agenzia                      TEXT,
    d02_cd_ass_fisc                  TEXT,
    c01_ds_iva                       TEXT,
    d02_cd_valuta                    TEXT,
    d02_flag_fatturata               TEXT,
    d03_riga                         NUMERIC,
    d03_anno_disp_cli                NUMERIC,
    d03_nr_disp_cli                  NUMERIC,
    d03_riga_disp_cli                NUMERIC,
    d03_capi_in_uscita               NUMERIC,
    d03_kg_in_uscita                 NUMERIC,
    d03_cd_iva                       TEXT,
    c01_perc_imponibile              NUMERIC,
    d03_sconto_01                    NUMERIC,
    d03_sconto_02                    NUMERIC,
    d03_provv_agente                 NUMERIC,
    d03_provv_agente_2               NUMERIC,
    d03_provv_agente_3               NUMERIC,
    d03_provv_agente_4               NUMERIC,
    d03_cd_articolo                  TEXT,
    d03_ds_articolo                  TEXT,
    d03_cd_unita_mis                 TEXT,
    g04_ds_unita_mis                 TEXT,
    d03_qta_in_uscita                NUMERIC,
    ew2_cd_linea                     TEXT,
    cw0_ds_linea                     TEXT,
    ew2_cd_stagione                  TEXT,
    z11_ds_stagione                  TEXT,
    ew2_cd_cliente                   TEXT,
    ew2_cd_articolo_fattura          TEXT,
    cwa_ds_articolo_cliente          TEXT,
    ew2_cd_composizione              TEXT,
    cw4_ds_composizione              TEXT,
    ew2_cd_ciclo                     TEXT,
    z09_ds_ciclo                     TEXT,
    z09_fl_fatturare                 TEXT,
    z09_fl_prezzo_zero               TEXT,
    ew2_flag_tp_prod                 TEXT,
    ew2_nr_capi_caricati             NUMERIC,
    ew2_kg_caricati                  NUMERIC,
    d03_prezzo_uni                   NUMERIC,
    d03_prezzo_capo                  NUMERIC,
    d03_prezzo_kg                    NUMERIC,
    d03_prezzo_forfait               NUMERIC,
    d03_note                         TEXT,
    d03_flag_prezzo_forfait          TEXT,
    tipo                             TEXT,
    d03_prezzo_colore                NUMERIC,
    d03_colori_in_uscita             NUMERIC,
    d03_anno_cartellino              NUMERIC,
    d03_nr_cartellino                NUMERIC,
    p07_nr_bagno                     NUMERIC,
    d03_prezzo_forfait_kg            NUMERIC,
    d03_prezzo_forfait_nr            NUMERIC,
    capiusare                        NUMERIC,
    p07_kg_programmati               NUMERIC,
    p07_nr_capi_programmati          NUMERIC,
    cw4_cd_gruppo_composizione       TEXT,
    p06_flag_usakginricercaprezzi    TEXT,
    codiceraggruppamento             TEXT,
    d02_cd_agente                    TEXT,
    d02_cd_agente_2                  TEXT,
    d02_cd_agente_3                  TEXT,
    d02_cd_agente_4                  TEXT,
    d02_cd_abi                       TEXT,
    d02_cd_cab                       TEXT,
    d02_cd_pagamento                 TEXT,
    ew2_cd_stagione_prod             TEXT,
    ds_stagione_prod                 TEXT,
    ew2_ds_articolo                  TEXT
);

CREATE INDEX IF NOT EXISTS idx_ddt_prezzi_003w_dt_bolla
    ON ddt_prezzi_003w (d02_dt_bolla);

CREATE INDEX IF NOT EXISTS idx_ddt_prezzi_003w_cliente
    ON ddt_prezzi_003w (d02_cd_cliente_fatt);

CREATE INDEX IF NOT EXISTS idx_ddt_prezzi_003w_prezzi
    ON ddt_prezzi_003w (d03_prezzo_capo, d03_prezzo_kg, d03_prezzo_forfait);
