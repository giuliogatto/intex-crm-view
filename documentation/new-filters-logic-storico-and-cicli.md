# Nuovi filtri pagina Cicli — logica di ricerca combinata Cicli + Storico disposizioni

Analisi per estendere la pagina **Cicli** (`frontend/app/src/pages/CicliPage.jsx`, API `GET /api/cicli` in `backend/app.py`) con filtri che pescano sia dalle tabelle cicli (Z09/Z08/Z02) sia dallo storico disposizioni (EW1/EW2).

Documenti di riferimento:

- [`analisi-storico.md`](./analisi-storico.md) — mappatura schermata «Storico Disposizioni Completo» → `EW1_TESTATA_DISPOSIZIONI` / `EW2_RIGHE_DISPOSIZIONI`
- `data/migrations/create-cicli-tables.sql` — tabelle cicli lato Postgres
- `data/migrations/create-storico-disposizioni-tables.sql` — tabelle storico lato Postgres
- `scripts/export_cicli_tables.txt`, `scripts/extract_upload_tables_storico.py` — export Oracle

Filtri richiesti:

1. Fasi: parole chiave cercate in modo **non letterale** (varianti, abbreviazioni, sinonimi) in fasi, descrizioni e note
2. Colore
3. Tessuto (es. `S3651`)
4. Commessa → campo «Rif. Disp. Cliente» dello storico
5. Modello (nome del capo nel codice del cliente)
6. Codice articolo fiscale (verifica del filtro esistente)

Vincolo: risultati **sempre in ordine cronologico**, dal ciclo inserito più di recente.

---

## 1. Sintesi

