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
    importo_totale NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    stato VARCHAR(50) NOT NULL DEFAULT 'Aperta'
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

-- Invoices Tables
CREATE TABLE fatture_testate (
    numero_disposizione VARCHAR(100) PRIMARY KEY,
    data_fattura DATE NOT NULL,
    codice_cliente VARCHAR(50) NOT NULL REFERENCES clienti(codice),
    codice_stagione VARCHAR(50) REFERENCES stagioni(codice),
    importo_totale NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    stato_pagamento VARCHAR(50) NOT NULL DEFAULT 'Aperta'
);

CREATE TABLE fatture_righe (
    id SERIAL PRIMARY KEY,
    numero_disposizione VARCHAR(100) NOT NULL REFERENCES fatture_testate(numero_disposizione) ON DELETE CASCADE,
    riga_disposizione INTEGER NOT NULL,
    numero_bolla VARCHAR(100),
    codice_articolo VARCHAR(100) REFERENCES articoli(codice),
    colore VARCHAR(100),
    kg_fatturati NUMERIC(10, 3) NOT NULL DEFAULT 0.000,
    capi_fatturati NUMERIC(10, 0) NOT NULL DEFAULT 0,
    importo_riga NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT uq_fatture_righe UNIQUE (numero_disposizione, riga_disposizione)
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


-- Seed Data

-- 1. Customers
INSERT INTO clienti (codice, ragione_sociale) VALUES
('1439', 'SERIGRAFIA ROSSI'),
('1392', 'TESSITURA ROSSI S.P.A.'),
('1283', 'MAGLIFICIO ROSSI IDEE MODA SRL'),
('XXX', 'TAM & COMPANY S.P.A.')
ON CONFLICT DO NOTHING;

-- 2. Seasons
INSERT INTO stagioni (codice, descrizione) VALUES
('PE2026', 'Primavera/Estate 2026'),
('AI25-26', 'Autunno/Inverno 2025-2026')
ON CONFLICT DO NOTHING;

-- 3. Articles
INSERT INTO articoli (codice, descrizione, composizione) VALUES
('CAPI 80LI20CO', 'Capi 80% Lino 20% Cotone', '80% LI 20% CO'),
('CAPI 80VI20PA', 'Capi 80% Viscosa 20% Poliammide', '80% VI 20% PA'),
('CAPI 100VI', 'Capi 100% Viscosa', '100% VI'),
('CAPI 100PA', 'Capi 100% Poliammide', '100% PA'),
('CAPI 100%VI', 'Capi 100% Viscosa speciale', '100% VI'),
('CAPI 95PA5CO', 'Capi 95% Poliammide 5% Cotone', '95% PA 5% CO'),
('CAPI 90%LI10%VI', 'Capi 90% Lino 10% Viscosa', '90% LI 10% VI'),
('CAPI 65%LI23%CO12%PA', 'Capi 65% Lino 23% Cotone 12% Poliammide', '65% LI 23% CO 12% PA'),
('CAPI 100%LI', 'Capi 100% Lino', '100% LI'),
('CAPI 50%PELLE30%LI13%VI5%PA2%EA', 'Capi Pelle e Misto', '50% PELLE 30% LI 13% VI 5% PA 2% EA')
ON CONFLICT DO NOTHING;

-- 4. Offers
INSERT INTO offerte_testate (numero_offerta, data_offerta, codice_cliente, codice_stagione, importo_totale, stato) VALUES
('OFF-2026-0142', '2026-02-12', '1283', 'PE2026', 12450.00, 'Accettata'),
('OFF-2026-0155', '2026-02-18', '1283', 'PE2026', 3200.00, 'Aperta'),
('OFF-2025-0891', '2025-11-05', '1283', 'AI25-26', 890.00, 'Rifiutata'),
-- Seeding an audit mismatch test offer for TAM & COMPANY
('OFF-2026-1000', '2026-02-15', 'XXX', 'PE2026', 1500.00, 'Accettata')
ON CONFLICT DO NOTHING;

INSERT INTO offerte_righe (numero_offerta, riga_num, codice_articolo, colore, quantita, prezzo_unitario, importo_riga) VALUES
('OFF-2026-0142', 1, 'CAPI 100VI', 'TORTORA', 100, 124.50, 12450.00),
('OFF-2026-0155', 1, 'CAPI 80VI20PA', 'MILITE', 40, 80.00, 3200.00),
('OFF-2025-0891', 1, 'CAPI 100%LI', 'NEW NERO REATT***', 10, 89.00, 890.00),
-- Mismatch target line (offered 100 items of CAPI 100%VI, but only 82.3 kg delivered/billed)
('OFF-2026-1000', 1, 'CAPI 100%VI', 'NERO ***REATT.(+D/T SOLO X CO/NY)', 100, 10.00, 1000.00),
('OFF-2026-1000', 2, 'CAPI 100PA', 'GRIGIO/AVIO', 5, 12.00, 60.00)
ON CONFLICT DO NOTHING;

-- 5. DDT/Bolle Testate (5 bolle from tam-fatture.txt)
INSERT INTO ddt_testate (numero_bolla, data_bolla, codice_cliente, codice_stagione) VALUES
('1756', '2026-03-03', 'XXX', 'PE2026'),
('1704', '2026-03-02', 'XXX', 'PE2026'),
('2380', '2026-03-27', 'XXX', 'PE2026'),
('1815', '2026-03-05', 'XXX', 'PE2026'),
('1915', '2026-03-10', 'XXX', 'PE2026')
ON CONFLICT DO NOTHING;

-- 6. Invoices Testate (7 dispositions from tam-fatture.txt)
INSERT INTO fatture_testate (numero_disposizione, data_fattura, codice_cliente, codice_stagione, importo_totale, stato_pagamento) VALUES
('1200', '2026-03-03', 'XXX', 'PE2026', 120.00, 'Pagata'),
('1207', '2026-03-03', 'XXX', 'PE2026', 883.00, 'Aperta'),
('1018', '2026-03-27', 'XXX', 'PE2026', 60.00, 'Pagata'),
('1438', '2026-03-03', 'XXX', 'PE2026', 480.00, 'Aperta'),
('1532', '2026-03-03', 'XXX', 'PE2026', 414.00, 'Pagata'),
('1533', '2026-03-03', 'XXX', 'PE2026', 120.00, 'Aperta'),
('1909', '2026-03-10', 'XXX', 'PE2026', 991.78, 'Aperta')
ON CONFLICT DO NOTHING;

-- 7. DDT Lines and Invoice Lines (mapped row-by-row from tam-fatture.txt)
-- 1
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 1, '1200', 2, NULL, 'CAPI 80LI20CO', 'TORTORA M', 0.8, 2, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1200', 2, '1756', 'CAPI 80LI20CO', 'TORTORA M', 0.8, 2, 60.00);

-- 2
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 2, '1200', 3, NULL, 'CAPI 80VI20PA', 'MILITE', 0.3, 1, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1200', 3, '1756', 'CAPI 80VI20PA', 'MILITE', 0.3, 1, 60.00);

-- 3
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1704', 1, '1207', 7, NULL, 'CAPI 100VI', 'TORTORA (R)', 5.5, 0, 0.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1207', 7, '1704', 'CAPI 100VI', 'TORTORA (R)', 5.5, 0, 0.00);

