-- ============================================================
-- Migration: create-logs.sql
-- Scopo: audit login utenti e ricerche effettuate
-- Prerequisiti: create-users.sql (tabella users)
-- ============================================================

CREATE TABLE IF NOT EXISTS logs (
    id          BIGSERIAL    PRIMARY KEY,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    event_type  VARCHAR(50)  NOT NULL,
    user_id     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    username    VARCHAR(255),
    details     JSONB        NOT NULL DEFAULT '{}'::jsonb,
    ip          VARCHAR(64),
    user_agent  TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_created
    ON logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_logs_event_created
    ON logs (event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_logs_user_created
    ON logs (user_id, created_at DESC);
