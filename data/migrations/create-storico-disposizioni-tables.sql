-- ============================================================
-- Migration: create-storico-disposizioni-tables.sql
-- Scopo: tabelle per Storico Disposizioni Completo (export CSV Oracle)
-- Sorgenti: scripts/extract_upload_tables_storico.py
--   → /var/data_imports/intex/{timestamp}_*.csv
--
-- File CSV corrispondenti (header = nomi colonna Oracle, case-insensitive):
--   *_storico_disposizioni.csv      → storico_disposizioni
--   *_ew1_testata_disposizioni.csv  → ew1_testata_disposizioni
--   *_ew2_righe_disposizioni.csv    → ew2_righe_disposizioni
--
-- Container DB: data-timescaledb-intex-1 (postgres / postgres)
-- ============================================================

-- ---------------------------------------------------------------------------
-- EW1 — testate disposizioni
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ew1_testata_disposizioni (
    ew1_anno_disposizione   INTEGER      NOT NULL,
    ew1_nr_disposizione     INTEGER      NOT NULL,
    ew1_st_record           VARCHAR(1),
    ew1_st_modifica         INTEGER,
    ew1_data_immissione     TIMESTAMP,
    ew1_data_bolla_cli      DATE,
    ew1_nr_bolla_cli        VARCHAR(20),
    ew1_cd_cliente          VARCHAR(6),
    ew1_rifer_cliente       VARCHAR(30),
    ew1_cd_linea            VARCHAR(6),
    ew1_cd_stagione         VARCHAR(6),
    ew1_flag_chiuso         VARCHAR(1),
    ew1_cd_provenienza      VARCHAR(13),
    ew1_flag_mail           VARCHAR(1),
    ew1_flag_esente         VARCHAR(1),
    PRIMARY KEY (ew1_anno_disposizione, ew1_nr_disposizione)
);

-- ---------------------------------------------------------------------------
-- EW2 — righe disposizioni
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ew2_righe_disposizioni (
    ew2_anno_disposizione         INTEGER        NOT NULL,
    ew2_nr_disposizione           INTEGER        NOT NULL,
    ew2_riga_disposizione         INTEGER        NOT NULL,
    ew2_st_record                 VARCHAR(1),
    ew2_st_modifica               INTEGER,
    ew2_nr_capi_caricati          NUMERIC(9),
    ew2_kg_caricati               NUMERIC(15, 3),
    ew2_scatola                   VARCHAR(20),
    ew2_ds_articolo               VARCHAR(40),
    ew2_cd_articolo_fiscale       VARCHAR(13),
    ew2_cd_articolo_fattura       VARCHAR(13),
    ew2_cd_composizione           VARCHAR(6),
    ew2_cd_ciclo                  VARCHAR(13),
    ew2_cd_cartella               VARCHAR(10),
    ew2_cd_colore                 VARCHAR(10),
    ew2_ds_colore                 VARCHAR(40),
    ew2_rif_disp_cliente          VARCHAR(40),
    ew2_note                      VARCHAR(200),
    ew2_note_ricetta              VARCHAR(60),
    ew2_flag_stampa_note          VARCHAR(1),
    ew2_cd_vasca                  VARCHAR(13),
    ew2_serie_vasca               INTEGER,
    ew2_cd_provenienza            VARCHAR(13),
    ew2_cd_destinazione           VARCHAR(13),
    ew2_nr_camp_nuovi_col         NUMERIC(15, 3),
    ew2_flag_bolle_aperte         VARCHAR(1),
    ew2_qualita                   VARCHAR(20),
    ew2_modello                   VARCHAR(20),
    ew2_nr_cotta                  NUMERIC(13),
    ew2_data_cons_richiesta       DATE,
    ew2_anno_cons_richiesta       INTEGER,
    ew2_sett_cons_richiesta       INTEGER,
    ew2_data_cons_confermata      DATE,
    ew2_anno_cons_confermata      INTEGER,
    ew2_sett_cons_confermata      INTEGER,
    ew2_flag_stato                VARCHAR(1),
    ew2_nr_ripreso                INTEGER,
    ew2_flag_stampa_entrate       VARCHAR(1),
    ew2_def_colore                VARCHAR(12),
    ew2_cd_reparto                VARCHAR(6),
    ew2_cd_raggrupp_vasche        VARCHAR(6),
    ew2_flag_chiuso               VARCHAR(1),
    ew2_cd_cliente                VARCHAR(6),
    ew2_nr_capi_ddt               NUMERIC(9),
    ew2_kg_ddt                    NUMERIC(15, 3),
    ew2_flag_tp_prod              VARCHAR(1),
    ew2_flag_tp_ddt               VARCHAR(1),
    ew2_cd_linea                  VARCHAR(6),
    ew2_cd_stagione               VARCHAR(6),
    ew2_rif_addebito_capi_mancanti VARCHAR(60),
    ew2_ammanco                   NUMERIC(9),
    ew2_cd_ricetta                VARCHAR(6),
    ew2_flag_tipo_ricetta         VARCHAR(1),
    ew2_nr_capi_prod              NUMERIC(9),
    ew2_kg_prod                   NUMERIC(11, 2),
    ew2_flag_laboratorio          VARCHAR(1),
    ew2_nr_colori_ddt             NUMERIC(9),
    ew2_nr_sacchi                 NUMERIC(9),
    ew2_cd_sconto_maggioraz       VARCHAR(6),
    ew2_stato_ricetta             VARCHAR(20),
    ew2_cd_ciclo_cli              VARCHAR(13),
    ew2_cd_stagione_prod          VARCHAR(6),
    ew2_prz_unitario              NUMERIC(17, 5),
    ew2_flag_tipo_prezzo          VARCHAR(1),
    ew2_prz_unitario_kg           NUMERIC(17, 5),
    ew2_flag_tipo_prezzo_kg       VARCHAR(1),
    PRIMARY KEY (
        ew2_anno_disposizione,
        ew2_nr_disposizione,
        ew2_riga_disposizione
    )
);

