# Analisi Offerte / Preventivi — Database Oracle Intex

Documento di sintesi della mappatura tra le schermate del gestionale **Wi@sh3** ("Offerte a Clienti", "Scheda lavorazione prototipi") e le tabelle/viste Oracle nello schema `INTEX2`.

Verificato su DB `INT2DB` (ottobre 2026) confrontando i dati Oracle con le foto delle schermate (cliente 2594 JACOB COHEN, offerte 39770 e 36625).

**Connessione sqlplus:** `INTEX2/SD@192.168.1.10:1521/INT2DB`

---

## 1. Conclusione

Le **offerte a clienti** (preventivi commerciali di lavorazione) vivono in:

| Ruolo | Oggetto Oracle | Righe (ott 2026) |
| :--- | :--- | ---: |
| **Testata offerta** | tabella `INTEX2.C37_TESTATA_LISTINI` | ~33.866 |
| **Testata decodificata (consigliata)** | view `INTEX2.C37_001W` | stessa base |
| **Righe fasi / prezzi** | tabella `INTEX2.C38_RIGHE_LISTINI` | ~113.000 |
| **Fasi del ciclo (descrizioni)** | `INTEX2.Z08_CICLI_LAVORAZIONE` → `Z02_FASI_DI_LAVORO` | ~321.000 / anagrafica |
| **Centri di costo (vendita capo/kg)** | `INTEX2.C51_RIPARTIZIONI_COSTI_CDC` → `C50_CDC_TAB` | ~38.000 / 7 |

Il **"Cod. Univoco"** mostrato in gestionale è la colonna **`C37_PRG`**.

**Non** sono le offerte (ipotesi scartate):

| Oggetto | Perché scartato |
| :--- | :--- |
| `INTEX2.C30_LISTINO_CLIENTI` | 0 righe (tabella vuota) |
| `NEXSTYLE/INTEXGR.C30_TEST_LIST_CLI` | ~40 righe — listini legacy, non le offerte commerciali |
| `INTEXPLURIMPRESA.PREVENTIVI` | 0 righe / dati estranei |
| `C52_PROTOTIPI_ATMAN` | 448 schede prototipo (foto/note), non l'elenco offerte |
| `STORICO_DISPOSIZIONI` / `EW1`/`EW2` | produzione dopo l'offerta, non il preventivo |

---

## 2. Schermate gestionale ↔ tabelle

| Schermata Wi@sh3 | Oggetto DB |
| :--- | :--- |
| Offerte a Clienti (elenco con Cod. Univoco, cliente, ciclo, linea, stagione…) | `C37_001W` / `C37_TESTATA_LISTINI` |
| Scheda offerta — testata, fasce prezzo, note | `C37_*` (fasce `C37_QT/PZ/TP/TQ_FASCIA_1..9`, note `C37_NOTE` / `C37_NOTE_LIBERE`) |
| Scheda offerta — griglia fasi (`C38_TP_PREZZO`, `C38_QTA_RIGA`, vendita capo/kg) | `C38_RIGHE_LISTINI` + `Z08` + `Z02` |
| Scheda offerta — riquadro "Centro 40 TINTORIA" | `C51_RIPARTIZIONI_COSTI_CDC` + `C50_CDC_TAB` |
| Badge "Prototipo" / "Offerta accettata" | `C37_FLAG_VISIBILE` (`P` / `S`) |
| Ricerca ciclo per fase | `Z09_TESTATE_CICLI_LAVORAZIONE` + `Z08` |
| Storico Disposizioni Completo | `STORICO_DISPOSIZIONI` (+ `EW1`/`EW2`) — post-offerta |

---

## 3. Modello dati

### 3.1 Chiave dell'offerta

Un'offerta è univoca (a livello di business) dalla **chiave a 7 campi**:

```
cliente + linea + stagione + composizione + articolo + ciclo + valuta
```

