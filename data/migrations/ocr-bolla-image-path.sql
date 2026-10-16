-- ============================================================
-- Migration: ocr-bolla-image-path.sql
-- Scopo: path relativo dell'immagine bolla salvata su disco
--        (volume Docker /data/ocr-bolla-images)
-- ============================================================

ALTER TABLE ocr_bolla_sessioni
    ADD COLUMN IF NOT EXISTS image_path VARCHAR(500);
