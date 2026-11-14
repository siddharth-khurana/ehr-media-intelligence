
import csv
import io
import json
import re
import hashlib
from dateutil import parser as date_parser
GENDER_MAP = {
    "m": "male",
    "male": "male",
    "man": "male",
    "f": "female",
    "female": "female",
    "woman": "female",
    "o": "other",
    "other": "other",
    "unknown": "unknown",
    "u": "unknown"
}
def normalize_date(value):
    if not value:
        return None
    try:
        return date_parser.parse(
            str(value),
            dayfirst=False
        ).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None
def normalize_mrn(value):
    if value is None or str(value).strip() == "":
        return None
    return re.sub(
        r"[^A-Za-z0-9]",
        "",
        str(value)
    ).upper()
def normalize_gender(value):
    if not value:
        return "unknown"
    return GENDER_MAP.get(
        str(value).strip().lower(),
        "unknown"
    )
def parse_input(filename, content):
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    text = content.decode(
        "utf-8-sig",
        errors="replace"
    )
    # JSON FILE PARSING
    if ext == "json":
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("records", [data])
        if not isinstance(data, list):
            raise ValueError(
                "JSON must be an object or an array of records"
            )
        return data
    # CSV FILE PARSING
    if ext == "csv":
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return []
        first_row = [
            value.strip().lower()
            for value in rows[0]
        ]
        known_headers = {
            "patient_id",
            "patientid",
            "id",
            "mrn",
            "medical_record_number",
            "full_name",
            "date_of_birth"
        }
        if known_headers.intersection(first_row):
            headers = first_row
            data_rows = rows[1:]
        else:
            headers = [
                "patient_id",
                "full_name",
                "dob",
                "gender",
                "mrn",
                "record_id",
                "record_date",
                "resource_type",
                "title",
                "text_content"
            ]
            data_rows = rows
        parsed = []
        for row_number, row in enumerate(data_rows, start=1):
            if not row or not any(value.strip() for value in row):
                continue
            if len(row) != len(headers):
                raise ValueError(
                    f"CSV row {row_number} has {len(row)} columns; "
                    f"expected {len(headers)}"
                )
            parsed.append(dict(zip(headers, row)))
        return parsed
    # TXT FILE PARSING
    if ext in ("txt", "text"):
        # Split records whenever a new patient header appears.
        chunks = re.split(
            r"(?im)(?=^(?:Patient:\s*)?[A-Z][^\n]*\bMRN[- ]?\d+\)?\s*$)",
            text.strip()
        )
        parsed = []
        for index, chunk in enumerate(chunks, start=1):
            lines = [
                line.strip()
                for line in chunk.splitlines()
                if line.strip() and line.strip() != "---"
            ]
            if not lines:
                continue
            first_line = lines[0]
            # Support:
            # Patient: Chris Jordan (MRN-007)
            # Morgan Blake - MRN006
            # Riley Quinn MRN-008
            patient_match = re.match(
                r"^(?:Patient:\s*)?(?P<name>.+?)\s*"
                r"(?:\(\s*MRN[- ]?(?P<mrn1>\d+)\s*\)"
                r"|-\s*MRN[- ]?(?P<mrn2>\d+)"
                r"|\s+MRN[- ]?(?P<mrn3>\d+))$",
                first_line,
                re.IGNORECASE
            )
            if not patient_match:
                raise ValueError(
                    f"Could not identify patient and MRN "
                    f"in TXT record {index}: {first_line}"
                )
            full_name = patient_match.group("name").strip()
            mrn_number = (
                patient_match.group("mrn1")
                or patient_match.group("mrn2")
                or patient_match.group("mrn3")
            )
            mrn = "MRN" + mrn_number
            # Mapping used for this synthetic sample dataset.
            patient_id = "patient-" + mrn_number
            record_date = None
            title = "Clinical Note"
            text_parts = []
            for line in lines[1:]:
                # Extract record date.
                date_value = re.sub(
                    r"^Date:\s\*",
                    "",
                    line,
                    flags=re.IGNORECASE
                ).strip()
                try:
                    parsed_date = date_parser.parse(
                        date_value,
                        dayfirst=True,
                        fuzzy=False
                    )
                    record_date = parsed_date.date().isoformat()
                    continue
                except (ValueError, TypeError, OverflowError):
                    pass
                # Extract note type and content.
                if ":" in line:
                    label, value = line.split(":", 1)
                    label = label.strip().lower()
                    value = value.strip()
                    if label == "note":
                        title = "Clinical Note"
                        text_parts.append(value)
                        continue
                    elif label == "lab":
                        title = "Lab Note"
                        text_parts.append(value)
                        continue
                    elif label == "imaging":
                        title = "Imaging Note"
                        text_parts.append(value)
                        continue
                text_parts.append(line)
            if not record_date:
                raise ValueError(
                    f"Missing or invalid date in TXT record {index}"
                )
            resource_type = (
                "DiagnosticReport"
                if title == "Lab Note"
                else "DocumentReference"
            )
            text_content = " ".join(text_parts)
            record_id = f"txt-{mrn_number}-{record_date}"
            parsed.append({
                "patient_id": patient_id,
                "full_name": full_name,
                "dob": None,
                "gender": "unknown",
                "mrn": mrn,
                "record_id": record_id,
                "record_date": record_date,
                "resource_type": resource_type,
                "title": title,
                "text_content": text_content
            })
        return parsed
    raise ValueError(
        "Unsupported file type. Upload JSON, CSV, or TXT."
    )