-- 4
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 3, '1207', 3, 'OFF-2026-1000', 'CAPI 100PA', 'GRIGIO/AVIO', 2.2, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1207', 3, '1756', 'CAPI 100PA', 'GRIGIO/AVIO', 2.2, 0, 60.00);

-- 5
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 4, '1207', 6, 'OFF-2026-1000', 'CAPI 100%VI', 'NERO ***REATT.(+D/T SOLO X CO/NY)', 82.3, 0, 823.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1207', 6, '1756', 'CAPI 100%VI', 'NERO ***REATT.(+D/T SOLO X CO/NY)', 82.3, 0, 823.00);

-- 6
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('2380', 1, '1018', 4, NULL, 'CAPI 95PA5CO', 'GHIACCIO CAPO CAMP', 2.5, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1018', 4, '2380', 'CAPI 95PA5CO', 'GHIACCIO CAPO CAMP', 2.5, 0, 60.00);

-- 7
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 5, '1438', 3, NULL, 'CAPI 100%VI', 'VERDE PISELLO', 0.5, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 3, '1756', 'CAPI 100%VI', 'VERDE PISELLO', 0.5, 0, 60.00);

-- 8
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 6, '1438', 2, NULL, 'CAPI 100%VI', 'BEIGE/TORTORA', 0.3, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 2, '1756', 'CAPI 100%VI', 'BEIGE/TORTORA', 0.3, 0, 60.00);

-- 9
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 7, '1438', 4, NULL, 'CAPI 100%VI', 'TORTORA', 0.5, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 4, '1756', 'CAPI 100%VI', 'TORTORA', 0.5, 0, 60.00);

-- 10
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 8, '1438', 8, NULL, 'CAPI 100%VI', 'NOCE', 0.3, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 8, '1756', 'CAPI 100%VI', 'NOCE', 0.3, 0, 60.00);

-- 11
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 9, '1438', 6, NULL, 'CAPI 100%VI', 'MILITE', 0.5, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 6, '1756', 'CAPI 100%VI', 'MILITE', 0.5, 0, 60.00);

