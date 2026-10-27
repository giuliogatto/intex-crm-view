-- ============================================================
-- Migration: create-c37-testata-listini.sql
-- Scopo: testate offerte/listini Oracle (Cod. Univoco = c37_prg)
-- Sorgente: INTEX2.C37_TESTATA_LISTINI
-- CSV: {timestamp}_c37_testata_listini.csv
--      (header = nomi colonna Oracle lowercase, SELECT *)
--
-- PK business = chiave a 7 campi (come Oracle PK_C37).
-- c37_prg è quasi univoco ma ha duplicati storici → solo INDEX, non PK.
-- ============================================================

CREATE TABLE IF NOT EXISTS c37_testata_listini (
    c37_cd_cliente        VARCHAR(6)   NOT NULL,
    c37_cd_linea          VARCHAR(6)   NOT NULL,
    c37_cd_stagione       VARCHAR(6)   NOT NULL,
    c37_cd_composizione   VARCHAR(6)   NOT NULL,
    c37_cd_articolo       VARCHAR(13)  NOT NULL,
    c37_cd_ciclo          VARCHAR(13)  NOT NULL,
    c37_cd_valuta         VARCHAR(3)   NOT NULL,
    c37_st_record         VARCHAR(1)   NOT NULL,
    c37_st_modifica       INTEGER      NOT NULL,
    c37_pz_tot_capo       NUMERIC,
    c37_pz_tot_kg         NUMERIC,
    c37_qt_fascia_1       NUMERIC,
    c37_tq_fascia_1       VARCHAR(1),
    c37_pz_fascia_1       NUMERIC,
    c37_tp_fascia_1       VARCHAR(1),
    c37_qt_fascia_2       NUMERIC,
    c37_tq_fascia_2       VARCHAR(1),
    c37_pz_fascia_2       NUMERIC,
    c37_tp_fascia_2       VARCHAR(1),
    c37_qt_fascia_3       NUMERIC,
    c37_tq_fascia_3       VARCHAR(1),
    c37_pz_fascia_3       NUMERIC,
    c37_tp_fascia_3       VARCHAR(1),
    c37_qt_fascia_4       NUMERIC,
    c37_tq_fascia_4       VARCHAR(1),
    c37_pz_fascia_4       NUMERIC,
    c37_tp_fascia_4       VARCHAR(1),
    c37_qt_fascia_5       NUMERIC,
    c37_tq_fascia_5       VARCHAR(1),
    c37_pz_fascia_5       NUMERIC,
    c37_tp_fascia_5       VARCHAR(1),
    c37_pz_fascia_c       NUMERIC,
    c37_tp_fascia_c       VARCHAR(1),
    c37_pz_fascia_p       NUMERIC,
    c37_tp_fascia_p       VARCHAR(1),
    c37_qt_fascia_6       NUMERIC,
    c37_tq_fascia_6       VARCHAR(1),
    c37_pz_fascia_6       NUMERIC,
    c37_tp_fascia_6       VARCHAR(1),
    c37_qt_fascia_7       NUMERIC,
    c37_tq_fascia_7       VARCHAR(1),
    c37_pz_fascia_7       NUMERIC,
    c37_tp_fascia_7       VARCHAR(1),
    c37_qt_fascia_8       NUMERIC,
    c37_tq_fascia_8       VARCHAR(1),
    c37_pz_fascia_8       NUMERIC,
    c37_tp_fascia_8       VARCHAR(1),
    c37_qt_fascia_9       NUMERIC,
    c37_tq_fascia_9       VARCHAR(1),
    c37_pz_fascia_9       NUMERIC,
    c37_tp_fascia_9       VARCHAR(1),
    c37_capi_commessa     NUMERIC,
    c37_prz_commessa      NUMERIC,
    c37_flag_visibile     VARCHAR(1)   NOT NULL,
    c37_flag_prototipo    VARCHAR(1)   NOT NULL,
    c37_note              TEXT,
    c37_referente         VARCHAR(60),
    c37_oggetto           VARCHAR(200),
    c37_cd_ciclo_cli      VARCHAR(13),
    c37_data_validita     DATE,
    c37_gruppo            VARCHAR(40),
    c37_pz_fascia_c_min   NUMERIC,
    c37_comp_print        VARCHAR(1000),
    c37_cd_tipo_centro    VARCHAR(10),
    c37_prg               INTEGER,
    c37_note_libere       TEXT,
    PRIMARY KEY (
        c37_cd_cliente,
        c37_cd_linea,
        c37_cd_stagione,
        c37_cd_composizione,
        c37_cd_articolo,
        c37_cd_ciclo,
        c37_cd_valuta
    )
);

-- Cod. Univoco (filtro UI futuro)
CREATE INDEX IF NOT EXISTS idx_c37_prg
    ON c37_testata_listini (c37_prg);

-- Join verso cicli_testate (chiave a 6 campi Z09)
CREATE INDEX IF NOT EXISTS idx_c37_ciclo_key
    ON c37_testata_listini (
        c37_cd_cliente,
        c37_cd_articolo,
        c37_cd_ciclo,
        c37_cd_linea,
        c37_cd_stagione,
        c37_cd_composizione
    );
