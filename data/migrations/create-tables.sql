-- Drop tables if they exist (for clean rebuilds)
DROP TABLE IF EXISTS fatture_righe CASCADE;
DROP TABLE IF EXISTS fatture_testate CASCADE;
DROP TABLE IF EXISTS ddt_righe CASCADE;
DROP TABLE IF EXISTS ddt_testate CASCADE;
DROP TABLE IF EXISTS offerte_righe CASCADE;
DROP TABLE IF EXISTS offerte_testate CASCADE;
DROP TABLE IF EXISTS articoli CASCADE;
DROP TABLE IF EXISTS stagioni CASCADE;
DROP TABLE IF EXISTS clienti CASCADE;

-- Master Data Tables
CREATE TABLE clienti (
    codice VARCHAR(50) PRIMARY KEY,
    ragione_sociale VARCHAR(255) NOT NULL
);

CREATE TABLE stagioni (
    codice VARCHAR(50) PRIMARY KEY,
    descrizione VARCHAR(100) NOT NULL
);

CREATE TABLE articoli (
    codice VARCHAR(100) PRIMARY KEY,
    descrizione VARCHAR(255),
    composizione VARCHAR(255)
);

-- Offers/Quotes Tables
CREATE TABLE offerte_testate (
    numero_offerta VARCHAR(100) PRIMARY KEY,
    data_offerta DATE NOT NULL,
    codice_cliente VARCHAR(50) NOT NULL REFERENCES clienti(codice),
    codice_stagione VARCHAR(50) REFERENCES stagioni(codice),
    importo_totale NUMERIC(12, 2) NOT NULL DEFAULT 0.00
);

CREATE TABLE offerte_righe (
    id SERIAL PRIMARY KEY,
    numero_offerta VARCHAR(100) NOT NULL REFERENCES offerte_testate(numero_offerta) ON DELETE CASCADE,
    riga_num INTEGER NOT NULL,
    codice_articolo VARCHAR(100) REFERENCES articoli(codice),
    colore VARCHAR(100),
    quantita NUMERIC(10, 2) NOT NULL DEFAULT 0,
    prezzo_unitario NUMERIC(10, 4) NOT NULL DEFAULT 0,
    importo_riga NUMERIC(12, 2) NOT NULL DEFAULT 0,
    CONSTRAINT uq_offerte_righe UNIQUE (numero_offerta, riga_num)
);

-- DDT/Bolle Tables
CREATE TABLE ddt_testate (
    numero_bolla VARCHAR(100) PRIMARY KEY,
    data_bolla DATE NOT NULL,
    codice_cliente VARCHAR(50) NOT NULL REFERENCES clienti(codice),
    codice_stagione VARCHAR(50) REFERENCES stagioni(codice)
);

CREATE TABLE ddt_righe (
    id SERIAL PRIMARY KEY,
    numero_bolla VARCHAR(100) NOT NULL REFERENCES ddt_testate(numero_bolla) ON DELETE CASCADE,
    riga_num INTEGER NOT NULL,
    numero_disposizione VARCHAR(100),
    riga_disposizione INTEGER,
    numero_offerta VARCHAR(100),
    codice_articolo VARCHAR(100) REFERENCES articoli(codice),
    colore VARCHAR(100),
    kg_consegnati NUMERIC(10, 3) NOT NULL DEFAULT 0.000,
    capi_consegnati NUMERIC(10, 0) NOT NULL DEFAULT 0,
    importo_riga NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT uq_ddt_righe UNIQUE (numero_bolla, riga_num)
);

-- Invoices Tables (disposition numbers are unique per customer, not globally)
CREATE TABLE fatture_testate (
    codice_cliente VARCHAR(50) NOT NULL REFERENCES clienti(codice),
    numero_disposizione VARCHAR(100) NOT NULL,
    data_fattura DATE NOT NULL,
    codice_stagione VARCHAR(50) REFERENCES stagioni(codice),
    importo_totale NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (codice_cliente, numero_disposizione)
);

CREATE TABLE fatture_righe (
    id SERIAL PRIMARY KEY,
    codice_cliente VARCHAR(50) NOT NULL,
    numero_disposizione VARCHAR(100) NOT NULL,
    riga_disposizione INTEGER NOT NULL,
    numero_bolla VARCHAR(100),
    codice_articolo VARCHAR(100) REFERENCES articoli(codice),
    colore VARCHAR(100),
    kg_fatturati NUMERIC(10, 3) NOT NULL DEFAULT 0.000,
    capi_fatturati NUMERIC(10, 0) NOT NULL DEFAULT 0,
    importo_riga NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT uq_fatture_righe UNIQUE (codice_cliente, numero_disposizione, riga_disposizione),
    CONSTRAINT fatture_righe_fatture_testate_fkey
        FOREIGN KEY (codice_cliente, numero_disposizione)
        REFERENCES fatture_testate(codice_cliente, numero_disposizione) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_clienti_ragione_sociale ON clienti (ragione_sociale);
CREATE INDEX idx_offerte_testate_search ON offerte_testate (codice_cliente, data_offerta, codice_stagione);
CREATE INDEX idx_ddt_testate_search ON ddt_testate (codice_cliente, data_bolla, codice_stagione);
CREATE INDEX idx_ddt_righe_links ON ddt_righe (numero_disposizione, numero_offerta);
CREATE INDEX idx_fatture_testate_search ON fatture_testate (codice_cliente, data_fattura, codice_stagione);
CREATE INDEX idx_fatture_righe_bolla ON fatture_righe (numero_bolla);

CREATE TABLE chats (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

create index idx_chats_user_id on chats(user_id);
create index idx_chats_model on chats(model);

create table messages (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    provider_message_id TEXT NOT NULL,
    role TEXT NOT NULL, -- user or assistant
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

create index idx_messages_chat_id on messages(chat_id);
