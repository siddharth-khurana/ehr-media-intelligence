from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any

class CanonicalPatient(BaseModel):
    model_config = ConfigDict(extra="ignore")
    patient_id: str
    full_name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    mrn: Optional[str] = None

class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    patient_id: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=5)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=5, ge=1, le=50)
    min_relevance_score: float = Field(default=0.20, ge=0, le=1)

class SummaryResponse(BaseModel):
    patient_id: str
    chief_concern: str
    key_diagnoses: list[str]
    recent_media_records: list[str]
    flagged_anomalies: list[str]
    confidence: str
    disclaimer: str
    cached: bool = False


class IngestResponse(BaseModel):
    files_processed: int
    patients_processed: int
    records_processed: int
    errors: list[str]
    audit_logs: list[dict[str, Any]]
    validation: dict[str, Any]

