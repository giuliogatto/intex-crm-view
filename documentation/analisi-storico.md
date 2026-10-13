# Analisi Storico Disposizioni Cliente — Database Oracle Intex

Documento di sintesi della mappatura tra la schermata gestionale **Wi@sh3** «Storico Disposizioni Completo» (storico disposizioni cliente) e le tabelle Oracle nello schema `INTEX2`.

Verificato su DB `INT2DB` (ottobre 2026) confrontando export CSV, count Oracle e foto delle schermate (cliente **2594 JACOB COHEN COMPANY SPA**).

**Connessione sqlplus:** `INTEX2/SD@192.168.1.10:1521/INT2DB`

**Script correlati:**

| File | Ruolo |
| :--- | :--- |
| `scripts/extract_upload_tables_storico.py` | Export Oracle → CSV → SFTP (`/var/data_imports/intex/`) |
| `data/migrations/create-storico-disposizioni-tables.sql` | Tabelle Postgres lato TimescaleDB |
| `scripts/all-tables-intex.txt` | Catalogo tabelle Oracle |

---

## 1. Conclusione (verdetto)

La schermata **Storico Disposizioni Completo** mostra lo storico **live** delle disposizioni di produzione. La fonte operativa è:

| Ruolo | Oggetto Oracle | Ordine di grandezza (ott 2026) |
| :--- | :--- | ---: |
| **Testata disposizione** | `INTEX2.EW1_TESTATA_DISPOSIZIONI` | ~195.000 |
| **Righe disposizione** | `INTEX2.EW2_RIGHE_DISPOSIZIONI` | proporzionale (~4 righe/testata in media recente) |
| **Chiave** | `(ANNO_DISPOSIZIONE, NR_DISPOSIZIONE)` + su EW2 `RIGA_DISPOSIZIONE` | — |
| **Filtro temporale UI** | `EW1_DATA_BOLLA_CLI` («Da/A Data Bolla») | — |

### Ipotesi scartata: `STORICO_DISPOSIZIONI` come sorgente della UI

| Oggetto | Perché scartato come fonte della schermata live |
| :--- | :--- |
| `INTEX2.STORICO_DISPOSIZIONI` | Nome e colonne sembrano fatti per la UI, ma è un **archivio denormalizzato fermo**. Totale ~673.000 righe; con `EW1_DATA_BOLLA_CLI` negli ultimi 365 giorni ≈ **13** righe; `IS NULL` ≈ **84**. Le disposizioni recenti di EW1 **non** ci sono come righe in STORICO. |

**Prova empirica (cliente 2594, bolle 10/01/2026–10/12/2026):**

```sql
SELECT COUNT(*)
FROM INTEX2.EW1_TESTATA_DISPOSIZIONI t,
     INTEX2.EW2_RIGHE_DISPOSIZIONI r
WHERE r.EW2_ANNO_DISPOSIZIONE = t.EW1_ANNO_DISPOSIZIONE
  AND r.EW2_NR_DISPOSIZIONE   = t.EW1_NR_DISPOSIZIONE
  AND t.EW1_CD_CLIENTE = '2594'
  AND t.EW1_DATA_BOLLA_CLI BETWEEN TO_DATE('10/01/2026','DD/MM/YYYY')
                               AND TO_DATE('10/12/2026','DD/MM/YYYY');
-- → 2014 righe (allineato alla griglia Wi@sh3)
```

La UI quindi **ricalcola** (o legge un altro percorso live basato su EW1/EW2 + join), non legge il pezzo Oracle `STORICO_DISPOSIZIONI` per i dati recenti.

> Nota: in [`analisi-offerte.md`](./analisi-offerte.md) la riga che collegava «Storico Disposizioni Completo → `STORICO_DISPOSIZIONI`» è **superata** da questa analisi.

---

## 2. Schermata Wi@sh3 — cosa mostra

Titolo finestra: **Storico Disposizioni Completo**.

Legenda griglia (testo rosso): *«Se il colore griglia è rosso, la fase è un Ripreso»*.

### 2.1 Filtri ricercabili («Parametri di Selezione»)

