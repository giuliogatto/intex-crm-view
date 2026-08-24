-- ============================================================
-- Migration: add-lavorazione-fields.sql
-- Scopo: aggiunge i campi necessari per l'Assistente DDT (Punto 1)
--   - cd_lavorazione / ds_lavorazione: tipo di lavorazione (da F07_003W)
--   - prezzo_un_capi / prezzo_un_kg: prezzi disaggregati per unità e kg
-- + indici GIN pg_trgm per ricerca fuzzy su offerte_righe
-- ============================================================

-- 1. Estendi fatture_righe con i nuovi campi
ALTER TABLE fatture_righe
    ADD COLUMN IF NOT EXISTS cd_lavorazione  VARCHAR(50),
    ADD COLUMN IF NOT EXISTS ds_lavorazione  VARCHAR(255),
    ADD COLUMN IF NOT EXISTS prezzo_un_capi  NUMERIC(10,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS prezzo_un_kg    NUMERIC(10,4) NOT NULL DEFAULT 0;

-- Indice per ricerche per tipo lavorazione (assistente DDT + analytics)
CREATE INDEX IF NOT EXISTS idx_fatture_righe_lavorazione
    ON fatture_righe (cd_lavorazione)
    WHERE cd_lavorazione IS NOT NULL;

-- Indice composite: cliente + lavorazione (query più comune nell'assistente)
CREATE INDEX IF NOT EXISTS idx_fatture_righe_cliente_lavorazione
    ON fatture_righe (codice_cliente, cd_lavorazione)
    WHERE cd_lavorazione IS NOT NULL;

-- 2. Abilita pg_trgm per ricerca fuzzy (articolo/colore su offerte_righe)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN trigram su codice_articolo in offerte_righe (step 2 cascata: similitudine)
CREATE INDEX IF NOT EXISTS idx_offerte_righe_articolo_trgm
    ON offerte_righe USING gin (codice_articolo gin_trgm_ops);

-- GIN trigram su colore (matching tollerante colore DDT → colore codificato)
CREATE INDEX IF NOT EXISTS idx_offerte_righe_colore_trgm
    ON offerte_righe USING gin (colore gin_trgm_ops);

-- GIN trigram su ds_lavorazione per ricerca testo libero sulla lavorazione
CREATE INDEX IF NOT EXISTS idx_fatture_righe_ds_lavorazione_trgm
    ON fatture_righe USING gin (ds_lavorazione gin_trgm_ops)
    WHERE ds_lavorazione IS NOT NULL;
