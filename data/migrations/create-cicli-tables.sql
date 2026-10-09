-- ============================================================
-- Migration: create-cicli-tables.sql
-- Scopo: tabelle per ricerca cicli di lavorazione (export CSV Oracle)
-- Sorgenti: scripts/export_cicli_tables.txt → csv/*.csv
--
-- File CSV corrispondenti:
--   z09_cicli_testate.csv      → cicli_testate
--   z08_cicli_fasi.csv         → cicli_fasi
--   z02_fasi.csv               → fasi_lavoro
--   r07_clienti.csv            → cicli_clienti
--   z11_stagioni.csv           → cicli_stagioni
--   cw4_composizioni.csv       → composizioni
--   cwa_articoli_cliente.csv   → articoli_cliente
--   cw0_linee.csv              → linee_tintoria
--
-- Nota: tabelle dedicate (non riusano clienti/stagioni/articoli gia'
-- sincronizzati da ORDS) perche' le chiavi/semantica Z09/CWA/CW4
-- non coincidono con CW1/F07.
-- ============================================================

-- Anagrafiche filtri / decodifiche
CREATE TABLE IF NOT EXISTS cicli_clienti (
    codice_cliente   VARCHAR(50)  PRIMARY KEY,
    ragione_sociale  VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS cicli_stagioni (
    codice_stagione  VARCHAR(50)  PRIMARY KEY,
    ds_stagione      VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS composizioni (
    codice_composizione  VARCHAR(50)  PRIMARY KEY,
    ds_composizione      VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS articoli_cliente (
    codice_cliente    VARCHAR(50)  NOT NULL,
    codice_articolo   VARCHAR(100) NOT NULL,
    ds_articolo       VARCHAR(255),
    PRIMARY KEY (codice_cliente, codice_articolo)
);

CREATE TABLE IF NOT EXISTS linee_tintoria (
    codice_cliente  VARCHAR(50)  NOT NULL,
    codice_linea    VARCHAR(50)  NOT NULL,
    ds_linea        VARCHAR(255),
    PRIMARY KEY (codice_cliente, codice_linea)
);

CREATE TABLE IF NOT EXISTS fasi_lavoro (
    codice_fase  VARCHAR(50)  PRIMARY KEY,
    ds_fase      VARCHAR(255)
);

-- Testate ciclo (chiave Oracle a 6 campi)
CREATE TABLE IF NOT EXISTS cicli_testate (
    codice_cliente       VARCHAR(50)  NOT NULL,
    codice_articolo      VARCHAR(100) NOT NULL,
    codice_ciclo         VARCHAR(100) NOT NULL,
    codice_ciclo_cli     VARCHAR(100),
    codice_linea         VARCHAR(50)  NOT NULL,
    codice_stagione      VARCHAR(50)  NOT NULL,
    codice_composizione  VARCHAR(50)  NOT NULL,
    st_record            VARCHAR(1),
    ds_ciclo             VARCHAR(255),
    ds_ciclo_bolle_fat   VARCHAR(500),
    ds_applicazione      VARCHAR(100),
    ds_ricamo            VARCHAR(100),
    ds_stampa            VARCHAR(100),
    note                 TEXT,
    codice_reparto       VARCHAR(50),
    codice_gruppo        VARCHAR(50),
    nr_revisione         INTEGER,
    perc_fallosita       NUMERIC(10, 4),
    data_ins             DATE,
    data_validita        DATE,
    flag_visibile        VARCHAR(1),
    flag_prototipo       VARCHAR(1),
    utente_inserimento   VARCHAR(50),
    PRIMARY KEY (
        codice_cliente,
        codice_articolo,
        codice_ciclo,
        codice_linea,
        codice_stagione,
        codice_composizione
    )
);

-- Fasi del ciclo (stessa chiave a 6 campi + sequenza)
CREATE TABLE IF NOT EXISTS cicli_fasi (
    codice_cliente       VARCHAR(50)  NOT NULL,
    codice_articolo      VARCHAR(100) NOT NULL,
    codice_ciclo         VARCHAR(100) NOT NULL,
    codice_linea         VARCHAR(50)  NOT NULL,
    codice_stagione      VARCHAR(50)  NOT NULL,
    codice_composizione  VARCHAR(50)  NOT NULL,
    sequenza             INTEGER      NOT NULL,
    codice_fase          VARCHAR(50),
    codice_macrofase     VARCHAR(50),
    codice_unita_mis     VARCHAR(50),
    note                 TEXT,
    st_record            VARCHAR(1),
    PRIMARY KEY (
        codice_cliente,
        codice_articolo,
        codice_ciclo,
        codice_linea,
        codice_stagione,
        codice_composizione,
        sequenza
    )
);

-- Indici per filtri di ricerca
CREATE INDEX IF NOT EXISTS idx_cicli_testate_cliente
    ON cicli_testate (codice_cliente);

CREATE INDEX IF NOT EXISTS idx_cicli_testate_stagione
    ON cicli_testate (codice_stagione);

CREATE INDEX IF NOT EXISTS idx_cicli_testate_composizione
    ON cicli_testate (codice_composizione);

CREATE INDEX IF NOT EXISTS idx_cicli_testate_articolo
    ON cicli_testate (codice_cliente, codice_articolo);

CREATE INDEX IF NOT EXISTS idx_cicli_testate_ciclo
    ON cicli_testate (codice_ciclo);

CREATE INDEX IF NOT EXISTS idx_cicli_testate_ds_ciclo
    ON cicli_testate (ds_ciclo);

CREATE INDEX IF NOT EXISTS idx_cicli_fasi_fase
    ON cicli_fasi (codice_fase);

CREATE INDEX IF NOT EXISTS idx_cicli_fasi_ciclo
    ON cicli_fasi (
        codice_cliente,
        codice_articolo,
        codice_ciclo,
        codice_linea,
        codice_stagione,
        codice_composizione
    );

CREATE INDEX IF NOT EXISTS idx_articoli_cliente_ds
    ON articoli_cliente (ds_articolo);

CREATE INDEX IF NOT EXISTS idx_cicli_clienti_ragione
    ON cicli_clienti (ragione_sociale);

CREATE INDEX IF NOT EXISTS idx_composizioni_ds
    ON composizioni (ds_composizione);
