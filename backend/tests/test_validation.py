
from app.services.validation.validator import validate_records


def sample_record():
    return {
        "patient_id": "patient-001",
        "full_name": "Alex Morgan",
        "dob": "1990-05-15",
        "gender": "male",
        "mrn": "MRN001",
        "record_id": "record-001",
        "record_date": "2025-06-15",
        "resource_type": "DocumentReference",
        "title": "Clinical Note",
        "text_content": "Patient record for testing."
    }


def test_valid_record():
    result = validate_records([sample_record()])

    assert result["valid"] is True
    assert result["error_count"] == 0


def test_missing_patient_id():
    record = sample_record()
    record["patient_id"] = None

    result = validate_records([record])

    assert result["valid"] is False
    assert any(
        error["field"] == "patient_id"
        for error in result["errors"]
    )


def test_invalid_dob():
    record = sample_record()
    record["dob"] = "invalid-date"

    result = validate_records([record])

    assert result["valid"] is False
    assert any(
        error["field"] == "dob"
        for error in result["errors"]
    )


def test_invalid_record_date():
    record = sample_record()
    record["record_date"] = "invalid-date"

    result = validate_records([record])

    assert result["valid"] is False
    assert any(
        error["field"] == "record_date"
        for error in result["errors"]
    )


def test_duplicate_record_id():
    first = sample_record()
    second = sample_record()

    result = validate_records([first, second])

    assert result["valid"] is False
    assert any(
        error["field"] == "record_id"
        for error in result["errors"]
    )


def test_invalid_resource_type():
    record = sample_record()
    record["resource_type"] = "InvalidResource"

    result = validate_records([record])

    assert result["valid"] is False
    assert any(
        error["field"] == "resource_type"
        for error in result["errors"]
    )
