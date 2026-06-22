# F07_003W — Oracle REST Endpoint Documentation

Invoice line details exposed via Oracle REST Data Services (ORDS) AutoREST. Each row represents an invoice line grouped by disposition number (`ew2_nr_disposizione`).

**Document type**: **Fatture** (invoices) only — not offerte or ordini. Quotes/orders use `F03_001W`; delivery notes use `D02_DDT_TESTATA_001W` / `D03_DDT_RIGHE_*`.

---

## Endpoint URLs

| Resource | URL |
| :--- | :--- |
| **Data endpoint** | `https://analisi.intexsrl.com/ords/intex2/F07_003W/` |
| **OpenAPI spec** | `https://analisi.intexsrl.com/ords/intex2/open-api-catalog/F07_003W/` |
| **Full ORDS catalog** | `https://analisi.intexsrl.com/ords/intex2/open-api-catalog/` |

- **Namespace**: AutoREST (`/ords/intex2/`, no `/v1/` prefix)
- **Auth**: Basic auth via `INTEX_ENDPOINT_USER` / `INTEX_ENDPOINT_PASSWORD` in `backend/.env`
- **OpenAPI title**: *ORDS generated API for F07_003W*

---

## HTTP Usage

### GET — list records

```
GET /ords/intex2/F07_003W/?limit=100&offset=0
GET /ords/intex2/F07_003W/?q={...}
```

| Parameter | Description |
| :--- | :--- |
| `limit` | Page size (use **100** with `DATA_BOLLA_ISO` filters; sync currently uses 20) |
| `offset` | Pagination offset |
| `q` | JSON filter object (ORDS query syntax) |

Response shape:

```json
{
  "items": [ { ... } ],
  "hasMore": true,
  "limit": 100,
  "offset": 0,
  "count": 100,
  "links": [ ... ]
}
```

### Performance notes

