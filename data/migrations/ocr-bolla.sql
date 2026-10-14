-- ============================================================
-- Migration: ocr-bolla.sql
-- Scopo: supporto «Upload bolla» pagina Cicli
--   - indice trigram per matching ragione sociale mittente
--   - sessioni OCR (cache per hash immagine + audit)
-- Prerequisiti: create-cicli-tables.sql, cicli-storico-search.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_cicli_clienti_ragione_trgm
    ON cicli_clienti USING gin (ragione_sociale gin_trgm_ops);

CREATE TABLE IF NOT EXISTS ocr_bolla_sessioni (
    id                 BIGSERIAL    PRIMARY KEY,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    username           VARCHAR(100),
    image_sha256       CHAR(64)     NOT NULL,
    mime_type          VARCHAR(50),
    image_bytes        INTEGER,
    model              VARCHAR(100),
    openai_response_id VARCHAR(100),
    ocr_json           JSONB        NOT NULL,
    cliente_scelto     VARCHAR(50),
    match_json         JSONB
);

CREATE INDEX IF NOT EXISTS idx_ocr_bolla_sessioni_sha
    ON ocr_bolla_sessioni (image_sha256, model, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ocr_bolla_sessioni_created
    ON ocr_bolla_sessioni (created_at DESC);