| Campo | Colonna C37 / C38 |
| :--- | :--- |
| Cliente | `C37_CD_CLIENTE` / `C38_CD_CLIENTE` |
| Linea | `C37_CD_LINEA` / `C38_CD_LINEA` |
| Stagione | `C37_CD_STAGIONE` / `C38_CD_STAGIONE` |
| Composizione | `C37_CD_COMPOSIZIONE` / `C38_CD_COMPOSIZIONE` |
| Articolo | `C37_CD_ARTICOLO` / `C38_CD_ARTICOLO` |
| Ciclo | `C37_CD_CICLO` / `C38_CD_CICLO` |
| Valuta | `C37_CD_VALUTA` / `C38_CD_VALUTA` |
| Sequenza riga | — / `C38_SEQUENZA` |

`C37_PRG` (Cod. Univoco) è il codice mostrato in UI. Attenzioni:

- Quasi sempre valorizzato (~33.863 su 33.866) e distinto (~33.837 valori).
- Esistono **~15 codici duplicati** su offerte vecchie (PRG ≤ 32240) e **3 record senza PRG**.
- Per join e sync usare preferibilmente la chiave a 7 campi; `C37_PRG` come codice display.

**`C38_C37_PRG` è sempre NULL** (~113k righe): le fasi **non** si collegano via codice univoco, solo via chiave a 7 campi.

### 3.2 Stato offerta

| `C37_FLAG_VISIBILE` | Significato in UI |
| :--- | :--- |
| `P` | Solo offerte ancora da accettare (badge "Prototipo" / proposta) |
| `S` | Solo offerte accettate |

Verificato confrontando:

- 39770 → Prototipo in foto → `FLAG_VISIBILE = P`
- 36625 → Offerta accettata in foto → `FLAG_VISIBILE = S`

`C37_FLAG_PROTOTIPO` (`S`/`N`) **non** distingue accettata vs da accettare.

Volumi (escluse stagioni listino standard `pe/ai` e `*`):

| Stato | Offerte |
| :--- | ---: |
| Accettate (`S`) | ~13.160 |
| Da accettare (`P`) | ~3.165 |

### 3.3 Stagioni speciali (listino standard)

| `C37_CD_STAGIONE` | Ruolo |
| :--- | :--- |
| `pe/ai` | ~15.072 — listino standard (checkbox "Visualizza Listino Standard") |
| `*` | ~2.469 — analogo / generico |

Nelle query di business (elenco offerte commerciali) conviene escludere `pe/ai` e `*`.

### 3.4 Relazioni e decodifiche

```
C37_TESTATA_LISTINI
  ├── R07_CLIENTI              (R07_CD_CLIENTE)
  ├── Z11_STAGIONI             (Z11_CD_STAGIONE)
  ├── CW4_COMPOSIZIONI         (CW4_CD_COMPOSIZIONE)
  ├── CW0_LINEA_TINTORIA       (CW0_CD_CLIENTE + CW0_CD_LINEA)
  ├── CWA_ARTICOLI_CLIENTE     (CWA_CD_CLIENTE + CWA_CD_ARTICOLO_CLIENTE)
  ├── Z09_TESTATE_CICLI_LAVORAZIONE
  │     chiave: cliente + articolo + ciclo + linea + stagione + composizione
  │     (descrizione ciclo, revisione, fallosità, utente, immagini)
  ├── C38_RIGHE_LISTINI        (FK_C38_C37 sulla chiave a 7 campi + SEQUENZA)
  │     └── Z08_CICLI_LAVORAZIONE (stessa chiave ciclo a 6 campi + SEQUENZA)
  │           └── Z02_FASI_DI_LAVORO (Z02_CD_FASE → descrizione fase)
  └── C51_RIPARTIZIONI_COSTI_CDC (stessa chiave a 7 campi)
        └── C50_CDC_TAB (C50_CD_AZIENDA='AZ1' + C50_CD_CDC)
```

**Nota join Z09:** la PK di `Z09` ha **6 colonne**. Joinare solo su cliente/articolo/ciclo produce righe duplicate.

**Nota articolo:** in `CWA` la colonna è `CWA_CD_ARTICOLO_CLIENTE` (non `CWA_CD_ARTICOLO`).

---

## 4. Colonne principali `C37_TESTATA_LISTINI`