- This endpoint can be **very slow** depending on which date column and filter syntax you use (see [Performance benchmarks](#performance-benchmarks) below).
- Prefer **`DATA_BOLLA_ISO`** or **`DATA_FATTURA_ISO`** with plain date strings — avoid **`D02_DT_BOLLA`** with `$date` objects for date ranges.
- The sync script currently filters on `D02_DT_BOLLA` (slow path); switching to `DATA_BOLLA_ISO` would likely cut sync time sharply.
- The sync script uses a dedicated page size (`FATTURE_LIMIT = 20`) and a 60-second HTTP timeout.
- With `DATA_BOLLA_ISO`, **`limit=100` stays fast (~1.2s)** — 5× more rows per page for only ~0.2s extra vs `limit=20`.
- Lowering `limit` from 20 → 1 does **not** materially help; raising it to 100 with a good date filter is safe and improves throughput.
- Add a short sleep between pages to avoid rate limiting (HTTP 429).

---

## curl examples

Credentials are in `backend/.env` (`INTEX_ENDPOINT_USER`, `INTEX_ENDPOINT_PASSWORD`, `INTEX_BASE_URL`).

### Setup

```bash
export INTEX_USER="arcadia_user"
export INTEX_PASS="your-password-here"
export BASE="https://analisi.intexsrl.com/ords/intex2/F07_003W"

# helper: run request + print timing
f07() {
  echo ">>> $1"
  curl -s -u "${INTEX_USER}:${INTEX_PASS}" \
    -w "\nHTTP %{http_code} | %{time_total}s | %{size_download} bytes\n" \
    --max-time 120 \
    "$2" | python3 -m json.tool 2>/dev/null | head -80
  echo
}
```

### 1) One record (no filter)

```bash
f07 "limit=1, no filter" "${BASE}/?limit=1"
```

Returns the first row in Oracle's default order (~4s). Not necessarily the latest record.

### 2) Date range filters

**Fast — `DATA_BOLLA_ISO` with plain date strings:**

```bash
Q='{"DATA_BOLLA_ISO":{"$between":["2026-03-01","2026-03-31"]}}'
f07 "limit=1, DATA_BOLLA_ISO March 2026" \
  "${BASE}/?limit=1&q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$Q'''))")"

Q='{"DATA_FATTURA_ISO":{"$between":["2026-03-01","2026-03-31"]}}'
f07 "limit=1, DATA_FATTURA_ISO March 2026" \
  "${BASE}/?limit=1&q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$Q'''))")"
```

**Slow — `D02_DT_BOLLA` with `$date` objects (current sync style):**

```bash
Q='{"D02_DT_BOLLA":{"$between":[{"$date":"2026-01-01T00:00:00Z"},{"$date":"2026-06-22T23:59:59Z"}]}}'
f07 "limit=1, D02_DT_BOLLA YTD 2026 (sync style — SLOW)" \
  "${BASE}/?limit=1&q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$Q'''))")"
```

### 3) Selective lookups (fast)

**Date + customer:**

```bash
Q='{"DATA_BOLLA_ISO":{"$between":["2026-03-01","2026-03-31"]},"EW2_CD_CLIENTE":"648"}'
f07 "limit=1, March 2026 + customer 648" \
  "${BASE}/?limit=1&q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$Q'''))")"
```

**Exact disposition (point lookup):**

```bash
Q='{"EW2_NR_DISPOSIZIONE":"1236"}'
f07 "limit=1, exact disposition" \
  "${BASE}/?limit=1&q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$Q'''))")"
```

### 4) Page size comparison

```bash
f07 "limit=20, no filter" "${BASE}/?limit=20"

Q='{"DATA_BOLLA_ISO":{"$between":["2026-03-01","2026-03-31"]}}'
ENC=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$Q'''))")

f07 "limit=20, March 2026" "${BASE}/?limit=20&q=${ENC}"

f07 "limit=100, March 2026 (recommended for bulk sync)" "${BASE}/?limit=100&q=${ENC}"

f07 "limit=100, no filter" "${BASE}/?limit=100"
```

### 5) Pagination (second page)

```bash
Q='{"DATA_BOLLA_ISO":{"$between":["2026-03-01","2026-03-31"]}}'
ENC=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$Q'''))")
f07 "page 2" "${BASE}/?limit=20&offset=20&q=${ENC}"
```

### 6) OpenAPI spec (schema, not data)

```bash
curl -s -u "${INTEX_USER}:${INTEX_PASS}" \
  "https://analisi.intexsrl.com/ords/intex2/open-api-catalog/F07_003W/" \
  | python3 -m json.tool | head -40
```

---

## Performance benchmarks

Measured live against `https://analisi.intexsrl.com` (June 2026):

| Request | Typical time | Notes |
| :--- | :--- | :--- |
| `limit=1`, no filter | ~4s | Full scan to return first row |
| `DATA_BOLLA_ISO` + narrow month range | **~1–2s** | Recommended date filter |
| `DATA_BOLLA_ISO` + customer code | **~1.3s** | Selective composite filter |
| `EW2_NR_DISPOSIZIONE` exact match | **~1.3s** | Point lookup |
| `limit=20` + `DATA_BOLLA_ISO` month range | **~1.0s** | Good bulk fetch |
| `limit=100` + `DATA_BOLLA_ISO` month range | **~1.2s** | Best throughput — 5× rows for ~0.2s extra |
| `limit=20`, no filter | ~4s | Page size barely affects time without a filter |
| `limit=100`, no filter | ~4.3s | Still fast; filter matters more than page size |
| `D02_DT_BOLLA` + `$date` YTD range | **~50–60s** | Current `oracle-sync.py` path — avoid |

### What makes it slow

1. **Wrong date column** — `D02_DT_BOLLA` (timestamp) triggers a full table scan; `DATA_BOLLA_ISO` (plain date) is much faster.
2. **Wrong date syntax** — `$date` objects on timestamp columns are slower than plain `"YYYY-MM-DD"` strings on ISO columns.
3. **Wide date ranges** — YTD or multi-year windows scan more rows than a single month.
4. **`limit` is not the bottleneck** — with a good `DATA_BOLLA_ISO` filter, `limit=100` (~1.2s) is nearly as fast as `limit=20` (~1.0s) or `limit=1` (~2s). Without a filter, `limit=100` is still ~4s.

### Recommendations for sync

- Change `sync_fatture_and_seasons()` to filter on `DATA_BOLLA_ISO` instead of `D02_DT_BOLLA`.
- Use plain date strings in `$between`: `["2026-03-01","2026-03-31"]`.
- Raise `FATTURE_LIMIT` from 20 → **100** once on `DATA_BOLLA_ISO` — fewer round-trips, still ~1.2s per page.
- Sync month-by-month if a wide range is needed, rather than one large YTD query.

---

## Filter examples (`q` parameter)

All fields in the view are filterable in AutoREST. Common filters used in production:

### Date range on delivery note date (ISO)

```
F07_003W/?q={"DATA_BOLLA_ISO":{"$between":["2026-02-01","2026-03-24"]}}
```

### Customer code (exact or prefix)

```
F07_003W/?q={"EW2_CD_CLIENTE":"648"}
F07_003W/?q={"EW2_CD_CLIENTE":{"$like":"64%"}}
```

### Season (description or code)

```
F07_003W/?q={"Z11_DS_STAGIONE":{"$like":"%AI%"}}
F07_003W/?q={"EW2_CD_STAGIONE":"PE 12"}
```

### Cycle code

```
F07_003W/?q={"EW2_CD_CICLO":{"$like":"%T100%"}}
```

### Combined filter

```
F07_003W/?q={"DATA_BOLLA_ISO":{"$between":["2026-02-01","2026-03-24"]},"EW2_CD_CLIENTE":{"$like":"64%"},"EW2_CD_CICLO":{"$like":"%T100%"},"Z11_DS_STAGIONE":{"$like":"%AI%"}}
```

### Invoice date range (ISO)

```
F07_003W/?q={"DATA_FATTURA_ISO":{"$between":["2026-02-01","2026-03-24"]}}
```

### Exact disposition (point lookup)

```
F07_003W/?q={"EW2_NR_DISPOSIZIONE":"1236"}
```

> **Note**: Filtering on a field that is not present in the view returns HTTP 403.

> **Performance**: Avoid filtering on `D02_DT_BOLLA` with `$date` objects — use `DATA_BOLLA_ISO` or `DATA_FATTURA_ISO` with plain `"YYYY-MM-DD"` strings instead (see [Performance benchmarks](#performance-benchmarks)).

---

## Response fields

Fields returned by the live endpoint (from a sample `?limit=1` response). Names are lowercase in JSON.

### Key business fields

| Field | Description |
| :--- | :--- |
| `ew2_nr_disposizione` | Disposition / invoice group number |
| `ew2_riga_disposizione` | Line number within disposition |
| `ew2_cd_cliente` | Customer code |
| `ew2_cd_stagione` | Season code (e.g. `PE 12`, `AI 12`) |
| `z11_ds_stagione` | Season description |
| `d02_nr_bolla` | Delivery note number |
| `d02_dt_bolla` | Delivery note date (ISO timestamp) |
| `data_bolla_iso` | Delivery note date (ISO date, filterable) |
| `dt_fattura_iso` | Invoice date (ISO date, filterable) |
| `f07_importo_riga` | Line amount |
| `f07_importo_riga_euro` | Line amount in EUR |
| `f07_kg_fatturati` | Invoiced kg |
| `f07_nr_capi_fatturati` | Invoiced pieces |
| `ew2_cd_articolo_fiscale` | Fiscal article code |
| `ew2_ds_articolo` | Article description |
| `ew2_cd_colore` / `ew2_ds_colore` | Color code / description |
| `cw1_ds_articolo_fiscale` | Fiscal article description |
| `cw4_ds_composizione` | Material composition |
| `cw8_ragione_soc` / `r07_ragione_soc_cli` | Customer company name |

### All fields (alphabetical)

```
c01_ds_iva
c01_perc_imponibile
cd_lavorazione
cw0_ds_linea
cw1_ds_articolo_fiscale
cw4_ds_composizione
cw8_ragione_soc
cwa_ds_articolo_cliente
d02_anno_bolla
d02_cd_tipo_bolla
d02_dt_bolla
d02_nr_bolla
data_bolla_iso
ds_lavorazione
dt_fattura_iso
ew1_cd_provenienza
ew1_data_bolla_cli
ew1_nr_bolla_cli
ew1_rifer_cliente
ew2_cd_articolo_fattura
ew2_cd_articolo_fiscale
ew2_cd_cartella
ew2_cd_ciclo
ew2_cd_cliente
ew2_cd_colore
ew2_cd_composizione
ew2_cd_linea
ew2_cd_stagione
ew2_ds_articolo
ew2_ds_colore
ew2_flag_tp_ddt
ew2_flag_tp_prod
ew2_kg_ddt
ew2_modello
ew2_nr_camp_nuovi_col
ew2_nr_capi_ddt
ew2_nr_disposizione
ew2_qualita
ew2_rif_disp_cliente
ew2_riga_disposizione
ew2_scatola
f07_anno_disp_cli
f07_cd_articolo
f07_cd_ciclo
f07_cd_fase
f07_cd_iva
f07_cd_tipo_riga
f07_cd_unita_mis
f07_d02_key
f07_d03_riga
f07_ds_articolo
f07_f03_anno_documento
f07_f03_cd_tipo_documento
f07_f03_dt_documento
f07_f03_key_riferimento
f07_f03_nr_documento
f07_flag_chiusa
f07_flag_prezzo_forfait_da
f07_importo_riga
f07_importo_riga_euro
f07_key
f07_kg_fatturati
f07_note
f07_nr_capi_fatturati
f07_nr_colori_fatturati
f07_nr_disp_cli
f07_prezzo_forfait
f07_prezzo_forfait_euro
f07_prezzo_forfait_kg
f07_prezzo_forfait_kg_euro
f07_prezzo_forfait_nr
f07_prezzo_un_capi
f07_prezzo_un_capi_euro
f07_prezzo_un_colori
f07_prezzo_un_colori_euro
f07_prezzo_un_kg
f07_prezzo_un_kg_euro
f07_prezzo_unitario
f07_prezzo_unitario_euro
f07_provv_agente
f07_provv_agente_2
f07_provv_agente_3
f07_provv_agente_4
f07_qta_fatturata
f07_riga
f07_riga_disp_cli
f07_sconto_01
f07_sconto_02
f07_st_modifica
f07_st_record
f08_ds_tipo_riga
fase_ciclo
g04_ds_unita_mis
g15_ds_articolo
r07_ragione_soc_cli
z02_ds_fase
z09_cd_ciclo_cli
z09_ds_ciclo
z09_ds_ciclo_bolle_fat
z11_ds_stagione
```

---

## Seasons workaround

The dedicated seasons view `Z11_STAGIONI` is **no longer exposed** (returns 404). Seasons must be derived from `F07_003W` by collecting unique values of `ew2_cd_stagione`.

See `backend/test-return-stagioni.py` for a minimal example.

---

## Local cache mapping

`F07_003W` is synced into TimescaleDB as:

| Remote source | Local table |
| :--- | :--- |
| Disposition header fields | `fatture_testate` |
| Line fields | `fatture_righe` |
| Unique `ew2_cd_stagione` | `stagioni` |

Sync implementation: `backend/oracle-sync.py` → `sync_fatture_and_seasons()`.

Local schema: `documentation/data-model.md` and `data/migrations/create-tables.sql`.

---

## Related documentation

| File | Content |
| :--- | :--- |
| `documentation/oracle-sync.md` | Sync architecture, pagination, incremental strategy |
| `documentation/Endpoint Tabelle wash.pdf` | Email thread with filter examples from Intex admin |
| `documentation/Endpoint Intex.pdf` | General ORDS endpoint notes |
| `documentation/F07_RIGHE_FATTURE.drawio` | Underlying ERP table `F07_RIGHE_FATTURE` schema |

---

## Related ORDS views

The OpenAPI catalog also lists sibling invoice views (not currently used by the sync):

- `F07_001W` — `https://analisi.intexsrl.com/ords/intex2/open-api-catalog/F07_001W/`
- `F07_002W` — `https://analisi.intexsrl.com/ords/intex2/open-api-catalog/f07_002w/`