| Campo UI | Colonna Oracle (EW1/EW2) | Note |
| :--- | :--- | :--- |
| Cod. Cliente | `EW1_CD_CLIENTE` / `EW2_CD_CLIENTE` | Nome: join `R07_CLIENTI.R07_RAGIONE_SOC` |
| Cod. Articolo Fiscale | `EW2_CD_ARTICOLO_FISCALE` | Desc: `CW1_ARTICOLI_FISCALI` |
| Da / A Data Bolla | `EW1_DATA_BOLLA_CLI` | Campo corretto per il filtro data UI |
| Commessa | candidato `EW1_RIFER_CLIENTE` | Da confermare semanticamente |
| Cod. Ciclo | `EW2_CD_CICLO` | Desc: `Z09_TESTATE_CICLI_LAVORAZIONE` |
| Parte del codice ciclo | `EW2_CD_CICLO` con `LIKE` | Match parziale |
| Cod. Composizione | `EW2_CD_COMPOSIZIONE` | Desc: `CW4_COMPOSIZIONI` |
| Cartella | `EW2_CD_CARTELLA` | Spesso = codice cliente |
| Colore | `EW2_CD_COLORE` / `EW2_DS_COLORE` | Anagrafica: `G31_COLORI` |
| Tipi di DDT da considerare | `EW2_FLAG_TP_DDT` | Conto lavoro / riparazione / vendita / visione (codici 1 char; mappa lettera da Distinct) |
| Tipologie da considerare | `EW2_FLAG_TP_PROD` | Documentato: **T**=Prototipi, **C**=Campionari, **P**=Produzione, **B**=Ceste/Bancali, altri (campioni colori / capi in visione) da allineare |

Su EW1 esiste anche `EW1_DATA_IMMISSIONE` (data inserimento sistema): **non** è il filtro «Data Bolla» della schermata.

### 2.2 Colonne griglia (esempi dalle foto)

Colonne tipiche (la griglia è scrollabile orizzontalmente; a sinistra rif./quantità, a destra reparto/vasche/terzisti):

| Colonna UI | Su EW1/EW2 | Serve anche (join / aggregato) |
| :--- | :--- | :--- |
| Cod. Cliente / Ragione Sociale | `EW1_CD_CLIENTE` | `R07_RAGIONE_SOC` |
| Data Bolla / Nr. Bolla | `EW1_DATA_BOLLA_CLI` / `EW1_NR_BOLLA_CLI` | — |
| Cod. / Articolo Fiscale | `EW2_CD_ARTICOLO_FISCALE` | `CW1_DS_ARTICOLO_FI` |
| Rif. Disp. Cliente | `EW2_RIF_DISP_CLIENTE` | — |
| Capi / Kg Caricati | `EW2_NR_CAPI_CARICATI` / `EW2_KG_CARICATI` | — |
| Riga Dispos. | `EW2_RIGA_DISPOSIZIONE` | — |
| Cartella | `EW2_CD_CARTELLA` | — |
| Chiuso | `EW1_FLAG_CHIUSO` / `EW2_FLAG_CHIUSO` | — |
| Tipo Prod. | `EW2_FLAG_TP_PROD` | desc tipo (in STORICO: `EW2_FLAG_TP_PROD_DESC`) |
| Cod. Comp. / Composizione | `EW2_CD_COMPOSIZIONE` | `CW4_DS_COMPOSIZIONE` |
| Ds. Stagione | `EW2_CD_STAGIONE` | `Z11_DS_STAGIONE` |
| Cod. Reparto / Reparto | `EW2_CD_REPARTO` | `Z01_DS_REPARTO` |
| Ripreso | `EW2_NR_RIPRESO` (numerico) | flag S/N UI: tipicamente da produzione (`P07_FLAG_RIPRESO` in STORICO) |
| Capi/Kg Lavorati, non lavorati, Evasi | proxy parziali `*_PROD` / `*_DDT` | in STORICO: `CAPILAVORATI`, `KGLAVORATI`, `CAPINONLAVORATI`, `KGNONLAVORATI`, `CAPIEVASI`, `KGEVASI` |
| Cartellini | no | aggregato da `P06`/`P07` (in STORICO: `CARTELLINI`) |
| Vasche | solo `EW2_CD_VASCA` | aggregato `P28` (in STORICO: `VASCHE`) |
| Terzisti | no | in STORICO: `FORNITORI` |
| Lista Fasi Extra | no | in STORICO: `LISTA_FASI_EXTRA` |
| Note | `EW2_NOTE` / `EW2_NOTE_RICETTA` | — |

**Sintesi:** EW1+EW2 bastano per **tutti i filtri di ricerca** e per una griglia «core». Per replicare la griglia completa denormalizzata della UI servono join/aggregati (come faceva `STORICO_DISPOSIZIONI` quando era aggiornato).

