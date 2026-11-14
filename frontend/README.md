# EHR Media Intelligence Platform — Frontend

Responsive React + Vite + Tailwind CSS frontend for the FastAPI backend.

## Features

- Responsive desktop sidebar and mobile navigation
- Natural-language semantic search with top-five ranked results
- Resource type and date filters
- Patient directory and patient detail drawer
- AI clinical summary generation and disclaimer display
- FHIR Bundle resource list, validation status and raw JSON viewer
- JSON, CSV and TXT file upload with ingestion audit log display
- Semantic index refresh action
- API connection status, loading states, errors, empty states and accessible labels

## Requirements

- Node.js 18+
- Running backend at `http://127.0.0.1:8000` (or configure another URL)

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Open the Vite URL shown in the terminal, usually http://localhost:5173.

## Backend connection

Set `VITE_API_BASE_URL` in `.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The frontend calls these backend endpoints:

- `GET /health`
- `GET /patients`
- `GET /patients/{patient_id}`
- `GET /patients/{patient_id}/bundle`
- `GET /validation/{patient_id}`
- `POST /ingest`
- `POST /patients/{patient_id}/summarize`
- `POST /index`
- `POST /search`

## Production build

```bash
npm run build
npm run preview
```

Build output is generated in `dist/`.

## Notes

- This is a frontend source implementation; it requires the backend API to be running.
- Use synthetic/de-identified demo records only. Do not upload real patient data.
- Backend CORS is currently permissive for local development. Restrict CORS origins before deployment.
