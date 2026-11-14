
import uuid
import base64
import json

from datetime import datetime, date, timezone

from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.diagnosticreport import DiagnosticReport
from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.bundle import Bundle


def _id(value):
    safe = "".join(
        c.lower() if c.isalnum() or c == "-" else "-"
        for c in str(value)
    )
    return safe.strip("-")[:60] or str(uuid.uuid4())


def _urn(resource_type, resource_id):
    """Generate a stable UUID reference for Bundle resources."""
    value = f"{resource_type}/{resource_id}"
    resource_uuid = uuid.uuid5(uuid.NAMESPACE_URL, value)
    return f"urn:uuid:{resource_uuid}"


def _serialize_model(model):
    """Convert FHIR model into JSON-compatible dictionary."""
    return json.loads(model.json(exclude_none=True))


def _fhir_datetime(value=None):
    """Convert a supplied date/datetime into FHIR-compatible dateTime."""
    if value is None or str(value).strip() == "":
        return None

    if isinstance(value, datetime):
        dt = value

    elif isinstance(value, date):
        dt = datetime.combine(value, datetime.min.time())

    else:
        value = str(value).strip()

        if len(value) == 10:
            value = f"{value}T00:00:00Z"

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError(f"Invalid dateTime value: {value}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat()


def map_patient(row):
    data = {
        "resourceType": "Patient",
        "id": _id(row["patient_id"]),
        "identifier": [
            {
                "system": "urn:local:mrn",
                "value": row["mrn"]
            }
        ] if row.get("mrn") else [],
        "name": [
            {"text": row["full_name"]}
        ],
        "gender": row.get("gender") or "unknown"
    }

    if row.get("dob"):
        data["birthDate"] = str(row["dob"])

    patient = Patient.parse_obj(data)

    return _serialize_model(patient)


def map_record(row, patient_ref, encounter_ref):
    rid = _id(row["record_id"])
    record_date = _fhir_datetime(row.get("record_date"))

    if row["resource_type"] == "DiagnosticReport":
        data = {
            "resourceType": "DiagnosticReport",
            "id": rid,
            "status": "final",
            "code": {
                "text": row.get("title") or "Diagnostic report"
            },
            "subject": {
                "reference": patient_ref
            },
            "encounter": {
                "reference": encounter_ref
            },
            "conclusion": (
                row.get("text_content")
                or "No conclusion supplied."
            )
        }

        if record_date:
            data["effectiveDateTime"] = record_date

        report = DiagnosticReport.parse_obj(data)

        return _serialize_model(report)

    data = {
        "resourceType": "DocumentReference",
        "id": rid,
        "status": "current",
        "type": {
            "text": row.get("title") or "Clinical document"
        },
        "subject": {
            "reference": patient_ref
        },
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain",
                    "title": row.get("title"),
                    "data": base64.b64encode(
                        (row.get("text_content") or "").encode("utf-8")
                    ).decode("ascii")
                }
            }
        ],
        "context": {
            "encounter": [
                {"reference": encounter_ref}
            ]
        }
    }

    if record_date:
        data["date"] = record_date

    document = DocumentReference.parse_obj(data)

    return _serialize_model(document)


def build_bundle(patient, records):
    pid = _id(patient["patient_id"])

    patient_ref = _urn("Patient", pid)

    encounter_id = f"enc-{pid}"
    encounter_ref = _urn("Encounter", encounter_id)

    patient_resource = map_patient(patient)

    encounter_data = {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "class": {
            "system": (
                "http://terminology.hl7.org/"
                "CodeSystem/v3-ActCode"
            ),
            "code": "AMB",
            "display": "ambulatory"
        },
        "subject": {
            "reference": patient_ref
        }
    }

    encounter = Encounter.parse_obj(encounter_data)
    encounter_resource = _serialize_model(encounter)

    resources = [
        patient_resource,
        encounter_resource
    ]

    for record in records:
        resources.append(
            map_record(
                record,
                patient_ref,
                encounter_ref
            )
        )

    entries = []

    for resource in resources:
        resource_type = resource["resourceType"]
        resource_id = resource["id"]

        entries.append({
            "fullUrl": _urn(resource_type, resource_id),
            "resource": resource
        })

    bundle_data = {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": _fhir_datetime(
            datetime.now(timezone.utc)
        ),
        "entry": entries
    }

    validated_bundle = Bundle.parse_obj(bundle_data)

    return _serialize_model(validated_bundle)


def validate_bundle(bundle):
    """
    Validate FHIR R4B Bundle structure and internal references.
    This is application-level validation, not full HL7 conformance.
    """

    errors = []

    try:
        validated = Bundle.parse_obj(bundle)
        data = _serialize_model(validated)

    except Exception as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "specification": "FHIR R4B model and reference validation"
        }

    entries = data.get("entry", [])

    full_urls = set()
    resource_keys = set()

    # Validate resource entries and identities
    for index, entry in enumerate(entries):
        resource = entry.get("resource")

        if not resource:
            errors.append(
                f"Entry {index}: Missing resource"
            )
            continue

        full_url = entry.get("fullUrl")
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")

        if not full_url:
            errors.append(
                f"Entry {index}: Missing fullUrl"
            )

        elif full_url in full_urls:
            errors.append(
                f"Entry {index}: Duplicate fullUrl: {full_url}"
            )

        else:
            full_urls.add(full_url)

        if not resource_type or not resource_id:
            errors.append(
                f"Entry {index}: Missing resourceType or resource ID"
            )
            continue

        resource_keys.add(
            f"{resource_type}/{resource_id}"
        )

        expected_url = _urn(
            resource_type,
            resource_id
        )

        if full_url and full_url != expected_url:
            errors.append(
                f"Entry {index}: fullUrl does not match resource identity"
            )

    # Validate internal references recursively
    def check_references(value, path="Bundle"):
        if isinstance(value, dict):

            reference = value.get("reference")

            if isinstance(reference, str):

                if reference.startswith("urn:uuid:"):
                    if reference not in full_urls:
                        errors.append(
                            f"{path}: Unresolved reference: {reference}"
                        )

                elif "/" in reference and not reference.startswith("#"):
                    if reference not in resource_keys:
                        errors.append(
                            f"{path}: Unresolved resource reference: {reference}"
                        )

            for key, child in value.items():
                check_references(
                    child,
                    f"{path}.{key}"
                )

        elif isinstance(value, list):

            for index, child in enumerate(value):
                check_references(
                    child,
                    f"{path}[{index}]"
                )

    check_references(data)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "specification": "FHIR R4B model and reference validation"
    }
