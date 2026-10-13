-- ============================================================
-- Migration: cicli-storico-search.sql
-- Scopo: indici, token storico, dizionario sinonimi, documento
--        di ricerca fasi per i nuovi filtri pagina Cicli.
-- Prerequisiti: create-cicli-tables.sql, create-storico-disposizioni-tables.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Wrapper IMMUTABLE di unaccent (necessario per indici / generated)
CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE STRICT
AS $$
  SELECT public.unaccent('public.unaccent', $1)
$$;

-- Normalizzazione testo ricerca fasi / descrizioni / note
CREATE OR REPLACE FUNCTION public.norm_search(input text)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE PARALLEL SAFE
AS $$
DECLARE
  t text;
BEGIN
  IF input IS NULL OR btrim(input) = '' THEN
    RETURN '';
  END IF;
  t := upper(public.immutable_unaccent(input));
  -- 40? -> 40° (encoding perso tipico export)
  t := regexp_replace(t, '([0-9])\?', '\1°', 'g');
  -- separatori tipici cicli/fasi -> spazio
  t := regexp_replace(t, '[+/().,;:\-]+', ' ', 'g');
  t := regexp_replace(t, '\s+', ' ', 'g');
  RETURN btrim(t);
END;
$$;

-- ---------------------------------------------------------------------------
-- Indici cicli
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_cicli_testate_data_ins
    ON cicli_testate (data_ins DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_cicli_testate_note_trgm
    ON cicli_testate USING gin (note gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_cicli_fasi_note_trgm
    ON cicli_fasi USING gin (note gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_fasi_lavoro_ds_trgm
    ON fasi_lavoro USING gin (ds_fase gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- Indici / colonne token storico (EW2)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_ew2_ciclo_key ON ew2_righe_disposizioni (
    ew2_cd_cliente,
    ew2_cd_articolo_fattura,
    ew2_cd_ciclo,
    ew2_cd_linea,
    ew2_cd_stagione,
    ew2_cd_composizione
);

CREATE INDEX IF NOT EXISTS idx_ew2_ds_colore_trgm
    ON ew2_righe_disposizioni USING gin (ew2_ds_colore gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_ew2_modello_trgm
    ON ew2_righe_disposizioni USING gin (ew2_modello gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_ew2_ds_art_trgm
    ON ew2_righe_disposizioni USING gin (ew2_ds_articolo gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_ew2_art_fiscale
    ON ew2_righe_disposizioni (ew2_cd_articolo_fiscale);

CREATE INDEX IF NOT EXISTS idx_ew2_qualita
    ON ew2_righe_disposizioni (ew2_qualita);

CREATE INDEX IF NOT EXISTS idx_ew2_note_trgm
    ON ew2_righe_disposizioni USING gin (ew2_note gin_trgm_ops);

-- Token commessa (RIF. DISP. CLIENTE)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'ew2_righe_disposizioni' AND column_name = 'ew2_rif_tokens'
  ) THEN
    ALTER TABLE ew2_righe_disposizioni
      ADD COLUMN ew2_rif_tokens text[]
      GENERATED ALWAYS AS (
        regexp_split_to_array(
          upper(COALESCE(ew2_rif_disp_cliente, '')),
          '[/\s,;\-]+'
        )
      ) STORED;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_ew2_rif_tokens
    ON ew2_righe_disposizioni USING gin (ew2_rif_tokens);

-- Token tessuto: qualita + ds_articolo + cd_colore + note
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'ew2_righe_disposizioni' AND column_name = 'ew2_tessuto_tokens'
  ) THEN
    ALTER TABLE ew2_righe_disposizioni
      ADD COLUMN ew2_tessuto_tokens text[]
      GENERATED ALWAYS AS (
        regexp_split_to_array(
          upper(
            COALESCE(ew2_qualita, '') || ' ' ||
            COALESCE(ew2_ds_articolo, '') || ' ' ||
            COALESCE(ew2_cd_colore, '') || ' ' ||
            COALESCE(ew2_note, '')
          ),
          '[/\s,;\-%]+'
        )
      ) STORED;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_ew2_tessuto_tokens
    ON ew2_righe_disposizioni USING gin (ew2_tessuto_tokens);

CREATE INDEX IF NOT EXISTS idx_ew1_rifer_cliente
    ON ew1_testata_disposizioni (ew1_rifer_cliente);

-- ---------------------------------------------------------------------------
-- Dizionario sinonimi / abbreviazioni fasi
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ricerca_sinonimi (
    gruppo   VARCHAR(50)  NOT NULL,
    termine  VARCHAR(50)  NOT NULL,
    PRIMARY KEY (gruppo, termine)
);

INSERT INTO ricerca_sinonimi (gruppo, termine) VALUES
  ('TINTURA', 'TINTURA'), ('TINTURA', 'TINTO'), ('TINTURA', 'TI'), ('TINTURA', 'T'),
  ('REATTIVO', 'REATTIVO'), ('REATTIVO', 'REATTIVA'), ('REATTIVO', 'REATT'), ('REATTIVO', 'TIR'),
  ('MANGIAPELO', 'MANGIAPELO'), ('MANGIAPELO', 'MPELO'), ('MANGIAPELO', 'M PELO'),
  ('ENZIMA', 'ENZIMA'), ('ENZIMA', 'ENZIMI'), ('ENZIMA', 'ENZ'),
  ('POMICE', 'POMICE'), ('POMICE', 'POM'),
  ('PERLITE', 'PERLITE'), ('PERLITE', 'PERL'),
  ('STONE WASH', 'STONE WASH'), ('STONE WASH', 'STONE'), ('STONE WASH', 'STW'), ('STONE WASH', 'SW'),
  ('SBOZZIMA', 'SBOZZIMA'), ('SBOZZIMA', 'SBOZZ'), ('SBOZZIMA', 'SBZ'),
  ('CANDEGGIO', 'CANDEGGIO'), ('CANDEGGIO', 'BLEACH'), ('CANDEGGIO', 'BLEACHED'), ('CANDEGGIO', 'SBIANCA'),
  ('CARTEGGIO', 'CARTEGGIO'), ('CARTEGGIO', 'CART'),
  ('LAVAGGIO', 'LAVAGGIO'), ('LAVAGGIO', 'LAV'), ('LAVAGGIO', 'LAVATO'),
  ('TRATTAMENTO', 'TRATTAMENTO'), ('TRATTAMENTO', 'TRATT'), ('TRATTAMENTO', 'TR'),
  ('PIGMENTO', 'PIGMENTO'), ('PIGMENTO', 'PIG'),
  ('SWEET', 'SWEET'), ('SWEET', 'SWE'),
  ('ROTTURE', 'ROTTURE'), ('ROTTURE', 'ROTT'),
  ('SPRUZZO', 'SPRUZZO'), ('SPRUZZO', 'SPR'),
  ('DEGRADE', 'DEGRADE'),
  ('STROPICCIO', 'STROPICCIO'), ('STROPICCIO', 'STROP'),
  ('PURGA', 'PURGA'),
  ('BAFFI', 'BAFFI'),
  ('USED', 'USED'), ('USED', 'DIRTY'), ('USED', 'OLD'),
  ('STRETCH', 'STRETCH'), ('STRETCH', 'STR'),
  ('MARMO', 'MARMO'),
  ('ASC APPESA', 'ASC APPESA'), ('ASC APPESA', 'ASC.APPESA'),
  ('RETE', 'RETE'), ('RETE', 'S RETE'), ('RETE', 'SRETE')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Documento di ricerca per ciclo (tabella, refreshabile dopo import)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cicli_search (
    codice_cliente       VARCHAR(50)  NOT NULL,
    codice_articolo      VARCHAR(100) NOT NULL,
    codice_ciclo         VARCHAR(100) NOT NULL,
    codice_linea         VARCHAR(50)  NOT NULL,
    codice_stagione      VARCHAR(50)  NOT NULL,
    codice_composizione  VARCHAR(50)  NOT NULL,
    search_doc           TEXT,
    PRIMARY KEY (
        codice_cliente,
        codice_articolo,
        codice_ciclo,
        codice_linea,
        codice_stagione,
        codice_composizione
    )
);

CREATE INDEX IF NOT EXISTS idx_cicli_search_trgm
    ON cicli_search USING gin (search_doc gin_trgm_ops);

-- Funzione di refresh (da chiamare dopo import CSV cicli)
CREATE OR REPLACE FUNCTION public.refresh_cicli_search()
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
  n integer;
BEGIN
  TRUNCATE cicli_search;
  INSERT INTO cicli_search (
    codice_cliente, codice_articolo, codice_ciclo,
    codice_linea, codice_stagione, codice_composizione,
    search_doc
  )
  SELECT
    t.codice_cliente,
    t.codice_articolo,
    t.codice_ciclo,
    t.codice_linea,
    t.codice_stagione,
    t.codice_composizione,
    public.norm_search(
      concat_ws(
        ' ',
        t.ds_ciclo,
        t.ds_ciclo_bolle_fat,
        t.note,
        string_agg(concat_ws(' ', z.ds_fase, f.note), ' ' ORDER BY f.sequenza)
      )
    )
  FROM cicli_testate t
  LEFT JOIN cicli_fasi f
    ON f.codice_cliente = t.codice_cliente
   AND f.codice_articolo = t.codice_articolo
   AND f.codice_ciclo = t.codice_ciclo
   AND f.codice_linea = t.codice_linea
   AND f.codice_stagione = t.codice_stagione
   AND f.codice_composizione = t.codice_composizione
  LEFT JOIN fasi_lavoro z ON z.codice_fase = f.codice_fase
  GROUP BY
    t.codice_cliente, t.codice_articolo, t.codice_ciclo,
    t.codice_linea, t.codice_stagione, t.codice_composizione,
    t.ds_ciclo, t.ds_ciclo_bolle_fat, t.note;

  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END;
$$;
