# Analisi export offerte commerciali — Oracle → CSV → SFTP

Come esportare le **offerte a clienti** (modello C37/C38) in CSV e caricarle su un server esterno, riusando lo schema di `scripts/extract_upload_tables.py`.

Mappatura tabelle e chiavi: vedi [`analisi-offerte.md`](./analisi-offerte.md).

**Premessa:** lo script attuale esporta ancora `C30_LISTINO_CLIENTI` / `C33_*` / `STORICO_DISPOSIZIONI` — **non** sono le offerte commerciali Wi@sh3. Questo documento descrive come estenderlo (o sostituire le `QUERIES`) per le offerte vere.

---

## 1. Obiettivo

Pipeline:

```
Oracle INT2DB  →  CSV locali (timestamped)  →  SFTP server Debian  →  import lato remoto
```

Lo script Python:

1. si connette a Oracle (`oracledb`);
2. esegue un dizionario `QUERIES` → un file CSV per chiave;
3. salva in `LOCAL_DIR` con prefisso `YYYYMMDD_HHMMSS_`;
4. carica via SFTP (`paramiko`) in `DEBIAN_REMOTE_DIR` (es. `/intex/`);
5. cancella i file locali dopo l’upload.

Configurazione connessione e destinazione: già in `scripts/extract_upload_tables.py` (Oracle `INTEX2@…/INT2DB`, host/credenziali SFTP).

---

## 2. Cosa esportare

Per avere un dataset offerte completo (cliente incluso) servono questi CSV.

### 2.1 Obbligatori (offerta)

| File CSV proposto | Sorgente Oracle | Contenuto |
| :--- | :--- | :--- |
| `c37_offerte_testate.csv` | view `INTEX2.C37_001W` | Testata + cliente (`R07_RAGIONE_SOC`) + decodifiche (linea, stagione, articolo, ciclo, …) |
| `c38_offerte_righe.csv` | `INTEX2.C38_RIGHE_LISTINI` (+ join opz. `Z08`/`Z02`) | Fasi / prezzi per offerta |

Preferire **`C37_001W`** alla sola `C37_TESTATA_LISTINI`: evita join lato script per cliente e descrizioni.

### 2.2 Consigliati (dettaglio scheda)

| File CSV proposto | Sorgente | Contenuto |
| :--- | :--- | :--- |
| `c38_offerte_righe_fasi.csv` | `C38` ⋈ `Z08` ⋈ `Z02` | Come griglia UI (seq, fase, descrizione, UM, vendita capo/kg) |
| `c51_offerte_cdc.csv` | `C51_RIPARTIZIONI_COSTI_CDC` ⋈ `C50_CDC_TAB` | Centri di costo (es. TINTORIA) |

### 2.3 Anagrafiche (full raro, non ogni run incrementale)

`R07_CLIENTI`, `Z02_FASI_DI_LAVORO`, `C50_CDC_TAB`, `Z11_STAGIONI`, … — solo se il server remoto non le ha già, o con sync periodico full.

---

## 3. Export incrementale (“ultime 2 settimane”)

### 3.1 Campo guida

| Campo | Note |
| :--- | :--- |
| **`Z09_DATA_INS`** | `DATE` su `C37_001W` — miglior filtro “recenti” (data inserimento ciclo) |
| `C37_DATA_VALIDITA` | Data validità, non creazione |
| `ANNO_INS` | Solo filtro per anno |
| `C37_PRG` | Utile per `ORDER BY … DESC` (“ultime N”), non è una data |
| `C37_ST_MODIFICA` / `C38_ST_MODIFICA` | `NUMBER` (versione), **non** usabile come finestra temporale |

`C38` **non ha colonne data**: le righe si esportano filtrando le testate selezionate (chiave a 7 campi).

### 3.2 Strategia a due passi

1. **Selezionare le testate** delle ultime N settimane su `C37_001W` con `Z09_DATA_INS`.
2. **Esportare C38 / C51** solo per quelle chiavi (cliente + linea + stagione + composizione + articolo + ciclo + valuta).

Opzionale: escludere listino standard `C37_CD_STAGIONE NOT IN ('pe/ai', '*')` come in gestionale.

### 3.3 Limiti

- `Z09_DATA_INS` è del ciclo (`Z09`), non un audit trail di modifica su `C37`: un’offerta aggiornata senza toccare il ciclo può restare fuori dalla finestra.
- Non esiste un `last_modified` affidabile su C37/C38; per “tutto ciò che è cambiato” servirebbe watermark su `ST_MODIFICA` o un full periodico.
- Campi incrementali ancora **da validare in produzione** (vedi §10 di `analisi-offerte.md`).

---

## 4. Come adattare `extract_upload_tables.py`

Il meccanismo resta identico: aggiungere/sostituire voci in `QUERIES`. Ogni entry = un CSV uploadato.

### 4.1 Testate (incrementale 14 giorni)

```python
"c37_offerte_testate.csv": """
    SELECT v.*
    FROM INTEX2.C37_001W v
    WHERE v.C37_PRG IS NOT NULL
      AND v.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
      AND v.Z09_DATA_INS >= TRUNC(SYSDATE) - 14
""",
```

Varianti:

- finestra parametrica: sostituire `14` con una costante `LOOKBACK_DAYS`;
- “ultime N offerte” senza data: `ORDER BY C37_PRG DESC` + `ROWNUM <= N` (come pattern attuale dello script, meno preciso).

### 4.2 Righe fasi collegate alle testate filtrate