-- 12
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 10, '1438', 7, NULL, 'CAPI 100%VI', 'GRIGIO CH CAPO CAMP', 0.7, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 7, '1756', 'CAPI 100%VI', 'GRIGIO CH CAPO CAMP', 0.7, 0, 60.00);

-- 13
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 11, '1438', 5, NULL, 'CAPI 100%VI', 'GRIGIO CH (CAPO CAMP.)', 0.6, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 5, '1756', 'CAPI 100%VI', 'GRIGIO CH (CAPO CAMP.)', 0.6, 0, 60.00);

-- 14
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 12, '1438', 9, NULL, 'CAPI 100%VI', 'PERLA CHSS', 0.3, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1438', 9, '1756', 'CAPI 100%VI', 'PERLA CHSS', 0.3, 0, 60.00);

-- 15
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 13, '1532', 8, NULL, 'CAPI 90%LI10%VI', 'GIALLO LIMONE', 0.2, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1532', 8, '1756', 'CAPI 90%LI10%VI', 'GIALLO LIMONE', 0.2, 0, 60.00);

-- 16
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 14, '1532', 5, NULL, 'CAPI 65%LI23%CO12%PA', 'SABBIA', 2.2, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1532', 5, '1756', 'CAPI 65%LI23%CO12%PA', 'SABBIA', 2.2, 0, 60.00);

-- 17
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 15, '1532', 4, NULL, 'CAPI 65%LI23%CO12%PA', 'NERO ***REATT.(+D/T SOLO X CO/NY)', 15.6, 0, 234.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1532', 4, '1756', 'CAPI 65%LI23%CO12%PA', 'NERO ***REATT.(+D/T SOLO X CO/NY)', 15.6, 0, 234.00);

-- 18
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 16, '1532', 3, NULL, 'CAPI 100%LI', 'NEW NERO REATT***(+D/T SOLO X CO/NY)', 2.1, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1532', 3, '1756', 'CAPI 100%LI', 'NEW NERO REATT***(+D/T SOLO X CO/NY)', 2.1, 0, 60.00);

-- 19
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 17, '1533', 3, NULL, 'CAPI 50%PELLE30%LI13%VI5%PA2%EA', 'FINANZA', 2.2, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1533', 3, '1756', 'CAPI 50%PELLE30%LI13%VI5%PA2%EA', 'FINANZA', 2.2, 0, 60.00);

-- 20
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1756', 18, '1533', 2, NULL, 'CAPI 50%PELLE30%LI13%VI5%PA2%EA', 'SBAGNATURA+DOPPIA TINTURA OLD', 2.2, 0, 60.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1533', 2, '1756', 'CAPI 50%PELLE30%LI13%VI5%PA2%EA', 'SBAGNATURA+DOPPIA TINTURA OLD', 2.2, 0, 60.00);

-- 21
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1815', 1, '1909', 2, NULL, 'CAPI 100%VI', 'BEIGE/TORTORA', 26.6, 0, 111.72);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1909', 2, '1815', 'CAPI 100%VI', 'BEIGE/TORTORA', 26.6, 0, 111.72);

-- 22
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1915', 1, '1909', 5, NULL, 'CAPI 100%VI', 'GRIGIO CH (CAPO CAMP.)', 73.7, 0, 309.54);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1909', 5, '1915', 'CAPI 100%VI', 'GRIGIO CH (CAPO CAMP.)', 73.7, 0, 309.54);

-- 23
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1915', 2, '1909', 1, NULL, 'CAPI 100%VI', 'PERLA CHSS', 64.7, 0, 271.74);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1909', 1, '1915', 'CAPI 100%VI', 'PERLA CHSS', 64.7, 0, 271.74);

-- 24
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1915', 3, '1909', 3, NULL, 'CAPI 100%VI', 'TORTORA', 9.7, 0, 85.00);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1909', 3, '1915', 'CAPI 100%VI', 'TORTORA', 9.7, 0, 85.00);

-- 25
INSERT INTO ddt_righe (numero_bolla, riga_num, numero_disposizione, riga_disposizione, numero_offerta, codice_articolo, colore, kg_consegnati, capi_consegnati, importo_riga)
VALUES ('1915', 4, '1909', 4, NULL, 'CAPI 100%VI', 'MILITE', 50.9, 0, 213.78);
INSERT INTO fatture_righe (numero_disposizione, riga_disposizione, numero_bolla, codice_articolo, colore, kg_fatturati, capi_fatturati, importo_riga)
VALUES ('1909', 4, '1915', 'CAPI 100%VI', 'MILITE', 50.9, 0, 213.78);