-- ---------------------------------------------------------------------------
-- STORICO — vista denormalizzata (griglia UI)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS storico_disposizioni (
    ew2_cd_articolo_fiscale   VARCHAR(13),
    cw1_ds_articolo_fi        VARCHAR(40),
    ew2_cd_colore             VARCHAR(10),
    ew2_cd_cartella           VARCHAR(10),
    ew2_ds_colore             VARCHAR(40),
    g31_ds_colore             VARCHAR(40),
    ew2_cd_ciclo              VARCHAR(13),
    z09_ds_ciclo              VARCHAR(40),
    ew2_cd_composizione       VARCHAR(6),
    cw4_ds_composizione       VARCHAR(60),
    ew1_data_bolla_cli        DATE,
    ew1_nr_bolla_cli          VARCHAR(20),
    ew1_cd_linea              VARCHAR(6),
    ew1_cd_cliente            VARCHAR(6),
    r07_ragione_soc           VARCHAR(40),
    ew2_anno_disposizione     INTEGER      NOT NULL,
    ew2_nr_disposizione       INTEGER      NOT NULL,
    ew2_riga_disposizione     INTEGER      NOT NULL,
    ew2_nr_capi_caricati      NUMERIC(9),
    ew2_kg_caricati           NUMERIC(15, 3),
    ew2_scatola               VARCHAR(20),
    ew2_ds_articolo           VARCHAR(40),
    ew2_rif_disp_cliente      VARCHAR(40),
    ew2_note                  VARCHAR(60),
    ew2_note_ricetta          VARCHAR(60),
    ew2_cd_provenienza        VARCHAR(13),
    cw8_ragione_soc_prov      VARCHAR(40),
    ew2_cd_destinazione       VARCHAR(13),
    cw8_ragione_soc_dest      VARCHAR(40),
    ew2_nr_camp_nuovi_col     NUMERIC(15, 3),
    ew2_flag_bolle_aperte     VARCHAR(1),
    ew2_qualita               VARCHAR(20),
    ew2_modello               VARCHAR(20),
    ew2_nr_cotta              NUMERIC(13),
    ew2_nr_ripreso            INTEGER,
    capievasi                 NUMERIC,
    kgevasi                   NUMERIC,
    capilavorati              NUMERIC,
    kglavorati                NUMERIC,
    capinonlavorati           NUMERIC,
    kgnonlavorati             NUMERIC,
    cw0_ds_linea              VARCHAR(40),
    bolle                     TEXT,
    ew2_flag_tp_prod          VARCHAR(1),
    ew2_flag_tp_prod_desc     VARCHAR(11),
    ew2_flag_chiuso           VARCHAR(1),
    p07_flag_ripreso          VARCHAR(2),
    fornitori                 TEXT,
    cartellini                VARCHAR(200),
    z09_cd_reparto_stat       VARCHAR(6),
    z01_ds_reparto            VARCHAR(40),
    vasche                    VARCHAR(200),
    cd_ciclo_cli              VARCHAR(13),
    ew2_cd_stagione           VARCHAR(6),
    z11_ds_stagione           VARCHAR(40),
    ew2_cd_stagione_prod      VARCHAR(6),
    ds_stagione_prod          VARCHAR(40),
    lista_fasi_extra          TEXT,
    ew2_flag_tp_ddt           VARCHAR(1),
    PRIMARY KEY (
        ew2_anno_disposizione,
        ew2_nr_disposizione,
        ew2_riga_disposizione
    )
);