def clean_records(raw_records):
    cleaned = []
    audit_logs = []
    seen = set()
    for index, raw in enumerate(raw_records, start=1):
        if not isinstance(raw, dict):
            audit_logs.append({
                "record": index,
                "changes": ["Skipped non-object record"],
                "status": "skipped"
            })
            continue
        changes = []
        # PATIENT ID
        patient_id = str(
            raw.get("patient_id")
            or raw.get("patientid")
            or raw.get("id")
            or ""
        ).strip()
        if not patient_id:
            mrn_guess = normalize_mrn(
                raw.get("mrn")
                or raw.get("medical_record_number")
            )
            if not mrn_guess:
                audit_logs.append({
                    "record": index,
                    "changes": [
                        "Skipped: no patient identifier or MRN"
                    ],
                    "status": "skipped"
                })
                continue
            patient_id = "mrn-" + mrn_guess.lower()
            changes.append(
                "Generated patient_id from MRN"
            )
        # PATIENT NAME
        name = str(
            raw.get("full_name")
            or raw.get("name")
            or "Unknown Patient"
        ).strip()
        if name == "Unknown Patient":
            changes.append(
                "Filled missing name with Unknown Patient"
            )
        # DATE OF BIRTH
        dob_raw = (
            raw.get("dob")
            or raw.get("date_of_birth")
        )
        dob = normalize_date(dob_raw)
        if dob_raw and not dob:
            changes.append(
                f"Invalid DOB '{dob_raw}' set to null"
            )
        elif dob_raw and dob != str(dob_raw):
            changes.append(
                f"Normalized DOB from '{dob_raw}' to '{dob}'"
            )
        # GENDER
        gender_raw = (
            raw.get("gender")
            or raw.get("sex")
        )
        gender = normalize_gender(gender_raw)
        if gender_raw and gender != str(gender_raw).lower():
            changes.append(
                f"Normalized gender '{gender_raw}' to '{gender}'"
            )
        # MRN
        mrn_raw = (
            raw.get("mrn")
            or raw.get("medical_record_number")
        )
        mrn = normalize_mrn(mrn_raw)
        if mrn_raw and mrn != str(mrn_raw):
            changes.append(
                f"Normalized MRN '{mrn_raw}' to '{mrn}'"
            )
        # RECORD DATE
        record_date_raw = (
            raw.get("record_date")
            or raw.get("date")
            or raw.get("created_at")
        )
        record_date = normalize_date(record_date_raw)
        if record_date_raw and not record_date:
            changes.append(
                f"Invalid record date '{record_date_raw}' set to null"
            )
        elif record_date_raw and record_date != str(record_date_raw):
            changes.append(
                f"Normalized record date to {record_date}"
            )
        # RECORD TITLE
        title = str(
            raw.get("title")
            or raw.get("document_title")
            or raw.get("record_type")
            or "Clinical document"
        )
        # RECORD CONTENT
        text_content = str(
            raw.get("text_content")
            or raw.get("text")
            or raw.get("content")
            or raw.get("notes")
            or ""
        )
        # FHIR RESOURCE TYPE
        resource_type = str(
            raw.get("resource_type")
            or raw.get("type")
            or "DocumentReference"
        )
        if resource_type.lower() in (
            "lab",
            "laboratory",
            "diagnosticreport"
        ):
            resource_type = "DiagnosticReport"
        else:
            resource_type = "DocumentReference"
        # RECORD ID
        record_id = str(
            raw.get("record_id")
            or raw.get("document_id")
            or hashlib.sha256(
                f"{patient_id}|{record_date}|{title}|{text_content}".encode()
            ).hexdigest()[:20]
        )
        # DUPLICATE DETECTION
        fingerprint = hashlib.sha256(
            f"{patient_id}|{record_date}|{title}|{text_content}".encode()
        ).hexdigest()
        if fingerprint in seen:
            audit_logs.append({
                "record": index,
                "patient_id": patient_id,
                "changes": ["Duplicate record removed"],
                "status": "duplicate"
            })
            continue
        seen.add(fingerprint)
        if not raw.get("patient_id") and raw.get("patientid"):
            changes.append(
                "Mapped patientid to patient_id"
            )
        # CLEANED RECORD
        cleaned.append({
            "patient_id": patient_id,
            "full_name": name,
            "dob": dob,
            "gender": gender,
            "mrn": mrn,
            "record_id": record_id,
            "record_date": record_date,
            "title": title,
            "text_content": text_content,
            "resource_type": resource_type,
            "source_index": index,
            "audit": changes
        })
        audit_logs.append({
            "record": index,
            "patient_id": patient_id,
            "changes": changes,
            "status": "cleaned"
        })
    return cleaned, audit_logs
