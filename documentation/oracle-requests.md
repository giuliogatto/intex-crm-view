# Comandi cURL per Endpoints Oracle ORDS (Intex)

Questo documento raccoglie la lista completa degli esatti comandi `curl` utilizzati per interrogare e testare le viste Oracle exposed via **Oracle REST Data Services (ORDS)** per il sistema Intex.

I comandi utilizzano i singoli apici (`'...'`) sia per le credenziali che per le URL, per evitare che la shell (`zsh` o `bash` su macOS/Linux) interpreti il carattere speciale `!` nella password come espansione della cronologia (`dquote>`).

---


## 🔑 Credenziali e Base URL

- **Base URL**: `https://analisi.intexsrl.com/ords/intex2`
- **Autenticazione**: Basic Auth (`-u 'arcadia_user:kuru2387BECAMWQ!'`)

---

## LISTA ENDPOINTS
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/open-api-catalog/' | python3 -m json.tool
```
---

## 🛠️ Suggerimento per Formattare l'Output JSON

Per visualizzare la risposta formattata in modo leggibile nel terminale, è possibile aggiungere `| jq .` o `| python3 -m json.tool` alla fine di ogni comando `curl`.

Esempio:
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/bma_view/?limit=1' | python3 -m json.tool
```

---

## 📋 Lista Comandi cURL per Endpoint

### 1. `D02_DDT_TESTATA_001W` — Testate DDT (Bolle di Consegna)

#### Visualizza il primo record (schema e campi)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/D02_DDT_TESTATA_001W/?limit=1'
```

#### Filtro incrementale su data creazione (`DT_CREAZIONE >= 2026-09-01`)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/D02_DDT_TESTATA_001W/?q=%7B%22DT_CREAZIONE%22%3A%7B%22%24gte%22%3A%7B%22%24date%22%3A%222026-09-01T00%3A00%3A00Z%22%7D%7D%7D'
```

---

### 2. `D03_DDT_RIGHE_002W` — Righe Dettaglio DDT (con ISO date e cartellini)

> **Nota**: Utilizzare la versione `002W` (non `001W`), poiché include i campi ISO `data_bolla_iso` e `data_bolla_cli_iso` necessari al sync incrementale.

#### Visualizza il primo record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/D03_DDT_RIGHE_002W/?limit=1'
```

#### Filtro incrementale su data bolla ISO (`data_bolla_iso >= 2026-09-01`)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/D03_DDT_RIGHE_002W/?q=%7B%22data_bolla_iso%22%3A%7B%22%24gte%22%3A%222026-09-01%22%7D%7D'
```

---

### 3. `F03_001W` — Testate Documenti Contabili (Fatture e Note di Accredito)

#### Visualizza i primi 5 record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/F03_001W/?limit=5'
```

#### Filtro incrementale su data documento (`F03_DT_DOCUMENTO >= 2026-09-01`)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/F03_001W/?q=%7B%22F03_DT_DOCUMENTO%22%3A%7B%22%24gte%22%3A%7B%22%24date%22%3A%222026-09-01T00%3A00%3A00Z%22%7D%7D%7D'
```

#### Filtro incrementale su data inserimento (`F03_DT_INSERIMENTO >= 2026-09-01`)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/F03_001W/?q=%7B%22F03_DT_INSERIMENTO%22%3A%7B%22%24gte%22%3A%7B%22%24date%22%3A%222026-09-01T00%3A00%3A00Z%22%7D%7D%7D'
```

---

### 4. `F07_003W` — Righe Dettaglio Fatture

#### Visualizza il primo record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/F07_003W/?limit=1'
```

#### Filtro incrementale su data inserimento ISO (`FE_DT_INSERIMENTO_ISO >= 2026-09-01`)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/F07_003W/?q=%7B%22FE_DT_INSERIMENTO_ISO%22%3A%7B%22%24gte%22%3A%222026-09-01%22%7D%7D'
```

---

### 5. `R07_R0236_C012456789_001W` — Anagrafica Clienti

#### Visualizza i primi record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/R07_R0236_C012456789_001W/?limit=5'
```

#### Filtro sui clienti modificati (versione > 0)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/R07_R0236_C012456789_001W/?q=%7B%22r07_st_modifica%22%3A%7B%22%24gt%22%3A0%7D%7D'
```

---

### 6. `CW1_ARTICOLI_FISCALI_001W` — Anagrafica Articoli Fiscali

#### Visualizza il primo record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/CW1_ARTICOLI_FISCALI_001W/?limit=1'
```

---

### 7. `CW4_COMPOSIZIONI_001W` — Anagrafica Composizioni Materiali

#### Visualizza il primo record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/CW4_COMPOSIZIONI_001W/?limit=1'
```

#### Filtro su data modifica (`SD_DT_MOD >= 2026-01-01`)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/CW4_COMPOSIZIONI_001W/?q=%7B%22SD_DT_MOD%22%3A%7B%22%24gte%22%3A%7B%22%24date%22%3A%222026-01-01T00%3A00%3A00Z%22%7D%7D%7D'
```

---

### 8. `C01_CODICI_IVA_001W` — Tabella Codici ed Aliquote IVA

#### Visualizza il primo record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/C01_CODICI_IVA_001W/?limit=1'
```

---

### 9. `C07_R02_C023_001W` — Anagrafica Agenti

#### Verifica record presenti
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/C07_R02_C023_001W/?limit=5'
```

---

### 10. `CW0_001W` — Anagrafica Linee Tintoria

#### Visualizza il primo record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/CW0_001W/?limit=1'
```

---

### 11. `CWA_001W` — Tabella Articoli Cliente

#### Visualizza i primi 10 record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/CWA_001W/?limit=10'
```

#### Paginazione con offset (es. offset 50.000, 20 record)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/CWA_001W/?offset=50000&limit=20'
```

---

### 12. `bma_view` — Anagrafica Aziende / Moduli ERP

> **Nota**: Il nome dell'endpoint va espresso interamente in minuscolo (`bma_view`).

#### Visualizza i record delle aziende
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/bma_view/?limit=10'
```

---

## ⚡ Comandi di Paginazione e Batching

### Download in batch da 10.000 record
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/CWA_001W/?limit=10000&offset=0'
```

### Verifica presenza di ulteriori record (`hasMore`)
```bash
curl -s -u 'arcadia_user:kuru2387BECAMWQ!' 'https://analisi.intexsrl.com/ords/intex2/D02_DDT_TESTATA_001W/?offset=30000&limit=1' | python3 -c "import sys, json; d=json.load(sys.stdin); print('count:', d.get('count'), 'hasMore:', d.get('hasMore'))"
```
