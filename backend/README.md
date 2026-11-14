# EHR Media Intelligence Platform – Backend

A FastAPI backend for the technical assessment. It ingests synthetic EHR records, cleans them, maps them to HL7 FHIR R4, generates AI summaries, and supports semantic search.

> **Privacy:** Use synthetic/demo data only. Never commit real patient data, PHI, API keys, or production exports.

## Implemented assessment tasks

1. **Ingestion & cleaning:** JSON, CSV and line-based TXT; missing identifiers, DOB/date normalization, gender mapping, MRN normalization, duplicate detection, canonical patient fields, and per-record audit logs.
2. **FHIR R4:** `Patient`, `Encounter`, `DocumentReference`, `DiagnosticReport`, and per-patient `Bundle`; validates resources with `fhir.resources`; persists Bundle JSON and validation report.
3. **AI summaries:** OpenAI Chat Completions integration; concise structured output, disclaimer, and SQLite cache keyed by patient ID and record-content hash. Without an API key, a clearly labelled local fallback is returned.
4. **Semantic search:** Sentence Transformers embeddings stored in persistent ChromaDB; top-five results, resource type/date filters.
5. **Frontend API support:** endpoints are ready for a separate React/Tailwind frontend.

## Requirements

- Python 3.11+
- OpenAI API key is optional for local setup; required for LLM-generated summaries.
- First run of Sentence Transformers downloads the embedding model and may take time.

## Setup (Ubuntu/Linux)

```bash
cd ehr-media-intelligence-backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env` if you want LLM summaries. Keep `.env` private.

## Run

```bash
uvicorn app.main:app --reload
```

Open:
- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## API workflow

### 1. Ingest synthetic data

Use Swagger `POST /ingest` and upload one or more of:
- `data/sample_records.json`
- `data/sample_records.csv`
- `data/sample_records.txt`

Example with curl:

```bash
curl -X POST "http://127.0.0.1:8000/ingest" \
  -F "files=@data/sample_records.json"
```

### 2. Review patients and FHIR

- `GET /patients`
- `GET /patients/{patient_id}`
- `GET /patients/{patient_id}/bundle`
- `GET /validation/{patient_id}`

### 3. Generate patient summary

`POST /patients/{patient_id}/summarize`

Example:

```bash
curl -X POST http://127.0.0.1:8000/patients/patient-001/summarize
```

The response includes `confidence`, `disclaimer`, and `cached`.

### 4. Index and search

First call `POST /index`, then `POST /search`:

```json
{
  "query": "patient with cough and fever discharge information",
  "resource_type": "DocumentReference",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "top_k": 5
}
```

`top_k` is limited to five.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/ingest` | Upload JSON/CSV/TXT |
| GET | `/patients` | List patients |
| GET | `/patients/{patient_id}` | Patient and record details |
| GET | `/patients/{patient_id}/bundle` | Retrieve FHIR Bundle |
| GET | `/validation/{patient_id}` | Bundle validation report |
| POST | `/patients/{patient_id}/summarize` | Generate/cache summary |
| POST | `/index` | Embed and index stored records |
| POST | `/search` | Semantic search with filters |

## Tests

```bash
pytest -q
```

The test suite includes cleaning edge cases and an API health check.

## Design notes and limitations

- The TXT parser expects `key: value` lines and blank lines between records.
- Conflicting MRNs for the same patient ID are logged; the first non-empty MRN is retained.
- This assessment implementation creates a synthetic ambulatory Encounter to provide valid encounter references. Real encounter matching requires source encounter identifiers and mapping rules.
- FHIR model validation is performed locally with the R4 `fhir.resources` package. For deployment-grade conformance, also validate generated Bundles against the official HL7 FHIR R4 validator.
- The initial semantic search is designed for the assessment-sized dataset. Benchmark the 50-record, under-two-second requirement on the target machine and record measured latency in the write-up.
- AI output is informational only, may be incomplete, and must be reviewed by qualified clinical staff. No diagnosis or treatment decision should be based on the generated summary.
- CORS is permissive for local development. Restrict allowed origins, add authentication/authorization, rate limiting, audit access logs, encryption, and secure secret management before any real deployment.
