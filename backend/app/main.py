import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import (
    init_db,
    save_patient,
    save_record,
    save_bundle,
    get_patient,
    list_patients,
    get_bundle,
    get_records,
)

from app.schemas import SearchRequest, IngestResponse

from app.services.ingestion.cleaner import (
    parse_input,
    clean_records,
)

from app.services.validation.validator import validate_records

from app.services.fhir.mapper import (
    build_bundle,
    validate_bundle,
    _id,
)

from app.services.ai.summarizer import summarize_patient

from app.services.search.engine import (
    index_records,
    search_records,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for folder in [
        settings.upload_dir,
        settings.fhir_bundle_dir,
        settings.chroma_path,
        "./storage",
    ]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Synthetic EHR ingestion, FHIR normalization, "
        "AI summaries and semantic search API"
    ),
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest(files: list[UploadFile] = File(...)):
    all_cleaned = []
    audit_logs = []
    errors = []
    processed_files = 0

    # 1. Parse and clean uploaded files.
    for upload in files:
        content = await upload.read()

        if len(content) > settings.max_upload_mb * 1024 * 1024:
            errors.append(
                f"{upload.filename}: exceeds "
                f"{settings.max_upload_mb} MB limit"
            )
            continue

        try:
            raw = parse_input(upload.filename or "", content)
            cleaned, logs = clean_records(raw)

            all_cleaned.extend(cleaned)

            audit_logs.extend([
                {"filename": upload.filename, **log}
                for log in logs
            ])

            Path(
                settings.upload_dir,
                Path(upload.filename or "upload").name,
            ).write_bytes(content)

            processed_files += 1

        except Exception as exc:
            errors.append(f"{upload.filename}: {exc}")

    # 2. Validate all cleaned records before saving anything.
    validation_report = validate_records(all_cleaned)

    errors_by_record = {}

    for item in validation_report.get("errors", []):
        record_number = item.get("record")

        if record_number is not None:
            errors_by_record.setdefault(record_number, []).append(item)

    valid_records = []

    for record_number, row in enumerate(all_cleaned, start=1):
        record_errors = errors_by_record.get(record_number, [])

        if record_errors:
            messages = [
                f"{item.get('field', 'unknown field')}: "
                f"{item.get('message', 'Validation failed')}"
                for item in record_errors
            ]

            audit_logs.append({
                "record": record_number,
                "patient_id": row.get("patient_id"),
                "changes": messages,
                "status": "rejected",
            })

            errors.append(
                f"Record {record_number} rejected: " + "; ".join(messages)
            )
            continue

        valid_records.append(row)

    validation_report["accepted_records"] = len(valid_records)
    validation_report["rejected_records"] = (
        len(all_cleaned) - len(valid_records)
    )

    # 3. Handle empty or fully rejected ingestion.
    if not valid_records:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid records to ingest",
                "errors": errors,
                "audit_logs": audit_logs,
                "validation": validation_report,
            },
        )

    # 4. Save only validated records.
    grouped = {}

    for row in valid_records:
        pid = row["patient_id"]

        patient = {
            key: row.get(key)
            for key in (
                "patient_id",
                "full_name",
                "dob",
                "gender",
                "mrn",
            )
        }

        existing = grouped.get(pid)

        if (
            existing
            and existing.get("mrn")
            and patient.get("mrn")
            and existing["mrn"] != patient["mrn"]
        ):
            audit_logs.append({
                "patient_id": pid,
                "changes": [
                    f"Conflicting MRN values: retained first value "
                    f"{existing['mrn']}"
                ],
                "status": "warning",
            })

            patient["mrn"] = existing["mrn"]

        elif existing:
            patient = {
                **existing,
                **{
                    key: value
                    for key, value in patient.items()
                    if value not in (None, "")
                },
            }

        grouped[pid] = patient
        save_patient(patient)

        encounter = {
            "record_id": row["record_id"],
            "patient_id": pid,
            "resource_type": row["resource_type"],
            "record_date": row["record_date"],
            "title": row["title"],
            "text_content": row["text_content"],
            "audit": row["audit"],
        }

        save_record({
            **encounter,
            "fhir": {"resourceType": "Pending"},
        })

    # 5. Generate and save FHIR bundles for patients with accepted records.
    for pid, patient in grouped.items():
        db_rows = get_records(pid)
        records = []

        for record in db_rows:
            records.append({
                "record_id": record["record_id"],
                "patient_id": pid,
                "resource_type": record["resource_type"],
                "record_date": record["record_date"],
                "title": record["title"],
                "text_content": record["text_content"],
                "audit": json.loads(record["audit_json"]),
            })

        try:
            bundle = build_bundle(patient, records)
            fhir_validation = validate_bundle(bundle)

            save_bundle(pid, bundle, fhir_validation)

            Path(
                settings.fhir_bundle_dir,
                f"{pid}.json",
            ).write_text(
                json.dumps(bundle, indent=2),
                encoding="utf-8",
            )

            resources = {
                entry["resource"].get("id"): entry["resource"]
                for entry in bundle.get("entry", [])
                if entry.get("resource", {}).get("resourceType")
                in ("DocumentReference", "DiagnosticReport")
            }

            for record in records:
                record["fhir"] = resources.get(
                    _id(record["record_id"]),
                    {"resourceType": "Pending"},
                )
                save_record(record)

        except Exception as exc:
            errors.append(f"FHIR bundle for {pid}: {exc}")

    # 6. Return accepted record counts and complete validation results.
    return IngestResponse(
        files_processed=processed_files,
        patients_processed=len(grouped),
        records_processed=len(valid_records),
        errors=errors,
        audit_logs=audit_logs,
        validation=validation_report,
    )


@app.get("/patients")
def patients():
    return {
        "items": list_patients()
    }


@app.get("/patients/{patient_id}")
def patient_detail(patient_id: str):
    patient = get_patient(patient_id)

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    return {
        "patient": patient,
        "records": [
            {
                key: record[key]
                for key in (
                    "record_id",
                    "resource_type",
                    "record_date",
                    "title",
                    "text_content",
                )
            }
            for record in get_records(patient_id)
        ],
    }


@app.get("/patients/{patient_id}/bundle")
def patient_bundle(patient_id: str):
    result = get_bundle(patient_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="FHIR Bundle not found",
        )

    return result


@app.post("/patients/{patient_id}/summarize")
def patient_summary(patient_id: str):
    if not get_patient(patient_id):
        raise HTTPException(
            status_code=404,
            detail="Patient not found",
        )

    try:
        return summarize_patient(patient_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Summary generation failed: {exc}",
        )


@app.post("/index")
def index():
    try:
        return index_records()

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Indexing failed: {exc}",
        )


@app.post("/search")
def search(payload: SearchRequest):
    try:
        search_result = search_records(
            query=payload.query,
            patient_id=payload.patient_id,
            resource_type=payload.resource_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            top_k=payload.top_k,
            min_relevance_score=payload.min_relevance_score,
            page=payload.page,
            page_size=payload.page_size,
        )

        return {
            "query": payload.query,
            "patient_id": payload.patient_id,
            "count": len(search_result["results"]),
            "total": search_result["total"],
            "page": payload.page,
            "page_size": payload.page_size,
            "total_pages": search_result["total_pages"],
            "results": search_result["results"],
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "Search failed. Run POST /index first. "
                f"Details: {str(e)}"
            )
        )


@app.get("/validation/{patient_id}")
def validation_report(patient_id: str):
    result = get_bundle(patient_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="FHIR Bundle not found",
        )

    return result["validation"]