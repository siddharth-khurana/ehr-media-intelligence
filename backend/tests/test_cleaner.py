from app.services.ingestion.cleaner import clean_records, normalize_date, normalize_gender, normalize_mrn

def test_normalizes_date_and_gender_and_mrn():
    rows, logs = clean_records([{"patient_id":"p1","name":"A Person","dob":"03/12/1980",
                                 "gender":"M","mrn":" ab-123 ","text":"note"}])
    assert rows[0]["dob"] == "1980-03-12"
    assert rows[0]["gender"] == "male"
    assert rows[0]["mrn"] == "AB123"

def test_skips_record_without_identifier():
    rows, logs = clean_records([{"name":"No ID"}])
    assert rows == []
    assert logs[0]["status"] == "skipped"

def test_removes_duplicate_records():
    item = {"patient_id":"p2","name":"B Person","record_date":"2024-01-01","title":"Lab","text":"Normal"}
    rows, logs = clean_records([item,item])
    assert len(rows) == 1
    assert any(log["status"] == "duplicate" for log in logs)

def test_invalid_date_becomes_none():
    assert normalize_date("not-a-date") is None

def test_unknown_gender_is_unknown():
    assert normalize_gender("not specified") == "unknown"

def test_mrn_punctuation_removed():
    assert normalize_mrn("mrn-00 12") == "MRN0012"