---

## 3. Ruolo delle tabelle

### 3.1 Core disposizioni (da usare)

#### `EW1_TESTATA_DISPOSIZIONI` — testata

Una riga = una disposizione (documento di carico / disposizione cliente).

Campi principali:

| Colonna | Significato |
| :--- | :--- |
| `EW1_ANNO_DISPOSIZIONE`, `EW1_NR_DISPOSIZIONE` | PK |
| `EW1_DATA_BOLLA_CLI` | Data bolla cliente (filtro UI) |
| `EW1_NR_BOLLA_CLI` | Numero bolla cliente |
| `EW1_CD_CLIENTE` | Cliente |
| `EW1_RIFER_CLIENTE` | Riferimento / possibile «Commessa» |
| `EW1_CD_LINEA`, `EW1_CD_STAGIONE` | Linea / stagione |
| `EW1_FLAG_CHIUSO` | Chiuso S/N |
| `EW1_DATA_IMMISSIONE` | Data inserimento in gestionale |
| `EW1_CD_PROVENIENZA` | Provenienza |

#### `EW2_RIGHE_DISPOSIZIONI` — righe

Una riga = dettaglio articolo/colore/ciclo della disposizione.

Campi principali (oltre la chiave a 3 campi):

| Area | Colonne |
| :--- | :--- |
| Quantità caricate | `EW2_NR_CAPI_CARICATI`, `EW2_KG_CARICATI` |
| Articolo / ciclo / composizione | `EW2_CD_ARTICOLO_FISCALE`, `EW2_CD_ARTICOLO_FATTURA`, `EW2_CD_CICLO`, `EW2_CD_COMPOSIZIONE`, `EW2_DS_ARTICOLO` |
| Cartella / colore | `EW2_CD_CARTELLA`, `EW2_CD_COLORE`, `EW2_DS_COLORE` |
| Riferimento cliente | `EW2_RIF_DISP_CLIENTE` |
| Note | `EW2_NOTE`, `EW2_NOTE_RICETTA` |
| Tipologie | `EW2_FLAG_TP_PROD`, `EW2_FLAG_TP_DDT` |
| Produzione / DDT (proxy) | `EW2_NR_CAPI_PROD`, `EW2_KG_PROD`, `EW2_NR_CAPI_DDT`, `EW2_KG_DDT` |
| Vasca / reparto / ripreso | `EW2_CD_VASCA`, `EW2_CD_REPARTO`, `EW2_NR_RIPRESO` |
| Chiusura / cliente / stagione | `EW2_FLAG_CHIUSO`, `EW2_CD_CLIENTE`, `EW2_CD_STAGIONE`, `EW2_CD_STAGIONE_PROD` |

Join testata↔righe:

```text
EW2_ANNO_DISPOSIZIONE = EW1_ANNO_DISPOSIZIONE
EW2_NR_DISPOSIZIONE   = EW1_NR_DISPOSIZIONE
```

#### `EW3_CICLI_DISPOSIZIONI` / `EW4_MATERIALI_DISPOSIZIONI`

Dettaglio ciclo e materiali legati alla disposizione. Presenti in `all-tables-intex.txt`; **non** ancora esportati nello script (colonne di join da verificare su DB prima di aggiungerli).

### 3.2 `STORICO_DISPOSIZIONI` — archivio denormalizzato (non live)

Oggetto Oracle con ~59 colonne che **assomiglia** alla griglia UI completa: già join di cliente, articolo fiscale, ciclo, composizione, stagione, quantità aggregate, `CARTELLINI`, `VASCHE`, `FORNITORI`, `LISTA_FASI_EXTRA`, `P07_FLAG_RIPRESO`, ecc.

| Aspetto | Dettaglio |
| :--- | :--- |
| Totale righe | ~673.000 |
| Bolle ultimi 365 gg | ~13 |
| `EW1_DATA_BOLLA_CLI` NULL | ~84 |
| Interpretazione | Snapshot/archivio **non aggiornato** con le disposizioni recenti; il gestionale non lo usa (più) come fonte della schermata live |
| Uso consigliato | Opzionale, dump full raro (`EXPORT_STORICO_ARCHIVE = True`); **non** per sync incrementale della UI |