| Colonna | Significato UI |
| :--- | :--- |
| `C37_PRG` | Cod. Univoco |
| `C37_CD_CLIENTE` | Cliente |
| `C37_CD_LINEA` | Linea |
| `C37_CD_STAGIONE` | Stagione |
| `C37_CD_COMPOSIZIONE` | Composizione |
| `C37_CD_ARTICOLO` | Articolo cliente |
| `C37_CD_CICLO` | Cod. Ciclo interno |
| `C37_CD_CICLO_CLI` | Ciclo Cliente |
| `C37_CD_VALUTA` | Valuta |
| `C37_PZ_TOT_CAPO` / `C37_PZ_TOT_KG` | Prezzo totale a capo / a kg |
| `C37_QT/PZ/TP/TQ_FASCIA_1..9` | Fasce prezzo (kg 1–4, capo 5–8, …) |
| `C37_FLAG_VISIBILE` | Stato: `P` da accettare, `S` accettata |
| `C37_FLAG_PROTOTIPO` | Flag prototipo (non = stato accettazione) |
| `C37_NOTE` / `C37_NOTE_LIBERE` | Note cliente / note libere |
| `C37_DATA_VALIDITA` | Data validità |
| `C37_GRUPPO` | Gruppo (sidebar elenco) |
| `C37_ST_RECORD` | Tipicamente `V` = valido |

---

## 5. Colonne principali `C38_RIGHE_LISTINI`

| Colonna | Significato UI |
| :--- | :--- |
| Chiave a 7 campi | Link alla testata C37 |
| `C38_SEQUENZA` | Seq (5, 10, 20, …) |
| `C38_TP_PREZZO` | Tipo prezzo (es. `C` capo, `K` kg) — colonna mostrata così in UI |
| `C38_QTA_RIGA` | Quantità riga |
| `C38_PZ_UNITARIO` / `C38_PZ_UNITARIO_KG` | Vendita a capo / a kg |
| `C38_CS_UNITARIO` / `C38_CS_UNITARIO_KG` | Costo unitario capo / kg |
| `C38_CD_FORNITORE` | Fornitore sulla fase |
| `C38_C37_PRG` | **Sempre NULL — non usare** |

La descrizione fase (`DIVISIONE CAPI`, `TINTO`, `MARMO`, …) e l'unità di misura (`NR`) arrivano da `Z08` + `Z02`, non da C38.

---

## 6. View Oracle

### 6.1 `C37_001W` — testata offerta arricchita (preferita)

View già usata dal gestionale / stampabile. Contiene i campi C37 più:

| Campo view | Origine |
| :--- | :--- |
| `R07_RAGIONE_SOC` | Cliente |
| `CW0_DS_LINEA` | Linea |
| `Z11_DS_STAGIONE` | Stagione |
| `CW4_DS_COMPOSIZIONE` | Composizione |
| `CWA_DS_ARTICOLO_CLIENTE` | Articolo |
| `Z09_DS_CICLO` | Descrizione ciclo |
| `Z01_DS_REPARTO` | Reparto (TINTO, DENIM, …) |
| `Z09_NR_REVISIONE`, `Z09_PERC_FALLOSITA` | Revisione / % fallosità |
| `Z09_UTENTE_INSERIMENTO`, `Z09_DATA_INS` | Chi / quando |
| `ANNO_INS` | Anno inserimento (filtro "Anno" in UI) |
| `C37_PRG` | Cod. Univoco |

Altre view correlate: `C37_SP_001W`, `C37_SP_002W`, `PRINT_C37_001W`.

### 6.2 View C38

| View | Note |
| :--- | :--- |
| `C38_001W`, `C38_002W` | Righe senza `C37_PRG` |
| `C38_003W` | Espone anche `C37_PRG` / `C37_FLAG_VISIBILE` (join lato view) |
| `C38_C41_001W` | Variante con materiali |

Per una griglia completa (fase + descrizione + prezzi) serve una query/view che unisca C38 + Z08 + Z02 (vedi §8.2).

### 6.3 ORDS

In `data/known_endpoints.json` **non** risultano ancora endpoint AutoREST per `C37_001W` / `C38_*`.

Da richiedere per l'app:

1. **`C37_001W`** — elenco e dettaglio testata offerte  
2. View/righe fasi (C38+Z08+Z02) o almeno `C38_003W` + join lato sync  