-- Indici filtri UI / ricerca
CREATE INDEX IF NOT EXISTS idx_ew1_cliente
    ON ew1_testata_disposizioni (ew1_cd_cliente);

CREATE INDEX IF NOT EXISTS idx_ew1_data_bolla
    ON ew1_testata_disposizioni (ew1_data_bolla_cli);

CREATE INDEX IF NOT EXISTS idx_ew2_cliente
    ON ew2_righe_disposizioni (ew2_cd_cliente);

CREATE INDEX IF NOT EXISTS idx_ew2_ciclo
    ON ew2_righe_disposizioni (ew2_cd_ciclo);

CREATE INDEX IF NOT EXISTS idx_ew2_cartella
    ON ew2_righe_disposizioni (ew2_cd_cartella);

CREATE INDEX IF NOT EXISTS idx_ew2_colore
    ON ew2_righe_disposizioni (ew2_cd_colore);

CREATE INDEX IF NOT EXISTS idx_ew2_composizione
    ON ew2_righe_disposizioni (ew2_cd_composizione);

CREATE INDEX IF NOT EXISTS idx_ew2_tp_prod
    ON ew2_righe_disposizioni (ew2_flag_tp_prod);

CREATE INDEX IF NOT EXISTS idx_ew2_tp_ddt
    ON ew2_righe_disposizioni (ew2_flag_tp_ddt);

CREATE INDEX IF NOT EXISTS idx_storico_cliente
    ON storico_disposizioni (ew1_cd_cliente);

CREATE INDEX IF NOT EXISTS idx_storico_data_bolla
    ON storico_disposizioni (ew1_data_bolla_cli);

CREATE INDEX IF NOT EXISTS idx_storico_ciclo
    ON storico_disposizioni (ew2_cd_ciclo);

CREATE INDEX IF NOT EXISTS idx_storico_cartella
    ON storico_disposizioni (ew2_cd_cartella);

CREATE INDEX IF NOT EXISTS idx_storico_colore
    ON storico_disposizioni (ew2_cd_colore);

CREATE INDEX IF NOT EXISTS idx_storico_composizione
    ON storico_disposizioni (ew2_cd_composizione);

CREATE INDEX IF NOT EXISTS idx_storico_tp_prod
    ON storico_disposizioni (ew2_flag_tp_prod);

CREATE INDEX IF NOT EXISTS idx_storico_tp_ddt
    ON storico_disposizioni (ew2_flag_tp_ddt);

CREATE INDEX IF NOT EXISTS idx_storico_ripreso
    ON storico_disposizioni (p07_flag_ripreso);

CREATE INDEX IF NOT EXISTS idx_storico_rif_disp
    ON storico_disposizioni (ew2_rif_disp_cliente);