| Tema | Conclusione |
| :--- | :--- |
| Entità risultato | Resta il **ciclo** (testata Z09, chiave a 6 campi). Lo storico serve come **filtro** (`EXISTS`) e come **arricchimento** (ultimo utilizzo, commesse, colori, modelli). |
| Collegamento ciclo ↔ storico | Ogni riga EW2 ha la stessa chiave a 6 campi di Z09: `cliente, articolo, ciclo, linea, stagione, composizione`, dove **`EW2_CD_ARTICOLO_FATTURA` = `Z09_CD_ARTICOLO_CLIENTE`**. Verificato su campioni reali (§3). |
| Filtri solo-cicli | cliente, stagione, codice ciclo, articolo cliente, composizione, descrizione, **fasi** |
| Filtri solo-storico | **colore, tessuto, commessa, modello, articolo fiscale** — nelle tabelle cicli non esistono |
| Regola di combinazione | AND tra tutti i filtri; i filtri storico devono essere soddisfatti **dalla stessa riga EW2** (es. colore + commessa sulla stessa riga di disposizione) |
| Filtro «Articolo» attuale | **Non** è l'articolo fiscale: cerca `Z09_CD_ARTICOLO_CLIENTE` + `CWA_DS_ARTICOLO_CLIENTE` (articolo cliente, es. `00060 CAPI/TIRELLE`). L'articolo fiscale (`EW2_CD_ARTICOLO_FISCALE`, quasi sempre `CAPI`) esiste solo nello storico. |
| Ordinamento attuale | `ORDER BY ragione_sociale, codice_ciclo, codice_stagione` → da cambiare in `data_ins DESC` |
| Ricerca semantica fasi | Normalizzazione + dizionario abbreviazioni/sinonimi + trigrammi (`pg_trgm`) in fase 1; espansione via embeddings (`pgvector`, già disponibile nell'immagine `timescaledb-ha:pg16`) in fase 2 |
| Prerequisito dati | Lo storico oggi copre solo **365 giorni** (`LOOKBACK_DAYS = 365`). Per cercare commesse/colori/modelli su cicli più vecchi serve un dump completo una tantum di EW1/EW2 + sync incrementale. |
| Punto aperto | **Tessuto**: non esiste un'anagrafica tessuti in `INTEX2` né una colonna dedicata certa. Candidati e query di verifica in §5.3. |

---

## 2. Stato attuale

### 2.1 Backend `GET /api/cicli`

`_cicli_filters()` / `_cicli_from_where()` in `backend/app.py`:

| Parametro | Colonne interrogate | Tipo match |
| :--- | :--- | :--- |
| `codice_cliente` | `t.codice_cliente` | esatto |
| `stagione` | `t.codice_stagione` | esatto |
| `codice_ciclo` | `t.codice_ciclo`, `t.codice_ciclo_cli` | `ILIKE %a%b%` |
| `articolo` | `ar.ds_articolo` (CWA), `t.codice_articolo` (Z09 articolo **cliente**) | `ILIKE %a%b%` |
| `composizione` | `co.ds_composizione`, `t.codice_composizione` | `ILIKE %a%b%` |
| `descrizione` | `t.ds_ciclo`, `t.ds_ciclo_bolle_fat` | `ILIKE %a%b%` |

Limiti:

- nessun filtro su fasi (`cicli_fasi`, `fasi_lavoro`) né su note (`cicli_testate.note`, `cicli_fasi.note`);
- le tabelle `ew1_testata_disposizioni` / `ew2_righe_disposizioni` non sono usate da nessun endpoint;
- ordinamento alfabetico per cliente, non cronologico; `data_ins` viene restituita ma non mostrata in UI;
- `_broad_like_pattern` è letterale nell'ordine delle parole (`tinto stretch` non trova `STRETCH+TINTO`).

### 2.2 Frontend `CicliPage.jsx`

Form con 6 campi (cliente, stagione, codice ciclo, articolo, composizione, descrizione), tabella risultati con espansione «Fasi» che chiama `GET /api/cicli/fasi` sulla chiave a 6 campi.

### 2.3 Volumi (CSV export ott 2026)

| Tabella | Righe | Note |
| :--- | ---: | :--- |
| `cicli_testate` (Z09) | ~108.000 | ~15.300 `ds_ciclo` distinte; ~6.800 testate con `note` valorizzata; `data_ins` NULL su ~680 |
| `cicli_fasi` (Z08) | ~321.000 | ~21.000 fasi con `note` (3.358 testi distinti: `A FREDDO`, `REATTIVO`, `MPELO`, `RINSE`, …) |
| `fasi_lavoro` (Z02) | ~375 | vocabolario delle fasi |
| `ew1_testata_disposizioni` | ~11.000 / anno (~195.000 totali) | |
| `ew2_righe_disposizioni` | ~41.000 / anno | |

---

## 3. Chiave di collegamento ciclo ↔ storico

### 3.1 Evidenza

Righe EW2 reali (`scripts/output-all-queries.txt`) confrontate con `csv/z09_cicli_testate.csv`:

| EW2 (disposizione 2026/8561 riga 15) | Valore | Z09 corrispondente |
| :--- | :--- | :--- |
| `EW2_CD_CLIENTE` | `1843` | `Z09_CD_CLIENTE = 1843` |
| `EW2_CD_ARTICOLO_FISCALE` | `CAPI` | — (non è in Z09) |
| `EW2_CD_ARTICOLO_FATTURA` | `00060` | `Z09_CD_ARTICOLO_CLIENTE = 00060` (CWA: «CAPI/TIRELLE») |
| `EW2_DS_ARTICOLO` | `CAPI/TIRELLE FIBBIE` | — |
| `EW2_CD_CICLO` | `TI.AC+RIC.INT` | `Z09_CD_CICLO = TI.AC+RIC.INT` |
| `EW2_CD_LINEA` | `.` | `Z09_CD_LINEA = .` |
| `EW2_CD_STAGIONE` | `*` | `Z09_CD_STAGIONE = *` |
| `EW2_CD_COMPOSIZIONE` | `00012` | `Z09_CD_COMPOSIZIONE = 00012` |

Stessa verifica su cliente `1869`, disposizione 2026/8562: `CAPI / T100 / . / PE 27 / 00001` → esiste in Z09 (`data_ins` 2026-10-08).

Quindi la join è:

```sql
ON  c.codice_cliente      = r.ew2_cd_cliente
AND c.codice_articolo     = r.ew2_cd_articolo_fattura
AND c.codice_ciclo        = r.ew2_cd_ciclo
AND c.codice_linea        = r.ew2_cd_linea
AND c.codice_stagione     = r.ew2_cd_stagione
AND c.codice_composizione = r.ew2_cd_composizione
```

### 3.2 Valori jolly `.` e `*`

In Z09 i valori `.` (linea 84%, stagione 59%, composizione 58% delle testate) e `*` stanno per «qualsiasi». Nei campioni EW2 la riga di disposizione riporta **già** il valore jolly del ciclo selezionato (es. stagione `*`), quindi la join esatta è quella corretta. Va comunque misurata la copertura (query §9.2): se una quota significativa di righe EW2 non trova Z09 in join esatta, aggiungere un fallback a specificità decrescente (stagione → `.`/`*`, poi composizione, poi linea).

### 3.3 Righe storico senza ciclo in anagrafica

Possono esistere righe EW2 il cui ciclo è stato cancellato/rinominato in Z09. Comportamento proposto:

- default: non mostrarle (il risultato è il ciclo);
- opzione «includi utilizzi senza ciclo in anagrafica»: mostrarle come riga con badge «ciclo non più in anagrafica» usando `EW2_CD_CICLO`, `EW2_CD_CICLO_CLI` e la descrizione da `STORICO_DISPOSIZIONI.Z09_DS_CICLO` se disponibile.

---

## 4. Mappa filtri → sorgente

| Filtro UI | Sorgente | Colonne | Match proposto |
| :--- | :--- | :--- | :--- |
| Cliente *(esistente)* | Cicli | `cicli_testate.codice_cliente` | esatto |
| Stagione *(esistente)* | Cicli | `cicli_testate.codice_stagione` | esatto (+ alias `stagioni_aliases.py`) |
| Codice ciclo *(esistente)* | Cicli | `codice_ciclo`, `codice_ciclo_cli` | parziale |
| Articolo cliente *(esistente, da rinominare)* | Cicli | `codice_articolo`, `articoli_cliente.ds_articolo` | parziale |
| Composizione *(esistente)* | Cicli | `codice_composizione`, `composizioni.ds_composizione` | parziale |
| Descrizione ciclo *(esistente)* | Cicli | `ds_ciclo`, `ds_ciclo_bolle_fat` | confluisce nella ricerca **Fasi** (vedi §6) |
| **Fasi / parole chiave** | Cicli (+ opz. Storico) | `fasi_lavoro.ds_fase`, `cicli_fasi.note`, `cicli_testate.ds_ciclo`, `ds_ciclo_bolle_fat`, `note`; opz. `ew2_note`, `ew2_note_ricetta` | semantico (§6) |
| **Colore** | Storico | `ew2_cd_colore`, `ew2_ds_colore` | codice: prefisso/esatto; descrizione: trigrammi |
| **Tessuto** | Storico | da confermare (§5.3): `ew2_qualita`, `ew2_ds_articolo`, `ew2_cd_colore` (parte dopo `/`), `ew2_note` | token esatto, case-insensitive |
| **Commessa** | Storico | `ew2_rif_disp_cliente` (+ `ew1_rifer_cliente`) | token (vedi §5.2) |
| **Modello** | Storico | `ew2_modello` (+ `ew2_ds_articolo`) | parziale / trigrammi |
| **Articolo fiscale** | Storico | `ew2_cd_articolo_fiscale` | esatto |
| *(utile)* Data bolla da/a | Storico | `ew1_data_bolla_cli` | range |
| *(utile)* Cartella | Storico | `ew2_cd_cartella` | esatto |

---

## 5. Dettaglio filtri storico

### 5.1 Colore

- `EW2_CD_COLORE` (es. `125/2829`, `04`) e `EW2_DS_COLORE` (es. `NAVY ***REATT`, `VERDE PRATO M /TRM`, `SUGAR (PERLA)`).
- Le descrizioni contengono suffissi tecnici (`***REATT`, `/TRM`): la ricerca deve essere per **contenimento/token**, non uguaglianza. `navy` → `ILIKE '%NAVY%'`; per tollerare refusi (`tortora`/`tortoira`) `word_similarity(q, ew2_ds_colore) > 0.5`.
- Se l'input è un codice (solo cifre/`/`) cercare su `ew2_cd_colore` con `ILIKE 'q%'` o uguaglianza della parte prima di `/`.
- Facoltativo: decodifica `G31_COLORI` (oggi non esportata).

### 5.2 Commessa (`RIF. DISP. CLIENTE`)

Valori reali: `489`, `489/502/570/571`, `489/502/571`, `57 CAS27F`, `27601 TRM`, `27600/1 TRM`.

Il campo contiene **più commesse** separate da `/` e talvolta suffissi. Il match `ILIKE '%489%'` darebbe falsi positivi (`1489`, `4890`). Proposta: match per token.

```sql
-- token = sequenze alfanumeriche separate da / spazio , ; -
:commessa = ANY (regexp_split_to_array(UPPER(r.ew2_rif_disp_cliente), '[/\s,;\-]+'))
-- fallback se nessun risultato: ILIKE '%' || :commessa || '%'
```

Per prestazioni conviene una colonna generata `ew2_rif_tokens text[]` con indice GIN (§8).

`EW1_RIFER_CLIENTE` (testata) è un riferimento affine: includerlo in OR finché non si conferma con l'utente che la «Commessa» della UI Wi@sh3 punta solo a EW2 (cfr. `analisi-storico.md` §2.1, dove era indicato come candidato).

### 5.3 Tessuto (es. `S3651`) — da confermare

Non esiste una tabella tessuti in `INTEX2` (catalogo `scripts/all-tables-intex.txt`) né una colonna con questo nome in EW2. Indizi dai campioni:

- `EW2_DS_ARTICOLO = 'CAPI/CAMICIA 2829 BUBACO 100%CO'` e `EW2_CD_COLORE = '125/2829'`: il `2829` compare in entrambi → probabile **codice tessuto** del cliente, ripetuto nel codice colore (colore `125` del tessuto `2829`);
- `EW2_QUALITA` (VARCHAR 20) è semanticamente il candidato naturale («qualità» = tessuto), ma è vuota nei campioni visti.

Query Oracle per individuare il campo (eseguire prima di implementare):

```sql
SELECT 'QUALITA' campo, COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_QUALITA) LIKE '%S3651%'
UNION ALL SELECT 'DS_ARTICOLO', COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_DS_ARTICOLO) LIKE '%S3651%'
UNION ALL SELECT 'CD_COLORE',   COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_CD_COLORE) LIKE '%S3651%'
UNION ALL SELECT 'DS_COLORE',   COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_DS_COLORE) LIKE '%S3651%'
UNION ALL SELECT 'MODELLO',     COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_MODELLO) LIKE '%S3651%'
UNION ALL SELECT 'NOTE',        COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_NOTE) LIKE '%S3651%'
UNION ALL SELECT 'RIF_DISP',    COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_RIF_DISP_CLIENTE) LIKE '%S3651%'
UNION ALL SELECT 'SCATOLA',     COUNT(*) FROM INTEX2.EW2_RIGHE_DISPOSIZIONI WHERE UPPER(EW2_SCATOLA) LIKE '%S3651%';

-- Riempimento di QUALITA negli ultimi 365 gg
SELECT COUNT(*), COUNT(r.EW2_QUALITA)
FROM INTEX2.EW2_RIGHE_DISPOSIZIONI r, INTEX2.EW1_TESTATA_DISPOSIZIONI t
WHERE r.EW2_ANNO_DISPOSIZIONE = t.EW1_ANNO_DISPOSIZIONE
  AND r.EW2_NR_DISPOSIZIONE   = t.EW1_NR_DISPOSIZIONE
  AND t.EW1_DATA_BOLLA_CLI >= TRUNC(SYSDATE) - 365;
```

Finché non c'è conferma, il filtro tessuto cerca il **token** in `ew2_qualita`, `ew2_ds_articolo`, parte dopo `/` di `ew2_cd_colore` e `ew2_note` (stessa logica a token della commessa, così `S3651` non matcha `S36510`).

### 5.4 Modello

`EW2_MODELLO` (VARCHAR 20) contiene il nome/codice capo del cliente: `BUBACO`, `FB0056 SLIDERS`, `FB0054 BUCKLE`, `MT 30 CR0645`. Il nome compare spesso anche in `EW2_DS_ARTICOLO` (`CAPI/CAMICIA 2829 BUBACO 100%CO`).

Match: `ew2_modello ILIKE '%q%' OR ew2_ds_articolo ILIKE '%q%'`, con fallback `word_similarity(q, ew2_modello) > 0.5` per refusi.

### 5.5 Codice articolo fiscale — verifica filtro esistente

| Concetto | Dove | Esempi | Nel filtro «Articolo» attuale? |
| :--- | :--- | :--- | :--- |
| Articolo **cliente** | `Z09_CD_ARTICOLO_CLIENTE` (= `EW2_CD_ARTICOLO_FATTURA`), descr. `CWA_ARTICOLI_CLIENTE` | `00060 CAPI/TIRELLE`, `00073 NASTRI`, `CAPI` | **Sì** |
| Articolo **fiscale** | `EW2_CD_ARTICOLO_FISCALE`, descr. `CW1_ARTICOLI_FISCALI` | quasi sempre `CAPI` nei campioni | **No** |

Il filtro attuale è corretto come «articolo cliente», ma **non** è l'articolo fiscale della schermata Wi@sh3. Proposta:

- rinominare l'etichetta UI attuale in **«Articolo cliente»**;
- aggiungere **«Articolo fiscale»** come filtro storico su `ew2_cd_articolo_fiscale` (select con valori distinti, visto che sono pochi; descrizioni da `CW1` se esportata).

Dato che l'articolo fiscale ha bassa selettività (`CAPI` quasi ovunque), è utile soprattutto combinato con gli altri filtri. Da confermare con l'utente se intendeva in realtà l'articolo cliente.

---

## 6. Ricerca semantica su fasi, descrizioni e note

### 6.1 Il problema

I testi sono abbreviati, senza un formato fisso:

- `ds_ciclo`: `S.RETE+TINTO+MPELO+A/S+ASC.APPESA+ARROTO`, `SBZ+POM+ENZ+BLEACH+TINTO`, `TI.COL.AC+RICETTAZIONE INTERNA`, `PURGA/SBOZZ+TINTO REATTIVO`;
- `fasi_lavoro.ds_fase`: `(ti)+PERLITE-ENZIMA`, `(ti.R)+MANGIAPELO`, `M.PELO+(ti)`, `STW 90+BLEACHED`;
- `cicli_fasi.note`: `A FREDDO`, `REATTIVA`, `40?` (encoding perso di `40°`), `ZETASOFT AK`, `PERMANGANATO`.

Lo stesso concetto ha molte forme: *mangiapelo* = `MPELO` = `M.PELO`; *tinto reattivo* = `TI.R` = `REATT` = `REATT.` = `REATTIVO` = `REATTIVA`; *stone wash* = `STW` = `SW`; *sbozzima* = `SBZ` = `SBOZZ`; *pomice* = `POM`; *enzima* = `ENZ` = `ENZ.` = `ENZIMI`.

### 6.2 Documento di ricerca per ciclo

Precalcolare un testo unico per ciclo, così il filtro diventa una sola condizione indicizzata invece di `EXISTS` su 320k fasi:

```text
search_doc(ciclo) = norm(ds_ciclo) ‖ norm(ds_ciclo_bolle_fat) ‖ norm(note testata)
                  ‖ Σ norm(ds_fase) ‖ Σ norm(note fase)
```

Normalizzazione `norm()` (funzione SQL `IMMUTABLE`):

1. `UPPER` + `unaccent` (`DEGRADE'` → `DEGRADE`);
2. `?` dopo cifra → `°` (`40?` → `40°`);
3. separatori `+ / . ( ) - ,` → spazio, **mantenendo** anche la forma originale compatta per i codici (`TI.R`, `A/S`);
4. espansione abbreviazioni tramite dizionario (§6.3) → si aggiungono le forme estese al documento (`MPELO` → `MPELO MANGIAPELO`).

Il documento si salva in una tabella/materialized view `cicli_search` (§8) con indice GIN trigrammi e `tsvector` (`italian`).

### 6.3 Dizionario sinonimi/abbreviazioni

Tabella `ricerca_sinonimi(gruppo, termine)`, popolata a partire dal vocabolario reale (375 fasi Z02 + token più frequenti di `ds_ciclo`). Primo nucleo dai dati:

| Gruppo (forma canonica) | Varianti osservate |
| :--- | :--- |
| TINTURA | `TINTO`, `TINTURA`, `TI`, `TI.`, `T.`, `(ti)` |
| REATTIVO | `REATTIVO`, `REATTIVA`, `REATT`, `REATT.`, `TI.R`, `(ti.R)` |
| MANGIAPELO | `MANGIAPELO`, `MPELO`, `M.PELO` |
| ENZIMA | `ENZIMA`, `ENZIMI`, `ENZ`, `ENZ.` |
| POMICE | `POMICE`, `POM` |
| PERLITE | `PERLITE`, `PERL` |
| STONE WASH | `STW`, `SW`, `STONE` |
| SBOZZIMA | `SBOZZIMA`, `SBOZZ`, `SBZ` |
| CANDEGGIO | `BLEACH`, `BLEACHED`, `SBIANCA` |
| CARTEGGIO | `CARTEGGIO`, `CART` |
| LAVAGGIO | `LAV`, `LAV.`, `LAVATO`, `LAVAGGIO` |
| TRATTAMENTO | `TR.`, `TRATT.`, `TRATTAMENTO` |
| PIGMENTO | `PIGMENTO`, `PIG`, `PIG.TO` |
| SWEET | `SWE`, `SWEET` |
| ROTTURE | `ROTTURE`, `ROTT` |
| SPRUZZO | `SPRUZZO`, `SPR` |
| DEGRADE | `DEGRADE`, `DEGRADE'` |
| STROPICCIO | `STROPICCIO`, `STROP` |
| COLORE ACIDO *(da confermare)* | `TI.COL.AC`, `T.COL.AC`, `COL.AC`, `AC` |
| A/S *(da confermare)* | `A/S` |

Le voci *da confermare* vanno validate con il reparto tecnico. Il dizionario è dato, non codice: si aggiorna senza deploy.

### 6.4 Algoritmo di match

Input: elenco di parole chiave (chip nella UI), es. `stone wash`, `mangiapelo`, `reattivo`.

Per ogni parola chiave:

1. **Normalizza** come il documento.
2. **Espandi** con il dizionario: `mangiapelo` → {`MANGIAPELO`, `MPELO`, `M.PELO`}.
3. **Match** sul `search_doc` del ciclo, a cascata:
   - termine breve (≤ 3 caratteri, es. `TI`, `SW`, `AC`) → regex con confini di parola `\mTI\M` (evita che `TI` matchi ovunque);
   - termine lungo → `search_doc ILIKE '%TERMINE%'` **oppure** `termine <% search_doc` (`word_similarity` di `pg_trgm`, soglia ~0,6) per assorbire varianti morfologiche e refusi (`stropicciato` ≈ `STROPICCIO`, `reattiva` ≈ `REATTIVO`);
   - opzionale: `to_tsvector('italian', search_doc) @@ plainto_tsquery('italian', termine)` per lo stemming italiano.
4. Una parola chiave è soddisfatta se **almeno una** variante matcha.

Tra parole chiave: **AND** di default (il ciclo deve contenere tutti i concetti), con toggle «almeno una» (OR).

L'ordinamento resta cronologico (§7): la similarità serve solo come **soglia**, non per ordinare. In risposta si restituisce per ogni ciclo l'elenco dei termini/fasi che hanno matchato, per evidenziarli in UI (es. badge «MPELO (fase 30)»).

### 6.5 Fase 2: espansione semantica con embeddings

Per concetti non coperti dal dizionario (es. utente scrive `effetto vissuto` → `USED`, `DIRTY`, `OLD`):

- `pgvector` è già nell'immagine `timescale/timescaledb-ha:pg16` (`data/docker-compose.yml`);
- si calcolano gli embeddings **solo del vocabolario** (375 `ds_fase` + token/frasi distinti di `ds_ciclo` e note: qualche migliaio di voci), non dei 108k cicli → costo trascurabile, ricalcolo solo per testi nuovi;
- a query time: embedding della parola chiave → top-k voci di vocabolario con similarità coseno sopra soglia → aggiunte alle varianti del passo 2 → stesso match del §6.4.

Alternativa/complemento: espansione via LLM con il servizio esistente (`backend/LLMservice.py`), chiedendo varianti **vincolate al vocabolario** e mettendo il risultato in cache per parola chiave. Più lenta (una chiamata a parola nuova) ma non richiede pipeline embeddings.

In entrambi i casi l'espansione resta **trasparente**: la UI mostra «cercato anche: MPELO, M.PELO» e l'utente può togliere varianti.

### 6.6 Note dello storico (opzionale)

Con il flag «cerca anche nelle note delle disposizioni» la stessa logica si applica a `ew2_note` (es. `A ROVESCIO, C/C7`, `VERIFICARE PESO`, `FARE VASCA PROVA`) e `ew2_note_ricetta`, tramite la join storico (§7.2). `STORICO_DISPOSIZIONI.LISTA_FASI_EXTRA` copre solo l'archivio vecchio e non va usata per il recente.

---

## 7. Query combinata

### 7.1 Principio

```text
RISULTATO = cicli_testate
            ∩ filtri cicli          (WHERE su t)
            ∩ filtro fasi           (match su cicli_search)
            ∩ filtri storico        (EXISTS su ew2 ⋈ ew1, stessa riga, chiave a 6 campi)
ORDINE    = data_ins DESC
```

- Nessun filtro storico attivo → la query storico non si esegue (performance invariata rispetto a oggi); l'arricchimento si calcola **solo per la pagina corrente**.
- Almeno un filtro storico attivo → `EXISTS` (o `JOIN` su CTE aggregata, sotto) obbligatorio.

### 7.2 SQL di riferimento (Postgres)

```sql
WITH storico_match AS (
    SELECT r.ew2_cd_cliente, r.ew2_cd_articolo_fattura, r.ew2_cd_ciclo,
           r.ew2_cd_linea, r.ew2_cd_stagione, r.ew2_cd_composizione,
           MAX(t.ew1_data_bolla_cli)                     AS ultima_bolla,
           COUNT(*)                                      AS n_righe_storico,
           (ARRAY_AGG(DISTINCT r.ew2_rif_disp_cliente))[1:5] AS commesse,
           (ARRAY_AGG(DISTINCT r.ew2_ds_colore))[1:5]        AS colori,
           (ARRAY_AGG(DISTINCT r.ew2_modello))[1:5]          AS modelli
    FROM ew2_righe_disposizioni r
    JOIN ew1_testata_disposizioni t
      ON t.ew1_anno_disposizione = r.ew2_anno_disposizione
     AND t.ew1_nr_disposizione   = r.ew2_nr_disposizione
    WHERE 1=1
      -- tutti i filtri storico sulla STESSA riga r
      AND (:colore    IS NULL OR r.ew2_ds_colore ILIKE '%'||:colore||'%' OR r.ew2_cd_colore ILIKE :colore||'%')
      AND (:commessa  IS NULL OR UPPER(:commessa) = ANY (r.ew2_rif_tokens))
      AND (:modello   IS NULL OR r.ew2_modello ILIKE '%'||:modello||'%' OR r.ew2_ds_articolo ILIKE '%'||:modello||'%')
      AND (:tessuto   IS NULL OR UPPER(:tessuto) = ANY (r.ew2_tessuto_tokens))
      AND (:art_fisc  IS NULL OR r.ew2_cd_articolo_fiscale = :art_fisc)
      AND (:da_bolla  IS NULL OR t.ew1_data_bolla_cli >= :da_bolla)
      AND (:a_bolla   IS NULL OR t.ew1_data_bolla_cli <= :a_bolla)
    GROUP BY 1, 2, 3, 4, 5, 6
)
SELECT t.*, cl.ragione_sociale, ar.ds_articolo, co.ds_composizione, st.ds_stagione, li.ds_linea,
       s.ultima_bolla, s.n_righe_storico, s.commesse, s.colori, s.modelli
FROM cicli_testate t
JOIN storico_match s                                   -- LEFT JOIN se nessun filtro storico
  ON  s.ew2_cd_cliente          = t.codice_cliente
  AND s.ew2_cd_articolo_fattura = t.codice_articolo
  AND s.ew2_cd_ciclo            = t.codice_ciclo
  AND s.ew2_cd_linea            = t.codice_linea
  AND s.ew2_cd_stagione         = t.codice_stagione
  AND s.ew2_cd_composizione     = t.codice_composizione
LEFT JOIN cicli_clienti cl ON ...                      -- join anagrafiche come oggi
JOIN cicli_search cs USING (codice_cliente, codice_articolo, codice_ciclo,
                            codice_linea, codice_stagione, codice_composizione)
WHERE <filtri cicli esistenti>
  AND <match fasi su cs.search_doc, §6.4>
ORDER BY t.data_ins DESC NULLS LAST, t.nr_revisione DESC NULLS LAST, t.codice_ciclo
LIMIT :limit OFFSET :offset;
```

Nel backend la query va costruita dinamicamente come oggi (`_cicli_from_where`), aggiungendo i pezzi solo per i filtri presenti; i parametri `NULL`-check sopra sono solo per leggibilità.

### 7.3 Due viste dei risultati

| Vista | Riga = | Uso |
| :--- | :--- | :--- |
| **Cicli** (default) | un ciclo Z09 | Come oggi, + colonne «Inserito il», «Ultimo utilizzo», «Commesse/colori/modelli» (anteprima). Espansioni: «Fasi» (esistente) e **«Utilizzi»** (righe storico del ciclo, filtrate con gli stessi filtri). |
| **Utilizzi** (toggle) | una riga EW2 | Quando l'utente cerca una commessa/colore specifico e vuole vedere le singole disposizioni (data bolla, nr bolla, rif. commessa, colore, modello, capi/kg) con il ciclo associato. Ordinata per `ew1_data_bolla_cli DESC`. |

Nuovo endpoint per l'espansione «Utilizzi»: `GET /api/cicli/utilizzi?<chiave 6 campi>&<filtri storico>&page=`.

---

## 8. Modifiche schema Postgres

Nuova migration proposta `data/migrations/cicli-storico-search.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
-- fase 2: CREATE EXTENSION IF NOT EXISTS vector;

-- Join ciclo ↔ storico
CREATE INDEX IF NOT EXISTS idx_ew2_ciclo_key ON ew2_righe_disposizioni (
    ew2_cd_cliente, ew2_cd_articolo_fattura, ew2_cd_ciclo,
    ew2_cd_linea, ew2_cd_stagione, ew2_cd_composizione);

-- Ordinamento cronologico
CREATE INDEX IF NOT EXISTS idx_cicli_testate_data_ins
    ON cicli_testate (data_ins DESC NULLS LAST);

-- Filtri storico
CREATE INDEX IF NOT EXISTS idx_ew2_ds_colore_trgm ON ew2_righe_disposizioni USING gin (ew2_ds_colore gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ew2_modello_trgm   ON ew2_righe_disposizioni USING gin (ew2_modello gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ew2_ds_art_trgm    ON ew2_righe_disposizioni USING gin (ew2_ds_articolo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ew2_art_fiscale    ON ew2_righe_disposizioni (ew2_cd_articolo_fiscale);

-- Token commessa / tessuto (colonne generate)
ALTER TABLE ew2_righe_disposizioni
  ADD COLUMN IF NOT EXISTS ew2_rif_tokens text[]
  GENERATED ALWAYS AS (regexp_split_to_array(UPPER(COALESCE(ew2_rif_disp_cliente, '')), '[/\s,;\-]+')) STORED;
CREATE INDEX IF NOT EXISTS idx_ew2_rif_tokens ON ew2_righe_disposizioni USING gin (ew2_rif_tokens);
-- ew2_tessuto_tokens: analogo, sulle colonne confermate in §5.3

-- Dizionario sinonimi
CREATE TABLE IF NOT EXISTS ricerca_sinonimi (
    gruppo   VARCHAR(50)  NOT NULL,
    termine  VARCHAR(50)  NOT NULL,
    PRIMARY KEY (gruppo, termine)
);

-- Documento di ricerca per ciclo (rigenerato dopo ogni import cicli)
CREATE MATERIALIZED VIEW IF NOT EXISTS cicli_search AS
SELECT t.codice_cliente, t.codice_articolo, t.codice_ciclo,
       t.codice_linea, t.codice_stagione, t.codice_composizione,
       norm_search(concat_ws(' ', t.ds_ciclo, t.ds_ciclo_bolle_fat, t.note,
                   string_agg(concat_ws(' ', z.ds_fase, f.note), ' ' ORDER BY f.sequenza))) AS search_doc
FROM cicli_testate t
LEFT JOIN cicli_fasi f USING (codice_cliente, codice_articolo, codice_ciclo,
                              codice_linea, codice_stagione, codice_composizione)
LEFT JOIN fasi_lavoro z ON z.codice_fase = f.codice_fase
GROUP BY 1, 2, 3, 4, 5, 6, t.ds_ciclo, t.ds_ciclo_bolle_fat, t.note;

CREATE UNIQUE INDEX IF NOT EXISTS ux_cicli_search_key ON cicli_search (
    codice_cliente, codice_articolo, codice_ciclo, codice_linea, codice_stagione, codice_composizione);
CREATE INDEX IF NOT EXISTS idx_cicli_search_trgm ON cicli_search USING gin (search_doc gin_trgm_ops);
```

`norm_search(text)` è una funzione SQL `IMMUTABLE` che applica la normalizzazione del §6.2 (wrapper di `unaccent` con dizionario esplicito, necessario per l'uso in indici). Dopo ogni import dei CSV cicli: `REFRESH MATERIALIZED VIEW CONCURRENTLY cicli_search;`.

---

## 9. Prerequisiti dati e verifiche

### 9.1 Copertura temporale dello storico

`extract_upload_tables_storico.py` esporta oggi solo le disposizioni con data bolla negli ultimi **365 giorni**. Cicli inseriti anni fa e mai riusati non risulterebbero cercabili per commessa/colore/modello. Proposta:

1. un dump completo una tantum (`LOOKBACK_DAYS = None`, ~195k testate) importato in Postgres;
2. sync periodico incrementale con lookback breve (es. 30 giorni) in **upsert** (`INSERT … ON CONFLICT DO UPDATE` tramite tabella di staging), invece del `TRUNCATE` + `\copy` attuale che cancellerebbe lo storico vecchio;
3. per l'archivio legacy pre-EW1 valutare l'import di `STORICO_DISPOSIZIONI` (stesse colonne chiave + `Z09_DS_CICLO`, `LISTA_FASI_EXTRA`) come fonte aggiuntiva, in UNION con EW2.

In UI va indicato il periodo coperto dai filtri storico («storico disponibile dal …»).

### 9.2 Copertura della join (Postgres, dopo import)

```sql
SELECT COUNT(*) AS righe_ew2,
       COUNT(*) FILTER (WHERE EXISTS (
         SELECT 1 FROM cicli_testate c
         WHERE c.codice_cliente      = r.ew2_cd_cliente
           AND c.codice_articolo     = r.ew2_cd_articolo_fattura
           AND c.codice_ciclo        = r.ew2_cd_ciclo
           AND c.codice_linea        = r.ew2_cd_linea
           AND c.codice_stagione     = r.ew2_cd_stagione
           AND c.codice_composizione = r.ew2_cd_composizione)) AS con_ciclo_esatto
FROM ew2_righe_disposizioni r
WHERE r.ew2_cd_ciclo IS NOT NULL;
```

Atteso ≥ 95%. Sotto questa soglia: analizzare i mancati (quale campo diverge) e introdurre il fallback jolly del §3.2.

### 9.3 Significato di `data_ins`

L'ordinamento usa `cicli_testate.data_ins` (`Z09_DATA_INS`). Dai dati sembra aggiornarsi alle revisioni (es. cliente 1843 ciclo `T111`: molte stagioni diverse con la stessa `data_ins` 2025-10-29 e `nr_revisione` 4). Va confermato se è «data creazione» o «data ultima revisione»; in ogni caso è la data più vicina a «ultimo ciclo inserito». Spareggio: `nr_revisione DESC`, poi `codice_ciclo`. Le ~680 testate senza data vanno in coda (`NULLS LAST`).

---

## 10. API e UI

### 10.1 Nuovi parametri `GET /api/cicli`

| Parametro | Tipo | Note |
| :--- | :--- | :--- |
| `fasi` | stringa ripetibile (`fasi=mangiapelo&fasi=stone wash`) | parole chiave semantiche |
| `fasi_mode` | `all` \| `any` | default `all` |
| `fasi_note_storico` | `0`/`1` | estende la ricerca a `ew2_note` / `ew2_note_ricetta` |
| `colore` | stringa | codice o descrizione |
| `tessuto` | stringa | token |
| `commessa` | stringa | token di `ew2_rif_disp_cliente` |
| `modello` | stringa | |
| `articolo_fiscale` | stringa | esatto |
| `data_bolla_da`, `data_bolla_a` | data | opzionali, restringono lo storico |
| `vista` | `cicli` \| `utilizzi` | default `cicli` |

Il parametro `articolo` esistente resta invariato (articolo cliente). In risposta, per ogni ciclo, si aggiungono: `data_ins` formattata, `ultima_bolla`, `n_righe_storico`, `commesse[]`, `colori[]`, `modelli[]`, `match_fasi[]` (termini/fasi che hanno soddisfatto la ricerca semantica) e, a livello di risposta, `fasi_espanse` (varianti usate per ogni parola chiave).

### 10.2 Modifiche `CicliPage.jsx`

- Form diviso in due gruppi: **«Ciclo»** (cliente, stagione, codice ciclo, articolo cliente, composizione) e **«Storico disposizioni»** (commessa, modello, colore, tessuto, articolo fiscale, data bolla da/a).
- Campo **«Fasi / lavorazioni»** con input a chip (Invio aggiunge una parola chiave), toggle tutte/almeno una, checkbox «anche note disposizioni»; sotto i chip, le varianti usate dalla ricerca.
- Il campo «Descrizione ciclo» confluisce nel campo Fasi (stessa sorgente testuale) oppure resta come filtro letterale: da decidere.
- Tabella: nuova colonna **«Inserito il»** (prima colonna, ordinamento fisso discendente) e **«Ultimo utilizzo»**; badge con i termini che hanno matchato; nuova espansione **«Utilizzi»** accanto a «Fasi».
- Toggle vista **Cicli / Utilizzi**.

---

## 11. Prestazioni

- Filtri storico: con l'indice sulla chiave a 6 campi e i GIN trigrammi, la CTE `storico_match` lavora su EW2 (~41k righe/anno, ~800k stimate su full dump) → ordine delle decine di ms.
- Filtro fasi: un solo `search_doc` per ciclo (108k righe) con GIN trigrammi; senza la materialized view, `EXISTS` su `cicli_fasi` + `fasi_lavoro` per ogni variante sarebbe molto più lento.
- `COUNT(*)` per la paginazione: stessa query senza `ORDER BY`/`LIMIT`, come oggi.
- Arricchimento storico senza filtri storico: calcolato solo per i ≤ 50 cicli della pagina (una query con `WHERE (chiave) IN (…)`).

---

## 12. Punti aperti da confermare con l'utente

1. **Tessuto**: in quale campo sta `S3651`? (query §5.3)
2. **Commessa**: solo `EW2_RIF_DISP_CLIENTE` o anche `EW1_RIFER_CLIENTE`?
3. **Articolo fiscale**: serve davvero il fiscale (`CAPI`, poco selettivo) o l'articolo cliente già presente?
4. **`data_ins`**: data creazione o ultima revisione? Va bene come criterio «ciclo più recente»?
5. **Dizionario**: validazione abbreviazioni dubbie (`A/S`, `AC`, `Q`, `EVO`, `RTF`, `DIPS`, …).
6. **Profondità storico**: quanti anni importare (impatta §9.1).
7. **Descrizione ciclo**: unire al campo Fasi o tenerlo separato e letterale?

---

## 13. Piano di implementazione

| Step | Contenuto | Dipende da |
| :--- | :--- | :--- |
| 1 | Verifiche Oracle/Postgres: tessuto (§5.3), copertura join (§9.2) | — |
| 2 | Export/import storico: dump completo + sync incrementale in upsert | 1 |
| 3 | Migration `cicli-storico-search.sql`: indici, colonne token, `ricerca_sinonimi`, `norm_search`, `cicli_search` | 1 |
| 4 | Backend: ordinamento `data_ins DESC`; filtri storico (commessa, modello, colore, tessuto, articolo fiscale, date bolla) con `EXISTS`/CTE; arricchimento pagina; endpoint `/api/cicli/utilizzi` | 2, 3 |
| 5 | Backend: ricerca fasi (normalizzazione, espansione dizionario, trigrammi, `match_fasi`) | 3 |
| 6 | Frontend: nuovi campi, chip fasi, colonne «Inserito il»/«Ultimo utilizzo», espansione Utilizzi, toggle vista; rinomina «Articolo» → «Articolo cliente» | 4, 5 |
| 7 | Fase 2: embeddings del vocabolario con `pgvector` (o espansione LLM con cache) | 5 |
