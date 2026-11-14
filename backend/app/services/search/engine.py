
from pathlib import Path
from datetime import date

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.db import get_records


_model = None
_collection = None


def _get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)

    return _model


def _get_collection():
    global _collection

    if _collection is None:
        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = client.get_or_create_collection("ehr_records")

    return _collection


def index_records():
    rows = get_records()

    if not rows:
        return {"indexed": 0}

    model = _get_model()
    collection = _get_collection()

    ids = []
    docs = []
    metas = []

    for row in rows:
        ids.append(row["record_id"])
        docs.append(
            (row.get("title") or "")
            + "\n"
            + (row.get("text_content") or "")
        )
        metas.append({
            "patient_id": row["patient_id"],
            "resource_type": row["resource_type"],
            "record_date": row.get("record_date") or ""
        })

    embeddings = model.encode(
        docs,
        normalize_embeddings=True
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=docs,
        metadatas=metas,
        embeddings=embeddings
    )

    return {"indexed": len(ids)}


def search_records(
    query,
    patient_id=None,
    resource_type=None,
    start_date=None,
    end_date=None,
    top_k=5,
    min_relevance_score=0.20,
    page=1,
    page_size=5,
):
    if page < 1:
        raise ValueError("Page must be at least 1")

    if not 1 <= page_size <= 50:
        raise ValueError("Page size must be between 1 and 50")

    if not 1 <= top_k <= 5:
        raise ValueError("top_k must be between 1 and 5")

    if not 0 <= min_relevance_score <= 1:
        raise ValueError("Minimum relevance score must be between 0 and 1")

    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None

    if start and end and start > end:
        raise ValueError("start_date cannot be after end_date")

    collection = _get_collection()
    model = _get_model()

    count = collection.count()

    if count == 0:
        return {
            "total": 0,
            "total_pages": 0,
            "results": []
        }

    conditions = []

    if patient_id:
        conditions.append({"patient_id": {"$eq": patient_id}})

    if resource_type:
        conditions.append({"resource_type": {"$eq": resource_type}})

    where = None

    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    vector = model.encode(
        [query],
        normalize_embeddings=True
    ).tolist()[0]

    result = collection.query(
        query_embeddings=[vector],
        n_results=count,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    matches = []

    for i, record_id in enumerate(result.get("ids", [[]])[0]):
        meta = result["metadatas"][0][i]
        distance = float(result["distances"][0][i])

        record_date = meta.get("record_date") or ""
        normalized_date = str(record_date)[:10]

        if start:
            if not normalized_date or normalized_date < start.isoformat():
                continue

        if end:
            if not normalized_date or normalized_date > end.isoformat():
                continue

        relevance_score = max(
            0.0,
            min(1.0, 1.0 - (distance / 2.0))
        )

        if relevance_score < min_relevance_score:
            continue

        matches.append({
            "record_id": record_id,
            "patient_id": meta["patient_id"],
            "resource_type": meta["resource_type"],
            "record_date": record_date,
            "text": result["documents"][0][i],
            "relevance_score": round(relevance_score, 4)
        })

    matches.sort(
        key=lambda item: item["relevance_score"],
        reverse=True
    )

    total = len(matches)
    total_pages = (total + page_size - 1) // page_size

    offset = (page - 1) * page_size

    return {
        "total": total,
        "total_pages": total_pages,
        "results": matches[offset:offset + page_size]
    }