---

## 7. Verifica fotografica (offerta 39770)

Dati Oracle vs scheda "Offerte a Clienti" / prototipo JACOB COHEN:

| Campo | Valore |
| :--- | :--- |
| Cod. Univoco | 39770 |
| Cliente | 2594 JACOB COHEN COMPANY SPA |
| Stagione | AI 27 / AI 27/28 |
| Composizione | 10001 naturali |
| Articolo | 00010 GIUBBINI |
| Ciclo | T141 — TINTO+MPELO+MARMO+A/S+PROF+DIV.CAPI |
| Prezzo capo | 15,55 |
| Fallosità | 5% |
| Note libere | `4,95+2+8,6` |
| Centro 40 | TINTORIA, vendita capo 15,55 |
| Stato | DA ACCETTARE (`FLAG_VISIBILE=P`) |

Fasi C38+Z08+Z02:

| Seq | Fase | Descrizione | Vendita kg |
| ---: | :--- | :--- | ---: |
| 5 | 000068 | DIVISIONE CAPI | 0 |
| 10 | 000001 | TINTO | 4,2 |
| 20 | 000005 | (ti)+M.PELO | 1,6 |
| 30 | 000107 | MARMO | 6,5 |
| 40 | 000063 | MANO SILICONICA C | 0 |
| 50 | 000114 | PROFUMO | 0 |
| 60 | 001128 | ASCIUGATURA COTONE 70° X 40' | 0 |
| 70 | 001049 | CONTROLLO QUALITA' | 0 |

Offerta 36625 (PE 26, T220, PANTALONI, prezzo 4,7): in foto "Offerta accettata" → `FLAG_VISIBILE=S`.

---

## 8. Query di esempio

Connessione: `sqlplus INTEX2/SD@192.168.1.10:1521/INT2DB`

Script completi in repo: `scripts/offerte-query-definitive.txt`, `scripts/offerte-controllo-finale.txt`.

### 8.1 Ultime 100 offerte (come elenco gestionale)

```sql
SELECT * FROM (
  SELECT v.C37_PRG AS cod_univoco,
         CASE v.C37_FLAG_VISIBILE
           WHEN 'P' THEN 'DA ACCETTARE'
           WHEN 'S' THEN 'ACCETTATA'
           ELSE v.C37_FLAG_VISIBILE
         END AS stato,
         v.C37_CD_CLIENTE AS cliente,
         v.R07_RAGIONE_SOC AS ragione_sociale,
         v.C37_CD_CICLO AS ciclo,
         v.C37_CD_CICLO_CLI AS ciclo_cli,
         v.Z09_DS_CICLO AS ds_ciclo,
         v.C37_CD_LINEA AS linea,
         v.CW0_DS_LINEA AS ds_linea,
         v.C37_CD_STAGIONE AS stagione,
         v.Z11_DS_STAGIONE AS ds_stagione,
         v.C37_CD_COMPOSIZIONE AS composizione,
         v.CW4_DS_COMPOSIZIONE AS ds_composizione,
         v.C37_CD_ARTICOLO AS articolo,
         v.CWA_DS_ARTICOLO_CLIENTE AS ds_articolo,
         v.Z01_DS_REPARTO AS reparto,
         v.C37_PZ_TOT_CAPO,
         v.C37_PZ_TOT_KG,
         v.Z09_PERC_FALLOSITA,
         v.Z09_UTENTE_INSERIMENTO AS utente,
         v.Z09_DATA_INS
  FROM INTEX2.C37_001W v
  WHERE v.C37_PRG IS NOT NULL
    AND v.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
  ORDER BY v.C37_PRG DESC
) WHERE ROWNUM <= 100;
```

> **sqlplus:** se compare `ORA-00923`, di solito è un apice “curvo” (tipografico) al posto di `'` ASCII — soprattutto su `'pe/ai'`. In quel caso Oracle interpreta `/` come divisione e fallisce il parse. Incolla da file `.txt` o ri-digita gli apici. Alternativa più compatta (già verificata):