Join sulla chiave a 7 campi (**non** usare `C38_C37_PRG`, sempre NULL):

```python
"c38_offerte_righe.csv": """
    SELECT r.*,
           z8.Z08_CD_FASE,
           z2.Z02_DS_FASE,
           z8.Z08_CD_UNITA_MIS
    FROM INTEX2.C37_TESTATA_LISTINI t
    JOIN INTEX2.C38_RIGHE_LISTINI r
      ON  r.C38_CD_CLIENTE      = t.C37_CD_CLIENTE
      AND r.C38_CD_LINEA        = t.C37_CD_LINEA
      AND r.C38_CD_STAGIONE     = t.C37_CD_STAGIONE
      AND r.C38_CD_COMPOSIZIONE = t.C37_CD_COMPOSIZIONE
      AND r.C38_CD_ARTICOLO     = t.C37_CD_ARTICOLO
      AND r.C38_CD_CICLO        = t.C37_CD_CICLO
      AND r.C38_CD_VALUTA       = t.C37_CD_VALUTA
    LEFT JOIN INTEX2.Z08_CICLI_LAVORAZIONE z8
      ON  z8.Z08_CD_CLIENTE          = t.C37_CD_CLIENTE
      AND z8.Z08_CD_ARTICOLO_CLIENTE = t.C37_CD_ARTICOLO
      AND z8.Z08_CD_CICLO            = t.C37_CD_CICLO
      AND z8.Z08_CD_LINEA            = t.C37_CD_LINEA
      AND z8.Z08_CD_STAGIONE         = t.C37_CD_STAGIONE
      AND z8.Z08_CD_COMPOSIZIONE     = t.C37_CD_COMPOSIZIONE
      AND z8.Z08_SEQUENZA            = r.C38_SEQUENZA
    LEFT JOIN INTEX2.Z02_FASI_DI_LAVORO z2
      ON z2.Z02_CD_FASE = z8.Z08_CD_FASE
    WHERE t.C37_PRG IS NOT NULL
      AND t.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
      AND EXISTS (
            SELECT 1 FROM INTEX2.C37_001W v
            WHERE v.C37_CD_CLIENTE      = t.C37_CD_CLIENTE
              AND v.C37_CD_LINEA        = t.C37_CD_LINEA
              AND v.C37_CD_STAGIONE     = t.C37_CD_STAGIONE
              AND v.C37_CD_COMPOSIZIONE = t.C37_CD_COMPOSIZIONE
              AND v.C37_CD_ARTICOLO     = t.C37_CD_ARTICOLO
              AND v.C37_CD_CICLO        = t.C37_CD_CICLO
              AND v.C37_CD_VALUTA       = t.C37_CD_VALUTA
              AND v.Z09_DATA_INS >= TRUNC(SYSDATE) - 14
          )
""",
```

(Stesso filtro data su `C51` se si esporta anche i CDC.)

### 4.3 Naming file e upload

Comportamento già implementato:

| Locale | Remoto (esempio) |
| :--- | :--- |
| `{LOCAL_DIR}/{ts}_c37_offerte_testate.csv` | `/intex/{ts}_c37_offerte_testate.csv` |

Il timestamp comune a tutti i file di un run permette al server remoto di raggruppare un batch di export.

---

## 5. Full vs incrementale

| Modalità | Quando | Approccio |
| :--- | :--- | :--- |
| **Incrementale** | cron giornaliero / ogni N ore | Filtro `Z09_DATA_INS >= SYSDATE - LOOKBACK` (+ overlap di sicurezza, es. 14–21 gg) |
| **Full** | prima volta o riconciliazione | `SELECT` senza filtro data; attenzione a ~34k testate / ~113k righe C38 |
| **Ibrido** | consigliato | Full iniziale una tantum; poi solo incrementale; full mensile di controllo |

Per full grandi volumi: valutare `cursor.arraysize`, scrittura CSV a chunk (`fetchmany`), o spool sqlplus — lo script attuale fa `fetchall()` in RAM.

---

## 6. Chiavi per il join lato server remoto

Dopo l’upload, il consumatore deve ricomporre testata ↔ righe così:

```
cliente + linea + stagione + composizione + articolo + ciclo + valuta
(+ C38_SEQUENZA per le fasi)
```

`C37_PRG` (Cod. Univoco) è codice display: quasi sempre valorizzato, ma con ~15 duplicati storici e 3 NULL — **non** usarlo come PK di sync.

---

## 7. Checklist implementativa

1. Sostituire/estendere `QUERIES` in `extract_upload_tables.py` con C37/C38 (e opz. C51) come sopra.
2. Introdurre `LOOKBACK_DAYS` (default 14) condiviso tra le query.
3. Verificare su DB una run dry (conteggi ultime 2 settimane vs gestionale).
4. Concordare col server remoto: encoding UTF-8, header colonna, overwrite vs append, retention file.
5. Non riesportare ad ogni run le anagrafiche statiche se già presenti remoto.
6. Tenere distinto questo export dalle “offerte” già in app Intex (`offerte_testate` = cartellini/ordini, non C37).

---

## 8. Riferimenti

| File | Ruolo |
| :--- | :--- |
| `documentation/analisi-offerte.md` | Modello dati C37/C38, query di verifica |
| `scripts/extract_upload_tables.py` | Template export CSV + SFTP |
| `scripts/offerte-query-definitive.txt` | Query SQL già validate su INT2DB |
| `data/known_endpoints.json` | ORDS: C37/C38 non ancora esposti (export diretto Oracle è il percorso attuale) |
