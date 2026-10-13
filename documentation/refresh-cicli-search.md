# Refresh `cicli_search` — documento di ricerca fasi

Come e quando ricostruire la tabella `cicli_search`, usata dalla ricerca per fasi / lavorazioni nella pagina Cicli.

Riferimenti:

- Migration: `data/migrations/cicli-storico-search.sql`
- Logica filtri: [`new-filters-logic-storico-and-cicli.md`](./new-filters-logic-storico-and-cicli.md) (§6)
- API: `POST /api/cicli/refresh-search` (`backend/cicli_routes.py`)

---

## 1. Perché esiste

La ricerca «Fasi / lavorazioni» non deve fare ogni volta un `EXISTS` su ~320.000 righe di `cicli_fasi` + join su `fasi_lavoro` e note testata.

Per ogni ciclo (chiave a 6 campi) si precalcola un unico testo `search_doc` che concatena e normalizza:

| Origine | Campi |
| :--- | :--- |
| Testata (`cicli_testate`) | `ds_ciclo`, `ds_ciclo_bolle_fat`, `note` |
| Fasi (`cicli_fasi` + `fasi_lavoro`) | `ds_fase`, `note` (in ordine di sequenza) |

La normalizzazione (`norm_search`) fa `UPPER`, toglie accenti (`unaccent`), sistematica `40?` → `40°`, e sostituisce i separatori tipici (`+`, `/`, `.`, …) con spazi.

Il risultato vive in **`cicli_search`** (una riga per ciclo), con indice GIN trigrammi su `search_doc`. La query di lista cicli fa join su questa tabella invece di scandire tutte le fasi.

---

## 2. Cosa fa il refresh

La funzione Postgres `public.refresh_cicli_search()`:

1. **`TRUNCATE cicli_search`** — svuota la tabella
2. **`INSERT … SELECT`** — ricostruisce una riga per ogni `cicli_testate`, aggregando le fasi
3. **Restituisce** il numero di righe inserite

Non è incrementale: ad ogni richiamo si ricalcola tutto. Con ~108.000 testate e ~320.000 fasi può richiedere da qualche decina di secondi a qualche minuto, a seconda del carico del DB.

La migration **crea** la tabella vuota e la funzione; **non** popola i dati da sola. Dopo il primo import CSV cicli (e dopo ogni re-import) serve un refresh esplicito.

---

## 3. Quando eseguirlo

| Momento | Serve refresh? |
| :--- | :--- |
| Prima applicazione di `cicli-storico-search.sql` | Sì, dopo che `cicli_testate` / `cicli_fasi` / `fasi_lavoro` sono già caricate |
| Dopo ogni re-import / `\copy` dei CSV cicli (`z09`, `z08`, `z02`, …) | **Sì** — altrimenti `search_doc` resta vecchio o assente |
| Solo filtri cliente / stagione / codice ciclo / storico (senza fasi) | No |
| Aggiornamento solo dizionario `ricerca_sinonimi` | No — i sinonimi sono letti a runtime, non finiscono in `search_doc` |
| Solo import storico EW1/EW2 | No — lo storico non popola `cicli_search` |

Regola pratica: **ogni volta che cambiano le tabelle cicli, rifare il refresh.**

---

## 4. Come eseguirlo

### 4.1 Da SQL (psql / pgAdmin)

Container tipico: `data-timescaledb-intex-1`.

```sql
SELECT public.refresh_cicli_search();
-- → intero = numero di cicli caricati in cicli_search
```

Verifica:

```sql
SELECT COUNT(*) FROM cicli_search;
SELECT COUNT(*) FROM cicli_testate;
-- i due count dovrebbero coincidere (o essere molto vicini)

SELECT search_doc
FROM cicli_search
WHERE codice_cliente = '1869' AND codice_ciclo = 'T100'
LIMIT 5;
```

### 4.2 Da API (autenticata)

```http
POST /api/cicli/refresh-search
Authorization: Bearer <token>
```

Risposta attesa:

```json
{ "status": "ok", "rows": 108054 }
```

Se la tabella non esiste (migration non applicata):

```json
{ "error": "cicli_search non esiste: applicare migration cicli-storico-search.sql" }
```

### 4.3 Dopo `apply_migrations.py`

```bash
cd backend
python apply_migrations.py cicli-storico-search.sql
# poi, con cicli già importati:
# SELECT refresh_cicli_search();
# oppure POST /api/cicli/refresh-search
```

---

## 5. Cosa succede se non si fa refresh

| Stato `cicli_search` | Comportamento ricerca fasi |
| :--- | :--- |
| Tabella assente o **vuota** | Fallback: `EXISTS` su `cicli_fasi` + `fasi_lavoro` + note/descrizioni testata. Funziona, ma è più lenta e non usa l’indice GIN sul documento unico. |
| Tabella **popolata ma stantia** | La ricerca fasi usa dati vecchi: cicli nuovi/modificati dopo l’ultimo refresh possono non matchare (o matchare testi obsoleti). |
| Tabella aggiornata | Path preferito: join su `cs.search_doc` + trigrammi / `word_similarity`. |

L’API controlla se c’è almeno una riga (`_cicli_search_ready`); se sì usa `cicli_search`, altrimenti il fallback.

I filtri **non** basati sulle fasi (cliente, stagione, codice ciclo, articolo cliente, composizione, storico) non dipendono da `cicli_search`.

---

## 6. Pipeline consigliata (import cicli)

```text
1. Export Oracle → CSV (scripts/export_cicli_tables.txt)
2. Import CSV → Postgres (TRUNCATE/COPY su cicli_*)
3. SELECT refresh_cicli_search();   ← obbligatorio per fasi performanti
4. (opzionale) verificare COUNT cicli_search ≈ COUNT cicli_testate
```

Se l’import cicli è automatizzato (cron / script), aggiungere lo step 3 subito dopo il carico.

---

## 7. Note operative

- **Durata:** non lanciare il refresh in mezzo a una sessione utente critica se il DB è sotto carico; preferire dopo l’import notturno.
- **Lock:** `TRUNCATE` + `INSERT` blocca `cicli_search` per la durata del refresh; le liste cicli senza filtro fasi restano ok; quelle con filtro fasi possono rallentare o vedere la tabella vuota per un istante se interrogano durante il `TRUNCATE`.
- **Spazio:** una riga per ciclo con testo aggregato; ordine di grandezza gestibile (~108k righe).
- **Sinonimi:** aggiornare `ricerca_sinonimi` non richiede refresh; aggiornare testi fasi/descrizioni sì.

---

## 8. Riepilogo

| Domanda | Risposta |
| :--- | :--- |
| Cos’è? | Tabella di denormalizzazione testo fasi+descrizioni per ciclo |
| Chi la crea vuota? | Migration `cicli-storico-search.sql` |
| Chi la riempie? | `refresh_cicli_search()` o `POST /api/cicli/refresh-search` |
| Quando? | Dopo ogni import/aggiornamento delle tabelle cicli |
| Se dimentico? | Ricerca fasi in fallback (più lenta) o su dati vecchi se la tabella non è vuota |
