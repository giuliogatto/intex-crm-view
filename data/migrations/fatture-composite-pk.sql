-- Upgrade existing DB: drop payment status, fix fatture PK to (codice_cliente, numero_disposizione).
-- Idempotent: safe to run on fresh old schema, partial runs, or already-migrated DB.
-- After applying, run a full fatture sync to repopulate collided disposition numbers.

DO $$
BEGIN
    -- 1. Remove stale "Pagata" seed rows (only if old column still exists)
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'fatture_testate'
          AND column_name = 'stato_pagamento'
    ) THEN
        DELETE FROM fatture_testate WHERE stato_pagamento = 'Pagata';
        ALTER TABLE fatture_testate DROP COLUMN stato_pagamento;
    END IF;

    -- 2. Ensure fatture_righe.codice_cliente exists and is populated
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'fatture_righe'
          AND column_name = 'codice_cliente'
    ) THEN
        ALTER TABLE fatture_righe ADD COLUMN codice_cliente VARCHAR(50);
    END IF;

    UPDATE fatture_righe r
    SET codice_cliente = f.codice_cliente
    FROM fatture_testate f
    WHERE r.numero_disposizione = f.numero_disposizione
      AND r.codice_cliente IS NULL;

    DELETE FROM fatture_righe WHERE codice_cliente IS NULL;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'fatture_righe'
          AND column_name = 'codice_cliente'
          AND is_nullable = 'YES'
    ) THEN
        ALTER TABLE fatture_righe ALTER COLUMN codice_cliente SET NOT NULL;
    END IF;

    -- 3. Skip PK migration if composite PK is already in place
    IF EXISTS (
        SELECT 1
        FROM pg_index i
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY (i.indkey)
        WHERE n.nspname = 'public'
          AND t.relname = 'fatture_testate'
          AND i.indisprimary
          AND a.attname = 'codice_cliente'
    ) THEN
        RAISE NOTICE 'fatture_testate already has composite PK (codice_cliente, numero_disposizione); skipping PK migration';
        RETURN;
    END IF;

    -- 4. Migrate from single-column PK (numero_disposizione) to composite PK
    ALTER TABLE fatture_righe DROP CONSTRAINT IF EXISTS fatture_righe_fatture_testate_fkey;
    ALTER TABLE fatture_righe DROP CONSTRAINT IF EXISTS fatture_righe_numero_disposizione_fkey;
    ALTER TABLE fatture_righe DROP CONSTRAINT IF EXISTS uq_fatture_righe;

    ALTER TABLE fatture_testate DROP CONSTRAINT IF EXISTS fatture_testate_pkey;

    ALTER TABLE fatture_testate
        ADD PRIMARY KEY (codice_cliente, numero_disposizione);

    ALTER TABLE fatture_righe
        ADD CONSTRAINT uq_fatture_righe
            UNIQUE (codice_cliente, numero_disposizione, riga_disposizione);

    ALTER TABLE fatture_righe
        ADD CONSTRAINT fatture_righe_fatture_testate_fkey
            FOREIGN KEY (codice_cliente, numero_disposizione)
            REFERENCES fatture_testate (codice_cliente, numero_disposizione)
            ON DELETE CASCADE;
END $$;
