
from datetime import date
from collections import Counter

VALID_GENDERS = {
    "male",
    "female",
    "other",
    "unknown"
}

VALID_RESOURCE_TYPES = {
    "DocumentReference",
    "DiagnosticReport"
}


def validate_records(records):
    errors = []
    warnings = []
    seen_record_ids = set()

    for index, record in enumerate(records, start=1):

        patient_id = record.get("patient_id")
        record_id = record.get("record_id")

        # Required patient fields
        if not patient_id:
            errors.append({
                "record": index,
                "field": "patient_id",
                "message": "Missing patient ID"
            })

        if not record.get("full_name") or (
            record.get("full_name") == "Unknown Patient"
        ):
            warnings.append({
                "record": index,
                "field": "full_name",
                "message": "Patient name is missing or unknown"
            })

        if not record.get("mrn"):
            warnings.append({
                "record": index,
                "field": "mrn",
                "message": "Missing medical record number"
            })

        # Date validation
        for field in ("dob", "record_date"):
            value = record.get(field)

            if field == "record_date" and not value:
                errors.append({
                    "record": index,
                    "field": field,
                    "message": "Record date is required"
                })
                continue

            if value:
                try:
                    parsed = date.fromisoformat(str(value))

                    if field == "dob" and parsed > date.today():
                        errors.append({
                            "record": index,
                            "field": field,
                            "message": "DOB cannot be in the future"
                        })

                    if field == "record_date" and parsed > date.today():
                        warnings.append({
                            "record": index,
                            "field": field,
                            "message": "Record date is in the future"
                        })

                except ValueError:
                    errors.append({
                        "record": index,
                        "field": field,
                        "message": "Invalid date format; expected YYYY-MM-DD"
                    })

        # Gender validation
        gender = record.get("gender")

        if gender and gender not in VALID_GENDERS:
            warnings.append({
                "record": index,
                "field": "gender",
                "message": "Unrecognized gender value"
            })

        # Record content
        if not record.get("title"):
            warnings.append({
                "record": index,
                "field": "title",
                "message": "Missing record title"
            })

        if not record.get("text_content"):
            warnings.append({
                "record": index,
                "field": "text_content",
                "message": "Record content is empty"
            })

        # FHIR resource type
        resource_type = record.get("resource_type")

        if resource_type not in VALID_RESOURCE_TYPES:
            errors.append({
                "record": index,
                "field": "resource_type",
                "message": "Unsupported FHIR resource type"
            })

        # Duplicate record ID
        if record_id:
            if record_id in seen_record_ids:
                errors.append({
                    "record": index,
                    "field": "record_id",
                    "message": "Duplicate record ID"
                })

            seen_record_ids.add(record_id)

    return {
        "total_records": len(records),
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings
    }