Colonne aggregate tipiche presenti solo (o soprattutto) qui rispetto a EW2 grezzo: `CAPIEVASI`, `KGEVASI`, `CAPILAVORATI`, `KGLAVORATI`, `CAPINONLAVORATI`, `KGNONLAVORATI`, `BOLLE`, `CARTELLINI`, `VASCHE`, `FORNITORI`, `LISTA_FASI_EXTRA`, descrizioni già risolte (`R07_RAGIONE_SOC`, `CW4_DS_COMPOSIZIONE`, `Z09_DS_CICLO`, `Z11_DS_STAGIONE`, `Z01_DS_REPARTO`, …).

### 3.3 Lookup / anagrafiche collegate ai filtri e alle descrizioni

| Tabella | Uso |
| :--- | :--- |
| `R07_CLIENTI` | Ragione sociale cliente |
| `CW1_ARTICOLI_FISCALI` | Descrizione articolo fiscale |
| `CWA_ARTICOLI_CLIENTE` | Articolo cliente |
| `CW4_COMPOSIZIONI` (+ `CW5_…`) | Descrizione composizione |
| `Z09_TESTATE_CICLI_LAVORAZIONE` | Descrizione ciclo, reparto statistico |
| `Z08_CICLI_LAVORAZIONE` / `Z02_FASI_DI_LAVORO` | Fasi / lista fasi extra |
| `Z11_STAGIONI` | Descrizione stagione |
| `G31_COLORI` | Descrizione colore anagrafica |
| `Z01_REPARTI` | Descrizione reparto |
| `CW0_LINEA_TINTORIA` | Descrizione linea |
| `CW8_PROVEN_DESTINAZ` | Provenienza / destinazione |
| `Z12_CAUSALI_RIPRESO` | Causali ripreso |
| `Z05_TIPI_CARTELLINI` | Tipi cartellino |

### 3.4 Produzione collegata (aggregati griglia)

| Tabella | Uso tipico in griglia |
| :--- | :--- |
| `P06_CARTELLINI_PROD` | Cartellini di produzione |
| `P07_CICLI_CARTELLINI` | Cicli su cartellino; `P07_FLAG_RIPRESO` (riga rossa UI) |
| `P12_CICLI_CARTELLINI` | Variante cicli cartellini |
| `P24_AVANZAMENTI_CARTELLINI` | Avanzamenti (lavorato) |
| `P28_VASCHE_CARTELLINI` | Vasche per cartellino |
| `CW7_VASCHE_TINTURA` / `CW9_RAGGRUPP_VASCHE` | Anagrafica vasche |
| `D02_DDT_TESTATA` / `D03_DDT_RIGHE_ART` / `D04_CARTELLINI_USCITI` | DDT / uscite (evasi) |
| `R01_FORNITORI` | Terzisti |
| `I01_TIPOLOGIA_BOLLE` / `I02_TESTATE_DDT_CL` / `I03_RIGHE_DDT_CL` | Tipologiche bolle lato cliente |

Queste tabelle **non** sono nello sync regolare attuale: la griglia Postgres oggi si basa su EW1/EW2 importati; gli aggregati si potranno ricostruire in seguito.

### 3.5 Altri schema (fuori scope operativo)

`INTEXPLURIMPRESA.DISPOSIZIONI`, `CONTOLAVORO`, e omologhi in `INTEXGR` / `NEXSTYLE`: non risultano la fonte della schermata Intex2 analizzata.

---

## 4. Perché sembrava `STORICO_DISPOSIZIONI` (e perché no)

1. **Nome** uguale al titolo schermata.
2. **Colonne** allineate 1:1 a filtri + griglia (incluse `VASCHE`, `FORNITORI`, `CARTELLINI`, quantità calcolate).
3. Documentazione precedente (`analisi-offerte.md`) la citava come destinazione della schermata.

Ma:

| Evidenza | Valore |
| :--- | :--- |
| Export STORICO ultimi 14/365 gg | ~13 righe |
| Export EW1/EW2 ultimi 365 gg | ~11.193 / ~40.763 |
| Count EW1⋈EW2 Jacob Cohen 2026 | **2014** (come in UI) |
| Count STORICO ultimi 365 gg su data bolla | **13** |
| EXISTS STORICO ∩ EW1 recenti | ancora ~**13** → non è un filtro data «sbagliato», mancano le **righe** |

Conclusione: `EW1_DATA_BOLLA_CLI` **è** il campo data corretto; su STORICO è valorizzato ma quasi solo su bolle vecchie. L’archivio non viene più popolato in parallelo a EW1/EW2.

---

## 5. Pipeline export / import (stato attuale)

### 5.1 Export

Script: `scripts/extract_upload_tables_storico.py`

