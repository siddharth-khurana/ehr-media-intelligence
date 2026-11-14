
from app.services.ai.summarizer import (
    extract_diagnoses,
    extract_findings,
    sort_records,
    summarize_locally,
    summarize_patient,
    summarize_with_gemini,
)


def test_extract_diagnoses():
    records = [
        {
            "text_content": (
                "Patient diagnosed with pneumonia. "
                "Treatment started."
            )
        }
    ]

    result = extract_diagnoses(records)

    assert len(result) == 1
    assert "diagnosed with pneumonia" in result[0]


def test_extract_imaging_findings():
    records = [
        {
            "title": "MRI Report",
            "text_content": (
                "Brain MRI shows no acute abnormality. "
                "Mild age-related changes noted."
            )
        }
    ]

    result = extract_findings(records)

    assert len(result) == 2
    assert any("acute abnormality" in item for item in result)
    assert any("age-related changes" in item for item in result)


def test_sort_records_newest_first():
    records = [
        {"record_date": "2025-01-01"},
        {"record_date": "2025-06-01"},
        {"record_date": "2025-03-01"},
    ]

    result = sort_records(records)

    assert result[0]["record_date"] == "2025-06-01"
    assert result[-1]["record_date"] == "2025-01-01"


def test_summarize_locally():
    records = [
        {
            "title": "MRI Report",
            "record_date": "2025-06-01",
            "text_content": (
                "Brain MRI shows no acute abnormality."
            )
        },
        {
            "title": "Progress Note",
            "record_date": "2025-05-01",
            "text_content": "Patient reports improved symptoms."
        }
    ]

    result = summarize_locally(records)

    assert result["chief_concern"]
    assert "MRI Report" in result["recent_media_records"]
    assert isinstance(result["key_diagnoses"], list)
    assert isinstance(result["flagged_anomalies"], list)


def test_summarize_empty_records():
    result = summarize_locally([])

    assert result["chief_concern"] == (
        "Not documented in supplied records."
    )
    assert result["key_diagnoses"] == []
    assert result["recent_media_records"] == []


def test_summarize_with_gemini_returns_valid_json(monkeypatch):
    class FakeResponse:
        text = '{"chief_concern": "Gemini summary", "key_diagnoses": [], "recent_media_records": ["MRI"], "flagged_anomalies": []}'

    class FakeModel:
        def generate_content(self, prompt, generation_config=None):
            return FakeResponse()

    def fake_configure(api_key):
        assert api_key == "gemini-test-key"

    monkeypatch.setattr(
        "app.services.ai.summarizer.settings.gemini_api_key",
        "gemini-test-key",
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.ai.summarizer.settings.gemini_model",
        "gemini-2.0-flash",
        raising=False,
    )
    monkeypatch.setattr(
        "app.services.ai.summarizer.genai",
        type("Dummy", (), {"configure": staticmethod(fake_configure), "GenerativeModel": staticmethod(lambda model: FakeModel())})(),
        raising=False,
    )

    result = summarize_with_gemini("sample clinical record")

    assert result["chief_concern"] == "Gemini summary"
    assert result["recent_media_records"] == ["MRI"]


def test_summarize_patient_falls_back_to_local_on_openai_failure(
    monkeypatch,
):
    records = [
        {
            "title": "Progress Note",
            "record_date": "2025-06-01",
            "text_content": (
                "Patient diagnosed with pneumonia. Follow-up ordered."
            ),
        }
    ]

    monkeypatch.setattr(
        "app.services.ai.summarizer.get_records",
        lambda patient_id: records,
    )
    monkeypatch.setattr(
        "app.services.ai.summarizer.get_summary",
        lambda patient_id, record_hash: None,
    )
    monkeypatch.setattr(
        "app.services.ai.summarizer.save_summary",
        lambda patient_id, record_hash, summary: None,
    )
    monkeypatch.setattr(
        "app.services.ai.summarizer.settings.openai_api_key",
        "fake-key",
        raising=False,
    )

    def raise_openai_error(_corpus):
        raise RuntimeError("OpenAI request failed")

    monkeypatch.setattr(
        "app.services.ai.summarizer.summarize_with_openai",
        raise_openai_error,
    )

    result = summarize_patient("patient-001")

    assert result["provider"] == "local"
    assert result["confidence"].startswith("Local rule-based extraction")
    assert "pneumonia" in result["chief_concern"].lower()
