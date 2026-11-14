
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_pagination(monkeypatch):
    def mock_search_records(**kwargs):
        return {
            "total": 2,
            "total_pages": 2,
            "results": [
                {
                    "record_id": "record-001",
                    "patient_id": "patient-006",
                    "resource_type": "DocumentReference",
                    "record_date": "2025-07-01",
                    "text": "MRI findings",
                    "relevance_score": 0.64
                }
            ]
        }

    monkeypatch.setattr(
        "app.main.search_records",
        mock_search_records
    )

    with TestClient(app) as client:
        response = client.post(
            "/search",
            json={
                "query": "brain MRI findings",
                "patient_id": "patient-006",
                "page": 1,
                "page_size": 1
            }
        )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total_pages"] == 2
    assert data["results"][0]["record_id"] == "record-001"


def test_search_invalid_date_range(monkeypatch):
    def mock_search_records(**kwargs):
        raise ValueError("start_date cannot be after end_date")

    monkeypatch.setattr(
        "app.main.search_records",
        mock_search_records
    )

    with TestClient(app) as client:
        response = client.post(
            "/search",
            json={
                "query": "brain MRI findings",
                "start_date": "2025-12-31",
                "end_date": "2025-01-01"
            }
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "start_date cannot be after end_date"
    )