- `LOOKBACK_DAYS = 365` (o `None` = full EW1/EW2)
- `EXPORT_STORICO_ARCHIVE = False` (default): esporta solo EW1 + EW2
- Destinazione SFTP: host Debian, path chroot `/intex/` → host **`/var/data_imports/intex/`**
- File: `{timestamp}_ew1_testata_disposizioni.csv`, `{timestamp}_ew2_righe_disposizioni.csv`

### 5.2 Tabelle Postgres

Migration: `data/migrations/create-storico-disposizioni-tables.sql`

- `ew1_testata_disposizioni`
- `ew2_righe_disposizioni`
- `storico_disposizioni` (opzionale; utile solo se si importa un dump archivio)

Container: `data-timescaledb-intex-1` (`psql -U postgres -d postgres`).

### 5.3 Re-import senza duplicati

`\copy` **inserisce**: con PK va in errore su duplicate key. Prima di ogni carico incrementale/sostitutivo:

```bash
TRUNCATE storico_disposizioni, ew2_righe_disposizioni, ew1_testata_disposizioni;
# poi \copy dei CSV nuovi (FROM STDIN dal path host)
```

Con lookback 365 giorni, truncate + copy sostituisce l’intero snapshot annual lato Postgres.

---

## 6. Query di controllo utili

```sql
-- Totali
SELECT COUNT(*) FROM INTEX2.EW1_TESTATA_DISPOSIZIONI;
SELECT COUNT(*) FROM INTEX2.STORICO_DISPOSIZIONI;

-- Range date STORICO
SELECT MIN(EW1_DATA_BOLLA_CLI), MAX(EW1_DATA_BOLLA_CLI)
FROM INTEX2.STORICO_DISPOSIZIONI;

SELECT COUNT(*) FROM INTEX2.STORICO_DISPOSIZIONI
WHERE EW1_DATA_BOLLA_CLI >= TRUNC(SYSDATE) - 365;

SELECT COUNT(*) FROM INTEX2.STORICO_DISPOSIZIONI
WHERE EW1_DATA_BOLLA_CLI IS NULL;

-- Allineamento UI (sqlplus: preferire join classica + TO_DATE)
SELECT COUNT(*)
FROM INTEX2.EW1_TESTATA_DISPOSIZIONI t,
     INTEX2.EW2_RIGHE_DISPOSIZIONI r
WHERE r.EW2_ANNO_DISPOSIZIONE = t.EW1_ANNO_DISPOSIZIONE
  AND r.EW2_NR_DISPOSIZIONE   = t.EW1_NR_DISPOSIZIONE
  AND t.EW1_CD_CLIENTE = '2594'
  AND t.EW1_DATA_BOLLA_CLI BETWEEN TO_DATE('10/01/2026','DD/MM/YYYY')
                               AND TO_DATE('10/12/2026','DD/MM/YYYY');
```

In sqlplus evitare letterali `DATE '…'` (possono dare *ORA-00933 SQL command not properly ended*) e evitare righe vuote dentro lo statement.

---

## 7. Roadmap consigliata

1. **Sync regolare:** solo EW1 + EW2 (già nello script) → base filtri e griglia core.
2. **Descrizioni UI:** join periodico o export anagrafiche (`R07`, `CW1`, `CW4`, `Z09`, `Z11`, `Z01`, `G31`, `CW0`) — in parte già presenti per i cicli.
3. **Griglia «completa» (cartellini, vasche, terzisti, fasi extra, quantità lavorate/evase):** o ricostruire aggregati da `P06`/`P07`/`P28`/DDT, o accettare proxy `EW2_*_PROD` / `*_DDT` dopo validazione.
4. **`STORICO_DISPOSIZIONI`:** non usare per il recente; eventuale full dump una tantum solo come archivio storico legacy.
5. **EW3/EW4:** aggiungere all’export dopo verify colonne chiave su Oracle.

---

## 8. Riferimenti interni

- Catalogo tabelle: `scripts/all-tables-intex.txt`
- Sample/colonne EW1/EW2/STORICO: `scripts/find-output.txt`, `scripts/output-all-queries.txt`
- ER parziale disposizioni (EW1/EW2): `documentation/F07_RIGHE_FATTURE.drawio`
- Offerte (post-disposizione ≠ preventivo): [`analisi-offerte.md`](./analisi-offerte.md)
- Export offerte (pattern script): [`analisi-export-offerte.md`](./analisi-export-offerte.md)
