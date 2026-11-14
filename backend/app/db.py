import json, sqlite3
from pathlib import Path
from contextlib import contextmanager
from app.config import settings

def _connect():
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_connection():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            dob TEXT,
            gender TEXT,
            mrn TEXT,
            canonical_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS records (
            record_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            record_date TEXT,
            title TEXT,
            text_content TEXT,
            fhir_json TEXT NOT NULL,
            audit_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        );
        CREATE INDEX IF NOT EXISTS idx_records_patient ON records(patient_id);
        CREATE INDEX IF NOT EXISTS idx_records_date ON records(record_date);
        CREATE TABLE IF NOT EXISTS bundles (
            patient_id TEXT PRIMARY KEY,
            bundle_json TEXT NOT NULL,
            validation_json TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(patient_id) REFERENCES patients(patient_id)
        );
        CREATE TABLE IF NOT EXISTS summaries (
            patient_id TEXT NOT NULL,
            record_hash TEXT NOT NULL,
            summary_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(patient_id, record_hash)
        );
        """)

def save_patient(patient):
    with get_connection() as conn:
        conn.execute("""INSERT INTO patients(patient_id,full_name,dob,gender,mrn,canonical_json)
        VALUES(?,?,?,?,?,?) ON CONFLICT(patient_id) DO UPDATE SET
        full_name=excluded.full_name,dob=excluded.dob,gender=excluded.gender,
        mrn=excluded.mrn,canonical_json=excluded.canonical_json""",
        (patient["patient_id"], patient["full_name"], patient.get("dob"),
         patient.get("gender"), patient.get("mrn"), json.dumps(patient)))

def save_record(record):
    with get_connection() as conn:
        conn.execute("""INSERT OR REPLACE INTO records
        (record_id,patient_id,resource_type,record_date,title,text_content,fhir_json,audit_json)
        VALUES(?,?,?,?,?,?,?,?)""",
        (record["record_id"], record["patient_id"], record["resource_type"],
         record.get("record_date"), record.get("title"), record.get("text_content",""),
         json.dumps(record["fhir"]), json.dumps(record.get("audit",[]))))

def save_bundle(patient_id, bundle, validation):
    with get_connection() as conn:
        conn.execute("""INSERT INTO bundles(patient_id,bundle_json,validation_json)
        VALUES(?,?,?) ON CONFLICT(patient_id) DO UPDATE SET
        bundle_json=excluded.bundle_json,validation_json=excluded.validation_json,
        updated_at=CURRENT_TIMESTAMP""",
        (patient_id, json.dumps(bundle), json.dumps(validation)))

def get_patient(patient_id):
    with get_connection() as conn:
        row = conn.execute("SELECT canonical_json FROM patients WHERE patient_id=?", (patient_id,)).fetchone()
        return json.loads(row["canonical_json"]) if row else None

def list_patients():
    with get_connection() as conn:
        return [json.loads(r["canonical_json"]) for r in conn.execute("SELECT canonical_json FROM patients ORDER BY full_name")]

def get_bundle(patient_id):
    with get_connection() as conn:
        row = conn.execute("SELECT bundle_json,validation_json FROM bundles WHERE patient_id=?", (patient_id,)).fetchone()
        return {"bundle":json.loads(row["bundle_json"]), "validation":json.loads(row["validation_json"])} if row else None

def get_records(patient_id=None):
    with get_connection() as conn:
        if patient_id:
            rows = conn.execute("SELECT * FROM records WHERE patient_id=?", (patient_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM records").fetchall()
        return [dict(r) for r in rows]

def get_summary(patient_id, record_hash):
    with get_connection() as conn:
        row = conn.execute("SELECT summary_json FROM summaries WHERE patient_id=? AND record_hash=?", (patient_id,record_hash)).fetchone()
        return json.loads(row["summary_json"]) if row else None

def save_summary(patient_id, record_hash, summary):
    with get_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO summaries(patient_id,record_hash,summary_json) VALUES(?,?,?)",
                     (patient_id,record_hash,json.dumps(summary)))