```sql
SELECT * FROM (
  SELECT v.C37_PRG AS cod_univoco,
         CASE v.C37_FLAG_VISIBILE WHEN 'P' THEN 'DA ACCETTARE'
                                  WHEN 'S' THEN 'ACCETTATA'
                                  ELSE v.C37_FLAG_VISIBILE END AS stato,
         v.C37_CD_CLIENTE AS cliente, v.R07_RAGIONE_SOC AS ragione_sociale,
         v.C37_CD_CICLO AS ciclo, v.C37_CD_CICLO_CLI AS ciclo_cli, v.Z09_DS_CICLO AS ds_ciclo,
         v.C37_CD_LINEA AS linea, v.CW0_DS_LINEA AS ds_linea,
         v.C37_CD_STAGIONE AS stagione, v.Z11_DS_STAGIONE AS ds_stagione,
         v.C37_CD_COMPOSIZIONE AS composizione, v.CW4_DS_COMPOSIZIONE AS ds_composizione,
         v.C37_CD_ARTICOLO AS articolo, v.CWA_DS_ARTICOLO_CLIENTE AS ds_articolo,
         v.Z01_DS_REPARTO AS reparto, v.C37_PZ_TOT_CAPO, v.C37_PZ_TOT_KG,
         v.Z09_PERC_FALLOSITA, v.Z09_UTENTE_INSERIMENTO AS utente, v.Z09_DATA_INS
  FROM INTEX2.C37_001W v
  WHERE v.C37_PRG IS NOT NULL
    AND v.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
  ORDER BY v.C37_PRG DESC
) WHERE ROWNUM <= 100;
```


### 8.2 Dettaglio fasi di un'offerta (es. 39770)

```sql
SELECT r.C38_SEQUENZA,
       z8.Z08_CD_FASE        AS fase,
       z2.Z02_DS_FASE        AS ds_fase,
       r.C38_TP_PREZZO       AS tp,
       z8.Z08_CD_UNITA_MIS   AS um,
       r.C38_QTA_RIGA,
       r.C38_PZ_UNITARIO     AS vendita_capo,
       r.C38_PZ_UNITARIO_KG  AS vendita_kg,
       r.C38_CS_UNITARIO     AS costo_capo,
       r.C38_CS_UNITARIO_KG  AS costo_kg,
       r.C38_CD_FORNITORE
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
WHERE t.C37_PRG = 39770
ORDER BY r.C38_SEQUENZA;
```

### 8.3 Centri di costo

```sql
SELECT c51.C51_CD_CDC AS cdc,
       c50.C50_DS_CDC AS ds_cdc,
       c51.C51_COSTO AS vendita_capo,
       c51.C51_COSTO_KG AS vendita_kg
FROM INTEX2.C37_TESTATA_LISTINI t
JOIN INTEX2.C51_RIPARTIZIONI_COSTI_CDC c51
  ON  c51.C51_CD_CLIENTE      = t.C37_CD_CLIENTE
  AND c51.C51_CD_LINEA        = t.C37_CD_LINEA
  AND c51.C51_CD_STAGIONE     = t.C37_CD_STAGIONE
  AND c51.C51_CD_COMPOSIZIONE = t.C37_CD_COMPOSIZIONE
  AND c51.C51_CD_ARTICOLO     = t.C37_CD_ARTICOLO
  AND c51.C51_CD_CICLO        = t.C37_CD_CICLO
  AND c51.C51_CD_VALUTA       = t.C37_CD_VALUTA
LEFT JOIN INTEX2.C50_CDC_TAB c50
  ON c50.C50_CD_AZIENDA = 'AZ1'
 AND c50.C50_CD_CDC     = c51.C51_CD_CDC
WHERE t.C37_PRG = 39770;
```

### 8.4 Offerte di un cliente/stagione

```sql
SELECT v.C37_PRG AS cod_univoco,
       CASE v.C37_FLAG_VISIBILE WHEN 'P' THEN 'DA ACCETTARE' WHEN 'S' THEN 'ACCETTATA' END AS stato,
       v.C37_CD_CICLO, v.C37_CD_CICLO_CLI, v.Z09_DS_CICLO,
       v.CW0_DS_LINEA, v.CW4_DS_COMPOSIZIONE, v.CWA_DS_ARTICOLO_CLIENTE,
       v.C37_PZ_TOT_CAPO, v.C37_PZ_TOT_KG
FROM INTEX2.C37_001W v
WHERE v.C37_CD_CLIENTE  = '2594'
  AND v.C37_CD_STAGIONE = 'AI 27'
ORDER BY v.C37_PRG DESC;
```

