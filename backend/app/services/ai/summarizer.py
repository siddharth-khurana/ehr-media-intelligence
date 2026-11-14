import hashlib
import json
import re

from google import genai
from google.genai import types

from app.config import settings
from app.db import get_summary, save_summary, get_records


DISCLAIMER = (
    "AI-generated summary for information retrieval only. "
    "It is not a clinical decision or a substitute for clinician review."
)

# Change this version when the summarization logic or prompt changes.
SUMMARY_VERSION = "gemini-v1"

DIAGNOSIS_KEYWORDS = [
    "diagnosis", "diagnosed with", "impression", "assessment",
    "hypertension", "diabetes", "pneumonia", "asthma", "fracture",
    "infection", "anemia", "cancer",
]

IMPORTANT_KEYWORDS = [
    "abnormal", "positive", "negative", "elevated", "increased",
    "decreased", "critical", "normal", "finding", "findings",
    "impression", "recommendation", "age-related", "acute", "mild",
    "severe", "stable", "progression", "resolved",
]


def sort_records(rows):
    """Sort records by date, newest first."""
    return sorted(
        rows,
        key=lambda row: row.get("record_date") or "",
        reverse=True,
    )


def extract_diagnoses(rows):
    """Extract diagnosis-related statements explicitly present in records."""
    diagnoses = []

    for record in rows:
        content = record.get("text_content") or ""
        for sentence in re.split(r"(?<=[.!?])\s+", content):
            sentence = sentence.strip()
            if not sentence:
                continue

            lowered = sentence.lower()
            if any(keyword in lowered for keyword in DIAGNOSIS_KEYWORDS):
                if sentence not in diagnoses:
                    diagnoses.append(sentence)

    return diagnoses[:10]


def extract_findings(rows):
    """Extract sentences containing clinically relevant terms."""
    findings = []

    for record in rows:
        content = record.get("text_content") or ""
        title = record.get("title") or "Clinical document"

        for sentence in re.split(r"(?<=[.!?])\s+", content):
            sentence = sentence.strip()
            if not sentence:
                continue

            lowered = sentence.lower()
            if any(keyword in lowered for keyword in IMPORTANT_KEYWORDS):
                item = f"{title}: {sentence}"
                if item not in findings:
                    findings.append(item)

    return findings[:10]


def summarize_locally(rows):
    """Deterministic fallback when Gemini is not configured or unavailable."""
    sorted_rows = sort_records(rows)
    recent_records = [
        record.get("title") or "Clinical document"
        for record in sorted_rows[:5]
    ]

    findings = extract_findings(sorted_rows)
    diagnoses = extract_diagnoses(sorted_rows)

    if findings:
        chief_concern = " ".join(findings[:3])[:700]
    elif sorted_rows:
        chief_concern = (
            sorted_rows[0].get("text_content")
            or "Clinical details not documented."
        )[:700]
    else:
        chief_concern = "Not documented in supplied records."

    return {
        "chief_concern": chief_concern,
        "key_diagnoses": diagnoses,
        "recent_media_records": recent_records,
        "flagged_anomalies": [
            "Rule-based extraction only. "
            "Clinical anomalies have not been independently verified."
        ],
    }


def summarize_with_gemini(corpus):
    """Generate a structured patient summary using the Gemini API."""
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = f"""
You are a cautious clinical information summarization assistant.
Summarize the following synthetic clinical records.

Return ONLY a valid JSON object with exactly these keys:
{{
  "chief_concern": "Concise summary of the main documented concern",
  "key_diagnoses": [],
  "recent_media_records": [],
  "flagged_anomalies": []
}}

Rules:
- Use only facts explicitly documented in the supplied records.
- Do not invent facts or infer undocumented diagnoses.
- If no diagnosis is explicitly documented, return an empty key_diagnoses array.
- Identify abnormal findings only when the source text supports them.
- Do not provide treatment recommendations or make clinical decisions.
- Keep each list concise.
- Return JSON only, without Markdown fences.

Synthetic clinical records:
{corpus[:18000]}
"""

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        content = response.text
        if not content:
            raise RuntimeError("Gemini returned an empty response.")

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise RuntimeError("Gemini returned an invalid JSON object.")

        # Normalize expected keys and types so the API response stays stable.
        for key in (
            "key_diagnoses",
            "recent_media_records",
            "flagged_anomalies",
        ):
            value = parsed.get(key, [])
            if not isinstance(value, list):
                parsed[key] = [str(value)] if value else []
        parsed["chief_concern"] = str(
            parsed.get("chief_concern") or "Not documented."
        )

        return parsed

    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Gemini returned invalid JSON. Please try again."
        ) from error
    except Exception as error:
        raise RuntimeError(f"Gemini summarization failed: {error}") from error


def summarize_patient(patient_id):
    """Generate a patient summary using Gemini, with a local fallback."""
    rows = get_records(patient_id)
    if not rows:
        raise ValueError("No records found for this patient.")

    sorted_rows = sort_records(rows)
    corpus = "\n".join(
        f"{record.get('title') or 'Clinical record'}: "
        f"{record.get('text_content') or ''}"
        for record in sorted_rows
    )

    use_gemini = bool(settings.gemini_api_key)
    provider = "gemini" if use_gemini else "local"
    model = settings.gemini_model if use_gemini else "rule-based"

    # Provider and model are included to prevent stale local summaries
    # from being returned after Gemini is configured.
    cache_source = (
        f"{SUMMARY_VERSION}:{provider}:{model}:{corpus}"
    )
    record_hash = hashlib.sha256(
        cache_source.encode("utf-8")
    ).hexdigest()

    cached = get_summary(patient_id, record_hash)
    if cached:
        cached["cached"] = True
        return cached

    if use_gemini:
        try:
            parsed = summarize_with_gemini(corpus)
            confidence = (
                f"Gemini-generated using {settings.gemini_model}; "
                "clinician review required."
            )
            actual_provider = "gemini"
            actual_model = settings.gemini_model
        except Exception as error:
            parsed = summarize_locally(sorted_rows)
            confidence = (
                "Gemini request failed; local rule-based extraction "
                f"was used instead. Details: {error}"
            )
            actual_provider = "local"
            actual_model = "rule-based"
    else:
        parsed = summarize_locally(sorted_rows)
        confidence = (
            "Local rule-based extraction; GEMINI_API_KEY not configured."
        )
        actual_provider = "local"
        actual_model = "rule-based"

    result = {
        "patient_id": patient_id,
        "chief_concern": str(
            parsed.get("chief_concern") or "Not documented."
        ),
        "key_diagnoses": parsed.get("key_diagnoses") or [],
        "recent_media_records": parsed.get("recent_media_records") or [],
        "flagged_anomalies": parsed.get("flagged_anomalies") or [],
        "confidence": confidence,
        "provider": actual_provider,
        "model": actual_model,
        "disclaimer": DISCLAIMER,
        "cached": False,
    }

    save_summary(patient_id, record_hash, result)
    return result
