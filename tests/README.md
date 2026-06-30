# Intex prompt regression tests

This suite checks that `backend/prompts.txt` produces predictable JSON and that the app routes each response to the correct UI tab and backend API — the same behaviour as `frontend/app/src/App.jsx` (`applyLlmResponse`).

Tests run **sequentially** (one LLM call at a time). Do not use `pytest-xdist` or parallel workers for the live LLM tests.

---

## Two kinds of tests

### Offline (`test_routing_offline.py`)

**Does not call the LLM.** No API key required. Fast and free.

Validates the **test harness and routing logic**:

- Expected JSON in `cases.py` (derived from `prompts.txt` examples) is internally consistent.
- Each case maps to the correct UI tab (`bolle`, `fatture`, `offerte`, `discrepanze`).
- Each case maps to the correct backend request, e.g.:
  - `GET /api/fatture?data_inizio=…&page=1&limit=50`
  - `GET /api/fatture/1207`
  - `GET /api/bolle/4761`
  - Discrepanze tab with no list API

Use offline tests when editing `cases.py`, `routing.py`, or the documented examples in `prompts.txt`.

**Question answered:** *“If the LLM returned this JSON, would the app do the right thing?”*

### Online (`test_prompts.py`)

**Calls the real LLM** (OpenAI or Gemini, same as `/llmrequest`). Requires API keys in `backend/.env`.

For each of **15 cases**:

1. Builds the full prompt (`prompts.txt` + user message), same as the first turn of a chat.
2. Sends one request to the configured LLM provider.
3. Parses the JSON response (same logic as `frontend/app/src/utils/llm.js`).
4. Asserts `area`, `filtri`, `azione`, and derived routing match the expected values in `cases.py`.

**Question answered:** *“Does the LLM actually return the JSON we expect?”*

**Cost:** 15 LLM API requests per full online run.

---

## Prerequisites

### Local (outside Docker)

- Python **3.9+** (3.11 recommended; the backend Docker image uses 3.11)
- Dependencies installed by `run.sh`:
  - `tests/requirements.txt` (pytest)
  - `backend/requirements.txt`

### Docker (recommended for online tests)

- Backend container running: `cd backend && docker compose up -d`
- `tests/` mounted at `/tests` inside `intex-api`
- LLM keys passed into the container via `backend/docker-compose.yml` (sourced from `backend/.env`):

```env
LLM_PROVIDER=OPENAI
OPENAI_APIKEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Or for Gemini:

```env
LLM_PROVIDER=GEMINI
GEMINI_APIKEY=...
GEMINI_MODEL=gemini-2.0-flash
```

If the container was created before the `/tests` volume was added, recreate it once:

```bash
cd backend && docker compose up -d --force-recreate
```

---

## How to run

### Offline only

**Local:**

```bash
cd tests
python3 -m pip install -r requirements.txt
python3 -m pytest test_routing_offline.py -v
```

**Docker:**

```bash
docker exec -w /tests intex-api \
  bash -c "pip install -q -r requirements.txt && python -m pytest test_routing_offline.py -v"
```

Or via the helper script:

```bash
./tests/run-docker.sh test_routing_offline.py -v
```

### Online only (live LLM)

**Local:**

```bash
./tests/run.sh test_prompts.py -v
```

Loads `backend/.env` automatically. Skips all online tests if no API key is set.

**Docker:**

```bash
./tests/run-docker.sh test_prompts.py -v
```

### Full suite (offline + online)

**Local:**

```bash
./tests/run.sh -v
```

**Docker:**

```bash
./tests/run-docker.sh -v
```

**Local, delegating to Docker:**

```bash
./tests/run.sh --docker -v
```

### Single case

```bash
./tests/run-docker.sh -k example_4_dettaglio_fattura -v
```

### Other pytest options

Any pytest flags can be passed through:

```bash
./tests/run-docker.sh test_prompts.py -v --maxfail=1
./tests/run.sh test_routing_offline.py -q
```

---

## Output

### Terminal

Offline and online tests print normal pytest output. Online tests also print one short line per case:

```
PASSED example_1_fatture_anno_cliente  (details → tests/results/prompt-test_20260630_143045.txt)
```

At the end of an online run:

```
Report written to: tests/results/prompt-test_20260630_143045.txt
```

Full prompts and LLM responses are **not** printed to the terminal.

### Report files (`tests/results/`)

Each online run creates one timestamped file:

```
tests/results/prompt-test_YYYYMMDD_HHMMSS.txt
```

Each case section in the file includes:

- Run timestamp
- User message
- Full prompt sent to the LLM
- Raw LLM response
- Parsed JSON
- Derived routing (tab, API path, export action)
- Failures (if any)

`.txt` files are gitignored; the `results/` directory is kept in git via `.gitkeep`.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMPT_TEST_REFERENCE_DATE` | `2026-06-30` | Date used for `{{OGGI}}` substitution in prompts and expectations |
| `LLM_PROVIDER` | `OPENAI` | `OPENAI` or `GEMINI` |
| `OPENAI_APIKEY` | — | Required for OpenAI online tests |
| `GEMINI_APIKEY` | — | Required for Gemini online tests |
| `INTEX_API_CONTAINER` | `intex-api` | Container name for `run-docker.sh` |

Example with a custom reference date:

```bash
PROMPT_TEST_REFERENCE_DATE=2026-06-18 ./tests/run-docker.sh test_prompts.py -v
```

---

## Project layout

| File | Purpose |
|------|---------|
| `cases.py` | 15 test cases: user message + expected JSON + routing |
| `routing.py` | Maps LLM JSON → UI tab + backend API (mirrors `App.jsx`) |
| `llm_parse.py` | Parses LLM output (mirrors `utils/llm.js`) |
| `reporting.py` | Writes timestamped report files |
| `test_routing_offline.py` | Offline routing / case consistency tests |
| `test_prompts.py` | Live LLM regression tests |
| `conftest.py` | Shared fixtures (reference date, LLM caller, report writer) |
| `run.sh` | Run locally; loads `backend/.env` |
| `run-docker.sh` | Run inside `intex-api` container |
| `results/` | Timestamped online test reports (`.txt`, gitignored) |

---

## Adding a test case

1. Add an example to `backend/prompts.txt` (user message → expected JSON).
2. Add a matching entry to `PROMPT_CASES` in `cases.py`.
3. Run offline tests first (no API cost):

   ```bash
   ./tests/run-docker.sh test_routing_offline.py -v
   ```

4. Run the new case online:

   ```bash
   ./tests/run-docker.sh -k your_new_case_id -v
   ```

---

## Quick reference

| Goal | Command |
|------|---------|
| Offline, local | `cd tests && python3 -m pytest test_routing_offline.py -v` |
| Offline, Docker | `./tests/run-docker.sh test_routing_offline.py -v` |
| Online, local | `./tests/run.sh test_prompts.py -v` |
| Online, Docker | `./tests/run-docker.sh test_prompts.py -v` |
| Everything, Docker | `./tests/run-docker.sh -v` |
| One case | `./tests/run-docker.sh -k example_4_dettaglio_fattura -v` |