### 8.5 Solo da accettare (ultime 50)

```sql
SELECT * FROM (
  SELECT v.C37_PRG, v.C37_CD_CLIENTE, v.R07_RAGIONE_SOC,
         v.C37_CD_STAGIONE, v.C37_CD_CICLO, v.Z09_DS_CICLO,
         v.C37_PZ_TOT_CAPO, v.C37_PZ_TOT_KG
  FROM INTEX2.C37_001W v
  WHERE v.C37_FLAG_VISIBILE = 'P'
    AND v.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
    AND v.C37_PRG IS NOT NULL
  ORDER BY v.C37_PRG DESC
) WHERE ROWNUM <= 50;
```

### 8.6 Conteggio accettate per stagione

```sql
SELECT v.C37_CD_STAGIONE, v.Z11_DS_STAGIONE, COUNT(*) AS n
FROM INTEX2.C37_001W v
WHERE v.C37_FLAG_VISIBILE = 'S'
  AND v.C37_CD_STAGIONE NOT IN ('pe/ai', '*')
GROUP BY v.C37_CD_STAGIONE, v.Z11_DS_STAGIONE
ORDER BY n DESC;
```

### 8.7 Testata da view per un Cod. Univoco

```sql
SELECT *
FROM INTEX2.C37_001W
WHERE C37_PRG IN (39770, 36625);
```

---

## 9. Percorso di scoperta (sintesi)

1. Catalogo `all_tables` → filtro business in `scripts/all-tables-intex.txt`.
2. Ipotesi etimologiche (`PREVENTIVI`, `TO_OFFERTE_PREZZI`) → tabelle vuote o irrilevanti.
3. Foto gestionale → colonne UI `C38_TP_PREZZO` / `C38_QTA_RIGA` → traccia su famiglia **C37/C38**.
4. `C37_TESTATA_LISTINI` ~33.8k righe; ricerca Cod. Univoco foto → hit su **`C37_PRG`**.
5. FK `FK_C38_C37`; `C38_C37_PRG` inutilizzabile (sempre NULL).
6. View `C37_001W` allineata alle foto; flag stato = `C37_FLAG_VISIBILE`.
7. Query definitive in `scripts/offerte-query-definitive.txt` — output senza errori, match 1:1 con schermate.

---

## 10. Implicazioni per l'app Intex

Nel dominio applicativo attuale, "offerte" nel frontend spesso mappa a **ordini/cartellini** (`offerte_testate` locali). Le **offerte commerciali Wi@sh3** sono invece questo modello C37/C38 (listino/preventivo di lavorazione per cliente-ciclo-stagione).

Per integrarle:

1. Esporre ORDS `C37_001W` (e una view righe fasi).
2. Sync incrementale: usare `Z09_DATA_INS` / `C37_DATA_VALIDITA` / `C37_ST_MODIFICA` (da validare) e chiave a 7 campi.
3. Filtri UI: `C37_FLAG_VISIBILE`, stagione (escludere `pe/ai`/`*` se non si vuole il listino standard), cliente, anno (`ANNO_INS`).
4. Distinguere nel prodotto "offerta commerciale (C37)" da "ordine/cartellino (P06/EW*)" se entrambi restano in scope.

---

## 11. File correlati nel repo

| File | Contenuto |
| :--- | :--- |
| `scripts/all-tables-intex.txt` | Tabelle business (no schema di sistema) |
| `scripts/find-offerte-c37-c38.txt` | Prima verifica C37/C38 |
| `scripts/offerte-controllo-finale.txt` | Controlli flag, PK, join |
| `scripts/offerte-query-definitive.txt` | Query operative finali |
| `scripts/output-query-controllo-definitive.txt` | Output di verifica (match foto) |
| `scripts/foto/` | Screenshot gestionale usati per il mapping |
| `data/known_endpoints.json` | Endpoint ORDS attuali (C37/C38 ancora assenti) |
