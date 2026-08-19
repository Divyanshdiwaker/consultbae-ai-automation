from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS people (
    person_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    email TEXT,
    normalized_email TEXT,
    phone TEXT,
    normalized_phone TEXT,
    city TEXT,
    normalized_city TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_people_email
ON people(normalized_email)
WHERE normalized_email IS NOT NULL AND normalized_email <> '';

CREATE UNIQUE INDEX IF NOT EXISTS ux_people_phone
ON people(normalized_phone)
WHERE normalized_phone IS NOT NULL AND normalized_phone <> '';

CREATE TABLE IF NOT EXISTS source_records (
    source_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    source_name TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    raw_data TEXT NOT NULL,
    match_method TEXT NOT NULL,
    match_confidence REAL NOT NULL,
    data_quality_flags TEXT,
    FOREIGN KEY (person_id) REFERENCES people(person_id)
);

CREATE TABLE IF NOT EXISTS applicant_data (
    person_id INTEGER PRIMARY KEY,
    experience_years REAL,
    current_ctc_inr REAL,
    applied_date TEXT,
    skills TEXT,
    FOREIGN KEY (person_id) REFERENCES people(person_id)
);

CREATE TABLE IF NOT EXISTS gig_worker_data (
    person_id INTEGER PRIMARY KEY,
    rate_amount REAL,
    rate_unit TEXT,
    status TEXT,
    skill_tags TEXT,
    FOREIGN KEY (person_id) REFERENCES people(person_id)
);

CREATE TABLE IF NOT EXISTS cbnexus_data (
    person_id INTEGER PRIMARY KEY,
    verified INTEGER,
    projects_completed INTEGER,
    FOREIGN KEY (person_id) REFERENCES people(person_id)
);

CREATE TABLE IF NOT EXISTS audio_submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration_seconds REAL NOT NULL,
    sample_rate_khz REAL NOT NULL,
    bitrate_kbps REAL,
    loudness_db REAL,
    noise_quality REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (person_id) REFERENCES people(person_id)
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False)
